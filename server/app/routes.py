"""This module contains the FastAPI routes for the server."""
import base64
import os
from typing import Final, TYPE_CHECKING

from fastapi import Cookie, FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import JSONResponse, RedirectResponse

from app.utils import isHostIP

if (TYPE_CHECKING):
    from app.main import Server


def setupRoutes(server: 'Server') -> None:
    """Setup the FastAPI routes."""
    app: FastAPI = server.app

    @app.get('/')
    async def root() -> JSONResponse:
        """Health endpoint"""
        return await test()

    @app.get('/test')
    async def test() -> JSONResponse:
        """Health endpoint"""
        return JSONResponse(content={'message': 'Hello, World!'})

    @app.get('/ping')
    async def ping() -> JSONResponse:
        """DEV! This endpoint triggers a ping event to the client, from the server."""
        return JSONResponse(await server.websocketHandler.ping())

    authRoutes(server)
    websocketRoutes(server)
    processingRoutes(server)
    servingRoutes(server)


def authRoutes(server: 'Server') -> None:
    """Setup the FastAPI auth routes."""
    app: FastAPI = server.app

    @app.get('/auth/login')
    async def login(request: Request) -> RedirectResponse:
        if (request.headers.get('x-forwarded-for')):
            clientIP = request.headers['x-forwarded-for']
        else:
            clientIP = request.client.host

        isHost = isHostIP(clientIP)
        return await server.musicAPI.login(isHost)

    @app.get('/auth/callback')
    async def callback(request: Request) -> RedirectResponse:
        SESSION_ID: Final = request.query_params.get('state')
        RESPONSE: Final = await server.musicAPI.callback(request, SESSION_ID)
        return RESPONSE

    @app.get('/auth/token')
    async def token(sessionID: str = Cookie(None)) -> JSONResponse:
        if (not sessionID):
            raise HTTPException(status_code=400, detail='No session ID provided.')
        return JSONResponse({
            'accessToken': server.sessionManager.getToken(sessionID),
            'provider': server.musicAPI.getProviderName(),
        })

    @app.get('/auth/logout')
    async def logout(sessionID: str = Cookie(None)) -> RedirectResponse:
        server.sessionManager.deleteSession(sessionID)
        return RedirectResponse(url='/')


def servingRoutes(server: 'Server') -> None:
    """Setup the FastAPI serving routes."""
    app: FastAPI = server.app

    # CAMERA
    @app.get('/capture')
    async def captureGet() -> JSONResponse:
        """
        This endpoint serves the camera capture.
        """
        data = None
        filePath = os.path.join(server.ROOT_DIR, 'data', 'captures', 'capture0.jpg')
        if (os.path.exists(filePath)):
            with open(filePath, 'rb') as labelFile:
                data = base64.b64encode(labelFile.read()).decode('utf-8')

        response = {
            'imageData': data,
        }
        return JSONResponse(content=response)

    # DATA
    @app.get('/isHost')
    async def clientIPGet(request: Request) -> JSONResponse:
        """
        This endpoint serves the client's own IP address back to them.
        This is useful to determine if the client is the host.
        """
        proxiedIP = request.headers.get('x-forwarded-for')
        return JSONResponse(content={ 'clientIP': proxiedIP, 'isHost': isHostIP(proxiedIP) })

    @app.get('/playlist')
    async def playlistIDGet(sessionID: str = Cookie(None)) -> JSONResponse:
        """
        This endpoint serves the playlist ID back to the client.
        """
        if (server.sessionManager.getHostPlaylistID() is not None):
            return JSONResponse(
                content={
                    'provider': server.musicAPI.getProviderName(),
                    'playlistID': server.sessionManager.getHostPlaylistID(),
                }
            )
        return JSONResponse(
            content={
                'provider': server.musicAPI.getProviderName(),
                'playlistID': server.musicAPI.getPlaylistByName(
                    sessionID, 'Virtual Turntable'
                )
            }
        )

    @app.get('/host')
    async def hostUserGet() -> JSONResponse:
        """
        This endpoint serves the host user's ID back to the client.
        """
        if (server.sessionManager.getHostUserID() is None):
            raise HTTPException(404, 'Host user not found')
        return JSONResponse(content={
            'hostUserID': server.sessionManager.getHostUserID(),
            'provider': server.musicAPI.getProviderName(),
        })


def processingRoutes(server: 'Server') -> None:
    """Setup the FastAPI processing routes."""
    app: FastAPI = server.app

    # CLIENT-DRIVEN IMAGE
    @app.post('/scan')
    async def scanPost(request: Request) -> JSONResponse:
        """
        This endpoint allows a client to send an image to the server for album detection.
        """
        # validate body content
        body = await request.body()
        if (not body):
            raise HTTPException(status_code=400, detail='No image data provided.')

        # save image
        IMAGE_PATH: Final = os.path.join(server.ROOT_DIR, 'data', 'upload.png')
        with open(IMAGE_PATH, 'wb') as file:
            file.write(body)

        return await server.predictAndPlayAlbum('upload.png')

    # CENTRE LABEL
    @app.post('/centreLabel')
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
        images, metadata = server.centreLabelhandler.findReleaseData(
            albumName, artistName, year, 'vinyl'
        )

        labelPath = os.path.join(server.ROOT_DIR, 'data', 'centreLabels', f'{albumID}.png')
        if (not os.path.exists(labelPath)):
            # if label not cached, attempt to find it

            # attempt to find a centre label
            foundCentreLabel = server.centreLabelhandler.serveCentreLabel(
                albumID, images=images
            )
            if (foundCentreLabel is None):
                # re-attmpt with broader search
                foundCentreLabel = server.centreLabelhandler.serveCentreLabel(
                    albumID, albumName, None, None, None
                )

            if (not foundCentreLabel or not os.path.exists(labelPath)):
                # failed to find a centre label
                labelData = None
            else:
                with open(labelPath, 'rb') as labelFile:
                    labelData = base64.b64encode(labelFile.read()).decode('utf-8')
        else:
            # load cached label
            with open(labelPath, 'rb') as labelFile:
                labelData = base64.b64encode(labelFile.read()).decode('utf-8')

        response = {
            'imageData': labelData,
        }
        if (metadata):
            response['metadata'] = metadata

        return JSONResponse(content=response)


def websocketRoutes(server: 'Server') -> None:
    """Setup the FastAPI websocket routes."""
    app: FastAPI = server.app

    @app.websocket('/ws')
    async def connectMainWebsocket(websocket: WebSocket, sessionID: str = Cookie(None)) -> None:
        if (not sessionID):
            await websocket.close(code=4001)
            return
        session = server.sessionManager.getSession(sessionID)
        if (not session):
            await websocket.close(code=4001)
            return
        await server.websocketHandler.handleConnection(
            websocket, sessionID=sessionID, isMain=session.get('isHost', False)
        )
