from processSim.tankSim import tankSim
from plcCom.plcModBusTCP import plcModBusTCP
from plcCom.plcS7 import plcS7
from plcCom.logoS7 import logoS7
import time
from configuration import configurationClass
from status import statusClass
from User_Interface.GUI import GuiClass

"""Initialize configuration instance with default parameters"""
config = configurationClass()

"""Initialize configuration instance with default parameters"""
status = statusClass()

"""Initialize process0 object"""
process0 = tankSim("process0")

"""Initialize Gui object"""
print("creating gui class...")
Gui0 = GuiClass()
validPlcConnection: bool = False


# remember at what time we started
startTime = time.time()


def tryConnectToPlc():
    global config, validPlcConnection, PlcCom
    """"Initialize plc communication object"""
    if config.plcProtocol == "ModBusTCP":
        PlcCom = plcModBusTCP(config.plcIpAdress, config.plcPort)
    elif config.plcProtocol == "plcS7":
        # IP address, rack, slot (from HW settings)
        PlcCom = plcS7(config.plcIpAdress,
                       config.plcRack, config.plcSlot)
    elif config.plcProtocol == "logoS7":
        PlcCom = logoS7(config.plcIpAdress,
                        config.tsapLogo, config.tsapServer)
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


# remember when last update was done
timeLastUpdate = 0


tryConnectToPlc()  # create initial PlcCom instance


while True:

    """Check for connect command from gui and tryConnect"""
    if (config.tryConnect == True):  # check connection status
        Gui0.updateData(config, status)
        validPlcConnection = False
        config.tryConnect = False
        print(
            f"Try connection to PLC at IP: {config.plcIpAdress} using protocol: {config.plcProtocol}")
        tryConnectToPlc()  # updates validPlcConnection

    """Get process control from plc or gui (config.plcGuiControl)"""
    # throttle calculations and data exchange between plc, process and gui
    if ((time.time() - timeLastUpdate) > config.simulationInterval):

        """
        Get process control from plc or gui
        PlcCom.updateData() and Gui0.updateData() check whether to change the status using config.plcGuiControl
        """
        # only try to contact plc if there is a connection
        if (validPlcConnection):
            PlcCom.updateData(config, status)
        else:
            # if control is plc but no plc connection, pretend plc outputs are all 0
            PlcCom.resetOutputs(config, status)

        """Update process values"""
        process0.updateData(config, status)
        """send new process status to gui"""
        Gui0.updateData(config, status)
        # print out the current time since start and status# print(f"Time: {int(time.time() - startTime)}, simRunning: {status.simRunning}, Liquid level: {int(status.liquidVolume)}, Liquid temp: {int(status.liquidTemperature)}")
        # print(f"Time: {int(time.time() - startTime)}, simRunning: {status.simRunning}, Liquid level: {int(status.liquidVolume)}, Liquid temp: {int(status.liquidTemperature)}")
        timeLastUpdate = time.time()

    # stop program if gui is closed
    if (config.doExit):
        quit()
    # always update gui for responsive buttons/input
    Gui0.updateGui()
