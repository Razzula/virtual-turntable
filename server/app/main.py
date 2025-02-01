"""FastAPI server application."""
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

ROOT_DIR: Final = os.path.dirname(os.path.abspath(__file__))
print(ROOT_DIR)

class Server:
    """FastAPI server application."""

    def __init__(self) -> None:
        """Initialise the FastAPI application."""

        load_dotenv('.env')
        self.app = FastAPI()

        DISCOGS_API_KEY: Final = os.getenv('DISCOGS_API_KEY')
        DISCOGS_API_SECRET: Final = os.getenv('DISCOGS_API_SECRET')

        APP_VERSION: Final = os.getenv('VERSION')
        APP_CONTACT: Final = os.getenv('CONTACT')

        origins = ['*']
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )

        # setup components
        self.websocketHandler = WebsocketHandler(self.getState, self.updateState)
        self.spotifyAPI = SpotifyAPI(self.websocketHandler.sendToClient, self.resetState)
        self.modelHandler = ModelHandler(
            ROOT_DIR,
            os.path.join(ROOT_DIR, '..', 'modelling', 'models', 'models'),
        )
        self.discogsAPI = DiscogsAPI(DISCOGS_API_KEY, DISCOGS_API_SECRET, APP_VERSION, APP_CONTACT)
        self.centreLabelhandler = CentreLabelHandler(os.path.join(ROOT_DIR, 'data'), self.discogsAPI)
        self.piController = PiController()
        
        self.state = {}

        # setup filestructure
        if (not os.path.exists(os.path.join(ROOT_DIR, 'data'))):
            os.makedirs(os.path.join(ROOT_DIR, 'data'))

        # load model
        self.modelHandler.loadModel(ModelType.OUROBOROS, 'Ouroboros-alpha.pth')

        # configure endpoints
        self.setupRoutes()

    def setupRoutes(self) -> None:
        """Setup the FastAPI routes."""

        # CORE
        @self.app.get("/")
        async def root() -> JSONResponse:
            """Health endpoint"""
            return await test()

        @self.app.get("/test")
        async def test() -> JSONResponse:
            """Health endpoint"""
            return JSONResponse(content={'message': 'Hello, World!'})

        @self.app.get("/ping")
        async def ping() -> JSONResponse:
            """DEV! This endpoint triggers a ping event to the client, from the server."""
            return JSONResponse(await self.websocketHandler.ping())

        # DEV
        @self.app.get("/scan")
        async def scanGet(fileName: str = 'testImage') -> JSONResponse:
            """
                DEV! This endpoint allows a developer to simulate a playevent
                (to mimic what the album detection would do).
            """
            # DETECT ALBUM
            SCAN_RESULT: Final = self.modelHandler.scan(os.path.join(ROOT_DIR, 'data', fileName))

            # FIND SPOTIFY ID
            # if (SCAN_RESULT['predictedProb'] < 0.5):
            #     raise HTTPException(status_code=400, detail='No album (sufficiently) detected.')
            ALBUM: Final = self.modelHandler.classes[SCAN_RESULT['predictedClass']]

            # TODO: extract this to API wrapper
            AUTH_TOKEN: Final = self.spotifyAPI.token().get('access_token')
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
                timeout=10
            )

            REQUEST.raise_for_status()
            RESPONSE: Final = REQUEST.json()
            SPOTIFY_ID = RESPONSE['albums']['items'][0]['id']

            print(SPOTIFY_ID)

            # ADD TO PLAYLIST
            self.spotifyAPI.addAlbumToPlaylist(SPOTIFY_ID, self.spotifyAPI.playlist())

            # SEND TO CLIENT
            await self.websocketHandler.sendToClient({
                'command': 'ALBUM',
                'value': SPOTIFY_ID,
            }, authToken=AUTH_TOKEN)

            return JSONResponse(content={'album': SPOTIFY_ID})

        @self.app.get("/shuffle")
        async def shuffleGet() -> JSONResponse:
            """
                DEV! This endpoint allows a developer to simulate a shuffle event.
            """
            self.spotifyAPI.shufflePlaylist(self.spotifyAPI.playlist())
            return JSONResponse(content={'message': 'Playing'})

        # CLIENT-DRIVEN IMAGE
        @self.app.post("/scan")
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
        @self.app.post("/centreLabel")
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
            images, metadata = self.centreLabelhandler.findReleaseData(albumName, artistName, year, 'vinyl')

            labelPath = os.path.join(ROOT_DIR, 'data', 'centreLabels', f'{albumID}.png')
            if (not os.path.exists(labelPath)):
                # if label not cached, attempt to find it

                # attempt to find a centre label
                foundCentreLabel = self.centreLabelhandler.serveCentreLabel(albumID, images=images)
                if (foundCentreLabel is None):
                    # re-attmpt with broader search
                    foundCentreLabel = self.centreLabelhandler.serveCentreLabel(albumID, albumName, None, None, None)

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
                "imageData": labelData,
            }
            if (metadata):
                response['metadata'] = metadata

            return JSONResponse(content=response)

        @self.app.get("/clientIP")
        async def clientIPGet(request: Request) -> JSONResponse:
            """
                This endpoint serves the client's own IP address back to them.
                This is useful to determine if the client is the host.
            """
            proxiedIP = request.headers.get("x-forwarded-for")
            if (proxiedIP):
                return JSONResponse(content={ 'clientIP': proxiedIP })
            else:
                return JSONResponse(content={ 'clientIP': request.client.host })

        @self.app.get("/playlist")
        async def playlistIDGet(sessionID: str = Cookie(None)) -> JSONResponse:
            """
                This endpoint serves the playlist ID back to the client.
            """
            if (self.spotifyAPI.vttPlaylistID is not None):
                return JSONResponse(content={ 'playlistID': self.spotifyAPI.vttPlaylistID })
            return JSONResponse(content={ 'playlistID': self.spotifyAPI.getPlaylistByName(sessionID, 'Virtual Turntable') })

        @self.app.get("/host")
        async def hostUserGet() -> JSONResponse:
            """
                This endpoint serves the host user's ID back to the client.
            """
            if (self.spotifyAPI.hostUserID is None):
                raise HTTPException(404, 'Host user not found')
            return JSONResponse(content={ 'hostUserID': self.spotifyAPI.hostUserID })

        # SPOTIFY AUTH
        @self.app.get("/auth/login")
        async def login(request: Request) -> RedirectResponse:
            if (request.headers.get("x-forwarded-for")):
                clientIP = request.headers.get("x-forwarded-for")
            else:
                clientIP = request.client.host

            isHost = clientIP == getLocalIP() # if client is host machine
            return await self.spotifyAPI.login(isHost)

        @self.app.get("/auth/callback")
        async def callback(request: Request) -> RedirectResponse:
            SESSION_ID: Final = request.query_params.get('state')
            RESPONSE: Final = await self.spotifyAPI.callback(request, SESSION_ID)
            return RESPONSE

        @self.app.get("/auth/token")
        async def token(sessionID: str = Cookie(None)) -> JSONResponse:
            if (not sessionID):
                raise HTTPException(status_code=400, detail='No session ID provided.')
            return JSONResponse(self.spotifyAPI.token(sessionID))

        @self.app.get("/auth/logout")
        async def logout(sessionID: str = Cookie(None)) -> RedirectResponse:
            if (sessionID and sessionID in self.spotifyAPI.sessions):
                self.spotifyAPI.sessions[sessionID] = None
            return RedirectResponse(url='/')

        # WEBSOCKET
        @self.app.websocket("/ws/main")
        async def connectMainWebsocket(websocket: WebSocket) -> None:
            await self.websocketHandler.handleConnectionRequest(websocket, isMain=True)

        @self.app.websocket("/ws/side")
        async def connectSideWebsocket(websocket: WebSocket) -> None:
            await self.websocketHandler.handleConnectionRequest(websocket, isMain=False)

    def get(self) -> FastAPI:
        """Return the FastAPI application singleton."""
        return self.app
    
    def getState(self) -> dict:
        return self.state
    
    def updateState(self, key: str, value: Any) -> None:
        self.state[key] = value
        
        # react to state
        if (key == 'playState'): # TODO make these enums
            self.piController.setMotorState(value)
    
    def resetState(self) -> None:
        self.state = {}

serverInstance = Server()
