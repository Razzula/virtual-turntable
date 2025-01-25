"""Handler class for WebSocket connections."""
from typing import List, Optional

from fastapi import WebSocket, HTTPException
from fastapi.websockets import WebSocketState

class WebsocketHandler:
    """Handler class for WebSocket connections."""

    def __init__(self) -> None:
        """Initialise the WebSocket handler."""
        self.currentWebsockets: List[WebSocket] = []

    async def handleConnectionRequest(self, websocket: WebSocket) -> None:
        """Handle a WebSocket connection request."""

        self.currentWebsockets.append(websocket)
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
            self.currentWebsockets.remove(websocket)
            print('Client disconnected.')

    async def sendToClient(self, data: dict[str, str], authToken: Optional[str] = None) -> None:
        """Send a message to the client."""

        for websocket in self.currentWebsockets:
            if (authToken):
                data['token'] = authToken
            await websocket.send_json(data)

    async def ping(self) -> dict[str, str]:
        """DEV! This endpoint triggers a ping event to the client, from the server."""
        if (len(self.currentWebsockets) == 0):
            raise HTTPException(status_code=400, detail='No client connected.')

        await self.sendToClient({'message': 'ping'})
        return {'message': 'ping'}
