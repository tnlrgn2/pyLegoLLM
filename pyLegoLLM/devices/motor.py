# pyLegoLLM/devices/motor.py

import asyncio
from pyLegoLLM.ble.utils import CHARACTERISTIC_INPUT_COMMAND_UUID, CHARACTERISTIC_OUTPUT_COMMAND_UUID

class Motor:
    """
    Represents a LEGO motor. Once initialized by the Manager upon detection,
    commands can be sent to control the motor.
    """
    def __init__(self, client, port: int, connected_device: int = 1, mode: int = 0x02, value_format: int = 0x00):
        """
        Initializes the Motor instance with the BLE client and port parameters.
        """
        self.client = client
        self.port = port
        self.connected_device = connected_device
        self.mode = mode
        self.value_format = value_format

    async def initialize(self):
        """
        Sends an 11-byte handshake command to initialize the motor port.
        Command: [0x01, 0x02, port, connected_device, mode, 0x01, 0x00, 0x00, 0x00, value_format, 0x01]
        """
        command = bytearray([
            0x01, 0x02,
            self.port,
            self.connected_device,
            self.mode,
            0x01, 0x00, 0x00, 0x00,
            self.value_format,
            0x01
        ])
        print(f"Initializing motor port {self.port} with command: {list(command)}")
        await self.client.write_gatt_char(CHARACTERISTIC_INPUT_COMMAND_UUID, command)
        print("Motor port initialized.")

    @staticmethod
    def calculate_motor_power(power: int) -> int:
        """
        For a WeDo 2.0 motor command:
          - For positive speeds, send the percentage (1–100).
          - For negative speeds, send (256 + power) (e.g. -50 becomes 206).
          - 0 stops the motor.
        """
        if power > 0:
            return power
        elif power < 0:
            return 256 + power
        else:
            return 0

    @staticmethod
    def write_motor_power_command(motor_value: int, port: int) -> bytearray:
        """
        Constructs a 4-byte motor command.
        For a WeDo 2.0 motor, the expected command is:
          [port, 0x01, 0x01, motor_value]
        """
        return bytearray([port, 0x01, 0x01, motor_value])

    async def send_command(self, power: int):
        """
        Sends a motor command to control the motor power.
        """
        motor_value = self.calculate_motor_power(power)
        command = self.write_motor_power_command(motor_value, self.port)
        await self.client.write_gatt_char(CHARACTERISTIC_OUTPUT_COMMAND_UUID, command)
        print(f"Motor command sent: port={self.port}, desired power={power} mapped to {motor_value}")
