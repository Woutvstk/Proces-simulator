# Getting Started - Adding Your Own Simulation

## What You Need to Know

You should be comfortable with basic Python. If you can write classes and functions, you're good to go. The framework handles all the PLC communication and GUI stuff - you just write the simulation logic.

## The 5 Files Every Simulation Needs

```
simulations/your_sim_name/
├── __init__.py          # Just copy from an existing sim
├── simulation.py        # Your main logic lives here
├── config.py            # Parameters users can tweak
├── status.py            # Current state (temps, levels, etc)
└── gui.py               # Visual widget (optional)
```

## Easiest Way to Start

Copy an existing simulation and modify it:

```bash
cd src/simulations/
cp -r PIDtankValve MyNewSim
cd MyNewSim
# Now edit the files
```

## What Goes in Each File

### simulation.py - The Main Logic

Your simulation class needs these methods. The framework calls them automatically:

```python
from core.interface import SimulationInterface

class MyNewSim(SimulationInterface):
    def start(self):
        # Called when user hits Start button
        pass

    def stop(self):
        # Called when user hits Stop button
        pass

    def reset(self):
        # Reset everything to initial state
        pass

    def update(self, dt):
        # Called every simulation cycle (usually 100ms)
        # dt = time since last update in seconds
        # This is where your physics/logic goes
        pass

    def get_name(self):
        return "MyNewSim"
```

The `update()` method is where you put your simulation logic. Read inputs from `self.status`, do your calculations, write outputs back to `self.status`.

### config.py - Settings

Put anything users might want to change here:

```python
class configuration:
    def __init__(self):
        self.max_speed = 100.0          # Max speed in m/s
        self.acceleration = 2.0         # Acceleration in m/s²
        self.simulationInterval = 0.1   # How often to update

        # IO addresses for PLC communication
        self.DIStart = {"byte": 0, "bit": 0}  # Start button
        self.AQSpeed = {"byte": 2}            # Speed output
```

### status.py - Current State

Everything that changes during the simulation:

```python
class status:
    def __init__(self):
        self.current_speed = 0.0
        self.is_moving = False
        self.sim_running = False

        # Values from PLC/GUI
        self.start_command = False
        self.target_speed = 0.0
```

### gui.py - Visualization (Optional)

PyQt5 widget to show your simulation visually. Check out PIDtankValve/gui.py for examples of SVG graphics and real-time updates.

## Register Your Simulation

Edit `src/main.py`:

```python
# Add import
from simulations.MyNewSim.simulation import MyNewSim

# In main(), add registration
sim_mgr.register_simulation('MyNewSim', MyNewSim)
```

That's it. Now your simulation appears in the nav menu.

## Quick Test

```bash
# Check for syntax errors
python -m py_compile src/simulations/MyNewSim/simulation.py

# Test import
cd src
python -c "from simulations.MyNewSim.simulation import MyNewSim; print('Works!')"

# Run the app
python main.py
```

## Common Gotchas

**Simulation doesn't appear in list**
→ Did you register it in main.py?

**"ModuleNotFoundError"**
→ File names must be exactly: simulation.py, config.py, status.py, gui.py

**"Can't instantiate abstract class"**
→ You're missing required methods from SimulationInterface

**Nothing in the logs**
→ Use `logger.info()` instead of `print()`

## Logging the Right Way

```python
import logging
logger = logging.getLogger(__name__)

# Use these instead of print()
logger.info("Important stuff users should see")
logger.debug("Detailed info for debugging")
logger.error("Something broke")
```

Debug messages only show when you're actively debugging. Info/error messages always show.

## Writing Good Code (Quick Tips)

**Use descriptive names:**

```python
# Meh
temp = 5
data = process(temp)

# Better
tank_capacity_liters = 5
current_volume = calculate_volume(tank_capacity_liters)
```

**Keep functions short:**
If a function is getting huge, split it up:

```python
def update(self, dt):
    self._update_physics(dt)
    self._update_sensors()
    self._check_limits()
```

**Add docstrings where helpful:**

```python
def calculate_flow(valve_opening, pressure):
    """
    Calculate flow rate through valve.

    valve_opening: 0.0 (closed) to 1.0 (fully open)
    pressure: Pressure difference in bar

    Returns flow rate in L/s
    """
    return valve_opening * pressure * 10.0
```

## Minimal Template

Here's the bare minimum `simulation.py`:

```python
import logging
from core.interface import SimulationInterface
from .config import configuration
from .status import status

logger = logging.getLogger(__name__)


class MyNewSim(SimulationInterface):
    def __init__(self):
        self.config = configuration()
        self.status = status()
        self._running = False

    def start(self):
        self._running = True
        logger.info("Simulation started")

    def stop(self):
        self._running = False

    def reset(self):
        self.status = status()

    def update(self, dt):
        if not self._running:
            return

        # Your logic here
        # Example: simple acceleration
        if self.status.start_command:
            self.status.current_speed += self.config.acceleration * dt
            self.status.current_speed = min(
                self.status.current_speed,
                self.config.max_speed
            )

    def get_status(self):
        return vars(self.status)

    def get_config(self):
        return vars(self.config)

    def set_config(self, config_dict):
        for key, value in config_dict.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def get_name(self):
        return "MyNewSim"

    def get_config_object(self):
        return self.config

    def get_status_object(self):
        return self.status
```

## Need More Examples?

Look at the existing simulations:

- **PIDtankValve/** - Complex physics with temperature and level control
- **conveyor/** - Simpler example (if it exists)

Check **ARCHITECTURE.md** for the big picture of how everything fits together.

## Summary

1. Copy an existing simulation folder
2. Edit the 5 files with your logic
3. Register in main.py
4. Test and run

The framework handles PLC communication, GUI, IO mapping, save/load, and all the infrastructure. You just write the simulation update() logic.
