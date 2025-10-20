import snap7
import snap7.util as s7util

class plcS7:
    """Class for communication with a Siemens S7 PLC using Snap7"""

    def __init__(self, ip: str, rack: int, slot: int, tcpport: int = 102):
        """Initialize the PLC client with IP, rack, slot, and TCP port"""
        self.ip = ip
        self.rack = rack
        self.slot = slot
        self.tcpport = tcpport
        self.client = snap7.client.Client()

    def connect(self):
        """Connect to the PLC and reset registers if successful"""
        try:
            self.client.connect(self.ip, self.rack, self.slot, self.tcpport)
            if self.client.get_connected():
                print(
                    f"Connected to S7 PLC at {self.ip}:{self.tcpport} (rack {self.rack}, slot {self.slot})")
                return True
            else:
                print(f"Cannot connect to S7 PLC at {self.ip}")
                return False
        except Exception as e:
            print("Connection error:", e)
            return False

    def disconnect(self):
        """Disconnect from the PLC if the connection is active"""
        if self.client.get_connected():
            self.client.disconnect()

    def isConnected(self) -> bool:
        """check if the connection is alive and attempt reconnection if not"""
        if not self.client.get_connected():
            print("Connection lost to the PLC!")
            return False
        else:
            return True

    def SetDI(self, index, value, db_number=10):
        """
        Set a digital input (DI) to 0 or 1.
        index: bit index (0-16)
        value: True/False or 1/0
        db_number: PLC data block
        """
        if 0 <= index < 16:
            self.isConnected()
            byte_index = index // 8  # determine which byte contains the bit
            bit_index = index % 8    # determine the bit position within the byte
            data = self.client.db_read(db_number, byte_index, 1)
            s7util.set_bool(data, 0, bit_index, bool(value))
            self.client.db_write(db_number, byte_index, data)
            return int(bool(value))
        return 0

    def SetAI(self, index, value, db_number=10):
        """
        Set an analog input (AI) as a 16-bit integer.
        index: input index (0-15)
        value: value (0-65535)
        db_number: PLC data block
        """
        if 0 <= index < 16:
            self.isConnected()
            val = int(value) & 0xFFFF  # ensure 16-bit
            byte_index = 4 + index * 2  # each AI occupies 2 bytes
            data = bytearray(2)
            s7util.set_int(data, 0, val)
            self.client.db_write(db_number, byte_index, data)
            return val
        return 0

    def GetDO(self, index, db_number=10):
        """
        Read a digital output (DO).
        index: output index (0-15)
        db_number: PLC data block
        """
        if 0 <= index < 16:
            self.isConnected()
            byte_index = 2 + index // 8  # determine which byte contains the bit
            bit_index = index % 8         # determine the bit position within the byte
            data = self.client.db_read(db_number, byte_index, 1)
            return int(s7util.get_bool(data, 0, bit_index))
        return 0

    def GetAO(self, index, db_number=10):
        """
        Read an analog output (AO) as a 16-bit integer.
        index: output index (0-15)
        db_number: PLC data block
        """
        if 0 <= index < 16:
            self.isConnected()
            byte_index = 36 + index * 2  # each AO occupies 2 bytes
            data = self.client.db_read(db_number, byte_index, 2)
            return s7util.get_int(data, 0)
        return 0

    def reset_registers(self, db_number=10):
        """
        Reset all registers in the data block to 0.
        db_number: PLC data block
        """
        data = bytearray(68)  # create zeroed byte array for reset
        self.client.db_write(db_number, 0, data)
