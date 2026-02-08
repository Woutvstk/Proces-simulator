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
                    result[var] = value.copy() if isinstance(
                        value, dict) else value
        else:
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):
                    result[key] = value.copy() if isinstance(
                        value, dict) else value

        return result

    @staticmethod
    def _deserialize_dict_to_object(obj: Any, data: Dict[str, Any]) -> None:
        """Restore object attributes from dictionary."""
        logger.info(f"[DESERIALIZE] Starting deserialization with {len(data)} attributes")
        for key, value in data.items():
            if hasattr(obj, key):
                try:
                    current_value = getattr(obj, key)
                    current_type = type(current_value)

                    if isinstance(current_value, dict) and isinstance(value, dict):
                        setattr(obj, key, value.copy())
                        logger.info(f"  [DESERIALIZE] {key} = {value} (dict)")
                    elif current_type in (int, float, str, bool):
                        converted_value = current_type(value)
                        setattr(obj, key, converted_value)
                        logger.info(f"  [DESERIALIZE] {key} = {converted_value} (from JSON: {value})")
                    else:
                        setattr(obj, key, value)
                        logger.info(f"  [DESERIALIZE] {key} = {value} (direct)")
                except (TypeError, ValueError) as e:
                    logger.warning(f"Could not convert {key}={value}: {e}")
                    setattr(obj, key, value)
            else:
                logger.info(f"  [DESERIALIZE] Skipping {key} (not in object)")
        logger.info(f"[DESERIALIZE] Completed deserialization")

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
                io_config_relative = Path(io_config_path).relative_to(
                    Path(__file__).parent.parent)
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
                        state_data["main_config"][var] = getattr(
                            main_config, var)

            # 2. Simulation state
            if simulation_manager:
                sim_name = simulation_manager.get_active_simulation_name()
                active_sim = simulation_manager.get_active_simulation()

                if active_sim and sim_name:
                    state_data["active_simulation"] = sim_name

                    if hasattr(active_sim, 'config'):
                        state_data["simulation_config"] = self._serialize_object_to_dict(
                            active_sim.config)
                        logger.info(
                            f"[SAVE]   Config: {len(state_data['simulation_config'])} vars")

                    if hasattr(active_sim, 'status'):
                        state_data["simulation_status"] = self._serialize_object_to_dict(
                            active_sim.status)
                        logger.info(
                            f"[SAVE]   Status: {len(state_data['simulation_status'])} vars")

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
                            logger.info(
                                f"[LOAD]   {var} = {getattr(main_config, var)!r}")
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
                    logger.error(
                        f"[LOAD] ✗ Simulation not registered: {sim_name}")
                    return False, None

                if not simulation_manager.load_simulation(sim_name, sim_name + "_loaded"):
                    logger.error(
                        f"[LOAD] ✗ Failed to load simulation: {sim_name}")
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
                            logger.info(
                                f"[LOAD] PLC mode detected - clearing manual actuator values")

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

                            # Lock flags for 5 seconds - always set, don't check hasattr
                            active_sim.status._lock_status_flags_until = time.monotonic() + 5.0

                            logger.info(
                                f"[LOAD] ✓ Manual values cleared + flags locked for 5 sec")

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
            # CRITICAL: Set flag to prevent write_gui_values_to_status() from
            # overwriting config during load (main loop race condition fix)
            main_window._loading_state = True
            logger.info("[LOAD] ✓ Loading flag set - blocking write_gui_values_to_status()")

            # 0. FIRST: Clear GUI inputs in Auto mode to prevent timer writes with stale values
            # This MUST happen before any other GUI sync to prevent race conditions
            _clear_gui_inputs_in_auto_mode(main_window, state_data)

            # 1. Activate protocol from loaded config (must be second to set up protocolManager)
            _activate_protocol_after_load(main_window)

            # 1.5 CRITICAL: Write saved IO signals to IO_configuration.json BEFORE reload
            # This ensures only saved signals are loaded
            if 'io_config' in state_data:
                import json
                io_config_data = state_data['io_config']
                num_signals = len(io_config_data.get('signals', []))
                logger.info(f"[LOAD] Writing {num_signals} saved signals to IO_configuration.json")
                
                with open(io_config_output_path, 'w', encoding='utf-8') as f:
                    json.dump(io_config_data, f, indent=2, ensure_ascii=False)
                
                logger.info("[LOAD]   ✓ IO_configuration.json updated with saved signals")

            # 2. Reload IO configuration
            _reload_io_config_after_load(
                main_window, str(io_config_output_path))

            # 3. Sync GUI widgets with loaded status
            _sync_status_to_gui_after_load(main_window, state_data)

            # 3.5. Populate ALL config parameters to entry fields (comprehensive)
            _populate_all_config_to_gui(main_window)

            # 4. Apply visual updates (buttons, controls) - NO clearing here, done in step 0
            _apply_gui_mode_visuals_after_load(main_window)

            # 5. Auto-connect if PLC mode was active
            _auto_connect_after_load(main_window)

            # CRITICAL: Clear flag to re-enable write_gui_values_to_status()
            main_window._loading_state = False
            logger.info("[LOAD] ✓ Loading flag cleared - write_gui_values_to_status() re-enabled")
            
        except Exception as e:
            logger.error(f"Post-load sync failed: {e}", exc_info=True)
            main_window._loading_state = False  # Clear flag even on error
            QMessageBox.warning(
                main_window,
                "Load Complete (Partial)",
                f"State loaded but GUI sync had issues.\nSee log for details."
            )
            return True

        logger.info(f"[LOAD] ========== SHOWING SUCCESS POPUP ==========")
        QMessageBox.information(
            main_window,
            "Load Successful",
            f"State loaded from:\n{file_path}\n\n{message}"
        )
        logger.info(f"[LOAD] ========== SUCCESS POPUP SHOWN ==========")

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

        simulation_manager = getattr(
            main_window.mainConfig, 'simulationManager', None)
        if not simulation_manager:
            return

        active_sim = simulation_manager.get_active_simulation()
        if not active_sim or not hasattr(active_sim, 'status'):
            return

        status = active_sim.status

        logger.info("[SAVE] Syncing GUI values to status...")

        # Auto/Manual buttons
        auto_btn = main_window.findChild(
            QPushButton, "pushButton_PidValveAuto")
        man_btn = main_window.findChild(QPushButton, "pushButton_PidValveMan")
        if auto_btn and man_btn:
            status.pidPidValveAutoCmd = auto_btn.isChecked()
            status.pidPidValveManCmd = man_btn.isChecked()
            logger.info(
                f"[SAVE]   Auto/Man: {auto_btn.isChecked()}/{man_btn.isChecked()}")

        # Analog/Digital radios
        radio_ai_temp = main_window.findChild(
            QRadioButton, "radioButton_PidTankValveAItemp")
        radio_di_temp = main_window.findChild(
            QRadioButton, "radioButton_PidTankValveDItemp")
        if radio_ai_temp:
            status.pidPidTankValveAItempCmd = radio_ai_temp.isChecked()
            status.pidPidTankValveDItempCmd = not radio_ai_temp.isChecked()

        radio_ai_level = main_window.findChild(
            QRadioButton, "radioButton_PidTankValveAIlevel")
        radio_di_level = main_window.findChild(
            QRadioButton, "radioButton_PidTankValveDIlevel")
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

        # CRITICAL FIX: Save config values BEFORE IO reload (which resets them)
        saved_config_values = {}
        # NOTE: Do NOT save custom_signal_names here! 
        # They are already in IO_configuration.json from the state file
        # and will be loaded correctly by load_io_config_from_file()
        if hasattr(active_sim, 'config'):
            config = active_sim.config
            
            if hasattr(config, 'importExportVariableList'):
                for var in config.importExportVariableList:
                    if hasattr(config, var):
                        saved_config_values[var] = getattr(config, var)
                logger.info(f"[LOAD]   Saved {len(saved_config_values)} config values before IO reload")

        # Load IO config (WARNING: This may reset config values!)
        # This will load custom_signal_names from IO_configuration.json (which was written from state file)
        active_sim.config.load_io_config_from_file(io_config_path)
        logger.info("[LOAD]   IO config loaded (including custom signal names from state)")

        # CRITICAL FIX: Restore config values AFTER IO reload
        if saved_config_values and hasattr(active_sim, 'config'):
            for var, value in saved_config_values.items():
                if hasattr(active_sim.config, var):
                    setattr(active_sim.config, var, value)
            logger.info(f"[LOAD]   Restored {len(saved_config_values)} config values after IO reload")
            
            # DEBUG: Verify restoration worked with object ID
            logger.info(f"[LOAD]   DEBUG: After restore, tankVolume={active_sim.config.tankVolume}, valveInMaxFlow={active_sim.config.valveInMaxFlow}")
            logger.info(f"[LOAD]   DEBUG: Config object id after restore: {id(active_sim.config)}")
        
        # Log custom signal names that were loaded from IO_configuration.json
        if hasattr(active_sim, 'config') and hasattr(active_sim.config, 'custom_signal_names'):
            num_custom = len(active_sim.config.custom_signal_names)
            logger.info(f"[LOAD]   Custom signal names loaded from state: {num_custom} names")

        # Update GUI refs - CRITICAL: This must point to the restored config
        if hasattr(main_window, 'tanksim_config'):
            main_window.tanksim_config = active_sim.config
            logger.info(f"[LOAD]   DEBUG: Updated main_window.tanksim_config (id={id(main_window.tanksim_config)})")
        if hasattr(main_window, 'set_simulation_status'):
            main_window.set_simulation_status(active_sim.status)

        # Reload IO tree and table
        if hasattr(main_window, 'load_io_tree'):
            main_window.load_io_tree()

        # Load table from config (which now contains only saved signals after load_state)
        # Use load_table_from_io_configuration_file() instead of load_all_tags_to_table()
        # because we want only the enabled signals from IO_configuration.json, not ALL tree tags
        io_screen = None
        
        # Try multiple methods to find IO Config page
        if hasattr(main_window, 'io_screen'):
            io_screen = main_window.io_screen
            logger.info("[LOAD]   Found io_screen via main_window.io_screen")
        
        if not io_screen and hasattr(main_window, 'stackedWidget_generalControls'):
            try:
                io_widget = main_window.stackedWidget_generalControls.widget(2)
                if io_widget:
                    io_screen = io_widget
                    logger.info("[LOAD]   Found io_screen via stackedWidget index 2")
            except Exception as e:
                logger.warning(f"[LOAD]   Could not get io_screen from stacked widget: {e}")
        
        # Try findChild as fallback
        if not io_screen:
            try:
                from PyQt5.QtWidgets import QWidget
                io_screen = main_window.findChild(QWidget, "io_screen")
                if io_screen:
                    logger.info("[LOAD]   Found io_screen via findChild")
            except Exception:
                pass
        
        if io_screen and hasattr(io_screen, 'load_table_from_io_configuration_file'):
            logger.info("[LOAD]   Calling load_table_from_io_configuration_file()...")
            io_screen.load_table_from_io_configuration_file(io_config_path)
            logger.info("[LOAD]   ✓ Table loaded from IO_configuration.json (saved signals only)")
        else:
            logger.warning(f"[LOAD]   Could not find io_screen or load_table_from_io_configuration_file method (io_screen={io_screen}, has_method={hasattr(io_screen, 'load_table_from_io_configuration_file') if io_screen else False})")

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

        status = active_sim.status if hasattr(active_sim, 'status') else None

        # Restore radio button states
        if status:
            logger.info("[LOAD] Restoring radio buttons and sliders...")
            
            # Temperature control radio buttons
            radio_ai_temp = main_window.findChild(QRadioButton, "radioButton_PidTankValveAItemp")
            radio_di_temp = main_window.findChild(QRadioButton, "radioButton_PidTankValveDItemp")
            if radio_ai_temp and hasattr(status, 'pidPidTankValveAItempCmd'):
                radio_ai_temp.blockSignals(True)
                radio_ai_temp.setChecked(status.pidPidTankValveAItempCmd)
                radio_ai_temp.blockSignals(False)
                logger.info(f"[LOAD]   radioButton_PidTankValveAItemp = {status.pidPidTankValveAItempCmd}")
            if radio_di_temp and hasattr(status, 'pidPidTankValveDItempCmd'):
                radio_di_temp.blockSignals(True)
                radio_di_temp.setChecked(status.pidPidTankValveDItempCmd)
                radio_di_temp.blockSignals(False)
                
            # Level control radio buttons
            radio_ai_level = main_window.findChild(QRadioButton, "radioButton_PidTankValveAIlevel")
            radio_di_level = main_window.findChild(QRadioButton, "radioButton_PidTankValveDIlevel")
            if radio_ai_level and hasattr(status, 'pidPidTankValveAIlevelCmd'):
                radio_ai_level.blockSignals(True)
                radio_ai_level.setChecked(status.pidPidTankValveAIlevelCmd)
                radio_ai_level.blockSignals(False)
                logger.info(f"[LOAD]   radioButton_PidTankValveAIlevel = {status.pidPidTankValveAIlevelCmd}")
            if radio_di_level and hasattr(status, 'pidPidTankValveDIlevelCmd'):
                radio_di_level.blockSignals(True)
                radio_di_level.setChecked(status.pidPidTankValveDIlevelCmd)
                radio_di_level.blockSignals(False)
                
            # Auto/Manual toggle buttons
            auto_btn = main_window.findChild(QPushButton, "pushButton_PidValveAuto")
            man_btn = main_window.findChild(QPushButton, "pushButton_PidValveMan")
            if auto_btn and hasattr(status, 'pidPidValveAutoCmd'):
                auto_btn.blockSignals(True)
                auto_btn.setChecked(status.pidPidValveAutoCmd)
                auto_btn.blockSignals(False)
                logger.info(f"[LOAD]   pushButton_PidValveAuto = {status.pidPidValveAutoCmd}")
            if man_btn and hasattr(status, 'pidPidValveManCmd'):
                man_btn.blockSignals(True)
                man_btn.setChecked(status.pidPidValveManCmd)
                man_btn.blockSignals(False)
                
            # Temperature setpoint slider
            slider_temp = main_window.findChild(QSlider, "slider_PidTankTempSP")
            if slider_temp and hasattr(status, 'pidPidTankTempSPValue'):
                slider_temp.blockSignals(True)
                slider_temp.setValue(int(status.pidPidTankTempSPValue))
                slider_temp.blockSignals(False)
                logger.info(f"[LOAD]   slider_PidTankTempSP = {status.pidPidTankTempSPValue}")
                
            # Level setpoint slider
            slider_level = main_window.findChild(QSlider, "slider_PidTankLevelSP")
            if slider_level and hasattr(status, 'pidPidTankLevelSPValue'):
                slider_level.blockSignals(True)
                slider_level.setValue(int(status.pidPidTankLevelSPValue))
                slider_level.blockSignals(False)
                logger.info(f"[LOAD]   slider_PidTankLevelSP = {status.pidPidTankLevelSPValue}")
                
            # Heater power slider (multiple instances)
            heater_value = int(status.heaterPowerFraction * 100.0) if hasattr(status, 'heaterPowerFraction') else 0
            for slider_name in ["heaterPowerSlider", "heaterPowerSlider_1", "heaterPowerSlider_2", "heaterPowerSlider_3"]:
                slider = main_window.findChild(QSlider, slider_name)
                if slider:
                    slider.blockSignals(True)
                    slider.setValue(heater_value)
                    slider.blockSignals(False)
            logger.info(f"[LOAD]   heaterPowerSlider = {heater_value}%")
                
            # Valve entries
            valve_in_entry = main_window.findChild(QLineEdit, "valveInEntry")
            if valve_in_entry and hasattr(status, 'valveInOpenFraction'):
                valve_in_entry.blockSignals(True)
                valve_in_entry.setText(str(round(status.valveInOpenFraction * 100.0, 1)))
                valve_in_entry.blockSignals(False)
                logger.info(f"[LOAD]   valveInEntry = {status.valveInOpenFraction * 100.0}%")
                
            valve_out_entry = main_window.findChild(QLineEdit, "valveOutEntry")
            if valve_out_entry and hasattr(status, 'valveOutOpenFraction'):
                valve_out_entry.blockSignals(True)
                valve_out_entry.setText(str(round(status.valveOutOpenFraction * 100.0, 1)))
                valve_out_entry.blockSignals(False)
                logger.info(f"[LOAD]   valveOutEntry = {status.valveOutOpenFraction * 100.0}%")

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
            level_cb = main_window.findChild(
                QCheckBox, "levelSwitchesCheckBox")
            if level_cb and hasattr(config, 'displayLevelSwitches'):
                level_cb.blockSignals(True)
                level_cb.setChecked(config.displayLevelSwitches)
                level_cb.blockSignals(False)

            temp_cb = main_window.findChild(
                QCheckBox, "analogValueTempCheckBox")
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
            slider_temp = main_window.findChild(
                QSlider, "slider_PidTankTempSP")
            if slider_temp and hasattr(status, 'pidPidTankTempSPValue'):
                slider_temp.blockSignals(True)
                slider_temp.setValue(status.pidPidTankTempSPValue)
                slider_temp.blockSignals(False)

            slider_level = main_window.findChild(
                QSlider, "slider_PidTankLevelSP")
            if slider_level and hasattr(status, 'pidPidTankLevelSPValue'):
                slider_level.blockSignals(True)
                slider_level.setValue(status.pidPidTankLevelSPValue)
                slider_level.blockSignals(False)
            
            # PID factor input fields
            qline_pfactor = main_window.findChild(QLineEdit, "Qline_SimPfactor")
            if qline_pfactor and hasattr(status, 'pidPfactorValue'):
                qline_pfactor.blockSignals(True)
                qline_pfactor.setText(str(status.pidPfactorValue))
                qline_pfactor.blockSignals(False)
                logger.info(f"[LOAD]   Qline_SimPfactor = {status.pidPfactorValue}")
            
            qline_ifactor = main_window.findChild(QLineEdit, "Qline_SimIfactor")
            if qline_ifactor and hasattr(status, 'pidIfactorValue'):
                qline_ifactor.blockSignals(True)
                qline_ifactor.setText(str(status.pidIfactorValue))
                qline_ifactor.blockSignals(False)
                logger.info(f"[LOAD]   Qline_SimIfactor = {status.pidIfactorValue}")
            
            qline_dfactor = main_window.findChild(QLineEdit, "Qline_SimDfactor")
            if qline_dfactor and hasattr(status, 'pidDfactorValue'):
                qline_dfactor.blockSignals(True)
                qline_dfactor.setText(str(status.pidDfactorValue))
                qline_dfactor.blockSignals(False)
                logger.info(f"[LOAD]   Qline_SimDfactor = {status.pidDfactorValue}")

        logger.info("[LOAD]   ✓ GUI sync complete")

    except Exception as e:
        logger.warning(f"[LOAD] GUI sync failed: {e}", exc_info=True)


