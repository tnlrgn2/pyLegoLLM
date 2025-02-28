import asyncio
from bleak import BleakScanner, BleakClient

# --- Custom UUID Helpers ---

UUID_CUSTOM_BASE = "1212-EFDE-1523-785FEABCD123"
UUID_STANDARD_BASE = "0000-1000-8000-00805f9b34fb"

def add_leading_zeroes(prefix: str) -> str:
    if prefix.startswith("0x"):
        prefix = prefix[2:]
    return ("00000000" + prefix)[-8:]

def uuid_with_prefix_custom_base(prefix: str) -> str:
    padding = add_leading_zeroes(prefix)
    return f"{padding}-{UUID_CUSTOM_BASE.lower()}"

# --- Characteristic UUIDs ---

# For motor and LED commands (Output Command)
CHARACTERISTIC_OUTPUT_COMMAND_UUID = uuid_with_prefix_custom_base("0x1565")
# For port initialization (Input Command)
CHARACTERISTIC_INPUT_COMMAND_UUID = uuid_with_prefix_custom_base("0x1563")
# Port Type characteristic (used for detecting attached devices)
CHARACTERISTIC_PORT_TYPE_UUID = "00001527-1212-efde-1523-785feabcd123"
# Sensor Value characteristic (for sensor notifications)
SENSOR_VALUE_CHARACTERISTIC_UUID = uuid_with_prefix_custom_base("0x1560")

# --- Global Variables ---

motor_port = None         # Will hold the port number for a motor (device type 1)
port_devices = {}         # Maps port IDs to device types

# --- Command Construction Functions ---

def write_motor_power_command(motor_power: int, port: int) -> bytearray:
    """
    Creates a 4-byte motor command.
    For a WeDo 2.0 motor, the expected command is:
      [port, 0x01, 0x01, motor_power]
    """
    return bytearray([port, 0x01, 0x01, motor_power])

def map_value(x, in_min, in_max, out_min, out_max):
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

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

# --- Tilt Sensor Parsing Function ---

def parse_tilt_sensor_data(data: bytearray) -> str:
    """
    Parses an 8-byte tilt sensor message using the logic from your Java code.
    If byte 3 (index 3) is 38 or 39, then tilt = byte 2.
    If byte 5 (index 5) is 38 or 39, then tilt = byte 4.
    Then returns one of:
      "BACK"  if tilt is between 10 and 40,
      "RIGHT" if tilt is between 60 and 90,
      "FORWARD" if tilt is between 170 and 190,
      "LEFT" if tilt is between 220 and 240,
      "NO_TILT" if tilt is between 120 and 140 or no other condition matches.
    """
    if len(data) < 8:
        return "NO_TILT"
    tilt = -1
    if data[3] in (38, 39):
        tilt = data[2]
    if data[5] in (38, 39):
        tilt = data[4]
    if 10 < tilt < 40:
        return "BACK"
    if 60 < tilt < 90:
        return "RIGHT"
    if 170 < tilt < 190:
        return "FORWARD"
    if 220 < tilt < 240:
        return "LEFT"
    if 120 < tilt < 140:
        return "NO_TILT"
    return "NO_TILT"

# --- Functions ---

