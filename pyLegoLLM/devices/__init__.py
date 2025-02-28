"""
pyLegoLLM.devices - A subpackage for managing LEGO devices like motors and LEDs.
"""

# Expose the Motor and LED classes at the package level
from .motor import Motor
from .led import LED

__all__ = ["Motor", "LED"]  # Optional: Defines what gets imported with `from devices import *`