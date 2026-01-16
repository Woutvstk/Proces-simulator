# Novice User Guide - Adding New Simulations

## Quick Start Guide for Beginners

This guide helps you add new simulations to the Industrial Simulation Framework. It assumes basic Python knowledge but no advanced programming experience.

## Overview

The framework follows a clear structure defined in `src/ARCHITECTURE.md`. All simulations use the same pattern, making it easy to add new ones by following existing examples.

## File Structure for a New Simulation

Every simulation needs exactly 5 files in its own folder:

```
src/simulations/[your_simulation_name]/
├── __init__.py          # Module initialization (copy from existing)
├── simulation.py        # Core logic (REQUIRED - implements SimulationInterface)
├── config.py            # Settings and parameters
├── status.py            # Runtime state and values
└── gui.py               # Visual display widget (if needed)
```

## Step-by-Step: Creating Your First Simulation

### Step 1: Choose a Name

Pick a descriptive name using PascalCase (e.g., `ConveyorBelt`, `MixingTank`, `PressureValve`).

### Step 2: Copy an Existing Simulation

The easiest way to start is to copy the PIDtankValve simulation:

```bash
cd src/simulations/
cp -r PIDtankValve MyNewSimulation
cd MyNewSimulation
```

### Step 3: Understand Each File

#### `simulation.py` - The Brain (REQUIRED)

This file contains your simulation logic. It **must** implement these methods:

```python
class MySimulation(SimulationInterface):
    def start(self) -> None:
        """Called when user clicks Start button"""
        pass
    
    def stop(self) -> None:
        """Called when user clicks Stop button"""
        pass
    
    def reset(self) -> None:
        """Called when user clicks Reset button"""
        pass
    
    def update(self, dt: float) -> None:
        """Called every simulation cycle (e.g., every 0.1 seconds)
        
        dt: time since last update in seconds
        
        This is where you put your physics/logic:
        - Read inputs from self.status
        - Calculate new values
        - Write outputs to self.status
        """
        pass
    
    def get_name(self) -> str:
        """Return simulation name"""
        return "MyNewSimulation"
```

#### `config.py` - The Settings

Define all configuration parameters that users can change:

```python
class configuration:
    def __init__(self):
        # Physical parameters
        self.maxSpeed = 100.0           # Maximum speed in m/s
        self.acceleration = 2.0         # Acceleration in m/s²
        self.simulationInterval = 0.1   # Update every 0.1 seconds
        
        # IO addresses (where PLC reads/writes data)
        self.DIStart = {"byte": 0, "bit": 0}  # Digital input
        self.AQSpeed = {"byte": 2}             # Analog output
```

#### `status.py` - The Current State

Define all runtime values that change during simulation:

```python
class status:
    def __init__(self):
        # Current state
        self.currentSpeed = 0.0
        self.isMoving = False
        self.simRunning = False
        
        # Inputs from PLC/GUI
        self.startCommand = False
        self.targetSpeed = 0.0
```

#### `gui.py` - The Visual Display (Optional)

Create a PyQt5 widget to show your simulation visually. Look at `PIDtankValve/gui.py` for examples of:
- SVG graphics (tanks, valves, etc.)
- Real-time updates
- Color changes based on state

### Step 4: Register Your Simulation

Edit `src/main.py` to add your simulation:

```python
# Add import at top
from simulations.MyNewSimulation.simulation import MyNewSimulation

# Register it in the main() function
def main():
    # ... existing code ...
    
    # Register simulations
    sim_mgr.register_simulation('PIDtankValve', PIDTankSimulation)
    sim_mgr.register_simulation('MyNewSimulation', MyNewSimulation)  # ADD THIS
```

## Important Rules

### 1. Never Import from `protocols/` folder

The `protocols/` folder contains PLC communication code that should not be modified.

### 2. Use Logging, Not print()

```python
# BAD
print("Speed is:", speed)

# GOOD
import logging
logger = logging.getLogger(__name__)
logger.info(f"Speed is: {speed}")
logger.debug(f"Debug info: {speed}")  # Only shows when debugging
logger.error(f"Error: {speed}")       # For errors
```

### 3. Use Clear Variable Names

```python
# BAD
temp = 5
data = process(temp)
result = data * 2

# GOOD
tank_capacity_liters = 5
current_volume_liters = calculate_volume(tank_capacity_liters)
doubled_volume = current_volume_liters * 2
```

