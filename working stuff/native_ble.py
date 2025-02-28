import asyncio
from bleak import BleakScanner, BleakClient

# --- Custom UUID Helpers ---

UUID_CUSTOM_BASE = "1212-EFDE-1523-785FEABCD123"
UUID_STANDARD_BASE = "0000-1000-8000-00805f9b34fb"

def add_leading_zeroes(prefix: str) -> str:
    """Removes '0x' if present and pads the string to 8 characters."""
    if prefix.startswith("0x"):
        prefix = prefix[2:]
    return ("00000000" + prefix)[-8:]

def uuid_with_prefix_custom_base(prefix: str) -> str:
    """Constructs a full UUID using the custom base and given prefix."""
    padding = add_leading_zeroes(prefix)
    return f"{padding}-{UUID_CUSTOM_BASE.lower()}"

# --- Characteristic UUIDs ---
# (Assuming the output command characteristic for motor/LED commands is this one.)
CHARACTERISTIC_OUTPUT_COMMAND_UUID = uuid_with_prefix_custom_base("0x1565")
# Input Command characteristic (for port initialization)
CHARACTERISTIC_INPUT_COMMAND_UUID = uuid_with_prefix_custom_base("0x1563")
# Port Type characteristic (used for detecting attached devices)
CHARACTERISTIC_PORT_TYPE_UUID = "00001527-1212-efde-1523-785feabcd123"

# --- Command Construction Functions ---

def write_motor_power_command(motor_power: int, port: int) -> bytearray:
    """
    Creates a 4-byte motor command in the format:
      [port, 0x01, 0x01, motor_power]
    """
    return bytearray([port, 0x01, 0x01, motor_power])

def calculate_motor_power(power: int) -> int:
    """
    For a WeDo 2.0 motor, the command expects:
      - A positive value from 1 to 100 for one direction.
      - A negative value is represented as (256 + power), e.g. -50 becomes 206.
      - 0 stops the motor.
    """
    if power > 0:
        return power
    elif power < 0:
        return 256 + power
    else:
        return 0

async def initialize_motor_port(client: BleakClient, port: int, connected_device: int = 1, mode: int = 0x02, value_format: int = 0x00):
    """
    Sends an 11-byte port initialization (handshake) command.
    Structure: [0x01, 0x02, port, connected_device, mode, 0x01, 0x00, 0x00, 0x00, value_format, 0x01]
    For a motor:
      - port: the port number (e.g., 1 or 2)
      - connected_device: 1 (motor)
      - mode: 0x02
      - value_format: 0x00
    """
    command = bytearray([0x01, 0x02, port, connected_device, mode, 0x01, 0x00, 0x00, 0x00, value_format, 0x01])
    print(f"Initializing motor port {port} with command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_INPUT_COMMAND_UUID, command)
    print("Motor port initialized.")

async def send_motor_command(client: BleakClient, port: int, power: int):
    """
    Sends a motor command using the 4-byte protocol.
    """
    motor_value = calculate_motor_power(power)
    command = write_motor_power_command(motor_value, port)
    print(f"Sending motor command to port {port}: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_OUTPUT_COMMAND_UUID, command)
    print(f"Motor command sent: port={port}, desired power={power} mapped to {motor_value}")

# --- LED Command Function ---

async def set_led_color(client: BleakClient, red: int, green: int, blue: int):
    """
    Sends an LED command to set the hub’s color.
    Expected structure: [0x06, 0x04, 0x03, R, G, B]
    """
    command = bytearray([0x06, 0x04, 0x03, red, green, blue])
    print(f"Sending LED color command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_OUTPUT_COMMAND_UUID, command)
    print(f"LED color command sent: R={red}, G={green}, B={blue}")

# --- Continuous Tasks ---

async def motor_control_loop_forever(client: BleakClient, power: int, motor_port: int):
    """Continuously sends the motor command at intervals for the detected motor port."""
    while True:
        await send_motor_command(client, port=motor_port, power=power)
        await asyncio.sleep(0.12)

async def cycle_led_colors_forever(client: BleakClient, duration: float = 3):
    """Cycles through a set of colors indefinitely, switching every 'duration' seconds."""
    colors = [
        (0, 0, 255),    # Blue
        (255, 0, 0),    # Red
        (0, 255, 0),    # Green
        (128, 0, 128)   # Purple
    ]
    while True:
        for red, green, blue in colors:
            print(f"Setting LED color to R={red}, G={green}, B={blue}")
            await set_led_color(client, red, green, blue)
            await asyncio.sleep(duration)

# --- Port Monitoring ---

# Global variable to store the motor port once detected.
motor_port = None

async def monitor_ports(client: BleakClient):
    """
    Subscribes to the Port Type characteristic notifications and updates the global motor_port
    when a device with type 1 (motor) is connected.
    """
    global motor_port

    def port_notification_handler(sender, data):
        global motor_port
        # Expected: data[0]=port, data[1]=connection status, data[3]=device type.
        if len(data) >= 4:
            port_id = data[0]
            is_connected = data[1]
            device_type = data[3]
            print(f"[Port Notification] Port: {port_id}, Connected: {is_connected}, Device Type: {device_type}")
            if is_connected == 1 and device_type == 1:
                if motor_port != port_id:
                    motor_port = port_id
                    print(f"Detected motor on port {motor_port}.")
        else:
            print(f"[Port Notification] Data: {list(data)}")
    
    await client.start_notify(CHARACTERISTIC_PORT_TYPE_UUID, port_notification_handler)
    print("Started monitoring port notifications.")
    while True:
        await asyncio.sleep(10)

# --- Main Function ---

async def main():
    global motor_port
    print("Scanning for LEGO WeDo 2.0 Hub...")
    devices = await BleakScanner.discover()
    wedo_address = None
    for device in devices:
        if device.name and ("WeDo" in device.name or "LPF2" in device.name):
            wedo_address = device.address
            print(f"Found device: {device.name} at {device.address}")
            break
    if wedo_address is None:
        print("No LEGO WeDo 2.0 Hub found.")
        return

    async with BleakClient(wedo_address) as client:
        if client.is_connected:
            print("Connected to LEGO WeDo 2.0 Hub!")
            await asyncio.sleep(2)  # Allow time for connection stabilization.
            
            # Start monitoring port notifications.
            monitor_task = asyncio.create_task(monitor_ports(client))
            
            # Wait until a motor is detected.
            while motor_port is None:
                print("Waiting for motor to be connected...")
                await asyncio.sleep(1)
            
            # Once a motor is detected, initialize that port.
            await initialize_motor_port(client, port=motor_port, connected_device=1, mode=0x02, value_format=0x00)
            await asyncio.sleep(0.5)
            
            # Run LED cycling and motor control concurrently.
            led_task = asyncio.create_task(cycle_led_colors_forever(client, duration=3))
            motor_task = asyncio.create_task(motor_control_loop_forever(client, power=50, motor_port=motor_port))
            
            # Wait indefinitely.
            await asyncio.gather(monitor_task, led_task, motor_task)
        else:
            print("Failed to connect.")

if __name__ == "__main__":
    asyncio.run(main())
