"""
Tank Simulation Status - Runtime state for PID tank simulation.

Contains:
- Valve positions (inlet/outlet opening fractions)
- Heater power and temperature
- Liquid volume and level sensors
- Flow rates
- PID controller state
- General control commands

External Libraries Used:
- csv (Python Standard Library) - Status export to CSV file
- logging (Python Standard Library) - Error and info logging
"""

import csv
import logging

logger = logging.getLogger(__name__)

import json


class status:
    def __init__(self):
        # Valve IN status (written by: plc, gui or import)
        self.valveInOpenFraction: float = 0.0

        # Valve OUT status (written by: plc, gui or import)
        self.valveOutOpenFraction: float = 0.0

        # Heating element status (written by: plc, gui or import)
        self.heaterPowerFraction: float = 0.0

        # Digital level sensor status (written by: simulation)
        self.digitalLevelSensorLowTriggered: bool = False
        self.digitalLevelSensorHighTriggered: bool = False

        # Liquid parameters (written by: simulation, import)
        self.liquidVolume: float = 100.0
        self.liquidTemperature: float = 0.0

        # Simulation status (written by: gui)
        self.simRunning = False

        # Flow rates (written by simulation)
        self.flowRateIn: float = 0.0
        self.flowRateOut: float = 0.0

        # General Controls - commands to PLC (written by: gui)
        self.generalStartCmd: bool = False
        self.generalStopCmd: bool = False
        self.generalResetCmd: bool = False

        # General Controls - slider values (written by: gui)
        self.generalControl1Value: int = 0
        self.generalControl2Value: int = 0
        self.generalControl3Value: int = 0

        # General Controls - indicators from PLC (written by: plc)
        self.indicator1: bool = False
        self.indicator2: bool = False
        self.indicator3: bool = False
        self.indicator4: bool = False

        # General Controls - analog outputs from PLC (written by: plc)
        self.analog1: int = 0
        self.analog2: int = 0
        self.analog3: int = 0

        self.importExportVariableList = [
            "liquidVolume", "liquidTemperature",
            "valveInOpenFraction", "valveOutOpenFraction", "heaterPowerFraction",
            "generalStartCmd", "generalStopCmd", "generalResetCmd",
            "generalControl1Value", "generalControl2Value", "generalControl3Value",
            "indicator1", "indicator2", "indicator3", "indicator4",
            "analog1", "analog2", "analog3",
            "pidStartCmd", "pidStopCmd", "pidResetCmd",
            "temperatureSetpoint", "levelSetpoint",
        ]

        # General Controls - PLC Outputs reflected in status (written by: plc or force)
        self.generalStartCmd: bool = False
        self.generalStopCmd: bool = False
        self.generalResetCmd: bool = False
        self.generalControl1Value: int = 0
        self.generalControl2Value: int = 0
        self.generalControl3Value: int = 0

        # General Controls - PLC Inputs (simulator outputs) (written by: force or UI in future)
        self.indicator1: bool = False
        self.indicator2: bool = False
        self.indicator3: bool = False
        self.indicator4: bool = False
        self.analog1: int = 0
        self.analog2: int = 0
        self.analog3: int = 0

        # PID Controls - commands to PLC (written by: gui)
        self.pidStartCmd: bool = False
        self.pidStopCmd: bool = False
        self.pidResetCmd: bool = False

        # PID Controls - setpoints (written by: gui or plc)
        self.temperatureSetpoint: float = 50.0  # °C
        self.levelSetpoint: float = 1000.0  # liters

        # PID Valve Controls - commands from GUI (written by: gui)
        self.pidPidValveStartCmd: bool = False
        self.pidPidValveStopCmd: bool = False
        self.pidPidValveResetCmd: bool = False
        self.pidPidValveAutoCmd: bool = True
        self.pidPidValveManCmd: bool = False
        self.pidPidTankValveAItempCmd: bool = True  # Default: Analog temperature
        self.pidPidTankValveDItempCmd: bool = False
        self.pidPidTankValveAIlevelCmd: bool = True  # Default: Analog level
        self.pidPidTankValveDIlevelCmd: bool = False
        # PID Valve Controls - setpoint values (written by: gui)
        self.pidPidTankTempSPValue: int = 0
        self.pidPidTankLevelSPValue: int = 0

    def get_actuator_control_source(self, plc_gui_control: str) -> str:
        """Return the control source for actuators: 'plc' or 'gui'.

        Rules:
        - GUI mode: GUI controls actuators.
        - PLC mode + Auto: PLC controls actuators.
        - PLC mode + Manual: GUI controls actuators (manual override).
        """
        if plc_gui_control == "gui":
            return "gui"

        # PLC mode
        if self.pidPidValveManCmd and not self.pidPidValveAutoCmd:
            return "gui"
        if self.pidPidValveAutoCmd and not self.pidPidValveManCmd:
            return "plc"

        # Ambiguous state: prefer manual override if set, else PLC
        if self.pidPidValveManCmd:
            return "gui"
        return "plc"

    def is_manual_override(self, plc_gui_control: str) -> bool:
        """True when PLC mode is active but GUI should control actuators."""
        return plc_gui_control == "plc" and self.get_actuator_control_source(plc_gui_control) == "gui"

    def saveToFile(self, exportFileName, createFile: bool = False):
        """Save status to a JSON file"""
        print(f"Exporting status to: {exportFileName}")

        data = {}
        for variable in self.importExportVariableList:
            data[variable] = getattr(self, variable)

        with open(exportFileName, "w") as file:
            json.dump(data, file, indent=4)

    def loadFromFile(self, importFileName: str):
        """Read status back from the JSON file"""
        with open(importFileName, "r") as file:
            data = json.load(file)

        for variable in self.importExportVariableList:
            if variable in data:
                current_type = type(getattr(self, variable))
                setattr(self, variable, current_type(data[variable]))
