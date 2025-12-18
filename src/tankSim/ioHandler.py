from configuration import configuration as mainConfigClass
from tankSim.configuration import configuration as configurationClass
from tankSim.status import status as statusClass
from plcCom.logoS7 import logoS7


class ioHandler:

    def __init__(self):
        self.debug_counter = 0
        self.last_forced_values = {}
        self.outputs_reset = False

    def mapValue(self, oldMin: int, oldMax: int, newMin: int, newMax: int, old: float) -> float:
        return round((old-oldMin)*(newMax-newMin)/(oldMax-oldMin)+newMin, 2)

    def updateIO(self, plc: logoS7, mainConfig: mainConfigClass, config: configurationClass,
             status: statusClass, forced_values: dict = None):
        """
        Bidirectional IO with force support
        """
        if forced_values is None:
            forced_values = {}

        if mainConfig.plcGuiControl == "plc":
            self.outputs_reset = False

        # Debug force changes
        if forced_values != self.last_forced_values:
            if forced_values:
                print(f"🔒 FORCE ACTIVE: {forced_values}")
            else:
                print("🔓 Force cleared")
            self.last_forced_values = forced_values.copy()

        self.debug_counter += 1
        debug_this_cycle = (self.debug_counter % 100 == 0)  # Every 100 cycles

        # =========================================================================
        # READ PLC OUTPUTS (actuators) → Write to status
        # =========================================================================

        # Valve In
        if "DQValveIn" in forced_values:
            status.valveInOpenFraction = float(1 if forced_values["DQValveIn"] else 0)
        elif "AQValveInFraction" in forced_values:
            status.valveInOpenFraction = self.mapValue(
                0, plc.analogMax, 0, 1, forced_values["AQValveInFraction"])
        elif (mainConfig.plcGuiControl == "plc"):
            dq_state = plc.GetDO(config.DQValveIn["byte"], config.DQValveIn["bit"])
            if dq_state == 1:
                status.valveInOpenFraction = float(1)
            else:
                aq_value = plc.GetAO(config.AQValveInFraction["byte"])
                status.valveInOpenFraction = self.mapValue(0, plc.analogMax, 0, 1, aq_value)

        # Valve Out  
        if "DQValveOut" in forced_values:
            status.valveOutOpenFraction = float(1 if forced_values["DQValveOut"] else 0)
        elif "AQValveOutFraction" in forced_values:
            status.valveOutOpenFraction = self.mapValue(
                0, plc.analogMax, 0, 1, forced_values["AQValveOutFraction"])
        elif (mainConfig.plcGuiControl == "plc"):
            dq_state = plc.GetDO(config.DQValveOut["byte"], config.DQValveOut["bit"])
            if dq_state == 1:
                status.valveOutOpenFraction = 1
            else:
                aq_value = plc.GetAO(config.AQValveOutFraction["byte"])
                status.valveOutOpenFraction = self.mapValue(0, plc.analogMax, 0, 1, aq_value)

        # Heater
        if "DQHeater" in forced_values:
            status.heaterPowerFraction = float(1 if forced_values["DQHeater"] else 0)
        elif "AQHeaterFraction" in forced_values:
            status.heaterPowerFraction = self.mapValue(
                0, plc.analogMax, 0, 1, forced_values["AQHeaterFraction"])
        elif (mainConfig.plcGuiControl == "plc"):
            dq_heater = plc.GetDO(config.DQHeater["byte"], config.DQHeater["bit"])
            aq_heater = plc.GetAO(config.AQHeaterFraction["byte"])
            
            # Priority: Digital ON = 100%, Digital OFF = use analog
            if dq_heater == 1:
                status.heaterPowerFraction = 1.0
            elif dq_heater == 0:
                if aq_heater > 0:
                    status.heaterPowerFraction = self.mapValue(0, plc.analogMax, 0, 1, aq_heater)
                else:
                    status.heaterPowerFraction = 0.0
            else:
                status.heaterPowerFraction = 0.0

        # =========================================================================
        # WRITE FORCED VALUES back to PLC outputs
        # =========================================================================
        
        if "DQValveIn" in forced_values:
            plc.SetDO(config.DQValveIn["byte"], config.DQValveIn["bit"], bool(forced_values["DQValveIn"]))
        if "AQValveInFraction" in forced_values:
            plc.SetAO(config.AQValveInFraction["byte"], int(forced_values["AQValveInFraction"]))

        if "DQValveOut" in forced_values:
            plc.SetDO(config.DQValveOut["byte"], config.DQValveOut["bit"], bool(forced_values["DQValveOut"]))
        if "AQValveOutFraction" in forced_values:
            plc.SetAO(config.AQValveOutFraction["byte"], int(forced_values["AQValveOutFraction"]))

        if "DQHeater" in forced_values:
            plc.SetDO(config.DQHeater["byte"], config.DQHeater["bit"], bool(forced_values["DQHeater"]))
        if "AQHeaterFraction" in forced_values:
            plc.SetAO(config.AQHeaterFraction["byte"], int(forced_values["AQHeaterFraction"]))

        # =========================================================================
        # WRITE TO PLC INPUTS (sensors) - Always write, with force support
        # =========================================================================

        # Digital Level Sensor High
        if "DILevelSensorHigh" in forced_values:
            value = bool(forced_values["DILevelSensorHigh"])
        else:
            value = status.digitalLevelSensorHighTriggered
        
        plc.SetDI(config.DILevelSensorHigh["byte"], config.DILevelSensorHigh["bit"], value)
        
        if debug_this_cycle:
            print(f"   📊 LevelHigh @ I{config.DILevelSensorHigh['byte']}.{config.DILevelSensorHigh['bit']} = {value}")

        # Digital Level Sensor Low
        if "DILevelSensorLow" in forced_values:
            value = bool(forced_values["DILevelSensorLow"])
        else:
            value = status.digitalLevelSensorLowTriggered
        
        plc.SetDI(config.DILevelSensorLow["byte"], config.DILevelSensorLow["bit"], value)
        
        if debug_this_cycle:
            print(f"   📊 LevelLow @ I{config.DILevelSensorLow['byte']}.{config.DILevelSensorLow['bit']} = {value}")

        # Analog Level Sensor
        if "AILevelSensor" in forced_values:
            value = int(forced_values["AILevelSensor"])
        else:
            value = int(self.mapValue(0, config.tankVolume, 0, plc.analogMax, status.liquidVolume))
        
        plc.SetAI(config.AILevelSensor["byte"], value)
        
        if debug_this_cycle:
            print(f"   📊 LevelSensor @ IW{config.AILevelSensor['byte']} = {value} (vol={status.liquidVolume:.1f})")

        # Analog Temperature Sensor
        if "AITemperatureSensor" in forced_values:
            value = int(forced_values["AITemperatureSensor"])
        else:
            value = int(self.mapValue(-50, 250, 0, plc.analogMax, status.liquidTemperature))
        
        plc.SetAI(config.AITemperatureSensor["byte"], value)
        
        if debug_this_cycle:
            print(f"   📊 TempSensor @ IW{config.AITemperatureSensor['byte']} = {value} (temp={status.liquidTemperature:.1f}°C)")


    def resetOutputs(self, mainConfig: mainConfigClass, config: configurationClass, status: statusClass):
        """Reset actuators when PLC connection is lost"""
        if (mainConfig.plcGuiControl == "plc"):
            status.valveInOpenFraction = float(0)
            status.valveOutOpenFraction = float(0)
            status.heaterPowerFraction = float(0)

            if not self.outputs_reset:
                print("PLC outputs reset (no connection)")
                self.outputs_reset = True
