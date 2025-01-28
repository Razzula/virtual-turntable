"""Handler class for WebSocket connections."""
import json
from typing import List, Optional

from fastapi import WebSocket, HTTPException
from fastapi.websockets import WebSocketState

class WebsocketHandler:
    """Handler class for WebSocket connections."""

    def __init__(self) -> None:
        """Initialise the WebSocket handler."""
        self.activeMainSocket: Optional[WebSocket] = None
        self.activeSideSockets: List[WebSocket] = []
        self.cache = {}

    async def handleConnectionRequest(self, websocket: WebSocket, isMain: bool) -> None:
        """Handle a WebSocket connection request."""

        if (isMain):
            # if (self.activeMainSocket is not None):
            #     # reject connection
            #     await websocket.close(code=123, reason='Another main socket is already connected.')
            #     return
            self.activeMainSocket = websocket
        else:
            self.activeSideSockets.append(websocket)
        await websocket.accept()
        print('Client connected.')

        # initial information batch
        for key, value in self.cache.items():
            await websocket.send_text(json.dumps({'command': key, 'value': value}))

        try:
            # monitor the connection
            while (websocket.client_state != WebSocketState.DISCONNECTED):
                request = await websocket.receive_text()
                print(f'{websocket.client}, (main={isMain}):', request)
                if (isMain):
                    # cache data
                    try:
                        data = json.loads(request)
                        self.cache[data['command']] = data['value']
                    except Exception:
                        data = request

                    # forward main messages to all side sockets
                    for sideSocket in self.activeSideSockets:
                        await sideSocket.send_text(request)
                else:
                    # redirect side messages to main socket
                    if (self.activeMainSocket is not None):
                        await self.activeMainSocket.send_text(request)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            try:
                await websocket.close()
            except Exception as e:
                pass # connection is already closed

            # cleanup
            if (isMain):
                self.activeMainSocket = None
            else:
                self.activeSideSockets.remove(websocket)
            print('Client disconnected.')

    async def sendToClient(self, data: dict[str, str], authToken: Optional[str] = None) -> None:
        """Send a message to the client."""

        for websocket in self.activeSideSockets:
            if (authToken):
                data['token'] = authToken
            await websocket.send_json(data)

    async def ping(self) -> dict[str, str]:
        """DEV! This endpoint triggers a ping event to the client, from the server."""
        if (len(self.activeSideSockets) == 0):
            raise HTTPException(status_code=400, detail='No client connected.')

        await self.sendToClient({'message': 'ping'})
        return {'message': 'ping'}
