import json
from pathlib import Path


class configuration:
    """Constructor: create configuration object with default parameters"""

    def __init__(self):
        """IO settings - These will be overwritten by load_io_config()"""
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

        # Mapping of signal names from io_config.json to configuration attributes
        self.io_signal_mapping = {
            # INPUTS FOR SIMULATOR (= PLC OUTPUTS)
            "ValveIn": "DQValveIn",
            "UpperValve": "DQValveIn",
            "ValveOut": "DQValveOut",
            "LowerValve": "DQValveOut",
            "Heater": "DQHeater",
            "ValveInFraction": "AQValveInFraction",
            "UpperValveFraction": "AQValveInFraction",
            "ValveOutFraction": "AQValveOutFraction",
            "LowerValveFraction": "AQValveOutFraction",
            "HeaterFraction": "AQHeaterFraction",
            "HeaterPower": "AQHeaterFraction",

            # OUTPUTS FROM SIMULATOR (= PLC INPUTS)
            "LevelSensorHigh": "DILevelSensorHigh",
            "TanklevelSensorHigh": "DILevelSensorHigh",
            "LevelSensorLow": "DILevelSensorLow",
            "TanklevelSensorLow": "DILevelSensorLow",
            "LevelSensor": "AILevelSensor",
            "TankLevel": "AILevelSensor",
            "TemperatureSensor": "AITemperatureSensor",
            "TankTemperature": "AITemperatureSensor",
        }

        # Reverse mapping: attribute name -> signal name (for status display)
        self.reverse_io_mapping = {v: k for k,
                                   v in self.io_signal_mapping.items()}

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
        self.heaterMaxPower: float = 10000.0
        self.tankHeatLoss: float = 150.0
        self.liquidTempTimeDelay: float = 0.0  # in seconds
        self.liquidSpecificHeatCapacity: float = 4186.0
        self.liquidSpecificWeight: float = 0.997
        self.liquidBoilingTemp: float = 100.0

        self.importExportVariableList = [
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
                print("Warning: No signals found in IO configuration")
                return

            for signal in config_data['signals']:
                signal_name = signal.get('name', '')
                signal_type = signal.get('type', '')
                address = signal.get('address', '')

                if signal_name in self.io_signal_mapping:
                    attr_name = self.io_signal_mapping[signal_name]

                    if '.' in address:
                        parts = address.split('.')
                        byte_part = parts[0][1:]
                        bit_part = parts[1]

                        try:
                            byte_val = int(byte_part)
                            bit_val = int(bit_part)
                            setattr(self, attr_name, {
                                    "byte": byte_val, "bit": bit_val})
                        except ValueError:
                            print(f"Cannot parse address: {address}")

                    elif 'W' in address:
                        byte_part = address.split('W')[1]
                        try:
                            byte_val = int(byte_part)
                            setattr(self, attr_name, {"byte": byte_val})
                        except ValueError:
                            print(f"Cannot parse address: {address}")

            self.update_io_range()
            print(
                f"IO configuration loaded, byte range: {self.lowestByte} - {self.highestByte}")

        except FileNotFoundError:
            print(f"IO configuration file not found: {config_file_path}")
        except json.JSONDecodeError:
            print(f"Invalid JSON in: {config_file_path}")
        except Exception as e:
            print(f"Error loading IO configuration: {e}")

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
