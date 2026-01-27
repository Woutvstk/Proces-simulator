"""
Save/Load Module - Complete Application State Management

This module provides complete save/load functionality for:
- Main configuration (PLC settings, protocol, control mode)
- Active simulation state (config and status/process values)
- IO configuration (embedded in save file)
- Validation and error checking

External Libraries Used:
- json (Python Standard Library) - State serialization and persistence
- pathlib (Python Standard Library) - File path handling
- datetime (Python Standard Library) - Timestamp generation
- logging (Python Standard Library) - Error and info logging
- typing (Python Standard Library) - Type hints
- shutil (Python Standard Library) - File operations
"""
import json
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .simulationManager import SimulationManager
    from .configuration import configuration

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages saving and loading complete application state.
    Handles all configurations, simulation data, and IO settings.
    """
    
    VERSION = "2.0"  
    
    def __init__(self):
        """Initialize the state manager."""
        pass
    
    @staticmethod
    def _serialize_object_to_dict(obj: Any) -> Dict[str, Any]:
        """
        Serialize an object to a dictionary for JSON export.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Dictionary representation of the object
        """
        result = {}
        
        # Get export list if available
        export_list = getattr(obj, 'importExportVariableList', None)
        
        if export_list:
            # Use the object's export list
            for var in export_list:
                if hasattr(obj, var):
                    value = getattr(obj, var)
                    # Handle nested objects (like dict for IO addresses)
                    if isinstance(value, dict):
                        result[var] = value.copy()
                    else:
                        result[var] = value
        else:
            # Fall back to all non-private attributes
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):
                    if isinstance(value, dict):
                        result[key] = value.copy()
                    else:
                        result[key] = value
        
        return result
    
    @staticmethod
    def _deserialize_dict_to_object(obj: Any, data: Dict[str, Any]) -> None:
        """
        Deserialize a dictionary to an object.
        
        Args:
            obj: Object to update
            data: Dictionary with values to set
        """
        for key, value in data.items():
            if hasattr(obj, key):
                try:
                    # Get current value to determine type
                    current_value = getattr(obj, key)
                    current_type = type(current_value)
                    
                    # Handle dict types specially (like IO addresses)
                    if isinstance(current_value, dict) and isinstance(value, dict):
                        setattr(obj, key, value.copy())
                    elif current_type in (int, float, str, bool):
                        # Convert to correct type
                        setattr(obj, key, current_type(value))
                    else:
                        # Set as-is for other types
                        setattr(obj, key, value)
                        
                except (TypeError, ValueError) as e:
                    logger.warning(f"Could not convert {key}={value} to correct type: {e}")
                    # Set as-is if conversion fails
                    setattr(obj, key, value)
    
    def save_state(
        self, 
        main_config: 'configuration',
        simulation_manager: Optional['SimulationManager'],
        io_config_path: str,
        save_file_path: str
    ) -> bool:
        """
        Save complete application state to JSON file.
        
        This saves:
        - Main configuration (PLC settings, protocol, control mode)
        - Active simulation name and state
        - Simulation configuration (tank parameters, intervals, etc.)
        - Simulation status (current values, running state, etc.)
        - IO configuration (complete JSON embedded)
        
        Args:
            main_config: Main configuration instance
            simulation_manager: SimulationManager instance
            io_config_path: Path to IO configuration JSON file
            save_file_path: Path where to save the complete state
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            logger.info(f"Saving application state to: {save_file_path}")
            
            # Initialize state structure
            # Make io_config_path relative to src directory for portability
            try:
                io_config_relative = Path(io_config_path).relative_to(Path(__file__).parent.parent)
                io_config_path_str = str(io_config_relative).replace('\\', '/')
            except (ValueError, AttributeError):
                # If path is not relative to src, use filename only
                io_config_path_str = Path(io_config_path).name
            
            state_data = {
                "version": self.VERSION,
                "timestamp": datetime.now().isoformat(),
                "description": "PLC Modbus Process Simulator - Complete Application State",
                "main_config": {},
                "active_simulation": None,
                "simulation_config": {},
                "simulation_status": {},
                "io_config": None,
                "io_config_original_path": io_config_path_str
            }
            
            # 1. Save main configuration
            logger.info("Serializing main configuration...")
            if hasattr(main_config, 'importExportVariableList'):
                for var in main_config.importExportVariableList:
                    if hasattr(main_config, var):
                        state_data["main_config"][var] = getattr(main_config, var)
            else:
                # Fallback: save all non-private attributes
                for key, value in main_config.__dict__.items():
                    if not key.startswith('_') and key != 'simulationManager':
                        state_data["main_config"][key] = value
            
            # 2. Save simulation state
            if simulation_manager:
                sim_name = simulation_manager.get_active_simulation_name()
                active_sim = simulation_manager.get_active_simulation()
                
                if active_sim and sim_name:
                    logger.info(f"Serializing simulation: {sim_name}")
                    state_data["active_simulation"] = sim_name
                    
                    # Save simulation config
                    if hasattr(active_sim, 'config'):
                        state_data["simulation_config"] = self._serialize_object_to_dict(active_sim.config)
                        logger.info(f"  - Config parameters: {len(state_data['simulation_config'])}")
                    
                    # Save simulation status
                    if hasattr(active_sim, 'status'):
                        state_data["simulation_status"] = self._serialize_object_to_dict(active_sim.status)
                        logger.info(f"  - Status parameters: {len(state_data['simulation_status'])}")
            
            # 3. Load and embed IO configuration
            io_path = Path(io_config_path)
            if io_path.exists():
                try:
                    with open(io_path, 'r') as f:
                        io_config_data = json.load(f)
                    state_data["io_config"] = io_config_data
                    logger.info(f"Embedded IO configuration from: {io_config_path}")
                except Exception as e:
                    logger.warning(f"Could not load IO config from {io_config_path}: {e}")
                    state_data["io_config"] = None
            else:
                logger.warning(f"IO configuration file not found: {io_config_path}")
                state_data["io_config"] = None
            
            # 4. Write to JSON file
            save_path = Path(save_file_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            logger.info(f"✓ State saved successfully to: {save_file_path}")
            logger.info(f"  - File size: {save_path.stat().st_size} bytes")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}", exc_info=True)
            return False
    
    def load_state(
        self,
        main_config: 'configuration',
        simulation_manager: Optional['SimulationManager'],
        io_config_output_path: str,
        load_file_path: str
    ) -> bool:
        """
        Load complete application state from JSON file with validation.
        
        This restores:
        - Main configuration (PLC settings, protocol, control mode)
        - Active simulation (auto-loads the simulation)
        - Simulation configuration
        - Simulation status (process values)
        - IO configuration (extracted and written to io_config_output_path)
        
        Args:
            main_config: Main configuration instance to update
            simulation_manager: SimulationManager instance
            io_config_output_path: Path where to write extracted IO config
            load_file_path: Path to load the complete state from
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            load_path = Path(load_file_path)
            
            if not load_path.exists():
                logger.error(f"State file not found: {load_file_path}")
                return False
            
            logger.info(f"Loading application state from: {load_file_path}")
            
            # 1. Load and validate JSON
            try:
                with open(load_path, 'r') as f:
                    state_data = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in state file: {e}")
                return False
            
            # 2. Validate structure
            required_keys = ["version", "main_config"]
            for key in required_keys:
                if key not in state_data:
                    logger.error(f"Invalid state file: missing required key '{key}'")
                    return False
            
            # Check version compatibility
            file_version = state_data.get("version", "unknown")
            logger.info(f"State file version: {file_version}")
            
            # 3. Load main configuration
            logger.info("Restoring main configuration...")
            main_config_data = state_data["main_config"]
            logger.debug(f"Main config data from file: {main_config_data}")
            
            if hasattr(main_config, 'importExportVariableList'):
                for var in main_config.importExportVariableList:
                    if var in main_config_data:
                        try:
                            current_value = getattr(main_config, var)
                            current_type = type(current_value)
                            new_value = main_config_data[var]
                            # Try converting to the target type, but fall back if conversion fails
                            try:
                                converted = current_type(new_value)
                            except Exception:
                                converted = new_value
                            setattr(main_config, var, converted)
                            logger.info(f"Set main_config.{var} = {getattr(main_config, var)!r}")
                        except Exception as e:
                            logger.warning(f"Could not set {var} from value {main_config_data.get(var)!r}: {e}")
            else:
                # Fallback: restore all attributes
                for key, value in main_config_data.items():
                    if hasattr(main_config, key):
                        try:
                            setattr(main_config, key, value)
                        except Exception as e:
                            logger.warning(f"Could not set {key}: {e}")
            
            # Debug: dump resulting main_config values for troubleshooting
            try:
                dump = {var: getattr(main_config, var) for var in getattr(main_config, 'importExportVariableList', [])}
                logger.debug(f"Resulting main_config values after load: {dump}")
            except Exception:
                pass
            
            logger.info("✓ Main configuration restored")
            
            # 4. Extract and save IO configuration
            if "io_config" in state_data and state_data["io_config"] is not None:
                try:
                    io_output_path = Path(io_config_output_path)
                    io_output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(io_output_path, 'w') as f:
                        json.dump(state_data["io_config"], f, indent=2)
                    
                    logger.info(f"✓ IO configuration extracted to: {io_config_output_path}")
                except Exception as e:
                    logger.error(f"Failed to extract IO configuration: {e}")
                    return False
            else:
                logger.warning("No IO configuration found in state file")
            
            # 5. Load simulation state
            if simulation_manager and "active_simulation" in state_data:
                sim_name = state_data["active_simulation"]
                
                if sim_name:
                    logger.info(f"Loading simulation: {sim_name}")
                    
                    # Check if simulation is registered
                    if sim_name not in simulation_manager.get_registered_simulations():
                        logger.error(f"Simulation '{sim_name}' not registered")
                        return False
                    
                    # Load the simulation (creates new instance)
                    if not simulation_manager.load_simulation(sim_name, sim_name + "_loaded"):
                        logger.error(f"Failed to load simulation: {sim_name}")
                        return False
                    
                    active_sim = simulation_manager.get_active_simulation()
                    
                    if active_sim:
                        # Restore simulation configuration
                        if "simulation_config" in state_data and state_data["simulation_config"]:
                            if hasattr(active_sim, 'config'):
                                self._deserialize_dict_to_object(
                                    active_sim.config, 
                                    state_data["simulation_config"]
                                )
                                logger.info("✓ Simulation configuration restored")
                        
                        # Restore simulation status
                        if "simulation_status" in state_data and state_data["simulation_status"]:
                            if hasattr(active_sim, 'status'):
                                self._deserialize_dict_to_object(
                                    active_sim.status,
                                    state_data["simulation_status"]
                                )
                                logger.info("✓ Simulation status restored")
                        
                        logger.info(f"✓ Simulation '{sim_name}' loaded successfully")
            
            logger.info("✓✓✓ Application state loaded successfully ✓✓✓")
            logger.info(f"  - Timestamp: {state_data.get('timestamp', 'unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load state: {e}", exc_info=True)
            return False
    
    def validate_state_file(self, file_path: str) -> tuple[bool, str]:
        """
        Validate a state file without loading it.
        
        Args:
            file_path: Path to state file to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                return False, f"File not found: {file_path}"
            
            # Try to load JSON
            try:
                with open(file_path_obj, 'r') as f:
                    state_data = json.load(f)
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON format: {str(e)}"
            
            # Check required keys
            required_keys = ["version", "main_config"]
            for key in required_keys:
                if key not in state_data:
                    return False, f"Missing required key: {key}"
            
            # Check version
            version = state_data.get("version", "unknown")
            
            # Extract info
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
            return False, f"Validation error: {str(e)}"


