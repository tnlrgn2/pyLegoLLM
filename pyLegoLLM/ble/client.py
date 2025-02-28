# pyLegoLLM/ble/client.py

import asyncio
from bleak import BleakClient

class LegoClient:
    """
    A class to manage the BLE connection and communication with the LEGO hub.
    """
    def __init__(self, address: str):
        self.address = address
        self.client = BleakClient(address)
        self.connected = False

    async def connect(self) -> bool:
        try:
            await self.client.connect()
            self.connected = True
            print(f"Connected to LEGO hub at {self.address}")
            return True
        except Exception as e:
            print(f"Failed to connect to LEGO hub: {e}")
            return False

    async def disconnect(self):
        if self.connected:
            await self.client.disconnect()
            self.connected = False
            print(f"Disconnected from LEGO hub at {self.address}")

    async def write_gatt_char(self, char_uuid, data):
        """
        Delegates the write_gatt_char call to the underlying BleakClient instance.
        """
        return await self.client.write_gatt_char(char_uuid, data)

    async def start_notify(self, char_uuid, callback):
        """
        Delegates the start_notify call to the underlying BleakClient instance.
        """
        return await self.client.start_notify(char_uuid, callback)

    async def stop_notify(self, char_uuid):
        """
        Delegates the stop_notify call to the underlying BleakClient instance.
        """
        return await self.client.stop_notify(char_uuid)
