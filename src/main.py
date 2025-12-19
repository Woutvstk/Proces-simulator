"""
Main Entry Point - Industrial Simulation Framework

This is the refactored main entry point using the new modular architecture.
It initializes core components, registers simulations, and runs the main loop.
"""
import sys
import os
import time
import logging
from pathlib import Path

# Add src to path for imports
src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Core imports
from core.configuration import configuration as mainConfigClass
from core.simulationManager import SimulationManager
from core.protocolManager import ProtocolManager

# IO imports
from IO.handler import IOHandler
from IO.protocols.plcS7 import plcS7
from IO.protocols.logoS7 import logoS7
from IO.protocols.PLCSimAPI.PLCSimAPI import plcSimAPI
from IO.protocols.PLCSimS7 import plcSimS7

# Simulation imports
from simulations.PIDtankValve.simulation import PIDTankSimulation

# GUI imports
from PyQt5.QtWidgets import QApplication
from gui.mainGui import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# INITIALIZATION
# ============================================================================

# Initialize core configuration
mainConfig = mainConfigClass()

# Initialize simulation manager
simulationManager = SimulationManager()

# Register available simulations
simulationManager.register_simulation("PIDtankValve", PIDTankSimulation)
logger.info("Registered simulations: " + str(simulationManager.get_registered_simulations()))

# Load the tank simulation by default
if simulationManager.load_simulation("PIDtankValve", "tankSimSimulation0"):
    logger.info("Default simulation loaded successfully")
else:
    logger.error("Failed to load default simulation")
    sys.exit(1)

# Initialize protocol manager
protocolManager = ProtocolManager()

# Initialize IO handler
ioHandler = IOHandler()

# Get references to the active simulation objects (for backward compatibility with old GUI)
active_sim = simulationManager.get_active_simulation()
tankSimConfig = active_sim.config
tankSimStatus = active_sim.status
tankSimIO = ioHandler  # Use new IO handler

# Set current process references (backward compatibility)
currentProcessConfig = tankSimConfig
currentProcessStatus = tankSimStatus
currentProcessIoHandler = tankSimIO
currentProcessSim = active_sim._simulation  # Access wrapped simulation

# Load IO configuration from JSON file
io_config_path = src_dir / "IO" / "IO_configuration.json"
if io_config_path.exists():
    tankSimConfig.load_io_config_from_file(io_config_path)
    logger.info(f"IO configuration loaded from: {io_config_path}")
else:
    logger.warning(f"IO configuration not found: {io_config_path}")

# Initialize Qt Application
app = QApplication(sys.argv)

# Load QSS style sheet
style_path = src_dir / "gui" / "media" / "style.qss"
if style_path.exists():
    with open(style_path, "r") as f:
        app.setStyleSheet(f.read())
    logger.info("Style sheet loaded")

# Initialize main window
window = MainWindow()

# Give MainWindow access to configurations (backward compatibility)
window.mainConfig = mainConfig
window.tanksim_config = tankSimConfig
window.tanksim_status = tankSimStatus

window.show()

# Remember start time
startTime = time.time()

# ============================================================================
# PLC CONNECTION HANDLING
# ============================================================================

validPlcConnection: bool = False
PlcCom = None


def tryConnectToPlc():
    """Initializes or attempts to connect/reconnect to the configured PLC"""
    global mainConfig, validPlcConnection, PlcCom, protocolManager
    
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
        protocolManager.deactivate()
        return
    
    # Initialize PLC communication object based on protocol
    logger.info(f"Initializing protocol: {mainConfig.plcProtocol}")
    
    if mainConfig.plcProtocol == "PLC S7-1500/1200/400/300/ET 200SP":
        PlcCom = plcS7(mainConfig.plcIpAdress, mainConfig.plcRack, mainConfig.plcSlot)
    elif mainConfig.plcProtocol == "logo!":
        PlcCom = logoS7(mainConfig.plcIpAdress, mainConfig.tsapLogo, mainConfig.tsapServer)
    elif mainConfig.plcProtocol == "PLCSim S7-1500 advanced":
        PlcCom = plcSimAPI()
    elif mainConfig.plcProtocol == "PLCSim S7-1500/1200/400/300/ET 200SP":
        PlcCom = plcSimS7(mainConfig.plcIpAdress, mainConfig.plcRack, mainConfig.plcSlot)
    else:
        validPlcConnection = False
        window.validPlcConnection = False
        window.plc = None
        window.update_connection_status_icon()
        return
    
    # Activate protocol in protocol manager
    protocolManager.activate_protocol(mainConfig.plcProtocol, PlcCom)
    
    # Attempt connection
    if protocolManager.connect():
        validPlcConnection = True
        logger.info(f"Connected to {mainConfig.plcProtocol}")
        
        # Reset INPUTS (sensors from simulator to PLC)
        protocolManager.reset_inputs(
            currentProcessConfig.lowestByte,
            currentProcessConfig.highestByte
        )
        
        # Reset OUTPUTS (actuators from PLC to simulator)
        protocolManager.reset_outputs(
            currentProcessConfig.lowestByte,
            currentProcessConfig.highestByte
        )
    else:
        validPlcConnection = False
        logger.warning("Connection failed")
    
    # Update GUI
    window.validPlcConnection = validPlcConnection
    window.plc = PlcCom if validPlcConnection else None
    window.update_connection_status_icon()


