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
    """Configuration object with default parameters for tank simulation."""

    def __init__(self):
        """Initialize configuration with default IO settings and process parameters."""

        # ===== IO SETTINGS =====
        # These will be overwritten by load_io_config_from_file()

        # PLC OUTPUTS (from PLC perspective = simulator inputs)
        # DIGITAL
        self.DQValveIn = {"byte": 0, "bit": 0}
        self.DQValveOut = {"byte": 0, "bit": 1}
        self.DQHeater = {"byte": 0, "bit": 2}

        # ANALOG
        self.AQValveInFraction = {"byte": 2}
        self.AQValveOutFraction = {"byte": 4}
        self.AQHeaterFraction = {"byte": 6}

        # PLC INPUTS (from PLC perspective = simulator outputs)
        # DIGITAL
        self.DILevelSensorHigh = {"byte": 0, "bit": 0}
        self.DILevelSensorLow = {"byte": 0, "bit": 1}

        # ANALOG
        self.AILevelSensor = {"byte": 2}
        self.AITemperatureSensor = {"byte": 4}

        # PID Valve Controls - DIGITAL (PLC Inputs)
        self.DIStart = {"byte": 0, "bit": 5}
        self.DIStop = {"byte": 0, "bit": 6}
        self.DIReset = {"byte": 0, "bit": 7}
        self.DIAuto = {"byte": 1, "bit": 0}
        self.DIMan = {"byte": 1, "bit": 1}
        self.AItemp = {"byte": 1, "bit": 2}
        self.DItemp = {"byte": 1, "bit": 3}
        self.AIlevel = {"byte": 1, "bit": 4}
        self.DIlevel = {"byte": 1, "bit": 5}

        # PID Valve Controls - ANALOG (PLC Inputs)
        self.AITempSP = {"byte": 12}
        self.AILevelSP = {"byte": 14}

        # PLC Outputs - General Controls
        # ANALOG
        self.AQGen_Analog1 = {"byte": 12}
        self.AQGen_Analog2 = {"byte": 14}
        self.AQgen_Analog3 = {"byte": 16}

        # DIGITAL
        self.DQGen_Indicator1 = {"byte": 0, "bit": 5}
        self.DQGen_Indicator2 = {"byte": 0, "bit": 6}
        self.DQGen_Indicator3 = {"byte": 0, "bit": 7}
        self.DQGen_Indicator4 = {"byte": 1, "bit": 0}

        # PLC Inputs - General Controls
        # DIGITAL
        self.DIGen_Start = {"byte": 0, "bit": 2}
        self.DIGen_Stop = {"byte": 0, "bit": 3}
        self.DIGen_Reset = {"byte": 0, "bit": 4}

        # ANALOG
        self.AIGen_Control1 = {"byte": 6}
        self.AIGen_Control2 = {"byte": 8}
        self.AIGen_Control3 = {"byte": 10}

        # ===== SIGNAL MAPPINGS =====

        # Dictionary to store signal names from IO configuration window
        # Maps attribute name (e.g., "DQValveOut") to signal name (e.g., "Sim_OutletValveOnOff")
        self.signal_names: dict[str, str] = {}

        # Custom signal name overrides, links custom names for general controls
        self.custom_signal_names: dict[str, str] = {}

        # Mapping: signal names (from io_config.json) -> internal attribute names
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
            "Sim_StartButton": "DIStart",
            "Sim_StopButton": "DIStop",
            "Sim_ResetButton": "DIReset",

            # Mode Switches
            "Sim_AutomaticMode": "DIAuto",
            "Sim_ManualMode": "DIMan",
            "Sim_TemperatureAnalogControl": "AItemp",
            "Sim_TemperatureDigitalControl": "DItemp",
            "Sim_WaterLevelAnalogControl": "AIlevel",
            "Sim_WaterLevelDigitalControl": "DIlevel",

            # Setpoints
            "Sim_TemperatureSetpoint": "AITempSP",
            "Sim_WaterLevelSetpoint": "AILevelSP",

            # General Controls - PLC Inputs => Simulator Outputs
            "Start": "DIGen_Start",
            "Stop": "DIGen_Stop",
            "Reset": "DIGen_Reset",
            "Control1": "AIGen_Control1",
            "Control2": "AIGen_Control2",
            "Control3": "AIGen_Control3",

            # General Controls - PLC Outputs => Simulator Inputs
            "Indicator1": "DQGen_Indicator1",
            "Indicator2": "DQGen_Indicator2",
            "Indicator3": "DQGen_Indicator3",
            "Indicator4": "DQGen_Indicator4",
            "Analog1": "AQGen_Analog1",
            "Analog2": "AQGen_Analog2",
            "Analog3": "AQGen_Analog3",
        }

        # Reverse mapping: internal attribute names -> signal names (for status display)
        # Example: {"DQValveIn": "Sim_InletValveOnOff", ...}
        self.reverse_io_mapping = {
            attr_name: signal_name
            for signal_name, attr_name in self.io_signal_mapping.items()
        }

        # Tracks which attributes are enabled by the current IO configuration file
        # Used for resetting process images
        # Signals not present in the JSON will remain disabled and should not be written/read
        self.enabled_attrs: set[str] = set()

        # Calculate byte range for communication protocols
        self.lowestByte, self.highestByte = self.get_byte_range()

        # ===== SIMULATION SETTINGS =====
        self.simulationInterval = 0.1  # seconds

        # ===== PROCESS SETTINGS =====
        self.tankVolume: float = 200.0  # liters
        self.valveInMaxFlow: float = 5.0  # liters/second
        self.valveOutMaxFlow: float = 2.0  # liters/second
        self.liquidVolumeTimeDelay: float = 0.0  # seconds

        self.ambientTemp: float = 21.0  # °C
        self.digitalLevelSensorHighTriggerLevel: float = 0.9 * self.tankVolume  # liters
        self.digitalLevelSensorLowTriggerLevel: float = 0.1 * self.tankVolume  # liters

        self.heaterMaxPower: float = 15000.0  # watts
        self.tankHeatLoss: float = 150.0  # watts
        self.liquidTempTimeDelay: float = 0.0  # seconds
        self.liquidSpecificHeatCapacity: float = 4186.0  # J/(kg·K)
        self.liquidSpecificWeight: float = 0.997  # kg/liter
        self.liquidBoilingTemp: float = 100.0  # °C

        # Variables that can be imported/exported
        self.importExportVariableList = [
            "simulationInterval",
            "tankVolume",
            "valveInMaxFlow",
            "valveOutMaxFlow",
            "ambientTemp",
            "digitalLevelSensorHighTriggerLevel",
            "digitalLevelSensorLowTriggerLevel",
            "heaterMaxPower",
            "tankHeatLoss",
            "liquidSpecificHeatCapacity",
            "liquidBoilingTemp",
            "liquidSpecificWeight"
        ]

    def get_byte_range(self) -> tuple[int, int]:
        """
        Calculate the lowest and highest byte addresses used in IO definitions.
        Used for resetting communication protocol buffers.

        Returns:
            Tuple of (lowest_byte, highest_byte)
        """
        bytes_used = []

        for value in self.__dict__.values():
            if isinstance(value, dict) and "byte" in value:
                bytes_used.append(value["byte"])

        if bytes_used:
            return min(bytes_used), max(bytes_used)
        else:
            return 0, 10  # Default range if no bytes defined

    def update_io_range(self) -> None:
        """Update byte range after IO configuration changes (e.g., GUI edits)."""
        self.lowestByte, self.highestByte = self.get_byte_range()

    def load_io_config_from_file(self, config_file_path: Path) -> None:
        """
        Load IO configuration from JSON file and update internal mappings.

        Reads io_configuration.json and updates byte/bit addresses for all mapped signals.
        Only signals present in the JSON file will be enabled for communication.

        Args:
            config_file_path: Path to the io_configuration.json file
        """
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            if 'signals' not in config_data:
                logger.warning("No signals found in IO configuration")
                return

            # Reset enabled signals - will be repopulated from file
            self.enabled_attrs.clear()
            self.signal_names.clear()  # Reset signal names

            # Build lookup including custom signal name aliases
            name_to_attr = dict(self.io_signal_mapping)

            # Add custom signal name overrides
            if hasattr(self, "custom_signal_names"):
                for attr, custom_name in self.custom_signal_names.items():
                    if custom_name:
                        name_to_attr[custom_name] = attr

            # Process each signal from the JSON file
            for signal in config_data['signals']:
                signal_name = signal.get('name', '')
                byte_str = signal.get('byte', '')
                bit_str = signal.get('bit', '')

                if signal_name not in name_to_attr:
                    continue  # Skip unknown signals

                attr_name = name_to_attr[signal_name]

                try:
                    byte_val = int(byte_str) if byte_str else None

                    if byte_val is None:
                        logger.warning(
                            f"Cannot parse byte value for signal '{signal_name}'")
                        continue

                    # Digital signal (has bit address)
                    if bit_str:
                        bit_val = int(bit_str)
                        setattr(self, attr_name, {
                                "byte": byte_val, "bit": bit_val})
                    else:
                        # Analog signal (word/int address, no bit)
                        setattr(self, attr_name, {"byte": byte_val})

                    self.enabled_attrs.add(attr_name)
                    # Store signal name for later retrieval (e.g., for SVG tag labels)
                    self.signal_names[attr_name] = signal_name

                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Cannot parse address for signal '{signal_name}': {e}")

            # Update byte range after loading new configuration
            self.update_io_range()

            # Provide aliases expected by IOHandler for general controls
            try:
                if hasattr(self, 'AIGen_Control1'):
                    self.AIControl1 = self.AIGen_Control1
                if hasattr(self, 'AIGen_Control2'):
                    self.AIControl2 = self.AIGen_Control2
                if hasattr(self, 'AIGen_Control3'):
                    self.AIControl3 = self.AIGen_Control3
            except Exception:
                pass

        except FileNotFoundError:
            logger.error(
                f"IO configuration file not found: {config_file_path}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in: {config_file_path}")
        except Exception as e:
            logger.error(f"Error loading IO configuration: {e}")

    def get_signal_name_for_attribute(self, attr_name: str) -> str:
        """
        Get the user-facing signal name for an internal attribute name.

        Used for status display and logging.

        Args:
            attr_name: Internal attribute name (e.g., "DQValveIn")

        Returns:
            Signal name (e.g., "Sim_InletValveOnOff") or empty string if not found
        """
        return self.reverse_io_mapping.get(attr_name, "")
