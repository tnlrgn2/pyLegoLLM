# pyLegoLLM/devices/led.py

import asyncio
from pyLegoLLM.ble.utils import CHARACTERISTIC_OUTPUT_COMMAND_UUID

class LED:
    """
    Represents a static LED device. Provides methods to set color, blink, or run in disco mode.
    """
    
    # Predefined main 8 colors (can be adjusted as needed)
    PREDEFINED_COLORS = {
        'red': (255, 0, 0),
        'green': (0, 255, 0),
        'blue': (0, 0, 255),
        'yellow': (255, 255, 0),
        'cyan': (0, 255, 255),
        'magenta': (255, 0, 255),
        'white': (255, 255, 255),
        'black': (0, 0, 0)
    }

    def __init__(self, client):
        """
        Initializes the LED with the given BLE client.
        """
        self.client = client
        self._mode_task = None

    async def _send_led_color(self, red: int, green: int, blue: int):
        """
        Sends an LED command in the format: [0x06, 0x04, 0x03, R, G, B]
        """
        command = bytearray([0x06, 0x04, 0x03, red, green, blue])
        print(f"Sending LED color command: {list(command)}")
        await self.client.write_gatt_char(CHARACTERISTIC_OUTPUT_COMMAND_UUID, command)
        print(f"LED color command sent: R={red}, G={green}, B={blue}")

    async def set_color_rgb(self, red: int, green: int, blue: int):
        """
        Sets the LED color using RGB values.
        Cancels any running mode (blink/disco) before setting the color.
        """
        self.stop_mode()
        await self._send_led_color(red, green, blue)

    async def set_color(self, color: str):
        """
        Sets the LED to one of the predefined colors.
        """
        self.stop_mode()
        color_lower = color.lower()
        if color_lower not in self.PREDEFINED_COLORS:
            print(f"Color '{color}' not defined. Available colors: {list(self.PREDEFINED_COLORS.keys())}")
            return
        red, green, blue = self.PREDEFINED_COLORS[color_lower]
        await self._send_led_color(red, green, blue)

    async def blink(self, color: str, duration: float):
        """
        Blinks the LED with the specified color for 'duration' seconds,
        then leaves the LED in the specified color.
        """
        self.stop_mode()
        color_lower = color.lower()
        if color_lower not in self.PREDEFINED_COLORS:
            print(f"Color '{color}' not defined. Available colors: {list(self.PREDEFINED_COLORS.keys())}")
            return

        red, green, blue = self.PREDEFINED_COLORS[color_lower]

        async def blink_task():
            end_time = asyncio.get_event_loop().time() + duration
            toggle = True
            while asyncio.get_event_loop().time() < end_time:
                if toggle:
                    await self._send_led_color(red, green, blue)
                else:
                    await self._send_led_color(0, 0, 0)  # turn off
                toggle = not toggle
                await asyncio.sleep(0.5)
            # After blinking, leave the LED on with the specified color.
            await self._send_led_color(red, green, blue)

        self._mode_task = asyncio.create_task(blink_task())
        await self._mode_task

    async def disco(self):
        """
        Puts the LED into disco mode: cycles through a set of colors every 2 seconds indefinitely.
        This mode will run until another command (which cancels the running mode) is issued.
        """
        self.stop_mode()

        async def disco_task():
            colors = [
                (0, 0, 255),    # Blue
                (255, 0, 0),    # Red
                (0, 255, 0),    # Green
                (128, 0, 128)   # Purple
            ]
            index = 0
            while True:
                red, green, blue = colors[index % len(colors)]
                print(f"Disco mode: Setting LED color to R={red}, G={green}, B={blue}")
                await self._send_led_color(red, green, blue)
                await asyncio.sleep(2)
                index += 1

        self._mode_task = asyncio.create_task(disco_task())

    def stop_mode(self):
        """
        Cancels any running blink or disco mode.
        """
        if self._mode_task is not None:
            self._mode_task.cancel()
            self._mode_task = None
