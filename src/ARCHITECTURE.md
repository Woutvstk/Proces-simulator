# Architecture Overview

## What This Thing Does

This is a PLC simulator that can run different process simulations (tank control, conveyors, etc) and talk to real/simulated PLCs via multiple protocols (S7-1200/1500, LOGO!, PLCSim). Built with PyQt5 for the GUI and structured to make adding new simulations relatively painless.

## Directory Layout

```
/src/
├── main.py                      # Entry point - main loop lives here
├── core/                        # Config, simulation registry, protocol manager
│   ├── configuration.py         # Main app config + save/load state
│   ├── interface.py             # Base class all simulations inherit from
│   ├── simulationManager.py     # Handles loading/switching simulations
│   └── protocolManager.py       # Manages PLC protocol connections
├── IO/                          # Everything related to PLC communication
│   ├── handler.py               # Generic IO handler (works with any simulation)
│   ├── IO_configuration.json    # IO mapping config
│   ├── IO_treeList_*.xml        # Per-simulation IO trees
│   └── protocols/               # Protocol implementations
│       ├── logoS7.py           # LOGO! S7 protocol
│       ├── plcS7.py            # PLC S7 protocol
│       ├── PLCSimAPI/          # PLCSim Advanced (requires DLL)
│       └── PLCSimS7/           # PLCSim via NetToPLCsim bridge
├── gui/                         # GUI stuff
│   ├── mainGui.py              # Main window - loads UI, delegates to pages
│   ├── pages/                  # Page logic split into mixins
│   │   ├── generalSettings.py  # Network/protocol settings
│   │   ├── ioConfigPage.py    # IO configuration table
│   │   ├── generalControls.py  # Start/Stop/Reset controls dock
│   │   └── simPage.py         # Simulation page navigation
│   └── media/                  # Icons, styles, Qt UI files
└── simulations/                # Simulation implementations
    └── PIDtankValve/          # Tank temperature/level control sim
        ├── simulation.py      # Main simulation logic
        ├── config.py          # Configuration parameters
        ├── status.py          # Runtime state
        └── gui.py             # Visualization widget
```

## Core Module

### configuration.py

Central config manager that handles:

- PLC connection settings (IP, protocol, rack/slot)
- Control mode (GUI vs PLC control)
- Complete state save/load to JSON

Save/load includes everything - main config, active simulation, process values, IO mapping. Makes it easy to restore exact state after restart.

```python
config = configuration()
config.Save(sim_mgr, "my_state.json", "IO/IO_configuration.json")
# Later...
config.Load(sim_mgr, "my_state.json")  # Auto-loads saved simulation
```

### simulationManager.py

Keeps track of available simulations and manages the active one. You register simulation classes, then load/unload them as needed.

```python
sim_mgr = SimulationManager()
sim_mgr.register_simulation('PIDtankValve', PIDTankSimulation)
sim_mgr.load_simulation('PIDtankValve', 'tank1')
sim_mgr.start_simulation()
```

### protocolManager.py

Handles protocol lifecycle - building, connecting, disconnecting. Has some helper methods to make it easier to get a protocol up and running from config settings.

```python
pm = ProtocolManager()
pm.initialize_and_connect(config, lowest_byte=0, highest_byte=10)
plc = pm.get_active_protocol()
```

### interface.py

Abstract base class that defines what every simulation needs to implement:

- start/stop/reset
- update(dt) - main simulation step
- get/set config and status
- IO getters/setters

## IO Module

### handler.py

Generic IO handler that works with any simulation. Reads outputs from PLC (or GUI), writes inputs to PLC. Handles forced values, manual mode, all that jazz. Simulation-agnostic - uses the config/status objects passed to it.

Key thing: In manual mode, GUI values override PLC outputs so you can test stuff manually even when connected.

### protocols/

Each protocol file (logoS7.py, plcS7.py, PLCSimAPI.py, etc) implements the same interface:

- GetDI/SetDI, GetDO/SetDO for digital IO
- GetAI/SetAI, GetAO/SetAO for analog IO
- connect/disconnect/isConnected

The actual protocol implementations are pretty much unchanged from the original code.

**Important note for PLCSim:** PLCSim mode can be sluggish in manual mode when sending coil commands. This is a known quirk - each C# API call through pythonnet has overhead, and when you stack 15-20 of them per cycle it adds up. Still usable, just don't expect 60fps GUI updates.

