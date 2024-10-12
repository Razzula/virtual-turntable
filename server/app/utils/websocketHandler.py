"""Handler class for WebSocket connections."""
from typing import Optional

from fastapi import WebSocket, HTTPException
from fastapi.websockets import WebSocketState

class WebsocketHandler:
    """Handler class for WebSocket connections."""

    def __init__(self) -> None:
        """Initialise the WebSocket handler."""
        self.currentWebsocket: Optional[WebSocket] = None

    async def handleConnectionRequest(self, websocket: WebSocket) -> None:
        """Handle a WebSocket connection request."""

        if (self.currentWebsocket is not None):
            raise HTTPException(status_code=400, detail='Another client is already connected.')

        self.currentWebsocket = websocket
        await websocket.accept()
        print('Client connected.')

        try:
            while (websocket.client_state != WebSocketState.DISCONNECTED):
                request = await websocket.receive_text()
                print(request)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            try:
                await websocket.close()
            except Exception as e:
                pass # connection is already closed
            self.currentWebsocket = None
            print('Client disconnected.')

    async def sendToClient(self, data: dict[str, str], authToken: Optional[str] = None) -> None:
        """Send a message to the client."""

        if (self.currentWebsocket is None):
            print('No client connected.')
            return

        if (authToken):
            data['token'] = authToken

        await self.currentWebsocket.send_json(data)

    async def ping(self) -> dict[str, str]:
        """DEV! This endpoint triggers a ping event to the client, from the server."""
        if (self.currentWebsocket is None):
            raise HTTPException(status_code=400, detail='No client connected.')

        await self.sendToClient({'message': 'ping'})
        return {'message': 'ping'}