def _activate_protocol_after_load(main_window: Any) -> None:
    """Activate protocol after loading state - COMPLETE protocol initialization.

    This function replicates the EXACT sequence that happens when:
    1. User selects protocol from dropdown (on_controller_changed)
    2. User clicks connect button (creates protocol instance in protocolManager)

    Critical: This builds the actual protocol instance and activates it in protocolManager,
    not just UI updates!
    """
    try:
        logger.info(
            "[LOAD] ========== ACTIVATING PROTOCOL FROM LOADED CONFIG ==========")

        if not hasattr(main_window, 'mainConfig') or not main_window.mainConfig:
            logger.warning("[LOAD] No mainConfig available")
            return

        config = main_window.mainConfig
        protocol_name = getattr(config, 'plcProtocol', 'GUI')
        plc_gui_control = getattr(config, 'plcGuiControl', 'gui')

        logger.info(
            f"[LOAD]   Protocol: {protocol_name}, Mode: {plc_gui_control}")

        # STEP 1: Sync dropdown to match loaded protocol (UI sync)
        if hasattr(main_window, 'controlerDropDown'):
            dropdown = main_window.controlerDropDown

            # Find matching item in dropdown
            # Dropdown items are in format "ProtocolName (MODE)" or just "ProtocolName"
            for i in range(dropdown.count()):
                item_text = dropdown.itemText(i)
                # Extract base name (remove mode suffix)
                if '(' in item_text:
                    base_name = item_text[:item_text.rfind('(')].strip()
                else:
                    base_name = item_text

                if base_name == protocol_name:
                    dropdown.blockSignals(True)
                    dropdown.setCurrentIndex(i)
                    dropdown.blockSignals(False)
                    logger.info(f"[LOAD]   Dropdown synced to: {item_text}")
                    break

        # STEP 2: Disconnect and deactivate existing protocol (if any)
        # This is CRITICAL - we need to clean up the old protocol completely
        if hasattr(main_window, 'validPlcConnection') and main_window.validPlcConnection:
            if hasattr(main_window, 'plc') and main_window.plc:
                try:
                    main_window.plc.disconnect()
                    logger.info("[LOAD]   Disconnected old protocol")
                except:
                    pass
            main_window.validPlcConnection = False
            main_window.plc = None
            if hasattr(main_window, 'update_connection_status_icon'):
                main_window.update_connection_status_icon()

            # Uncheck connect button
            if hasattr(main_window, 'pushButton_connect'):
                try:
                    main_window.pushButton_connect.blockSignals(True)
                    main_window.pushButton_connect.setChecked(False)
                    main_window.pushButton_connect.blockSignals(False)
                except:
                    pass

        # STEP 3: Deactivate old protocol in protocolManager
        # This is what was MISSING - we need to clean up protocolManager!
        if hasattr(config, 'protocolManager') and config.protocolManager:
            try:
                config.protocolManager.deactivate()
                logger.info(
                    "[LOAD]   Deactivated old protocol in protocolManager")
            except Exception as e:
                logger.warning(
                    f"[LOAD]   Could not deactivate old protocol: {e}")

        # STEP 4: Configure UI based on protocol type (same as on_controller_changed)
        if protocol_name == "GUI":
            # GUI mode - disable connect button and IP field
            config.plcGuiControl = "gui"
            try:
                if hasattr(main_window, 'pushButton_connect'):
                    main_window.pushButton_connect.setEnabled(False)
                if hasattr(main_window, 'lineEdit_IPAddress'):
                    main_window.lineEdit_IPAddress.setEnabled(False)
            except:
                pass
            logger.info("[LOAD]   GUI mode - connection disabled")
        else:
            # PLC mode - enable connect button and IP field
            config.plcGuiControl = "plc"
            try:
                if hasattr(main_window, 'pushButton_connect'):
                    main_window.pushButton_connect.setEnabled(True)
                if hasattr(main_window, 'lineEdit_IPAddress'):
                    main_window.lineEdit_IPAddress.setEnabled(True)
            except:
                pass

            # STEP 5: BUILD AND ACTIVATE PROTOCOL IN PROTOCOLMANAGER
            # This is the CRITICAL step that was missing!
            # We need to create the actual protocol instance like main.py does
            if hasattr(config, 'protocolManager') and config.protocolManager:
                protocol_manager = config.protocolManager

                try:
                    # Build protocol instance from config (same as initialize_and_connect does)
                    logger.info(
                        f"[LOAD]   Building protocol instance: {protocol_name}")
                    protocol_instance = protocol_manager.build_protocol_from_config(
                        config)

                    if protocol_instance:
                        # Activate protocol in manager (same as initialize_and_connect does)
                        if protocol_manager.activate_protocol(protocol_name, protocol_instance):
                            logger.info(
                                f"[LOAD]   ✓✓✓ Protocol instance ACTIVATED in protocolManager: {protocol_name}")
                        else:
                            logger.error(
                                f"[LOAD]   ✗ Failed to activate protocol in protocolManager")
                    else:
                        logger.error(
                            f"[LOAD]   ✗ Failed to build protocol instance")

                except Exception as e:
                    logger.error(
                        f"[LOAD]   ✗ Exception building/activating protocol: {e}", exc_info=True)
            else:
                logger.warning(
                    "[LOAD]   No protocolManager available in config")

            logger.info(
                "[LOAD]   PLC mode - connection enabled, protocol instance created")

        # STEP 6: Update IP address field to match loaded config
        if hasattr(main_window, 'lineEdit_IPAddress'):
            loaded_ip = getattr(config, 'plcIpAdress', '192.168.0.1')
            try:
                main_window.lineEdit_IPAddress.blockSignals(True)
                main_window.lineEdit_IPAddress.setText(loaded_ip)
                main_window.lineEdit_IPAddress.blockSignals(False)
                logger.info(f"[LOAD]   IP address: {loaded_ip}")
            except:
                pass

        # STEP 7: Update active method label if available
        if hasattr(main_window, '_update_active_method_label'):
            try:
                main_window._update_active_method_label(protocol_name)
                logger.info(f"[LOAD]   Active method label updated")
            except:
                pass

        # STEP 8: Update vat_widget controller mode if it exists
        if hasattr(main_window, 'vat_widget'):
            try:
                # Use dropdown text if available, otherwise protocol name
                if hasattr(main_window, 'controlerDropDown'):
                    controller_text = main_window.controlerDropDown.currentText()
                else:
                    controller_text = protocol_name
                main_window.vat_widget.controler = controller_text
                main_window.vat_widget.rebuild()
                logger.info(f"[LOAD]   VatWidget controller updated")
            except:
                pass

        logger.info(
            f"[LOAD] ========== ✓ PROTOCOL ACTIVATION COMPLETE: {protocol_name} ==========")

    except Exception as e:
        logger.error(
            f"[LOAD] ✗✗✗ Protocol activation FAILED: {e}", exc_info=True)


