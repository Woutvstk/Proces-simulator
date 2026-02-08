# Adding a New Simulation - Complete Step-by-Step Guide

This comprehensive guide walks you through creating a new simulation from scratch. By the end, you'll have a fully integrated simulation with GUI visualization, IO mapping, settings panel, and state persistence.

We'll use a practical example: creating a **ConveyorBelt** simulation that models a motor-driven conveyor with load detection and speed control.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step 1: Project Structure](#step-1-project-structure)
3. [Step 2: Configuration Class](#step-2-configuration-class)
4. [Step 3: Status Class](#step-3-status-class)
5. [Step 4: Simulation Class](#step-4-simulation-class)
6. [Step 5: GUI Visualization](#step-5-gui-visualization)
7. [Step 6: Settings Panel](#step-6-settings-panel)
8. [Step 7: IO Signal Definition (XML)](#step-7-io-signal-definition-xml)
9. [Step 8: Framework Integration](#step-8-framework-integration)
10. [Step 9: GUI Integration](#step-9-gui-integration)
11. [Step 10: Testing & Validation](#step-10-testing--validation)
12. [Advanced Topics](#advanced-topics)
13. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, make sure you understand:

- **Python basics**: Classes, inheritance, dictionaries
- **PyQt5 fundamentals**: Widgets, signals, layouts
- **PLC addressing**: I/Q memory, byte/bit notation
- **Process control**: Sensors, actuators, control loops
- **Framework architecture**: Read `ARCHITECTURE.md` first

**Recommended tools:**

- Qt Designer (for GUI layout) ui file is found in the following space: src\gui\media\mainWindowPIDRegelaarSim.ui
- Text editor with Python support (VSC)
- PLC simulator or real PLC for testing

---

## Step 1: Project Structure

Create the directory structure for your simulation:

```
src/simulations/conveyor/
├── __init__.py
├── simulation.py      # Physics engine
├── config.py          # Configuration parameters & IO mapping
├── status.py          # Runtime state variables
├── gui.py             # Visualization widget
└── settingsGui.py     # Configuration panel
```

### Create **init**.py

```python
"""
Conveyor Belt Simulation Package

A motor-driven conveyor belt with:
- Variable speed control (digital or analog)
- Load detection sensor
- Position tracking
- Emergency stop
"""
from .simulation import ConveyorSimulation

__all__ = ['ConveyorSimulation']
```

This makes the simulation importable: `from simulations.conveyor import ConveyorSimulation`

---

## Step 2: Configuration Class

The configuration class defines:

1. IO signal mappings (PLC addresses)
2. Physical parameters (belt length, max speed, etc.)
3. Control parameters (acceleration limits, etc.)

### Create config.py

```python
"""
Conveyor Simulation Configuration

Contains IO mappings and physical parameters for the conveyor simulation.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class configuration:
    """Conveyor simulation configuration"""

    def __init__(self):
        # ===================================================================
        # IO SIGNAL MAPPINGS
        # ===================================================================

        # PLC OUTPUTS (PLC writes, simulation reads) - ACTUATORS
        # Digital outputs
        self.DQMotorRun = {"byte": 0, "bit": 0}          # Motor on/off
        self.DQMotorReverse = {"byte": 0, "bit": 1}      # Reverse direction
        # Analog outputs
        self.AQMotorSpeed = {"byte": 2}                  # Speed 0-100%

        # General Controls - Simulation control (optional)
        self.DIStart = {"byte": 0, "bit": 2}
        self.DIStop = {"byte": 0, "bit": 3}
        self.DIReset = {"byte": 0, "bit": 4}

        # PLC INPUTS (PLC reads, simulation writes) - SENSORS
        # Digital inputs
        self.DILoadDetected = {"byte": 0, "bit": 0}      # Load on belt
        self.DIAtPosition = {"byte": 0, "bit": 1}        # At target position
        self.DIEmergencyStop = {"byte": 0, "bit": 2}     # E-stop triggered
        # Analog inputs
        self.AICurrentSpeed = {"byte": 4}                # Actual speed 0-100%
        self.AIPosition = {"byte": 6}                    # Belt position 0-100%

        # General Controls - Indicators
        self.DQIndicator1 = {"byte": 0, "bit": 5}
        self.DQIndicator2 = {"byte": 0, "bit": 6}

        # ===================================================================
        # PHYSICAL PARAMETERS
        # ===================================================================

        self.beltLength = 10.0               # meters
        self.maxSpeed = 2.0                  # m/s
        self.acceleration = 0.5              # m/s²
        self.deceleration = 0.8              # m/s²
        self.motorInertia = 0.2              # seconds to reach target speed

        # Load simulation
        self.loadWeight = 50.0               # kg (affects acceleration)
        self.emptyBeltWeight = 20.0          # kg

        # ===================================================================
        # CONTROL PARAMETERS
        # ===================================================================

        self.digitalSpeedSlow = 0.5          # m/s when digital mode
        self.digitalSpeedFast = 1.5          # m/s when digital mode

        # ===================================================================
        # SIMULATION SETTINGS
        # ===================================================================

        self.lowestByte = 0                  # PLC memory range
        self.highestByte = 20
        self.simulationInterval = 0.1        # Update interval (seconds)

        # ===================================================================
        # METADATA
        # ===================================================================

        # Mapping of signal names to config attribute names
        self.io_signal_mapping = {}

        # Custom user-defined signal names (attribute_name -> custom_name)
        self.custom_signal_names: dict[str, str] = {}

        # Variables to include in state save/load
        self.importExportVariableList = [
            # Physical parameters
            'beltLength',
            'maxSpeed',
            'acceleration',
            'deceleration',
            'motorInertia',
            'loadWeight',
            'emptyBeltWeight',
            # Control parameters
            'digitalSpeedSlow',
            'digitalSpeedFast',
            # Simulation settings
            'simulationInterval'
        ]

    def load_io_config_from_file(self, file_path: str) -> None:
        """Load IO configuration from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # Load signal mappings
            if 'signals' in config_data:
                for signal in config_data['signals']:
                    signal_name = signal.get('name')
                    if hasattr(self, signal_name):
                        # Update byte/bit mapping
                        byte_val = signal.get('byte', '')
                        bit_val = signal.get('bit', '')

                        if signal.get('type') == 'Bool' and bit_val:
                            setattr(self, signal_name, {
                                "byte": int(byte_val) if byte_val else 0,
                                "bit": int(bit_val) if bit_val else 0
                            })
                        elif signal.get('type') == 'Int':
                            setattr(self, signal_name, {
                                "byte": int(byte_val) if byte_val else 0
                            })

            # Load custom signal names
            if 'custom_signal_names' in config_data:
                if isinstance(config_data['custom_signal_names'], dict):
                    self.custom_signal_names = config_data['custom_signal_names'].copy()
                    logger.info(f"Loaded {len(self.custom_signal_names)} custom signal name(s)")

            logger.info(f"IO configuration loaded from {file_path}")

        except Exception as e:
            logger.error(f"Failed to load IO config: {e}", exc_info=True)

    def printConfigToLog(self) -> None:
        """Print all configuration parameters to log (debug helper)"""
        logger.info("=== Conveyor Configuration ===")
        logger.info(f"Belt Length: {self.beltLength} m")
        logger.info(f"Max Speed: {self.maxSpeed} m/s")
        logger.info(f"Acceleration: {self.acceleration} m/s²")
        logger.info(f"Motor Inertia: {self.motorInertia} s")

        # Print custom signal names if any
        if hasattr(self, "custom_signal_names") and self.custom_signal_names:
            logger.info("=== Custom Signal Names ===")
            for attr, custom_name in self.custom_signal_names.items():
                logger.info(f"  {attr} → '{custom_name}'")
```

**Key points:**

- Digital signals have `byte` and `bit` fields
- Analog signals have only `byte` field (word address)
- Use descriptive parameter names
- Include all parameters in `importExportVariableList` for state persistence
- `custom_signal_names` dict enables user-defined names

---

## Step 3: Status Class

The status class holds runtime variables that change during simulation. Think of it as the "state snapshot" at any moment.

### Create status.py

```python
"""
Conveyor Simulation Status

Runtime state variables for the conveyor simulation.
"""
import logging

logger = logging.getLogger(__name__)


class status:
    """Conveyor simulation runtime status"""

    def __init__(self):
        # ===================================================================
        # ACTUATOR STATES (Read from PLC outputs)
        # ===================================================================

        self.motorRun = False                # Motor on/off command
        self.motorReverse = False            # Reverse direction command
        self.motorSpeedCmd = 0.0             # Commanded speed (0-100%)

        # ===================================================================
        # SENSOR VALUES (Written to PLC inputs)
        # ===================================================================

        self.loadDetected = False            # Load present on belt
        self.atPosition = False              # At target position
        self.emergencyStop = False           # E-stop activated
        self.currentSpeed = 0.0              # Actual belt speed (0-100%)
        self.position = 0.0                  # Belt position (0-100%)

        # ===================================================================
        # INTERNAL STATE (Not directly IO-mapped)
        # ===================================================================

        self.actualSpeedMps = 0.0            # Speed in m/s (internal)
        self.positionMeters = 0.0            # Position in meters (internal)
        self.targetSpeedMps = 0.0            # Target speed for ramp
        self.motorRunning = False            # Internal motor state
        self.direction = 1                   # 1 = forward, -1 = reverse

        # Simulation control
        self.simRunning = False
        self.simPaused = False

        # ===================================================================
        # STATE PERSISTENCE
        # ===================================================================

        # Variables to save/load in state files
        self.importExportVariableList = [
            # Actuators
            'motorRun',
            'motorReverse',
            'motorSpeedCmd',
            # Sensors
            'loadDetected',
            'atPosition',
            'emergencyStop',
            'currentSpeed',
            'position',
            # Internal state
            'actualSpeedMps',
            'positionMeters',
            'targetSpeedMps',
            'motorRunning',
            'direction',
            # Control
            'simRunning',
            'simPaused'
        ]

    def reset(self) -> None:
        """Reset to initial state"""
        # Actuators
        self.motorRun = False
        self.motorReverse = False
        self.motorSpeedCmd = 0.0

        # Sensors
        self.loadDetected = False
        self.atPosition = False
        self.emergencyStop = False
        self.currentSpeed = 0.0
        self.position = 0.0

        # Internal
        self.actualSpeedMps = 0.0
        self.positionMeters = 0.0
        self.targetSpeedMps = 0.0
        self.motorRunning = False
        self.direction = 1

        logger.info("[Conveyor] Status reset to initial state")
```

**Key points:**

- Separate actuator states (from PLC) and sensor values (to PLC)
- Include internal calculation variables
- Include all in `importExportVariableList` for state save/load
- Provide `reset()` method for Reset button

---

## Step 4: Simulation Class

The simulation class contains the physics engine and implements the `SimulationInterface`.

### Create simulation.py

```python
"""
Conveyor Belt Simulation

Physics-based simulation of a motor-driven conveyor belt with load detection
and variable speed control.

External Libraries:
- logging (Python standard library)
"""
import logging
import time
from core.interface import SimulationInterface
from .config import configuration
from .status import status

logger = logging.getLogger(__name__)


class ConveyorSimulation(SimulationInterface):
    """Conveyor belt physics simulation"""

    def __init__(self, instance_name: str = "conveyor0"):
        """
        Initialize conveyor simulation

        Args:
            instance_name: Unique identifier for this simulation instance
        """
        self.instance_name = instance_name
        self.config = configuration()
        self.status = status()
        self._last_update_time = time.time()

        logger.info(f"[{self.instance_name}] Conveyor simulation created")

    def start(self) -> None:
        """Start the simulation"""
        self.status.simRunning = True
        self.status.simPaused = False
        self._last_update_time = time.time()
        logger.info(f"[{self.instance_name}] Simulation started")

    def stop(self) -> None:
        """Pause the simulation"""
        self.status.simPaused = True
        logger.info(f"[{self.instance_name}] Simulation paused")

    def reset(self) -> None:
        """Reset simulation to initial state"""
        self.status.reset()
        self._last_update_time = time.time()
        logger.info(f"[{self.instance_name}] Simulation reset")

    def update(self, dt: float, status_obj: status) -> None:
        """
        Main simulation update - called every cycle

        Args:
            dt: Time delta since last update (seconds)
            status_obj: Status object (same as self.status)
        """
        if not self.status.simRunning or self.status.simPaused:
            return

        # Use dt parameter (more accurate than internal timing)
        # But cap it to prevent huge jumps after pause
        dt = min(dt, 0.5)

        # ================================================================
        # READ ACTUATORS (from PLC outputs)
        # ================================================================

        motor_on = self.status.motorRun
        reverse_cmd = self.status.motorReverse
        speed_cmd_pct = self.status.motorSpeedCmd  # 0-100%

        # ================================================================
        # PROCESS CONTROL LOGIC
        # ================================================================

        # Update direction
        self.status.direction = -1 if reverse_cmd else 1

        # Calculate target speed
        if motor_on and not self.status.emergencyStop:
            # Convert percentage to m/s
            target_speed = (speed_cmd_pct / 100.0) * self.config.maxSpeed
            # Clamp to valid range
            target_speed = max(0.0, min(target_speed, self.config.maxSpeed))
        else:
            target_speed = 0.0

        self.status.targetSpeedMps = target_speed

        # ================================================================
        # PHYSICS SIMULATION
        # ================================================================

        # Apply acceleration/deceleration with inertia
        speed_diff = target_speed - self.status.actualSpeedMps

        if abs(speed_diff) > 0.01:
            # Calculate acceleration rate
            if speed_diff > 0:
                # Accelerating
                max_change = self.config.acceleration * dt
                # Load affects acceleration
                total_weight = self.config.emptyBeltWeight
                if self.status.loadDetected:
                    total_weight += self.config.loadWeight
                accel_factor = self.config.emptyBeltWeight / total_weight
                max_change *= accel_factor
            else:
                # Decelerating
                max_change = self.config.deceleration * dt

            # Apply speed change with limit
            if abs(speed_diff) < max_change:
                self.status.actualSpeedMps = target_speed
            else:
                self.status.actualSpeedMps += max_change if speed_diff > 0 else -max_change

        # Update position
        displacement = self.status.actualSpeedMps * self.status.direction * dt
        self.status.positionMeters += displacement

        # Wrap position around belt length
        while self.status.positionMeters >= self.config.beltLength:
            self.status.positionMeters -= self.config.beltLength
        while self.status.positionMeters < 0:
            self.status.positionMeters += self.config.beltLength

        # Check if at target position (example: position 0 is "home")
        position_tolerance = 0.1  # meters
        self.status.atPosition = abs(self.status.positionMeters) < position_tolerance

        # Update motor running state
        self.status.motorRunning = motor_on and (self.status.actualSpeedMps > 0.01)

        # ================================================================
        # WRITE SENSORS (to PLC inputs)
        # ================================================================

        # Convert internal values to PLC format
        self.status.currentSpeed = (self.status.actualSpeedMps / self.config.maxSpeed) * 100.0
        self.status.position = (self.status.positionMeters / self.config.beltLength) * 100.0

        # Clamp sensor values to valid ranges
        self.status.currentSpeed = max(0.0, min(100.0, self.status.currentSpeed))
        self.status.position = max(0.0, min(100.0, self.status.position))

    def get_config(self) -> configuration:
        """Return configuration object"""
        return self.config

    def set_config(self, config: configuration) -> None:
        """Update configuration"""
        self.config = config
        logger.info(f"[{self.instance_name}] Configuration updated")

    def get_status(self) -> status:
        """Return status object"""
        return self.status

    def set_status(self, status_obj: status) -> None:
        """Update status"""
        self.status = status_obj
        logger.info(f"[{self.instance_name}] Status updated")
```

**Key points:**

- Inherit from `SimulationInterface`
- Implement all required methods (start, stop, reset, update, getters/setters)
- Physics in `update()` method - read actuators, calculate, write sensors
- Use `dt` parameter for time-based calculations
- Cap dt to prevent huge jumps
- Add realistic physics (inertia, acceleration limits, load effects)
- Log important events

---

## Step 5: GUI Visualization

The GUI visualization widget displays the simulation state graphically.

### Create gui.py

```python
"""
Conveyor Visualization Widget

Qt widget that displays the conveyor belt simulation state with animated graphics.

External Libraries:
- PyQt5 (GPL v3) - GUI framework
"""
import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGridLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette, QColor

logger = logging.getLogger(__name__)


class ConveyorVisualizationWidget(QWidget):
    """Visual representation of conveyor belt state"""

    def __init__(self, config, status, parent=None):
        super().__init__(parent)
        self.config = config
        self.status = status

        self.initUI()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)  # 10 Hz refresh

    def initUI(self):
        """Initialize user interface"""
        layout = QVBoxLayout()

        # Title
        title = QLabel("Conveyor Belt Simulation")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Grid for status display
        grid = QGridLayout()

        # Motor status
        grid.addWidget(QLabel("Motor Status:"), 0, 0)
        self.motor_status_label = QLabel("STOPPED")
        self.motor_status_label.setStyleSheet("font-weight: bold; color: red;")
        grid.addWidget(self.motor_status_label, 0, 1)

        # Direction
        grid.addWidget(QLabel("Direction:"), 1, 0)
        self.direction_label = QLabel("FORWARD")
        grid.addWidget(self.direction_label, 1, 1)

        # Current speed
        grid.addWidget(QLabel("Current Speed:"), 2, 0)
        self.speed_label = QLabel("0.00 m/s (0%)")
        grid.addWidget(self.speed_label, 2, 1)

        # Speed progress bar
        self.speed_bar = QProgressBar()
        self.speed_bar.setRange(0, 100)
        self.speed_bar.setValue(0)
        grid.addWidget(self.speed_bar, 3, 0, 1, 2)

        # Position
        grid.addWidget(QLabel("Position:"), 4, 0)
        self.position_label = QLabel("0.00 m (0%)")
        grid.addWidget(self.position_label, 4, 1)

        # Position progress bar
        self.position_bar = QProgressBar()
        self.position_bar.setRange(0, 100)
        self.position_bar.setValue(0)
        grid.addWidget(self.position_bar, 5, 0, 1, 2)

        # Load detected
        grid.addWidget(QLabel("Load Detected:"), 6, 0)
        self.load_label = QLabel("NO")
        self.load_label.setStyleSheet("color: gray;")
        grid.addWidget(self.load_label, 6, 1)

        # At position
        grid.addWidget(QLabel("At Target Position:"), 7, 0)
        self.at_position_label = QLabel("NO")
        self.at_position_label.setStyleSheet("color: gray;")
        grid.addWidget(self.at_position_label, 7, 1)

        # Emergency stop
        grid.addWidget(QLabel("Emergency Stop:"), 8, 0)
        self.estop_label = QLabel("NO")
        self.estop_label.setStyleSheet("color: green;")
        grid.addWidget(self.estop_label, 8, 1)

        layout.addLayout(grid)
        layout.addStretch()

        self.setLayout(layout)

    def update_display(self):
        """Update display with current simulation state"""
        try:
            # Motor status
            if self.status.motorRunning:
                self.motor_status_label.setText("RUNNING")
                self.motor_status_label.setStyleSheet("font-weight: bold; color: green;")
            elif self.status.motorRun:
                self.motor_status_label.setText("STARTING")
                self.motor_status_label.setStyleSheet("font-weight: bold; color: orange;")
            else:
                self.motor_status_label.setText("STOPPED")
                self.motor_status_label.setStyleSheet("font-weight: bold; color: red;")

            # Direction
            if self.status.direction < 0:
                self.direction_label.setText("REVERSE")
                self.direction_label.setStyleSheet("color: orange;")
            else:
                self.direction_label.setText("FORWARD")
                self.direction_label.setStyleSheet("color: blue;")

            # Speed
            speed_mps = self.status.actualSpeedMps
            speed_pct = self.status.currentSpeed
            self.speed_label.setText(f"{speed_mps:.2f} m/s ({speed_pct:.1f}%)")
            self.speed_bar.setValue(int(speed_pct))

            # Position
            pos_m = self.status.positionMeters
            pos_pct = self.status.position
            self.position_label.setText(f"{pos_m:.2f} m ({pos_pct:.1f}%)")
            self.position_bar.setValue(int(pos_pct))

            # Load detected
            if self.status.loadDetected:
                self.load_label.setText("YES")
                self.load_label.setStyleSheet("font-weight: bold; color: red;")
            else:
                self.load_label.setText("NO")
                self.load_label.setStyleSheet("color: gray;")

            # At position
            if self.status.atPosition:
                self.at_position_label.setText("YES")
                self.at_position_label.setStyleSheet("font-weight: bold; color: green;")
            else:
                self.at_position_label.setText("NO")
                self.at_position_label.setStyleSheet("color: gray;")

            # Emergency stop
            if self.status.emergencyStop:
                self.estop_label.setText("ACTIVE")
                self.estop_label.setStyleSheet("font-weight: bold; color: red;")
            else:
                self.estop_label.setText("NO")
                self.estop_label.setStyleSheet("color: green;")

        except Exception as e:
            logger.error(f"Error updating conveyor display: {e}")
```

**Key points:**

- Inherit from QWidget
- Store references to config and status
- Use QTimer for periodic updates (10-20 Hz is good)
- Update labels/progress bars based on status values
- Use color coding for visual feedback
- Handle exceptions in update method

**For advanced graphics:** Use QGraphicsView with QGraphicsScene for animated SVG or custom drawings. See PIDtankValve/gui.py for SVG example.

---

## Step 6: Settings Panel

The settings panel allows users to configure simulation parameters at runtime.

### Create settingsGui.py

```python
"""
Conveyor Settings Panel

Qt widget for editing conveyor simulation configuration parameters.

External Libraries:
- PyQt5 (GPL v3) - GUI framework
"""
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QDoubleSpinBox,
                              QGroupBox, QLabel, QPushButton)
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)


class ConveyorSettingsWidget(QWidget):
    """Settings panel for conveyor simulation"""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

        self.initUI()
        self.load_values_from_config()

    def initUI(self):
        """Initialize user interface"""
        layout = QVBoxLayout()

        # Title
        title = QLabel("Conveyor Configuration")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # ====== Physical Parameters ======
        physical_group = QGroupBox("Physical Parameters")
        physical_layout = QFormLayout()

        self.belt_length_spin = QDoubleSpinBox()
        self.belt_length_spin.setRange(1.0, 100.0)
        self.belt_length_spin.setSingleStep(0.5)
        self.belt_length_spin.setSuffix(" m")
        self.belt_length_spin.valueChanged.connect(self.on_value_changed)
        physical_layout.addRow("Belt Length:", self.belt_length_spin)

        self.max_speed_spin = QDoubleSpinBox()
        self.max_speed_spin.setRange(0.1, 10.0)
        self.max_speed_spin.setSingleStep(0.1)
        self.max_speed_spin.setSuffix(" m/s")
        self.max_speed_spin.valueChanged.connect(self.on_value_changed)
        physical_layout.addRow("Max Speed:", self.max_speed_spin)

        self.acceleration_spin = QDoubleSpinBox()
        self.acceleration_spin.setRange(0.1, 5.0)
        self.acceleration_spin.setSingleStep(0.1)
        self.acceleration_spin.setSuffix(" m/s²")
        self.acceleration_spin.valueChanged.connect(self.on_value_changed)
        physical_layout.addRow("Acceleration:", self.acceleration_spin)

        self.deceleration_spin = QDoubleSpinBox()
        self.deceleration_spin.setRange(0.1, 5.0)
        self.deceleration_spin.setSingleStep(0.1)
        self.deceleration_spin.setSuffix(" m/s²")
        self.deceleration_spin.valueChanged.connect(self.on_value_changed)
        physical_layout.addRow("Deceleration:", self.deceleration_spin)

        self.inertia_spin = QDoubleSpinBox()
        self.inertia_spin.setRange(0.01, 2.0)
        self.inertia_spin.setSingleStep(0.05)
        self.inertia_spin.setSuffix(" s")
        self.inertia_spin.valueChanged.connect(self.on_value_changed)
        physical_layout.addRow("Motor Inertia:", self.inertia_spin)

        physical_group.setLayout(physical_layout)
        layout.addWidget(physical_group)

        # ====== Load Parameters ======
        load_group = QGroupBox("Load Parameters")
        load_layout = QFormLayout()

        self.load_weight_spin = QDoubleSpinBox()
        self.load_weight_spin.setRange(0.0, 500.0)
        self.load_weight_spin.setSingleStep(10.0)
        self.load_weight_spin.setSuffix(" kg")
        self.load_weight_spin.valueChanged.connect(self.on_value_changed)
        load_layout.addRow("Load Weight:", self.load_weight_spin)

        self.empty_weight_spin = QDoubleSpinBox()
        self.empty_weight_spin.setRange(1.0, 200.0)
        self.empty_weight_spin.setSingleStep(5.0)
        self.empty_weight_spin.setSuffix(" kg")
        self.empty_weight_spin.valueChanged.connect(self.on_value_changed)
        load_layout.addRow("Empty Belt Weight:", self.empty_weight_spin)

        load_group.setLayout(load_layout)
        layout.addWidget(load_group)

        # ====== Control Parameters ======
        control_group = QGroupBox("Control Parameters")
        control_layout = QFormLayout()

        self.slow_speed_spin = QDoubleSpinBox()
        self.slow_speed_spin.setRange(0.1, 5.0)
        self.slow_speed_spin.setSingleStep(0.1)
        self.slow_speed_spin.setSuffix(" m/s")
        self.slow_speed_spin.valueChanged.connect(self.on_value_changed)
        control_layout.addRow("Digital Slow Speed:", self.slow_speed_spin)

        self.fast_speed_spin = QDoubleSpinBox()
        self.fast_speed_spin.setRange(0.1, 10.0)
        self.fast_speed_spin.setSingleStep(0.1)
        self.fast_speed_spin.setSuffix(" m/s")
        self.fast_speed_spin.valueChanged.connect(self.on_value_changed)
        control_layout.addRow("Digital Fast Speed:", self.fast_speed_spin)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # ====== Actions ======
        button_layout = QVBoxLayout()

        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_button)

        layout.addLayout(button_layout)
        layout.addStretch()

        self.setLayout(layout)

    def load_values_from_config(self):
        """Load current values from configuration"""
        self.belt_length_spin.setValue(self.config.beltLength)
        self.max_speed_spin.setValue(self.config.maxSpeed)
        self.acceleration_spin.setValue(self.config.acceleration)
        self.deceleration_spin.setValue(self.config.deceleration)
        self.inertia_spin.setValue(self.config.motorInertia)
        self.load_weight_spin.setValue(self.config.loadWeight)
        self.empty_weight_spin.setValue(self.config.emptyBeltWeight)
        self.slow_speed_spin.setValue(self.config.digitalSpeedSlow)
        self.fast_speed_spin.setValue(self.config.digitalSpeedFast)

    def on_value_changed(self):
        """Handle value changes - write to config immediately"""
        self.config.beltLength = self.belt_length_spin.value()
        self.config.maxSpeed = self.max_speed_spin.value()
        self.config.acceleration = self.acceleration_spin.value()
        self.config.deceleration = self.deceleration_spin.value()
        self.config.motorInertia = self.inertia_spin.value()
        self.config.loadWeight = self.load_weight_spin.value()
        self.config.emptyBeltWeight = self.empty_weight_spin.value()
        self.config.digitalSpeedSlow = self.slow_speed_spin.value()
        self.config.digitalSpeedFast = self.fast_speed_spin.value()

    def reset_to_defaults(self):
        """Reset all parameters to default values"""
        default_config = type(self.config)()  # Create new instance with defaults
        self.config.beltLength = default_config.beltLength
        self.config.maxSpeed = default_config.maxSpeed
        self.config.acceleration = default_config.acceleration
        self.config.deceleration = default_config.deceleration
        self.config.motorInertia = default_config.motorInertia
        self.config.loadWeight = default_config.loadWeight
        self.config.emptyBeltWeight = default_config.emptyBeltWeight
        self.config.digitalSpeedSlow = default_config.digitalSpeedSlow
        self.config.digitalSpeedFast = default_config.digitalSpeedFast

        self.load_values_from_config()
        logger.info("[Conveyor] Configuration reset to defaults")
```

**Key points:**

- Group related parameters with QGroupBox
- Use appropriate spin boxes with ranges, steps, and suffixes
- Write to config immediately on value change (real-time update)
- Provide reset to defaults button
- Use clear labels and tooltips

---

## Step 7: IO Signal Definition (XML)

Create XML file that defines all signals for drag-drop IO mapping.

### Create IO/IO_treeList_conveyor.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<root>
    <!-- General Controls (reusable across simulations) -->
    <category name="GeneralControls" description="Common simulation controls">
        <subcategory name="Digital" description="Digital control signals">
            <signal name="DIStart" type="Bool" range="0-1" io_prefix="I"
                    description="Start simulation"/>
            <signal name="DIStop" type="Bool" range="0-1" io_prefix="I"
                    description="Stop simulation"/>
            <signal name="DIReset" type="Bool" range="0-1" io_prefix="I"
                    description="Reset simulation"/>
        </subcategory>
    </category>

    <!-- Conveyor-specific signals -->
    <category name="ConveyorSim" description="Conveyor belt simulation signals">
        <subcategory name="Outputs" description="Actuator outputs (PLC → Simulation)">
            <subcategory name="Digital" description="Digital actuators">
                <signal name="DQMotorRun" type="Bool" range="0-1" io_prefix="Q"
                        description="Motor run command (ON/OFF)"/>
                <signal name="DQMotorReverse" type="Bool" range="0-1" io_prefix="Q"
                        description="Motor reverse direction"/>
            </subcategory>
            <subcategory name="Analog" description="Analog actuators">
                <signal name="AQMotorSpeed" type="Int" range="0-27648" io_prefix="Q"
                        description="Motor speed command 0-100%"/>
            </subcategory>
        </subcategory>

        <subcategory name="Inputs" description="Sensor inputs (Simulation → PLC)">
            <subcategory name="Digital" description="Digital sensors">
                <signal name="DILoadDetected" type="Bool" range="0-1" io_prefix="I"
                        description="Load present on belt"/>
                <signal name="DIAtPosition" type="Bool" range="0-1" io_prefix="I"
                        description="Belt at target position"/>
                <signal name="DIEmergencyStop" type="Bool" range="0-1" io_prefix="I"
                        description="Emergency stop activated"/>
            </subcategory>
            <subcategory name="Analog" description="Analog sensors">
                <signal name="AICurrentSpeed" type="Int" range="0-27648" io_prefix="I"
                        description="Actual belt speed 0-100%"/>
                <signal name="AIPosition" type="Int" range="0-27648" io_prefix="I"
                        description="Belt position 0-100%"/>
            </subcategory>
        </subcategory>
    </category>

    <!-- Indicators (optional) -->
    <category name="Indicators" description="Status indicators">
        <subcategory name="Digital" description="Digital indicators">
            <signal name="DQIndicator1" type="Bool" range="0-1" io_prefix="Q"
                    description="General indicator 1"/>
            <signal name="DQIndicator2" type="Bool" range="0-1" io_prefix="Q"
                    description="General indicator 2"/>
        </subcategory>
    </category>
</root>
```

**Key points:**

- Use hierarchical structure (category → subcategory → signal)
- Signal names MUST match config.py attribute names exactly
- Use descriptive category/subcategory names
- Separate Outputs (Q) and Inputs (I) clearly
- Include good descriptions (appear in table tooltips)
- Keep GeneralControls consistent across simulations

---

## Step 8: Framework Integration

Register the simulation with the framework so it can be loaded and managed.

### Edit main.py

Add these changes to `main.py`:

```python
# At the top, add import
from simulations.conveyor.simulation import ConveyorSimulation

# In the initialization section (around line 40), add registration:
# Register available simulations
simulationManager.register_simulation("PIDtankValve", PIDTankSimulation)
simulationManager.register_simulation("conveyor", ConveyorSimulation)  # ADD THIS
logger.info("Registered simulations: " +
            str(simulationManager.get_registered_simulations()))

# Load the default simulation (keep existing or change to conveyor):
if simulationManager.load_simulation("conveyor", "conveyorSim0"):
    logger.info("Default simulation loaded successfully")
else:
    logger.error("Failed to load default simulation")
    sys.exit(1)
```

**Key points:**

- Use unique simulation name ("conveyor")
- Use consistent instance ID pattern ("conveyorSim0")
- Register BEFORE loading
- Keep existing simulations registered (multi-simulation support)

---

## Step 9: GUI Integration

Add navigation button and wire up visualization/settings panels.

### Step 9.1: Add Navigation Button in Qt Designer

1. Open `gui/media/mainWindowPIDRegelaarSim.ui` in Qt Designer
2. Find the left navigation panel (vertical layout with buttons)
3. Add new QPushButton below existing simulation buttons
4. Set object name: `pushButton_conveyor`
5. Set text: `Conveyor Belt`
6. Set icon if desired
7. Save UI file

### Step 9.2: Wire Up in mainGui.py

Add to `mainGui.py`:

```python
# In the SimPageMixin class, add button connection:
def setup_sim_page_connections(self):
    """Connect simulation navigation buttons"""
    # Existing connections...
    self.pushButton_tanksim.clicked.connect(lambda: self.switch_simulation('PIDtankValve'))

    # Add conveyor button
    if hasattr(self, 'pushButton_conveyor'):
        self.pushButton_conveyor.clicked.connect(lambda: self.switch_simulation('conveyor'))

# In switch_simulation method, add visualization case:
def switch_simulation(self, sim_name: str):
    """Switch to different simulation"""
    try:
        # Stop current simulation
        self.simulationManager.stop_simulation()

        # Load new simulation
        if sim_name == 'PIDtankValve':
            success = self.simulationManager.load_simulation('PIDtankValve', 'tankSimSimulation0')
        elif sim_name == 'conveyor':
            success = self.simulationManager.load_simulation('conveyor', 'conveyorSim0')
        else:
            logger.error(f"Unknown simulation: {sim_name}")
            return

        if not success:
            logger.error(f"Failed to load simulation: {sim_name}")
            return

        # Update references
        active_sim = self.simulationManager.get_active_simulation()
        self.tanksim_config = active_sim.config
        self.set_simulation_status(active_sim.status)

        # Switch visualization widget
        if sim_name == 'PIDtankValve':
            from simulations.PIDtankValve.gui import TankVisualizationWidget
            self.tankSimWidget = TankVisualizationWidget(
                self.tanksim_config,
                active_sim.status,
                self
            )
            # Add to stacked widget
            ...
        elif sim_name == 'conveyor':
            from simulations.conveyor.gui import ConveyorVisualizationWidget
            self.conveyorWidget = ConveyorVisualizationWidget(
                self.tanksim_config,
                active_sim.status,
                self
            )
            # Add to stacked widget (same pattern as tank)
            ...

        # Reload IO tree for new simulation
        self.load_io_tree()

        logger.info(f"Switched to simulation: {sim_name}")

    except Exception as e:
        logger.error(f"Error switching simulation: {e}", exc_info=True)
```

### Step 9.3: Add Settings Panel

In `mainGui.py`, add settings widget initialization:

```python
# In __init__ method, create settings widget:
from simulations.conveyor.settingsGui import ConveyorSettingsWidget

self.conveyorSettingsWidget = ConveyorSettingsWidget(
    self.tanksim_config,  # Will be conveyor config when conveyor active
    self
)

# Add to settings stacked widget or tab widget
```

**Key points:**

- Navigation button object name must match in code
- Create visualization widget when switching simulations
- Add to appropriate stacked widget or layout
- Reload IO tree after simulation switch
- Handle errors gracefully

---

## Step 10: Testing & Validation

Test your simulation thoroughly before declaring it complete.

### Testing Checklist

**[ ] Simulation Physics:**

- [ ] Motor starts/stops correctly
- [ ] Speed ramps up/down with acceleration limits
- [ ] Direction changes work
- [ ] Position updates correctly
- [ ] Load affects acceleration
- [ ] Emergency stop works

**[ ] IO Mapping:**

- [ ] Signals appear in tree view
- [ ] Drag-drop to table works
- [ ] Addresses can be edited
- [ ] Auto-assign works
- [ ] No address conflicts detected incorrectly
- [ ] Custom signal names work
- [ ] Force values override correctly

**[ ] GUI:**

- [ ] Visualization updates in real-time
- [ ] Labels show correct values
- [ ] Progress bars animate
- [ ] Colors indicate states correctly
- [ ] Settings panel saves values
- [ ] Navigation button switches correctly

**[ ] State Persistence:**

- [ ] Save state includes all config parameters
- [ ] Save state includes all status values
- [ ] Load state restores configuration
- [ ] Load state restores simulation state
- [ ] Custom signal names persist
- [ ] IO mapping persists

**[ ] PLC Communication:**

- [ ] Connect to PLC successful
- [ ] Actuator outputs read correctly
- [ ] Sensor inputs written correctly
- [ ] Manual mode overrides work
- [ ] Force values work
- [ ] Disconnection handled gracefully

### Test Procedure

1. **Start Application**
   - Verify conveyor simulation loads
   - Check console for errors

2. **Map IO Signals**
   - Drag all signals to table
   - Use auto-assign
   - Save configuration
   - Restart application
   - Verify IO config loads correctly

3. **Test GUI Mode**
   - Use manual controls to run motor
   - Verify visualization updates
   - Test speed control
   - Test direction change
   - Test emergency stop

4. **Test PLC Connection**
   - Connect to PLC or PLCSim
   - Write simple PLC program that toggles outputs
   - Verify simulation responds to PLC commands
   - Verify PLC receives sensor values
   - Test disconnect/reconnect

5. **Test State Save/Load**
   - Run simulation to specific state
   - Save state file
   - Change some parameters
   - Load state file
   - Verify everything restored correctly

6. **Test Edge Cases**
   - Very fast speed changes
   - Rapid start/stop
   - Load state while simulation running
   - Switch simulations and back
   - Force all signals at once

---

## Advanced Topics

### Custom Graphics with SVG

For more sophisticated visualization, use SVG graphics:

```python
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt5.QtCore import QByteArray

class ConveyorVisualizationWidget(QWidget):
    def __init__(self, config, status, parent=None):
        super().__init__(parent)
        self.config = config
        self.status = status

        # Load SVG
        self.svg_data = self.load_svg()
        self.renderer = QSvgRenderer(QByteArray(self.svg_data.encode()))

        # Create graphics view
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)

        # ... render SVG elements

    def update_display(self):
        # Modify SVG elements based on status
        # Example: move belt graphic, color motor, etc.
        pass
```

### Multi-Instance Support

To run multiple instances of same simulation:

```python
# Register multiple instances
simulationManager.load_simulation("conveyor", "conveyor1")
simulationManager.load_simulation("conveyor", "conveyor2")

# Each has independent config/status
sim1 = simulationManager.get_simulation("conveyor1")
sim2 = simulationManager.get_simulation("conveyor2")
```

Current framework supports single active simulation, but architecture allows extension.

### Advanced Physics

Add more realistic physics:

```python
# Friction losses
friction_force = 0.1 * self.status.actualSpeedMps * total_weight
deceleration_from_friction = friction_force / total_weight

# Mechanical efficiency
motor_efficiency = 0.85
actual_power = commanded_power * motor_efficiency

# Belt slip
if acceleration_too_high:
    self.status.belt_slipping = True
    actual_acceleration *= 0.5
```

### Communication with External Systems

Read from/write to external sources:

```python
# Read from file
with open('load_schedule.json') as f:
    schedule = json.load(f)
    self.status.loadDetected = schedule['current_load']

# Write to database
import sqlite3
conn = sqlite3.connect('simulation_log.db')
conn.execute('INSERT INTO speed_log VALUES (?, ?)',
             (time.time(), self.status.currentSpeed))
conn.commit()

# Network communication
import socket
sock = socket.socket()
sock.sendto(f"SPEED:{self.status.currentSpeed}".encode(), ('localhost', 5000))
```

---

## Troubleshooting

### Simulation not appearing in navigation

**Check:**

- Simulation registered in main.py
- Import statement correct
- Button connected to switch_simulation method
- Button object name matches code

### IO signals not in tree

**Check:**

- XML file named correctly (IO_treeList_conveyor.xml)
- XML file in IO/ directory
- XML syntax valid (use XML validator)
- load_io_tree() loads correct file for simulation

### Signals not updating during runtime

**Check:**

- PLC connected (check connection LED)
- Addresses mapped correctly
- No address conflicts
- Byte range covers all signals (lowestByte/highestByte)
- IO handler updateIO() called every cycle
- Protocol getters/setters working

### Custom names not persisting

**Check:**

- save_configuration() includes custom_signal_names
- load_table_from_io_configuration_file() loads custom names
- Table clear saves/restores custom names
- Attribute names used as keys (not signal names)

### State load doesn't restore simulation

**Check:**

- Simulation name in state file matches registered name
- importExportVariableList includes all important variables
- Serialization/deserialization handles all data types
- GUI sync after load updates all widgets

### Performance issues

**Check:**

- Update interval not too small (min 20ms for PLCSim)
- Visualization update rate reasonable (10-20 Hz max)
- No expensive operations in update() method
- Logging not too verbose (use DEBUG level sparingly)

---

## Summary

You've created a complete simulation from scratch! Here's what we covered:

1. Project structure with 6 core files
2. Configuration class with IO mappings and parameters
3. Status class with runtime state variables
4. Simulation class with physics engine
5. GUI visualization widget with real-time display
6. Settings panel for parameter configuration
7. XML signal definition for IO mapping
8. Framework integration (registration)
9. GUI integration (navigation + widgets)
10. Testing and validation

**Your simulation now has:**

- Full PLC communication support (all protocols)
- IO mapping via drag-and-drop
- Custom signal names
- State save/load
- Manual mode support
- Force value overrides
- Real-time visualization
- Parameter configuration
- Multi-simulation switching

**Next steps:**

- Refine physics model
- Add advanced visualization (SVG, animations)
- Create PLC program to control simulation
- Add logging and data export
- Implement additional sensors/actuators
- Test with real PLC hardware

---

**Document Version:** 1.0  
**Last Updated:** February 2026  
**Status:** Complete Guide - Ready for Development

**Questions or Issues?** Check ARCHITECTURE.md and IO_FLOW.txt for deeper understanding of the framework.