async def initialize_motor_port(client: BleakClient, port: int, connected_device: int = 1, mode: int = 0x02, value_format: int = 0x00):
    """
    Sends an 11-byte handshake command to initialize a port.
    Command: [0x01, 0x02, port, connected_device, mode, 0x01, 0x00, 0x00, 0x00, value_format, 0x01]
    For a motor, connected_device should be 1.
    """
    command = bytearray([0x01, 0x02, port, connected_device, mode, 0x01, 0x00, 0x00, 0x00, value_format, 0x01])
    print(f"Initializing motor port {port} with command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_INPUT_COMMAND_UUID, command)
    print("Motor port initialized.")

async def send_motor_command(client: BleakClient, port: int, power: int):
    """
    Sends a motor command as a 4-byte packet.
    Debug prints are minimized.
    """
    motor_value = calculate_motor_power(power)
    command = write_motor_power_command(motor_value, port)
    # Sending motor command (debug print commented out)
    # print(f"Sending motor command to port {port}: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_OUTPUT_COMMAND_UUID, command)
    # print(f"Motor command sent: port={port}, desired power={power} mapped to {motor_value}")

async def set_led_color(client: BleakClient, red: int, green: int, blue: int):
    """
    Sends an LED command in the format: [0x06, 0x04, 0x03, R, G, B]
    """
    command = bytearray([0x06, 0x04, 0x03, red, green, blue])
    print(f"Sending LED color command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_OUTPUT_COMMAND_UUID, command)
    print(f"LED color command sent: R={red}, G={green}, B={blue}")

# --- Continuous Tasks ---

async def motor_control_loop_forever(client: BleakClient, power: int, motor_port: int):
    """Continuously sends the motor command every ~120ms."""
    while True:
        await send_motor_command(client, port=motor_port, power=power)
        await asyncio.sleep(0.12)

async def cycle_led_colors_forever(client: BleakClient, duration: float = 3):
    """Cycles through LED colors indefinitely, including purple."""
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

# --- Port and Sensor Monitoring ---

async def monitor_ports(client: BleakClient):
    """
    Subscribes to Port Type notifications and updates:
      - global motor_port when a device with type 1 (motor) is detected
      - port_devices dictionary for all connected devices.
    """
    global motor_port, port_devices

    def port_notification_handler(sender, data):
        global motor_port, port_devices
        if len(data) >= 4:
            port_id = data[0]
            is_connected = data[1]
            device_type = data[3]
            print(f"[Port Notification] Port: {port_id}, Connected: {is_connected}, Device Type: {device_type}")
            port_devices[port_id] = device_type
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

async def monitor_sensor_values(client: BleakClient):
    """
    Subscribes to sensor value notifications (from SENSOR_VALUE_CHARACTERISTIC_UUID).
    Distinguishes:
      - Tilt sensor (device type 34): parses an 8-byte message using parse_tilt_sensor_data.
      - Distance sensor (device type 35): parses using parse_distance_sensor_data (see below).
    """
    def sensor_notification_handler(sender, data):
        print(f"[Sensor Notification] Raw data: {list(data)}")
        if len(data) >= 8:
            port_id = data[1]
            device_type = port_devices.get(port_id)
            message_type = data[0]
            if message_type == 0x45:
                if device_type == 34:
                    tilt_result = parse_tilt_sensor_data(data)
                    print(f"[Tilt Sensor] Port {port_id}: Tilt = {tilt_result}")
                elif device_type == 35:
                    # For distance sensor, mimic the Java logic:
                    # If data[5] is 176-179, distance = data[4] - 69.
                    if data[5] in (176, 177, 178, 179):
                        distance = data[4] - 69
                        print(f"[Distance Sensor] Port {port_id}: Distance = {distance}")
                    else:
                        print(f"[Distance Sensor] Port {port_id}: Invalid data")
                else:
                    print(f"[Sensor Notification] Unhandled device type {device_type} on port {port_id}")
            else:
                print(f"[Sensor Notification] Unhandled message type {message_type} on port {port_id}")
        else:
            print(f"[Sensor Notification] Incomplete data: {list(data)}")
    await client.start_notify(SENSOR_VALUE_CHARACTERISTIC_UUID, sensor_notification_handler)
    print("Started monitoring sensor values.")
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
            
            # Start monitoring port notifications and sensor values.
            monitor_ports_task = asyncio.create_task(monitor_ports(client))
            sensor_values_task = asyncio.create_task(monitor_sensor_values(client))
            
            # Wait until a motor (device type 1) is detected.
            while motor_port is None:
                #print("Waiting for motor to be connected...")
                await asyncio.sleep(1)
            
            # Once a motor is detected, initialize that port.
            await initialize_motor_port(client, port=motor_port, connected_device=1, mode=0x02, value_format=0x00)
            await asyncio.sleep(0.5)
            
            # Run LED cycling and motor control concurrently.
            led_task = asyncio.create_task(cycle_led_colors_forever(client, duration=3))
            motor_task = asyncio.create_task(motor_control_loop_forever(client, power=50, motor_port=motor_port))
            
            await asyncio.gather(monitor_ports_task, sensor_values_task, led_task, motor_task)
        else:
            print("Failed to connect.")

if __name__ == "__main__":
    asyncio.run(main())
