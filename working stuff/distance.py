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
CHARACTERISTIC_OUTPUT_COMMAND_UUID = uuid_with_prefix_custom_base("0x1565")  # motor/LED commands
CHARACTERISTIC_INPUT_COMMAND_UUID = uuid_with_prefix_custom_base("0x1563")   # port initialization
CHARACTERISTIC_PORT_TYPE_UUID = "00001527-1212-efde-1523-785feabcd123"       # port notifications
SENSOR_VALUE_CHARACTERISTIC_UUID = uuid_with_prefix_custom_base("0x1560")     # sensor notifications

# --- Global Variables ---
motor_port = None         # Port number for motor (device type 1)
port_devices = {}         # Maps port IDs to device types
initialized_ports = {}    # Tracks sensor initialization status

# --- Command Construction Functions ---
def write_motor_power_command(motor_power: int, port: int) -> bytearray:
    # For WeDo 2.0, the motor command is a 4-byte packet: [port, 0x01, 0x01, motor_power]
    return bytearray([port, 0x01, 0x01, motor_power])

def calculate_motor_power(power: int) -> int:
    if power > 0:
        return power
    elif power < 0:
        return 256 + power
    else:
        return 0

# --- Sensor Port Initialization Functions ---
async def initialize_tilt_sensor_port(client: BleakClient, port: int):
    command = bytearray([0x01, 0x02, port, 34, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01])
    print(f"Initializing tilt sensor on port {port} with command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_INPUT_COMMAND_UUID, command)
    print(f"Tilt sensor initialized on port {port}")

async def initialize_distance_sensor_port(client: BleakClient, port: int):
    command = bytearray([0x01, 0x02, port, 35, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01])
    print(f"Initializing distance sensor on port {port} with command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_INPUT_COMMAND_UUID, command)
    print(f"Distance sensor initialized on port {port}")

async def initialize_motor_port(client: BleakClient, port: int):
    command = bytearray([0x01, 0x02, port, 1, 0x02, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01])
    print(f"Initializing motor on port {port} with command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_INPUT_COMMAND_UUID, command)
    print(f"Motor initialized on port {port}")

async def send_motor_command(client: BleakClient, port: int, power: int):
    motor_value = calculate_motor_power(power)
    command = write_motor_power_command(motor_value, port)
    await client.write_gatt_char(CHARACTERISTIC_OUTPUT_COMMAND_UUID, command)

async def set_led_color(client: BleakClient, red: int, green: int, blue: int):
    command = bytearray([0x06, 0x04, 0x03, red, green, blue])
    #print(f"Sending LED color command: {list(command)}")
    await client.write_gatt_char(CHARACTERISTIC_OUTPUT_COMMAND_UUID, command)
    #print(f"LED color command sent: R={red}, G={green}, B={blue}")

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
            #print(f"Setting LED color to R={red}, G={green}, B={blue}")
            await set_led_color(client, red, green, blue)
            await asyncio.sleep(duration)

# --- Polling Task for Distance Sensor ---
async def poll_distance_sensor(client: BleakClient, port: int):
    while True:
        try:
            data = await client.read_gatt_char(SENSOR_VALUE_CHARACTERISTIC_UUID)
            print(f"[Distance Sensor Poll] Raw data (length {len(data)}): {list(data)}")
            print(f"[Distance Sensor Poll] Hex: {data.hex()}")
            if len(data) < 8:
                print(f"[Distance Sensor Poll] Port {port}: Data length {len(data)} less than expected (expected 8 bytes).")
                # Additionally print each byte with its index:
                for i, b in enumerate(data):
                    print(f"   Byte {i}: {b} (0x{b:02x})")
            else:
                # If 8 bytes, process as expected:
                if data[5] in (176, 177, 178, 179):
                    distance = (data[4] & 0xff) - 69
                    print(f"[Distance Sensor Poll] Port {port}: Distance = {distance}")
                else:
                    print(f"[Distance Sensor Poll] Port {port}: Unexpected value in byte 5: {data[5]}")
        except Exception as e:
            print(f"[Distance Sensor Poll] Exception: {e}")
        await asyncio.sleep(2)


# --- Sensor Parsing Functions ---
def parse_tilt_sensor_data(data: bytearray) -> str:
    if len(data) < 8:
        print("Tilt sensor data too short:", list(data))
        return "NO_TILT"
    tilt = -1
    if data[3] in (38, 39):
        tilt = data[2]
        print(f"Tilt sensor: using data[2]={data[2]} because data[3]={data[3]}")
    elif data[5] in (38, 39):
        tilt = data[4]
        print(f"Tilt sensor: using data[4]={data[4]} because data[5]={data[5]}")
    else:
        print(f"Tilt sensor: unexpected header bytes: data[3]={data[3]}, data[5]={data[5]}")
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

# --- Sensor Notification Handler ---
def sensor_notification_handler(sender, data):
    print(f"[Sensor Notification] Raw data ({len(data)} bytes): {list(data)}")
    if len(data) < 4:
        print("[Sensor Notification] Data length less than expected.")
        return
    port_id = data[1]
    message_type = data[0]
    print(f"[Sensor Notification] Message Type: {message_type}, Port ID: {port_id}")
    device_type = port_devices.get(port_id)
    print(f"[Sensor Notification] Device type for port {port_id}: {device_type}")
    if device_type == 34:
        if len(data) >= 8:
            tilt_result = parse_tilt_sensor_data(data)
            print(f"[Tilt Sensor] Port {port_id}: Tilt = {tilt_result}")
        else:
            print(f"[Tilt Sensor] Port {port_id}: Data length {len(data)} too short for tilt parsing.")
    elif device_type == 35:
        if len(data) == 8:
            if data[5] in (176, 177, 178, 179):
                distance = (data[4] & 0xff) - 69
                print(f"[Distance Sensor] Port {port_id}: Distance = {distance}")
            else:
                print(f"[Distance Sensor] Port {port_id}: Unexpected value in byte 5: {data[5]}")
        else:
            print(f"[Distance Sensor] Port {port_id}: Unexpected data length: {len(data)}")
    else:
        print(f"[Sensor Notification] Unhandled device type {device_type} on port {port_id}")

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
            if is_connected == 1 and device_type == 35:
                if not initialized_ports.get((port_id, 35), False):
                    asyncio.create_task(initialize_distance_sensor_port(client, port_id))
                    initialized_ports[(port_id, 35)] = True
            if is_connected == 1 and device_type == 34:
                if not initialized_ports.get((port_id, 34), False):
                    asyncio.create_task(initialize_tilt_sensor_port(client, port_id))
                    initialized_ports[(port_id, 34)] = True
            if is_connected == 1 and device_type == 1:
                if motor_port != port_id:
                    motor_port = port_id
                    print(f"Detected motor on port {motor_port}.")
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
            await asyncio.sleep(2)
            
            monitor_ports_task = asyncio.create_task(monitor_ports(client))
            sensor_values_task = asyncio.create_task(monitor_sensor_values(client))
            led_task = asyncio.create_task(cycle_led_colors_forever(client, duration=3))
            motor_detection_task = asyncio.create_task(motor_detection_and_control(client, power=50))
            
            # If a distance sensor is detected on any port, start polling it.
            async def check_and_poll_distance_sensor():
                while True:
                    for port, device in port_devices.items():
                        if device == 35:
                            print(f"[Distance Sensor Poll] Starting poll on port {port}.")
                            await poll_distance_sensor(client, port)
                    await asyncio.sleep(5)
            distance_sensor_task = asyncio.create_task(check_and_poll_distance_sensor())
            
            await asyncio.gather(monitor_ports_task, sensor_values_task, led_task, motor_detection_task, distance_sensor_task)
        else:
            print("Failed to connect.")

if __name__ == "__main__":
    asyncio.run(main())
