import asyncio
from bleak import BleakScanner, BleakClient

async def list_gatt_services(address):
    async with BleakClient(address) as client:
        if client.is_connected:
            print(f"Connected to device: {address}")
            services = await client.get_services()
            print("Discovered GATT Services and Characteristics:")
            for service in services:
                print(f"\nService: {service.uuid} ({service.description})")
                for char in service.characteristics:
                    props = ", ".join(char.properties)
                    print(f"  Characteristic: {char.uuid} ({char.description}) [Properties: {props}]")
        else:
            print("Failed to connect to the device.")

async def main():
    print("Scanning for LEGO WeDo 2.0 Hub...")
    devices = await BleakScanner.discover()
    wedo_address = None

    # Look for a device with "WeDo" or "LPF2" in its name.
    for device in devices:
        if device.name and ("WeDo" in device.name or "LPF2" in device.name):
            wedo_address = device.address
            print(f"Found device: {device.name} at {device.address}")
            break

    if wedo_address is None:
        print("No LEGO WeDo 2.0 Hub found.")
        return

    await list_gatt_services(wedo_address)

if __name__ == "__main__":
    asyncio.run(main())
