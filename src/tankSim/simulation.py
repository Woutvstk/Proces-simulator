import time
from tankSim.configurationTS import configuration as configurationClass
from tankSim.status import status as statusClass


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

    """
    Update simulation values in function of current statues and config
    """

    def doSimulation(self, config: configurationClass, status: statusClass) -> None:
        """check if simRunning before changing any data"""
        if (status.simRunning == True):
            """If simulation (re)starts, set _lastRun to current time and skip update at time 0"""
            if (self._lastSimRunningState == False):
                self._lastRun = time.time()
                # remember sim was runnning during previous update
                self._lastSimRunningState = status.simRunning
                print("🚀 Simulation FIRST RUN - initializing timer")
                return

            """
            Calculate how much time has passed since lastRun to scale changes to process values
            Should be close to config.simulationInterval, but added for accuracy
            """
            self._timeSinceLastRun = time.time() - self._lastRun
            self._lastRun = time.time()
            
            # Debug every 10 cycles
            if not hasattr(self, '_debug_counter'):
                self._debug_counter = 0
            self._debug_counter += 1
            
            if self._debug_counter % 10 == 0:
                print(f"💧 doSimulation: valveIn={status.valveInOpenFraction:.2f}, valveOut={status.valveOutOpenFraction:.2f}, vol={status.liquidVolume:.1f}")
            
            # calculate new liquidVolume
            status.liquidVolume = min(
                status.liquidVolume+config.valveInMaxFlow*status.valveInOpenFraction * self._timeSinceLastRun, config.tankVolume)

            status.liquidVolume = max(
                status.liquidVolume-config.valveOutMaxFlow*status.valveOutOpenFraction * self._timeSinceLastRun, 0)

            # check if digital liquid level sensors are triggered
            status.digitalLevelSensorHighTriggered = (
                status.liquidVolume >= config.digitalLevelSensorHighTriggerLevel)
            status.digitalLevelSensorLowTriggered = (
                status.liquidVolume >= config.digitalLevelSensorLowTriggerLevel)

            if (status.liquidVolume > 0):
                # Calculate new liquid temperature
                status.liquidTemperature = min(
                    status.liquidTemperature+config.heaterMaxPower*status.heaterPowerFraction/config.liquidSpecificHeatCapacity/config.liquidSpecificWeight/status.liquidVolume * self._timeSinceLastRun, config.liquidBoilingTemp)
                status.liquidTemperature = max(
                    status.liquidTemperature-config.tankHeatLoss * 1 / config.liquidSpecificHeatCapacity/config.liquidSpecificWeight/status.liquidVolume * self._timeSinceLastRun, config.ambientTemp)
            else:
                status.liquidTemperature = 0

        else:
            # remember sim was NOT runnning during previous update
            self._lastSimRunningState = status.simRunning