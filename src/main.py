from processSim.tankSim import tankSim
from plcCom.plcModBusTCP import plcModBusTCP
from plcCom.plcS7 import plcS7
from plcCom.logoS7 import logoS7
import time
from configuration import configuration


"""Initialize configuration instance with default parameters"""
config = configuration()
"""Initialize process0 object"""


process0 = tankSim("process0", 2000, 200, 135, 10000, 250, 21)
process0.simStart()


validPlcConnection: bool = False


# remember at what time we started
startTime = time.time()

plcAnalogMax = 32767


def mapValue(oldMin: int, oldMax: int, newMin: int, newMax: int, old: float) -> float:
    return (old-oldMin)*(newMax-newMin)/(oldMax-oldMin)+newMin


def sendPlcOutToProcessAndUi():
    if (PlcCom.GetDO(config.DQValveIn)):  # if DQ valveIn = 1, ignore analog setpoint
        process0.valveInOpenFraction = 1
    else:
        process0.valveInOpenFraction = mapValue(
            0, plcAnalogMax, 0, 1, PlcCom.GetAO(config.AQValveInFraction))
    if (PlcCom.GetDO(config.DQValveOut)):  # if DQ valveOut = 1, ignore analog setpoint
        process0.valveOutOpenFraction = 1
    else:
        process0.valveOutOpenFraction = mapValue(
            0, plcAnalogMax, 0, 1, PlcCom.GetAO(config.AQValveOutFraction))
    if (PlcCom.GetDO(config.DQHeater)):  # if DQ heater = 1, ignore analog setpoint
        process0.heaterPowerFraction = 1
    else:
        process0.heaterPowerFraction = PlcCom.GetAO(config.AQHeaterFraction)


def sendProcessStatusToPlcInAndUi():
    PlcCom.SetDI(config.DILevelSensorHigh,
                 process0.digitalLevelSensorHighTriggered)
    PlcCom.SetDI(config.DILevelSensorLow,
                 process0.digitalLevelSensorLowTriggered)
    PlcCom.SetAI(config.AILevelSensor, mapValue(
        0, process0.tankVolume, 0, plcAnalogMax, process0.liquidVolume))
    PlcCom.SetAI(config.AITemperatureSensor, mapValue(-50, 250,
                 0, plcAnalogMax, process0.liquidTemperature))


while True:

    if (validPlcConnection == False):  # no valid connection -> try to connect

        # TODO: notify UI that there is no connection
        # UI.validPlcConnection = False
        # UI.update()
        # TODO: wait until UI connect button is clicked
        # if(UI.connectButtonClicked)
        #   UI.connectButtonClicked = False
        #
        #   TODO: ask UI to update config
        #   UI.updateConfig(config)
        """"Initialize plc communication object"""
        if config.plcProtocol == "ModBusTCP":
            PlcCom = plcModBusTCP(config.plcIpAdress, config.plcPort)
        elif config.plcProtocol == "plcS7":
            # IP address, rack, slot (from HW settings)
            PlcCom = plcS7(config.plcIpAdress, config.plcRack, config.plcSlot)
        elif config.plcProtocol == "logoS7":
            PlcCom = logoS7(config.plcIpAdress, config.taspLogo, config.taspServer)
        else:
            print("Error: no valid plcProtocol")

        '''connect/reconnect'''
        if PlcCom.isConnected():
            validPlcConnection = True
        else:
            if PlcCom.connect():  # run connect, returns True/False
                validPlcConnection = True
                PlcCom.reset_registers()
            else:
                validPlcConnection = False
            # wait a bit before next try, plcsim taks some time to connect
            time.sleep(1)

    elif (validPlcConnection == True):  # valid connection -> run main logic

        """
        Check if PLC is still connected
        """
        if not PlcCom.isConnected():  # check connection status
            validPlcConnection = False
            continue  # skip rest of loop

        """
        Transfer data between modules
        """
        sendPlcOutToProcessAndUi()
        sendProcessStatusToPlcInAndUi()

        """
        Check if a config/process update happened in UI and update config/process if needed
        """
        # TODO: implement UI.hasConfigUpdate() and UI.updateConfig(config)
        # if(UI.hasConfigUpdate()):
        #    UI.updateConfig(config)

        # TODO: implement UI.hasProcessUpdate() and UI.updateProcess(process)
        # if(UI.hasProcessUpdate()):
        #    UI.updateProcess(process0)

    # print out the current time since start and status
    print(
        f"Time: {int(time.time() - startTime)}, ValidConnection: {validPlcConnection}, Liquid level: {int(process0.liquidVolume)}, Liquid temp: {int(process0.liquidTemperature)}")
    # throttle code
    time.sleep(0.1)
