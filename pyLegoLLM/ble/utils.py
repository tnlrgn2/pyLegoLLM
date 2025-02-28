# pyLegoLLM/ble/utils.py

class UUIDHelper:
    UUID_CUSTOM_BASE = "1212-EFDE-1523-785FEABCD123"
    UUID_STANDARD_BASE = "0000-1000-8000-00805f9b34fb"

    @staticmethod
    def add_leading_zeroes(prefix: str) -> str:
        """
        Removes the '0x' prefix (if present) and pads the value to ensure 8 digits.
        """
        if prefix.startswith("0x"):
            prefix = prefix[2:]
        return ("00000000" + prefix)[-8:]

    @staticmethod
    def uuid_with_prefix_custom_base(prefix: str) -> str:
        """
        Constructs a full UUID using the custom base.
        """
        padding = UUIDHelper.add_leading_zeroes(prefix)
        return f"{padding}-{UUIDHelper.UUID_CUSTOM_BASE.lower()}"

# Characteristic UUIDs for various commands
CHARACTERISTIC_OUTPUT_COMMAND_UUID = UUIDHelper.uuid_with_prefix_custom_base("0x1565")
CHARACTERISTIC_INPUT_COMMAND_UUID = UUIDHelper.uuid_with_prefix_custom_base("0x1563")
CHARACTERISTIC_PORT_TYPE_UUID = "00001527-1212-efde-1523-785feabcd123"
SENSOR_VALUE_CHARACTERISTIC_UUID = UUIDHelper.uuid_with_prefix_custom_base("0x1560")

# Global variables for device management (if needed in the future)
motor_port = None
port_devices = {}
