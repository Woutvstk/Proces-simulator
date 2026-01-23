"""
Tank Simulation Configuration - Configuration parameters for PID tank simulation.

Contains:
- IO address mappings (PLC inputs/outputs)
- Physical parameters (tank volume, flow rates, heating power)
- PID controller settings
- Simulation timing parameters

External Libraries Used:
- json (Python Standard Library) - IO configuration file parsing
- pathlib (Python Standard Library) - File path handling
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class configuration:
    """Constructor: create configuration object with default parameters"""

    def __init__(self):
        """IO settings - These will be overwritten by load_io_config()"""
        # PLC OUTPUTS (from PLC perspective = simulator inputs)
        # DIGITAL
        self.DQValveIn = {"byte": 0, "bit": 0}
        self.DQValveOut = {"byte": 0, "bit": 1}
        self.DQHeater = {"byte": 0, "bit": 2}
        # General Controls - DIGITAL (PLC Inputs)
        self.DIStart = {"byte": 0, "bit": 2}
        self.DIStop = {"byte": 0, "bit": 3}
        self.DIReset = {"byte": 0, "bit": 4}
        # ANALOG
        self.AQValveInFraction = {"byte": 2}
        self.AQValveOutFraction = {"byte": 4}
        self.AQHeaterFraction = {"byte": 6}
        # General Controls - ANALOG (PLC Inputs)
        self.AIControl1 = {"byte": 6}
        self.AIControl2 = {"byte": 8}
        self.AIControl3 = {"byte": 10}

        # PLC INPUTS (from PLC perspective = simulator outputs)
        # DIGITAL
        self.DILevelSensorHigh = {"byte": 0, "bit": 0}
        self.DILevelSensorLow = {"byte": 0, "bit": 1}
        # General Controls - DIGITAL (PLC Outputs)
        self.DQIndicator1 = {"byte": 0, "bit": 5}
        self.DQIndicator2 = {"byte": 0, "bit": 6}
        self.DQIndicator3 = {"byte": 0, "bit": 7}
        self.DQIndicator4 = {"byte": 1, "bit": 0}
        # ANALOG
        self.AILevelSensor = {"byte": 2}
        self.AITemperatureSensor = {"byte": 4}
        # General Controls - ANALOG (PLC Outputs)
        self.AQAnalog1 = {"byte": 12}
        self.AQAnalog2 = {"byte": 14}
        self.AQAnalog3 = {"byte": 16}

        # PID Valve Controls - DIGITAL (PLC Inputs)
        self.DIPidValveStart = {"byte": 0, "bit": 5}
        self.DIPidValveStop = {"byte": 0, "bit": 6}
        self.DIPidValveReset = {"byte": 0, "bit": 7}
        self.DIPidValveAuto = {"byte": 1, "bit": 0}
        self.DIPidValveMan = {"byte": 1, "bit": 1}
        self.DIPidTankValveAItemp = {"byte": 1, "bit": 2}
        self.DIPidTankValveDItemp = {"byte": 1, "bit": 3}
        self.DIPidTankValveAIlevel = {"byte": 1, "bit": 4}
        self.DIPidTankValveDIlevel = {"byte": 1, "bit": 5}
        # PID Valve Controls - ANALOG (PLC Inputs)
        self.AIPidTankTempSP = {"byte": 12}
        self.AIPidTankLevelSP = {"byte": 14}

        # Custom signal name overrides (persisted via IO save/load)
        self.custom_signal_names: dict[str, str] = {}

        # Mapping of signal names from io_config.json to configuration attributes
        self.io_signal_mapping = {
            # INPUTS FOR SIMULATOR (= PLC OUTPUTS)
            "Sim_InletValveOnOff": "DQValveIn",
            "Sim_OutletValveOnOff": "DQValveOut",
            "Sim_HeaterOnOff": "DQHeater",
            "Sim_InletValvePosition": "AQValveInFraction",
            "Sim_OutletValvePosition": "AQValveOutFraction",
            "Sim_HeaterPowerLevel": "AQHeaterFraction",

            # OUTPUTS FROM SIMULATOR (= PLC INPUTS)
            "Sim_WaterLevelHigh": "DILevelSensorHigh",
            "Sim_WaterLevelLow": "DILevelSensorLow",
            "Sim_WaterLevelMeasurement": "AILevelSensor",
            "Sim_WaterTemperatureMeasurement": "AITemperatureSensor",

            # PLC Controls Buttons
            "Sim_StartButton": "DIPidValveStart",
            "Sim_StopButton": "DIPidValveStop",
            "Sim_ResetButton": "DIPidValveReset",

            # Mode Switches
            "Sim_AutomaticMode": "DIPidValveAuto",
            "Sim_ManualMode": "DIPidValveMan",
            "Sim_TemperatureAnalogControl": "DIPidTankValveAItemp",
            "Sim_TemperatureDigitalControl": "DIPidTankValveDItemp",
            "Sim_WaterLevelAnalogControl": "DIPidTankValveAIlevel",
            "Sim_WaterLevelDigitalControl": "DIPidTankValveDIlevel",

            # Setpoints
            "Sim_TemperatureSetpoint": "AIPidTankTempSP",
            "Sim_WaterLevelSetpoint": "AIPidTankLevelSP",

            # General Controls - PLC Inputs => Simulator Outputs
            "Start": "DIStart",
            "Stop": "DIStop",
            "Reset": "DIReset",
            "Control1": "AIControl1",
            "Control2": "AIControl2",
            "Control3": "AIControl3",

            # General Controls - PLC Outputs => Simulator Inputs
            "Indicator1": "DQIndicator1",
            "Indicator2": "DQIndicator2",
            "Indicator3": "DQIndicator3",
            "Indicator4": "DQIndicator4",
            "Analog1": "AQAnalog1",
            "Analog2": "AQAnalog2",
            "Analog3": "AQAnalog3",
        }

        # Reverse mapping: attribute name -> signal name (for status display)
        self.reverse_io_mapping = {v: k for k,
                                   v in self.io_signal_mapping.items()}

        # Tracks which attributes are explicitly enabled by the current IO configuration file
        # Signals not present in the JSON will remain disabled and should not be written/read
        self.enabled_attrs: set[str] = set()

        self.lowestByte, self.highestByte = self.get_byte_range()

        """Simulation settings"""
        self.simulationInterval = 0.2  # in seconds

        """Process settings"""
        self.tankVolume: float = 200.0
        self.valveInMaxFlow: float = 5.0
        self.valveOutMaxFlow: float = 2.0
        self.liquidVolumeTimeDelay: float = 0.0  # in seconds
        self.ambientTemp: float = 21.0
        self.digitalLevelSensorHighTriggerLevel: float = 0.9 * self.tankVolume
        self.digitalLevelSensorLowTriggerLevel: float = 0.1 * self.tankVolume
        self.heaterMaxPower: float = 750.0
        self.tankHeatLoss: float = 150.0
        self.liquidTempTimeDelay: float = 0.0  # in seconds
        self.liquidSpecificHeatCapacity: float = 4186.0
        self.liquidSpecificWeight: float = 0.997
        self.liquidBoilingTemp: float = 100.0

        self.importExportVariableList = [
            "simulationInterval",
            "tankVolume", "valveInMaxFlow", "valveOutMaxFlow", "ambientTemp",
            "digitalLevelSensorHighTriggerLevel", "digitalLevelSensorLowTriggerLevel",
            "heaterMaxPower", "tankHeatLoss", "liquidSpecificHeatCapacity",
            "liquidBoilingTemp", "liquidSpecificWeight"
        ]

    def get_byte_range(self):
        """Return the lowest and highest byte used in all IO definitions."""
        bytes_used = []

        for _, value in self.__dict__.items():
            if isinstance(value, dict) and "byte" in value:
                bytes_used.append(value["byte"])

        if bytes_used:
            lowestByte = min(bytes_used)
            highestByte = max(bytes_used)
            return lowestByte, highestByte
        else:
            return 0, 10

    def update_io_range(self):
        """Call this when IO data changes (e.g. GUI edits addresses)."""
        self.lowestByte, self.highestByte = self.get_byte_range()

    def load_io_config_from_file(self, config_file_path: Path):
        """
        Load IO configuration from JSON file and update internal mappings.
        This method reads the io_configuration.json and updates the byte/bit
        addresses for all mapped signals.

        Args:
            config_file_path: Path to the io_configuration.json file
        """
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            if 'signals' not in config_data:
                logger.warning("No signals found in IO configuration")
                return

            # Reset enabled signals; will be repopulated based on file content
            self.enabled_attrs.clear()

            # Build lookup that includes custom signal names (aliases)
            name_to_attr = dict(self.io_signal_mapping)
            try:
                if hasattr(self, "custom_signal_names"):
                    for attr, custom_name in self.custom_signal_names.items():
                        if custom_name:
                            name_to_attr[custom_name] = attr
            except Exception:
                pass

            for signal in config_data['signals']:
                signal_name = signal.get('name', '')
                signal_type = signal.get('type', '')
                
                # Use byte and bit directly from JSON (preferred source)
                byte_str = signal.get('byte', '')
                bit_str = signal.get('bit', '')

                if signal_name in name_to_attr:
                    attr_name = name_to_attr[signal_name]

                    try:
                        # Try to use byte/bit from JSON first
                        byte_val = int(byte_str) if byte_str else None
                        
                        if byte_val is not None:
                            # Check if this is a digital signal (has bit info)
                            if bit_str:
                                bit_val = int(bit_str)
                                setattr(self, attr_name, {"byte": byte_val, "bit": bit_val})
                            else:
                                # Analog signal (word/int address, no bit)
                                setattr(self, attr_name, {"byte": byte_val})
                            
                            self.enabled_attrs.add(attr_name)
                        else:
                            logger.warning(f"Cannot parse byte value for signal '{signal_name}'")
                            
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Cannot parse address for signal '{signal_name}': {e}")

            self.update_io_range()

        except FileNotFoundError:
            logger.error(f"IO configuration file not found: {config_file_path}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in: {config_file_path}")
        except Exception as e:
            logger.error(f"Error loading IO configuration: {e}")

    def get_signal_name_for_attribute(self, attr_name: str) -> str:
        """
        Get the signal name for a given attribute name.
        Used for status display.

        Args:
            attr_name: Internal attribute name (e.g., "DQValveIn")

        Returns:
            Signal name (e.g., "ValveIn") or empty string if not found
        """
        return self.reverse_io_mapping.get(attr_name, "")
