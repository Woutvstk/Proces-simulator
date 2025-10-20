import snap7
#https://python-snap7.readthedocs.io/en/1.0/logo.html

class logoS7:
    """Class for communication with a Siemens S7 PLC using Snap7"""

    def __init__(self, ip: str, tasplogo: int, tsapServer: int, tcpport: int = 102):
        """Initialize the PLC logo with IP, rack, slot, and TCP port"""
        self.ip = ip
        self.tasplogo = tasplogo
        self.taspServer = tsapServer
        self.tcpport = tcpport
        self.logo = snap7.logo.Logo()

    def connect(self):
        """Connect to the LOGO"""
        ### <ip_address, tsap_snap7 (logo) 03.00 = 0x0300, tsap_logo (server) 20.00 = 0x2000>
        try:
            self.logo.create()
            self.logo.connect(self.ip, self.tasplogo, self.taspServer)
            if self.logo.get_connected():
                print(
                    f"Connected to S7 LOGO at {self.ip}:{self.tcpport} (tsaplogo {self.tasplogo}, tsapServer {self.taspServer})")
                return True
            else:
                print(f"Cannot connect to S7 LOGO! at {self.ip}")
                return False
        except Exception as e:
            print("Connection error:", e)
            return False

    def disconnect(self):
        """Disconnect from the PLC if the connection is active"""
        if self.logo.get_connected():
            self.logo.disconnect()
            self.logo.destroy()

    def isConnected(self) -> bool:
        """check if the connection is alive and attempt reconnection if not"""
        if not self.logo.get_connected():
            print("Connection lost to the LOGO!")
            return False
        else:
            return True

    def SetDI(self, index, value):
        """
        Set a digital input (DI) to 0 or 1.
        index: bit index (0-16)
        value: True/False or 1/0
        """
        if 0 <= index < 16:
            byte_index = index // 8  # determine which byte contains the bit
            bit_index = index % 8    # determine the bit position within the byte
            address = "V" + str(byte_index) + "." + str(bit_index)
            self.logo.write(address,value)
            return int(bool(value))
        return 0

    def SetAI(self, index, value):
        """
        Set an analog input (AI) as a 16-bit integer.
        index: input index (0-15)
        value: value (0-65535)
        """
        if 0 <= index < 16:
            val = int(value) & 0xFFFF  # ensure 16-bit
            byte_index = 4 + index *2  # each AI occupies 2 bytes 
            address = "VW" + str(byte_index)
            self.logo.write(address, val)
            return val
        return 0

    def GetDO(self, index):
        """
        Read a digital output (DO).
        index: output index (0-15)
        """
        if 0 <= index < 16:
            byte_index = 2 + index // 8   # determine which byte contains the bit
            bit_index = index % 8  # determine the bit position within the byte
            address = "V" + str(byte_index) + "." + str(bit_index)
            data = self.logo.read(address)
            return int(bool(data)) 
        return 0

    def GetAO(self, index):
        """
        Read an analog output (AO) as a 16-bit integer.
        index: output index (0-15)
        """
        if 0 <= index < 16:
            byte_index = 36 + index * 2  # each AO occupies 2 bytes
            address = "VW" + str(byte_index)
            data = self.logo.read(address)
            return int(data)
        return 0

    def reset_registers(self, db_number=10):
        """
        Reset all registers in the data block to 0.
        """
        for i in range(0,3):
            for j in range(0,7):
                address = "V" + str(j) + "." + str(i)
                self.logo.write(address, 0)

        for i in range(4,68):
            address = "VW" + str(i)
            self.logo.write(address, 0)

