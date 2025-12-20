# Project Restructuring - Industrial Simulation Framework

## Overview

This document describes the modular architecture implemented for the Industrial Simulation Framework. The application manages multiple simulations (PLC tank controls, conveyors, etc.) with different protocols (Logo S7, PLC S7, PLCSimAPI) and provides a GUI interface for monitoring and control.

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