def _clear_gui_inputs_in_auto_mode(main_window: Any, state_data: dict) -> None:
    """CRITICAL FIRST STEP: Clear valve/heater GUI inputs in Auto mode BEFORE any other GUI operations.

    This prevents race conditions where timer-based callbacks (_on_update_all_settings) 
    read stale GUI values and write them to status before we can clear them.
    """
    try:
        from PyQt5.QtWidgets import QLineEdit, QSlider

        # Determine if in Auto mode
        gui_mode = (hasattr(main_window, 'mainConfig') and
                    main_window.mainConfig and
                    main_window.mainConfig.plcGuiControl == "gui")

        # Get Auto/Man state from loaded status
        auto_state = True  # Default to Auto
        manual_state = False

        try:
            simulation_manager = main_window.mainConfig.simulationManager if hasattr(
                main_window, 'mainConfig') else None
            if simulation_manager:
                active_sim = simulation_manager.get_active_simulation()
                if active_sim and hasattr(active_sim, 'status'):
                    auto_state = getattr(
                        active_sim.status, 'pidPidValveAutoCmd', True)
                    manual_state = getattr(
                        active_sim.status, 'pidPidValveManCmd', False)
        except Exception:
            pass

        # Only clear if in PLC Auto mode (not GUI mode, and Auto is active)
        if not gui_mode and auto_state and not manual_state:
            logger.info(
                "[LOAD] ⚠ CLEARING GUI inputs FIRST (PLC Auto mode) to prevent timer writes")

            # Clear valve entry fields
            valve_in_entry = main_window.findChild(QLineEdit, "valveInEntry")
            if valve_in_entry:
                valve_in_entry.blockSignals(True)
                valve_in_entry.setText("0")
                valve_in_entry.blockSignals(False)

            valve_out_entry = main_window.findChild(QLineEdit, "valveOutEntry")
            if valve_out_entry:
                valve_out_entry.blockSignals(True)
                valve_out_entry.setText("0")
                valve_out_entry.blockSignals(False)

            # Clear heater slider
            for slider_name in ["heaterPowerSlider", "heaterPowerSlider_1", "heaterPowerSlider_2", "heaterPowerSlider_3"]:
                slider = main_window.findChild(QSlider, slider_name)
                if slider:
                    slider.blockSignals(True)
                    slider.setValue(0)
                    slider.blockSignals(False)
                    break

            # Clear VatWidget values IMMEDIATELY
            if hasattr(main_window, 'vat_widget') and main_window.vat_widget:
                main_window.vat_widget.adjustableValveInValue = 0
                main_window.vat_widget.adjustableValveOutValue = 0
                main_window.vat_widget.heaterPowerFraction = 0.0
                logger.info(
                    "[LOAD]   ✓ VatWidget values cleared (valveIn=0, valveOut=0, heater=0)")

            logger.info(
                "[LOAD]   ✓ GUI inputs cleared BEFORE any timer callbacks")
        else:
            logger.info(
                f"[LOAD] No clearing needed (gui_mode={gui_mode}, auto={auto_state}, man={manual_state})")

    except Exception as e:
        logger.warning(f"[LOAD] GUI input clearing failed: {e}", exc_info=True)


