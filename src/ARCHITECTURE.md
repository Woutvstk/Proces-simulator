# Architecture Overview

## What This Thing Does

This is an industrial process simulator that bridges the gap between control system development and real-world testing. It runs physics-based process simulations (tank temperature control, conveyor systems, etc.) while communicating with PLCs through multiple protocols - whether it's real hardware via S7-1200/1500, a compact LOGO! controller, or virtual testing with Siemens PLCSim.

The architecture is built around modularity: simulations are self-contained units that plug into a common framework. The GUI (PyQt5) provides real-time visualization, flexible IO mapping, and diagnostic tools. Everything from simulation physics to PLC addressing is designed to be intuitive for engineers familiar with ladder logic and process control, while maintaining clean code separation for developers.

## Directory Layout

The codebase follows a layered architecture with clear separation of concerns:

```
/src/
├── main.py                      # Application entry point - main event loop
├── core/                        # Core framework components
│   ├── configuration.py         # Application-wide settings + state persistence
│   ├── interface.py             # Abstract base class for all simulations
│   ├── simulationManager.py     # Simulation lifecycle & registry management
│   ├── protocolManager.py       # Protocol abstraction & connection handling
│   └── load_save.py            # Complete state serialization with GUI sync
├── IO/                          # PLC communication layer
│   ├── handler.py               # Protocol-agnostic IO exchange logic
│   ├── buttonPulseManager.py    # Button pulse timing for momentary signals
│   ├── IO_configuration.json    # Current IO mapping (auto-generated)
│   ├── IO_treeList_*.xml        # Per-simulation signal definitions
│   └── protocols/               # Protocol implementations
│       ├── logoS7.py           # LOGO! S7 protocol (via Snap7)
│       ├── plcS7.py            # Standard S7 protocol (S7-1200/1500/300/400)
│       ├── PLCSimAPI/          # PLCSim Advanced (requires Siemens DLL)
│       └── PLCSimS7/           # PLCSim Classic via NetToPLCsim bridge
├── gui/                         # User interface layer
│   ├── mainGui.py              # Main window orchestration
│   ├── customWidgets.py        # Custom Qt widgets (editable table, etc.)
│   ├── tooltipManager.py       # Dynamic tooltip system
│   ├── trendGraphWindow.py     # Real-time data plotting
│   ├── pages/                  # Page-specific logic (mixins)
│   │   ├── generalSettings.py  # Network & protocol configuration
│   │   ├── ioConfigPage.py    # IO mapping with drag-drop & conflict detection
│   │   ├── generalControls.py  # Manual control panel (floating dock)
│   │   ├── simPage.py         # Simulation navigation
│   │   └── simSettings.py     # Simulation parameter configuration
│   └── media/                  # UI resources
│       ├── *.ui               # Qt Designer files
│       ├── *.qss              # Stylesheets
│       └── icon/              # Icons & graphics
└── simulations/                # Simulation implementations
    ├── PIDtankValve/          # Tank temperature/level control
    │   ├── simulation.py      # Physics engine & update loop
    │   ├── config.py          # IO mapping + physical parameters
    │   ├── status.py          # Runtime state (sensor values, actuator states)
    │   ├── gui.py             # Visualization widget (SVG animation)
    │   └── settingsGui.py     # Parameter configuration panel
    └── conveyor/              # (Similar structure for conveyor simulation)
```

## Core Module

The core module provides the foundational framework that all simulations build upon. It handles application lifecycle, state management, and protocol abstraction.

### configuration.py

Central configuration hub for application-wide settings. Manages PLC connection parameters, control modes, and provides complete state persistence.

**Key responsibilities:**

- PLC connection settings (IP address, protocol selection, rack/slot)
- Control mode management (GUI vs PLC control)
- Complete state serialization to JSON (delegates to StateManager)
- Application lifecycle flags (doExit, tryConnect, etc.)

The configuration object is passed throughout the application and serves as the single source of truth for connection settings.

```python
mainConfig = configuration()
mainConfig.plcIp = "192.168.0.1"
mainConfig.plcProtocol = "S7-1200/1500"
```

### load_save.py (StateManager)

Comprehensive state management system that captures and restores the complete application state. This is what makes "save state → restart → load state" work seamlessly.

**What gets saved:**

- Main configuration (PLC settings, protocol, IP, rack/slot)
- Active simulation name
- Simulation configuration (tank volume, flow rates, PID gains, etc.)
- Simulation status (current temperature, level, valve positions)
- IO configuration (complete signal mapping with custom names)
- Byte offsets and force values

**Critical features:**

- GUI synchronization: Automatically syncs loaded values back to all GUI widgets
- Loading lock: Sets `_loading_state` flag to prevent race conditions during load
- IO table rebuild: Completely clears and rebuilds IO table from saved state
- Custom signal names: Preserves user-defined signal names across save/load
- Version tracking: JSON includes version field for future compatibility

**Save process:**

1. Serialize main config
2. Serialize active simulation config & status
3. Embed IO_configuration.json (includes custom names)
4. Write to JSON file with timestamp

