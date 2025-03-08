"""This file contains the StateManager class, which is responsible for managing the state of the application."""

from typing import Any

from app.enums.StateKeys import Commands, StateKeys
from app.modules.Hardware.piController import PiController
from app.modules.websocketHandler import WebsocketHandler
from app.modules.Hardware.IHardwareController import IHardwareController


class StateManager:
    """
    StateManager class is responsible for managing the state of the application.
    Utilises an observer paattern to notify clients of state changes, allowing real-time reactivity.
    Uses a dictionary to store the state of the application.
    """

    def __init__(self,
        websocketHandler: WebsocketHandler,
        hardwareController: IHardwareController | None,
        provider: str | None,
    ) -> None:
        """Initialise the StateManager class."""
        self.__state: dict[str, bool | dict[str, bool | int]] = {
            'playState': False,
            'settings': {
                'enableMotor': True,
                'enableRemote': True,
                'enforceSignature': True,
                'volume': 50,
            },
        }
        self.websocketHandler = websocketHandler
        self.hardwareController = hardwareController
        self.provider = provider

    def getState(self) -> dict[str, bool | dict[str, bool | int]]:
        """Return the current state of the application."""
        return self.__state

    async def updateState(self, key: StateKeys, value: Any) -> None:
        """TODO"""
        if (self.__state.get(key.value) == value):
            # non-update, can be ignored
            return
        self.__state[key.value] = value

        # react to state change
        # manage hardware broadcasts
        if (self.hardwareController is not None):
            if (key == StateKeys.SETTINGS):
                if (value.get('enableMotor', False)):
                    self.hardwareController.setMotorSpeed(100)
                else:
                    self.hardwareController.setMotorSpeed(0)

            if (key == StateKeys.PLAY_STATE):
                self.hardwareController.setMotorState(1 if value else 0)
            elif (key == Commands.FAST_FORWARD):
                self.hardwareController.setMotorState(1)
            elif (key == Commands.REWIND):
                self.hardwareController.setMotorState(-1)

        # manage software broadcasts
        if (key in [StateKeys.PLAY_STATE, StateKeys.CURRENT_TRACK, StateKeys.SETTINGS]):
            await self.websocketHandler.broadcast(
                {'command': key.value, 'value': value, 'provider': self.provider }
            )

    def resetState(self) -> None:
        """Reset the state of the application."""
        self.__state = {
            'playState': False,
            'settings': {
                'enableMotor': True,
                'enableRemote': True,
                'enforceSignature': True,
                'volume': 50,
            },
        }
        if (self.hardwareController is not None):
            self.hardwareController.setMotorSpeed(0)
            self.hardwareController.setMotorState(0)
