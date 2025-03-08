"""Test suite for the StateManager class."""
import unittest
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

from app.enums.StateKeys import StateKeys
from app.modules.stateManager import StateManager


class TestStateManager(unittest.IsolatedAsyncioTestCase):
    """Test suite for the StateManager class."""

    def setUp(self) -> None:
        """Set up test dependencies before each test."""
        self.websocketHandler: MagicMock = MagicMock()
        self.websocketHandler.broadcast = AsyncMock()
        self.hardwareController: MagicMock = MagicMock()
        self.stateManager: StateManager = StateManager(
            self.websocketHandler, self.hardwareController, 'test',
        )

    async def testGetStateInitial(self) -> None:
        """Test that the initial state is correctly set."""
        state: Dict[str, Any] = self.stateManager.getState()
        self.assertFalse(state['playState'])
        self.assertIn('settings', state)

    async def testUpdateStateValue(self) -> None:
        """Test updating the play state updates the state and triggers hardware and broadcast."""
        await self.stateManager.updateState(StateKeys.PLAY_STATE, True)

        self.assertTrue(self.stateManager.getState()[StateKeys.PLAY_STATE.value])

    async def testUpdateStateBroadcasts(self) -> None:
        """Test updating the settings triggers hardware and broadcast."""
        newSettings: Dict[str, Any] = {'enableMotor': True}
        await self.stateManager.updateState(StateKeys.SETTINGS, newSettings)

        self.hardwareController.setMotorSpeed.assert_called_with(100)
        self.websocketHandler.broadcast.assert_awaited_with({
            'command': StateKeys.SETTINGS.value,
            'value': newSettings,
            'provider': 'test',
        })

    async def testResetState(self) -> None:
        """Test resetting the state to default values."""
        await self.stateManager.updateState(StateKeys.PLAY_STATE, True)
        # reset the broadcast call history so we only catch calls from resetState
        self.websocketHandler.broadcast.reset_mock()

        self.stateManager.resetState()
        self.assertFalse(self.stateManager.getState()['playState'])
        self.hardwareController.setMotorSpeed.assert_called_with(0)
        self.hardwareController.setMotorState.assert_called_with(0)
        # resetState doesn't trigger a broadcast
        self.websocketHandler.broadcast.assert_not_called()


if __name__ == '__main__':
    unittest.main()
