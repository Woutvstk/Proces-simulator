import snap7
import snap7.util as s7util


class logoS7:
    """
    Class for communication with a Siemens LOGO PLC using Snap7.

    This class provides bit- and word-level access for digital and analog I/O,
    compatible with the LOGO memory structure.
    """

    def __init__(self, ip: str, tsapLogo: int, tsapServer: int, tcpport: int = 102):
        """
        Initialize the LOGO client with IP, TSAP parameters and TCP port.

        Parameters:
        ip (str): IP address of the LOGO PLC
        tsapLogo (int): TSAP address of the LOGO PLC
        tsapServer (int): TSAP address of the local server
        tcpport (int): TCP port for the connection (default: 102)
        """
        try:
            self.ip = ip
            self.tsapLogo = tsapLogo
            self.tsapServer = tsapServer
            self.tcpport = tcpport
            self.logo = snap7.logo.Logo()
        except Exception as e:
            print(f"__init__ error: {e}")

    def connect(self,instance_name: str | None = None) -> bool:
        """
        Connect to the LOGO PLC.

        Returns:
        bool: True if connected successfully, False otherwise.
        """
        try:
            self.logo.connect(self.ip, self.tsapLogo, self.tsapServer)
            if self.logo.get_connected():
                print(f"Connected to LOGO PLC at {self.ip}:{self.tcpport}")
                return True
            else:
                print(f"Cannot connect to LOGO PLC at {self.ip}")
                return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def disconnect(self):
        """
        Disconnect from the LOGO PLC if the connection is active.
        """
        try:
            if self.logo.get_connected():
                self.logo.disconnect()
                print("Disconnected from LOGO PLC.")
        except Exception as e:
            print(f"Disconnect() error: {e}")

    def isConnected(self) -> bool:
        """
        Check if the connection to the LOGO PLC is alive.

        Returns:
        bool: True if connected, False otherwise.
        """
        try:
            return self.logo.get_connected()
        except Exception as e:
            print(f"isConnected() error: {e}")
            return False

    def SetDI(self, byte: int, bit: int, value: bool) -> int:
        """
        Set a digital input (DI) bit in the LOGO V-memory.

        Parameters:
        byte (int): Byte index (0–n)
        bit (int): Bit index (0–7)
        value (bool): True/False or 1/0 to set or clear the bit

        Returns:
        int: 1 or 0 if successful, -1 on error
        """
        try:
            if 0 <= bit < 8:
                address = f"V{byte}.{bit}"
                self.logo.write(address, int(bool(value)))
                return int(bool(value))
            return -1
        except Exception as e:
            print(f"SetDI() error at byte {byte}, bit {bit}: {e}")
            return -1

    def GetDO(self, byte: int, bit: int) -> int:
        """
        Read a digital output (DO) bit from the LOGO V-memory.

        Parameters:
        byte (int): Byte index (0–n)
        bit (int): Bit index (0–7)

        Returns:
        int: 1 or 0 if successful, -1 on error
        """
        try:
            if 0 <= bit < 8:
                address = f"V{byte + 1064}.{bit}"
                data = self.logo.read(address)
                return int(bool(data))
            return -1
        except Exception as e:
            print(f"GetDO() error at byte {byte}, bit {bit}: {e}")
            return -1

    def SetAI(self, byte: int, value: int) -> int:
        """
        Set an analog input (AI) value in the LOGO V-memory.

        Parameters:
        byte (int): Starting byte index
        value (int): 16-bit unsigned integer (0–65535)

        Returns:
        int: Value written, -1 on error
        """
        try:
            if byte >= 0:
                val = int(value) & 0xFFFF
                address = f"VW{byte}"
                self.logo.write(address, val)
                return val
            return -1
        except Exception as e:
            print(f"SetAI() error at byte {byte}: {e}")
            return -1

    def GetAO(self, byte: int) -> int:
        """
        Read an analog output (AO) value from the LOGO V-memory.

        Parameters:
        byte (int): Starting byte index (must be even)

        Returns:
        int: 16-bit unsigned integer, -1 on error
        """
        try:
            if byte % 2 == 0:
                address = f"VW{byte + 1072}"
                data = self.logo.read(address)
                return int(data)
            return -1
        except Exception as e:
            print(f"GetAO() error at byte {byte}: {e}")
            return -1

    def resetSendInputs(self, startByte: int, endByte: int) -> bool:
        """
        Reset all V-memory inputs (DI, AI) to 0 within the specified range.

        Parameters:
        startByte (int): Start byte index
        endByte (int): End byte index

        Returns:
        bool: True if successful, False otherwise
        """
        try:
            for byte in range(startByte, endByte + 1):
                address = f"VW{byte}"
                self.logo.write(address, 0)
            return True
        except Exception as e:
            print(f"resetSendInputs() error: {e}")
            return False
