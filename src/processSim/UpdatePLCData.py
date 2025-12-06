from processSim.configuration import configurationClass 
from processSim.status import statusClass


plcAnalogMax = 32767
class updateDataClass:

    def mapValue(self, oldMin: int, oldMax: int, newMin: int, newMax: int, old: float) -> float:
        return round((old-oldMin)*(newMax-newMin)/(oldMax-oldMin)+newMin,2)
    
    def updateData(self,plc,config: configurationClass, status: statusClass):
            if not plc.isConnected(): #prevents writing to non existing adresses
                return
            if (config.plcGuiControl == "plc"):
                if (plc.GetDO(config.DQValveIn["byte"],config.DQValveIn["bit"])):  # if DQ valveIn = 1, ignore analog setpoint
                    status.valveInOpenFraction = float(1)
                else:
                    status.valveInOpenFraction = self.mapValue(
                        0, plcAnalogMax, 0, 1, plc.GetAO(config.AQValveInFraction["byte"]))

                if (plc.GetDO(config.DQValveOut["byte"],config.DQValveOut["bit"])):  # if DQ valveOut = 1, ignore analog setpoint
                    status.valveOutOpenFraction = 1
                else:
                    status.valveOutOpenFraction = self.mapValue(
                        0, plcAnalogMax, 0, 1, plc.GetAO(config.AQValveOutFraction["byte"]))

                if (plc.GetDO(config.DQHeater["byte"],config.DQHeater["bit"] )):  # if DQ heater = 1, ignore analog setpoint
                    status.heaterPowerFraction = 1
                else:
                    status.heaterPowerFraction = plc.GetAO(config.AQHeaterFraction["byte"])

                # always set PLC inputs even if gui controls process
                plc.SetDI(config.DILevelSensorHigh["byte"],
                        config.DILevelSensorHigh["bit"],status.digitalLevelSensorHighTriggered)
                plc.SetDI(config.DILevelSensorLow["byte"],
                        config.DILevelSensorLow["bit"],status.digitalLevelSensorLowTriggered)
                plc.SetAI(config.AILevelSensor["byte"], 
                        self.mapValue(0, config.tankVolume, 0, plcAnalogMax, status.liquidVolume))
                plc.SetAI(config.AITemperatureSensor["byte"], 
                        self.mapValue(-50, 250,0, plcAnalogMax, status.liquidTemperature))

    def resetOutputs(self, config: configurationClass, status: statusClass):
        # only update status if controller by plc
        if (config.plcGuiControl == "plc"):
            status.valveInOpenFraction = float(0)
            status.valveOutOpenFraction = float(0)
            status.heaterPowerFraction = float(0)