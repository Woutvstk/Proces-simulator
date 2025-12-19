import snap7
import snap7.util as s7util


class plcS7:
    """Class for communication with a Siemens S7 PLC using Snap7."""
    analogMax = 32767  # Max value for signed 16-bit integer

    def __init__(self, ip: str, rack: int, slot: int, tcpport: int = 102):
        """
        Initialize the PLC client with IP, rack, slot, and TCP port.

        Parameters:
        ip (str): IP address of the PLC
        rack (int): Rack number of the PLC
        slot (int): Slot number of the PLC
        tcpport (int): TCP port for the connection (default: 102)
        """
        self.ip = ip
        self.rack = rack
        self.slot = slot
        self.tcpport = tcpport
        self.client = snap7.client.Client()

    def connect(self, instance_name: str | None = None) -> bool:
        """
        Connect to the PLC.

        Returns:
        bool: True if connected successfully, False otherwise.
        """
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
            # Try different slots in case of an S7-400/300
            for i in range(0, 2):
                try:
                    self.client.connect(self.ip, self.rack, i, self.tcpport)
                    print(
                        f"Connected to S7 PLC at {self.ip}:{self.tcpport} (rack {self.rack}, slot {i})")
                    return True
                except Exception:
                    continue
            print("Connection error:", e)
            return False

    def disconnect(self) -> bool:
        """
        Disconnect from the PLC if the connection is active.
        """
        try:
            if self.client.get_connected():
                self.client.disconnect()
            return True
        except:
            return False

    def isConnected(self) -> bool:
        """
        Check if the connection to the PLC is alive.

        Returns:
        bool: True if connected, False otherwise.
        """
        if not self.client.get_connected():
            print("Connection lost to the PLC!")
            return False
        return True

    def SetDI(self, byte: int, bit: int, value: int) -> int:
        """
        Set a digital input (DI) bit in the PLC input process image.

        Parameters:
        byte (int): Byte index in the PLC input area (E/I)
        bit (int): Bit position (0–7) within the byte
        value (int): 1/0 or True/False to set or clear the bit

        Returns:
        int: The value set (1/0), -1 on error
        """
        if self.isConnected():
            if byte >= 0 and 0 <= bit <= 7:
                try:
                    current_data = self.client.eb_read(start=byte, size=1)
                    buffer_DI = bytearray(current_data)
                    if value:
                        buffer_DI[0] |= (1 << bit)
                    else:
                        buffer_DI[0] &= ~(1 << bit)
                    self.client.eb_write(start=byte, size=1, data=buffer_DI)
                    return int(bool(value))
                except Exception as e:
                    print("Error:", e)
                    return -1
            return -1
        return -1

    def GetDO(self, byte: int, bit: int) -> int:
        """
        Read a digital output (DO) bit from the PLC output process image.

        Parameters:
        byte (int): Byte index in the PLC output area (A/Q)
        bit (int): Bit position (0–7) within the byte

        Returns:
        int: 0 or 1 if successful, -1 on error
        """
        if self.isConnected():
            if byte >= 0 and 0 <= bit <= 7:
                try:
                    data = self.client.ab_read(byte, 1)
                    return int(s7util.get_bool(data, 0, bit))
                except Exception as e:
                    print("Error:", e)
                    return -1
            return -1
        return -1

    def SetAI(self, startByte: int, value: int) -> int:
        """
        Set an analog input (AI) value as a 16-bit UNSIGNED INTEGER in the PLC input process image.

        Parameters:
        startByte (int): Byte index in the PLC input area (E/I)
        value (int | float): Analog value (0–65535)

        Returns:
        int: Value set, -1 on error
        """
        if self.isConnected():
            if startByte >= 0 and 0 <= value <= 65535:
                try:
                    buffer_AI = bytearray(2)
                    val_int = int(round(value)) if isinstance(
                        value, float) else int(value)
                    lowByte = val_int & 0xFF
                    highByte = (val_int >> 8) & 0xFF
                    buffer_AI[0] = highByte
                    buffer_AI[1] = lowByte
                    self.client.eb_write(
                        start=startByte, size=2, data=buffer_AI)
                    return val_int
                except Exception as e:
                    print("Error:", e)
                    return -1
            return -1
        return -1

    def GetAO(self, startByte: int) -> int:
        """
        Read an analog output (AO) value as a 16-bit SIGNED INTEGER from the PLC output process image.

        Parameters:
        startByte (int): Byte index in the PLC output area (A/Q)

        Returns:
        int: Signed 16-bit value (-32768–32767), -1 on error
        """
        if self.isConnected():
            if startByte >= 0:
                try:
                    data = self.client.ab_read(start=startByte, size=2)
                    return s7util.get_int(data, 0)
                except Exception as e:
                    print("Error:", e)
                    return -1
            return -1
        return -1

    def SetDO(self, byte: int, bit: int, value: int) -> int:
        """
        Set a digital output (DO) bit in the PLC output process image.

        Parameters:
        byte (int): Byte index in the PLC output area (A/Q)
        bit (int): Bit position (0–7) within the byte
        value (int): 1/0 or True/False to set or clear the bit

        Returns:
        int: The value set (1/0), -1 on error
        """
        if self.isConnected():
            if byte >= 0 and 0 <= bit <= 7:
                try:
                    current_data = self.client.ab_read(start=byte, size=1)
                    buffer_DO = bytearray(current_data)
                    if value:
                        buffer_DO[0] |= (1 << bit)
                    else:
                        buffer_DO[0] &= ~(1 << bit)
                    self.client.ab_write(start=byte, data=buffer_DO)
                    return int(bool(value))
                except Exception as e:
                    print(f"SetDO error: {e}")
                    return -1
            return -1
        return -1

    def SetAO(self, startByte: int, value: int) -> int:
        """
        Set an analog output (AO) value as a 16-bit SIGNED INTEGER in the PLC output process image.

        Parameters:
        startByte (int): Byte index in the PLC output area (A/Q)
        value (int | float): Analog value (-32768–32767)

        Returns:
        int: Value set, -1 on error
        """
        if self.isConnected():
            if startByte >= 0 and -32768 <= value <= 32767:
                try:
                    buffer_AO = bytearray(2)
                    val_int = int(round(value)) if isinstance(
                        value, float) else int(value)

                    # Convert to signed 16-bit and then to bytes (Big Endian)
                    if val_int < 0:
                        val_int = val_int & 0xFFFF  # Two's complement

                    lowByte = val_int & 0xFF
                    highByte = (val_int >> 8) & 0xFF
                    buffer_AO[0] = highByte
                    buffer_AO[1] = lowByte

                    self.client.ab_write(start=startByte, data=buffer_AO)
                    return val_int
                except Exception as e:
                    print(f"SetAO error: {e}")
                    return -1
            return -1
        return -1

    def resetSendInputs(self, startByte: int, endByte: int) -> bool:
        """
        Reset all input data sent to the PLC (DI, AI).

        Parameters:
        startByte (int): Start byte index to reset
        endByte (int): End byte index to reset

        Returns:
        bool: True if successful, False otherwise
        """
        if self.isConnected():
            if startByte >= 0 and endByte > startByte:
                try:
                    bufferEmpty = bytearray(endByte - startByte + 1)
                    self.client.eb_write(start=startByte, size=(
                        endByte - startByte + 1), data=bufferEmpty)
                    return True
                except Exception as e:
                    print("Error:", e)
                    return False
            return False
        return False

    def resetSendOutputs(self, startByte: int, endByte: int) -> bool:
        """
        Reset all output data sent to the PLC (DO, AO) by writing zeros.

        Parameters:
        startByte (int): Start byte index to reset
        endByte (int): End byte index to reset

        Returns:
        bool: True if successful, False otherwise
        """
        if self.isConnected():
            if startByte >= 0 and endByte >= startByte:
                try:
                    size = endByte - startByte + 1
                    bufferEmpty = bytearray(size)
                    self.client.ab_write(start=startByte, data=bufferEmpty)
                    print(f"Output area reset: bytes {startByte}-{endByte}")
                    return True
                except Exception as e:
                    print(f"resetSendOutputs error: {e}")
                    return False
            return False
        return False
