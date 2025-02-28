# sample_app.py

import asyncio
from pyLegoLLM.ble import LegoScanner, LegoClient
from pyLegoLLM.manager import Manager
from pyLegoLLM.devices.motor import Motor
from pyLegoLLM.devices.led import LED

async def motor_command_routine(manager, client):
    """
    Waits until a motor is detected by the manager.
    When detected, it initializes the motor and sends a power command of 50,
    then after 5 seconds sends a command of -50.
    """
    print("Waiting for motor detection...")
    # Poll for the motor_port in the manager (set by port notifications)
    while manager.motor_port is None:
        await asyncio.sleep(1)

    # Motor detected; create and initialize the Motor instance.
    motor = Motor(client, manager.motor_port)
    await motor.initialize()
    
    # Send motor command with power 50.
    await motor.send_command(50)
    print("Sent motor command with power 50.")
    
    # Wait for 5 seconds.
    await asyncio.sleep(5)
    
    # Send motor command with power -50.
    await motor.send_command(-50)
    print("Sent motor command with power -50.")

async def led_demo(client):
    """
    Exercises LED functionality:
      1. Sets LED to a predefined red.
      2. Sets LED to an RGB green.
      3. Blinks LED with blue for 5 seconds.
      4. Enters disco mode for 6 seconds, then stops and sets LED to white.
    """
    led = LED(client)
    
    print("Setting LED to predefined red...")
    await led.set_color("red")
    await asyncio.sleep(3)
    
    print("Setting LED to RGB green...")
    await led.set_color_rgb(0, 255, 0)
    await asyncio.sleep(3)
    
    print("Blinking LED with blue for 5 seconds...")
    await led.blink("blue", 5)
    await asyncio.sleep(3)
    
    print("Starting disco mode on LED...")
    await led.disco()
    await asyncio.sleep(6)
    led.stop_mode()
    
    print("Setting LED to white after disco mode...")
    await led.set_color("white")
    await asyncio.sleep(3)

async def main():
    scanner = LegoScanner()
    hub_address = await scanner.discover_hub()
    if hub_address is None:
        print("LEGO hub not found. Exiting.")
        return

    client = LegoClient(hub_address)
    if await client.connect():
        # Initialize the Manager with the connected client.
        manager = Manager(client)
        
        # Run the manager's monitoring tasks concurrently in the background.
        manager_task = asyncio.create_task(manager.run())
        
        # Run both motor and LED routines concurrently.
        motor_task = asyncio.create_task(motor_command_routine(manager, client))
        #led_task = asyncio.create_task(led_demo(client))
        
        #await asyncio.gather(motor_task, led_task)
        await asyncio.gather(motor_task)
        
        # Optionally, cancel the manager task after routines complete.
        manager_task.cancel()
    else:
        print("Failed to connect to the LEGO hub.")

if __name__ == '__main__':
    asyncio.run(main())
