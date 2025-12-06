from processSim.tankSim import tankSim
from plcCom.plcModBusTCP import plcModBusTCP
from plcCom.plcS7 import plcS7
from plcCom.logoS7 import logoS7
from plcCom.PLCSimAPI import plcSimAPI
from plcCom.PLCSimS7 import plcSimS7
from processSim.configuration import configurationClass
from processSim.status import statusClass
from User_Interface.GUI import GuiClass
from processSim.UpdatePLCData import updateDataClass
import time

"""Initialize configuration instance with default parameters"""
config = configurationClass()

"""Initialize configuration instance with default parameters"""
status = statusClass()

"""Initialize updateData instance"""
PLCdata = updateDataClass() 

"""Initialize process0 object"""
process0 = tankSim("process0")

"""Initialize Gui object only if main"""
Gui0 = None
validPlcConnection: bool = False
print("creating gui class...")
Gui0 = GuiClass()

# remember at what time we started
startTime = time.time()

def tryConnectToPlc():
    global config, validPlcConnection, PlcCom  # creates a global var inside a function (normally local)
    """"Initialize plc communication object"""
    if config.plcProtocol == "ModBusTCP":
        PlcCom = plcModBusTCP(config.plcIpAdress, config.plcPort)
    elif config.plcProtocol == "PLC S7-1500/1200/400/300":
        PlcCom = plcS7(config.plcIpAdress,
                       config.plcRack, config.plcSlot,config.plcPort)
    elif config.plcProtocol == "logo!":
        PlcCom = logoS7(config.plcIpAdress,
                        config.tsapLogo, config.tsapServer)
    elif config.plcProtocol == "PLCSim advanced S7-1500": #included since it working principle is different the the PLCsimS7 and might be an alternative if issues persist
        PlcCom = plcSimAPI()
    elif config.plcProtocol == "PLCsim S7-1500/1200(G1-G2)/400/300/ET200 CPU":
        PlcCom = plcSimS7(config.plcIpAdress,
                       config.plcRack, config.plcSlot,config.plcPort)
    else:
        print("Error: no valid plcProtocol")

    '''connect/reconnect'''
    if PlcCom.isConnected():
        validPlcConnection = True
    else:
        if PlcCom.connect():  # run connect, returns True/False
            validPlcConnection = True
            PlcCom.resetSendInputs(config.lowestByte, config.highestByte) 
        else:
            validPlcConnection = False


# remember when last update was done
timeLastUpdate = 0

tryConnectToPlc()  # create initial PlcCom instance


# main loop only runs if this file is run directly
if __name__ == "__main__":
    
    # Use a try block for the main execution logic
    try:
        while True:

            """Check for connect command from gui and tryConnect"""
            if (config.tryConnect == True):  # check connection status
                Gui0.updateData(config, status)
                validPlcConnection = False
                config.tryConnect = False
                print(
                    f"Try connection to PLC at IP: {config.plcIpAdress} using protocol: {config.plcProtocol}")
                tryConnectToPlc()  # updates validPlcConnection

            """Get process control from plc or gui (config.plcGuiControl)"""
            # throttle calculations and data exchange between plc, process and gui
            if ((time.time() - timeLastUpdate) > config.simulationInterval):

                """
                Get process control from plc or gui
                PlcCom.updateData() and Gui0.updateData() check whether to change the status using config.plcGuiControl
                """
                # only try to contact plc if there is a connection
                if (validPlcConnection):
                    PLCdata.updateData(PlcCom,config, status)
                else:
                    # if control is plc but no plc connection, pretend plc outputs are all 0
                    PLCdata.resetOutputs(config, status)

                """Update process values"""
                process0.updateData(config, status)
                """send new process status to gui"""
                Gui0.updateData(config, status)

                # print out the current time since start and status
                # print(f"Time: {int(time.time() - startTime)}, simRunning: {status.simRunning}, Liquid level: {int(status.liquidVolume)}, Liquid temp: {int(status.liquidTemperature)}")
                # print(f"Time: {int(time.time() - startTime)}, simRunning: {status.simRunning}, Liquid level: {int(status.liquidVolume)}, Liquid temp: {int(status.liquidTemperature)}")
                timeLastUpdate = time.time()

            # stop program if gui is closed
            if (config.doExit):
                # We break the loop; cleanup is guaranteed by the 'finally' block below.
                break 

            # always update gui for responsive buttons/input
            if Gui0 is not None:
                Gui0.updateGui()

    # Capture keyboard interrupt (Ctrl+C) for graceful shutdown
    except KeyboardInterrupt:
        print("\nApplication manually interrupted by user.")
        
    # Capture other potential exceptions
    except Exception as e:
        print(f"\nFATAL ERROR: The application encountered an unexpected error: {e}")
        
    # The 'finally' block ensures cleanup is performed on ANY exit.
    finally:
        # Check if PlcCom object exists before trying to disconnect
        if 'PlcCom' in globals():
            print("\nInitiating shutdown of PLC communication and server process...")
            # This calls PlcCom.disconnect(), which terminates NetToPLCSim.exe <--------------
            PlcCom.disconnect() 
        print("Application successfully terminated.")