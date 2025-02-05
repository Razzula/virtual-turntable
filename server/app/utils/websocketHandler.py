"""Handler class for WebSocket connections."""
import json
from typing import Any, List, Optional

from fastapi import WebSocket, HTTPException
from fastapi.websockets import WebSocketState
from app.enums.StateKeys import StateKeys

class WebsocketHandler:
    """Handler class for WebSocket connections."""

    def __init__(self, getState: Any, handleCommand: Any) -> None:
        """Initialise the WebSocket handler."""
        self.activeMainSocket: Optional[WebSocket] = None
        self.activeSideSockets: List[WebSocket] = []

        self.getState = getState
        self.handleCommand = handleCommand

    async def handleConnection(self, websocket: WebSocket, sessionID: str, isMain: bool) -> None:
        """Handle a WebSocket connection request."""

        if (isMain):
            # override existing connections
            self.activeMainSocket = websocket
        else:
            self.activeSideSockets.append(websocket)
        await websocket.accept()
        print(f'Client connected. ({sessionID})')

        # initial information batch
        currentState = self.getState()
        if (currentState):
            for key, value in currentState.items():
                await websocket.send_text(json.dumps({'command': key, 'value': value}))

        try:
            # monitor the connection
            while (websocket.client_state != WebSocketState.DISCONNECTED):
                request = await websocket.receive_text()
                # if (isMain):
                    # cache data

                data = json.loads(request)
                command = data.get('command')
                if (command is not None):
                    print(f'{websocket.client} [{"HOST" if isMain else "SIDE"}]:', command)
                    await self.handleCommand(sessionID, command, data.get('value')) 
                else:
                    print(print(f'{websocket.client} [{"HOST" if isMain else "SIDE"}]:', request))
                    
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
    
    async def sendToHost(self, data: dict[str, str]) -> None:
        """Send a message to the host client."""
        # send to main socket
        if (self.activeMainSocket is not None):
            await self.activeMainSocket.send_json(data)
    
    async def sentToClients(self, data: dict[str, str]) -> None:
        """Send a message to the other clients."""
        # broadcast to side sockets
        for websocket in self.activeSideSockets:
            await websocket.send_json(data)

    async def broadcast(self, data: dict[str, str]) -> None:
        """Send a message to the all connected clients."""
        await self.sendToHost(data)
        await self.sentToClients(data)
        print('Broadcast', data.get('command'))

    async def ping(self) -> dict[str, str]:
        """DEV! This endpoint triggers a ping event to the client, from the server."""
        if (len(self.activeSideSockets) == 0):
            raise HTTPException(status_code=400, detail='No client connected.')

        await self.broadcast({'message': 'ping'})
        return {'message': 'ping'}
