"""
PID Tank Valve Simulation - Core simulation logic for tank with PID control.

Implements SimulationInterface with:
- Liquid level physics (inflow, outflow, conservation)
- Temperature dynamics (heating, cooling, thermal mass)
- Valve control (analog positioning)
- Level sensors (digital high/low switches)
- Time delay simulation for realistic sensor lag
- PID controller integration

External Libraries Used:
- time (Python Standard Library) - Timestamp tracking
- copy (Python Standard Library) - Deep copy for delay queue
- typing (Python Standard Library) - Type hints for clarity
"""

import time
import copy
import logging
from typing import Dict, Any
from simulations.PIDtankValve.config import configuration as configurationClass
from simulations.PIDtankValve.status import status as statusClass
from core.interface import SimulationInterface

logger = logging.getLogger(__name__)


class delayHandlerClass:
    def __init__(self):
        self.statusHistory = []  # status history list for delayed inputs
        self.lastWriteIndex = -1
        self.historySize = 0

    def queueAdd(self, newStatus: statusClass, config: configurationClass):
        status = copy.deepcopy(newStatus)
        status.timeStamp = time.time()
        # Calculate history size based on MAX delay to accommodate all delays
        self.historySize = max(config.liquidVolumeTimeDelay,
                               config.liquidTempTimeDelay)/config.simulationInterval
        # only write to list if at least one delay > 0
        if self.historySize > 0:
            self.lastWriteIndex += 1
            if self.lastWriteIndex > self.historySize:
                self.lastWriteIndex = 0

            if len(self.statusHistory) <= self.lastWriteIndex:
                self.statusHistory.append(status)
            else:
                self.statusHistory[self.lastWriteIndex] = status

    def getDelayedAttribute(self, config: configurationClass, status: statusClass, attrName: str):
        """
        Returns the most recent (newest) stored value of the requested attribute
        that is still older than the configured delay time.
        
        Each attribute uses its own delay time, independent of other attributes.
        """
        # Map attribute to config delay
        delayMap = {
            "valveInOpenFraction": config.liquidVolumeTimeDelay,
            "valveOutOpenFraction": config.liquidVolumeTimeDelay,
            "heaterPowerFraction": config.liquidTempTimeDelay,
            "timeStamp": config.liquidVolumeTimeDelay
        }

        if attrName not in delayMap:
            raise ValueError(f"Unknown delayed attribute: {attrName}")

        # If NO delays at all, return current value
        if config.liquidVolumeTimeDelay <= 0 and config.liquidTempTimeDelay <= 0:
            return getattr(status, attrName)
        
        # Get the specific delay for this attribute
        delayInSeconds = delayMap[attrName]
        
        # If this specific attribute has no delay, return current value
        if delayInSeconds <= 0:
            return getattr(status, attrName)
        
        # History exists and this attribute has a delay
        if len(self.statusHistory) > 0:
            # Calculate how many indices back we need to go for this specific attribute's delay
            delayInIndex = delayInSeconds / config.simulationInterval
            
            # Find the delayed status index (oldest value still within delay window)
            delayedStatusIndex = int((self.lastWriteIndex - delayInIndex + 1) % self.historySize)
            
            if len(self.statusHistory) > delayedStatusIndex:
                return getattr(self.statusHistory[delayedStatusIndex], attrName)
            else:
                return getattr(status, attrName)
        else:
            return getattr(status, attrName)


