import time
import copy
from tankSim.configuration import configuration as configurationClass
from tankSim.status import status as statusClass


class delayHandlerClass:
    def __init__(self):
        self.statusHistory = []  # status history list for delayed inputs
        self.lastWriteIndex = -1
        self.historySize = 0

    def queueAdd(self, newStatus: statusClass, config: configurationClass):
        status = copy.deepcopy(newStatus)
        status.timeStamp = time.time()
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

        if self.historySize > 0:
            delayInSeconds = delayMap[attrName]
            delayInIndex = delayInSeconds/config.simulationInterval
            delayedStatusIndex = int((self.lastWriteIndex -
                                      delayInIndex+1) % self.historySize)
            if len(self.statusHistory) > delayedStatusIndex:
                return getattr(self.statusHistory[delayedStatusIndex], attrName)
            else:
                return 0
        # all delays are 0
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
        """
        INPUT:  config (max flows, heater power, etc.)
                status (actuele actuator posities)
        
        OUTPUT: status (nieuwe liquidVolume, liquidTemperature)
        """
        self.delayHandler.queueAdd(status, config)
        """check if simRunning before changing any data"""
        if (status.simRunning == True):
            """If simulation (re)starts, set _lastRun to current time and skip update at time 0"""
            if (self._lastSimRunningState == False):
                self._lastRun = time.time()
                self._lastSimRunningState = status.simRunning
                print("Simulation FIRST RUN - initializing timer")
                return

            """Get delayed values"""
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

            # Debug every 10 cycles - TOON DELAYED VALUES!
            if not hasattr(self, '_debug_counter'):
                self._debug_counter = 0
            self._debug_counter += 1

            if self._debug_counter % 10 == 0:
                print(f"🔄 Simulation: valveIn={self.delayedValveInOpenFraction:.2f} (delayed), "
                    f"valveOut={self.delayedValveOutOpenFraction:.2f} (delayed), "
                    f"heater={self.delayedHeaterPowerFraction:.2f} (delayed), "
                    f"vol={status.liquidVolume:.1f}, temp={status.liquidTemperature:.1f}°C")

            # calculate new liquidVolume
            status.liquidVolume = min(
                status.liquidVolume + status.flowRateIn * self._timeSinceLastRun, config.tankVolume)

            status.liquidVolume = max(
                status.liquidVolume - status.flowRateOut * self._timeSinceLastRun, 0)

            # check if digital liquid level sensors are triggered
            status.digitalLevelSensorHighTriggered = (
                status.liquidVolume >= config.digitalLevelSensorHighTriggerLevel)
            status.digitalLevelSensorLowTriggered = (
                status.liquidVolume >= config.digitalLevelSensorLowTriggerLevel)

            if (status.liquidVolume > 0):
                # Calculate temperature CHANGE per cycle
                heater_increase = config.heaterMaxPower * self.delayedHeaterPowerFraction / (
                    config.liquidSpecificHeatCapacity * config.liquidSpecificWeight * status.liquidVolume
                ) * self._timeSinceLastRun
                
                heat_loss_decrease = config.tankHeatLoss / (
                    config.liquidSpecificHeatCapacity * config.liquidSpecificWeight * status.liquidVolume
                ) * self._timeSinceLastRun
                
                # Apply both heating and cooling
                new_temp = status.liquidTemperature + heater_increase - heat_loss_decrease
                
                # Clamp between ambient and boiling
                status.liquidTemperature = max(config.ambientTemp, min(new_temp, config.liquidBoilingTemp))
                
                # Debug temperature change every 50 cycles
                if self._debug_counter % 50 == 0:
                    print(f"🌡️  Temp: {status.liquidTemperature:.1f}°C (heater: +{heater_increase:.3f}, loss: -{heat_loss_decrease:.3f})")
            else:
                status.liquidTemperature = config.ambientTemp

        else:
            # remember sim was NOT runnning during previous update
            self._lastSimRunningState = status.simRunning