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
CHARACTERISTIC_OUTPUT_COMMAND_UUID = uuid_with_prefix_custom_base("0x1565")  # for motor/LED commands
CHARACTERISTIC_INPUT_COMMAND_UUID = uuid_with_prefix_custom_base("0x1563")   # for port initialization
CHARACTERISTIC_PORT_TYPE_UUID = "00001527-1212-efde-1523-785feabcd123"       # for port notifications
SENSOR_VALUE_CHARACTERISTIC_UUID = uuid_with_prefix_custom_base("0x1560")     # for sensor notifications

# --- Global Variables ---
motor_port = None         # Will hold the port number for a motor (device type 1)
port_devices = {}         # Maps port IDs to device types
initialized_ports = {}    # Tracks sensor initialization per port

motor_initialized = False # For motor port initialization

# --- Command Construction Functions ---
def write_motor_power_command(motor_power: int, port: int) -> bytearray:
    # For WeDo 2.0, the motor command is a 4-byte packet: [port, 0x01, 0x01, motor_power]
    return bytearray([port, 0x01, 0x01, motor_power])

def map_value(x, in_min, in_max, out_min, out_max):
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

def calculate_motor_power(power: int) -> int:
    # Positive speeds: send the percentage (1-100).
    # Negative speeds: send (256 + power), e.g. -50 becomes 206.
    if power > 0:
        return power
    elif power < 0:
        return 256 + power
    else:
        return 0

