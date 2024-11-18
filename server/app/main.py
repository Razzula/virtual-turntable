"""FastAPI server application."""
import os
from typing import Final, Optional
from urllib.parse import urlencode
import base64

from fastapi import FastAPI, HTTPException, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.websockets import WebSocketState
from dotenv import load_dotenv
import requests

from app.utils.spotifyAuth import SpotifyAuth
from app.utils.websocketHandler import WebsocketHandler
from app.utils.modelHandler import ModelHandler
from app.utils.centreLabelHandler import CentreLabelHandler
from app.utils.discogsAPI import DiscogsAPI
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
        self.spotifyAuth = SpotifyAuth()
        self.websocketHandler = WebsocketHandler()
        self.modelHandler = ModelHandler(
            ROOT_DIR,
            os.path.join(ROOT_DIR, '..', 'modelling', 'models', 'models'),
        )
        self.discogsAPI = DiscogsAPI(DISCOGS_API_KEY, DISCOGS_API_SECRET, APP_VERSION, APP_CONTACT)
        self.centreLabelhandler = CentreLabelHandler(os.path.join(ROOT_DIR, 'data'), self.discogsAPI)

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
            AUTH_TOKEN: Final = self.spotifyAuth.token().get('access_token')
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

            # SEND TO CLIENT
            await self.websocketHandler.sendToClient({
                'command': 'ALBUM',
                'value': SPOTIFY_ID,
            }, authToken=AUTH_TOKEN)

            return JSONResponse(content={'album': SPOTIFY_ID})

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

            metadata = None

            labelPath = os.path.join(ROOT_DIR, 'data', 'centreLabels', f'{albumID}.png')
            if (not os.path.exists(labelPath)):
                # if label not cached, attempt to find it

                # get data for Discogs API
                albumName = body.get('albumName')
                if (albumName is None):
                    raise HTTPException(status_code=400, detail='No album name provided.')
                artistName = body.get('artistName')
                year = body.get('year')

                # attempt to find a centre label
                centreLabel = self.centreLabelhandler.serveCentreLabel(albumID, albumName, artistName, year, 'vinyl')
                if (centreLabel is None):
                    # re-attmpt with broader search
                    centreLabel = self.centreLabelhandler.serveCentreLabel(albumID, albumName, None, None, None)

                if (centreLabel is None or not os.path.exists(labelPath)):
                    # failed to find a centre label
                    labelData = None
                else:
                    with open(labelPath, "rb") as labelFile:
                        labelData = base64.b64encode(labelFile.read()).decode('utf-8')
                    metadata = centreLabel
            else:
                # load cached label
                with open(labelPath, "rb") as labelFile:
                    labelData = base64.b64encode(labelFile.read()).decode('utf-8')

            response = {
                "imageData": labelData,
            }
            if (metadata is not None):
                response['metadata'] = metadata

            return JSONResponse(content=response)

        # SPOTIFY AUTH
        @self.app.get("/auth/login")
        async def login() -> RedirectResponse:
            return await self.spotifyAuth.login()

        @self.app.get("/auth/callback")
        async def callback(request: Request) -> RedirectResponse:
            return await self.spotifyAuth.callback(request)

        @self.app.get("/auth/token")
        async def token() -> JSONResponse:
            return JSONResponse(self.spotifyAuth.token())

        # WEBSOCKET
        @self.app.websocket("/ws")
        async def connectWebsocket(websocket: WebSocket) -> None:
            await self.websocketHandler.handleConnectionRequest(websocket)

    def get(self) -> FastAPI:
        """Return the FastAPI application singleton."""
        return self.app

serverInstance = Server()
