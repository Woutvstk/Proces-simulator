import snap7

""" continued with the byte, bit structure for program compatibility, 
    due to the different mapping in LOGO we get now:
    i1 = byte:0 bit:0 // i10 = byte:1 bit:1, ..."""

class logoS7:
    """Class for communication with a Siemens LOGO PLC using Snap7."""

    def __init__(self, ip: str, tsapLogo: int, tsapServer: int, tcpport: int = 102):
        """
        Initialize the LOGO client with IP, TSAP for LOGO and server, and TCP port.

        Parameters:
        ip (str): IP address of the LOGO PLC
        tsapLogo (int): TSAP of the LOGO PLC
        tsapServer (int): TSAP of the server
        tcpport (int): TCP port (default: 102)
        """
        self.ip = ip
        self.tsapLogo = tsapLogo
        self.tsapServer = tsapServer
        self.tcpport = tcpport
        self.logo = snap7.logo.Logo()

    def connect(self) -> bool:
        """
        Connect to the LOGO PLC.

        Returns:
        bool: True if connected successfully, False otherwise.
        """
        try:
            self.logo.connect(self.ip, self.tsapLogo, self.tsapServer)
            if self.logo.get_connected():
                print(f"Connected to LOGO at {self.ip}")
                return True
            else:
                print(f"Cannot connect to LOGO at {self.ip}")
                return False
        except Exception as e:
            print("Connection error:", e)
            return False

    def disconnect(self):
        """Disconnect from the LOGO PLC if connected."""
        if self.logo.get_connected():
            self.logo.disconnect()

    def isConnected(self) -> bool:
        """Check if the connection to the LOGO PLC is alive."""
        return self.logo.get_connected()

    def SetDI(self, byte: int, bit: int, value: bool) -> int:
        """
        Set a digital input (DI) via byte and bit.

        Parameters:
        byte (int): Byte index (0..n)
        bit (int): Bit position within the byte (0..7)
        value (bool): True/False to set or clear the bit

        Returns:
        int: Value set (1/0), -1 on error

        Example:
        i1 = byte:0 bit:0 // i10 = byte:1 bit:1, ...
        """
        if 0 <= bit < 8:
            address = f"V{byte+1024}.{bit}"
            self.logo.write(address, int(bool(value)))
            return int(bool(value))
        return -1

    def GetDO(self, byte: int, bit: int) -> int:
        """
        Read a digital output (DO) via byte and bit.

        Parameters:
        byte (int): Byte index (0..n)
        bit (int): Bit position within the byte (0..7)

        Returns:
        int: 0 or 1 if successful, -1 on error

        Example:
        q1 = byte:0 bit:0 // q10 = byte:1 bit:1, ...
        """
        if 0 <= bit < 8:
            address = f"V{byte+1064}.{bit}"
            data = self.logo.read(address)
            return int(bool(data))
        return -1

    def SetAI(self, byte: int, value: int) -> int:
        """
        Set an analog input (AI) value via byte.

        Parameters:
        byte (int): Byte index
        value (int): Analog value (0–65535)

        Returns:
        int: Value set, -1 on error
        """
        if byte >= 0:
            val = int(value) & 0xFFFF
            address = f"VW{byte+1032}"
            self.logo.write(address, val)
            return val
        return -1

    def GetAO(self, byte: int) -> int:
        """
        Read an analog output (AO) value via byte.

        Parameters:
        byte (int): Byte index (must be even, 2 bytes per AO)

        Returns:
        int: Analog output value, -1 on error
        """
        if byte % 2 == 0:
            address = f"VW{byte+1072}"
            data = self.logo.read(address)
            return int(data)
        return -1

    def resetSendInputs(self):
        """
        Reset all V memory (inputs) to 0.
        """
        for byte in range(1024, 1468):
            self.logo.write(f"VW{byte}", 0)