# Global instance for easy access
_state_manager = StateManager()


def save_application_state(
    main_config: 'configuration',
    simulation_manager: Optional['SimulationManager'],
    io_config_path: str,
    save_file_path: str
) -> bool:
    """
    Convenience function to save application state.
    
    Args:
        main_config: Main configuration instance
        simulation_manager: SimulationManager instance
        io_config_path: Path to IO configuration JSON file
        save_file_path: Path where to save the complete state
        
    Returns:
        True if saved successfully, False otherwise
    """
    return _state_manager.save_state(
        main_config, 
        simulation_manager, 
        io_config_path, 
        save_file_path
    )


def load_application_state(
    main_config: 'configuration',
    simulation_manager: Optional['SimulationManager'],
    io_config_output_path: str,
    load_file_path: str
) -> bool:
    """
    Convenience function to load application state.
    
    Args:
        main_config: Main configuration instance
        simulation_manager: SimulationManager instance
        io_config_output_path: Path where to write extracted IO config
        load_file_path: Path to load the complete state from
        
    Returns:
        True if loaded successfully, False otherwise
    """
    return _state_manager.load_state(
        main_config,
        simulation_manager,
        io_config_output_path,
        load_file_path
    )


def validate_state_file(file_path: str) -> tuple[bool, str]:
    """
    Convenience function to validate a state file.
    
    Args:
        file_path: Path to state file to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    return _state_manager.validate_state_file(file_path)
