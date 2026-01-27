"""
Save/Load Page Mixin - Handles save/load button functionality.

This mixin provides:
- Save button handlers (pushButton_Save2, pushButton_Save)
- Load button handlers (pushButton_Load2, pushButton_Load)
- File dialog integration
- State validation and error handling
- GUI updates after load

External Libraries Used:
- PyQt5 (GPL v3) - GUI framework and file dialogs
- logging (Python Standard Library) - Error and info logging
- pathlib (Python Standard Library) - File path handling
"""
import logging
import time
from pathlib import Path
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QWidget, QPushButton, QSlider, QLineEdit, QRadioButton
from PyQt5.QtCore import QTimer

from core.load_save import save_application_state, load_application_state, validate_state_file

logger = logging.getLogger(__name__)


class SaveLoadMixin:
    """
    Mixin class for save/load functionality.
    Combined with MainWindow via multiple inheritance.
    """

    def init_save_load_page(self):
        """Initialize save/load button connections."""
        try:
            # Connect Save buttons
            if hasattr(self, 'pushButton_Save'):
                self.pushButton_Save.clicked.connect(self.on_save_clicked)
            
            if hasattr(self, 'pushButton_Save2'):
                self.pushButton_Save2.clicked.connect(self.on_save_clicked)
            
            # Connect Load buttons
            if hasattr(self, 'pushButton_Load'):
                self.pushButton_Load.clicked.connect(self.on_load_clicked)
            
            if hasattr(self, 'pushButton_Load2'):
                self.pushButton_Load2.clicked.connect(self.on_load_clicked)
            
            logger.info("Save/Load buttons initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize save/load buttons: {e}")

    def on_save_clicked(self):
        """Handle save button click - prompts for file and saves complete state."""
        try:
            # Get file path from user
            default_path = Path.cwd() / "saved_states"
            default_path.mkdir(exist_ok=True)
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Application State",
                str(default_path / "simulation_state.json"),
                "JSON Files (*.json);;All Files (*.*)"
            )
            
            if not file_path:
                # User cancelled
                return
            
            # Ensure .json extension
            if not file_path.endswith('.json'):
                file_path += '.json'
            
            # Get paths
            src_dir = Path(__file__).resolve().parent.parent.parent
            io_config_path = src_dir / "IO" / "IO_configuration.json"
            
            # Get simulation manager from mainConfig
            simulation_manager = None
            if hasattr(self, 'mainConfig') and hasattr(self.mainConfig, 'simulationManager'):
                simulation_manager = self.mainConfig.simulationManager
            
            # Sync GUI states to status/config before saving
            try:
                if simulation_manager:
                    active_sim = simulation_manager.get_active_simulation()
                    
                    # DON'T sync simRunning - we don't want to auto-start the simulation on load
                    # User explicitly requested simRunning should NOT be saved
                    
                    if active_sim and hasattr(active_sim, 'status'):
                        try:
                            # Sync PID valve control states to status
                            
                            # Auto/Manual mode buttons
                            auto_btn = self.findChild(QPushButton, "pushButton_PidValveAuto")
                            man_btn = self.findChild(QPushButton, "pushButton_PidValveMan")
                            if auto_btn and man_btn:
                                active_sim.status.pidPidValveAutoCmd = auto_btn.isChecked()
                                active_sim.status.pidPidValveManCmd = man_btn.isChecked()
                                logger.info(f"    ✓ Synced Auto/Man: Auto={auto_btn.isChecked()}, Man={man_btn.isChecked()}")
                            
                            # Temperature control radio buttons (Analog/Digital)
                            radio_ai_temp = self.findChild(QRadioButton, "radioButton_PidTankValveAItemp")
                            radio_di_temp = self.findChild(QRadioButton, "radioButton_PidTankValveDItemp")
                            if radio_ai_temp and radio_di_temp:
                                active_sim.status.pidPidTankValveAItempCmd = radio_ai_temp.isChecked()
                                active_sim.status.pidPidTankValveDItempCmd = radio_di_temp.isChecked()
                                logger.info(f"    ✓ Synced Temp control: AI={radio_ai_temp.isChecked()}, DI={radio_di_temp.isChecked()}")
                            
                            # Level control radio buttons (Analog/Digital)
                            radio_ai_level = self.findChild(QRadioButton, "radioButton_PidTankValveAIlevel")
                            radio_di_level = self.findChild(QRadioButton, "radioButton_PidTankValveDIlevel")
                            if radio_ai_level and radio_di_level:
                                active_sim.status.pidPidTankValveAIlevelCmd = radio_ai_level.isChecked()
                                active_sim.status.pidPidTankValveDIlevelCmd = radio_di_level.isChecked()
                                logger.info(f"    ✓ Synced Level control: AI={radio_ai_level.isChecked()}, DI={radio_di_level.isChecked()}")
                            
                            # Heater power slider (0-100%)
                            heater_sliders = [
                                self.findChild(QSlider, "heaterPowerSlider"),
                                self.findChild(QSlider, "heaterPowerSlider_1"),
                                self.findChild(QSlider, "heaterPowerSlider_2"),
                                self.findChild(QSlider, "heaterPowerSlider_3")
                            ]
                            for slider in heater_sliders:
                                if slider:
                                    # Slider is 0-100, status is 0.0-1.0
                                    active_sim.status.heaterPowerFraction = slider.value() / 100.0
                                    logger.info(f"    ✓ Synced heater power: {slider.value()}% ({active_sim.status.heaterPowerFraction:.2f})")
                                    break
                            
                            # Temperature setpoint slider (0-27648 range)
                            slider_temp = self.findChild(QSlider, "slider_PidTankTempSP")
                            if slider_temp:
                                active_sim.status.pidPidTankTempSPValue = slider_temp.value()
                                logger.info(f"    ✓ Synced temp setpoint: {slider_temp.value()}")
                            
                            # Level setpoint slider (0-27648 range)
                            slider_level = self.findChild(QSlider, "slider_PidTankLevelSP")
                            if slider_level:
                                active_sim.status.pidPidTankLevelSPValue = slider_level.value()
                                logger.info(f"    ✓ Synced level setpoint: {slider_level.value()}")
                            
                            # Valve positions from entry fields (manual mode) - convert to fractions
                            valve_in_entry = self.findChild(QLineEdit, "valveInEntry")
                            if valve_in_entry:
                                try:
                                    val = float(valve_in_entry.text() or 0)
                                    active_sim.status.valveInOpenFraction = val / 100.0  # Convert % to fraction
                                    logger.info(f"    ✓ Synced valve in: {val}% ({active_sim.status.valveInOpenFraction:.2f})")
                                except ValueError:
                                    pass
                            
                            valve_out_entry = self.findChild(QLineEdit, "valveOutEntry")
                            if valve_out_entry:
                                try:
                                    val = float(valve_out_entry.text() or 0)
                                    active_sim.status.valveOutOpenFraction = val / 100.0  # Convert % to fraction
                                    logger.info(f"    ✓ Synced valve out: {val}% ({active_sim.status.valveOutOpenFraction:.2f})")
                                except ValueError:
                                    pass
                            
                        except Exception as e:
                            logger.warning(f"    Could not sync PID control states: {e}", exc_info=True)
                    
                    # Sync GUI display settings and ALL config values to config before saving
                    if active_sim and hasattr(active_sim, 'config'):
                        try:
                            # Tank color from dropdown
                            colorDropDown = self.findChild(QWidget, "colorDropDown")
                            if colorDropDown:
                                tank_color = colorDropDown.currentData()
                                if tank_color:
                                    active_sim.config.tankColor = tank_color
                                    logger.info(f"    ✓ Synced tankColor to config: {tank_color}")
                            
                            # Display checkboxes
                            levelSwitchesCheckBox = self.findChild(QWidget, "levelSwitchesCheckBox")
                            if levelSwitchesCheckBox:
                                active_sim.config.displayLevelSwitches = levelSwitchesCheckBox.isChecked()
                                logger.info(f"    ✓ Synced displayLevelSwitches to config: {levelSwitchesCheckBox.isChecked()}")
                            
                            analogValueTempCheckBox = self.findChild(QWidget, "analogValueTempCheckBox")
                            if analogValueTempCheckBox:
                                active_sim.config.displayTemperature = analogValueTempCheckBox.isChecked()
                                logger.info(f"    ✓ Synced displayTemperature to config: {analogValueTempCheckBox.isChecked()}")
                            
                            # Sync all entry fields to config
                            # Tank volume (UI in m³, config in liters)
                            volumeEntry = self.findChild(QWidget, "volumeEntry")
                            if volumeEntry:
                                try:
                                    m3 = float(volumeEntry.text())
                                    active_sim.config.tankVolume = m3 * 1000.0
                                    logger.info(f"    ✓ Synced tankVolume: {active_sim.config.tankVolume}L")
                                except ValueError:
                                    pass
                            
                            # Max flows
                            for entry_name in ['maxFlowInEntry', 'maxFlowInEntry1', 'maxFlowInEntry2']:
                                entry = self.findChild(QWidget, entry_name)
                                if entry:
                                    try:
                                        active_sim.config.valveInMaxFlow = float(entry.text())
                                        logger.info(f"    ✓ Synced valveInMaxFlow: {active_sim.config.valveInMaxFlow}")
                                        break
                                    except ValueError:
                                        pass
                            
                            for entry_name in ['maxFlowOutEntry', 'maxFlowOutEntry1', 'maxFlowOutEntry2']:
                                entry = self.findChild(QWidget, entry_name)
                                if entry:
                                    try:
                                        active_sim.config.valveOutMaxFlow = float(entry.text())
                                        logger.info(f"    ✓ Synced valveOutMaxFlow: {active_sim.config.valveOutMaxFlow}")
                                        break
                                    except ValueError:
                                        pass
                            
                            # Heater max power - CRITICAL FIX
                            for entry_name in ['powerHeatingCoilEntry', 'powerHeatingCoilEntry2']:
                                entry = self.findChild(QWidget, entry_name)
                                if entry:
                                    try:
                                        active_sim.config.heaterMaxPower = float(entry.text())
                                        logger.info(f"    ✓ Synced heaterMaxPower: {active_sim.config.heaterMaxPower}")
                                        break
                                    except ValueError:
                                        pass
                            
                            # Physical properties
                            ambientTempEntry = self.findChild(QWidget, "ambientTempEntry")
                            if ambientTempEntry:
                                try:
                                    active_sim.config.ambientTemp = float(ambientTempEntry.text())
                                    logger.info(f"    ✓ Synced ambientTemp: {active_sim.config.ambientTemp}")
                                except ValueError:
                                    pass
                            
                            heatLossVatEntry = self.findChild(QWidget, "heatLossVatEntry")
                            if heatLossVatEntry:
                                try:
                                    active_sim.config.tankHeatLoss = float(heatLossVatEntry.text())
                                    logger.info(f"    ✓ Synced tankHeatLoss: {active_sim.config.tankHeatLoss}")
                                except ValueError:
                                    pass
                            
                            specificHeatCapacity = self.findChild(QWidget, "specificHeatCapacity")
                            if specificHeatCapacity:
                                try:
                                    active_sim.config.liquidSpecificHeatCapacity = float(specificHeatCapacity.text())
                                    logger.info(f"    ✓ Synced liquidSpecificHeatCapacity: {active_sim.config.liquidSpecificHeatCapacity}")
                                except ValueError:
                                    pass
                            
                            boilingTempEntry = self.findChild(QWidget, "boilingTempEntry")
                            if boilingTempEntry:
                                try:
                                    active_sim.config.liquidBoilingTemp = float(boilingTempEntry.text())
                                    logger.info(f"    ✓ Synced liquidBoilingTemp: {active_sim.config.liquidBoilingTemp}")
                                except ValueError:
                                    pass
                            
                            # Density (UI in kg/m³, config in kg/L)
                            specificWeightEntry = self.findChild(QWidget, "specificWeightEntry")
                            if specificWeightEntry:
                                try:
                                    rho_m3 = float(specificWeightEntry.text())
                                    active_sim.config.liquidSpecificWeight = rho_m3 / 1000.0
                                    logger.info(f"    ✓ Synced liquidSpecificWeight: {active_sim.config.liquidSpecificWeight}")
                                except ValueError:
                                    pass
                            
                            # Time delays - CRITICAL FIX
                            timeDelayfillingEntry = self.findChild(QWidget, "timeDelayfillingEntry")
                            if timeDelayfillingEntry:
                                try:
                                    active_sim.config.liquidVolumeTimeDelay = float(timeDelayfillingEntry.text())
                                    logger.info(f"    ✓ Synced liquidVolumeTimeDelay: {active_sim.config.liquidVolumeTimeDelay}")
                                except ValueError:
                                    pass
                            
                            timeDelayTempEntry = self.findChild(QWidget, "timeDelayTempEntry")
                            if timeDelayTempEntry:
                                try:
                                    active_sim.config.liquidTempTimeDelay = float(timeDelayTempEntry.text())
                                    logger.info(f"    ✓ Synced liquidTempTimeDelay: {active_sim.config.liquidTempTimeDelay}")
                                except ValueError:
                                    pass
                            
                            # Level switch thresholds (UI in %, config in liters)
                            levelSwitchMaxHeightEntry = self.findChild(QWidget, "levelSwitchMaxHeightEntry")
                            if levelSwitchMaxHeightEntry and active_sim.config.tankVolume > 0:
                                try:
                                    high_pct = float(levelSwitchMaxHeightEntry.text())
                                    active_sim.config.digitalLevelSensorHighTriggerLevel = (high_pct / 100.0) * active_sim.config.tankVolume
                                    logger.info(f"    ✓ Synced digitalLevelSensorHighTriggerLevel: {active_sim.config.digitalLevelSensorHighTriggerLevel}L ({high_pct}%)")
                                except ValueError:
                                    pass
                            
                            levelSwitchMinHeightEntry = self.findChild(QWidget, "levelSwitchMinHeightEntry")
                            if levelSwitchMinHeightEntry and active_sim.config.tankVolume > 0:
                                try:
                                    low_pct = float(levelSwitchMinHeightEntry.text())
                                    active_sim.config.digitalLevelSensorLowTriggerLevel = (low_pct / 100.0) * active_sim.config.tankVolume
                                    logger.info(f"    ✓ Synced digitalLevelSensorLowTriggerLevel: {active_sim.config.digitalLevelSensorLowTriggerLevel}L ({low_pct}%)")
                                except ValueError:
                                    pass
                            
                        except Exception as e:
                            logger.warning(f"    Could not sync GUI settings to config: {e}", exc_info=True)
            except Exception as e:
                logger.warning(f"Could not sync status/config before save: {e}", exc_info=True)
            
            # Save state
            logger.info(f"Saving state to: {file_path}")
            
            success = save_application_state(
                main_config=self.mainConfig,
                simulation_manager=simulation_manager,
                io_config_path=str(io_config_path),
                save_file_path=file_path
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "Save Successful",
                    f"Application state saved successfully to:\n{file_path}\n\n"
                    f"This file contains:\n"
                    f"• Main configuration (PLC settings, protocol)\n"
                    f"• Simulation configuration\n"
                    f"• Current process values\n"
                    f"• IO configuration"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Save Failed",
                    f"Failed to save application state to:\n{file_path}\n\n"
                    f"Check the log for details."
                )
                
        except Exception as e:
            logger.error(f"Error during save: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Save Error",
                f"An error occurred while saving:\n{str(e)}"
            )

    def on_load_clicked(self):
        """Handle load button click - prompts for file and loads complete state."""
        try:
            # Get file path from user
            default_path = Path.cwd() / "saved_states"
            default_path.mkdir(exist_ok=True)
            
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load Application State",
                str(default_path),
                "JSON Files (*.json);;All Files (*.*)"
            )
            
            if not file_path:
                # User cancelled
                return
            
            # Validate file first (single popup flow)
            is_valid, message = validate_state_file(file_path)
            
            if not is_valid:
                QMessageBox.critical(
                    self,
                    "Invalid State File",
                    f"The selected file is not a valid state file:\n\n{message}"
                )
                return
            
            # Get paths
            src_dir = Path(__file__).resolve().parent.parent.parent
            io_config_output_path = src_dir / "IO" / "IO_configuration.json"
            
            # Get simulation manager from mainConfig
            simulation_manager = None
            if hasattr(self, 'mainConfig') and hasattr(self.mainConfig, 'simulationManager'):
                simulation_manager = self.mainConfig.simulationManager
            
            # Load state
            logger.info(f"Loading state from: {file_path}")
            
            success = load_application_state(
                main_config=self.mainConfig,
                simulation_manager=simulation_manager,
                io_config_output_path=str(io_config_output_path),
                load_file_path=file_path
            )
            
            if success:
                # Reload IO configuration in the active simulation
                self._reload_io_config_after_load(str(io_config_output_path))

                # Push loaded config/status into GUI fields to avoid defaults overwriting
                try:
                    if simulation_manager:
                        sim = simulation_manager.get_active_simulation()
                        if sim and hasattr(self, 'apply_loaded_state_to_gui'):
                            logger.info(">>> Calling apply_loaded_state_to_gui...")
                            self.apply_loaded_state_to_gui(
                                getattr(sim, 'config', None),
                                getattr(sim, 'status', None)
                            )
                            logger.info(">>> ✓ State applied to GUI")
                except Exception as e:
                    logger.error(f"ERROR: Could not apply loaded state to GUI fields: {e}", exc_info=True)
                
                # Update GUI to reflect loaded state
                self._update_gui_after_load()
                
                QMessageBox.information(
                    self,
                    "Load Successful",
                    f"Application state loaded successfully from:\n{file_path}\n\n"
                    f"{message}\n\n"
                    f"The application is now ready to run with the loaded configuration."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Load Failed",
                    f"Failed to load application state from:\n{file_path}\n\n"
                    f"Check the log for details."
                )
                
        except Exception as e:
            logger.error(f"Error during load: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Load Error",
                f"An error occurred while loading:\n{str(e)}"
            )

    def _reload_io_config_after_load(self, io_config_path: str):
        """
        Reload IO configuration after loading state.
        
        Args:
            io_config_path: Path to IO configuration file
        """
        try:
            logger.info(f">>> Reloading IO config from: {io_config_path}")
            # Get active simulation
            simulation_manager = None
            if hasattr(self, 'mainConfig') and hasattr(self.mainConfig, 'simulationManager'):
                simulation_manager = self.mainConfig.simulationManager
            
            if simulation_manager:
                active_sim = simulation_manager.get_active_simulation()
                if active_sim and hasattr(active_sim, 'config'):
                    # Reload IO config
                    active_sim.config.load_io_config_from_file(io_config_path)
                    logger.info(f"    ✓ IO configuration loaded from: {io_config_path}")
                    
                    # Update GUI references
                    if hasattr(self, 'tanksim_config'):
                        self.tanksim_config = active_sim.config
                    
                    if hasattr(self, 'tanksim_status'):
                        self.set_simulation_status(active_sim.status)
                    
                    # Load IO tree FIRST (needed for load_all_tags_to_table)
                    try:
                        if hasattr(self, 'load_io_tree'):
                            logger.info("    >>> Loading IO tree for active simulation...")
                            self.load_io_tree()
                            logger.info(f"    ✓ IO tree loaded")
                    except Exception as e:
                        logger.error(f"    ERROR: Could not load IO tree: {e}", exc_info=True)
                    
                    # Now update IO table from loaded config
                    try:
                        # First, load the byte offsets from the JSON file
                        import json
                        with open(io_config_path, 'r', encoding='utf-8') as f:
                            io_config_data = json.load(f)
                        if 'offsets' in io_config_data and hasattr(self, 'io_screen'):
                            self.io_screen.byte_offsets = io_config_data['offsets'].copy()
                            logger.info(f"    ✓ Loaded byte offsets: {io_config_data['offsets']}")
                        
                        # Clear table before loading
                        if hasattr(self, 'tableWidget_IO'):
                            self.tableWidget_IO.setRowCount(0)
                            logger.info("    ✓ Cleared IO table")
                        
                        # Load all tags from IO tree to table (uses offsets)
                        if hasattr(self, 'load_all_tags_to_table'):
                            logger.info("    >>> Loading all tags from tree to table...")
                            self.load_all_tags_to_table()
                            logger.info(f"    ✓ All tags loaded to table")
                        
                        # Then update addresses from config (custom mappings)
                        if hasattr(self, '_update_table_from_config'):
                            logger.info("    >>> Updating table addresses from config...")
                            self._update_table_from_config()
                            logger.info(f"    ✓ Table addresses updated from config")
                    except Exception as e:
                        logger.error(f"    ERROR: Could not update IO table: {e}", exc_info=True)
                    
                    # Start forced write period for IO handler
                    if hasattr(self, 'mainConfig') and hasattr(self.mainConfig, 'ioHandler'):
                        self.mainConfig.ioHandler.start_force_write_period()
                        logger.info("    ✓ Started IO forced write period after load")
                        
        except Exception as e:
            logger.error(f"ERROR: Failed to reload IO config after load: {e}", exc_info=True)

    def _update_gui_after_load(self):
        """Update GUI elements after loading state."""
        try:
            # Update controller dropdown to match loaded protocol
            if hasattr(self, 'controlerDropDown') and hasattr(self, 'mainConfig'):
                protocol = self.mainConfig.plcProtocol
                
                # Map protocol to dropdown text
                protocol_map = {
                    "GUI": "GUI (MIL)",
                    "logo!": "logo! (HIL)",
                    "PLC S7-1500/1200/400/300/ET 200SP": "PLC S7-1500/1200/400/300/ET 200SP (HIL)",
                    "PLCSim S7-1500 advanced": "PLCSim S7-1500 advanced (SIL)",
                    "PLCSim S7-1500/1200/400/300/ET 200SP": "PLCSim S7-1500/1200/400/300/ET 200SP (SIL)"
                }
                
                dropdown_text = protocol_map.get(protocol, protocol)
                
                # Block signals to prevent triggering connection attempts
                self.controlerDropDown.blockSignals(True)
                
                # Try exact display text match first
                if self.controlerDropDown.findText(dropdown_text) >= 0:
                    self.controlerDropDown.setCurrentText(dropdown_text)
                else:
                    # Fallback: try to match by base protocol name (e.g., 'logo!')
                    matched = False
                    for i in range(self.controlerDropDown.count()):
                        item = self.controlerDropDown.itemText(i)
                        if item.startswith(protocol):
                            self.controlerDropDown.setCurrentIndex(i)
                            matched = True
                            break
                    if not matched:
                        # Last resort: set text directly (may not be present in list)
                        self.controlerDropDown.setCurrentText(dropdown_text)
                
                self.controlerDropDown.blockSignals(False)
                
                # Ensure mainConfig matches what we just set (avoid races)
                try:
                    self.mainConfig.plcProtocol = protocol
                except Exception:
                    pass
                
                # Update active method label
                if hasattr(self, '_update_active_method_label'):
                    self._update_active_method_label(protocol)
            
            # Update IP address field
            if hasattr(self, 'lineEdit_IPAddress') and hasattr(self, 'mainConfig'):
                self.lineEdit_IPAddress.blockSignals(True)
                self.lineEdit_IPAddress.setText(self.mainConfig.plcIpAdress)
                self.lineEdit_IPAddress.blockSignals(False)
            
            # Update network adapter selection
            if hasattr(self, 'comboBox_networkPort') and hasattr(self, 'mainConfig'):
                adapter = self.mainConfig.selectedNetworkAdapter
                self.comboBox_networkPort.blockSignals(True)
                index = self.comboBox_networkPort.findText(adapter)
                if index >= 0:
                    self.comboBox_networkPort.setCurrentIndex(index)
                self.comboBox_networkPort.blockSignals(False)
            
            # Disconnect if currently connected (state was loaded, connection is invalid)
            if hasattr(self, 'pushButton_connect'):
                if self.pushButton_connect.isChecked():
                    self.pushButton_connect.blockSignals(True)
                    self.pushButton_connect.setChecked(False)
                    self.pushButton_connect.blockSignals(False)
                    
                    # Update connection state
                    self.validPlcConnection = False
                    self.plc = None
                    
                    # Update icon
                    if hasattr(self, 'update_connection_status_icon'):
                        self.update_connection_status_icon()
            
            # Enable/disable connect button based on protocol
            if hasattr(self, 'pushButton_connect') and hasattr(self, 'mainConfig'):
                is_gui_mode = self.mainConfig.plcProtocol == "GUI"
                self.pushButton_connect.setEnabled(not is_gui_mode)
                if hasattr(self, 'lineEdit_IPAddress'):
                    self.lineEdit_IPAddress.setEnabled(not is_gui_mode)
            
            # Prevent GUI controls from overwriting freshly loaded status for a short window
            try:
                self._suppress_gui_to_status_until = time.monotonic() + 1.0
            except Exception:
                pass
            
            # Update window references to loaded simulation
            try:
                if hasattr(self, 'mainConfig') and hasattr(self.mainConfig, 'simulationManager'):
                    simulation_manager = self.mainConfig.simulationManager
                    active_sim = simulation_manager.get_active_simulation()
                    active_sim_name = simulation_manager.get_active_simulation_name()
                    
                    if active_sim:
                        # Update window references
                        self.tanksim_config = active_sim.config
                        self.set_simulation_status(active_sim.status)
                        logger.info(f"    ✓ Updated window references to loaded simulation: {active_sim_name}")
                        
                        # Map simulation name to page index
                        sim_name_to_index = {
                            "PIDtankValve": 0,
                            "dualTank": 1,
                            "conveyor": 2
                        }
                        
                        # Open the correct simulation page (singleTankPage, dualTankPage, conveyorPage)
                        sim_index = sim_name_to_index.get(active_sim_name)
                        if sim_index is not None and hasattr(self, 'start_simulation'):
                            try:
                                self.start_simulation(sim_index)
                                logger.info(f"    ✓ Opened {active_sim_name} page (index {sim_index})")
                            except Exception as e:
                                logger.warning(f"    Failed to open simulation page: {e}", exc_info=True)
                        
                        # DON'T auto-start simulation on load - user explicitly requested this
                        # simRunning is not saved, so simulation stays stopped
                        logger.info(f"    Simulation will NOT auto-start (simRunning not saved)")
            except Exception as e:
                logger.error(f"Failed to update simulation references: {e}", exc_info=True)

            # Trigger an immediate display refresh from loaded status/config
            try:
                if hasattr(self, 'update_tanksim_display'):
                    self.update_tanksim_display()
                if hasattr(self, '_update_general_controls_ui'):
                    self._update_general_controls_ui()
            except Exception:
                pass
            
            logger.info("GUI updated after state load")
            
        except Exception as e:
            logger.error(f"Failed to update GUI after load: {e}", exc_info=True)

    def apply_loaded_state_to_gui(self, config, status):
        """Apply loaded configuration and status to GUI elements.
        
        Args:
            config: Simulation configuration object
            status: Simulation status object
        """
        try:
            logger.info(">>> Applying loaded state to GUI elements...")
            
            if config:
                # Apply tank color from config
                if hasattr(config, 'tankColor'):
                    colorDropDown = self.findChild(QWidget, "colorDropDown")
                    if colorDropDown:
                        # Find index by color data (hex value)
                        for i in range(colorDropDown.count()):
                            if colorDropDown.itemData(i) == config.tankColor:
                                colorDropDown.blockSignals(True)
                                colorDropDown.setCurrentIndex(i)
                                colorDropDown.blockSignals(False)
                                logger.info(f"    ✓ Set tankColor from config: {config.tankColor}")
                                break
                
                # Apply display checkboxes from config
                if hasattr(config, 'displayLevelSwitches'):
                    levelSwitchesCheckBox = self.findChild(QWidget, "levelSwitchesCheckBox")
                    if levelSwitchesCheckBox:
                        levelSwitchesCheckBox.blockSignals(True)
                        levelSwitchesCheckBox.setChecked(config.displayLevelSwitches)
                        levelSwitchesCheckBox.blockSignals(False)
                        logger.info(f"    ✓ Set displayLevelSwitches from config: {config.displayLevelSwitches}")
                
                if hasattr(config, 'displayTemperature'):
                    analogValueTempCheckBox = self.findChild(QWidget, "analogValueTempCheckBox")
                    if analogValueTempCheckBox:
                        analogValueTempCheckBox.blockSignals(True)
                        analogValueTempCheckBox.setChecked(config.displayTemperature)
                        analogValueTempCheckBox.blockSignals(False)
                        logger.info(f"    ✓ Set displayTemperature from config: {config.displayTemperature}")
                
                # Apply configuration entry fields (tank volume, flows, power, etc.)
                try:
                    # Tank volume (in m³, config stores liters)
                    volumeEntry = self.findChild(QWidget, "volumeEntry")
                    if volumeEntry and hasattr(config, 'tankVolume'):
                        volumeEntry.blockSignals(True)
                        volumeEntry.setText(str(config.tankVolume / 1000.0))  # Convert liters to m³
                        volumeEntry.blockSignals(False)
                        logger.info(f"    ✓ Set tankVolume: {config.tankVolume}L ({config.tankVolume/1000.0}m³)")
                    
                    # Max flow in
                    for entry_name in ['maxFlowInEntry', 'maxFlowInEntry1', 'maxFlowInEntry2']:
                        entry = self.findChild(QWidget, entry_name)
                        if entry and hasattr(config, 'valveInMaxFlow'):
                            entry.blockSignals(True)
                            entry.setText(str(config.valveInMaxFlow))
                            entry.blockSignals(False)
                    if hasattr(config, 'valveInMaxFlow'):
                        logger.info(f"    ✓ Set valveInMaxFlow: {config.valveInMaxFlow}")
                    
                    # Max flow out
                    for entry_name in ['maxFlowOutEntry', 'maxFlowOutEntry1', 'maxFlowOutEntry2']:
                        entry = self.findChild(QWidget, entry_name)
                        if entry and hasattr(config, 'valveOutMaxFlow'):
                            entry.blockSignals(True)
                            entry.setText(str(config.valveOutMaxFlow))
                            entry.blockSignals(False)
                    if hasattr(config, 'valveOutMaxFlow'):
                        logger.info(f"    ✓ Set valveOutMaxFlow: {config.valveOutMaxFlow}")
                    
                    # Heater max power
                    for entry_name in ['powerHeatingCoilEntry', 'powerHeatingCoilEntry2']:
                        entry = self.findChild(QWidget, entry_name)
                        if entry and hasattr(config, 'heaterMaxPower'):
                            entry.blockSignals(True)
                            entry.setText(str(config.heaterMaxPower))
                            entry.blockSignals(False)
                    if hasattr(config, 'heaterMaxPower'):
                        logger.info(f"    ✓ Set heaterMaxPower: {config.heaterMaxPower}")
                    
                    # Other config fields
                    field_mapping = {
                        'ambientTempEntry': 'ambientTemp',
                        'heatLossVatEntry': 'tankHeatLoss',
                        'specificHeatCapacity': 'liquidSpecificHeatCapacity',
                        'boilingTempEntry': 'liquidBoilingTemp',
                        'specificWeightEntry': 'liquidSpecificWeight',
                        'timeDelayfillingEntry': 'liquidVolumeTimeDelay',
                        'timeDelayTempEntry': 'liquidTempTimeDelay',
                    }
                    
                    for entry_name, config_attr in field_mapping.items():
                        entry = self.findChild(QWidget, entry_name)
                        if entry and hasattr(config, config_attr):
                            value = getattr(config, config_attr)
                            # Convert density from kg/L to kg/m³ for UI
                            if config_attr == 'liquidSpecificWeight':
                                value = value * 1000.0
                            entry.blockSignals(True)
                            entry.setText(str(value))
                            entry.blockSignals(False)
                            logger.info(f"    ✓ Set {config_attr}: {getattr(config, config_attr)}")
                    
                    # Level switch thresholds (% of tank volume)
                    if hasattr(config, 'digitalLevelSensorHighTriggerLevel') and hasattr(config, 'tankVolume') and config.tankVolume > 0:
                        levelSwitchMaxHeightEntry = self.findChild(QWidget, "levelSwitchMaxHeightEntry")
                        if levelSwitchMaxHeightEntry:
                            high_pct = (config.digitalLevelSensorHighTriggerLevel / config.tankVolume) * 100.0
                            levelSwitchMaxHeightEntry.blockSignals(True)
                            levelSwitchMaxHeightEntry.setText(str(high_pct))
                            levelSwitchMaxHeightEntry.blockSignals(False)
                            logger.info(f"    ✓ Set digitalLevelSensorHighTriggerLevel: {high_pct}% ({config.digitalLevelSensorHighTriggerLevel}L)")
                    
                    if hasattr(config, 'digitalLevelSensorLowTriggerLevel') and hasattr(config, 'tankVolume') and config.tankVolume > 0:
                        levelSwitchMinHeightEntry = self.findChild(QWidget, "levelSwitchMinHeightEntry")
                        if levelSwitchMinHeightEntry:
                            low_pct = (config.digitalLevelSensorLowTriggerLevel / config.tankVolume) * 100.0
                            levelSwitchMinHeightEntry.blockSignals(True)
                            levelSwitchMinHeightEntry.setText(str(low_pct))
                            levelSwitchMinHeightEntry.blockSignals(False)
                            logger.info(f"    ✓ Set digitalLevelSensorLowTriggerLevel: {low_pct}% ({config.digitalLevelSensorLowTriggerLevel}L)")
                            
                except Exception as e:
                    logger.warning(f"Could not set config entry fields: {e}", exc_info=True)
            
            logger.info(">>> ✓ Loaded state applied to GUI successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply loaded state to GUI: {e}", exc_info=True)