# --- Sensor Port Initialization Functions ---
async def initialize_tilt_sensor_port(client: BleakClient, port: int):
    # Example command for tilt sensor initialization (may require tweaking)
    command = bytearray([0x01, 0x02, port, 34, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01])
    print(f"Initializing tilt sensor on port {port} with command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_INPUT_COMMAND_UUID, command)
    print(f"Tilt sensor initialized on port {port}")

async def initialize_distance_sensor_port(client: BleakClient, port: int):
    # Example command for distance sensor initialization (may require tweaking)
    command = bytearray([0x01, 0x02, port, 35, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01])
    print(f"Initializing distance sensor on port {port} with command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_INPUT_COMMAND_UUID, command)
    print(f"Distance sensor initialized on port {port}")

async def initialize_motor_port(client: BleakClient, port: int):
    # Example motor initialization command (for device type 1)
    command = bytearray([0x01, 0x02, port, 1, 0x02, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01])
    print(f"Initializing motor on port {port} with command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_INPUT_COMMAND_UUID, command)
    print(f"Motor initialized on port {port}")

async def send_motor_command(client: BleakClient, port: int, power: int):
    motor_value = calculate_motor_power(power)
    command = write_motor_power_command(motor_value, port)
    # (Motor command logging is minimized)
    await client.write_gatt_char(CHARACTERISTIC_OUTPUT_COMMAND_UUID, command)

async def set_led_color(client: BleakClient, red: int, green: int, blue: int):
    command = bytearray([0x06, 0x04, 0x03, red, green, blue])
    print(f"Sending LED color command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_OUTPUT_COMMAND_UUID, command)
    print(f"LED color command sent: R={red}, G={green}, B={blue}")

# --- Continuous Tasks ---
async def motor_control_loop_forever(client: BleakClient, power: int, motor_port: int):
    while True:
        await send_motor_command(client, port=motor_port, power=power)
        await asyncio.sleep(0.12)

async def cycle_led_colors_forever(client: BleakClient, duration: float = 3):
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

# --- Sensor Parsing and Notification ---
def sensor_notification_handler(sender, data):
    print(f"[Sensor Notification] Raw data ({len(data)} bytes): {list(data)}")
    if len(data) < 4:
        print("[Sensor Notification] Data length less than expected (4 bytes required).")
        return
    port_id = data[1]
    message_type = data[0]
    print(f"[Sensor Notification] Message Type: {message_type}, Port ID: {port_id}")
    device_type = port_devices.get(port_id)
    print(f"[Sensor Notification] Device type for port {port_id}: {device_type}")
    # For our LPF2 hub, sensor notifications are 4 bytes.
    if device_type == 34:
        # Assume tilt sensor: use the third byte (index 2) as the tilt reading.
        tilt_val = data[2]
        print(f"[Tilt Sensor] Port {port_id}: Tilt raw value = {tilt_val}")
    elif device_type == 35:
        # Assume distance sensor: use the third byte as the raw distance reading.
        distance_val = data[2]
        print(f"[Distance Sensor] Port {port_id}: Distance raw value = {distance_val}")
    else:
        print(f"[Sensor Notification] Unhandled device type {device_type} on port {port_id}.")

async def monitor_sensor_values(client: BleakClient):
    await client.start_notify(SENSOR_VALUE_CHARACTERISTIC_UUID, sensor_notification_handler)
    print("Started monitoring sensor values.")
    while True:
        await asyncio.sleep(10)

# --- Port Monitoring ---
async def monitor_ports(client: BleakClient):
    global motor_port, port_devices, initialized_ports
    initialized_ports = {}
    def port_notification_handler(sender, data):
        global motor_port, port_devices, initialized_ports
        print(f"[Port Notification Raw] {list(data)}")
        if len(data) >= 4:
            port_id = data[0]
            is_connected = data[1]
            device_type = data[3]
            print(f"[Port Notification] Port: {port_id}, Connected: {is_connected}, Device Type: {device_type}")
            port_devices[port_id] = device_type
            # Detect motor (device type 1)
            if is_connected == 1 and device_type == 1:
                if motor_port != port_id:
                    motor_port = port_id
                    print(f"Detected motor on port {motor_port}.")
            # For tilt sensor (34)
            if is_connected == 1 and device_type == 34:
                if not initialized_ports.get((port_id, 34), False):
                    asyncio.create_task(initialize_tilt_sensor_port(client, port_id))
                    initialized_ports[(port_id, 34)] = True
            # For distance sensor (35)
            if is_connected == 1 and device_type == 35:
                if not initialized_ports.get((port_id, 35), False):
                    asyncio.create_task(initialize_distance_sensor_port(client, port_id))
                    initialized_ports[(port_id, 35)] = True
        else:
            print(f"[Port Notification] Incomplete data: {list(data)}")
    await client.start_notify(CHARACTERISTIC_PORT_TYPE_UUID, port_notification_handler)
    print("Started monitoring port notifications.")
    while True:
        print(f"[Port Devices] {port_devices}")
        print(f"[Initialized Ports] {initialized_ports}")
        await asyncio.sleep(10)

# --- Motor Detection Task ---
async def motor_detection_and_control(client: BleakClient, power: int):
    global motor_port
    while True:
        if motor_port is not None:
            print(f"[Motor Detection] Motor detected on port {motor_port}.")
            if port_devices.get(motor_port) == 1 and not initialized_ports.get((motor_port, 1), False):
                await initialize_motor_port(client, port=motor_port)
                initialized_ports[(motor_port, 1)] = True
                print("[Motor Detection] Motor port initialized.")
            # Motor control loop is started by the separate task.
        else:
            print("[Motor Detection] No motor detected yet.")
        await asyncio.sleep(2)

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
            await asyncio.sleep(2)  # Stabilize connection.
            
            # Start monitoring port notifications and sensor values.
            monitor_ports_task = asyncio.create_task(monitor_ports(client))
            sensor_values_task = asyncio.create_task(monitor_sensor_values(client))
            
            # Start LED color cycling (always running).
            led_task = asyncio.create_task(cycle_led_colors_forever(client, duration=3))
            
            # Start motor detection & control.
            motor_detection_task = asyncio.create_task(motor_detection_and_control(client, power=50))
            
            await asyncio.gather(monitor_ports_task, sensor_values_task, led_task, motor_detection_task)
        else:
            print("Failed to connect.")

if __name__ == "__main__":
    asyncio.run(main())