def _auto_connect_after_load(main_window: Any) -> None:
    """Auto-connect to PLC if loaded state had PLC protocol active.

    This triggers the same connection process as clicking the Connect button,
    ensuring that PLC outputs are immediately read after loading.
    """
    try:
        if not hasattr(main_window, 'mainConfig') or not main_window.mainConfig:
            return

        config = main_window.mainConfig

        # Only auto-connect if in PLC mode (not GUI mode)
        if config.plcGuiControl != "plc":
            logger.info("[LOAD] GUI mode - skipping auto-connect")
            return

        # Check if protocol is configured
        if not config.plcProtocol or config.plcProtocol == "GUI (offline simulation)":
            logger.info("[LOAD] No PLC protocol - skipping auto-connect")
            return

        logger.info(f"[LOAD] ========== AUTO-CONNECTING TO PLC ==========")
        logger.info(f"[LOAD]   Protocol: {config.plcProtocol}")
        logger.info(f"[LOAD]   IP: {config.plcIpAdress}")

        # Trigger connection via tryConnect flag (same as Connect button)
        config.tryConnect = True

        # Also check the connect button to reflect connection attempt
        from PyQt5.QtWidgets import QPushButton
        connect_btn = main_window.findChild(QPushButton, "pushButton_connect")
        if connect_btn:
            connect_btn.blockSignals(True)
            connect_btn.setChecked(True)
            connect_btn.blockSignals(False)
            logger.info("[LOAD]   Connect button checked")

        logger.info("[LOAD] ========== ✓ AUTO-CONNECT TRIGGERED ==========")
        logger.info("[LOAD]   Connection will be established in main loop")

    except Exception as e:
        logger.warning(f"[LOAD] Auto-connect failed: {e}", exc_info=True)