**Load process:**

1. Parse JSON and validate version
2. Clear GUI inputs to prevent stale values
3. Write IO config to IO_configuration.json
4. Reload simulation config (loads custom names from file)
5. Restore simulation status values
6. Sync all values back to GUI widgets
7. Rebuild IO table from saved configuration
8. Show success popup

```python
# Save complete state
state_mgr = StateManager()
state_mgr.save_state_interactive(main_window, sim_manager)

# Load restores everything
state_mgr.load_state_interactive(main_window, sim_manager)
```

### simulationManager.py

Registry and lifecycle manager for simulations. Handles registration, loading, switching, and updating simulations.

**Registration pattern:**

```python
sim_mgr = SimulationManager()
sim_mgr.register_simulation('PIDtankValve', PIDTankSimulation)
sim_mgr.register_simulation('conveyor', ConveyorSimulation)
```

**Lifecycle methods:**

- `load_simulation(name, instance_id)`: Instantiates and activates a simulation
- `start_simulation()`: Starts the active simulation's update loop
- `stop_simulation()`: Pauses updates
- `reset_simulation()`: Calls simulation's reset method
- `update_simulation(dt, status)`: Delegates to active simulation's update()

The manager maintains references to all registered classes and the currently active simulation instance. It's simulation-agnostic - it doesn't care what the simulation does, just that it implements the interface.

### protocolManager.py

Protocol lifecycle manager that abstracts away protocol differences. The IO handler doesn't need to know whether it's talking to a real PLC, LOGO!, or PLCSim - it just calls standard methods.

**Protocol abstraction:**
All protocols implement the same interface:

- `GetDI/SetDI(byte, bit)` - Digital input operations
- `GetDO/SetDO(byte, bit)` - Digital output operations
- `GetAI/SetAI(byte)` - Analog input (word) operations
- `GetAO/SetAO(byte, value)` - Analog output (word) operations
- `connect()` - Establish connection
- `disconnect()` - Clean shutdown
- `isConnected()` - Connection status

**Connection management:**

```python
pm = ProtocolManager()
success = pm.initialize_and_connect(mainConfig, lowest_byte=0, highest_byte=20)
if success:
    protocol = pm.get_active_protocol()
    # Use protocol for IO operations
pm.disconnect()  # Clean shutdown
```

**Protocol implementations:**

- **logoS7.py**: LOGO! controllers via Snap7 (special address translation)
- **plcS7.py**: Standard S7 PLCs (S7-1200/1500/300/400/ET 200SP)
- **PLCSimAPI**: Siemens PLCSim Advanced (requires SimulationRuntimeManager DLL)
- **PLCSimS7**: PLCSim Classic via NetToPLCsim.exe bridge (legacy mode)

**PLCSim performance optimization:**
PLCSim S7 protocol uses ThreadPoolExecutor with throttling to handle the 40+ TCP calls per cycle:

- 6 worker threads
- Semaphore limiting 4 concurrent operations
- 3ms throttle between calls
- 2-second grace period after connection to allow initialization

### interface.py

Abstract base class defining the contract all simulations must fulfill. Enforces consistent structure across different simulation types.

**Required methods:**

- `start()`: Initialize simulation
- `stop()`: Pause simulation
- `reset()`: Reset to initial state
- `update(dt, status)`: Main physics/logic update (called every cycle)
- `get_config()`: Return configuration object
- `set_config(config)`: Accept new configuration
- `get_status()`: Return current state
- `set_status(status)`: Restore state

**Design philosophy:**
The interface is deliberately minimal. It doesn't dictate what the simulation does or how it works internally - it only specifies the methods needed for the framework to interact with it. This makes it easy to add wildly different simulation types (pneumatic systems, motors, chemical processes) without changing core code.

## IO Module

The IO module handles all PLC communication. It's designed to be simulation-agnostic - the same IO handler works with any simulation as long as it follows the config/status pattern.

### handler.py

The IO handler is the bridge between PLC memory and simulation state. It orchestrates bidirectional data exchange while respecting forced values, manual mode, and byte offsets.

**Core method: `updateIO(protocol, mainConfig, config, status, forced_values, manual_mode)`**

This is called every cycle from the main loop. It performs two operations:

**1. PLC → Simulation (Read actuators)**

- Read PLC output bytes (Q memory area)
- Extract signal values using byte/bit addresses from config
- Check forced values FIRST (highest priority)
- Check manual mode values SECOND (GUI overrides)
- Apply PLC values LAST (lowest priority)
- Write final values to simulation status object

**2. Simulation → PLC (Write sensors)**

- Read sensor values from simulation status
- Check forced values for sensor overrides
- Apply byte offsets if configured
- Write to PLC input bytes (I memory area)

**Forced write period:**
After connection or config change, the handler enters a 3-second "forced write period" where it aggressively writes all outputs to ensure the PLC sees correct initial values. This prevents race conditions during startup.

**Priority chain:**