class simulation:

    """
    Constructor
    """

    def __init__(self, name: str) -> None:

        # name of the process
        self.name: str = name

        # internal variables
        self._lastRun = time.time()
        self._lastSimRunningState = False

        # delay handler
        self.delayHandler: delayHandlerClass = delayHandlerClass()

        self.delayedValveInOpenFraction = 0.0
        self.delayedValveOutOpenFraction = 0.0
        self.delayedHeaterPowerFraction = 0.0

    """
    Update simulation values in function of current statues and config
    """

    def doSimulation(self, config: configurationClass, status: statusClass) -> None:
        self.delayHandler.queueAdd(status, config)
        """check if simRunning before changing any data"""
        if (status.simRunning == True):
            """If simulation (re)starts, set _lastRun to current time and skip update at time 0"""
            if (self._lastSimRunningState == False):
                self._lastRun = time.time()
                # remember sim was runnning during previous update
                self._lastSimRunningState = status.simRunning
                return

            """
            Calculate how much time has passed since lastRun to scale changes to process values
            Should be close to config.simulationInterval, but added for accuracy
            """
            newDelayedValveInOpenFraction = self.delayHandler.getDelayedAttribute(
                config, status, "valveInOpenFraction")
            newDelayedValveOutOpenFraction = self.delayHandler.getDelayedAttribute(
                config,  status, "valveOutOpenFraction")
            newDelayedHeaterPowerFraction = self.delayHandler.getDelayedAttribute(
                config,  status, "heaterPowerFraction")

            if newDelayedValveInOpenFraction != None:
                self.delayedValveInOpenFraction = newDelayedValveInOpenFraction
            if newDelayedValveOutOpenFraction != None:
                self.delayedValveOutOpenFraction = newDelayedValveOutOpenFraction
            if newDelayedHeaterPowerFraction != None:
                self.delayedHeaterPowerFraction = newDelayedHeaterPowerFraction

            self._timeSinceLastRun = time.time() - self._lastRun
            self._lastRun = time.time()

            # calculate flowrates (delayed)
            status.flowRateIn = config.valveInMaxFlow * self.delayedValveInOpenFraction
            status.flowRateOut = config.valveOutMaxFlow * self.delayedValveOutOpenFraction

            # Debug every 10 cycles
            if not hasattr(self, '_debug_counter'):
                self._debug_counter = 0
            self._debug_counter += 1

            if self._debug_counter % 10 == 0:
                logger.debug(
                    f"doSimulation: valveIn={status.valveInOpenFraction:.2f}, valveOut={status.valveOutOpenFraction:.2f}, vol={status.liquidVolume:.1f}")

            # calculate new liquidVolume (net flow with proper clamping)
            net_flow = (status.flowRateIn - status.flowRateOut) * self._timeSinceLastRun
            status.liquidVolume = max(0, min(config.tankVolume, status.liquidVolume + net_flow))

            # check if digital liquid level sensors are triggered
            status.digitalLevelSensorHighTriggered = (
                status.liquidVolume >= config.digitalLevelSensorHighTriggerLevel)
            status.digitalLevelSensorLowTriggered = (
                status.liquidVolume >= config.digitalLevelSensorLowTriggerLevel)

            if (status.liquidVolume > 0):
                # Realistic thermal dynamics with non-linear response
                # ========================================================
                # This implements first-order thermal lag to simulate realistic
                # process behavior with "sponginess" instead of linear response.
                #
                # The key insight: thermal response is exponential, not linear.
                # We approach setpoint asymptotically, creating natural overshoot
                # prevention and realistic transient behavior.
                
                # Use effective minimum volume to avoid extreme rates near empty tank
                effective_volume = max(status.liquidVolume, 0.001)
                
                # Calculate thermal time constant (tau) in seconds
                # Larger volumes and higher heat loss = longer response time
                # This creates natural system damping
                thermal_time_constant = (config.liquidSpecificHeatCapacity * 
                                        config.liquidSpecificWeight * 
                                        effective_volume) / config.tankHeatLoss
                
                # Calculate heat input rate (Joules/second = Watts)
                heat_input_rate = config.heaterMaxPower * self.delayedHeaterPowerFraction
                
                # Calculate heat loss rate (proportional to temp difference)
                # This creates exponential cooling behavior
                temp_difference = status.liquidTemperature - config.ambientTemp
                heat_loss_rate = config.tankHeatLoss * temp_difference
                
                # Net heat rate (Watts)
                net_heat_rate = heat_input_rate - heat_loss_rate
                
                # Temperature change using exponential approach (first-order lag)
                # This prevents overshoot and creates realistic "spongy" response
                dT = (net_heat_rate / (config.liquidSpecificHeatCapacity * 
                      config.liquidSpecificWeight * effective_volume)) * self._timeSinceLastRun
                
                # Apply first-order lag filter for smooth transitions
                # The damping factor depends on thermal time constant
                lag_factor = self._timeSinceLastRun / (thermal_time_constant + self._timeSinceLastRun)
                dT_damped = dT * lag_factor
                
                # Update temperature with bounds
                new_temp = status.liquidTemperature + dT_damped
                status.liquidTemperature = max(
                    min(new_temp, config.liquidBoilingTemp),
                    config.ambientTemp
                )
            else:
                # When the tank is empty, temperature equals ambient
                status.liquidTemperature = config.ambientTemp

        else:
            # remember sim was NOT runnning during previous update
            self._lastSimRunningState = status.simRunning


class PIDTankSimulation(SimulationInterface):
    """
    PID Tank Valve Simulation implementing SimulationInterface.
    
    This wraps the original simulation class to provide a uniform interface
    for the simulation manager.
    """
    
    def __init__(self, name: str):
        """Initialize the PID tank simulation."""
        self.name = name
        self.config = configurationClass()
        self.status = statusClass()
        self._simulation = simulation(name)
    
    def start(self) -> None:
        """Start the simulation."""
        self.status.simRunning = True
    
    def stop(self) -> None:
        """Stop the simulation."""
        self.status.simRunning = False
    
    def reset(self) -> None:
        """Reset simulation to initial state."""
        self.status = statusClass()
        self._simulation = simulation(self.name)
    
    def update(self, dt: float) -> None:
        """
        Update simulation state.
        
        Args:
            dt: Time delta since last update (not used, internal timing used)
        """
        self._simulation.doSimulation(self.config, self.status)

    def get_name(self) -> str:
        """Get simulation name."""
        return self.name
    
    
    def get_status(self) -> Dict[str, Any]:
        """Get current simulation status as dictionary."""
        status_dict = {}
        for attr in self.status.importExportVariableList:
            if hasattr(self.status, attr):
                status_dict[attr] = getattr(self.status, attr)
        return status_dict
    
    def set_input(self, key: str, value: Any) -> None:
        """Set simulation input value."""
        if hasattr(self.status, key):
            setattr(self.status, key, value)
    
    def get_output(self, key: str) -> Any:
        """Get simulation output value."""
        if hasattr(self.status, key):
            return getattr(self.status, key)
        return None
    
    def get_config(self) -> Dict[str, Any]:
        """Get simulation configuration as dictionary."""
        config_dict = {}
        # Get all non-private attributes
        for key, value in self.config.__dict__.items():
            if not key.startswith('_'):
                config_dict[key] = value
        return config_dict
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """Update simulation configuration."""
        for key, value in config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def get_config_object(self):
        """Get the configuration object directly (for save/load)."""
        return self.config
    
    def get_status_object(self):
        """Get the status object directly (for save/load)."""
        return self.status

