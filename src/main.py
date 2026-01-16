"""
Main Entry Point - Industrial Simulation Framework

This is the refactored main entry point using the new modular architecture.
It initializes core components, registers simulations, and runs the main loop.

External Libraries Used:
- PyQt5 (GPL v3) - GUI framework for main application window
- logging (Python Standard Library) - Application-wide logging configuration
- pathlib (Python Standard Library) - Path handling for imports
"""
import sys
import os
import time
import logging
from pathlib import Path

# Suppress Qt warnings about invalid font sizes
os.environ['QT_LOGGING_RULES'] = '*=false'

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

# Suppress Snap7 logging completely to prevent spam when connection is lost
logging.getLogger('snap7.client').setLevel(logging.CRITICAL)
logging.getLogger('snap7.common').setLevel(logging.CRITICAL)

# ============================================================================
# INITIALIZATION
# ============================================================================

# Initialize core configuration
mainConfig = mainConfigClass()

# Initialize simulation manager
simulationManager = SimulationManager()
# Expose simulation manager via mainConfig so GUI/mixins can query active simulation
mainConfig.simulationManager = simulationManager

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

# Get references to the active simulation objects
active_sim = simulationManager.get_active_simulation()
active_config = active_sim.config
active_status = active_sim.status

# Load IO configuration from JSON file
io_config_path = src_dir / "IO" / "IO_configuration.json"
if io_config_path.exists():
    active_config.load_io_config_from_file(io_config_path)
    logger.info(f"IO configuration loaded from: {io_config_path}")
    # Start forced write period after loading config (500ms)
    ioHandler.start_force_write_period()
else:
    logger.warning(f"IO configuration not found: {io_config_path}")

# Initialize Qt Application
app = QApplication(sys.argv)

# Set tooltip delay to 1.75 seconds
os.environ['QT_TOOLTIP_DELAY'] = '1750'

# Load QSS style sheet
style_path = src_dir / "gui" / "media" / "style.qss"
if style_path.exists():
    with open(style_path, "r") as f:
        app.setStyleSheet(f.read())

# Initialize main window with mainConfig
window = MainWindow(mainConfig)

# Store ioHandler reference in mainConfig for GUI access
mainConfig.ioHandler = ioHandler

# Provide MainWindow access to tank simulation objects
window.tanksim_config = active_config
window.set_simulation_status(active_status)

window.show()

