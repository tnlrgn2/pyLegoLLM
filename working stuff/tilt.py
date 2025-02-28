# pyLegoLLM/devices/tilt.py

import asyncio
from pyLegoLLM.ble.utils import CHARACTERISTIC_INPUT_COMMAND_UUID

async def initialize_tilt_sensor_port(client, port: int):
    """
    Initializes a tilt sensor on the given port.
    
    Command:
      [0x01, 0x02, port, 34, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01]
    The value '34' designates the device type for a tilt sensor.
    """
    command = bytearray([0x01, 0x02, port, 34, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01])
    print(f"Initializing tilt sensor on port {port} with command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_INPUT_COMMAND_UUID, command)
    print(f"Tilt sensor initialized on port {port}")
