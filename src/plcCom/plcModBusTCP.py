from pymodbus.client import ModbusTcpClient
import time


class plcModBusTCP:
    """
    Class for Modbus TCP communication with a PLC.
    """

    def __init__(self, ip: str, port: int = 502):
        """Initialize the Modbus client with IP and port"""
        self.ip = ip
        self.port = port
        self.client = None

    def connect(self):
        """Connect to the Modbus server and reset registers if successful"""
        self.client = ModbusTcpClient(self.ip, port=self.port)
        if self.client.connect():
            print(f"Connected to Modbus server {self.ip}:{self.port}")
            return True
        else:
            print(f"Cannot connect to Modbus server {self.ip}:{self.port}")
            return False

    def disconnect(self):
        """Close the connection to the Modbus server"""
        if self.client:
            self.client.close()

    def isConnected(self) -> bool:
        """isConnected connection and attempt to reconnect if broken"""
        if self.client is None or not self.client.is_socket_open():
            print("Connection lost to the PLC!")
            return False
        else:
            return True

    def SetDI(self, index, value):
        """
        Write a digital input (0/1) to the Modbus registers.
        index: register index (0-15)
        value: 0 or 1 (or True/False)
        """
        self.isConnected()
        if 0 <= index < 16:
            self.client.write_register(index, int(bool(value)))
            return int(bool(value))  # return as int
        return 0

    def SetAI(self, index, value):
        """
        Write an analog input (0-65535) to the Modbus registers.
        index: register index (16-31)
        value: integer value
        """
        self.isConnected()
        if 16 <= index < 32:
            val = int(value) & 0xFFFF  # ensure 16-bit
            self.client.write_register(index, val)
            return val
        return 0

    def GetDO(self, index):
        """
        Read a digital output (coil) from the Modbus server.
        index: coil index
        """
        self.isConnected()
        rr = self.client.read_coils(index, count=1)
        if rr.isError():
            return 0
        return int(rr.bits[0])  # return 0 or 1

    def GetAO(self, index):
        """
        Read an analog output (holding register) from the Modbus server.
        index: register index
        """
        self.isConnected()
        rr = self.client.read_holding_registers(index + 32, count=1)
        if rr.isError():
            return None
        return rr.registers[0]

    def reset_registers(self):
        """Reset all DI and AI registers to 0"""
        for i in range(16):
            self.client.write_register(i, 0)       # reset DI registers
            self.client.write_register(i + 16, 0)  # reset AI registers
