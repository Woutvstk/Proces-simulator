import threading
import time


class tankSim:

    """
    Constructor
    """

    def __init__(self, name: str, tankVolume: int, flowValveIn: int, flowValveOut: int) -> None:
        self.name = name
        self.tankVolume = tankVolume
        self.flowValveIn = flowValveIn
        self.valveInOpen = False
        self.flowValveOut = flowValveOut
        self.valveOutOpen = False

        self.liquidVolume = 0

        self.simPaused = False
        self._simInterval = 0.1  # time interval in seconds to do simulation calculations
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

            if (self.valveInOpen):
                self.liquidVolume = min(
                    self.liquidVolume+self.flowValveIn * self._simInterval, self.tankVolume)
            if (self.valveOutOpen):
                self.liquidVolume = max(
                    self.liquidVolume-self.flowValveOut * self._simInterval, 0)

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