# ============================================================================
# MAIN LOOP
# ============================================================================

timeLastUpdate = 0
connectionLostLogged = False

if __name__ == "__main__":
    try:
        logger.info("Starting main loop...")
        
        while not mainConfig.doExit:
            app.processEvents()
            
            # Check for connect command from GUI
            if mainConfig.tryConnect:
                validPlcConnection = False
                connectionLostLogged = False
                mainConfig.tryConnect = False
                print(f"\nAttempting connection to PLC...")
                print(f"   IP: {mainConfig.plcIpAdress}")
                print(f"   Protocol: {mainConfig.plcProtocol}")
                tryConnectToPlc()
                
                # Update GUI connection status
                window.validPlcConnection = validPlcConnection
                window.plc = PlcCom if validPlcConnection else None
                window.update_connection_status_icon()
            
            # Process loop for simulation and data exchange
            # Throttle calculations and data exchange
            if (time.time() - timeLastUpdate) > currentProcessConfig.simulationInterval:
                
                # Get process control from PLC or GUI
                if validPlcConnection:
                    try:
                        # Check if connection is still alive
                        if not protocolManager.is_connected():
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
                            
                            # Get forced values from GUI
                            forced_values = window.get_forced_io_values()
                            
                            # Update IO with force support
                            currentProcessIoHandler.updateIO(
                                PlcCom, mainConfig, currentProcessConfig, currentProcessStatus,
                                forced_values=forced_values)
                    
                    except Exception as e:
                        if not connectionLostLogged:
                            print(f"\nPLC communication error: {e}")
                            logger.error(f"PLC communication error: {e}")
                            connectionLostLogged = True
                        validPlcConnection = False
                        window.validPlcConnection = False
                        window.plc = None
                        window.update_connection_status_icon()
                        currentProcessIoHandler.resetOutputs(
                            mainConfig, currentProcessConfig, currentProcessStatus)
                else:
                    # If control is PLC but no PLC connection, pretend PLC outputs are all 0
                    currentProcessIoHandler.resetOutputs(
                        mainConfig, currentProcessConfig, currentProcessStatus)
                
                # Update process values (Run simulation)
                # Using the simulation manager's update method
                dt = time.time() - timeLastUpdate
                simulationManager.update_simulation(dt)
                
                # Update GUI display with new process values
                window.update_tanksim_display()
                
                timeLastUpdate = time.time()
        
        # ===== EXIT CLEANUP =====
        logger.info("Exiting application...")
        
        # Disconnect from PLC
        if validPlcConnection and protocolManager:
            protocolManager.disconnect()
            print("Disconnected from PLC")
        
        # Kill any remaining NetToPLCSim processes
        try:
            import subprocess
            result = subprocess.run(
                ['taskkill', '/F', '/IM', 'NetToPLCSim.exe'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2
            )
            if result.returncode == 0:
                print("Terminated NetToPLCSim.exe processes")
        except:
            pass
        
        sys.exit(0)
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        mainConfig.doExit = True
        
        # Cleanup
        if validPlcConnection and protocolManager:
            protocolManager.disconnect()
            print("Disconnected from PLC")
        
        # Kill any remaining NetToPLCSim processes
        try:
            import subprocess
            subprocess.run(
                ['taskkill', '/F', '/IM', 'NetToPLCSim.exe'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2
            )
        except:
            pass
        
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        print(f"ERROR: {e}")
        sys.exit(1)
