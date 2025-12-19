"""
IO Module - Input/Output operations, protocols, and hardware communication.

This module provides:
- Protocol communication (Logo S7, PLC S7, PLCSimAPI)
- IO handler for reading/writing simulation data
- IO configuration management
"""

from .handler import IOHandler

__all__ = ['IOHandler']