def _populate_all_config_to_gui(main_window: Any) -> None:
    """
    Populate ALL configuration parameters from config object to GUI entry fields.
    This is the comprehensive GUI population that was missing - ensures every
    config parameter updates its corresponding widget after load.
    """
    try:
        logger.info("=" * 80)
        logger.info("[LOAD-GUI] Populating ALL config parameters to GUI fields...")
        logger.info("=" * 80)

        # FIX: Use main_window.tanksim_config directly (updated at line 660)
        # instead of retrieving from simulation_manager which may return stale reference
        if not hasattr(main_window, 'tanksim_config'):
            logger.warning("[LOAD-GUI] No tanksim_config in main_window")
            return

        config = main_window.tanksim_config
        logger.info(f"[LOAD-GUI] DEBUG: Using main_window.tanksim_config (id={id(config)})")
        logger.info(f"[LOAD-GUI] DEBUG: Config values - tankVolume={config.tankVolume}, valveInMaxFlow={config.valveInMaxFlow}")
        count = 0

        # 1. Simulation Interval
        if hasattr(config, 'simulationInterval'):
            print(f"Loading simulationInterval: {config.simulationInterval}")
            logger.info(f"  [1/17] simulationInterval: {config.simulationInterval}")
            if hasattr(main_window, 'simulationIntervalEntry'):
                main_window.simulationIntervalEntry.blockSignals(True)
                main_window.simulationIntervalEntry.setText(str(config.simulationInterval))
                main_window.simulationIntervalEntry.blockSignals(False)
                logger.info(f"    ✓ simulationIntervalEntry = '{config.simulationInterval}'")
                count += 1

        # 2. Tank Volume (convert liters to m³)
        if hasattr(config, 'tankVolume'):
            print(f"Loading tankVolume: {config.tankVolume}")
            volume_m3 = config.tankVolume / 1000.0
            logger.info(f"  [2/17] tankVolume: {config.tankVolume} L ({volume_m3:.3f} m³)")
            if hasattr(main_window, 'volumeEntry'):
                main_window.volumeEntry.blockSignals(True)
                main_window.volumeEntry.setText(str(round(volume_m3, 2)))
                main_window.volumeEntry.blockSignals(False)
                logger.info(f"    ✓ volumeEntry = '{round(volume_m3, 2)}'")
                count += 1

        # 3. Valve In Max Flow
        if hasattr(config, 'valveInMaxFlow'):
            print(f"Loading valveInMaxFlow: {config.valveInMaxFlow}")
            logger.info(f"  [3/17] valveInMaxFlow: {config.valveInMaxFlow}")
            if hasattr(main_window, 'maxFlowInEntry'):
                main_window.maxFlowInEntry.blockSignals(True)
                main_window.maxFlowInEntry.setText(str(config.valveInMaxFlow))
                main_window.maxFlowInEntry.blockSignals(False)
                logger.info(f"    ✓ maxFlowInEntry = '{config.valveInMaxFlow}'")
                count += 1

        # 4. Valve Out Max Flow
        if hasattr(config, 'valveOutMaxFlow'):
            print(f"Loading valveOutMaxFlow: {config.valveOutMaxFlow}")
            logger.info(f"  [4/17] valveOutMaxFlow: {config.valveOutMaxFlow}")
            if hasattr(main_window, 'maxFlowOutEntry'):
                main_window.maxFlowOutEntry.blockSignals(True)
                main_window.maxFlowOutEntry.setText(str(config.valveOutMaxFlow))
                main_window.maxFlowOutEntry.blockSignals(False)
                logger.info(f"    ✓ maxFlowOutEntry = '{config.valveOutMaxFlow}'")
                count += 1

        # 5. Ambient Temperature
        if hasattr(config, 'ambientTemp'):
            print(f"Loading ambientTemp: {config.ambientTemp}")
            logger.info(f"  [5/17] ambientTemp: {config.ambientTemp}")
            if hasattr(main_window, 'ambientTempEntry'):
                main_window.ambientTempEntry.blockSignals(True)
                main_window.ambientTempEntry.setText(str(config.ambientTemp))
                main_window.ambientTempEntry.blockSignals(False)
                logger.info(f"    ✓ ambientTempEntry = '{config.ambientTemp}'")
                count += 1

        # 6. Digital Level Sensor High Trigger (convert liters to percentage)
        if hasattr(config, 'digitalLevelSensorHighTriggerLevel'):
            trigger_liters = config.digitalLevelSensorHighTriggerLevel
            print(f"Loading digitalLevelSensorHighTriggerLevel: {trigger_liters}")
            # Convert from liters to percentage of tank volume
            tank_volume = getattr(config, 'tankVolume', 200.0)
            trigger_pct = (trigger_liters / tank_volume * 100.0) if tank_volume > 0 else 90.0
            trigger_pct_rounded = round(trigger_pct, 1)
            logger.info(f"  [6/17] digitalLevelSensorHighTriggerLevel: {trigger_liters} L ({trigger_pct_rounded:.1f}%)")
            if hasattr(main_window, 'levelSwitchMaxHeightEntry'):
                main_window.levelSwitchMaxHeightEntry.blockSignals(True)
                main_window.levelSwitchMaxHeightEntry.setText(str(trigger_pct_rounded))
                main_window.levelSwitchMaxHeightEntry.blockSignals(False)
                logger.info(f"    ✓ levelSwitchMaxHeightEntry = '{trigger_pct_rounded}%'")
                count += 1

        # 7. Digital Level Sensor Low Trigger (convert liters to percentage)
        if hasattr(config, 'digitalLevelSensorLowTriggerLevel'):
            trigger_liters = config.digitalLevelSensorLowTriggerLevel
            print(f"Loading digitalLevelSensorLowTriggerLevel: {trigger_liters}")
            # Convert from liters to percentage of tank volume
            tank_volume = getattr(config, 'tankVolume', 200.0)
            trigger_pct = (trigger_liters / tank_volume * 100.0) if tank_volume > 0 else 10.0
            trigger_pct_rounded = round(trigger_pct, 1)
            logger.info(f"  [7/17] digitalLevelSensorLowTriggerLevel: {trigger_liters} L ({trigger_pct_rounded:.1f}%)")
            if hasattr(main_window, 'levelSwitchMinHeightEntry'):
                main_window.levelSwitchMinHeightEntry.blockSignals(True)
                main_window.levelSwitchMinHeightEntry.setText(str(trigger_pct_rounded))
                main_window.levelSwitchMinHeightEntry.blockSignals(False)
                logger.info(f"    ✓ levelSwitchMinHeightEntry = '{trigger_pct_rounded}%'")
                count += 1

        # 8. Heater Max Power (convert W to kW)
        if hasattr(config, 'heaterMaxPower'):
            print(f"Loading heaterMaxPower: {config.heaterMaxPower}")
            power_w = config.heaterMaxPower 
            logger.info(f"  [8/17] heaterMaxPower: {config.heaterMaxPower} W ({power_w:.3f} W)")
            if hasattr(main_window, 'powerHeatingCoilEntry'):
                main_window.powerHeatingCoilEntry.blockSignals(True)
                main_window.powerHeatingCoilEntry.setText(str(round(power_w, 2)))
                main_window.powerHeatingCoilEntry.blockSignals(False)
                logger.info(f"    ✓ powerHeatingCoilEntry = '{round(power_w, 2)}'")
                count += 1

        # 9. Tank Heat Loss
        if hasattr(config, 'tankHeatLoss'):
            print(f"Loading tankHeatLoss: {config.tankHeatLoss}")
            logger.info(f"  [9/17] tankHeatLoss: {config.tankHeatLoss}")
            if hasattr(main_window, 'heatLossVatEntry'):
                main_window.heatLossVatEntry.blockSignals(True)
                main_window.heatLossVatEntry.setText(str(config.tankHeatLoss))
                main_window.heatLossVatEntry.blockSignals(False)
                logger.info(f"    ✓ heatLossVatEntry = '{config.tankHeatLoss}'")
                count += 1

        # 10. Liquid Specific Heat Capacity
        if hasattr(config, 'liquidSpecificHeatCapacity'):
            print(f"Loading liquidSpecificHeatCapacity: {config.liquidSpecificHeatCapacity}")
            logger.info(f"  [10/17] liquidSpecificHeatCapacity: {config.liquidSpecificHeatCapacity}")
            if hasattr(main_window, 'specificHeatCapacity'):
                main_window.specificHeatCapacity.blockSignals(True)
                main_window.specificHeatCapacity.setText(str(config.liquidSpecificHeatCapacity))
                main_window.specificHeatCapacity.blockSignals(False)
                logger.info(f"    ✓ specificHeatCapacity = '{config.liquidSpecificHeatCapacity}'")
                count += 1

        # 11. Liquid Boiling Temperature
        if hasattr(config, 'liquidBoilingTemp'):
            print(f"Loading liquidBoilingTemp: {config.liquidBoilingTemp}")
            logger.info(f"  [11/17] liquidBoilingTemp: {config.liquidBoilingTemp}")
            if hasattr(main_window, 'boilingTempEntry'):
                main_window.boilingTempEntry.blockSignals(True)
                main_window.boilingTempEntry.setText(str(config.liquidBoilingTemp))
                main_window.boilingTempEntry.blockSignals(False)
                logger.info(f"    ✓ boilingTempEntry = '{config.liquidBoilingTemp}'")
                count += 1

        # 12. Liquid Specific Weight (stored as kg/L, display as kg/m³)
        if hasattr(config, 'liquidSpecificWeight'):
            print(f"Loading liquidSpecificWeight: {config.liquidSpecificWeight}")
            # Convert from kg/L to kg/m³ for display
            weight_kgm3 = config.liquidSpecificWeight * 1000.0
            logger.info(f"  [12/17] liquidSpecificWeight: {config.liquidSpecificWeight} kg/L ({weight_kgm3} kg/m³)")
            if hasattr(main_window, 'specificWeightEntry'):
                main_window.specificWeightEntry.blockSignals(True)
                main_window.specificWeightEntry.setText(str(weight_kgm3))
                main_window.specificWeightEntry.blockSignals(False)
                logger.info(f"    ✓ specificWeightEntry = '{weight_kgm3} kg/m³'")
                count += 1

        # 13. Liquid Volume Time Delay
        if hasattr(config, 'liquidVolumeTimeDelay'):
            print(f"Loading liquidVolumeTimeDelay: {config.liquidVolumeTimeDelay}")
            logger.info(f"  [13/17] liquidVolumeTimeDelay: {config.liquidVolumeTimeDelay}")
            if hasattr(main_window, 'timeDelayfillingEntry'):
                main_window.timeDelayfillingEntry.blockSignals(True)
                main_window.timeDelayfillingEntry.setText(str(config.liquidVolumeTimeDelay))
                main_window.timeDelayfillingEntry.blockSignals(False)
                logger.info(f"    ✓ timeDelayfillingEntry = '{config.liquidVolumeTimeDelay}'")
                count += 1

        # 14. Liquid Temperature Time Delay
        if hasattr(config, 'liquidTempTimeDelay'):
            print(f"Loading liquidTempTimeDelay: {config.liquidTempTimeDelay}")
            logger.info(f"  [14/17] liquidTempTimeDelay: {config.liquidTempTimeDelay}")
            if hasattr(main_window, 'timeDelayTempEntry'):
                main_window.timeDelayTempEntry.blockSignals(True)
                main_window.timeDelayTempEntry.setText(str(config.liquidTempTimeDelay))
                main_window.timeDelayTempEntry.blockSignals(False)
                logger.info(f"    ✓ timeDelayTempEntry = '{config.liquidTempTimeDelay}'")
                count += 1

        # 15. Tank Color
        if hasattr(config, 'tankColor'):
            print(f"Loading tankColor: {config.tankColor}")
            logger.info(f"  [15/17] tankColor: {config.tankColor}")
            if hasattr(main_window, 'colorDropDown'):
                found = False
                for i in range(main_window.colorDropDown.count()):
                    if main_window.colorDropDown.itemData(i) == config.tankColor:
                        main_window.colorDropDown.blockSignals(True)
                        main_window.colorDropDown.setCurrentIndex(i)
                        main_window.colorDropDown.blockSignals(False)
                        logger.info(f"    ✓ colorDropDown index {i} = '{config.tankColor}'")
                        found = True
                        count += 1
                        break
                if not found:
                    logger.warning(f"    ⚠ Color '{config.tankColor}' not found in colorDropDown")

        # 16. Display Level Switches
        if hasattr(config, 'displayLevelSwitches'):
            print(f"Loading displayLevelSwitches: {config.displayLevelSwitches}")
            logger.info(f"  [16/17] displayLevelSwitches: {config.displayLevelSwitches}")
            if hasattr(main_window, 'levelSwitchesCheckBox'):
                main_window.levelSwitchesCheckBox.blockSignals(True)
                main_window.levelSwitchesCheckBox.setChecked(config.displayLevelSwitches)
                main_window.levelSwitchesCheckBox.blockSignals(False)
                logger.info(f"    ✓ levelSwitchesCheckBox = {config.displayLevelSwitches}")
                count += 1

        # 17. Display Temperature
        if hasattr(config, 'displayTemperature'):
            print(f"Loading displayTemperature: {config.displayTemperature}")
            logger.info(f"  [17/17] displayTemperature: {config.displayTemperature}")
            if hasattr(main_window, 'analogValueTempCheckBox'):
                main_window.analogValueTempCheckBox.blockSignals(True)
                main_window.analogValueTempCheckBox.setChecked(config.displayTemperature)
                main_window.analogValueTempCheckBox.blockSignals(False)
                logger.info(f"    ✓ analogValueTempCheckBox = {config.displayTemperature}")
                count += 1

        logger.info("=" * 80)
        logger.info(f"[LOAD-GUI] ✓ Config population complete: {count}/17 fields updated")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"[LOAD-GUI] ERROR in _populate_all_config_to_gui: {e}", exc_info=True)


