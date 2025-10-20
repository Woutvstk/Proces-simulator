import threading
import time


class tankSim:

    """
    Constructor
    """

    def __init__(self, name: str, tankVolume: int, valveInMaxFlow: float, valveOutMaxFlow: float, heaterMaxPower: float, tankHeatLoss: float, ambientTemp: float) -> None:

        # name of the process
        self.name: str = name

        # environment temperature
        self.ambientTemp: float = ambientTemp

        # parameters of the tank
        self.tankVolume: int = tankVolume
        self.tankHeatLoss: float = tankHeatLoss

        # valve IN settings
        self.valveInMaxFlow: float = valveInMaxFlow
        self.valveInOpenFraction: float = 0

        # valve OUT settings
        self.valveOutMaxFlow: float = valveOutMaxFlow
        self.valveOutOpenFraction: float = 0

        # heating element settings
        self.heaterMaxPower: float = heaterMaxPower
        self.heaterPowerFraction: float = 0

        # digital level sensor settings
        self.digitalLevelSensorLowTriggered: bool = False
        self.digitalLevelSensorLowTriggerLevel: int = 0.1*tankVolume  # default at 10%

        self.digitalLevelSensorHighTriggered: bool = False
        self.digitalLevelSensorHighTriggerLevel: int = 0.9*tankVolume  # default at 90%

        # liquid parameters

        self.liquidVolume = 0
        # specific heat capacity in Joeles/Kg*°C (4186 for water)
        self.liquidSpecificHeatCapacity: float = 4186
        # specific weight in kg per liter (water: 1)
        self.liquidSpecificWeight: float = 1
        # initialize liquid temp at ambient
        self.liquidTemperature = self.ambientTemp
        # boiling temperature of liquid (water: 100)
        self.liquidBoilingTemp = 100

        # simulation settings
        self.simPaused = False

        # internal variables
        self._simInterval = 1  # time interval in seconds to do simulation calculations
        self._stopThread = False
        self._thread = threading.Thread(
            target=self._run, args=(), daemon=True)

    """
    Main proces that does the simulating
    """

    def _run(self):
        while True:
            time.sleep(self._simInterval)
            if (self._stopThread):
                print(f"Now stopping thread of {self.name}")
                break
            if (self.simPaused):
                continue

            # calculate new liquidVolume
            self.liquidVolume = min(
                self.liquidVolume+self.valveInMaxFlow*self.valveInOpenFraction * self._simInterval, self.tankVolume)

            self.liquidVolume = max(
                self.liquidVolume-self.valveOutMaxFlow*self.valveOutOpenFraction * self._simInterval, 0)

            # check if digital liquid level sensors are triggered
            self.digitalLevelSensorHighTriggered = (
                self.liquidVolume >= self.digitalLevelSensorHighTriggerLevel)
            self.digitalLevelSensorLowTriggered = (
                self.liquidVolume >= self.digitalLevelSensorLowTriggerLevel)

            if (self.liquidVolume > 0):
                # Calculate new liquid temperature
                self.liquidTemperature = min(
                    self.liquidTemperature+self.heaterMaxPower*self.heaterPowerFraction/self.liquidSpecificHeatCapacity/self.liquidSpecificWeight/self.liquidVolume * self._simInterval, self.liquidBoilingTemp)
                self.liquidTemperature = max(
                    self.liquidTemperature-self.tankHeatLoss * 1 / self.liquidSpecificHeatCapacity/self.liquidSpecificWeight/self.liquidVolume * self._simInterval, self.ambientTemp)
            else:
                self.liquidTemperature = 0

    """
    Member functions
    """

    """
    Simulation Functions
    """

    # start simulation thread
    def simStart(self) -> None:
        self._stopThread = False
        self._thread.start()

    # stop simulation thread, must be called before deleting instance
    def simStop(self) -> None:
        self._stopThread = True

    # pause simulation calculations
    def simPause(self) -> None:
        self.simPaused = True

    # continue simulation calculation after being paused
    def simContinue(self) -> None:
        self.simPaused = False
