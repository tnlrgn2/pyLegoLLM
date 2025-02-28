# pyLegoLLM/ble/__init__.py

"""
pyLegoLLM.ble - A package for handling Bluetooth Low Energy (BLE) communication with LEGO devices.
Provides functionality for scanning, connecting, and interacting with LEGO BLE devices.
"""

from .scanner import LegoScanner
from .client import LegoClient
from .utils import (
    UUIDHelper,
    CHARACTERISTIC_OUTPUT_COMMAND_UUID,
    CHARACTERISTIC_INPUT_COMMAND_UUID,
    CHARACTERISTIC_PORT_TYPE_UUID,
    SENSOR_VALUE_CHARACTERISTIC_UUID,
    motor_port,
    port_devices
)
