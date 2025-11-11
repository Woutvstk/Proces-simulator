from pymodbus.client import ModbusTcpClient

class plcModBusTCP:
    """
    Class for Modbus TCP communication with a PLC.
    Works with bytes and bits like plcS7, while keeping register-based functionality.
    """

    def __init__(self, ip: str, port: int = 502):
        """
        Initialize the Modbus TCP client.

        Parameters:
        ip (str): IP address of the Modbus server
        port (int): TCP port (default: 502)
        """
        self.ip = ip
        self.port = port
        self.client = None

    def connect(self) -> bool:
        """Connect to the Modbus server and return True if successful."""
        self.client = ModbusTcpClient(self.ip, port=self.port)
        if self.client.connect():
            print(f"Connected to Modbus server {self.ip}:{self.port}")
            return True
        else:
            print(f"Cannot connect to Modbus server {self.ip}:{self.port}")
            return False

    def disconnect(self):
        """Disconnect from the Modbus server."""
        if self.client:
            self.client.close()

    def isConnected(self) -> bool:
        """Check if the connection to the Modbus server is alive."""
        if self.client is None or not self.client.is_socket_open():
            print("Connection lost to the PLC!")
            return False
        return True

    def SetDI(self, byte: int, bit: int, value: int) -> int:
        """
        Set a digital input (DI) bit in the PLC register map.

        Parameters:
        byte (int): Modbus register address (0–15)
        bit (int): Bit position within the register (0–7)
        value (int): True/False or 1/0 to set or clear the bit

        Returns:
        int: Value set (1/0), -1 on error
        """
        self.isConnected()
        if byte >= 0 and 0 <= bit <= 7:
            rr = self.client.read_holding_registers(byte, count=1)
            if rr.isError():
                return -1
            current_byte = rr.registers[0] & 0xFF

            if value:
                current_byte |= (1 << bit)
            else:
                current_byte &= ~(1 << bit)

            self.client.write_register(byte, current_byte)
            return int(bool(value))
        return -1

    def GetDO(self, byte: int, bit: int) -> int:
        """
        Read a digital output (DO) bit from Modbus coils.

        Parameters:
        byte (int): Coil byte address
        bit (int): Bit position within the byte (0–7)

        Returns:
        int: 0 or 1 if successful, -1 on error
        """
        self.isConnected()
        if byte >= 0 and 0 <= bit <= 7:
            coil_start = byte * 8
            rr = self.client.read_coils(coil_start, count=8)
            if rr.isError():
                return -1
            return int(rr.bits[bit])
        return -1

    def SetAI(self, byte: int, value: int) -> int:
        """
        Set an analog input (AI) value (16-bit unsigned) in Modbus registers.

        Parameters:
        byte (int): Modbus register address (16–31 typical)
        value (int): Analog value (0–65535)

        Returns:
        int: Value set, -1 on error
        """
        self.isConnected()
        if byte >= 0:
            value = int(value) & 0xFFFF
            high_byte = (value >> 8) & 0xFF
            low_byte = value & 0xFF
            word_value = (high_byte << 8) | low_byte
            self.client.write_register(byte, word_value)
            return value
        return -1

    def GetAO(self, byte: int):
        """
        Read an analog output (AO) value (16-bit unsigned) from Modbus registers.

        Parameters:
        byte (int): Modbus register address (typically 32+)

        Returns:
        int: Value read from the register, None on error
        """
        self.isConnected()
        if byte >= 0:
            rr = self.client.read_holding_registers(byte + 32, count=1)
            if rr.isError():
                return None
            return rr.registers[0]
        return None

    def resetSendInputs(self, start_byte: int = 0, end_byte: int = 48):
        """
        Reset all Modbus registers in the specified range to 0.

        Parameters:
        start_byte (int): Starting register address (default 0)
        end_byte (int): Ending register address (default 48)
        """
        self.isConnected()
        for byte in range(start_byte, end_byte):
            self.client.write_register(byte, 0)
