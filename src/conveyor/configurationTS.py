import csv
import json
from pathlib import Path


class configuration:
    """
    Constructor: create configuration object with default parameters
    """

    def __init__(self):
        """
        IO settings - These will be overwritten by load_io_config()
        """
        # PLC OUTPUTS (from PLC perspective = simulator inputs)
        # DIGITAL
        self.DQValveIn = {"byte": 0, "bit": 0}   # False = Closed
        self.DQValveOut = {"byte": 0, "bit": 1}  # False = Closed
        self.DQHeater = {"byte": 0, "bit": 2}    # False = Off
        # ANALOG
        self.AQValveInFraction = {"byte": 2}     # 0 = Closed, MAX = full open
        self.AQValveOutFraction = {"byte": 4}    # 0 = Closed, MAX = full open
        self.AQHeaterFraction = {"byte": 6}      # 0 = Off, MAX = full power

        # PLC INPUTS (from PLC perspective = simulator outputs)
        # DIGITAL
        self.DILevelSensorHigh = {"byte": 0, "bit": 0}
        self.DILevelSensorLow = {"byte": 0, "bit": 1}
        # ANALOG
        self.AILevelSensor = {"byte": 2}
        self.AITemperatureSensor = {"byte": 4}

        # Mapping of signal names from io_config.json to configuration attributes
        self.io_signal_mapping = {
            # === INPUTS FOR SIMULATOR (= PLC OUTPUTS) ===
            # Digital outputs
            "ValveIn": "DQValveIn",
            "UpperValve": "DQValveIn",
            "ValveOut": "DQValveOut",
            "LowerValve": "DQValveOut",
            "Heater": "DQHeater",
            
            # Analog outputs (controllable valves/heater)
            "ValveInFraction": "AQValveInFraction",
            "UpperValveFraction": "AQValveInFraction",
            "ValveOutFraction": "AQValveOutFraction",
            "LowerValveFraction": "AQValveOutFraction",
            "HeaterFraction": "AQHeaterFraction",
            "HeaterPower": "AQHeaterFraction",
            
            # === OUTPUTS FROM SIMULATOR (= PLC INPUTS) ===
            # Digital inputs
            "LevelSensorHigh": "DILevelSensorHigh",
            "TanklevelSensorHigh": "DILevelSensorHigh",
            "LevelSensorLow": "DILevelSensorLow",
            "TanklevelSensorLow": "DILevelSensorLow",
            
            # Analog inputs
            "LevelSensor": "AILevelSensor",
            "TankLevel": "AILevelSensor",
            "TemperatureSensor": "AITemperatureSensor",
            "TankTemperature": "AITemperatureSensor",
        }

        # Load IO configuration if it exists
        self.load_io_config()
        
        self.lowestByte, self.highestByte = self.get_byte_range()

        """
        Simulation settings
        """
        self.simulationInterval = 0.2  # in seconds
        
        """
        Process settings
        """
        self.tankVolume: float = 200.0
        self.valveInMaxFlow: float = 5.0
        self.valveOutMaxFlow: float = 2.0
        self.ambientTemp: float = 21.0
        self.digitalLevelSensorHighTriggerLevel: float = 0.9 * self.tankVolume
        self.digitalLevelSensorLowTriggerLevel: float = 0.1 * self.tankVolume
        self.heaterMaxPower: float = 10000.0
        self.tankHeatLoss: float = 150.0
        self.liquidSpecificHeatCapacity: float = 4186.0
        self.liquidSpecificWeight: float = 0.997
        self.liquidBoilingTemp: float = 100.0

        self.importExportVariableList = [
            "tankVolume", "valveInMaxFlow", "valveOutMaxFlow", "ambientTemp", 
            "digitalLevelSensorHighTriggerLevel", "digitalLevelSensorLowTriggerLevel", 
            "heaterMaxPower", "tankHeatLoss", "liquidSpecificHeatCapacity", 
            "liquidBoilingTemp", "liquidSpecificWeight"
        ]

    def load_io_config(self, config_file: str = "io_config.json"):
        """
        Load IO configuration from io_config.json and update the IO addresses
        """
        io_config_path = Path(config_file)
        
        if not io_config_path.exists():
            print(f"i{config_file} not found, using default IO addresses")
            return False
        
        try:
            with open(io_config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            signals = config_data.get('signals', [])
            updated_signals = []
            
            for signal in signals:
                signal_name = signal.get('name', '')
                # ... (rest of signal extraction and attribute matching logic remains the same) ...
                signal_type = signal.get('type', '')
                signal_status = signal.get('status', '')
                address = signal.get('address', '')
                byte_str = signal.get('byte', '')
                bit_str = signal.get('bit', '')
                
                # Find the mapping for this signal (partial match)
                config_attr = None
                for key, attr in self.io_signal_mapping.items():
                    if key.lower() in signal_name.lower():
                        config_attr = attr
                        break
                
                if not config_attr:
                    print(f"Signal '{signal_name}' not recognized, skipped")
                    continue
                
                # Parse address data
                try:
                    byte_val = int(byte_str) if byte_str else None
                    bit_val = int(bit_str) if bit_str else None
                    
                    if byte_val is None:
                        print(f"No byte value for '{signal_name}'")
                        continue
                    
                    # Update the configuration
                    if signal_type == 'bool' and bit_val is not None:
                        setattr(self, config_attr, {"byte": byte_val, "bit": bit_val})
                        updated_signals.append(f"{config_attr}: {address}")
                        print(f"{config_attr:30s} <- {signal_name:30s} @ {address}")
                    
                    elif signal_type in ['int', 'word']:
                        setattr(self, config_attr, {"byte": byte_val})
                        updated_signals.append(f"{config_attr}: {address}")
                        print(f"{config_attr:30s} <- {signal_name:30s} @ {address}")
                
                except (ValueError, AttributeError) as e:
                    print(f"Error parsing '{signal_name}': {e}")
                    continue
            
            if updated_signals:
                print(f"\nIO configuration loaded: {len(updated_signals)} signals configured")
                return True
            else:
                print(f"\nNo signals configured from {config_file}")
                return False
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error in {config_file}: {e}")
            return False
        except Exception as e:
            print(f"Error loading {config_file}: {e}")
            return False

    def reload_io_config(self):
        """
        Reload IO configuration and update byte ranges
        """
        print("\nReloading IO configuration...")
        success = self.load_io_config()
        self.lowestByte, self.highestByte = self.get_byte_range()
        print(f"Byte range: {self.lowestByte} to {self.highestByte}\n")
        return success

    def get_byte_range(self):
        """
        Return the lowest and highest byte used in all IO definitions.
        """
        bytes_used = []

        for _, value in self.__dict__.items():
            if isinstance(value, dict) and "byte" in value:
                bytes_used.append(value["byte"])

        if bytes_used:
            lowestByte = min(bytes_used)
            highestByte = max(bytes_used)
            return lowestByte, highestByte
        else:
            return 0, 10  # Default range

    def update_io_range(self):
        """
        Call this when IO data changes (e.g. GUI edits addresses).
        """
        self.lowestByte, self.highestByte = self.get_byte_range()

    def get_io_summary(self):
        """
        Provide an overview of all IO configuration
        """
        summary = {
            'inputs': [],   # PLC inputs (simulator outputs)
            'outputs': []   # PLC outputs (simulator inputs)
        }
        
        # Digital outputs (PLC -> Simulator)
        summary['outputs'].append({
            'name': 'DQValveIn',
            'address': f"Q{self.DQValveIn['byte']}.{self.DQValveIn['bit']}",
            'type': 'bool'
        })
        summary['outputs'].append({
            'name': 'DQValveOut',
            'address': f"Q{self.DQValveOut['byte']}.{self.DQValveOut['bit']}",
            'type': 'bool'
        })
        summary['outputs'].append({
            'name': 'DQHeater',
            'address': f"Q{self.DQHeater['byte']}.{self.DQHeater['bit']}",
            'type': 'bool'
        })
        
        # Analog outputs
        summary['outputs'].append({
            'name': 'AQValveInFraction',
            'address': f"QW{self.AQValveInFraction['byte']}",
            'type': 'word'
        })
        summary['outputs'].append({
            'name': 'AQValveOutFraction',
            'address': f"QW{self.AQValveOutFraction['byte']}",
            'type': 'word'
        })
        summary['outputs'].append({
            'name': 'AQHeaterFraction',
            'address': f"QW{self.AQHeaterFraction['byte']}",
            'type': 'word'
        })
        
        # Digital inputs (Simulator -> PLC)
        summary['inputs'].append({
            'name': 'DILevelSensorHigh',
            'address': f"I{self.DILevelSensorHigh['byte']}.{self.DILevelSensorHigh['bit']}",
            'type': 'bool'
        })
        summary['inputs'].append({
            'name': 'DILevelSensorLow',
            'address': f"I{self.DILevelSensorLow['byte']}.{self.DILevelSensorLow['bit']}",
            'type': 'bool'
        })
        
        # Analog inputs
        summary['inputs'].append({
            'name': 'AILevelSensor',
            'address': f"IW{self.AILevelSensor['byte']}",
            'type': 'word'
        })
        summary['inputs'].append({
            'name': 'AITemperatureSensor',
            'address': f"IW{self.AITemperatureSensor['byte']}",
            'type': 'word'
        })
        
        return summary

    # Save config to a JSON file (NEW - alongside CSV)
    def saveToJsonFile(self, exportFileName: str = "tankSimConfig.json"):
        """Save configuration in JSON format"""
        print(f"Exporting config to JSON: {exportFileName}")
        
        config_dict = {}
        for variable in self.importExportVariableList:
            config_dict[variable] = getattr(self, variable)
        
        # Add IO configuration
        config_dict['io_summary'] = self.get_io_summary()
        config_dict['lowestByte'] = self.lowestByte
        config_dict['highestByte'] = self.highestByte
        
        try:
            with open(exportFileName, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            print(f"JSON config saved")
            return True
        except Exception as e:
            print(f"Error saving JSON: {e}")
            return False

    # Save config to a CSV file (EXISTING)
    def saveToFile(self, exportFileName, createFile: bool = False):
        """Save configuration in CSV format"""
        print(f"Exporting config to CSV: {exportFileName}")
        openMode = "w" if createFile else "a"

        with open(exportFileName, openMode, newline="") as file:
            writer = csv.writer(file)
            if createFile:
                writer.writerow(["variable", "value"])
            for variable in self.importExportVariableList:
                writer.writerow([variable, getattr(self, variable)])

    # Load config from JSON (NEW)
    def loadFromJsonFile(self, importFileName: str = "tankSimConfig.json"):
        """Load configuration from JSON format"""
        try:
            with open(importFileName, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            for variable in self.importExportVariableList:
                if variable in config_dict:
                    setattr(self, variable, config_dict[variable])
            
            print(f"Config loaded from JSON: {importFileName}")
            
            # Also reload IO config
            self.reload_io_config()
            return True
            
        except FileNotFoundError:
            print(f"File not found: {importFileName}")
            return False
        except Exception as e:
            print(f"Error loading JSON config: {e}")
            return False

    # Read config back from the CSV file 
    def loadFromFile(self, importFileName: str):
        """Load configuration from CSV format"""
        with open(importFileName, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                for variable in self.importExportVariableList:
                    if row["variable"] == variable:
                        setattr(self, variable, type(
                            getattr(self, variable))(row["value"]))
        print(f"Config loaded from CSV: {importFileName}")
        
        self.reload_io_config()

    def print_current_config(self):
        """Print current configuration for debugging"""
        print("\n" + "="*60)
        print("CURRENT IO CONFIGURATION")
        print("="*60)
        
        summary = self.get_io_summary()
        
        print("\n PLC OUTPUTS (Simulator Inputs):")
        for output in summary['outputs']:
            print(f"  {output['name']:25s} @ {output['address']:8s} ({output['type']})")
        
        print("\nPLC INPUTS (Simulator Outputs):")
        for input_sig in summary['inputs']:
            print(f"  {input_sig['name']:25s} @ {input_sig['address']:8s} ({input_sig['type']})")
        
        print(f"\nByte range: {self.lowestByte} - {self.highestByte}")
        print("="*60 + "\n")