```
Actuators: Forced Values > Manual Mode > PLC Values
Sensors:   Forced Values > Simulation Values
```

**Button pulse handling:**
Momentary buttons (Start, Stop, Reset) use pulse timing via ButtonPulseManager. A button press triggers a 200ms pulse, then automatically releases. This mimics real momentary push-buttons.

**Manual mode behavior:**
When manual mode is active AND PLC is connected:

- GUI controls (sliders, checkboxes) override PLC actuator outputs
- Simulation still runs with GUI-provided values
- Sensors still go TO the PLC (so PLC program can read them)
- Useful for testing simulation behavior without modifying PLC program

### buttonPulseManager.py

Manages timing for momentary button signals. Tracks active pulses and automatically clears them after the configured duration (default 200ms).

```python
pulse_mgr = ButtonPulseManager()
pulse_mgr.start_pulse('DIStart', duration_ms=200)
# After 200ms, pulse automatically clears
```

Called from main loop via `update()` to check elapsed time and clear expired pulses.

### protocols/

Each protocol implementation provides the same interface but with protocol-specific communication logic.

#### logoS7.py

LOGO! controllers via Snap7. Key difference: LOGO! uses different address notation:

- Inputs: V0.0, V0.1 (instead of I0.0, I0.1)
- Outputs: Q1, Q2 (instead of Q0.0, Q0.1)
- Analog: VW2, AQ1 (instead of IW2, QW2)

The IO config page automatically translates between internal format (I/Q) and LOGO format (V/Q) when in LOGO mode.

#### plcS7.py

Standard S7 protocol for industrial PLCs (S7-1200/1500/300/400/ET 200SP). Uses Snap7 library for communication. Supports both TCP/IP and MPI/Profibus (via adapter).

#### PLCSimAPI/

Siemens PLCSim Advanced integration. Requires SimulationRuntimeManager DLL. Provides direct API access to simulated PLC instances. Fast and reliable, but only works with TIA Portal v16+.

#### PLCSimS7/

PLCSim Classic via NetToPLCsim.exe bridge. Legacy mode for older TIA versions. Uses external process (NetToPLCsim.exe) to translate between TCP and PLCSIM protocol. Requires special configuration file (NetToPLCsim.exe.config).

