"""Hardware controller for Raspberry Pi."""
import asyncio
import time
from typing import Awaitable, Callable, Optional

import cv2
import lgpio

from app.modules.Hardware.IHardwareController import IHardwareController


class PiController(IHardwareController):
    """Hardware controller for Raspberry Pi."""

    def __init__(self,
        onMotorStall: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:

        self.onMotorStall = onMotorStall

        # DEFINE CONTROL PINS
        # (numbers are GPIO value, not pin number)

        # motor
        self.MTR_FWD = 23
        self.MTR_REV = 24
        self.MTR_PWM = 12  # must be PWM-capable pin (18 seems to have fried)
        # motor includes a rotary encoder component
        self.MTR_ENC_A = 17
        self.MTR_ENC_B = 27

        # rotary encoder 2
        self.ENC_DT = 6
        self.ENC_CLK = 5
        self.ENC_SW = 13

        # hinge switch
        self.HNG = 16

        # button
        self.BTN = 26

        # CONFIGURE PIN OUTPUTS
        # open the gpio chip and set the pins as output
        self.h = lgpio.gpiochip_open(0)

        lgpio.gpio_claim_output(self.h, self.MTR_FWD)
        lgpio.gpio_claim_output(self.h, self.MTR_REV)
        lgpio.gpio_claim_output(self.h, self.MTR_PWM)
        self.setMotorSpeed(100)

        lgpio.gpio_claim_output(self.h, self.ENC_SW, lgpio.SET_PULL_UP)  # pull-up enabled

        lgpio.gpio_claim_output(self.h, self.HNG, lgpio.SET_PULL_UP)  # pull-up enabled
        lgpio.gpio_claim_output(self.h, self.BTN, lgpio.SET_PULL_UP)  # pull-up enabled

    def __del__(self) -> None:
        """Clean up GPIO pins."""
        # set to 'stable' state
        lgpio.gpio_write(self.h, self.MTR_FWD, 0)
        lgpio.gpio_write(self.h, self.MTR_REV, 0)
        self.setMotorSpeed(0)

        lgpio.gpiochip_close(self.h)
        # print('Cleaned up')

    # MOTOR
    def setMotorState(self, direction: int) -> None:
        """Set the motor direction (1 for forward, -1 for reverse, 0 for stop)."""
        if (direction == 0):
            lgpio.gpio_write(self.h, self.MTR_FWD, 0)
            lgpio.gpio_write(self.h, self.MTR_REV, 0)
        else:
            if (direction > 0):
                lgpio.gpio_write(self.h, self.MTR_FWD, 1)
                lgpio.gpio_write(self.h, self.MTR_REV, 0)
            elif (direction < 0):
                lgpio.gpio_write(self.h, self.MTR_FWD, 0)
                lgpio.gpio_write(self.h, self.MTR_REV, 1)

            asyncio.create_task(self.reactToEncoderStall())

    def setMotorSpeed(self, speed: int) -> None:
        """Set motor speed (% duty cycle)."""
        speed = min(100, speed)  # clamp
        frequency = 1000  # 1 kHz PWM frequency

        if (speed > 0):
            lgpio.tx_pwm(self.h, self.MTR_PWM, frequency, speed)  # start PWM
            asyncio.create_task(self.reactToEncoderStall())
        else:
            lgpio.tx_pwm(self.h, self.MTR_PWM, frequency, 0)  # start PWM

    # ENCODER
    def getIsEncoderButtonDown(self) -> bool:
        """Returns True if the button is pressed, False if open."""
        # LOW means closed, since GPIO has internal pull-up
        return bool(lgpio.gpio_read(self.h, self.ENC_SW) == 0)

    async def reactToEncoder(self,
        onFreeRotate: Optional[Callable[[int], Awaitable[None]]] = None,
        onDownRotate: Optional[Callable[[int], Awaitable[None]]] = None,
        onDownOnly: Optional[Callable[[], Awaitable[None]]] = None
    ) -> None:
        """React to rotary encoder input events."""
        print('Listening to encoder on GPIOs', self.ENC_CLK, self.ENC_DT, self.ENC_SW)
        lastState = lgpio.gpio_read(self.h, self.ENC_CLK)
        buttonWasDown = self.getIsEncoderButtonDown()

        ignoreUntilButtonUp = False

        while True:
            clkState = lgpio.gpio_read(self.h, self.ENC_CLK)
            dtState = lgpio.gpio_read(self.h, self.ENC_DT)
            buttonDown = self.getIsEncoderButtonDown()

            if (not buttonDown):
                ignoreUntilButtonUp = False

            # react to rotation
            if (clkState != lastState):  # rotation detected
                if (dtState == clkState):
                    # clockwise
                    if (buttonDown):
                        if (not ignoreUntilButtonUp):
                            ignoreUntilButtonUp = True
                            if (onDownRotate):
                                await onDownRotate(1)
                    else:
                        if (onFreeRotate):
                            await onFreeRotate(1)
                else:
                    # anticlockwise
                    if (buttonDown):
                        if (not ignoreUntilButtonUp):
                            ignoreUntilButtonUp = True
                            if (onDownRotate):
                                await onDownRotate(-1)
                    else:
                        if (onFreeRotate):
                            await onFreeRotate(-1)

            # react to button-only
            if (buttonDown and not buttonWasDown):
                await asyncio.sleep(0.1)  # debounce
                if (self.getIsEncoderButtonDown()):  # ensure button still down
                    await asyncio.sleep(0.4)  # ensure short-pulse only
                    if (not self.getIsEncoderButtonDown()):
                        # button is not still held- short pulse
                        if (onDownOnly):
                            await onDownOnly()

            buttonWasDown = buttonDown
            lastState = clkState
            await asyncio.sleep(0.01)  # small delay to avoid CPU overload

    async def reactToEncoderStall(self) -> None:
        """React to motor stall events."""
        if (self.onMotorStall is None):
            return

        lastState = lgpio.gpio_read(self.h, self.MTR_ENC_A)
        lastTime = time.time()
        while True:
            clkState = lgpio.gpio_read(self.h, self.MTR_ENC_A)
            if (clkState != lastState):
                lastTime = time.time()

            if (time.time() - lastTime > 1):
                await self.onMotorStall()
                return

            lastState = clkState
            await asyncio.sleep(0.1)

    # HINGE
    def getIsHingeClosed(self) -> bool:
        """Returns True if the hinge is closed, False if open."""
        # LOW means closed, since GPIO has internal pull-up
        return bool(lgpio.gpio_read(self.h, self.HNG) == 0)

    async def reactToHinge(self,
        onClosed: Optional[Callable[[], Awaitable[None]]] = None,
        onOpen: Optional[Callable[[], Awaitable[None]]] = None
    ) -> None:
        """React to hinge state changes."""
        print('Listening to switch on GPIO', self.HNG)
        hingeWasClosed = self.getIsHingeClosed()

        while True:
            if (self.getIsHingeClosed()):
                if (not hingeWasClosed):
                    if (onClosed is not None):
                        await onClosed()
                    hingeWasClosed = True
            else:
                if (hingeWasClosed):
                    if (onOpen is not None):
                        await onOpen()
                    hingeWasClosed = False
            await asyncio.sleep(0.2)  # small delay to avoid CPU overload

    # BUTTON
    def getIsButtonDown(self) -> bool:
        """Returns True if the button is pressed, False if open."""
        # LOW means closed, since GPIO has internal pull-up
        return bool(lgpio.gpio_read(self.h, self.BTN) == 0)

    async def reactToButton(self,
        onDown: Optional[Callable[[], Awaitable[None]]] = None,
        onUp: Optional[Callable[[], Awaitable[None]]] = None
    ) -> None:
        """React to button press/release events."""
        print('Listening to button on GPIO', self.BTN)
        buttonWasDown = self.getIsButtonDown()

        while (True):
            if (self.getIsButtonDown()):
                if (not buttonWasDown):
                    if (onDown is not None):
                        await onDown()
                    buttonWasDown = True
            else:
                if (buttonWasDown):
                    if (onUp is not None):
                        await onUp()
                    buttonWasDown = False
            await asyncio.sleep(0.01) # small delay to avoid CPU overload

    # CAMERA
    def takePhotos(self, maxCameras: int = 1) -> list[cv2.typing.MatLike]:
        """Captures an image from each connected camera and returns them as an array."""
        photos = []
        for i in range(maxCameras):
            cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
            if (not cap.isOpened()):
                cap.release()
                continue
            ret, frame = cap.read()
            cap.release()
            if (not ret):
                print(f'Error: Failed to capture image from camera {i}')
                continue
            photos.append(frame)
        return photos
