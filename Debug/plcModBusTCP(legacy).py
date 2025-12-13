from pymodbus.client import ModbusTcpClient


class plcModBusTCP:
    """
    Class for Modbus TCP communication with a PLC.
    Works with bytes and bits like plcS7, while keeping register-based functionality.
    """

    def __init__(self, ip: str, port: int = 502):
        try:
            self.ip = ip
            self.port = port
            self.client = None
        except Exception as e:
            print("Error in __init__:", e)

        self.analogMax = 32767  # TODO correct to 27xxx

    def connect(self,instance_name: str | None = None) -> bool:
        try:
            self.client = ModbusTcpClient(self.ip, port=self.port)
            if self.client.connect():
                print(f"Connected to Modbus server {self.ip}:{self.port}")
                return True
            else:
                print(f"Cannot connect to Modbus server {self.ip}:{self.port}")
                return False
        except Exception as e:
            print("Error in connect:", e)
            return False

    def disconnect(self):
        try:
            if self.client:
                self.client.close()
        except Exception as e:
            print("Error in disconnect:", e)

    def isConnected(self) -> bool:
        try:
            if self.client is None or not self.client.is_socket_open():
                print("Connection lost to the PLC!")
                return False
            return True
        except Exception as e:
            print("Error in isConnected:", e)
            return False

    def SetDI(self, byte: int, bit: int, value: int) -> int:
        try:
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
        except Exception as e:
            print("Error in SetDI:", e)
            return -1

    def GetDO(self, byte: int, bit: int) -> int:
        try:
            self.isConnected()
            if byte >= 0 and 0 <= bit <= 7:
                coil_start = byte * 8
                rr = self.client.read_coils(coil_start, count=8)
                if rr.isError():
                    return -1
                return int(rr.bits[bit])
            return -1
        except Exception as e:
            print("Error in GetDO:", e)
            return -1

    def SetAI(self, byte: int, value: int) -> int:
        try:
            self.isConnected()
            if byte >= 0:
                value = int(value) & 0xFFFF
                high_byte = (value >> 8) & 0xFF
                low_byte = value & 0xFF
                word_value = (high_byte << 8) | low_byte
                self.client.write_register(byte, word_value)
                return value
            return -1
        except Exception as e:
            print("Error in SetAI:", e)
            return -1

    def GetAO(self, byte: int):
        try:
            self.isConnected()
            if byte >= 0:
                rr = self.client.read_holding_registers(byte + 32, count=1)
                if rr.isError():
                    return None
                return rr.registers[0]
            return None
        except Exception as e:
            print("Error in GetAO:", e)
            return None

    def resetSendInputs(self, start_byte: int = 0, end_byte: int = 48):
        try:
            self.isConnected()
            for byte in range(start_byte, end_byte):
                self.client.write_register(byte, 0)
        except Exception as e:
            print("Error in resetSendInputs:", e)
