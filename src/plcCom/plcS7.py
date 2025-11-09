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
        """Connect to the PLC, returns "true" if connected"""
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
        """check if the connection is alive, connected returns "true" """
        if not self.client.get_connected():
            print("Connection lost to the PLC!")
            return False
        else:
            return True

    def SetDI(self, byte: int, bit: int, value: int):
        """
        Set a digital input (DI) bit in the PLC input process image (E/I area).

        byte: selects which input byte in the PLC is used, as defined by the GUI  
        bit: bit position (0–7) within the selected byte  
        value: True/False or 1/0 to set or clear the bit
        """
        buffer_DI = bytearray(2)
        if byte >= 0:
            if 7 >= bit >= 0:
                if value:  # if the value is > 0
                    # shift binary 1 by bit index, e.g. (1 << 3) = 00001000
                    buffer_DI[0] |= (1 << bit)
                else:
                    # invert bit mask, e.g. ~(1 << 3) = 11110111
                    buffer_DI[0] &= ~(1 << bit)
                self.client.eb_write(start=byte, size=1, data=buffer_DI)
                return int(bool(value))
        return -1

    def GetDO(self, byte: int, bit: int):
        """
        Read a digital output (DO) bit from the PLC output process image (A/Q area).

        byte: selects which output byte in the PLC is used, as defined by the GUI  
        bit: bit position (0–7) within the selected byte
        """
        if byte >= 0:
            if 7 >= bit >= 0:
                data = self.client.ab_read(byte, 1)
                return int(s7util.get_bool(data, 0, bit))
        return -1

    def SetAI(self, byte: int, value: int):
        """
        Set an analog input (AI) value as a 16-bit UNSIGNED INTEGER (0–65535) in the PLC input process image (E/I area).

        byte: selects which input byte in the PLC is used, as defined by the GUI  
        value: 0–65535 (word)
        """
        buffer_AI = bytearray(32)
        if byte >= 0:
            if 0 <= value <= 65535:
                lowByte = value & 0xFF  # 0xFF = mask for one byte (0b11111111)
                highByte = (value >> 8) & 0xFF
                buffer_AI[0] = highByte
                buffer_AI[1] = lowByte
                self.client.eb_write(start=byte, size=2, data=buffer_AI)
                return int(value)
            return -1
        return -1

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

    def resetSendInputs(self, startByte: int, endByte: int):
        """
        Resets all send input data to the PLC (DI, AI)
        """
        bufferEmpty = bytearray(2)
        self.client.eb_write(start=startByte, size=endByte, data=bufferEmpty)
        self.client.ab_write(start=startByte, size=endByte, data=bufferEmpty)
