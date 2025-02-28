# pyLegoLLM

**pyLegoLLM** is a Python package designed to control LEGO devices (e.g., motors, LEDs, sensors) via Bluetooth Low Energy (BLE). This package serves as the **low-level layer** to enable **Large Language Models (LLMs)** and other AI systems to interact with LEGO devices programmatically. It is not just a basic controller but is developed with the broader vision of enabling LLMs to control IoT devices over BLE.

---

## **Why pyLegoLLM?**

The goal of `pyLegoLLM` is to bridge the gap between **natural language instructions** and **physical device control**. By providing a robust, low-level API for LEGO devices, this package lays the foundation for integrating LEGO-based IoT systems with LLMs. This enables scenarios such as:
- **Voice-controlled LEGO robots**: Use natural language to command LEGO devices.
- **AI-driven automation**: Allow LLMs to orchestrate complex behaviors across multiple LEGO devices.
- **Educational tools**: Teach programming and robotics by combining LEGO with AI.

This package is designed to be **extensible**, allowing developers to build higher-level abstractions or integrate it into larger AI systems.

---

## **Features**

- **BLE Communication**: Connect to and control LEGO devices over Bluetooth Low Energy.
- **Device Management**: Manage motors, LEDs, and sensors with a simple API.
- **Asynchronous Design**: Built on `asyncio` for non-blocking, event-driven control.
- **LLM-Friendly**: Designed to be easily integrated with AI systems for natural language control.

---

## **Installation**

You can install `pyLegoLLM` via pip:

```bash
pip install pyLegoLLM
```

---

## **Usage**
See the sample app for a basic usage. 

You can also try:


```bash
from pyLegoLLM import Manager
from pyLegoLLM.ble import LegoClient
from pyLegoLLM.devices import Motor

async def main():
    # Connect to a LEGO device
    client = LegoClient()
    await client.connect()

    # Initialize the manager
    manager = Manager(client)

    # Detect and control a motor
    motor = Motor(client, port=0)
    await motor.initialize()
    await motor.send_command(power=50)  # Run the motor at 50% power

    # Monitor ports and sensor values
    await manager.run()

# Run the program
asyncio.run(main())
```
---

## **Enabling LLM Control**
To integrate with an LLM, you can map natural language commands to pyLegoLLM API calls. For example:
```bash
def handle_command(command: str):
    if "turn on the motor" in command:
        motor.send_command(power=100)
    elif "blink the LED" in command:
        led.blink(color="red", duration=5)
```

## **Roadmap**
Add support for more LEGO devices (e.g., sensors, lights).
Develop an LLM integration layer for natural language control.
Provide pre-built examples for common use cases (e.g., voice-controlled robots).

## **Contributing**
If you’re interested in improving pyLegoLLM, please:
Fork the repository.
Create a new branch for your feature or bugfix.
Submit a pull request.

## **License**
pyLegoLLM is released under the MIT License. See the LICENSE file for details.

## **Acknowledgments**
Inspired by the potential of LLMs to control physical devices.