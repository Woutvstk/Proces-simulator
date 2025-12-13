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
from tankSim.simulation import simulation as tankSimClass # Corrected class name
from tankSim.status import status as tankSimStatusClass
from tankSim.configurationTS import configuration as tankSimConfigurationClass # Using configurationTS
from tankSim.ioHandler import ioHandler as tankSimIoHandlerClass
from mainGui.mainGui import MainWindow # Import MainWindow

"""Initialize objects for main GUI setup (Part 1 of original structure)"""
mainConfig = mainConfigClass()
validPlcConnection: bool = False

"""Initialize objects for tankSim (Part 2 of original structure)"""
print("\nInitializing TankSim process...")

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
    print(f"IO configuration loaded from: {io_config_path}")
else:
    print(f"No IO configuration found at: {io_config_path}")

print("="*60)
print("Creating main GUI...")
print("="*60)

app = QApplication(sys.argv)

# Determine the project root path (already defined above, remove duplicate)
style_path = project_root / "guiCommon" / "style.qss"

# Load QSS style sheet
if os.path.exists(style_path):
    with open(style_path, "r") as f:
        app.setStyleSheet(f.read())
else:
    print("Warning: style.qss not found")

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
    
    # Don't connect in GUI mode
    if mainConfig.plcGuiControl == "gui":
        print("\n⚠️ Cannot connect: In GUI control mode")
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
    
    print(f"\nConnecting to PLC...")
    print(f"   Protocol: {mainConfig.plcProtocol}")
    print(f"   IP: {mainConfig.plcIpAdress}")
    
    """Initialize plc communication object based on protocol"""
    try:
        if mainConfig.plcProtocol == "PLC S7-1500/1200/400/300/ET 200SP":
            PlcCom = plcS7(mainConfig.plcIpAdress, mainConfig.plcRack, mainConfig.plcSlot)
        elif mainConfig.plcProtocol == "logo!":
            PlcCom = logoS7(mainConfig.plcIpAdress, mainConfig.tsapLogo, mainConfig.tsapServer)
        elif mainConfig.plcProtocol == "PLCSim S7-1500 advanced":
            PlcCom = plcSimAPI()
        elif mainConfig.plcProtocol == "PLCSim S7-1500/1200/400/300/ET 200SP":
            PlcCom = plcSimS7(mainConfig.plcIpAdress, mainConfig.plcRack, mainConfig.plcSlot)
        else:
            print(f"⚠️ Invalid protocol: {mainConfig.plcProtocol}")
            validPlcConnection = False
            window.validPlcConnection = False
            window.plc = None
            window.update_connection_status_icon()
            return
    except Exception as e:
        print("Error: no valid plcProtocol exception:", e)
        validPlcConnection = False
        window.validPlcConnection = False
        window.plc = None
        window.update_connection_status_icon()
        return

    '''connect/reconnect logic'''
    if PlcCom.isConnected():
        validPlcConnection = True
        print("✅ PLC already connected")
    else:
        if PlcCom.connect():  # run connect, returns True/False
            validPlcConnection = True
            # Use byte ranges from current process config (as in new code)
            PlcCom.resetSendInputs(
                currentProcessConfig.lowestByte,
                currentProcessConfig.highestByte
            )
            print(f"✅ PLC connected")
            print(f"   Byte range: {currentProcessConfig.lowestByte} - {currentProcessConfig.highestByte}")
        else:
            validPlcConnection = False
            print("❌ PLC connection failed")
    
    # Update GUI
    window.validPlcConnection = validPlcConnection
    window.plc = PlcCom if validPlcConnection else None
    window.update_connection_status_icon()

# remember when last update was done
timeLastUpdate = 0

print("\n" + "="*60)
print("TANKSIM READY")
print("="*60)

# main loop only runs if this file is run directly (Part 3 of original structure)
if __name__ == "__main__":
    while True:
        app.processEvents()
        
        """Check for connect command from GUI and tryConnect"""
        if mainConfig.tryConnect:
            validPlcConnection = False
            mainConfig.tryConnect = False
            print(f"\nAttempting connection to PLC...")
            print(f"   IP: {mainConfig.plcIpAdress}")
            print(f"   Protocol: {mainConfig.plcProtocol}")
            tryConnectToPlc()
            
            # Update GUI connection status - NIEUW
            window.validPlcConnection = validPlcConnection
            window.plc = PlcCom if validPlcConnection else None
            window.update_connection_status_icon()

            
        """Process loop for simulation and data exchange"""
        # Throttle calculations and data exchange
        if ((time.time() - timeLastUpdate) > currentProcessConfig.simulationInterval):
            
            """
            Get process control from plc or gui
            """
            # only try to contact plc if there is a connection
            if validPlcConnection:
                # Force callback functions
                def force_callback(signal_name, io_type):
                    """Check if signal is forced in GUI"""
                    table = window.tableWidget_IO
                    for row in range(table.rowCount()):
                        name_item = table.item(row, 0)
                        if name_item and name_item.text() == signal_name:
                            if table.is_row_forced(row):
                                return table.get_forced_value(row)
                    return None
                
                def status_callback(signal_name, value, io_type):
                    """Update status display in GUI"""
                    # This is now handled by update_io_status_display timer
                    pass
                
                currentProcessIoHandler.updateIO(
                    PlcCom, mainConfig, currentProcessConfig, currentProcessStatus)
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
            