## GUI Module

Refactored to separate the main window bootstrap logic from actual page logic.

**mainGui.py** - Loads the Qt UI file, compiles resources if needed, creates the main window. Delegates all the actual work to page mixins. Basically just glue code.

**Page mixins:**

- **generalSettings.py** - Protocol/network settings page
- **ioConfigPage.py** - IO tree with drag/drop, address editing, conflict detection. Auto-loads the right XML file when you switch simulations. Has special handling for LOGO mode address translation (internal format vs LOGO display format).
- **generalControls.py** - Floating dock with Start/Stop/Reset and manual control sliders
- **simPage.py** - Handles switching between simulations and updating the IO tree when you change sims

## Simulations Module

Each simulation follows the same pattern:

```
simulation_name/
  ├── simulation.py    # Implements SimulationInterface
  ├── config.py        # Parameters (volumes, flow rates, etc)
  ├── status.py        # Runtime state (current temp, level, etc)
  └── gui.py           # Qt widget for visualization
```

### PIDtankValve Example

Tank simulation with:

- Inlet/outlet valves (digital or analog control)
- Heater (digital or analog)
- Temperature control with heat loss
- Level sensors (digital + analog)
- Liquid physics (specific heat, boiling point, etc)

The gui.py uses SVG manipulation to animate the tank visually - liquid level, temperature color coding, valve states, etc.

## Data Flow

**Control Modes:**

- **GUI mode**: GUI widgets write to status, those values drive the simulation and optionally get sent to PLC as inputs
- **PLC mode**: PLC outputs control the simulation, GUI shows feedback
- **Manual mode** (while connected): GUI overrides PLC outputs, but sensors still go to PLC. Useful for testing.

**Main Loop (main.py):**

1. Process Qt events
2. Update simulation physics: `sim_mgr.update_simulation(dt)`
3. If PLC connected: Exchange IO via handler
4. Update GUI displays
5. Repeat

**Simulation Switching:**
When you click a different simulation in the nav menu, it:

1. Stops current simulation
2. Loads new simulation via SimulationManager
3. Reloads IO tree from the new sim's XML file
4. Switches the GUI page

## Save/Load Format

Saves to JSON with this structure:

```json
{
  "version": "1.0",
  "timestamp": "...",
  "main_config": {
    /* PLC settings, protocol, IP, etc */
  },
  "active_simulation": "PIDtankValve",
  "simulation_config": {
    /* Tank volume, flow rates, etc */
  },
  "simulation_status": {
    /* Current liquid level, temp, etc */
  },
  "io_config_path": "IO/IO_configuration.json"
}
```

Pretty straightforward. Load() restores everything and auto-switches to the saved simulation.

## LOGO Mode Quirks

LOGO addresses use a different format than standard S7:

- Inputs: V0.0, V0.1 instead of I0.0, I0.1
- Outputs: Q1, Q2 instead of Q0.0, Q0.1
- Analog: VW2, AQ1 instead of IW2, QW2

The IO config page has an "interpolator" that translates between internal format (used for communication) and LOGO display format (shown in table). This runs automatically when in LOGO mode.

Conflict detection had to be fixed to compare LOGO format addresses, not internal format. Byte offsets also needed special handling per signal type (digital input uses BoolInput offset, analog output uses DWORDOutput offset, etc).

## Testing

Run `python test_save_load.py` to verify save/load works correctly. It creates a temp file, saves state, loads it back, and validates everything matches.

For GUI testing just run `python main.py` and click around.

## Known Issues & Fixes

- **PLCSim manual mode flickering**: Fixed by restructuring when GUI events process and fixing forced_values priority
- **LOGO address conflicts**: Fixed by running interpolator before conflict checks
- **Trend window gaps during drag**: Fixed by adding moveEvent/resizeEvent handlers
- **GUI sluggish in PLCSim mode**: Reduced IO interval from 100ms to 50ms, added processEvents() after update cycle

## Adding New Simulations

1. Create folder in `simulations/`
2. Implement simulation.py with SimulationInterface
3. Create config.py, status.py, gui.py
4. Create IO_treeList_yoursim.xml in IO/
5. Register in main.py: `sim_mgr.register_simulation('yoursim', YourSimClass)`
6. Add nav button in Qt Designer

That's pretty much it. The IO handler and protocol stuff all work automatically once you have the config/status structure set up right.
