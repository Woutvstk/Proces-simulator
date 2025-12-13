# general imports
import sys
import os
from pathlib import Path
import time

from plcCom.plcS7 import plcS7
from plcCom.logoS7 import logoS7
from plcCom.PLCSimAPI import plcSimAPI
from plcCom.PLCSimS7 import plcSimS7
from configuration import configuration as mainConfigClass

from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QPushButton, QMenu, QAction,
    QWidget, QVBoxLayout)

from PyQt5.QtCore import QTimer, QSize
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter

# tankSim specific imports
from tankSim.simulation import simulation as tankSimClass
from tankSim.status import status as tankSimStatusClass
from tankSim.configurationTS import configuration as tankSimConfigurationClass
from tankSim.ioHandler import ioHandler as tankSimIoHandlerClass
from mainGui.mainGui import MainWindow

"""Initialize objects for main GUI setup (Part 1 of original structure)"""
mainConfig = mainConfigClass()
validPlcConnection: bool = False


PlcCom = None  # Initialize PlcCom here to ensure it's defined for the global scope usage later


"""Initialize objects for tankSim (Part 2 of original structure)"""
# Initialize configuration instance
tankSimConfig = tankSimConfigurationClass()
# Initialize status instance
tankSimStatus = tankSimStatusClass()
# Initialize ioHandler instance
tankSimIO = tankSimIoHandlerClass()
# Initialize simulation object
tankSim = tankSimClass("tankSimSimulation0")

# set chosen process to tankSim
currentProcessConfig: tankSimConfigurationClass = tankSimConfig
currentProcessStatus: tankSimStatusClass = tankSimStatus
currentProcessIoHandler: tankSimIoHandlerClass = tankSimIO
currentProcessSim: tankSimClass = tankSim

# Load IO configuration from JSON file
project_root = Path(__file__).resolve().parent
io_config_path = project_root / "tankSim" / "io_configuration.json"
if io_config_path.exists():
    tankSimConfig.load_io_config_from_file(io_config_path)
else:
    pass  # Removed unnecessary print

app = QApplication(sys.argv)

# Determine the project root path (already defined above, remove duplicate)
style_path = project_root / "guiCommon" / "style.qss"

# Load QSS style sheet
if os.path.exists(style_path):
    with open(style_path, "r") as f:
        app.setStyleSheet(f.read())
else:
    pass  # Removed unnecessary print

window = MainWindow()

# Give MainWindow access to configurations
window.mainConfig = mainConfig
window.tanksim_config = tankSimConfig
window.tanksim_status = tankSimStatus

window.show()

# remember at what time we started
startTime = time.time()


def tryConnectToPlc():
    """Initializes or attempts to connect/reconnect to the configured PLC"""
    # Use global variables
    global mainConfig, validPlcConnection, PlcCom
    window.clear_all_forces()

    # Don't connect in GUI mode
    if mainConfig.plcGuiControl == "gui":
        validPlcConnection = False
        window.validPlcConnection = False
        window.plc = None
        window.update_connection_status_icon()
        # Untoggle connect button
        try:
            window.pushButton_connect.blockSignals(True)
            window.pushButton_connect.setChecked(False)
            window.pushButton_connect.blockSignals(False)
        except:
            pass
        return

    """Initialize plc communication object based on protocol"""
    if mainConfig.plcProtocol == "PLC S7-1500/1200/400/300/ET 200SP":
        PlcCom = plcS7(mainConfig.plcIpAdress,
                       mainConfig.plcRack, mainConfig.plcSlot)
    elif mainConfig.plcProtocol == "logo!":
        PlcCom = logoS7(mainConfig.plcIpAdress,
                        mainConfig.tsapLogo, mainConfig.tsapServer)
    elif mainConfig.plcProtocol == "PLCSim S7-1500 advanced":
        PlcCom = plcSimAPI()
    elif mainConfig.plcProtocol == "PLCSim S7-1500/1200/400/300/ET 200SP":
        PlcCom = plcSimS7(mainConfig.plcIpAdress,
                          mainConfig.plcRack, mainConfig.plcSlot)
    else:
        validPlcConnection = False
        window.validPlcConnection = False
        window.plc = None
        window.update_connection_status_icon()
        return

    '''connect/reconnect logic'''
    if PlcCom.connect():  # run connect, returns True/False
        validPlcConnection = True
        # Use byte ranges from current process config

        # Reset INPUTS (sensors from simulator to PLC)
        PlcCom.resetSendInputs(
            currentProcessConfig.lowestByte,
            currentProcessConfig.highestByte
        )

        # Reset OUTPUTS (actuators from PLC to simulator) - important for force!
        PlcCom.resetSendOutputs(
            currentProcessConfig.lowestByte,
            currentProcessConfig.highestByte
        )

    else:
        validPlcConnection = False

    # Update GUI
    window.validPlcConnection = validPlcConnection
    window.plc = PlcCom if validPlcConnection else None
    window.update_connection_status_icon()


