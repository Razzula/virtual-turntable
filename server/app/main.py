"""FastAPI server application."""
import os
from typing import Final, Optional
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.websockets import WebSocketState
from dotenv import load_dotenv
import requests

from app.utils.spotifyAuth import SpotifyAuth
from app.utils.websocketHandler import WebsocketHandler
from app.utils.modelHandler import ModelHandler

ROOT_DIR: Final = os.path.dirname(os.path.abspath(__file__))
print(ROOT_DIR)

class Server:
    """FastAPI server application."""

    def __init__(self) -> None:
        """Initialise the FastAPI application."""

        load_dotenv('.env')
        self.app = FastAPI()

        origins = ['*']
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )

        self.spotifyAuth = SpotifyAuth()
        self.websocketHandler = WebsocketHandler()
        self.modelHandler = ModelHandler(ROOT_DIR, os.path.join(ROOT_DIR, '..', 'modelling', 'models', 'models', 'simpleCNN.pth'))

        self.setupRoutes()

    def setupRoutes(self) -> None:
        """Setup the FastAPI routes."""

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

        @self.app.get("/scan")
        async def scan() -> JSONResponse:
            """
                DEV! This endpoint allows a developer to simulate a playevent
                (to mimic what the album detection would do).
            """
            # DETECT ALBUM
            SCAN_RESULT: Final = self.modelHandler.scan(os.path.join(ROOT_DIR, 'data', 'testImage.png'))

            # FIND SPOTIFY ID
            if (SCAN_RESULT['predictedProb'] < 0.5):
                raise HTTPException(status_code=400, detail='No album (sufficiently) detected.')
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

        @self.app.get("/auth/login")
        async def login() -> RedirectResponse:
            return await self.spotifyAuth.login()

        @self.app.get("/auth/callback")
        async def callback(request: Request) -> RedirectResponse:
            return await self.spotifyAuth.callback(request)

        @self.app.get("/auth/token")
        async def token() -> JSONResponse:
            return JSONResponse(self.spotifyAuth.token())

        @self.app.websocket("/ws")
        async def connectWebsocket(websocket: WebSocket) -> None:
            await self.websocketHandler.handleConnectionRequest(websocket)

    def get(self) -> FastAPI:
        """Return the FastAPI application singleton."""
        return self.app

serverInstance = Server()