### 4. Keep Functions Short

If a function is longer than 50 lines, split it into smaller functions:

```python
# Instead of one huge function:
def update(self, dt):
    # 100 lines of code...
    pass

# Split into logical pieces:
def update(self, dt):
    self._update_physics(dt)
    self._update_sensors()
    self._check_limits()

def _update_physics(self, dt):
    # 20 lines
    pass

def _update_sensors(self):
    # 15 lines
    pass

def _check_limits(self):
    # 10 lines
    pass
```

### 5. Add Docstrings

Every function and class should explain what it does:

```python
def calculate_flow_rate(valve_opening, pressure_difference):
    """
    Calculate liquid flow rate through a valve.
    
    Args:
        valve_opening: Valve position from 0.0 (closed) to 1.0 (fully open)
        pressure_difference: Pressure difference in bar
        
    Returns:
        Flow rate in liters per second
    """
    return valve_opening * pressure_difference * 10.0
```

## Testing Your Simulation

### 1. Check for Syntax Errors

```bash
python3 -m py_compile src/simulations/MyNewSimulation/simulation.py
```

### 2. Test Imports

```bash
cd src
python3 -c "from simulations.MyNewSimulation.simulation import MyNewSimulation; print('Success!')"
```

### 3. Run the Application

```bash
cd src
python3 main.py
```

## Common Mistakes

### Mistake 1: Forgetting to Update in main.py

**Symptom**: Simulation doesn't appear in the list

**Fix**: Add your simulation to the registration in `main.py`

### Mistake 2: Wrong File Names

**Symptom**: "ModuleNotFoundError"

**Fix**: Make sure files are named exactly: `simulation.py`, `config.py`, `status.py`, `gui.py`

### Mistake 3: Not Implementing All Methods

**Symptom**: "TypeError: Can't instantiate abstract class"

**Fix**: Your simulation class must have all required methods from `SimulationInterface`

### Mistake 4: Using print() Instead of Logging

**Symptom**: No output or cluttered console

**Fix**: Use `logger.info()`, `logger.debug()`, `logger.error()`

## Getting Help

1. **Look at existing simulations**: `PIDtankValve` and `conveyor` are good examples
2. **Read ARCHITECTURE.md**: Explains the complete structure
3. **Check the interface**: `src/core/interface.py` shows what methods you need
4. **Follow the pattern**: All simulations work the same way

## Quick Reference: File Templates

### Minimal `simulation.py`

```python
"""
[Your Simulation Name] - Brief description.

External Libraries Used:
- typing (Python Standard Library) - Type hints
"""

import logging
from typing import Dict, Any
from core.interface import SimulationInterface
from .config import configuration
from .status import status

logger = logging.getLogger(__name__)


class MyNewSimulation(SimulationInterface):
    """Your simulation description"""
    
    def __init__(self):
        self.config = configuration()
        self.status = status()
        self._running = False
    
    def start(self) -> None:
        """Start simulation"""
        self._running = True
        logger.info("Simulation started")
    
    def stop(self) -> None:
        """Stop simulation"""
        self._running = False
        logger.info("Simulation stopped")
    
    def reset(self) -> None:
        """Reset to initial state"""
        self.status = status()
        logger.info("Simulation reset")
    
    def update(self, dt: float) -> None:
        """Update simulation (called every cycle)
        
        Args:
            dt: Time since last update in seconds
        """
        if not self._running:
            return
        
        # Your simulation logic here
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Return current status as dictionary"""
        return vars(self.status)
    
    def get_config(self) -> Dict[str, Any]:
        """Return current config as dictionary"""
        return vars(self.config)
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """Update config from dictionary"""
        for key, value in config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def get_name(self) -> str:
        """Return simulation name"""
        return "MyNewSimulation"
    
    def get_config_object(self):
        """Return config object"""
        return self.config
    
    def get_status_object(self):
        """Return status object"""
        return self.status
```

## Summary

1. Copy an existing simulation folder
2. Modify the 5 files (simulation.py, config.py, status.py, gui.py, __init__.py)
3. Register in main.py
4. Test imports and run
5. Use logging, clear names, short functions, and docstrings

**Remember**: The framework does the heavy lifting. You just write the simulation logic!