# remember when last update was done
timeLastUpdate = 0
connectionLostLogged = False


# main loop only runs if this file is run directly
if __name__ == "__main__":
    while True:
        app.processEvents()

        """Check for connect command from GUI and tryConnect"""
        if mainConfig.tryConnect:
            validPlcConnection = False
            connectionLostLogged = False  # Reset flag when attempting new connection
            mainConfig.tryConnect = False
            print(f"\nAttempting connection to PLC...")
            print(f"   IP: {mainConfig.plcIpAdress}")
            print(f"   Protocol: {mainConfig.plcProtocol}")
            tryConnectToPlc()

            # Update GUI connection status
            window.validPlcConnection = validPlcConnection
            window.plc = PlcCom if validPlcConnection else None
            window.update_connection_status_icon()

        """Process loop for simulation and data exchange"""
        # Throttle calculations and data exchange
        if ((time.time() - timeLastUpdate) > currentProcessConfig.simulationInterval):

            """Get process control from plc or gui"""
            # only try to contact plc if there is a connection
            if validPlcConnection:
                try:
                    # Check if connection is still alive
                    if not PlcCom.isConnected():
                        if not connectionLostLogged:
                            print("\nConnection lost to the PLC!")
                            connectionLostLogged = True
                        validPlcConnection = False
                        window.validPlcConnection = False
                        window.plc = None
                        window.update_connection_status_icon()
                        currentProcessIoHandler.resetOutputs(
                            mainConfig, currentProcessConfig, currentProcessStatus)
                    else:
                        # Connection OK - reset flag
                        connectionLostLogged = False

                        # Haal geforceerde waardes op van GUI
                        forced_values = window.get_forced_io_values()

                        # Update IO met force support
                        currentProcessIoHandler.updateIO(
                            PlcCom, mainConfig, currentProcessConfig, currentProcessStatus,
                            forced_values=forced_values)

                except Exception as e:
                    if not connectionLostLogged:
                        print(f"\nPLC communication error: {e}")
                        connectionLostLogged = True
                    validPlcConnection = False
                    window.validPlcConnection = False
                    window.plc = None
                    window.update_connection_status_icon()
                    currentProcessIoHandler.resetOutputs(
                        mainConfig, currentProcessConfig, currentProcessStatus)
            else:
                # if control is plc but no plc connection, pretend plc outputs are all 0
                currentProcessIoHandler.resetOutputs(
                    mainConfig, currentProcessConfig, currentProcessStatus)

            """Update process values (Run simulation)"""
            currentProcessSim.doSimulation(
                currentProcessConfig, currentProcessStatus)

            timeLastUpdate = time.time()

        """Check for exit command from GUI"""
        if mainConfig.doExit:
            print("\nExiting TankSim...")
            sys.exit(0)


# =============================================================================
# STAP 3: Voeg een isConnected() methode toe aan je PLC classes
# =============================================================================

# Voor plcS7.py, logoS7.py, PLCSimAPI.py, PLCSimS7.py:
# Voeg deze methode toe indien niet aanwezig:

def isConnected(self):
    """Check if the PLC connection is still active"""
    try:
        if not hasattr(self, 'plc') or self.plc is None:
            return False

        # Try a simple operation to check connection
        # For S7 connections:
        if hasattr(self.plc, 'get_connected'):
            return self.plc.get_connected()

        # Alternative: try to read a byte to test connection
        try:
            self.plc.read_area(0x83, 0, 0, 1)  # Try to read 1 byte from inputs
            return True
        except:
            return False
    except:
        return False


"""
=============================================================================
ALTERNATIEVE OPLOSSING (als isConnected niet werkt):
=============================================================================

Als je PLC library geen goede isConnected() heeft, gebruik dan deze aanpak:
"""

# Voeg deze variabele toe bovenaan main.py
lastConnectionCheck = time.time()
connectionCheckInterval = 2.5

if validPlcConnection:
    # Only check connection periodically, not every cycle
    if (time.time() - lastConnectionCheck) > connectionCheckInterval:
        try:
            # Try to perform a dummy read to check connection
            PlcCom.GetDI(0, 0)  # Try to read input 0.0
            lastConnectionCheck = time.time()
            connectionLostLogged = False  # Connection OK, reset flag
        except Exception as e:
            if not connectionLostLogged:
                print(
                    f"\n Connection lost to the PLC during periodic check: {e}")
                connectionLostLogged = True
            validPlcConnection = False
            window.validPlcConnection = False
            window.plc = None
            window.update_connection_status_icon()

    # Normal IO update
    if validPlcConnection:  # Check again after connection check
        forced_values = window.get_forced_io_values()
        currentProcessIoHandler.updateIO(
            PlcCom, mainConfig, currentProcessConfig, currentProcessStatus,
            forced_values=forced_values)
