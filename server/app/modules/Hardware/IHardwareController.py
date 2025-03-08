"""Interface for hardware control."""
from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Optional

import cv2


class IHardwareController(ABC):
    """Interface for hardware control."""

    @abstractmethod
    def setMotorState(self, direction: int) -> None:
        """Set the motor direction (1 for forward, -1 for reverse, 0 for stop)."""
        raise NotImplementedError

    @abstractmethod
    def setMotorSpeed(self, speed: int) -> None:
        """Set motor speed (% duty cycle)."""
        raise NotImplementedError

    @abstractmethod
    def getIsEncoderButtonDown(self) -> bool:
        """Returns True if the rotary encoder button is pressed, False if open."""
        raise NotImplementedError

    @abstractmethod
    async def reactToEncoder(
        self,
        onFreeRotate: Optional[Callable[[int], Awaitable[None]]] = None,
        onDownRotate: Optional[Callable[[int], Awaitable[None]]] = None,
        onDownOnly: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        """React to rotary encoder input events."""
        raise NotImplementedError

    @abstractmethod
    def getIsHingeClosed(self) -> bool:
        """Returns True if the hinge is closed, False if open."""
        raise NotImplementedError

    @abstractmethod
    async def reactToHinge(
        self,
        onClosed: Optional[Callable[[], Awaitable[None]]] = None,
        onOpen: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        """React to hinge state changes."""
        raise NotImplementedError

    @abstractmethod
    def getIsButtonDown(self) -> bool:
        """Returns True if the button is pressed, False if open."""
        raise NotImplementedError

    @abstractmethod
    async def reactToButton(
        self,
        onDown: Optional[Callable[[], Awaitable[None]]] = None,
        onUp: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        """React to button press/release events."""
        raise NotImplementedError

    @abstractmethod
    def takePhotos(self, maxCameras: int = 1) -> list[cv2.typing.MatLike]:
        """Capture images from connected cameras and return them as a list."""
        raise NotImplementedError
