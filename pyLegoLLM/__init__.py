# pyLegoLLM/__init__.py

"""
pyLegoLLM - A Python package to control LEGO bricks via BLE.
Version: 0.1.0
"""

__version__ = "0.1.0"

# Expose BLE-related functionality
from .ble import (
    LegoScanner,
    LegoClient,
    UUIDHelper,
    CHARACTERISTIC_OUTPUT_COMMAND_UUID,
    CHARACTERISTIC_INPUT_COMMAND_UUID,
    CHARACTERISTIC_PORT_TYPE_UUID,
    SENSOR_VALUE_CHARACTERISTIC_UUID,
    motor_port,
    port_devices
)

#from .devices import *

# Expose the manager and exceptions if implemented
from .manager import *
#from .exceptions import *
