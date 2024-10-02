"""FastAPI server application."""
import os
import random
import string
from urllib.parse import urlencode

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.websockets import WebSocketState
import requests

load_dotenv('.env')

SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

app = FastAPI()
origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

tokens = {}
currentWebsocket = None

# HEALTH ENDPOINTS
@app.get('/')
async def root() -> JSONResponse:
    """Health endpoint"""
    return await test()

@app.get('/test')
async def test() -> JSONResponse:
    """Health endpoint"""
    return JSONResponse(content={'message': 'Hello, World!'})

def generateRandomString(length: int) -> str:
    """Generate a random string of letters and digits with a given length"""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

# WEBSOCKET
@app.websocket('/ws')
async def websocketEndpoint(websocket: WebSocket) -> None:
    """Endpoint that establishes a websocket connection"""
    global currentWebsocket

    if (currentWebsocket is not None):
        print('A client is attempting to connect while another client is already connected.')
        raise HTTPException(status_code=400, detail='Another client is already connected.')

    currentWebsocket = websocket
    await websocket.accept()

    # main loop
    while (True):
        if (websocket.client_state == WebSocketState.DISCONNECTED):
            break

        try:
            request = await websocket.receive_text()
            print(request)
        except Exception as e:
            print('Error with websocket:', e, 'Terminating connection.')
            break

    if (websocket.client_state != WebSocketState.DISCONNECTED):
        await websocket.close()
    currentWebsocket = None

async def sendToClient(data: dict[str, str], supplyAuth: bool = False) -> None:
    """Send a message to the client"""
    if (currentWebsocket is None):
        print('No client connected.')
        return
    if (supplyAuth and (ACCESS_TOKEN := tokens.get('access_token'))):
        data['token'] = ACCESS_TOKEN

    await currentWebsocket.send_json(data)

# PI CONTROLS
@app.get('/ping')
async def ping() -> JSONResponse:
    """DEV! This endpoint triggers a ping event to the client, from the server."""
    if (currentWebsocket is None):
        raise HTTPException(status_code=400, detail='No client connected.')

    await sendToClient({'message': 'ping'})
    return JSONResponse(content={'message': 'ping'})

@app.get('/setAlbum')
async def setAlbum() -> JSONResponse:
    """
        DEV! This endpoint allows a developer to simulate a playevent
        (to mimic what the album detection would do).
    """

    await sendToClient({
        'command': 'ALBUM',
        'value': '7ligZljXfUtcKPCotWul5g', # Jeff Wayne's Musical Version of The War of The Worlds
    }, supplyAuth=True)
    return JSONResponse(content={'message': 'play'})

# SPOTIFY AUTHENTICATION
@app.get('/auth/login')
async def login() -> RedirectResponse:
    """Spotify auth login endpoint"""

    scope = 'streaming user-read-email user-read-private user-modify-playback-state'
    state = generateRandomString(16)

    authQueryParameters = {
        'response_type': "code",
        'client_id': SPOTIFY_CLIENT_ID,
        'scope': scope,
        'redirect_uri': 'http://localhost:1948/virtual-turntable/auth/callback',
        'state': state
    }
    url = f'https://accounts.spotify.com/authorize/?{urlencode(authQueryParameters)}'

    return RedirectResponse(url)

@app.get('/auth/callback')
async def callback(request: Request) -> RedirectResponse:
    """Spotify auth callback endpoint"""

    AUTH_CODE = request.query_params.get('code')
    if (not AUTH_CODE):
        raise HTTPException(status_code=400, detail='Missing authorisation code.')

    REDIRECT_URI = 'http://localhost:1948/virtual-turntable/auth/callback'

    response = requests.post(
        'https://accounts.spotify.com/api/token',
        data = {
            'code': AUTH_CODE,
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code'
        },
        auth = (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
        timeout = 20
    )

    response.raise_for_status()
    BODY = response.json()
    tokens['access_token'] = BODY.get('access_token')

    return RedirectResponse(url='/')

@app.get('/auth/token')
async def token() -> JSONResponse:
    """Spotify auth token endpoint"""
    ACCESS_TOKEN = tokens.get('access_token')
    if (not ACCESS_TOKEN):
        raise HTTPException(status_code=404, detail='Access token not found.')

    return JSONResponse(content={'access_token': ACCESS_TOKEN})
