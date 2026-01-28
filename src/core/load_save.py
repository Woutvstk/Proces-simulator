"""
Complete Save/Load Module - Application State Management with GUI Integration

ARCHITECTURE:
- StateManager: Core serialization/deserialization logic (no GUI)
- StateManager.save_state_interactive(): Save with file dialog (GUI caller)
- StateManager.load_state_interactive(): Load with file dialog + GUI sync (GUI caller)
- Helper functions: Sync GUI↔Status, Apply mode visuals

FUNCTIONALITY SNAPSHOT:
1. Save: Captures complete state (config, status, IO) → JSON file
2. Load: Restores exact snapshot + syncs GUI + locks IO handler during load
3. GUI Sync: Bi-directional sync between user inputs and internal state

External Libraries:
- json, logging, pathlib, datetime (standard library)
- PyQt5 (GUI dialogs and widgets)
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .simulationManager import SimulationManager
    from .configuration import configuration

logger = logging.getLogger(__name__)


class StateManager:
    """
    Core state management: serialize/deserialize application state.
    Handles: configuration, simulation data, IO settings, status.
    """
    
    VERSION = "2.0"
    
    def __init__(self):
        """Initialize state manager."""
        pass
    
    # =========================================================================
    # SERIALIZATION HELPERS
    # =========================================================================
    
    @staticmethod
    def _serialize_object_to_dict(obj: Any) -> Dict[str, Any]:
        """Convert object to JSON-serializable dictionary."""
        result = {}
        export_list = getattr(obj, 'importExportVariableList', None)
        
        if export_list:
            for var in export_list:
                if hasattr(obj, var):
                    value = getattr(obj, var)
                    result[var] = value.copy() if isinstance(value, dict) else value
        else:
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):
                    result[key] = value.copy() if isinstance(value, dict) else value
        
        return result
    
    @staticmethod
    def _deserialize_dict_to_object(obj: Any, data: Dict[str, Any]) -> None:
        """Restore object attributes from dictionary."""
        for key, value in data.items():
            if hasattr(obj, key):
                try:
                    current_value = getattr(obj, key)
                    current_type = type(current_value)
                    
                    if isinstance(current_value, dict) and isinstance(value, dict):
                        setattr(obj, key, value.copy())
                    elif current_type in (int, float, str, bool):
                        setattr(obj, key, current_type(value))
                    else:
                        setattr(obj, key, value)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Could not convert {key}={value}: {e}")
                    setattr(obj, key, value)
    
    # =========================================================================
    # CORE SAVE/LOAD (NO GUI)
    # =========================================================================
    
    def save_state(
        self,
        main_config: 'configuration',
        simulation_manager: Optional['SimulationManager'],
        io_config_path: str,
        save_file_path: str
    ) -> bool:
        """
        CORE SAVE: Serialize all state to JSON file.
        
        Saves: main_config, simulation (config+status), IO configuration
        Returns: True if success, False if failure
        """
        try:
            logger.info(f"[SAVE] Serializing state to: {save_file_path}")
            
            # Make IO path relative for portability
            try:
                io_config_relative = Path(io_config_path).relative_to(Path(__file__).parent.parent)
                io_config_path_str = str(io_config_relative).replace('\\', '/')
            except (ValueError, AttributeError):
                io_config_path_str = Path(io_config_path).name
            
            state_data = {
                "version": self.VERSION,
                "timestamp": datetime.now().isoformat(),
                "description": "PLC Simulator - Complete State Snapshot",
                "main_config": {},
                "active_simulation": None,
                "simulation_config": {},
                "simulation_status": {},
                "io_config": None,
                "io_config_original_path": io_config_path_str
            }
            
            # 1. Main configuration
            if hasattr(main_config, 'importExportVariableList'):
                for var in main_config.importExportVariableList:
                    if hasattr(main_config, var):
                        state_data["main_config"][var] = getattr(main_config, var)
            
            # 2. Simulation state
            if simulation_manager:
                sim_name = simulation_manager.get_active_simulation_name()
                active_sim = simulation_manager.get_active_simulation()
                
                if active_sim and sim_name:
                    state_data["active_simulation"] = sim_name
                    
                    if hasattr(active_sim, 'config'):
                        state_data["simulation_config"] = self._serialize_object_to_dict(active_sim.config)
                        logger.info(f"[SAVE]   Config: {len(state_data['simulation_config'])} vars")
                    
                    if hasattr(active_sim, 'status'):
                        state_data["simulation_status"] = self._serialize_object_to_dict(active_sim.status)
                        logger.info(f"[SAVE]   Status: {len(state_data['simulation_status'])} vars")
            
            # 3. IO configuration
            io_path = Path(io_config_path)
            if io_path.exists():
                try:
                    with open(io_path, 'r') as f:
                        state_data["io_config"] = json.load(f)
                    logger.info(f"[SAVE]   IO Config: embedded")
                except Exception as e:
                    logger.warning(f"[SAVE]   IO Config: failed to load ({e})")
            
            # 4. Write JSON
            save_path = Path(save_file_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            logger.info(f"[SAVE] ✓ Success ({save_path.stat().st_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"[SAVE] ✗ Failed: {e}", exc_info=True)
            return False
    
    def load_state(
        self,
        main_config: 'configuration',
        simulation_manager: Optional['SimulationManager'],
        io_config_output_path: str,
        load_file_path: str
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        CORE LOAD: Deserialize state from JSON file.
        
        Returns: (success: bool, state_data: dict or None)
        Caller must handle GUI sync + IO reload.
        """
        try:
            load_path = Path(load_file_path)
            
            if not load_path.exists():
                logger.error(f"[LOAD] ✗ File not found: {load_file_path}")
                return False, None
            
            logger.info(f"[LOAD] Reading state from: {load_file_path}")
            
            # Load JSON
            try:
                with open(load_path, 'r') as f:
                    state_data = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"[LOAD] ✗ Invalid JSON: {e}")
                return False, None
            
            # Validate
            if not all(k in state_data for k in ["version", "main_config"]):
                logger.error(f"[LOAD] ✗ Invalid structure")
                return False, None
            
            logger.info(f"[LOAD] Version: {state_data.get('version')}")
            
            # Load main config
            logger.info(f"[LOAD] Restoring main_config...")
            main_config_data = state_data.get("main_config", {})
            
            if hasattr(main_config, 'importExportVariableList'):
                for var in main_config.importExportVariableList:
                    if var in main_config_data:
                        try:
                            current_value = getattr(main_config, var)
                            current_type = type(current_value)
                            new_value = main_config_data[var]
                            try:
                                converted = current_type(new_value)
                            except Exception:
                                converted = new_value
                            setattr(main_config, var, converted)
                            logger.info(f"[LOAD]   {var} = {getattr(main_config, var)!r}")
                        except Exception as e:
                            logger.warning(f"[LOAD]   {var}: failed ({e})")
            
            logger.info(f"[LOAD] Main config restored")
            
            # Extract IO config
            if state_data.get("io_config"):
                try:
                    io_output_path = Path(io_config_output_path)
                    io_output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(io_output_path, 'w') as f:
                        json.dump(state_data["io_config"], f, indent=2)
                    
                    logger.info(f"[LOAD] IO config extracted")
                except Exception as e:
                    logger.error(f"[LOAD] ✗ Failed to extract IO config: {e}")
                    return False, None
            
            # Load simulation
            if simulation_manager and state_data.get("active_simulation"):
                sim_name = state_data["active_simulation"]
                
                if sim_name not in simulation_manager.get_registered_simulations():
                    logger.error(f"[LOAD] ✗ Simulation not registered: {sim_name}")
                    return False, None
                
                if not simulation_manager.load_simulation(sim_name, sim_name + "_loaded"):
                    logger.error(f"[LOAD] ✗ Failed to load simulation: {sim_name}")
                    return False, None
                
                logger.info(f"[LOAD] Simulation '{sim_name}' loaded")
                
                active_sim = simulation_manager.get_active_simulation()
                if active_sim:
                    # Restore config
                    if state_data.get("simulation_config") and hasattr(active_sim, 'config'):
                        self._deserialize_dict_to_object(
                            active_sim.config,
                            state_data["simulation_config"]
                        )
                        logger.info(f"[LOAD]   Config restored")
                    
                    # Restore status + apply load fixes
                    if state_data.get("simulation_status") and hasattr(active_sim, 'status'):
                        self._deserialize_dict_to_object(
                            active_sim.status,
                            state_data["simulation_status"]
                        )
                        logger.info(f"[LOAD]   Status restored")
                        
                        # CRITICAL FIX: PLC mode → clear manual values + lock flags
                        if hasattr(main_config, 'plcGuiControl') and main_config.plcGuiControl == 'plc':
                            logger.info(f"[LOAD] PLC mode detected - clearing manual actuator values")
                            
                            # Clear manual values
                            if hasattr(active_sim.status, 'valveInOpenFraction'):
                                active_sim.status.valveInOpenFraction = 0.0
                            if hasattr(active_sim.status, 'valveOutOpenFraction'):
                                active_sim.status.valveOutOpenFraction = 0.0
                            if hasattr(active_sim.status, 'heaterPowerFraction'):
                                active_sim.status.heaterPowerFraction = 0.0
                            
                            # Force Auto mode
                            if hasattr(active_sim.status, 'pidPidValveManCmd'):
                                active_sim.status.pidPidValveManCmd = False
                            if hasattr(active_sim.status, 'pidPidValveAutoCmd'):
                                active_sim.status.pidPidValveAutoCmd = True
                            
                            # Lock flags for 3 seconds
                            if hasattr(active_sim.status, '_lock_status_flags_until'):
                                active_sim.status._lock_status_flags_until = time.monotonic() + 3.0
                            
                            logger.info(f"[LOAD] ✓ Manual values cleared + flags locked for 3 sec")
            
            logger.info(f"[LOAD] ✓ Success")
            return True, state_data
            
        except Exception as e:
            logger.error(f"[LOAD] ✗ Failed: {e}", exc_info=True)
            return False, None
    
    def validate_state_file(self, file_path: str) -> tuple[bool, str]:
        """Check if file is valid state file."""
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                return False, f"File not found"
            
            try:
                with open(file_path_obj, 'r') as f:
                    state_data = json.load(f)
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON: {str(e)}"
            
            if not all(k in state_data for k in ["version", "main_config"]):
                return False, f"Invalid structure"
            
            version = state_data.get("version", "unknown")
            timestamp = state_data.get("timestamp", "unknown")
            sim_name = state_data.get("active_simulation", "None")
            has_io = state_data.get("io_config") is not None
            
            message = (
                f"Valid state file (v{version})\n"
                f"Timestamp: {timestamp}\n"
                f"Simulation: {sim_name}\n"
                f"IO Config: {'Included' if has_io else 'Not included'}"
            )
            
            return True, message
            
        except Exception as e:
            return False, f"Error: {str(e)}"


