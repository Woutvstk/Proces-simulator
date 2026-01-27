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
from PyQt5.QtWidgets import QFileDialog, QMessageBox
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
                    
                    # Apply loaded IO config to GUI table
                    try:
                        if hasattr(self, 'apply_loaded_io_config'):
                            logger.info("    >>> Applying loaded IO config to GUI table...")
                            result = self.apply_loaded_io_config(Path(io_config_path))
                            logger.info(f"    ✓ IO config applied to GUI: {result}")
                    except Exception as e:
                        logger.error(f"    ERROR: Could not apply loaded IO config to GUI: {e}", exc_info=True)
                    
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
