
# general imports
import time
from plcCom.plcModBusTCP import plcModBusTCP
from plcCom.plcS7 import plcS7
from plcCom.logoS7 import logoS7
from plcCom.PLCSimAPI import plcSimAPI
from configuration import configuration as mainConfigClass
from guiCommon.QtDesignerLayout import *
from guiCommon.Resource_rc import *
from mainGui.mainGui import *
import sys
import os
import xml.etree.ElementTree as ET

from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QPushButton, QMenu, QAction,
    QWidget, QVBoxLayout
)
from PyQt5.QtCore import QTimer, QSize
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter


# tankSim specific imports
from tankSim.simulation import simulation as tankSimCLass
# from tankSim.tankSimGui import gui as tankSimGui TODO move tanksimGui here
from tankSim.status import status as tankSimStatusClass
from tankSim.configuration import configuration as tankSimConfigurationClass
from tankSim.ioHandler import ioHandler as tankSimIoHandlerClass

"""Initialize objects for main"""
Gui0 = None
mainConfig = mainConfigClass()
validPlcConnection: bool = False
print("Creating main gui...")
app = QApplication(sys.argv)
base_path = os.path.dirname(os.path.abspath(__file__))
style_path = os.path.join(base_path, "guiCommon/style.qss")

if os.path.exists(style_path):
    with open(style_path, "r") as f:
        app.setStyleSheet(f.read())
else:
    print("style.qss niet gevonden")

window = MainWindow()
window.show()
sys.exit(app.exec())


"""Initialize objects for tankSim"""
# Initialize configuration instance with default parameters
tankSimConfig = tankSimConfigurationClass()
# Initialize status instance with default parameters
tankSimStatus = tankSimStatusClass()
# Initialize ioHandler instance
tankSimIO = tankSimIoHandlerClass()
# Initialize simulation object
tankSim = tankSimCLass("tankSimSimulation0")

# set chosen process to tankSIm
# types now of tankSim process, should change to base class
currentProcessConfig: tankSimConfigurationClass = tankSimConfig
currentProcessStatus: tankSimStatusClass = tankSimStatus
currentProcessIoHandler: tankSimIoHandlerClass = tankSimIO
currentProcessSim: tankSimCLass = tankSim

# remember at what time we started
startTime = time.time()


def tryConnectToPlc():
    # creates a global var inside a function (normally local)
    global mainConfig, validPlcConnection, PlcCom
    """"Initialize plc communication object"""
    if mainConfig.plcProtocol == "ModBusTCP":
        PlcCom = plcModBusTCP(mainConfig.plcIpAdress, mainConfig.plcPort)
    elif mainConfig.plcProtocol == "PLC S7-1500/1200/400/300":
        PlcCom = plcS7(mainConfig.plcIpAdress,
                       mainConfig.plcRack, mainConfig.plcSlot)
    elif mainConfig.plcProtocol == "logo!":
        PlcCom = logoS7(mainConfig.plcIpAdress,
                        mainConfig.tsapLogo, mainConfig.tsapServer)
    elif mainConfig.plcProtocol == "PLCSim":
        PlcCom = plcSimAPI()
    else:
        print("Error: no valid plcProtocol")

    '''connect/reconnect'''
    if PlcCom.isConnected():
        validPlcConnection = True
    else:
        if PlcCom.connect():  # run connect, returns True/False
            validPlcConnection = True
            PlcCom.resetSendInputs(mainConfig.lowestByte,
                                   mainConfig.highestByte)
        else:
            validPlcConnection = False


# remember when last update was done
timeLastUpdate = 0

tryConnectToPlc()  # create initial PlcCom instance


# main loop only runs if this file is run directly
if __name__ == "__main__":
    while True:

        """Check for connect command from gui and tryConnect"""
        if (mainConfig.tryConnect == True):  # check connection status
            Gui0.updateDataMain(mainConfig)
            validPlcConnection = False
            mainConfig.tryConnect = False
            print(
                f"Try connection to PLC at IP: {mainConfig.plcIpAdress} using protocol: {mainConfig.plcProtocol}")
            tryConnectToPlc()  # updates validPlcConnection

        """Get process control from plc or gui (mainConfig.plcGuiControl)"""
        # throttle calculations and data exchange between plc, process and gui
        if ((time.time() - timeLastUpdate) > currentProcessConfig.simulationInterval):

            """
            Get process control from plc or gui
            PlcCom.updateData() and Gui0.updateData() check whether to change the status using mainConfig.plcGuiControl
            """
            # only try to contact plc if there is a connection
            if (validPlcConnection):
                currentProcessIoHandler.updateIO(
                    PlcCom, currentProcessConfig, currentProcessStatus)
            else:
                # if control is plc but no plc connection, pretend plc outputs are all 0
                currentProcessIoHandler.resetOutputs(
                    mainConfig, currentProcessConfig, currentProcessStatus)

            """Update process values"""
            currentProcessSim.doSimulation(
                currentProcessConfig, currentProcessStatus)
            """send new process status to gui"""
            Gui0.updateDataMain(mainConfig)
            Gui0.updateData(
                mainConfig, currentProcessConfig, currentProcessStatus)

            # print out the current time since start and status
            # print(f"Time: {int(time.time() - startTime)}, simRunning: {currentProcessStatus.simRunning}, Liquid level: {int(currentProcessStatus.liquidVolume)}, Liquid temp: {int(currentProcessStatus.liquidTemperature)}")
            timeLastUpdate = time.time()

        # stop program if gui is closed
        if (mainConfig.doExit):
            quit()

        # always update gui for responsive buttons/input
        if Gui0 is not None:
            Gui0.updateGui()