# Remember start time
startTime = time.time()
validPlcConnection: bool = False
lastConnectionLossTime = 0  # Track when connection was last lost
CONNECTION_LOSS_COOLDOWN = 2.0  # Wait 2 seconds before trying to recover
connectionErrorOccurred = False  # Flag to prevent reconnection loop after error


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
            
            time.sleep(0.005)
            
            # Check for connect command from GUI
            if mainConfig.tryConnect:
                validPlcConnection = False
                connectionLostLogged = False
                connectionErrorOccurred = False  # Reset error flag on new connection attempt
                mainConfig.tryConnect = False
                # Clear GUI force overrides before connecting
                try:
                    window.clear_all_forces()
                except Exception:
                    pass

                # In GUI mode, skip PLC connection entirely
                if mainConfig.plcGuiControl == "gui":
                    validPlcConnection = False
                    window.validPlcConnection = False
                    window.plc = None
                    window.update_connection_status_icon()
                    protocolManager.deactivate()
                else:
                    ok = protocolManager.initialize_and_connect(
                        mainConfig,
                        active_config.lowestByte,
                        active_config.highestByte,
                    )
                    validPlcConnection = bool(ok)
                    if not ok:
                        logger.warning("Connection failed")
                        # Auto-uncheck connect button on connection failure
                        try:
                            window.pushButton_connect.blockSignals(True)
                            window.pushButton_connect.setChecked(False)
                            window.pushButton_connect.blockSignals(False)
                        except Exception:
                            pass
                    else:
                        # Connection successful - start forced write period (500ms)
                        ioHandler.start_force_write_period()
                        logger.info("Connection established - starting 500ms IO initialization period")

                # Update GUI connection status
                window.validPlcConnection = validPlcConnection
                window.plc = protocolManager.get_active_protocol() if validPlcConnection else None
                window.update_connection_status_icon()
            
            # Process loop for simulation and data exchange
            # PLCSim communication can be slower; throttle slightly
            io_interval = active_config.simulationInterval
            if mainConfig.plcProtocol == "PLCSim S7-1500/1200/400/300/ET 200SP":
                # Use a minimum interval of 200ms for PLCSim instead of 1s
                io_interval = max(0.2, active_config.simulationInterval)
            
            # Throttle calculations and data exchange
            if (time.time() - timeLastUpdate) > io_interval:
                
                # Get process control from PLC or GUI
                # Only try to use connection if: valid AND no error has occurred
                if validPlcConnection and not connectionErrorOccurred:
                    try:
                        # Check if connection is still alive
                        if not protocolManager.is_connected():
                            if not connectionLostLogged:
                                logger.warning("Connection lost to the PLC")
                                connectionLostLogged = True
                                lastConnectionLossTime = time.time()
                            validPlcConnection = False
                            window.validPlcConnection = False
                            window.plc = None
                            # Auto-uncheck connect button when connection is lost
                            try:
                                window.pushButton_connect.blockSignals(True)
                                window.pushButton_connect.setChecked(False)
                                window.pushButton_connect.blockSignals(False)
                            except Exception:
                                pass
                            window.update_connection_status_icon()
                            # Disconnect the protocol to clean up
                            try:
                                protocolManager.disconnect()
                            except:
                                pass
                            ioHandler.resetOutputs(
                                mainConfig, active_config, active_status)
                        else:
                            # Connection OK - reset flag
                            connectionLostLogged = False
                            
                            # Get forced values from GUI
                            forced_values = window.get_forced_io_values()
                            
                            # Check if Manual mode is active (GUI controls valves/heater)
                            manual_mode = False
                            try:
                                if hasattr(window, 'vat_widget') and window.vat_widget:
                                    manual_mode = window.vat_widget.is_manual_mode()
                            except Exception:
                                manual_mode = False
                            
                            # Update IO with force support
                            # In Manual mode, don't read valve/heater from PLC (GUI controls them)
                            # But still write sensor values to PLC
                            try:
                                ioHandler.updateIO(
                                    protocolManager.get_active_protocol(),
                                    mainConfig,
                                    active_config,
                                    active_status,
                                    forced_values=forced_values,
                                    manual_mode=manual_mode)
                            except:
                                # Any error during IO - immediately trigger disconnection
                                raise
                    
                    except Exception as e:
                        # Set error flag immediately to prevent further attempts
                        connectionErrorOccurred = True
                        validPlcConnection = False
                        window.validPlcConnection = False
                        window.plc = None
                        
                        # Auto-uncheck connect button on communication error
                        try:
                            window.pushButton_connect.blockSignals(True)
                            window.pushButton_connect.setChecked(False)
                            window.pushButton_connect.blockSignals(False)
                        except Exception:
                            pass
                        
                        # Immediately disconnect to clean up the broken connection
                        try:
                            protocolManager.disconnect()
                        except:
                            pass
                        
                        window.update_connection_status_icon()
                        ioHandler.resetOutputs(mainConfig, active_config, active_status)
                        
                        # Log once
                        if not connectionLostLogged:
                            logger.warning("Connection lost to the PLC")
                            connectionLostLogged = True
                            lastConnectionLossTime = time.time()
                else:
                    # If control is PLC but no PLC connection, pretend PLC outputs are all 0
                    ioHandler.resetOutputs(
                        mainConfig, active_config, active_status)
                
                # Update button pulse timers
                try:
                    if hasattr(window, '_button_pulse_manager'):
                        window._button_pulse_manager.update()
                except Exception as e:
                    logger.error(f"Error updating button pulse manager: {e}", exc_info=True)
                
                # Write GUI values to status BEFORE simulation runs (Manual mode must update valves first)
                try:
                    if hasattr(window, 'write_gui_values_to_status'):
                        window.write_gui_values_to_status()
                except Exception as e:
                    logger.error(f"Error in write_gui_values_to_status: {e}", exc_info=True)
                
                # Update process values (Run simulation)
                # Using the simulation manager's update method
                dt = time.time() - timeLastUpdate
                simulationManager.update_simulation(dt)
                
                # Update GUI display with new simulation results
                try:
                    window.update_tanksim_display()
                except Exception as e:
                    logger.error(f"Error in update_tanksim_display: {e}", exc_info=True)
                
                timeLastUpdate = time.time()
        
        # ===== EXIT CLEANUP =====
        logger.info("Exiting application...")
        
        # Disconnect from PLC
        if validPlcConnection and protocolManager:
            protocolManager.disconnect()
            logger.info("Disconnected from PLC")
        
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
                logger.info("Terminated NetToPLCSim.exe processes")
        except:
            pass
        
        sys.exit(0)
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        mainConfig.doExit = True
        
        # Cleanup
        if validPlcConnection and protocolManager:
            protocolManager.disconnect()
            logger.info("Disconnected from PLC (interrupt)")
        
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
        sys.exit(1)
