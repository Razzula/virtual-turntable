import time
import lgpio

class PiController:
    """TODO"""
    
    def __init__(self) -> None:
        # numbers are GPIO value (not pin number)
        self.MOTOR = 17

        # open the gpio chip and set the LED pin as output
        self.h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(self.h, self.MOTOR)
        # print('Setup')
    
    def __del__(self) -> None:
        # set to 'stable' state
        lgpio.gpio_write(self.h, self.MOTOR, 0)

        lgpio.gpiochip_close(self.h)
        # print('Cleaned up')
    
    def setMotorState(self, on: bool) -> None:
        onBinary = 1 if on else 0
        lgpio.gpio_write(self.h, self.MOTOR, onBinary)
