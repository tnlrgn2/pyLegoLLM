# pyLegoLLM/ble/scanner.py

import asyncio
from bleak import BleakScanner

class LegoScanner:
    """
    A class to handle scanning and discovering LEGO WeDo 2.0 Hubs.
    """

    async def discover_hub(self) -> str:
        """
        Scans for the LEGO WeDo 2.0 Hub using BLE.
        Returns the hub's address if found; otherwise, returns None.
        """
        print("Scanning for LEGO WeDo 2.0 Hub...")
        print("You can now power on the lego...")
        devices = await BleakScanner.discover()
        for device in devices:
            if device.name and ("WeDo" in device.name or "LPF2" in device.name):
                print(f"Found device: {device.name} at {device.address}")
                return device.address
        print("No LEGO WeDo 2.0 Hub found.")
        return None
