# Project Restructuring - Industrial Simulation Framework

## Overview

This document describes the modular architecture implemented for the Industrial Simulation Framework. The application manages multiple simulations (PLC tank controls, conveyors, etc.) with different protocols (Logo S7, PLC S7, PLCSimAPI) and provides a GUI interface for monitoring and control.

---

## Data Flow Overview (For First-Time Readers)

This section explains how data flows through the application for newcomers to the codebase.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                          │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────────┐  │
│  │   Sidebar     │  │  Sim Controls │  │   I/O Config       │  │
│  │   Navigation  │  │  (Buttons,    │  │   (Tree/Table)     │  │
│  │               │  │   Sliders)    │  │                    │  │
│  └───────┬───────┘  └───────┬───────┘  └─────────┬──────────┘  │
│          │                  │                     │              │
│          └──────────────────┴─────────────────────┘              │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │    mainGui.py      │
                    │  (Main Window)     │
                    │  - Page Mixins     │
                    │  - Update Timer    │
                    └─────────┬──────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌───────▼──────────┐
│ configuration  │   │ SimulationMgr   │   │ ProtocolManager  │
│ (Settings)     │   │ (Active Sim)    │   │ (PLC Connect)    │
└───────┬────────┘   └────────┬────────┘   └───────┬──────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │    IOHandler       │
                    │  (Data Exchange)   │
                    └─────────┬──────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌───────▼──────────┐
│  GUI Controls  │   │   Simulation    │   │   PLC Device     │
│  (User Input)  │◄──│   Engine        │◄──│  (S7/Logo/API)   │
│                │   │  (Physics/Logic)│   │                  │
└────────────────┘   └─────────────────┘   └──────────────────┘
```

### Data Flow Sequence

1. **User Input** → User interacts with GUI (clicks Start, adjusts slider)
   - GUI widgets (buttons, sliders) trigger signal handlers
   - Signal handlers update `tanksim_status` variables
   
2. **GUI → Status** → Updates are written to status object
   - Example: `tanksim_status.generalStartCmd = True`
   - Example: `tanksim_status.generalControl1Value = slider_value`

3. **Status → I/O Handler** → IOHandler reads status values
   - In GUI mode: GUI controls are treated as simulation inputs
   - In PLC mode: PLC outputs override GUI controls
   
4. **I/O Handler ↔ PLC** → Bidirectional communication
   - `IOHandler.updateIO()` called in main loop
   - Reads PLC outputs → writes to status (PLC controls simulation)
   - Reads status → writes to PLC inputs (simulation feeds back to PLC)
   
5. **Simulation Engine** → Physics/logic calculations
   - `simulation.update(dt)` processes one time step
   - Reads inputs from status (valve positions, heater power)
   - Calculates new state (liquid level, temperature)
   - Writes results back to status
   
6. **Display Update** → GUI reflects current state
   - Main timer (`update_all_values()`) runs every 100ms
   - Reads status values and updates all displays
   - Tank visualization, I/O table, indicators, etc.

### Control Modes

The application supports two control modes via `configuration.plcGuiControl`:

**GUI Mode (`"gui"`)**:
- User controls simulation directly via GUI widgets
- GUI sliders/buttons → `tanksim_status` → Simulation
- PLC receives simulation outputs as inputs (monitoring only)
- Flow: `GUI → Status → Simulation → Status → PLC`

**PLC Mode (`"plc"`)**:
- PLC controls the simulation
- PLC outputs → `tanksim_status` → Simulation
- GUI displays reflect PLC control (read-only mode)
- Flow: `PLC → Status → Simulation → Status → GUI`

### Key Data Structures

**`configuration`** (Global App Settings):
- `plcGuiControl`: Control mode ("gui" or "plc")
- `plcProtocol`: Selected protocol ("PLC S7", "Logo S7", etc.)
- `plcIpAdress`: PLC IP address
- `tryConnect`: Connection request flag

**`tanksim_config`** (Simulation Parameters):
- `tankVolume`: Tank capacity in liters
- `valveInMaxFlow`: Max inlet flow rate
- `valveOutMaxFlow`: Max outlet flow rate
- `heaterPower`: Heater power in watts
- Static configuration that rarely changes

**`tanksim_status`** (Runtime Values):
- `liquidVolume`: Current liquid level
- `liquidTemperature`: Current temperature
- `valveInOpenFraction`: Inlet valve position (0.0-1.0)
- `valveOutOpenFraction`: Outlet valve position (0.0-1.0)
- `heaterPowerFraction`: Heater power fraction (0.0-1.0)
- `simRunning`: Is simulation active?
- `generalStartCmd`, `generalStopCmd`, `generalResetCmd`: Control commands
- `generalControl1Value`, `generalControl2Value`, `generalControl3Value`: Analog setpoints
- Dynamic values that change continuously

### Example: Start Button Press Flow

```
1. User clicks "Start" button in General Controls dock
   ↓
