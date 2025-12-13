from configuration import configuration as mainConfigClass
from tankSim.configurationTS import configuration as configurationClass
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
        Bidirectional IO with force support:
        - PLC mode: read PLC outputs and write to status (WITH FORCE OVERRIDE)
        - GUI mode: use forced values for simulator inputs
        - ALWAYS: write status to PLC inputs (sensors)
        - Force values have priority when writing to PLC inputs AND reading outputs
        
        Args:
            forced_values: Dict with {attr_name: forced_value} for forced values
        """
        if forced_values is None:
            forced_values = {}
        
        # Reset flag when connection is restored
        if mainConfig.plcGuiControl == "plc":
            self.outputs_reset = False
        
        # Debug force changes
        if forced_values != self.last_forced_values:
            if forced_values:
                print(f"FORCE ACTIVE: {forced_values}")
            else:
                print("Force cleared")
            self.last_forced_values = forced_values.copy()
        
        self.debug_counter += 1
        debug_this_cycle = (self.debug_counter % 50 == 0)
        
        # Read PLC outputs (actuators) with force override
        
        # Valve In
        if "DQValveIn" in forced_values:
            status.valveInOpenFraction = float(1 if forced_values["DQValveIn"] else 0)
            if debug_this_cycle:
                print(f"   ValveIn FORCED: {status.valveInOpenFraction}")
        elif "AQValveInFraction" in forced_values:
            status.valveInOpenFraction = self.mapValue(0, plc.analogMax, 0, 1, forced_values["AQValveInFraction"])
            if debug_this_cycle:
                print(f"   ValveInFraction FORCED: {status.valveInOpenFraction}")
        elif (mainConfig.plcGuiControl == "plc"):
            if (plc.GetDO(config.DQValveIn["byte"], config.DQValveIn["bit"])):
                status.valveInOpenFraction = float(1)
            else:
                status.valveInOpenFraction = self.mapValue(
                    0, plc.analogMax, 0, 1, plc.GetAO(config.AQValveInFraction["byte"]))
        
        # Valve Out
        if "DQValveOut" in forced_values:
            status.valveOutOpenFraction = float(1 if forced_values["DQValveOut"] else 0)
            if debug_this_cycle:
                print(f"   ValveOut FORCED: {status.valveOutOpenFraction}")
        elif "AQValveOutFraction" in forced_values:
            status.valveOutOpenFraction = self.mapValue(0, plc.analogMax, 0, 1, forced_values["AQValveOutFraction"])
            if debug_this_cycle:
                print(f"   ValveOutFraction FORCED: {status.valveOutOpenFraction}")
        elif (mainConfig.plcGuiControl == "plc"):
            if (plc.GetDO(config.DQValveOut["byte"], config.DQValveOut["bit"])):
                status.valveOutOpenFraction = 1
            else:
                status.valveOutOpenFraction = self.mapValue(
                    0, plc.analogMax, 0, 1, plc.GetAO(config.AQValveOutFraction["byte"]))
        
        # Heater
        if "DQHeater" in forced_values:
            status.heaterPowerFraction = float(1 if forced_values["DQHeater"] else 0)
            if debug_this_cycle:
                print(f"   Heater FORCED: {status.heaterPowerFraction}")
        elif "AQHeaterFraction" in forced_values:
            status.heaterPowerFraction = self.mapValue(0, plc.analogMax, 0, 1, forced_values["AQHeaterFraction"])
            if debug_this_cycle:
                print(f"   HeaterFraction FORCED: {status.heaterPowerFraction}")
        elif (mainConfig.plcGuiControl == "plc"):
            if (plc.GetDO(config.DQHeater["byte"], config.DQHeater["bit"])):
                status.heaterPowerFraction = 1
            else:
                status.heaterPowerFraction = self.mapValue(
                    0, plc.analogMax, 0, 1, plc.GetAO(config.AQHeaterFraction["byte"]))
        
        # Write forced output values back to PLC
        
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
        
        # Always write to PLC inputs (sensors) with force support
        
        # Digital Level Sensor High
        if "DILevelSensorHigh" in forced_values:
            value = bool(forced_values["DILevelSensorHigh"])
            if debug_this_cycle:
                print(f"   DILevelSensorHigh FORCED: {value} @ {config.DILevelSensorHigh}")
        else:
            value = status.digitalLevelSensorHighTriggered
        
        plc.SetDI(config.DILevelSensorHigh["byte"],
                  config.DILevelSensorHigh["bit"], value)
        
        # Digital Level Sensor Low
        if "DILevelSensorLow" in forced_values:
            value = bool(forced_values["DILevelSensorLow"])
            if debug_this_cycle:
                print(f"   DILevelSensorLow FORCED: {value} @ {config.DILevelSensorLow}")
        else:
            value = status.digitalLevelSensorLowTriggered
        
        plc.SetDI(config.DILevelSensorLow["byte"],
                  config.DILevelSensorLow["bit"], value)
        
        # Analog Level Sensor
        if "AILevelSensor" in forced_values:
            value = int(forced_values["AILevelSensor"])
            if debug_this_cycle:
                print(f"   AILevelSensor FORCED: {value} @ byte {config.AILevelSensor['byte']}")
        else:
            value = int(self.mapValue(0, config.tankVolume, 0, plc.analogMax, status.liquidVolume))
            if debug_this_cycle:
                print(f"   AILevelSensor: vol={status.liquidVolume:.1f}mm -> PLC={value} @ byte {config.AILevelSensor['byte']}")
        
        plc.SetAI(config.AILevelSensor["byte"], value)
        
        # Analog Temperature Sensor
        if "AITemperatureSensor" in forced_values:
            value = int(forced_values["AITemperatureSensor"])
            if debug_this_cycle:
                print(f"   AITemperatureSensor FORCED: {value} @ byte {config.AITemperatureSensor['byte']}")
        else:
            value = int(self.mapValue(-50, 250, 0, plc.analogMax, status.liquidTemperature))
            if debug_this_cycle:
                print(f"   AITemperatureSensor: temp={status.liquidTemperature:.1f}C -> PLC={value} @ byte {config.AITemperatureSensor['byte']}")
        
        plc.SetAI(config.AITemperatureSensor["byte"], value)

    def resetOutputs(self, mainConfig: mainConfigClass, config: configurationClass, status: statusClass):
        """Reset actuators when PLC connection is lost"""
        if (mainConfig.plcGuiControl == "plc"):
            status.valveInOpenFraction = float(0)
            status.valveOutOpenFraction = float(0)
            status.heaterPowerFraction = float(0)
            
            if not self.outputs_reset:
                print("PLC outputs reset (no connection)")
                self.outputs_reset = True