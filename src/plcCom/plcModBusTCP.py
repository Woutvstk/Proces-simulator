from pymodbus.client import ModbusTcpClient
from configuration import configurationClass
from status import statusClass

plcAnalogMax = 32767


def mapValue(oldMin: int, oldMax: int, newMin: int, newMax: int, old: float) -> float:
    return (old - oldMin) * (newMax - newMin) / (oldMax - oldMin) + newMin


class plcModBusTCP:
    """
    Class for Modbus TCP communication with a PLC.
    Works with bytes and bits like plcS7, while keeping register-based functionality.
    """

    def __init__(self, ip: str, port: int = 502):
        self.ip = ip
        self.port = port
        self.client = None

    def connect(self):
        """Connect to the Modbus server"""
        self.client = ModbusTcpClient(self.ip, port=self.port)
        if self.client.connect():
            print(f"Connected to Modbus server {self.ip}:{self.port}")
            return True
        else:
            print(f"Cannot connect to Modbus server {self.ip}:{self.port}")
            return False

    def disconnect(self):
        """Disconnect from the Modbus server"""
        if self.client:
            self.client.close()

    def isConnected(self) -> bool:
        """Check if connection is alive"""
        if self.client is None or not self.client.is_socket_open():
            print("Connection lost to the PLC!")
            return False
        return True

    def SetDI(self, byte: int, bit: int, value: int):
        """
        Set a digital input (DI) bit in the PLC register map.
        byte: selects Modbus register (0–15)
        bit: bit position (0–7)
        value: True/False or 1/0
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

    def GetDO(self, byte: int, bit: int):
        """
        Read a digital output (DO) bit from Modbus coils.
        byte: selects coil byte
        bit: bit position (0–7)
        """
        self.isConnected()
        if byte >= 0 and 0 <= bit <= 7:
            coil_start = byte * 8
            rr = self.client.read_coils(coil_start, count=8)
            if rr.isError():
                return -1
            return int(rr.bits[bit])
        return -1

    def SetAI(self, byte: int, value: int):
        """
        Set an analog input (AI) value (16-bit unsigned) in Modbus registers.
        byte: Modbus register address (16–31 typical)
        value: 0–65535
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
        byte: Modbus register address (typically 32+)
        """
        self.isConnected()
        if byte >= 0:
            rr = self.client.read_holding_registers(byte + 32, count=1)
            if rr.isError():
                return None
            return rr.registers[0]
        return None

    def updateData(self, config: configurationClass, status: statusClass):
        # Only update if PLC controls process
        if config.plcGuiControl == "plc":
            if self.GetDO(config.DQValveIn["byte"], config.DQValveIn["bit"]):
                status.valveInOpenFraction = float(1)
            else:
                status.valveInOpenFraction = mapValue(
                    0, plcAnalogMax, 0, 1, self.GetAO(config.AQValveInFraction))

            if self.GetDO(config.DQValveOut["byte"], config.DQValveOut["bit"]):
                status.valveOutOpenFraction = 1
            else:
                status.valveOutOpenFraction = mapValue(
                    0, plcAnalogMax, 0, 1, self.GetAO(config.AQValveOutFraction))

            if self.GetDO(config.DQHeater["byte"], config.DQHeater["bit"]):
                status.heaterPowerFraction = 1
            else:
                status.heaterPowerFraction = self.GetAO(
                    config.AQHeaterFraction)

        # Always send process inputs to PLC
        self.SetDI(config.DILevelSensorHigh["byte"], config.DILevelSensorHigh["bit"],
                   status.digitalLevelSensorHighTriggered)
        self.SetDI(config.DILevelSensorLow["byte"], config.DILevelSensorLow["bit"],
                   status.digitalLevelSensorLowTriggered)
        self.SetAI(config.AILevelSensor, mapValue(
            0, config.tankVolume, 0, plcAnalogMax, status.liquidVolume))
        self.SetAI(config.AITemperatureSensor, mapValue(
            -50, 250, 0, plcAnalogMax, status.liquidTemperature))

    def resetOutputs(self, config: configurationClass, status: statusClass):
        """Reset process inputs when PLC control active"""
        if config.plcGuiControl == "plc":
            status.valveInOpenFraction = float(0)
            status.valveOutOpenFraction = float(0)
            status.heaterPowerFraction = float(0)

    def reset_registers(self, start_byte: int = 0, end_byte: int = 48):
        """Reset all Modbus registers in range to 0"""
        self.isConnected()
        for byte in range(start_byte, end_byte):
            self.client.write_register(byte, 0)
