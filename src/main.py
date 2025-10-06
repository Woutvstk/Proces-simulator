from processSim.tankSim import tankSim
from plcCom.plcModBusTCP import plcModBusTCP
from plcCom.plcS7 import plcS7
import time

"""Initialize process0 object"""

process0 = tankSim("process0", 2000, 250, 135)
process0.simStart()

""""Initialize plc communication object"""


# remember at what time we started
startTime = time.time()


while True:
    # print out the current time since start and the current liquid level
    print(
        f"At time: {int(time.time() - startTime)}, Current liquid level: {int(process0.liquidVolume)}")

    # only print out status every second
    time.sleep(1)

    # during the first 10 seconds: let liquid flow in the tank
    if ((time.time() - startTime) < 10):
        process0.valveInOpen = True
        process0.valveOutOpen = False

    # during 10 to 20 seconds: let liquid flow out of the tank
    elif (10 < (time.time() - startTime) < 20):
        process0.valveInOpen = False
        process0.valveOutOpen = True

    # after 20 close both valves
    else:
        process0.valveInOpen = False
        process0.valveOutOpen = False
