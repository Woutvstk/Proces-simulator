from configuration import configuration as mainConfigClass
from tankSim.configurationTS import configuration as configurationClass
from tankSim.status import status as statusClass
from plcCom.logoS7 import logoS7

class ioHandler:

    def mapValue(self, oldMin: int, oldMax: int, newMin: int, newMax: int, old: float) -> float:
        return round((old-oldMin)*(newMax-newMin)/(oldMax-oldMin)+newMin, 2)

    def updateIO(self, plc: logoS7, mainConfig: mainConfigClass, config: configurationClass, status: statusClass):
        """
        Bidirectionele IO:
        - PLC mode: lees PLC outputs → schrijf naar status
        - ALTIJD: schrijf status → PLC inputs (sensoren)
        """
        if (mainConfig.plcGuiControl == "plc"):
            # === LEES PLC OUTPUTS (actuatoren) ===
            # Valve In - check digital first, then analog
            if (plc.GetDO(config.DQValveIn["byte"], config.DQValveIn["bit"])):
                status.valveInOpenFraction = float(1)
            else:
                status.valveInOpenFraction = self.mapValue(
                    0, plc.analogMax, 0, 1, plc.GetAO(config.AQValveInFraction["byte"]))
            
            # Valve Out - check digital first, then analog
            if (plc.GetDO(config.DQValveOut["byte"], config.DQValveOut["bit"])):
                status.valveOutOpenFraction = 1
            else:
                status.valveOutOpenFraction = self.mapValue(
                    0, plc.analogMax, 0, 1, plc.GetAO(config.AQValveOutFraction["byte"]))
            
            # Heater - check digital first, then analog
            if (plc.GetDO(config.DQHeater["byte"], config.DQHeater["bit"])):
                status.heaterPowerFraction = 1
            else:
                status.heaterPowerFraction = self.mapValue(
                    0, plc.analogMax, 0, 1, plc.GetAO(config.AQHeaterFraction["byte"]))
        
        # === ALTIJD SCHRIJF NAAR PLC INPUTS (sensoren) ===
        # Dit gebeurt ongeacht of we in GUI of PLC mode zitten
        plc.SetDI(config.DILevelSensorHigh["byte"],
                  config.DILevelSensorHigh["bit"], status.digitalLevelSensorHighTriggered)
        plc.SetDI(config.DILevelSensorLow["byte"],
                  config.DILevelSensorLow["bit"], status.digitalLevelSensorLowTriggered)
        plc.SetAI(config.AILevelSensor["byte"],
                  int(self.mapValue(0, config.tankVolume, 0, plc.analogMax, status.liquidVolume)))
        plc.SetAI(config.AITemperatureSensor["byte"],
                  int(self.mapValue(-50, 250, 0, plc.analogMax, status.liquidTemperature)))

    def resetOutputs(self, mainConfig: mainConfigClass, config: configurationClass, status: statusClass):
        """Reset actuatoren bij verloren PLC verbinding"""
        if (mainConfig.plcGuiControl == "plc"):
            status.valveInOpenFraction = float(0)
            status.valveOutOpenFraction = float(0)
            status.heaterPowerFraction = float(0)