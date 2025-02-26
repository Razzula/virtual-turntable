"""FastAPI server application."""

import asyncio
import os
from typing import Any, Final, Optional
from urllib.parse import urlencode
import base64

from fastapi import FastAPI, HTTPException, WebSocket, Request, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.websockets import WebSocketState
from dotenv import load_dotenv
import requests

from app.utils.spotifyAPI import SpotifyAPI, getLocalIP
from app.utils.websocketHandler import WebsocketHandler
from app.utils.modelHandler import ModelHandler
from app.utils.centreLabelHandler import CentreLabelHandler
from app.utils.discogsAPI import DiscogsAPI
from app.utils.piController import PiController
from modelling.models.ModelType import ModelType
from app.enums.StateKeys import Commands, StateKeys

ROOT_DIR: Final = os.path.dirname(os.path.abspath(__file__))
print(ROOT_DIR)


class Server:
    """FastAPI server application."""

    def __init__(self) -> None:
        """Initialise the FastAPI application."""
        # SETUP
        load_dotenv('.env')
        self.app = FastAPI()

        DISCOGS_API_KEY: Final = os.getenv('DISCOGS_API_KEY')
        DISCOGS_API_SECRET: Final = os.getenv('DISCOGS_API_SECRET')

        APP_VERSION: Final = os.getenv('VERSION')
        APP_CONTACT: Final = os.getenv('CONTACT')

        GPIO_ACCESS: Final = os.getenv('GPIO_ACCESS')
        
        HOSTNAME: Final = os.getenv('HOSTNAME', 'localhost')

        origins = ['*']
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )

        # setup modules
        self.websocketHandler = WebsocketHandler(self.getState, self.handleCommand)
        self.spotifyAPI = SpotifyAPI(HOSTNAME, self.websocketHandler.broadcast, self.resetState)
        self.modelHandler = ModelHandler(
            ROOT_DIR,
            os.path.join(ROOT_DIR, '..', 'modelling', 'models', 'models'),
        )
        self.discogsAPI = DiscogsAPI(
            DISCOGS_API_KEY, DISCOGS_API_SECRET, APP_VERSION, APP_CONTACT
        )
        self.centreLabelhandler = CentreLabelHandler(
            os.path.join(ROOT_DIR, 'data'), self.discogsAPI
        )
        if (GPIO_ACCESS is None or GPIO_ACCESS != 'off'):
            self.piController = PiController()
            print('Hardware controller configured.')
        else:
            self.piController = None

        # setup components
        self.__state = {
            'playState': False,
            'settings': {
                'enableMotor': True,
                'enableRemote': True,
                'enforceSignature': True,
                'volume': 50,
            },
        }

        # setup hardware listeners
        if self.piController is not None:
            asyncio.create_task(
                self.piController.reactToHinge(
                    onClosed=lambda: self.updateState(StateKeys.PLAY_STATE, False),
                    onOpen=lambda: self.updateState(StateKeys.PLAY_STATE, True),
                )
            )

            asyncio.create_task(
                self.piController.reactToButton(
                    onDown=lambda: self.triggerCamera(),
                )
            )

            asyncio.create_task(
                self.piController.reactToEncoder(
                    onFreeRotate=lambda x: self.updateVolume(x),
                    onDownRotate=lambda x: self.changeTrack(x),
                    onDownOnly=lambda: self.togglePlayState(),
                )
            )

        # setup filestructure
        if (not os.path.exists(os.path.join(ROOT_DIR, 'data'))):
            os.makedirs(os.path.join(ROOT_DIR, 'data'))

        # load model
        self.modelHandler.loadModel(ModelType.OUROBOROS, 'Ouroboros-alpha.pth')

        # configure endpoints
        self.setupRoutes()
        self.app.add_event_handler('shutdown', self.shutdown)

    def get(self) -> FastAPI:
        """Return the FastAPI application singleton."""
        return self.app

    # STATE MANAGEMENT
    def getState(self) -> dict:
        """TODO"""
        return self.__state

    async def updateState(self, key: StateKeys, value: Any) -> None:
        """TODO"""
        if (self.__state.get(key.value) == value):
            # non-update, can be ignored
            return
        self.__state[key.value] = value

        # react to state change
        # manage hardware broadcasts
        if (self.piController is not None):
            if (key == StateKeys.SETTINGS):
                if (value.get('enableMotor', False)):
                    self.piController.setMotorSpeed(100)
                else:
                    self.piController.setMotorSpeed(0)

            if (key == StateKeys.PLAY_STATE):
                self.piController.setMotorState(1 if value else 0)
            elif (key == Commands.FAST_FORWARD):
                self.piController.setMotorState(1)
            elif (key == Commands.REWIND):
                self.piController.setMotorState(-1)

        # manage software broadcasts
        if (key in [StateKeys.PLAY_STATE, StateKeys.CURRENT_TRACK, StateKeys.SETTINGS]):
            await self.websocketHandler.broadcast(
                {'command': key.value, 'value': value}
            )

    def resetState(self) -> None:
        """TODO"""
        self.__state = {
            'playState': False,
            'settings': {
                'enableMotor': True,
                'enableRemote': True,
                'enforceSignature': True,
            },
        }

    async def handleCommand(
        self, sessionID: str, command: str, value: Any = None
    ) -> None:
        """TODO"""
        requestFromHost = self.spotifyAPI.sessions[sessionID]['isHost']
        requestFromHostUser = (
            self.spotifyAPI.sessions[sessionID]['userID'] == self.spotifyAPI.hostUserID
        )
        settings = self.__state.get('settings')
        if (settings and not requestFromHost):
            if (not settings.get('enableRemote', False)):
                print('Remote calls disabled. Call ignored.')
                return
            if (settings.get('enforceSignature', True) and not requestFromHostUser):
                print(sessionID, 'is not host. Call ignored.')
                return

        # state modifications
        for key in [StateKeys.PLAY_STATE, StateKeys.CURRENT_TRACK]:
            if (command == key.value):
                await self.updateState(key, value)
                return

        if (command == StateKeys.SETTINGS.value):
            if (not requestFromHost):
                # only allow host to control sensitive settings
                for setting in ['enableMotor', 'enableRemote', 'enforceSignature']:
                    if (settings.get(setting) != value.get(setting)):
                        print(sessionID, 'is not host')
                        return
                # settings such as volume, are allowed
            await self.updateState(StateKeys.SETTINGS, value)
            return

        # to-server commands
        # for key in [Commands.FAST_FORWARD, Commands.REWIND]:
        #     if (command == key.value):
        #         await self.updateState(StateKeys.PLAY_STATE, False)
        #         if (self.piController is not None):
        #             self.piController.setMotorState(-1 if (key == Commands.REWIND) else 1)
        #         return

        # if (command == Commands.SEEK.value):
        #     pass

        # remote-to-host commands
        for key in [Commands.PLAY_NEXT, Commands.PLAY_PREVIOUS]:
            if (command == key.value):
                await self.websocketHandler.sendToHost({'command': command})
                return

        for key in [Commands.PLAY_ALBUM]:
            if (command == key.value):
                await self.websocketHandler.sendToHost({'command': command, 'value': value})
                return

    async def togglePlayState(self) -> None:
        """TODO"""
        currentPlayState = self.getState().get(StateKeys.PLAY_STATE.value)
        await self.updateState(StateKeys.PLAY_STATE, not currentPlayState)

    async def updateVolume(self, delta) -> None:
        """TODO"""
        currentSettings = self.getState().get('settings')
        if (currentSettings):
            currentVolume = currentSettings.get('volume', 50)
            newVolume = min(100, max(0, currentVolume + (delta * 5)))
            newSettings = currentSettings.copy()
            newSettings['volume'] = newVolume
            await self.updateState(StateKeys.SETTINGS, newSettings)

    async def changeTrack(self, direction) -> None:
        """TODO"""
        if (direction > 0):
            await self.websocketHandler.sendToHost(
                {'command': Commands.PLAY_NEXT.value}
            )
        elif (direction < 0):
            await self.websocketHandler.sendToHost(
                {'command': Commands.PLAY_PREVIOUS.value}
            )

    async def triggerCamera(self) -> None:
        """TODO"""
        print('Lights! Camera! Action!!')

    # Setup FastAPI endpoints
    def setupRoutes(self) -> None:
        """Setup the FastAPI routes."""

        # CORE
        @self.app.get('/')
        async def root() -> JSONResponse:
            """Health endpoint"""
            return await test()

        @self.app.get('/test')
        async def test() -> JSONResponse:
            """Health endpoint"""
            return JSONResponse(content={'message': 'Hello, World!'})

        @self.app.get('/ping')
        async def ping() -> JSONResponse:
            """DEV! This endpoint triggers a ping event to the client, from the server."""
            return JSONResponse(await self.websocketHandler.ping())

        # DEV
        @self.app.get('/scan')
        async def scanGet(fileName: str = 'testImage') -> JSONResponse:
            """
            DEV! This endpoint allows a developer to simulate a playevent
            (to mimic what the album detection would do).
            """
            # DETECT ALBUM
            SCAN_RESULT: Final = self.modelHandler.scan(
                os.path.join(ROOT_DIR, 'data', fileName)
            )

            # FIND SPOTIFY ID
            # if (SCAN_RESULT['predictedProb'] < 0.5):
            #     raise HTTPException(status_code=400, detail='No album (sufficiently) detected.')
            ALBUM: Final = self.modelHandler.classes[SCAN_RESULT['predictedClass']]

            # TODO: extract this to API wrapper
            AUTH_TOKEN: Final = self.spotifyAPI.hostToken()
            PARAMS: Final = {
                'q': f'{ALBUM["name"]} artist:{ALBUM["artist"]} year:{ALBUM["year"]}',
                'type': 'album',
                'limit': 1,
            }
            REQUEST: Final = requests.get(
                f'https://api.spotify.com/v1/search/?{urlencode(PARAMS)}',
                headers={
                    'Authorization': f'Bearer {AUTH_TOKEN}',
                },
                timeout=10,
            )

            REQUEST.raise_for_status()
            RESPONSE: Final = REQUEST.json()
            SPOTIFY_ID = RESPONSE['albums']['items'][0]['id']

            print(SPOTIFY_ID)

            # ADD TO PLAYLIST
            self.spotifyAPI.addAlbumToPlaylist(SPOTIFY_ID, self.spotifyAPI.playlist())

            # SEND TO CLIENT
            await self.websocketHandler.sendToHost({
                'command': 'playAlbum',
                'value': SPOTIFY_ID,
            })

            return JSONResponse(content={'album': SPOTIFY_ID})

        @self.app.get('/shuffle')
        async def shuffleGet() -> JSONResponse:
            """
            DEV! This endpoint allows a developer to simulate a shuffle event.
            """
            self.spotifyAPI.shufflePlaylist(self.spotifyAPI.playlist())
            return JSONResponse(content={'message': 'Playing'})

        # CLIENT-DRIVEN IMAGE
        @self.app.post('/scan')
        async def scanPost(request: Request) -> JSONResponse:
            """
            This endpoint allows a client to send an image to the server for album detection.
            """
            # validate body content
            body = await request.body()
            if (not body):
                raise HTTPException(status_code=400, detail='No image data provided.')

            # save image
            IMAGE_PATH: Final = os.path.join(ROOT_DIR, 'data', 'upload.png')
            with open(IMAGE_PATH, 'wb') as file:
                file.write(body)

            return await scanGet('upload.png') # TODO: refactor to use genuine method, when available

        # CENTRE LABEL
        @self.app.post('/centreLabel')
        async def centreLabelGet(request: Request) -> JSONResponse:
            """
            This endpoint serves the centre label for the given album.
            """
            # validate body content
            body = await request.json()
            if (not body):
                raise HTTPException(status_code=400, detail='No data provided.')

            albumID = body.get('albumID', 'undefined')
            if (albumID == 'undefined'):
                raise HTTPException(status_code=400, detail='No album provided.')

            # get data for Discogs API
            albumName = body.get('albumName')
            if (albumName is None):
                raise HTTPException(status_code=400, detail='No album name provided.')
            artistName = body.get('artistName')
            year = body.get('year')

            # get data
            images, metadata = self.centreLabelhandler.findReleaseData(
                albumName, artistName, year, 'vinyl'
            )

            labelPath = os.path.join(ROOT_DIR, 'data', 'centreLabels', f'{albumID}.png')
            if (not os.path.exists(labelPath)):
                # if label not cached, attempt to find it

                # attempt to find a centre label
                foundCentreLabel = self.centreLabelhandler.serveCentreLabel(
                    albumID, images=images
                )
                if foundCentreLabel is None:
                    # re-attmpt with broader search
                    foundCentreLabel = self.centreLabelhandler.serveCentreLabel(
                        albumID, albumName, None, None, None
                    )

                if (not foundCentreLabel or not os.path.exists(labelPath)):
                    # failed to find a centre label
                    labelData = None
                else:
                    with open(labelPath, "rb") as labelFile:
                        labelData = base64.b64encode(labelFile.read()).decode('utf-8')
            else:
                # load cached label
                with open(labelPath, "rb") as labelFile:
                    labelData = base64.b64encode(labelFile.read()).decode('utf-8')

            response = {
                'imageData': labelData,
            }
            if (metadata):
                response['metadata'] = metadata

            return JSONResponse(content=response)

        @self.app.get('/isHost')
        async def clientIPGet(request: Request) -> JSONResponse:
            """
            This endpoint serves the client's own IP address back to them.
            This is useful to determine if the client is the host.
            """
            hostIP = getLocalIP()
            proxiedIP = request.headers.get("x-forwarded-for")
            return JSONResponse(content={ 'clientIP': proxiedIP, 'isHost': (hostIP == proxiedIP) })

        @self.app.get('/playlist')
        async def playlistIDGet(sessionID: str = Cookie(None)) -> JSONResponse:
            """
            This endpoint serves the playlist ID back to the client.
            """
            if (self.spotifyAPI.vttPlaylistID is not None):
                return JSONResponse(
                    content={'playlistID': self.spotifyAPI.vttPlaylistID}
                )
            return JSONResponse(
                content={
                    'playlistID': self.spotifyAPI.getPlaylistByName(
                        sessionID, 'Virtual Turntable'
                    )
                }
            )

        @self.app.get('/host')
        async def hostUserGet() -> JSONResponse:
            """
            This endpoint serves the host user's ID back to the client.
            """
            if (self.spotifyAPI.hostUserID is None):
                raise HTTPException(404, 'Host user not found')
            return JSONResponse(content={ 'hostUserID': self.spotifyAPI.hostUserID })

        # SPOTIFY AUTH
        @self.app.get('/auth/login')
        async def login(request: Request) -> RedirectResponse:
            if (request.headers.get("x-forwarded-for")):
                clientIP = request.headers.get("x-forwarded-for")
            else:
                clientIP = request.client.host

            isHost = clientIP == getLocalIP() # if client is host machine
            return await self.spotifyAPI.login(isHost)

        @self.app.get('/auth/callback')
        async def callback(request: Request) -> RedirectResponse:
            SESSION_ID: Final = request.query_params.get('state')
            RESPONSE: Final = await self.spotifyAPI.callback(request, SESSION_ID)
            return RESPONSE

        @self.app.get('/auth/token')
        async def token(sessionID: str = Cookie(None)) -> JSONResponse:
            if (not sessionID):
                raise HTTPException(status_code=400, detail='No session ID provided.')
            return JSONResponse(self.spotifyAPI.token(sessionID))

        @self.app.get('/auth/logout')
        async def logout(sessionID: str = Cookie(None)) -> RedirectResponse:
            if (sessionID and sessionID in self.spotifyAPI.sessions):
                self.spotifyAPI.sessions[sessionID] = None
            return RedirectResponse(url='/')

        # WEBSOCKET
        @self.app.websocket('/ws')
        async def connectMainWebsocket(websocket: WebSocket, sessionID: str = Cookie(None)) -> None:
            if (not sessionID):
                await websocket.close(code=4001)
                return
            session = self.spotifyAPI.sessions.get(sessionID)
            if not session:
                await websocket.close(code=4001)
                return
            await self.websocketHandler.handleConnection(
                websocket, sessionID=sessionID, isMain=session.get('isHost', False)
            )

    async def shutdown(self) -> None:
        """Ensure all background tasks are cancelled when stopping."""
        await asyncio.gather()


serverInstance = Server()