**PLCSim S7 performance notes:**
PLCSim via NetToPLCsim involves 40+ TCP roundtrips per cycle (each DI/DO/AI/AO is a separate API call through C#/pythonnet). To prevent choppy GUI:

- ThreadPoolExecutor with 6 workers processes calls concurrently
- Semaphore limits to 4 simultaneous operations
- 3ms throttle between calls prevents overwhelming the bridge
- Extra `processEvents()` after each cycle keeps GUI responsive
- Minimum IO interval of 20ms (vs 100ms+ for simulation physics)

## GUI Module

The GUI layer is built with PyQt5 and organized around a mixin pattern. The main window delegates functionality to specialized page classes, keeping code organized and maintainable.

### mainGui.py

Main window orchestrator. Loads the Qt UI file (created in Qt Designer), initializes page mixins, and wires up navigation. Inherits from multiple mixin classes to combine functionality.

**Responsibilities:**

- Load UI file and compile resources
- Create instances of all page classes
- Set up simulation navigation
- Provide access points for IO handler, protocol manager, etc.
- Handle window-level events (close, resize, etc.)

**Mixin pattern:**

```python
class MainWindow(GeneralSettingsMixin, IOConfigMixin, SimPageMixin, ...):
    def __init__(self):
        # Each mixin adds its own methods and event handlers
        self.setup_general_settings()
        self.setup_io_config_page()
        # ...
```

This pattern keeps related functionality grouped while avoiding massive single-file classes.

### customWidgets.py

Custom Qt widgets that extend standard widgets with application-specific behavior.

**EditableTableWidget:**
Extends QTableWidget with:

- Row data caching (`row_data` dict)
- Custom signal name support
- Force value tracking (`forced_rows` dict)
- Conflict detection helper methods
- `_save_row_data()` / `_clear_row_data()` for lifecycle management

**EditableTableWidgetItem / ReadOnlyTableWidgetItem:**
Custom table cells with proper styling and editability control.

### tooltipManager.py

Dynamic tooltip system that provides context-sensitive help. Tooltips are defined in a central dictionary and automatically applied to widgets by object name.

```python
TOOLTIPS = {
    'pushButton_connect': 'Establish connection to PLC...',
    'QLineEdit_BoolInput': 'Byte offset for digital inputs...',
    # ...
}
```

### trendGraphWindow.py

Real-time data plotting window using pyqtgraph. Displays multiple signals on a time-based chart with:

- Configurable update rate
- Multiple Y-axes for different signal ranges
- Live legend
- Auto-scaling
- Export to image/CSV

### Page Classes

#### generalSettings.py (GeneralSettingsMixin)

Protocol and network configuration page. Handles:

- Protocol selection dropdown
- IP address / COM port configuration
- Rack/slot settings (for S7 protocols)
- Connection/disconnection logic
- Protocol-specific UI adjustments (hiding/showing fields based on selection)

**Protocol switching:**
When user changes protocol dropdown, the mixin shows/hides relevant widgets:

- S7 protocols: Show rack/slot, hide COM port
- LOGO: Show only IP address
- PLCSim: Show instance selector

#### ioConfigPage.py (IOConfigMixin)

The most complex page - handles IO signal mapping with drag-drop, address assignment, conflict detection, and force functionality.

**Left side - IO Tree:**

- Loads signal definitions from XML (`IO_treeList_*.xml`)
- Hierarchical structure (Inputs/Outputs → Digital/Analog → Signals)
- Drag-drop to table
- Auto-refreshes when simulation changes

**Right side - IO Table:**
Columns:

1. **Signal Name** (editable - custom names supported)
2. **Type** (Bool/Int - read-only)
3. **Byte** (editable)
4. **Bit** (editable, only for digital signals)
5. **Address** (computed - read-only, shows combined address)
6. **Status** (read-only, shows current value during runtime)
7. **Description** (read-only, from XML)
8. **Range** (read-only, from XML)
9. **Force** (checkbox - enable forced value)
10. **Force Value** (editable when force enabled)

**Custom signal names:**
Users can rename signals in the table. Custom names are:

- Stored in `config.custom_signal_names` dict (keyed by attribute name)
- Saved to IO_configuration.json
- Persisted across save/load operations
- Displayed in GUI visualization and tooltips
- Automatically deleted when signal is removed from table

**Drag-drop workflow:**

1. User drags signal from tree
2. Drop on table triggers `drop_on_table()`
3. System checks for duplicates
4. Signal added to first empty row (or inserted at drop position)
5. Byte offset automatically applied
6. `_save_row_data()` caches the row information

**Address conflict detection:**
Before saving or when addresses change:

- Scans all rows for overlapping byte/bit addresses
- Highlights conflicts in red
- Prevents saving until resolved
- LOGO mode: Converts addresses to LOGO format before comparison

**Byte offsets:**
Global offsets added to all signals of a type:

- BoolInput: Offset for digital inputs
- BoolOutput: Offset for digital outputs
- DWORDInput: Offset for analog inputs
- DWORDOutput: Offset for analog outputs

**Key methods:**

- `load_io_tree()`: Parse XML and populate tree widget
- `load_table_from_io_configuration_file()`: Load saved IO mapping
- `save_configuration()`: Write IO mapping to JSON (includes custom names)
- `load_all_tags_to_table()`: Load ALL signals from XML (ignores saved config)
- `check_address_conflicts()`: Validate no overlapping addresses
- `get_forced_io_values()`: Collect all forced signals as dict

**LOGO mode address translation:**
When in LOGO mode, addresses display as V0.0, Q1, etc. but are stored internally as I0.0, Q0.0, etc. The "interpolator" runs automatically:

- Before conflict checks (convert to LOGO format for comparison)
- After user edits address (convert back to internal format)
- When loading saved config (ensure display matches mode)

**Table clearing for state load:**
When loading a state or IO config file:

1. Save custom_signal_names to temp dict (prevents deletion)
2. Clear all rows with `_clear_row_data()`
3. Remove all rows: `setRowCount(0)`
4. Restore custom_signal_names from temp dict
5. Add new rows and populate from file
   This ensures clean slate and prevents mixing old/new data.

#### generalControls.py (GeneralControlsMixin)

Floating dock widget with manual control interface:

- Start/Stop/Reset buttons (with pulse generation)
- Manual mode toggle
- Generic control sliders (Control1, Control2, Control3)
- Valve/heater sliders (simulation-specific)
- Real-time value display

**Manual mode:**
When enabled, these controls override PLC outputs. Allows testing simulation without running PLC program.

#### simPage.py (SimPageMixin)

Handles simulation navigation and switching:

- Detects available simulations from registry
- Creates navigation buttons dynamically
- Switches active simulation on button click
- Reloads IO tree when simulation changes
- Updates visualization widget

#### simSettings.py (SimSettingsMixin)

Simulation parameter configuration panel:

- Tank volume, flow rates, heating power
- PID controller gains (Kp, Ki, Kd)
- Liquid properties (specific heat, boiling point)
- Setpoint values
- Min/max ranges

Changes are immediately written to active simulation config.

## Simulations Module

Each simulation is a self-contained package following a consistent structure. This makes simulations interchangeable and easy to understand.

### Standard Structure

```
simulation_name/
  ├── simulation.py    # Implements SimulationInterface - main physics/logic
  ├── config.py        # Configuration parameters and IO mapping
  ├── status.py        # Runtime state (current values)
  ├── gui.py           # Visualization widget
  └── settingsGui.py   # Configuration panel widget
```

### simulation.py

The core simulation class that implements `SimulationInterface`. Contains all physics calculations and process logic.

**Required methods:**

- `__init__()`: Create config and status objects
- `start()`: Initialize simulation state
- `stop()`: Pause execution
- `reset()`: Return to initial conditions
- `update(dt, status)`: Main physics update (called every cycle)

**Design pattern:**
The update() method receives `dt` (time delta) and a `status` object. It:

1. Reads actuator values from status (valves, heaters, etc.)
2. Calculates physics (temperature, level, flow, etc.)
3. Writes sensor values back to status
4. Updates internal state variables

No direct PLC or GUI interaction - keeps simulation portable and testable.

### config.py

Defines two types of parameters:

**1. IO Mapping:**
Byte/bit addresses for all PLC signals:

```python
self.DQValveIn = {"byte": 0, "bit": 0}  # Digital output
self.AQHeaterFraction = {"byte": 2}     # Analog output (word)
self.AITemperature = {"byte": 4}        # Analog input (word)
```

**2. Physical Parameters:**
Process-specific values:

```python
self.tankVolume = 1000.0              # Liters
self.valveInMaxFlow = 50.0            # L/min
self.heaterMaxPower = 5000.0          # Watts
self.liquidSpecificHeat = 4186.0      # J/(kg·K)
```

**Special attributes:**

- `io_signal_mapping`: Dict mapping signal names to attribute names
- `custom_signal_names`: Dict storing user-defined signal names (keyed by attr name)
- `lowestByte` / `highestByte`: Defines PLC memory range to read/write
- `importExportVariableList`: List of params to include in state save/load

**Methods:**

- `load_io_config_from_file(path)`: Load IO mapping from JSON
- `printConfigToLog()`: Debug helper to dump all settings

### status.py

Runtime state container. Holds current values for all sensors and actuators.

**Example attributes:**

```python
self.liquidLevel = 50.0           # % (sensor)
self.temperature = 20.0           # °C (sensor)
self.valveInOpen = False          # Boolean (actuator)
self.heaterPowerFraction = 0.0    # 0-1 (actuator)
```

**importExportVariableList:**
Defines which attributes get saved/loaded in state files. Only listed variables persist across sessions.

The IO handler reads actuator values from status and writes sensor values to status. The simulation reads actuators and writes sensors. It's the shared communication buffer.

### gui.py

Visualization widget that renders the simulation state graphically. For PIDtankValve, uses SVG manipulation to animate:

- Liquid level (fills tank shape)
- Temperature (color gradient - blue when cold, red when hot)
- Valve states (open/closed indicators)
- Heater state (glow effect when active)
- Sensor values (text overlays)

**Update method:**
Called from main loop after physics update. Reads status values and updates SVG elements:

```python
def update_display(self, status):
    self.update_tank_level(status.liquidLevel)
    self.update_temperature_display(status.temperature)
    self.update_valve_indicators(status.valveInOpen, status.valveOutOpen)
    # ...
```

**Custom signal names integration:**
The visualization checks `config.custom_signal_names` and uses custom names for tooltips and labels if defined.

### settingsGui.py

Qt widget for editing simulation configuration parameters. Provides input fields for all configurable values:

- Physical parameters (volumes, flow rates, powers)
- PID tuning (Kp, Ki, Kd gains)
- Setpoints and limits
- Time constants

Changes are written directly to the active simulation's config object. Some simulations recalculate derived values when settings change (e.g., time constants from volume/flow).

### PIDtankValve Simulation Details

A temperature/level controlled tank with dual valve control and heating.

**Process description:**

- Tank with configurable volume
- Inlet valve (digital or proportional control)
- Outlet valve (digital or proportional control)
- Electric heater (digital or proportional control)
- Temperature sensor (analog 0-100°C)
- Level sensor (analog 0-100%)
- High/low level switches (digital)

**Physics model:**

- Mass balance: `dLevel/dt = (flowIn - flowOut) / tankVolume`
- Energy balance: `dTemp/dt = (heaterPower - heatLoss) / (mass * specificHeat)`
- Heat loss: Convection to ambient (Newton's cooling law)
- Boiling limit: Temperature capped at liquid's boiling point

**Control modes:**

- **Digital**: Valves fully open or closed, heater on/off
- **Proportional**: 0-100% control for smooth operation

**PID controller:**
Optional PID loop can control heater power based on temperature setpoint. Tunable Kp/Ki/Kd gains.

## Data Flow

Understanding data flow is key to working with this architecture. There are three primary data paths:

### 1. Control Modes

**GUI Mode (no PLC connection):**

```
GUI Widgets → write_gui_values_to_status() → Status Object → Simulation
                                                ↓
                                          GUI Display
```

The General Controls dock provides manual inputs. Simulation runs standalone. Good for testing physics without hardware.

**PLC Mode (connected):**

```
PLC Outputs → Protocol → IO Handler → Status Object → Simulation → Status Object → IO Handler → Protocol → PLC Inputs
                                                                           ↓
                                                                     GUI Display (read-only)
```

PLC program controls the simulation. GUI shows feedback. This is the normal operating mode.

**Manual Mode (connected but GUI override):**

```
GUI Widgets → Status Object → Simulation → Status Object → IO Handler → Protocol → PLC Inputs
    ↓                                                                           ↑
    └─────── Overrides PLC Outputs ──────────────────────────────────────────┘
```

Manual mode flag tells IO handler to use GUI values instead of PLC outputs for actuators. Sensors still go TO the PLC so the PLC program can read them. Useful for testing without modifying PLC code.

**Force Values (any mode):**
Force values have HIGHEST priority and override everything:

```
Forced Values → Status Object (bypasses PLC and GUI)
```

Set via IO Config page checkboxes. Useful for isolating specific signals during debugging.

### 2. Main Loop Flow

The main loop in `main.py` orchestrates everything:

```python
while not mainConfig.doExit:
    # 1. Process Qt events (button clicks, etc.)
    app.processEvents()

    # 2. Handle connection/disconnection requests
    if mainConfig.tryConnect:
        protocolManager.initialize_and_connect(...)

    # 3. Exchange IO with PLC (if connected)
    if validPlcConnection:
        forced_values = window.get_forced_io_values()
        manual_mode = window.is_manual_mode()
        ioHandler.updateIO(protocol, mainConfig, config, status, forced_values, manual_mode)
    else:
        # No PLC - but still process forced values from IO Config page!
        if forced_values:
            ioHandler.updateIO(None, mainConfig, config, status, forced_values, manual_mode)

    # 4. Update button pulse timers
    window._button_pulse_manager.update()

    # 5. Write GUI values to status (if in Manual mode)
    window.write_gui_values_to_status()

    # 6. Run simulation physics
    dt = time.time() - timeLastUpdate
    simulationManager.update_simulation(dt, status)

    # 7. Update GUI displays
    window.update_tanksim_display()

    # 8. PLCSim gets extra processEvents() for responsiveness
    if mainConfig.plcProtocol == "PLCSim S7-1500/1200/400/300/ET 200SP":
        app.processEvents()

    timeLastUpdate = time.time()
```

**Timing notes:**

- Default simulation interval: 100ms+ (adjustable)
- PLCSim minimum interval: 20ms (due to TCP overhead)
- Button pulses: 200ms duration
- Forced write period: 3000ms after connection

### 3. Simulation Switching

When user clicks a different simulation in navigation:

```
1. simPage detects button click
2. Stop current simulation
3. Load new simulation via SimulationManager
4. Update mainConfig references
5. Reload IO tree from new XML file
6. Clear IO table (optional - depends on workflow)
7. Switch GUI visualization page
8. Start new simulation
```

The IO configuration is simulation-specific. When you switch simulations, you typically need to reconfigure IO mapping (or load a saved config for that simulation).

### 4. State Save/Load Flow

**Save:**

```
User clicks Save State
    ↓
StateManager.save_state_interactive()
    ↓
Collect data:
  - mainConfig settings
  - Active simulation name
  - Simulation config
  - Simulation status
  - IO_configuration.json (with custom names)
    ↓
Write to JSON file
    ↓
Show success popup
```

**Load:**

```
User clicks Load State
    ↓
StateManager.load_state_interactive()
    ↓
Parse JSON file
    ↓
Set _loading_state flag (prevents race conditions)
    ↓
Clear GUI inputs in Auto mode
    ↓
Write IO config to IO_configuration.json
    ↓
Reload IO config from file (loads custom names)
    ↓
Restore simulation config values
    ↓
Restore simulation status values
    ↓
Sync all values to GUI widgets
    ↓
Completely clear IO table:
  - Save custom_signal_names temporarily
  - Clear all rows
  - Remove all rows (setRowCount(0))
  - Restore custom_signal_names
    ↓
Rebuild IO table from saved config
    ↓
Clear _loading_state flag
    ↓
Show success popup
```

**Critical: Table clearing during load**
The IO table MUST be completely cleared before loading to prevent mixing old and new signals. The process:

1. Save `custom_signal_names` dict (prevents deletion during clear)
2. Call `_clear_row_data()` on each row (cleanup)
3. Call `clearContents()` (remove all items)
4. Call `setRowCount(0)` (remove all rows)
5. Restore `custom_signal_names` dict
6. Add fresh rows from saved configuration

This ensures custom names survive the reload process.

## Save/Load Format

State files use JSON format with comprehensive data capture:

```json
{
  "version": "2.0",
  "timestamp": "2026-02-01 14:30:22",
  "main_config": {
    "plcIp": "192.168.0.1",
    "plcRack": 0,
    "plcSlot": 1,
    "plcProtocol": "S7-1200/1500",
    "plcGuiControl": "plc",
    "connectionTimeout": 5.0
  },
  "active_simulation": "PIDtankValve",
  "simulation_config": {
    "tankVolume": 1000.0,
    "valveInMaxFlow": 50.0,
    "heaterMaxPower": 5000.0,
    "pidKp": 2.0,
    "pidKi": 0.1,
    "pidKd": 0.5
    // ... all configuration parameters
  },
  "simulation_status": {
    "liquidLevel": 45.2,
    "temperature": 67.8,
    "valveInOpen": true,
    "heaterPowerFraction": 0.65
    // ... all status values
  },
  "io_config": {
    "signals": [
      {
        "name": "DQValveIn",
        "type": "Bool",
        "byte": "0",
        "bit": "0",
        "io_prefix": "Q"
      },
      {
        "name": "AITemperature",
        "type": "Int",
        "byte": "4",
        "bit": "",
        "io_prefix": "I"
      }
      // ... all mapped signals
    ],
    "offsets": {
      "BoolInput": 0,
      "BoolOutput": 0,
      "DWORDInput": 2,
      "DWORDOutput": 2
    },
    "custom_signal_names": {
      "AITemperature": "Tank_Temp_PV",
      "DQValveIn": "Inlet_Valve"
      // ... user-defined names
    }
  },
  "io_config_original_path": "IO/IO_configuration.json"
}
```

**Version tracking:** The `version` field allows future compatibility checks. Current version is "2.0".

**Timestamp:** Human-readable timestamp for reference.

**Embedded IO config:** Complete IO configuration embedded in state file (not just a reference). This makes state files portable - you don't need separate IO config files.

**Custom signal names:** User-defined signal names are preserved and restored. Keyed by attribute name (not signal name) for stability across renames.

## LOGO Mode Quirks

LOGO! controllers use different address notation than standard S7 PLCs. The application handles this automatically, but it's important to understand the translation:

### Address Format Differences

**Standard S7:**

- Digital Inputs: I0.0, I0.1, I0.2, ...
- Digital Outputs: Q0.0, Q0.1, Q0.2, ...
- Analog Inputs: IW2, IW4, IW6, ... (word addresses)
- Analog Outputs: QW2, QW4, QW6, ...

**LOGO! Format:**

- Digital Inputs: V0.0, V0.1, V0.2, ... (V = "Variable")
- Digital Outputs: Q1, Q2, Q3, ... (no byte.bit notation)
- Analog Inputs: VW2, VW4, VW6, ...
- Analog Outputs: AQ1, AQ2, AQ3, ... (AQ = "Analog Output")

### Internal vs Display Format

The application stores addresses internally in standard S7 format for consistency. When in LOGO mode:

- **Display:** Shows LOGO format (V0.0, Q1, AQ2) in UI
- **Storage:** Stores S7 format (I0.0, Q0.0, QW2) in files
- **Translation:** "Interpolator" converts automatically

### When Translation Happens

1. **Loading LOGO config:** S7 format read from file → converted to LOGO for display
2. **User edits address:** LOGO format input → converted to S7 for storage
3. **Conflict detection:** All addresses converted to LOGO format before comparison
4. **Saving config:** S7 format saved to file (independent of current mode)

### Byte Offsets in LOGO Mode

Offsets work differently per signal type:

- **Digital Input (V):** Uses `BoolInput` offset
- **Digital Output (Q):** Uses `BoolOutput` offset
- **Analog Input (VW):** Uses `DWORDInput` offset
- **Analog Output (AQ):** Uses `DWORDOutput` offset

The system tracks IO prefix and applies the appropriate offset automatically.

### Conflict Detection Fix

Early versions had a bug where conflict detection used internal S7 addresses, causing false positives/negatives in LOGO mode. Fixed by converting ALL addresses to LOGO format before comparison:

```python
if logo_mode:
    # Convert to LOGO format first
    addr1_logo = interpolate_to_logo(addr1, signal1_type)
    addr2_logo = interpolate_to_logo(addr2, signal2_type)
    # Then compare
    if addr1_logo == addr2_logo:
        # Conflict!
```

## Testing

Run `python test_save_load.py` to verify save/load works correctly. It creates a temp file, saves state, loads it back, and validates everything matches.

For GUI testing just run `python main.py` and click around.

## Known Issues & Solutions

### PLCSim Performance (NetToPLCsim Bridge)

**Problem:** GUI becomes choppy when using PLCSim S7 protocol with manual controls.

**Root cause:** Each DI/DO/AI/AO operation goes through NetToPLCsim.exe (C# bridge) via pythonnet. With 40+ calls per cycle, the TCP roundtrip overhead adds up to 150-200ms total latency.

**Solution implemented:**

- ThreadPoolExecutor with 6 worker threads processes calls concurrently
- Semaphore limits to 4 simultaneous operations (prevents overwhelming bridge)
- 3ms throttle between calls for flow control
- Minimum IO interval increased to 20ms (from simulation's 100ms+)
- Extra `processEvents()` after each cycle keeps GUI responsive
- 2-second grace period after connection allows initialization

Result: GUI remains responsive even with heavy IO load. Not perfect, but usable for testing.

### LOGO Address Conflict False Positives

**Problem:** Conflict detection reported overlaps that didn't exist in LOGO mode.

**Root cause:** Conflict checker compared internal S7 format addresses, but LOGO format addresses are different (V0.0 vs I0.0).

**Solution:** Convert all addresses to LOGO format BEFORE comparison when in LOGO mode. Now conflicts are detected correctly regardless of mode.

### State Load Adding Unwanted Signals

**Problem:** Loading a saved state added ALL available signals to IO table, not just the saved ones.

**Root cause:** State load called `load_all_tags_to_table()` which loads everything from XML.

**Solution:** Changed to write saved IO config to `IO_configuration.json` BEFORE reload, then call `load_table_from_io_configuration_file()` which only loads saved signals. Table is completely cleared first to prevent mixing old/new data.

### Custom Signal Names Lost on State Load

**Problem:** User-defined signal names disappeared after loading a state file.

**Root cause:** Multi-step issue:

1. Old custom names saved before IO reload
2. New custom names loaded from state file
3. Old custom names restored, overwriting new ones
4. Table clear deleted custom names from config

**Solution:**

1. Removed the "save and restore old custom names" logic - let them load from file
2. During table clear, save custom names temporarily before `_clear_row_data()`, then restore after
3. Ensure `save_configuration()` includes custom names in JSON output

Now custom names persist correctly through save/load cycles.

### Trend Window Gaps During Window Drag

**Problem:** Real-time trend graph showed gaps when dragging/resizing window.

**Root cause:** Qt events blocked during drag operation, preventing data updates.

**Solution:** Added `moveEvent()` and `resizeEvent()` handlers that call `processEvents()` during window manipulation. Keeps data flowing even when window is being moved.

### Table Not Clearing Before State Load

**Problem:** Loading a state while IO table had different signals mixed old and new data.

**Root cause:** `load_table_from_io_configuration_file()` only cleared row data, didn't remove rows.

**Solution:** Complete table clear sequence:

1. Save custom_signal_names temporarily
2. Call `_clear_row_data()` on all rows
3. Call `clearContents()` to remove items
4. Call `setRowCount(0)` to remove rows
5. Restore custom_signal_names
6. Build fresh rows from file

Table now starts from clean slate on every load.

### Load All Tags Only Loading Some Tags

**Problem:** "Load All Tags" button only loaded simulation-specific tags, ignoring GeneralControls.

**Root cause:** Filter logic checked `enabled_attrs` which excluded many signals.

**Solution:** Removed the filter completely. "Load All Tags" now loads EVERY signal from the XML tree, regardless of category or enabled status. Also added table clear before loading.

## Testing & Development

### Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run from src directory
cd src
python main.py
```

The application will:

1. Initialize with PIDtankValve simulation loaded
2. Load IO configuration from `IO/IO_configuration.json` if it exists
3. Start forced write period (3 seconds)
4. Open main window with all tabs available

### Testing Save/Load

The `test_save_load.py` script validates state persistence:

```bash
python test_save_load.py
```

It performs:

1. Create test configuration
2. Save to temporary file
3. Load from file
4. Validate all values match
5. Test serialization/deserialization

### GUI Testing

Manual testing workflow:

1. Map some IO signals via drag-drop
2. Assign addresses (or use auto-assign)
3. Connect to PLC (or use GUI mode)
4. Run simulation and verify sensor updates
5. Test manual mode overrides
6. Set force values and verify behavior
7. Save state to file
8. Restart application
9. Load state and verify everything restored

### Performance Profiling

For performance issues:

1. Add timing logs around suspected slow code
2. Check IO interval settings (may be too aggressive)
3. Monitor thread pool utilization (PLCSim mode)
4. Profile with cProfile for detailed analysis

## Adding New Simulations

See [ADD_SIMULATION.md](ADD_SIMULATION.md) for complete step-by-step guide.

Quick overview:

1. Create folder in `simulations/`
2. Implement simulation.py with SimulationInterface
3. Create config.py, status.py, gui.py, settingsGui.py
4. Create IO_treeList_yoursim.xml in IO/
5. Register in main.py: `sim_mgr.register_simulation('yoursim', YourSimClass)`
6. Add navigation button in Qt Designer
7. Wire up settings panel

The framework handles IO exchange, protocol management, and state persistence automatically.

## References & Dependencies

### External Libraries

**Core:**

- Python 3.8+ (standard library)
- PyQt5 5.15+ (GPL v3) - GUI framework
- pyqtgraph (MIT) - Real-time plotting

**PLC Communication:**

- python-snap7 (MIT) - S7 protocol (LOGO! and S7 PLCs)
- pythonnet (MIT) - .NET interop for PLCSim API

**Utilities:**

- pathlib, json, logging (standard library)

### Hardware Requirements

**Minimum:**

- Windows 10/11 (for PLCSim support)
- 4GB RAM
- Network adapter for TCP/IP protocols

**Recommended:**

- 8GB RAM (for PLCSim Advanced)
- Dedicated network adapter for PLC communication
- TIA Portal v16+ (if using PLCSim)

---

**Document Version:** 2.0  
**Last Updated:** February 2026  
**Architecture Status:** Stable - Ready for simulation development
