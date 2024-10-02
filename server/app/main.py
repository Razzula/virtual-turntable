"""FastAPI server application."""
import os
import random
import string
from urllib.parse import urlencode

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
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

    print(response)
    print((SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
    response.raise_for_status()
    BODY = response.json()
    tokens['access_token'] = BODY.get('access_token')
    print(BODY)

    return RedirectResponse(url='/')

@app.get('/auth/token')
async def token() -> JSONResponse:
    """Spotify auth token endpoint"""
    ACCESS_TOKEN = tokens.get('access_token')
    if (not ACCESS_TOKEN):
        raise HTTPException(status_code=404, detail='Access token not found.')

    return JSONResponse(content={'access_token': ACCESS_TOKEN})
