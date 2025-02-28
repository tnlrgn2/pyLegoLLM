# pyLegoLLM/manager.py

import asyncio
from pyLegoLLM.ble.utils import (
    CHARACTERISTIC_PORT_TYPE_UUID,
    SENSOR_VALUE_CHARACTERISTIC_UUID,
)

class Manager:
    """
    The main controller that manages devices, monitors ports, and coordinates tasks.
    It listens for port notifications to detect connected devices (like motors)
    and sensor notifications to process sensor data.
    """
    def __init__(self, client):
        """
        Initializes the Manager with a connected BLE client.
        """
        self.client = client
        self.motor_port = None
        self.port_devices = {}        # Maps port IDs to device types.
        self.initialized_ports = {}   # Tracks sensor initialization per port.

    def port_notification_handler(self, sender, data):
        """
        Callback for port notifications.
        Updates port_devices if needed.
        """
        if len(data) >= 4:
            port_id = data[0]
            is_connected = data[1]
            device_type = data[3]
            print(f"[Port Notification] Port: {port_id}, Connected: {is_connected}, Device Type: {device_type}")
            self.port_devices[port_id] = device_type

            # Detect motor (device type 1)
            if is_connected == 1 and device_type == 1:
                if self.motor_port != port_id:
                    self.motor_port = port_id
                    print(f"Detected motor on port {self.motor_port}.")

        else:
            print(f"[Port Notification] Incomplete data: {list(data)}")

    async def monitor_ports(self):
        """
        Subscribes to port type notifications and continuously monitors ports.
        """
        await self.client.start_notify(CHARACTERISTIC_PORT_TYPE_UUID, self.port_notification_handler)
        print("Started monitoring port notifications.")
        while True:
            print(f"[Port Devices] {self.port_devices}")
            print(f"[Initialized Ports] {self.initialized_ports}")
            await asyncio.sleep(10)

    def sensor_notification_handler(self, sender, data):
        """
        Callback for sensor notifications.
        For now just prints notifications.
        TODO: Process sensor data.
        """
        print(f"[Sensor Notification] Raw data ({len(data)} bytes): {list(data)}")
        if len(data) < 4:
            print("[Sensor Notification] Data length less than expected (4 bytes required).")
            return
        port_id = data[1]
        message_type = data[0]
        print(f"[Sensor Notification] Message Type: {message_type}, Port ID: {port_id}")
        device_type = self.port_devices.get(port_id)
        print(f"[Sensor Notification] Device type for port {port_id}: {device_type}")

    async def monitor_sensor_values(self):
        """
        Subscribes to sensor value notifications and continuously monitors sensor data.
        """
        await self.client.start_notify(SENSOR_VALUE_CHARACTERISTIC_UUID, self.sensor_notification_handler)
        print("Started monitoring sensor values.")
        while True:
            await asyncio.sleep(10)

    async def run(self):
        """
        Runs the manager by concurrently monitoring ports and sensor values.
        """
        await asyncio.gather(
            self.monitor_ports(),
            self.monitor_sensor_values()
        )
