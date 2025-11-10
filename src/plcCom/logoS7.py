import snap7

plcAnalogMax = 32767

""" continued with the byte, bit structure for program compatebility, 
   due to the different mapping in logo we get now :
   i1 = byte:0 bit :0 // i10 = byte:1 bit :1,..."""


def mapValue(oldMin: int, oldMax: int, newMin: int, newMax: int, old: float) -> float:
    return (old - oldMin) * (newMax - newMin) / (oldMax - oldMin) + newMin


class logoS7:
    """Class for communication with a Siemens LOGO PLC using Snap7"""

    def __init__(self, ip: str, tsapLogo: int, tsapServer: int, tcpport: int = 102):
        self.ip = ip
        self.tsapLogo = tsapLogo
        self.tsapServer = tsapServer
        self.tcpport = tcpport
        self.logo = snap7.logo.Logo()

    def connect(self):
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
        if self.logo.get_connected():
            self.logo.disconnect()

    def isConnected(self) -> bool:
        return self.logo.get_connected()

    def SetDI(self, byte: int, bit: int, value: bool):
        """
        Sets a digital input (DI) via byte and bit.
        byte: 0..n  | bit: 0..7

        example:
        i1 = byte:0 bit :0 // i10 = byte:1 bit :1,..."""

        if 0 <= bit < 8:
            address = f"V{byte+1024}.{bit}"
            self.logo.write(address, int(bool(value)))
            return int(bool(value))
        return 0

    def GetDO(self, byte: int, bit: int):
        """
        Lees een digitale output (DO) via byte en bit.
        byte: 0..n  | bit: 0..7
        example:
        q1 = byte:0 bit :0 // q10 = byte:1 bit :1,...
        """
        if 0 <= bit < 8:
            address = f"V{byte+1064}.{bit}"
            data = self.logo.read(address)
            return int(bool(data))
        return 0

    def SetAI(self, byte: int, value: int):
        """
        Zet een analoge input (AI) via byte."""
        if byte >= 0:
            val = int(value) & 0xFFFF
            address = f"VW{byte+1032}"
            self.logo.write(address, val)
            return val
        return 0

    def GetAO(self, byte: int):
        """
        Lees een analoge output (AO) via byte.
        Elke AO = 2 bytes => byte moet even zijn.
        """
        if byte % 2 == 0:
            address = f"VW{byte+1072}"
            data = self.logo.read(address)
            return int(data)
        return 0

    def resetSendInputs(self):
        """Reset alle V geheugen naar 0"""
        for byte in range(1024, 1468):
            self.logo.write(f"VW{byte}", 0)