2. Signal handler: generalControls._on_start_clicked()
   ↓
3. Updates status: tanksim_status.generalStartCmd = True
   ↓
4. Main loop iteration:
   a. IOHandler.updateIO() transfers generalStartCmd to PLC input
   b. Simulation.update(dt) sees start command, sets simRunning = True
   c. Simulation begins physics calculations
   ↓
5. GUI update timer (100ms):
   a. Reads tanksim_status.simRunning
   b. Updates status indicator (LED turns green)
   c. Updates tank visualization
   d. Updates I/O table display
```

---

### Directory Structure

````
/src/
├── main.py                      # architecture entry point
├── requirements.txt
├── core/                        # Core module - Central configuration and managers
│   ├── __init__.py
│   ├── configuration.py         # Main config with Save/Load functionality
│   ├── interface.py             # Abstract base class for simulations
│   ├── simulationManager.py     # Manages simulation instances
│   └── protocolManager.py       # Protocol activation and lifecycle
├── IO/                          # IO module - All input/output operations
│   ├── __init__.py
│   ├── handler.py               # Generic IO handler (simulation-agnostic)
│   ├── IO_treeList_*.xml        # Per-simulation IO trees (PIDtankValve, conveyor)
│   ├── IO_configuration.json    # IO configuration data
│   └── protocols/               # Communication protocols
│       ├── __init__.py
│       ├── logoS7.py            # Logo S7 protocol
│       ├── plcS7.py             # PLC S7 protocol
│       ├── PLCSimAPI/           # PLCSimAPI protocols
│       │    ├── PLCSimAPI.py
│       │    └── SiemensAPI.DLL
│       └── PLCSimS7/
│            ├── PLCSimS7.py
│            └── NetToPLCsim/    # includes hidden EXE
├── gui/                         # GUI module (refactored)
│   ├── mainGui.py               # Main window bootstraps UI, delegates to pages
│   ├── pages/                   # Page mixins (modular logic)
│   │   ├── generalSettings.py   # Process settings UI + logic
│   │   ├── ioConfigPage.py      # IO tree loader (per simulation)
│   │   ├── generalControls.py   # General controls dock + handlers
│   │   └── simPage.py           # Navigation + simulation page controls
│   └── media/                   # GUI assets, icons, styles, .ui, .qrc
├── simulations/                 # Simulations module
│   ├── __init__.py
│   └── PIDtankValve/            # Tank simulation
│       ├── __init__.py
│       ├── simulation.py        # Implements SimulationInterface
│       ├── status.py            # Runtime status
│       ├── config.py            # Configuration parameters
│       ├── SimGui.py            # Visualization widget
│       └── media/               # Simulation-specific assets

## Key Components

### 1. Core Module (`/src/core/`)

#### `configuration.py`
Central configuration with enhanced Save/Load functionality:

**Features:**
- PLC connection settings management
- **JSON-based state persistence**
- Complete application state save/load
- Validation on load

**Usage:**
```python
from core.configuration import configuration
from core.simulationManager import SimulationManager

config = configuration()
sim_mgr = SimulationManager()

# Save complete state
config.Save(sim_mgr, "saved_state.json", "IO/IO_configuration.json")

# Load complete state (auto-opens simulation)
config.Load(sim_mgr, "saved_state.json")
````

**Saved State Includes:**

