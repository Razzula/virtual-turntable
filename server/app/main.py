"""FastAPI server application."""

import asyncio
import os
from typing import Any, Final

import cv2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.enums.StateKeys import Commands, StateKeys
from app.modules.centreLabelHandler import CentreLabelHandler
from app.modules.modelHandler import ModelHandler
from app.APIs.MusicAPI.IMusicAPI import IMusicAPI
from app.APIs.MusicAPI.SpotifyAPI import SpotifyAPI
from app.modules.Hardware.piController import PiController
from app.modules.sessionManager import SessionManager
from app.utils import isHostIP
from app.modules.websocketHandler import WebsocketHandler
from app.routes import setupRoutes
from app.APIs.DiscogsAPI import DiscogsAPI
from modelling.models.utils.ModelType import ModelType
from app.modules.stateManager import StateManager


class Server:
    """FastAPI server application."""

    def __init__(self) -> None:
        """Initialise the FastAPI application."""
        # SETUP
        self.ROOT_DIR: Final = os.path.dirname(os.path.abspath(__file__))
        print(self.ROOT_DIR)

        load_dotenv('.env')
        self.app = FastAPI()

        DISCOGS_API_KEY: Final = os.getenv('DISCOGS_API_KEY')
        DISCOGS_API_SECRET: Final = os.getenv('DISCOGS_API_SECRET')

        APP_VERSION: Final = os.getenv('VERSION')
        APP_CONTACT: Final = os.getenv('CONTACT')

        GPIO_ACCESS: Final = os.getenv('GPIO_ACCESS')

        HOSTNAME: Final = os.getenv('HOSTNAME', 'localhost')
        MUSIC_PROVIDER = 'Spotify'

        origins = ['*']
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )

        # setup modules
        self.sessionManager = SessionManager()
        self.websocketHandler = WebsocketHandler(self.getState, self.handleCommand)

        if (MUSIC_PROVIDER == 'Spotify'):
            self.musicAPI: IMusicAPI = SpotifyAPI(
                self.sessionManager, HOSTNAME, self.websocketHandler.broadcast, self.resetState
            )
        else:
            raise NotImplementedError('Specified music provider not supported.')

        self.modelHandler = ModelHandler(
            self.ROOT_DIR,
            os.path.join(self.ROOT_DIR, '..', 'modelling', 'models', 'models'),
        )
        self.discogsAPI = DiscogsAPI(
            DISCOGS_API_KEY, DISCOGS_API_SECRET, APP_VERSION, APP_CONTACT
        )
        self.centreLabelhandler = CentreLabelHandler(
            os.path.join(self.ROOT_DIR, 'data'), self.discogsAPI
        )
        if (GPIO_ACCESS is None or GPIO_ACCESS != 'off'):
            self.hardwareController = PiController()
            print('Hardware controller configured.')
        else:
            self.hardwareController = None

        self.stateManager = StateManager(
            self.websocketHandler,
            self.hardwareController,
            self.musicAPI.getProviderName(),
        )

        # setup hardware listeners
        if (self.hardwareController is not None):
            asyncio.create_task(
                self.hardwareController.reactToHinge(
                    onClosed=lambda: self.stateManager.updateState(StateKeys.PLAY_STATE, False),
                    onOpen=lambda: self.stateManager.updateState(StateKeys.PLAY_STATE, True),
                )
            )

            asyncio.create_task(
                self.hardwareController.reactToButton(
                    onDown=self.triggerCamera,
                )
            )

            asyncio.create_task(
                self.hardwareController.reactToEncoder(
                    onFreeRotate=self.updateVolume,
                    onDownRotate=self.changeTrack,
                    onDownOnly=self.togglePlayState,
                )
            )

        # setup filestructure
        if (not os.path.exists(os.path.join(self.ROOT_DIR, 'data'))):
            os.makedirs(os.path.join(self.ROOT_DIR, 'data'))

        # load model
        self.modelHandler.loadModel(ModelType.BABY_OUROBOROS, 'BabyOuroboros-mini.pth')

        # configure endpoints
        self.setupRoutes()
        self.app.add_event_handler('shutdown', self.shutdown)

    def get(self) -> FastAPI:
        """Return the FastAPI application singleton."""
        return self.app

    def getState(self) -> dict[str, bool | dict[str, bool | int]]:
        """Return the current state of the application."""
        state = self.stateManager.getState()
        if (isinstance(state, dict)):
            return state
        else:
            raise TypeError('State is not of expected type')

    def resetState(self) -> None:
        """Reset the state of the application."""
        self.stateManager.resetState()

    async def handleCommand(
        self, sessionID: str, command: str, value: Any = None
    ) -> None:
        """TODO"""
        currentUserID = self.sessionManager.getSession(sessionID).get('userID')
        requestIsFromHost = self.sessionManager.getSession(sessionID).get('isHost', False)
        requestIsFromHostUser = (
            # ensure this user is the host (either from host or remote device)
            # hence, check userID, not sessionID
            currentUserID == self.sessionManager.getHostUserID()
        )
        settings = self.stateManager.getState().get('settings')
        if (settings and not requestIsFromHost):
            if (not isinstance(settings, dict)):
                print('Settings are not a dictionary.')
                # since settings cannot be fetched, assume strictest settings
                settings = {
                    'enableRemote': False,
                    'enforceSignature': True,
                }
            if (not settings.get('enableRemote', False)):
                print('Remote calls disabled. Call ignored.')
                return
            if (settings.get('enforceSignature', True) and not requestIsFromHostUser):
                print(sessionID, 'is not host. Call ignored.')
                return

        # state modifications
        for key in [StateKeys.PLAY_STATE, StateKeys.CURRENT_TRACK]:
            if (command == key.value):
                await self.stateManager.updateState(key, value)
                return

        if (command == StateKeys.SETTINGS.value):
            if (not requestIsFromHost):
                # only allow host to control sensitive settings
                for setting in ['enableMotor', 'enableRemote', 'enforceSignature']:
                    if (not isinstance(settings, dict)):
                        # since settings cannot be fetched, protect sensitive settings
                        return
                    if (settings.get(setting) != value.get(setting)):
                        print(sessionID, 'is not host')
                        return
                # settings such as volume, are allowed
            await self.stateManager.updateState(StateKeys.SETTINGS, value)
            return

        # remote-to-host commands
        for key in [Commands.PLAY_NEXT, Commands.PLAY_PREVIOUS]:
            if (command == key.value):
                await self.websocketHandler.sendToHost({'command': command})
                return

        for key in [Commands.PLAY_ALBUM, Commands.PLAY_PLAYLIST]:
            if (command == key.value):
                await self.websocketHandler.sendToHost({'command': command, 'value': value})
                return

    async def togglePlayState(self) -> None:
        """TODO"""
        currentPlayState = self.getState().get(StateKeys.PLAY_STATE.value)
        await self.stateManager.updateState(StateKeys.PLAY_STATE, not currentPlayState)

    async def updateVolume(self, delta: float) -> None:
        """TODO"""
        currentSettings = self.getState().get('settings')
        if (isinstance(currentSettings, dict) and currentSettings):
            currentVolume = currentSettings.get('volume', 50)
            if (not isinstance(currentVolume, int)):
                currentVolume = 50
            newVolume = min(100, max(0, currentVolume + (delta * 5)))
            newSettings = currentSettings.copy()
            newSettings['volume'] = int(newVolume)
            await self.stateManager.updateState(StateKeys.SETTINGS, newSettings)

    async def changeTrack(self, direction: float) -> None:
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
        captures = self.hardwareController.takePhotos(maxCameras=3)

        if (not captures):
            return
        print('Captured camera(s)')

        dirPath = os.path.join(self.ROOT_DIR, 'data', 'captures')
        if (not os.path.exists(dirPath)):
            # create dir
            os.makedirs(dirPath)
        else:
            # clear previous results
            for fileName in os.listdir(dirPath):
                filePath = os.path.join(dirPath, fileName)
                if (os.path.isfile(filePath) or os.path.islink(filePath)):
                    os.unlink(filePath)

        # handle new images
        sent = False
        for (i, frame) in enumerate(captures):
            if (frame is None):
                continue

            # get image dimensions
            height, width, _ = frame.shape

            # determine center square
            size = min(height, width)
            xStart = (width - size) // 2
            yStart = (height - size) // 2

            # crop
            croppedFrame = frame[yStart:yStart + size, xStart:xStart + size]

            fileName = f'capture{i}.jpg'
            cv2.imwrite(os.path.join(dirPath, fileName), croppedFrame)

            if (not sent):
                # start rendering process in client, whilst model runs prediction
                await self.websocketHandler.sendToHost({
                    'command': 'capture'
                })  # serve image to host client

        await self.predictAndPlayAlbum('captures')  # run album prediction, and serve to host

    async def predictAndPlayAlbum(self, fileName: str) -> JSONResponse:
        """TODO"""
        # DETECT ALBUM
        SCAN_RESULT: Final = self.modelHandler.scan(
            os.path.join(self.ROOT_DIR, 'data', fileName)
        )

        # HANDLE RESULT
        result = None
        if (len(SCAN_RESULT) > 1):
            # consensus
            currentMax = 0
            for scanResult in SCAN_RESULT:
                if (scanResult.get('predictedProb', 0) > currentMax):
                    result = scanResult
                    currentMax = scanResult.get('predictedProb', 0)
        elif (len(SCAN_RESULT) == 1):
            # singular
            result = SCAN_RESULT[0]
        else:
            raise HTTPException(status_code=404, detail='No prediction found for images.')

        if (result is None):
            raise HTTPException(status_code=400, detail='No album detected.')

        # if (result['predictedProb'] < 0.5):
        #     raise HTTPException(status_code=400, detail='No album (sufficiently) detected.')
        ALBUM: Final = self.modelHandler.classes[result['predictedClass']]

        # FIND VENDOR'S ID
        ALBUM_ID: Final = self.musicAPI.searchForAlbum(ALBUM)
        if (ALBUM_ID is None):
            raise HTTPException(
                status_code=404, detail=f'Album not found on {self.musicAPI.getProviderName()}.'
            )
        print(ALBUM_ID)

        # ADD TO PLAYLIST
        self.musicAPI.addAlbumToPlaylist(ALBUM_ID, self.sessionManager.getHostPlaylistID())
        await self.websocketHandler.broadcast({
            'command': Commands.REFRESH_PLAYLIST.value,
            'value': self.sessionManager.getHostPlaylistID(),
        })

        # SEND TO CLIENTM
        await self.websocketHandler.sendToHost({
            'command': Commands.PLAY_ALBUM.value,
            'value': ALBUM_ID,
        })

        return JSONResponse(content={'album': ALBUM_ID})

    # Setup FastAPI endpoints
    def setupRoutes(self) -> None:
        """Setup the FastAPI routes."""
        setupRoutes(self)

    async def shutdown(self) -> None:
        """Ensure all background tasks are cancelled when stopping."""
        await asyncio.gather()


serverInstance = Server()