def _apply_gui_mode_visuals_after_load(main_window: Any) -> None:
    """Apply Auto/Manual mode button visuals after load.

    NOTE: Valve/heater clearing is now done in _clear_gui_inputs_in_auto_mode() 
    which runs FIRST to prevent race conditions.
    """
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
            sim_name_to_index = {"PIDtankValve": 0,
                                 "dualTank": 1, "conveyor": 2}
            if sim_name in sim_name_to_index:
                main_window.start_simulation(sim_name_to_index[sim_name])

        # Sync button states
        auto_btn = main_window.findChild(
            QPushButton, "pushButton_PidValveAuto")
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

        # NOTE: Valve/heater clearing is done FIRST in _clear_gui_inputs_in_auto_mode()
        # to prevent race conditions with timer callbacks

        # Update control groupbox visuals - pass correct enabled state
        # In Auto mode (not manual), controls should be disabled (grayed out)
        gui_mode = (hasattr(main_window, 'mainConfig') and
                    main_window.mainConfig and
                    main_window.mainConfig.plcGuiControl == "gui")
        man_state = getattr(status, 'pidPidValveManCmd', False)
        # Enable if GUI mode or Manual override
        controls_enabled = gui_mode or man_state

        if hasattr(main_window, 'vat_widget') and hasattr(main_window.vat_widget, '_update_control_groupboxes'):
            main_window.vat_widget._update_control_groupboxes(controls_enabled)

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