- Main configuration (PLC protocol, IP, control mode)
- Active simulation name
- Simulation configuration (all parameters)
- Simulation status (all process values)
- IO configuration path reference

#### `simulationManager.py`

Manages simulation lifecycle:

- Register available simulations
- Load/unload simulations
- Start/stop/reset operations
- Provide status to other modules

#### `protocolManager.py`

Manages PLC protocol connections:

- Activate specific protocol
- Connect/disconnect operations
- Protocol state management
- Convenience helpers to build/activate/connect from `configuration` and prime IO ranges

**Helpers:**

- `build_protocol_from_config(config)`: creates the appropriate protocol instance using `config.plcProtocol` and related fields.
- `initialize_and_connect(config, lowest_byte, highest_byte)`: builds, activates, connects, and resets IO ranges.

**Usage (helpers):**

```python
from core.protocolManager import ProtocolManager
from core.configuration import configuration

config = configuration()
pm = ProtocolManager()

ok = pm.initialize_and_connect(config, lowest_byte=0, highest_byte=10)
if ok:
  plc = pm.get_active_protocol()
  # ... use IO handler with plc
```

#### `interface.py`

Abstract base class defining the contract all simulations must implement:

```python
class SimulationInterface(ABC):
    def start(self) -> None
    def stop(self) -> None
    def reset(self) -> None
    def update(self, dt: float) -> None
    def get_status(self) -> Dict[str, Any]
    def set_input(self, key: str, value: Any) -> None
    def get_output(self, key: str) -> Any
    def get_config(self) -> Dict[str, Any]
    def set_config(self, config: Dict[str, Any]) -> None
    def get_name(self) -> str
```

### 2. IO Module (`/src/IO/`)

#### `handler.py`

Generic IO handler that works with any simulation:

- Reads from PLC or GUI
- Writes to PLC or GUI
- Force value support
- Simulation-agnostic design

#### `protocols/`

All protocol files **remain unchanged** from original implementation:

- `logoS7.py` - Logo S7 communication
- `plcS7.py` - PLC S7 communication
- `PLCSimAPI/` - PLCSimAPI implementations

### 3. GUI Module (`/src/gui/`)

Refactored to separate window bootstrapping from page logic.

