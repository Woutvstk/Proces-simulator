import snap7
import snap7.util as s7util
from configuration import configurationClass
from status import statusClass

plcAnalogMax = 32767


def mapValue(oldMin: int, oldMax: int, newMin: int, newMax: int, old: float) -> float:
    return (old-oldMin)*(newMax-newMin)/(oldMax-oldMin)+newMin


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

    def updateData(self, config: configurationClass, status: statusClass):
        # only update status if controller by plc
        if (config.plcGuiControl == "plc"):
            if (self.GetDO(config.DQValveIn)):  # if DQ valveIn = 1, ignore analog setpoint
                status.valveInOpenFraction = float(1)
            else:
                status.valveInOpenFraction = mapValue(
                    0, plcAnalogMax, 0, 1, self.GetAO(config.AQValveInFraction))

            if (self.GetDO(config.DQValveOut)):  # if DQ valveOut = 1, ignore analog setpoint
                status.valveOutOpenFraction = 1
            else:
                status.valveOutOpenFraction = mapValue(
                    0, plcAnalogMax, 0, 1, self.GetAO(config.AQValveOutFraction))

            if (self.GetDO(config.DQHeater)):  # if DQ heater = 1, ignore analog setpoint
                status.heaterPowerFraction = 1
            else:
                status.heaterPowerFraction = self.GetAO(
                    config.AQHeaterFraction)

        # always set PLC inputs even if gui controls process
        self.SetDI(config.DILevelSensorHigh,
                   status.digitalLevelSensorHighTriggered)
        self.SetDI(config.DILevelSensorLow,
                   status.digitalLevelSensorLowTriggered)
        self.SetAI(config.AILevelSensor, mapValue(
            0, config.tankVolume, 0, plcAnalogMax, status.liquidVolume))
        self.SetAI(config.AITemperatureSensor, mapValue(-50, 250,
                   0, plcAnalogMax, status.liquidTemperature))

    def resetOutputs(self, config: configurationClass, status: statusClass):
        # only update status if controller by plc
        if (config.plcGuiControl == "plc"):
            status.valveInOpenFraction = float(0)
            status.valveOutOpenFraction = float(0)
            status.heaterPowerFraction = float(0)

    def reset_registers(self, db_number=10):
        """
        Reset all registers in the data block to 0.
        db_number: PLC data block
        """
        data = bytearray(68)  # create zeroed byte array for reset
        self.client.db_write(db_number, 0, data)
