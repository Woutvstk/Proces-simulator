"""
Central Configuration Module.

This module provides:
- Initial application state loading on startup
- Save/Load complete simulation states via simulationManager
- Centralized config access for all modules
- JSON-based state persistence with validation
"""
import csv
import json
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Dict, Any
from datetime import datetime

if TYPE_CHECKING:
    from .simulationManager import SimulationManager

logger = logging.getLogger(__name__)


class configuration:
    """
    Main configuration class for the application.
    Manages PLC connection settings and application state.
    """

    def __init__(self):
        """Constructor: create configuration object with default parameters"""
        
        # Control process through gui or plc
        self.plcGuiControl = "plc"  # options: gui/plc
        self.doExit = False
        
        # PLC connection settings
        # Options: "Gui", "PLC S7-1500/1200/400/300/ET 200SP", "PLC S7-300/400", 
        #          "logo!", "PLCSim S7-1500 advanced", "PLCSim S7-1500/1200/400/300/ET 200SP"
        self.plcProtocol: str = "PLC S7-1500/1200/400/300/ET 200SP"
        self.plcIpAdress: str = "192.168.0.1"
        self.plcPort: int = 502  # ModBusTCP default port
        self.plcRack: int = 0
        self.plcSlot: int = 1
        self.tsapLogo: int = 0x0300  # CLIENT(sim) SIDE
        self.tsapServer: int = 0x0200  # LOGO SIDE
        
        # Network adapter selection for PLC discovery
        # "auto" = check all adapters, or specific adapter name = use only that adapter
        self.selectedNetworkAdapter: str = "auto"
        
        # Set True by gui, set False by main
        self.tryConnect: bool = False
        
        # Variables to export/import
        self.importExportVariableList = [
            "plcGuiControl", "plcProtocol",
            "plcIpAdress", "plcPort", "plcRack", "plcSlot", 
            "tsapLogo", "tsapServer", "selectedNetworkAdapter"
        ]
    
    def saveToFile(self, exportFileName: str, createFile: bool = False) -> bool:
        """
        Save configuration to a CSV file.
        
        Args:
            exportFileName: Path to the export file
            createFile: If True, creates new file; if False, appends to existing
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            logger.info(f"Exporting config to: {exportFileName}")
            openMode: str = "w" if createFile else "a"
            
            with open(exportFileName, openMode, newline="") as file:
                writer = csv.writer(file)
                if createFile:
                    # Add CSV header for new file
                    writer.writerow(["variable", "value"])
                
                # Write all variables from list with value to CSV
                for variable in self.importExportVariableList:
                    writer.writerow([variable, getattr(self, variable)])
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config to {exportFileName}: {e}")
            return False
    
    def loadFromFile(self, importFileName: str) -> bool:
        """
        Load configuration from a CSV file.
        
        Args:
            importFileName: Path to the import file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(importFileName, "r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    for variable in self.importExportVariableList:
                        if row["variable"] == variable:
                            # Convert to correct type based on current attribute type
                            current_type = type(getattr(self, variable))
                            setattr(self, variable, current_type(row["value"]))
            
            logger.info(f"Config loaded from: {importFileName}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load config from {importFileName}: {e}")
            return False
    
    def _serialize_object_to_dict(self, obj: Any) -> Dict[str, Any]:
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
                    result[var] = getattr(obj, var)
        else:
            # Fall back to all non-private attributes
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):
                    result[key] = value
        
        return result
    
    def _deserialize_dict_to_object(self, obj: Any, data: Dict[str, Any]) -> None:
        """
        Deserialize a dictionary to an object.
        
        Args:
            obj: Object to update
            data: Dictionary with values to set
        """
        for key, value in data.items():
            if hasattr(obj, key):
                # Convert to correct type based on current attribute type
                try:
                    current_type = type(getattr(obj, key))
                    setattr(obj, key, current_type(value))
                except (TypeError, ValueError) as e:
                    logger.warning(f"Could not convert {key}={value} to type {current_type}: {e}")
                    # Set as-is if conversion fails
                    setattr(obj, key, value)
    
    def Save(self, simulation_manager: Optional['SimulationManager'], 
             export_filename: str, io_config_path: Optional[str] = None) -> bool:
        """
        Save complete application state to JSON file.
        
        This saves:
        - Main configuration (PLC settings, protocol, control mode)
        - Active simulation name and state
        - Simulation configuration (tank parameters, intervals, etc.)
        - Simulation status (current values, running state, etc.)
        - IO configuration path reference
        
        Args:
            simulation_manager: SimulationManager instance to save simulation state
            export_filename: Path to save the complete state (JSON format)
            io_config_path: Optional path to IO configuration file to reference
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            state_data = {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "main_config": {},
                "active_simulation": None,
                "simulation_config": {},
                "simulation_status": {},
                "io_config_path": io_config_path or "IO/IO_configuration.json"
            }
            
            # Save main configuration
            for var in self.importExportVariableList:
                state_data["main_config"][var] = getattr(self, var)
            
            # Save simulation state if manager is provided and has active simulation
            if simulation_manager:
                sim_name = simulation_manager.get_active_simulation_name()
                active_sim = simulation_manager.get_active_simulation()
                
                if active_sim and sim_name:
                    state_data["active_simulation"] = sim_name
                    
                    # Get simulation config and serialize it
                    if hasattr(active_sim, 'get_config_object'):
                        config_obj = active_sim.get_config_object()
                        state_data["simulation_config"] = self._serialize_object_to_dict(config_obj)
                    elif hasattr(active_sim, 'config'):
                        state_data["simulation_config"] = self._serialize_object_to_dict(active_sim.config)
                    
                    # Get simulation status and serialize it
                    if hasattr(active_sim, 'get_status_object'):
                        status_obj = active_sim.get_status_object()
                        state_data["simulation_status"] = self._serialize_object_to_dict(status_obj)
                    elif hasattr(active_sim, 'status'):
                        state_data["simulation_status"] = self._serialize_object_to_dict(active_sim.status)
                    
                    logger.info(f"Prepared simulation state for: {sim_name}")
            
            # Write to JSON file
            export_path = Path(export_filename)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_path, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            logger.info(f"Complete state saved to: {export_filename}")
            print(f"✓ Configuration saved to: {export_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save complete state: {e}")
            print(f"✗ Failed to save configuration: {e}")
            return False
    
    def Load(self, simulation_manager: Optional['SimulationManager'], 
             import_filename: str) -> bool:
        """
        Load complete application state from JSON file with validation.
        
        This restores:
        - Main configuration (PLC settings, protocol, control mode)
        - Active simulation (auto-loads the simulation)
        - Simulation configuration
        - Simulation status (process values)
        - IO configuration path
        
        Args:
            simulation_manager: SimulationManager instance to load simulation into
            import_filename: Path to load the complete state from (JSON format)
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            import_path = Path(import_filename)
            
            if not import_path.exists():
                logger.error(f"Import file not found: {import_filename}")
                print(f"✗ Configuration file not found: {import_filename}")
                return False
            
            # Load JSON data
            with open(import_path, 'r') as f:
                state_data = json.load(f)
            
            # Validate JSON structure
            required_keys = ["version", "main_config", "active_simulation"]
            for key in required_keys:
                if key not in state_data:
                    logger.error(f"Invalid state file: missing '{key}'")
                    print(f"✗ Invalid configuration file: missing '{key}'")
                    return False
            
            # Check version compatibility
            if state_data["version"] != "1.0":
                logger.warning(f"State file version {state_data['version']} may not be compatible")
            
            # Load main configuration
            main_config = state_data["main_config"]
            for var in self.importExportVariableList:
                if var in main_config:
                    try:
                        current_type = type(getattr(self, var))
                        setattr(self, var, current_type(main_config[var]))
                    except Exception as e:
                        logger.warning(f"Could not set {var}: {e}")
            
            logger.info("Main configuration loaded")
            
            # Load simulation state if manager is provided
            if simulation_manager and state_data["active_simulation"]:
                sim_name = state_data["active_simulation"]
                
                # Check if simulation is registered
                if sim_name not in simulation_manager.get_registered_simulations():
                    logger.error(f"Simulation '{sim_name}' not registered")
                    print(f"✗ Simulation '{sim_name}' not available")
                    return False
                
                # Load the simulation (this will create a new instance)
                logger.info(f"Loading simulation: {sim_name}")
                if not simulation_manager.load_simulation(sim_name, sim_name + "_loaded"):
                    logger.error(f"Failed to load simulation: {sim_name}")
                    print(f"✗ Failed to load simulation: {sim_name}")
                    return False
                
                active_sim = simulation_manager.get_active_simulation()
                
                if active_sim:
                    # Restore simulation configuration
                    if "simulation_config" in state_data and state_data["simulation_config"]:
                        if hasattr(active_sim, 'get_config_object'):
                            config_obj = active_sim.get_config_object()
                            self._deserialize_dict_to_object(config_obj, state_data["simulation_config"])
                            logger.info("Simulation configuration restored")
                        elif hasattr(active_sim, 'config'):
                            self._deserialize_dict_to_object(active_sim.config, state_data["simulation_config"])
                            logger.info("Simulation configuration restored")
                    
                    # Restore simulation status (process values)
                    if "simulation_status" in state_data and state_data["simulation_status"]:
                        if hasattr(active_sim, 'get_status_object'):
                            status_obj = active_sim.get_status_object()
                            self._deserialize_dict_to_object(status_obj, state_data["simulation_status"])
                            logger.info("Simulation status restored")
                        elif hasattr(active_sim, 'status'):
                            self._deserialize_dict_to_object(active_sim.status, state_data["simulation_status"])
                            logger.info("Simulation status restored")
                    
                    logger.info(f"Simulation '{sim_name}' loaded and configured")
                    print(f"✓ Simulation '{sim_name}' loaded successfully")
                
                # Note: IO configuration should be loaded separately by the IO handler
                if "io_config_path" in state_data:
                    io_path = state_data["io_config_path"]
                    logger.info(f"IO configuration path: {io_path}")
                    print(f"  IO configuration: {io_path}")
            
            logger.info(f"Complete state loaded from: {import_filename}")
            print(f"✓ Configuration loaded from: {import_filename}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in state file: {e}")
            print(f"✗ Invalid JSON in configuration file: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load complete state: {e}")
            print(f"✗ Failed to load configuration: {e}")
            return False