- **mainGui.py**: Loads Qt `.ui`, compiles `.qrc` to `Resource_rc.py` if available, constructs `MainWindow` and delegates behavior to page mixins. Holds only orchestration and app-level timers.
- **pages/generalSettings.py**: `ProcessSettingsMixin` sets up process/network controls; updates `configuration`.
- **pages/ioConfigPage.py**: `IOConfigMixin` provides `load_io_tree()` which selects `IO/IO_treeList_<simulation>.xml` based on active simulation and repopulates the IO tree. Loads common “GeneralControls” plus simulation-specific nodes. Legacy `IO_treeList.xml` supported as fallback.
- **pages/generalControls.py**: `GeneralControlsMixin` manages the floating dock, Start/Stop/Reset buttons, analog slider ranges and status writes, plus status-driven UI updates (indicators, LCDs). Honors GUI vs PLC control mode.
- **pages/simPage.py**: `SimPageMixin` owns navigation (`settings`, `IO`, `sim`, `sim settings`), start/close of simulations, float/dock of sim pages, and keeps `MainScreen` content switched to active page. On simulation change, updates `simulationManager`’s active name and triggers `load_io_tree()`.
- **media/**: `mainWindowPIDRegelaarSim.ui`, `style.qss`, `Resource.qrc`, icons. `pyrcc5` compiles resources to `Resource_rc.py` at runtime; falls back gracefully if missing.

### 4. Simulations Module (`/src/simulations/`)

Each simulation follows standard structure:

#### `PIDtankValve/`

- `simulation.py` - Implements `SimulationInterface`
- `config.py` - Configuration parameters (tankVolume, flowRates, etc.)
- `status.py` - Runtime status (liquidVolume, temperature, etc.)
- `SimGui.py` - Qt widget for visualization

### 5. IO Module (`/src/IO/`)

- **IO*treeList*\*.xml**: Per-simulation IO trees, e.g. `IO_treeList_PIDtankValve.xml`, `IO_treeList_conveyor.xml`. Loader merges common GeneralControls with sim-specific sections. The IO tree reloads when the active simulation changes.
- **IO_configuration.json**: IO address/range configuration loaded on startup; used by the IO handler.

### 6. Entry Point (`/src/main.py`)

- Initializes `configuration`, `SimulationManager`, `ProtocolManager`, `IOHandler`.
- Registers and loads default simulation (`PIDtankValve`).
- Starts `QApplication`, builds `MainWindow`, assigns `mainConfig`, `tanksim_config`, `tanksim_status` for legacy compatibility.
- Runs the main loop: processes Qt events, handles PLC connect/disconnect via `ProtocolManager.initialize_and_connect()`, updates simulation and IO, and refreshes the GUI. Legacy bridging variables have been removed in favor of `active_config`/`active_status` from `SimulationManager`.

## GUI ↔ IO ↔ PLC ↔ Simulation Data Flow

- **Control Mode**: `configuration.plcGuiControl` selects `$gui$` vs `$plc$`.
  - $gui$: GUI widgets write into `tanksim_status` (e.g., general controls sliders/buttons). IO handler publishes these as PLC inputs where applicable.
  - $plc$: PLC outputs override GUI controls; `generalControls` sliders reflect PLC-driven values.
- **Simulation Selection**: `SimPageMixin.start_simulation(index)` sets `simulationManager._active_simulation_name` (or loads if registered) and calls `IOConfigMixin.load_io_tree()` to reload per-simulation IO tree.
- **Main Loop (main.py)**:
  - Updates simulation via `simulationManager.update_simulation(dt)`.
  - If PLC connected: `ProtocolManager` exchanges IO; `IOHandler.updateIO()` transfers values between PLC and `tanksim_status` with force support.
  - GUI timer `MainWindow.update_all_values()` refreshes widgets: simulation display, IO status, general controls dock, and connection icon.
- **Resources/UI**: `mainGui.py` loads `.ui`, compiles `.qrc` if present, and applies `style.qss`.
- **Save/Load**: `configuration.Save(sim_mgr, path, io_config)` persists complete app state; `Load()` restores and auto-loads the saved simulation.

## Save/Load Functionality

### JSON Structure

The saved state file has the following structure:

```json
{
  "version": "1.0",
  "timestamp": "2025-12-19T16:05:30.974135",
  "main_config": {
    "plcGuiControl": "gui",
    "plcProtocol": "PLC S7-1500/1200/400/300/ET 200SP",
    "plcIpAdress": "192.168.1.100",
    ...
  },
  "active_simulation": "PIDtankValve",
  "simulation_config": {
    "simulationInterval": 0.1,
    "tankVolume": 2000.0,
    "valveInMaxFlow": 10.0,
    ...
  },
  "simulation_status": {
    "liquidVolume": 750.5,
    "liquidTemperature": 45.3,
    "simRunning": true,
    ...
  },
  "io_config_path": "IO/IO_configuration.json"
}
```

### Testing Save/Load

Run the test script to verify functionality:

```bash
cd src
python test_save_load.py
```

Expected output:

```
✓✓✓ ALL TESTS PASSED ✓✓✓

The Save/Load functionality is working correctly:
  ✓ JSON file created with complete state
  ✓ Simulation auto-loaded from saved name
  ✓ All configuration values restored
  ✓ All status/process values restored
  ✓ IO configuration path preserved
```

## Usage Examples

### Basic Simulation Loading

```python
from core.simulationManager import SimulationManager
from simulations.PIDtankValve.simulation import PIDTankSimulation

# Create manager
sim_mgr = SimulationManager()

# Register simulation types
sim_mgr.register_simulation('PIDtankValve', PIDTankSimulation)

# Load a simulation
sim_mgr.load_simulation('PIDtankValve', 'my_tank_sim')

# Control simulation
sim_mgr.start_simulation()
sim_mgr.update_simulation(dt=0.1)
sim_mgr.stop_simulation()

# Get status
status = sim_mgr.get_status()
print(f"Liquid volume: {status['liquidVolume']}")
```

### Protocol Management

```python
from core.protocolManager import ProtocolManager
from IO.protocols.plcS7 import plcS7

# Create manager
protocol_mgr = ProtocolManager()

# Create protocol instance
plc = plcS7("192.168.0.1", rack=0, slot=1)

# Activate and connect
protocol_mgr.activate_protocol("PLC S7", plc)
if protocol_mgr.connect():
    print("Connected to PLC")

    # Reset IO ranges
    protocol_mgr.reset_inputs(0, 10)
    protocol_mgr.reset_outputs(0, 10)

    # Later...
    protocol_mgr.disconnect()
```

### Complete Application Flow

```python
from core.configuration import configuration
from core.simulationManager import SimulationManager
from core.protocolManager import ProtocolManager
from IO.handler import IOHandler
from simulations.PIDtankValve.simulation import PIDTankSimulation

# Initialize core components
config = configuration()
sim_mgr = SimulationManager()
protocol_mgr = ProtocolManager()
io_handler = IOHandler()

# Register and load simulation
sim_mgr.register_simulation('PIDtankValve', PIDTankSimulation)
sim_mgr.load_simulation('PIDtankValve', 'tank1')

# Get simulation objects
active_sim = sim_mgr.get_active_simulation()

# Main loop
while True:
    # Update simulation
    sim_mgr.update_simulation(dt=0.1)

    # Handle IO if protocol connected
    if protocol_mgr.is_connected():
        plc = protocol_mgr.get_active_protocol()
        io_handler.updateIO(
            plc, config,
            active_sim.config,
            active_sim.status
        )
```

## Migration Status

### ✅ Completed

- Core module fully implemented
- IO module restructured with protocols moved
- Simulations module created with PIDtankValve
- Save/Load functionality implemented and tested
- Protocol files preserved unchanged
- New main.py created with architecture integration

### 🔄 In Progress

- GUI page modularization: completed for navigation, IO tree, general controls
- Conveyor simulation migration
- Import path updates as new pages/sims land

### ⏳ Pending

- Full GUI refactoring to new structure
- Conveyor simulation migration
- Legacy folder cleanup
- Complete integration testing

## Benefits of New Architecture

1. **Modularity**: Clear separation of concerns
2. **Extensibility**: Easy to add new simulations or protocols
3. **Maintainability**: Uniform interfaces and structure
4. **State Persistence**: Complete save/load with validation
5. **Testability**: Components can be tested independently

## Testing

### Unit Tests

```bash
# Test core components
python -c "from core.configuration import configuration; c = configuration()"

# Test Save/Load
python test_save_load.py

# Test simulation loading
python -c "
from core.simulationManager import SimulationManager
from simulations.PIDtankValve.simulation import PIDTankSimulation
m = SimulationManager()
m.register_simulation('PIDtankValve', PIDTankSimulation)
m.load_simulation('PIDtankValve', 'test')
"
```

### Integration Test

```bash
# Run the main (requires PyQt5)
python main.py
```

## Notes

- Protocol files in `/IO/protocols/` are **unchanged** from original
- Old directory structure temporarily preserved for backward compatibility
- GUI modularization active: `MainWindow` delegates to page mixins; no legacy bridging in `main.py`
- All simulation data (config, status) properly serialized in JSON format

## Future Enhancements

1. Page registry to construct/register content widgets programmatically
2. Add conveyor simulation
3. Enhanced simulation switching with transitions
4. Add more comprehensive validation in Load()
5. Support for multiple simultaneous simulations
6. Plugin architecture for custom simulations

---

## GUI Widgets Documentation

### Custom Widgets (`/src/gui/widgets/`)

The application includes custom reusable widgets for enhanced user experience:

#### SidebarButton (`sidebar_button.py`)

Custom QPushButton subclass for collapsible sidebar navigation.

**Features:**
- Supports `expanded` property for dynamic QSS styling
- Smooth hover effects with scale transformation (1.02x)
- Active/checked state styling with visual feedback
- Integrates with sidebar animation system (300ms ease-in-out)

**Usage:**
```python
from gui.widgets import SidebarButton

button = SidebarButton("Settings", icon=settings_icon)
button.expanded = True  # Expand to show text
button.expanded = False  # Collapse to icon only
```

#### SimControlPanel (`sim_control_panel.py`)

Standardized control panel for simulation pages with consistent UX.

**Control Buttons (Color-coded):**
- **Start** (Green #4CAF50) - Initiates simulation
- **Stop** (Red #f44336) - Halts simulation
- **Pause** (Yellow #ff9800) - Temporarily pauses execution
- **Reset** (Gray #757575) - Resets to default values

**Setpoint Sliders:**
- Temperature: 0-100°C with real-time value display
- Water Flow: 0-100 L/min with real-time value display

**Status Indicator:**
- LED-style indicator showing current state (Running/Stopped/Paused)
- Color changes based on state

**I/O Integration:**
Each control automatically generates I/O configuration entries with unique IDs following the pattern: `SIM_{SimName}_{ControlType}_{Index}`

**Signals:**
```python
startClicked()          # Emitted when Start button clicked
stopClicked()           # Emitted when Stop button clicked
pauseClicked()          # Emitted when Pause button clicked
resetClicked()          # Emitted when Reset button clicked
temperatureChanged(int) # Emitted when temperature setpoint changes
waterFlowChanged(int)   # Emitted when water flow setpoint changes
```

**Usage:**
```python
from gui.widgets import SimControlPanel

control_panel = SimControlPanel(parent=self, sim_name="TankSimulation")
control_panel.startClicked.connect(self.on_simulation_start)
control_panel.temperatureChanged.connect(self.on_temp_setpoint_changed)

# Get I/O configuration for integration
io_config = control_panel.get_io_config()
```

---

## Visual Design System

### Professional Blue Theme

The application follows a consistent professional blue accent theme throughout:

**Color Palette:**
- **Primary Blue:** #3a7bd5 - Main actions and active states
- **Dark Blue:** #2a5f9e - Hover states and emphasis
- **Light Blue:** #4a8fe7 - Secondary actions
- **Accent Blue:** #5aa3ff - Highlights and borders
- **Background Dark:** #1e1e1e - Dark backgrounds
- **Background Light:** #2d2d30 - Sidebar and panels
- **Text Primary:** #ffffff - Main text on dark backgrounds
- **Text Secondary:** #cccccc - Secondary text

**Control-Specific Colors:**
- **Success/Start:** #4CAF50 (Green)
- **Danger/Stop:** #f44336 (Red)
- **Warning/Pause:** #ff9800 (Orange)
- **Neutral/Reset:** #757575 (Gray)

### Animation Timings

Consistent animation timings for professional feel:
- **Hover effects:** 150ms transition
- **Button press:** 100ms animation
- **Sidebar expand/collapse:** 300ms ease-in-out
- **Panel expansions:** 300ms ease-in-out
- **Value updates:** 200ms smooth interpolation

### Design Principles

1. **Consistency:** All buttons, inputs, and controls follow the same design language
2. **Feedback:** Visual feedback for all user interactions (hover, active, disabled states)
3. **Accessibility:** Clear contrast ratios, adequate click targets (minimum 40px height)
4. **Professional:** Industrial application aesthetic with modern touches
5. **Performance:** Smooth animations without impacting simulation performance

---

## License Compliance

### Third-Party Libraries

This project uses the following open-source libraries:

**PyQt5** (GPL v3 License)
- Website: https://www.riverbankcomputing.com/software/pyqt/
- License: GNU General Public License v3
- Usage: GUI framework and widgets

**NumPy** (BSD License)
- Website: https://numpy.org/
- License: BSD 3-Clause License
- Usage: Numerical computations in simulation engine

**python-snap7** (MIT License)
- Website: https://github.com/gijzelaerr/python-snap7
- License: MIT License
- Usage: Siemens S7 PLC communication

**pymodbus** (BSD License)
- Website: https://github.com/pymodbus-dev/pymodbus
- License: BSD License
- Usage: Modbus protocol implementation

**pythonnet** (MIT License)
- Website: https://github.com/pythonnet/pythonnet
- License: MIT License
- Usage: .NET interoperability for PLCSim API

### License Header Template

All new Python files include the following header:

```python
"""
This module is part of the PLC-modbus-proces-simulator project.

Libraries used:
- PyQt5: GPL v3 License (https://www.riverbankcomputing.com/software/pyqt/)
- NumPy: BSD License (https://numpy.org/doc/stable/license.html)
- python-snap7: MIT License (https://github.com/gijzelaerr/python-snap7)
- pymodbus: BSD License (https://github.com/pymodbus-dev/pymodbus)
- pythonnet: MIT License (https://github.com/pythonnet/pythonnet)

Full license information available in LICENSE.txt
"""
```

### Compliance Notes

- **GPL v3 (PyQt5):** This project complies with GPL v3 by being open source
- **BSD/MIT Libraries:** Compatible with GPL v3, no restrictions
- All licenses preserved in their respective library installations
- Full license texts available in project LICENSE.txt file

---

## Migration Status

### Completed ✅

- [x] Core module architecture (configuration, simulationManager, protocolManager)
- [x] PIDtankValve simulation fully migrated and tested
- [x] GUI refactored to page mixins (generalSettings, ioConfigPage, generalControls, simPage)
- [x] Per-simulation IO tree loading system
- [x] Save/Load complete application state (JSON)
- [x] Protocol manager with helper functions
- [x] General Controls dock with GUI/PLC mode support
- [x] Professional blue theme styling
- [x] Sidebar animation improvements (600ms → 300ms)
- [x] Custom GUI widgets (SidebarButton, SimControlPanel)
- [x] Comprehensive data flow documentation

### In Progress 🔄

- [ ] Dashboard editor with drag-and-drop widget creation
- [ ] I/O configuration enhancements (inline editing, search/filter)
- [ ] Settings page with persistence (QSettings)
- [ ] Integration of SimControlPanel into simulation pages

### Planned 📋

- [ ] Conveyor simulation migration
- [ ] Additional simulation types (heating system, mixing tank)
- [ ] Advanced PID tuning interface
- [ ] Real-time trending and data logging
- [ ] Recipe management system
- [ ] Multi-language support (i18n)
- [ ] Advanced diagnostics and error logging
- [ ] Simulation scenario scripting

---

## Development Guidelines

### Adding a New Simulation

1. Create simulation folder in `/src/simulations/{name}/`
2. Implement `SimulationInterface` in `simulation.py`
3. Create `config.py` and `status.py` classes
4. Create visualization widget in `gui.py`
5. Create IO tree XML: `IO/IO_treeList_{name}.xml`
6. Register simulation in `main.py`
7. Add navigation button in UI file

### Modifying GUI

1. Edit `.ui` file in Qt Designer (recommended) OR
2. Update page mixins in `/src/gui/pages/` for logic
3. Update `style.qss` for styling (preferred over inline styles)
4. Follow professional blue theme color palette
5. Maintain consistent animation timings

### Testing Workflow

1. Test individual components in isolation
2. Test integration with existing systems
3. Verify PLC communication doesn't break
4. Check GUI mode and PLC mode both work
5. Test save/load functionality
6. Verify no console errors or warnings

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Document all public methods with docstrings
- Add comments for complex logic only
- Keep functions focused and concise
- Maintain existing code patterns

---

## Troubleshooting

### Common Issues

**pyrcc5 fails to compile resources:**
- Application continues without compiled resources
- Icons may not display correctly
- Install PyQt5-tools: `pip install PyQt5-tools`

**PLC connection fails:**
- Check IP address configuration
- Verify PLC is accessible on network
- Ensure correct protocol selected
- Check firewall settings

**Simulation doesn't update:**
- Verify simulation is started (check status indicator)
- Check main loop is running
- Verify timer interval is appropriate
- Check for exceptions in console

**GUI elements not styled:**
- Verify style.qss is loaded
- Check for QSS syntax errors
- Inspect element names match selectors
- Use Qt Style Sheet editor for debugging

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export DEBUG_MODE=1
python src/main.py
```

### Performance Optimization

- Reduce update timer interval if needed (default 100ms)
- Disable unused visualizations
- Optimize simulation calculations
- Profile with cProfile if performance issues persist

---

End of Architecture Documentation