# =========================================================================
# GUI INTEGRATION FUNCTIONS (Called from MainWindow)
# =========================================================================

def save_state_interactive(main_window: Any) -> bool:
    """
    INTERACTIVE SAVE: Show dialog + save + show result.
    
    Args:
        main_window: Qt MainWindow instance (has mainConfig, simulation refs)
        
    Returns: True if saved, False if cancelled/failed
    """
    try:
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        
        # Show file dialog
        default_path = Path.cwd() / "saved_states"
        default_path.mkdir(exist_ok=True)
        
        file_path, _ = QFileDialog.getSaveFileName(
            main_window,
            "Save Application State",
            str(default_path / "simulation_state.json"),
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not file_path:
            return False
        
        if not file_path.endswith('.json'):
            file_path += '.json'
        
        # Sync GUI → Status (capture current user inputs)
        _sync_gui_to_status_before_save(main_window)
        
        # Save
        src_dir = Path(__file__).resolve().parent.parent
        io_config_path = src_dir / "IO" / "IO_configuration.json"
        
        simulation_manager = None
        if hasattr(main_window, 'mainConfig') and hasattr(main_window.mainConfig, 'simulationManager'):
            simulation_manager = main_window.mainConfig.simulationManager
        
        manager = StateManager()
        success = manager.save_state(
            main_config=main_window.mainConfig,
            simulation_manager=simulation_manager,
            io_config_path=str(io_config_path),
            save_file_path=file_path
        )
        
        if success:
            QMessageBox.information(
                main_window,
                "Save Successful",
                f"State saved to:\n{file_path}"
            )
        else:
            QMessageBox.critical(
                main_window,
                "Save Failed",
                f"Failed to save state.\nSee log for details."
            )
        
        return success
        
    except Exception as e:
        logger.error(f"save_state_interactive failed: {e}", exc_info=True)
        return False


def load_state_interactive(main_window: Any) -> bool:
    """
    INTERACTIVE LOAD: Show dialog + load + sync GUI + reload IO.
    
    Args:
        main_window: Qt MainWindow instance
        
    Returns: True if loaded, False if cancelled/failed
    """
    try:
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        
        # Show file dialog
        default_path = Path.cwd() / "saved_states"
        default_path.mkdir(exist_ok=True)
        
        file_path, _ = QFileDialog.getOpenFileName(
            main_window,
            "Load Application State",
            str(default_path),
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not file_path:
            return False
        
        # Validate
        manager = StateManager()
        is_valid, message = manager.validate_state_file(file_path)
        
        if not is_valid:
            QMessageBox.critical(
                main_window,
                "Invalid State File",
                f"File is not a valid state file:\n\n{message}"
            )
            return False
        
        # Load
        src_dir = Path(__file__).resolve().parent.parent
        io_config_output_path = src_dir / "IO" / "IO_configuration.json"
        
        simulation_manager = None
        if hasattr(main_window, 'mainConfig') and hasattr(main_window.mainConfig, 'simulationManager'):
            simulation_manager = main_window.mainConfig.simulationManager
        
        success, state_data = manager.load_state(
            main_config=main_window.mainConfig,
            simulation_manager=simulation_manager,
            io_config_output_path=str(io_config_output_path),
            load_file_path=file_path
        )
        
        if not success:
            QMessageBox.critical(
                main_window,
                "Load Failed",
                f"Failed to load state.\nSee log for details."
            )
            return False
        
        # Post-load operations
        try:
            _reload_io_config_after_load(main_window, str(io_config_output_path))
            _sync_status_to_gui_after_load(main_window, state_data)
            _apply_gui_mode_visuals_after_load(main_window)
        except Exception as e:
            logger.error(f"Post-load sync failed: {e}", exc_info=True)
            QMessageBox.warning(
                main_window,
                "Load Complete (Partial)",
                f"State loaded but GUI sync had issues.\nSee log for details."
            )
            return True
        
        QMessageBox.information(
            main_window,
            "Load Successful",
            f"State loaded from:\n{file_path}\n\n{message}"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"load_state_interactive failed: {e}", exc_info=True)
        return False


# =========================================================================
# GUI SYNC HELPERS
# =========================================================================

def _sync_gui_to_status_before_save(main_window: Any) -> None:
    """
    Capture all GUI inputs and sync to simulation status before saving.
    This ensures the JSON captures what user entered.
    """
    try:
        from PyQt5.QtWidgets import QLineEdit, QSlider, QRadioButton, QPushButton
        
        if not hasattr(main_window, 'mainConfig'):
            return
        
        simulation_manager = getattr(main_window.mainConfig, 'simulationManager', None)
        if not simulation_manager:
            return
        
        active_sim = simulation_manager.get_active_simulation()
        if not active_sim or not hasattr(active_sim, 'status'):
            return
        
        status = active_sim.status
        
        logger.info("[SAVE] Syncing GUI values to status...")
        
        # Auto/Manual buttons
        auto_btn = main_window.findChild(QPushButton, "pushButton_PidValveAuto")
        man_btn = main_window.findChild(QPushButton, "pushButton_PidValveMan")
        if auto_btn and man_btn:
            status.pidPidValveAutoCmd = auto_btn.isChecked()
            status.pidPidValveManCmd = man_btn.isChecked()
            logger.info(f"[SAVE]   Auto/Man: {auto_btn.isChecked()}/{man_btn.isChecked()}")
        
        # Analog/Digital radios
        radio_ai_temp = main_window.findChild(QRadioButton, "radioButton_PidTankValveAItemp")
        radio_di_temp = main_window.findChild(QRadioButton, "radioButton_PidTankValveDItemp")
        if radio_ai_temp:
            status.pidPidTankValveAItempCmd = radio_ai_temp.isChecked()
            status.pidPidTankValveDItempCmd = not radio_ai_temp.isChecked()
        
        radio_ai_level = main_window.findChild(QRadioButton, "radioButton_PidTankValveAIlevel")
        radio_di_level = main_window.findChild(QRadioButton, "radioButton_PidTankValveDIlevel")
        if radio_ai_level:
            status.pidPidTankValveAIlevelCmd = radio_ai_level.isChecked()
            status.pidPidTankValveDIlevelCmd = not radio_ai_level.isChecked()
        
        # Heater slider
        for slider_name in ["heaterPowerSlider", "heaterPowerSlider_1", "heaterPowerSlider_2", "heaterPowerSlider_3"]:
            slider = main_window.findChild(QSlider, slider_name)
            if slider:
                status.heaterPowerFraction = slider.value() / 100.0
                break
        
        # Setpoint sliders
        slider_temp = main_window.findChild(QSlider, "slider_PidTankTempSP")
        if slider_temp:
            status.pidPidTankTempSPValue = slider_temp.value()
        
        slider_level = main_window.findChild(QSlider, "slider_PidTankLevelSP")
        if slider_level:
            status.pidPidTankLevelSPValue = slider_level.value()
        
        # Valve entries
        valve_in_entry = main_window.findChild(QLineEdit, "valveInEntry")
        if valve_in_entry:
            try:
                val = float(valve_in_entry.text() or 0)
                status.valveInOpenFraction = val / 100.0
            except ValueError:
                pass
        
        valve_out_entry = main_window.findChild(QLineEdit, "valveOutEntry")
        if valve_out_entry:
            try:
                val = float(valve_out_entry.text() or 0)
                status.valveOutOpenFraction = val / 100.0
            except ValueError:
                pass
        
        logger.info("[SAVE]   ✓ GUI sync complete")
        
    except Exception as e:
        logger.warning(f"[SAVE] GUI sync failed: {e}", exc_info=True)


def _reload_io_config_after_load(main_window: Any, io_config_path: str) -> None:
    """Reload IO configuration and update tables."""
    try:
        logger.info("[LOAD] Reloading IO configuration...")
        
        simulation_manager = None
        if hasattr(main_window, 'mainConfig') and hasattr(main_window.mainConfig, 'simulationManager'):
            simulation_manager = main_window.mainConfig.simulationManager
        
        if not simulation_manager:
            return
        
        active_sim = simulation_manager.get_active_simulation()
        if not active_sim or not hasattr(active_sim, 'config'):
            return
        
        # Load IO config
        active_sim.config.load_io_config_from_file(io_config_path)
        logger.info("[LOAD]   IO config loaded")
        
        # Update GUI refs
        if hasattr(main_window, 'tanksim_config'):
            main_window.tanksim_config = active_sim.config
        if hasattr(main_window, 'set_simulation_status'):
            main_window.set_simulation_status(active_sim.status)
        
        # Reload IO tree and table
        if hasattr(main_window, 'load_io_tree'):
            main_window.load_io_tree()
        
        if hasattr(main_window, 'load_all_tags_to_table'):
            main_window.load_all_tags_to_table()
        
        if hasattr(main_window, '_update_table_from_config'):
            main_window._update_table_from_config()
        
        # Start forced write period
        if hasattr(main_window, 'mainConfig') and hasattr(main_window.mainConfig, 'ioHandler'):
            main_window.mainConfig.ioHandler.start_force_write_period()
        
        logger.info("[LOAD]   ✓ IO reloaded")
        
    except Exception as e:
        logger.warning(f"[LOAD] IO reload failed: {e}", exc_info=True)


def _sync_status_to_gui_after_load(main_window: Any, state_data: Dict[str, Any]) -> None:
    """Sync loaded status values back to GUI widgets."""
    try:
        from PyQt5.QtWidgets import QLineEdit, QSlider, QComboBox, QCheckBox, QRadioButton, QPushButton
        
        logger.info("[LOAD] Syncing status to GUI...")
        
        simulation_manager = None
        if hasattr(main_window, 'mainConfig') and hasattr(main_window.mainConfig, 'simulationManager'):
            simulation_manager = main_window.mainConfig.simulationManager
        
        if not simulation_manager:
            return
        
        active_sim = simulation_manager.get_active_simulation()
        if not active_sim:
            return
        
        # Update GUI from config
        if hasattr(active_sim, 'config'):
            config = active_sim.config
            
            # Tank volume
            volume_entry = main_window.findChild(QLineEdit, "volumeEntry")
            if volume_entry and hasattr(config, 'tankVolume'):
                volume_entry.blockSignals(True)
                volume_entry.setText(str(config.tankVolume / 1000.0))
                volume_entry.blockSignals(False)
            
            # Max flows
            for entry_name, config_attr in [
                ('maxFlowInEntry', 'valveInMaxFlow'),
                ('maxFlowOutEntry', 'valveOutMaxFlow'),
                ('powerHeatingCoilEntry', 'heaterMaxPower'),
            ]:
                entry = main_window.findChild(QLineEdit, entry_name)
                if entry and hasattr(config, config_attr):
                    entry.blockSignals(True)
                    entry.setText(str(getattr(config, config_attr)))
                    entry.blockSignals(False)
            
            # Display checkboxes
            level_cb = main_window.findChild(QCheckBox, "levelSwitchesCheckBox")
            if level_cb and hasattr(config, 'displayLevelSwitches'):
                level_cb.blockSignals(True)
                level_cb.setChecked(config.displayLevelSwitches)
                level_cb.blockSignals(False)
            
            temp_cb = main_window.findChild(QCheckBox, "analogValueTempCheckBox")
            if temp_cb and hasattr(config, 'displayTemperature'):
                temp_cb.blockSignals(True)
                temp_cb.setChecked(config.displayTemperature)
                temp_cb.blockSignals(False)
        
        # Update GUI from status
        if hasattr(active_sim, 'status'):
            status = active_sim.status
            
            # Heater slider
            for slider_name in ["heaterPowerSlider", "heaterPowerSlider_1", "heaterPowerSlider_2"]:
                slider = main_window.findChild(QSlider, slider_name)
                if slider and hasattr(status, 'heaterPowerFraction'):
                    slider.blockSignals(True)
                    slider.setValue(int(status.heaterPowerFraction * 100))
                    slider.blockSignals(False)
                    break
            
            # Setpoint sliders
            slider_temp = main_window.findChild(QSlider, "slider_PidTankTempSP")
            if slider_temp and hasattr(status, 'pidPidTankTempSPValue'):
                slider_temp.blockSignals(True)
                slider_temp.setValue(status.pidPidTankTempSPValue)
                slider_temp.blockSignals(False)
            
            slider_level = main_window.findChild(QSlider, "slider_PidTankLevelSP")
            if slider_level and hasattr(status, 'pidPidTankLevelSPValue'):
                slider_level.blockSignals(True)
                slider_level.setValue(status.pidPidTankLevelSPValue)
                slider_level.blockSignals(False)
        
        logger.info("[LOAD]   ✓ GUI sync complete")
        
    except Exception as e:
        logger.warning(f"[LOAD] GUI sync failed: {e}", exc_info=True)


def _apply_gui_mode_visuals_after_load(main_window: Any) -> None:
    """Apply Auto/Manual mode button visuals after load."""
    try:
        from PyQt5.QtWidgets import QPushButton
        
        logger.info("[LOAD] Applying mode visuals...")
        
        simulation_manager = None
        if hasattr(main_window, 'mainConfig') and hasattr(main_window.mainConfig, 'simulationManager'):
            simulation_manager = main_window.mainConfig.simulationManager
        
        if not simulation_manager:
            return
        
        active_sim = simulation_manager.get_active_simulation()
        if not active_sim or not hasattr(active_sim, 'status'):
            return
        
        status = active_sim.status
        
        # Start simulation page
        if hasattr(main_window, 'start_simulation'):
            sim_name = simulation_manager.get_active_simulation_name()
            sim_name_to_index = {"PIDtankValve": 0, "dualTank": 1, "conveyor": 2}
            if sim_name in sim_name_to_index:
                main_window.start_simulation(sim_name_to_index[sim_name])
        
        # Sync button states
        auto_btn = main_window.findChild(QPushButton, "pushButton_PidValveAuto")
        man_btn = main_window.findChild(QPushButton, "pushButton_PidValveMan")
        
        if auto_btn and man_btn:
            auto_state = getattr(status, 'pidPidValveAutoCmd', True)
            man_state = getattr(status, 'pidPidValveManCmd', False)
            
            auto_btn.blockSignals(True)
            man_btn.blockSignals(True)
            auto_btn.setChecked(auto_state)
            man_btn.setChecked(man_state)
            auto_btn.blockSignals(False)
            man_btn.blockSignals(False)
            
            logger.info(f"[LOAD]   Auto/Man buttons: {auto_state}/{man_state}")
        
        # Update control groupbox visuals
        if hasattr(main_window, 'vat_widget') and hasattr(main_window.vat_widget, '_update_control_groupboxes'):
            main_window.vat_widget._update_control_groupboxes()
        
        logger.info("[LOAD]   ✓ Mode visuals applied")
        
    except Exception as e:
        logger.warning(f"[LOAD] Mode visuals failed: {e}", exc_info=True)


# =========================================================================
# GLOBAL INSTANCE + CONVENIENCE FUNCTIONS
# =========================================================================

_state_manager = StateManager()

def save_application_state(
    main_config: 'configuration',
    simulation_manager: Optional['SimulationManager'],
    io_config_path: str,
    save_file_path: str
) -> bool:
    """Non-interactive save (for internal use)."""
    return _state_manager.save_state(main_config, simulation_manager, io_config_path, save_file_path)

def load_application_state(
    main_config: 'configuration',
    simulation_manager: Optional['SimulationManager'],
    io_config_output_path: str,
    load_file_path: str
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """Non-interactive load (for internal use)."""
    return _state_manager.load_state(main_config, simulation_manager, io_config_output_path, load_file_path)

def validate_state_file(file_path: str) -> tuple[bool, str]:
    """Validate state file."""
    return _state_manager.validate_state_file(file_path)


# =========================================================================
# MIXIN FOR MAINWINDOW (replaces saveLoadPage.SaveLoadMixin)
# =========================================================================

class SaveLoadMixin:
    """Qt Mixin for MainWindow - provides save/load button handlers."""
    
    def init_save_load_page(self):
        """Initialize save/load button connections."""
        try:
            from PyQt5.QtWidgets import QPushButton
            
            buttons = [
                ('pushButton_Save', self.on_save_clicked),
                ('pushButton_Save2', self.on_save_clicked),
                ('pushButton_Load', self.on_load_clicked),
                ('pushButton_Load2', self.on_load_clicked),
            ]
            
            for button_name, callback in buttons:
                btn = self.findChild(QPushButton, button_name)
                if btn:
                    btn.clicked.connect(callback)
            
            logger.info("[INIT] Save/Load buttons connected")
        except Exception as e:
            logger.error(f"[INIT] Failed to init save/load buttons: {e}")
    
    def on_save_clicked(self):
        """Handle Save button click."""
        save_state_interactive(self)
    
    def on_load_clicked(self):
        """Handle Load button click."""
        load_state_interactive(self)
