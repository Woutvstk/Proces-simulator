import snap7
import snap7.util as s7util
import time
import logging

#Code succesfully tested with S7-1500/1200(G1-G2)/400/300/ET200 CPU in standard and advanced license(for the S7-1500)

# Optional: Suppress the verbose Snap7 logging during connection attempts
logging.getLogger('snap7.client').setLevel(logging.WARNING)

# This global variable will hold the active Snap7 client object once connected.
WORKING_CLIENT = None 

# Initializing global buffers for Read/Write operations.
# Note: These buffers must be large enough to cover the highest I/O address used.
# 40 bytes is chosen here to cover I/O addresses up to byte 39 (e.g., IW20 and IW32).
buffer_DI = bytearray(40)
buffer_DO = bytearray(40) 
buffer_AI = bytearray(40) 
buffer_AO = bytearray(40)

# --- PLC CLIENT CLASS ---
class PlcClient:
    """Class for managing the Snap7 connection and fundamental PLC communication."""

    def __init__(self, ip: str, rack: int, slot: int, tcpport: int = 102):
        """
        Initialize the PLC client parameters.
        """
        # --- ATTENTION: HARDCODED IP AND PORT FOR PLCSIM ---
        # The variables passed to __init__ are overridden below for a fixed setup.
        self.ip = "192.168.0.1" # HARDCODED IP. CHANGE THIS for real PLC (e.g., "192.168.0.1") or use "127.0.0.1" for NetToPLCSim.
        self.rack = rack
        self.slot = slot
        self.tcpport = 102 # HARDCODED PORT. Change to 102 for a real PLC, or keep 1024/1025/... for PLCSimS7.
        self.client = snap7.client.Client()

    def connect(self) -> bool:
        """
        Connects to the PLC. Tries alternative slots (0, 1, 2) if the initial attempt fails.
        """
        print(f"Attempting to connect to {self.ip}:{self.tcpport} (Rack {self.rack}, Slot {self.slot})...")
        initial_slot = self.slot
        
        # --- Initial Connection Attempt ---
        try:
            self.client.connect(self.ip, self.rack, self.slot, self.tcpport)
            if self.client.get_connected():
                print(f"✅ Successfully connected to S7 PLC at {self.ip} (Rack {self.rack}, Slot {self.slot})")
                return True
        except Exception as e:
            # --- Retry Logic for different S7 PLC Slots ---
            # Try alternate slots (0, 1, or 2) common for S7-300/400/1200 configurations.
            for i in [0, 1, 2]:
                if i != initial_slot:
                    try:
                        self.client.connect(self.ip, self.rack, i, self.tcpport)
                        if self.client.get_connected():
                            print(f"✅ Connected to S7 PLC at {self.ip} (Rack {self.rack}, alternative Slot {i})")
                            self.slot = i # Update instance slot to the successful one
                            return True
                    except Exception:
                        continue # Keep trying other slots
            
            # If all attempts failed
            print(f"❌ Connection failed after all attempts. Error: {e}")
            return False

    def disconnect(self) -> bool:
        """
        Disconnects from the PLC if the connection is currently active.
        """
        try:
            if self.client.get_connected():
                self.client.disconnect()
            return True
        except:
            return False

    def isConnected(self) -> bool:
        """
        Checks if the live connection to the PLC is still active.
        """
        if not self.client.get_connected():
            print("Connection lost to the PLC!")
            return False
        return True


# --- HELPER FUNCTIONS (RELY ON GLOBAL WORKING_CLIENT) ---

def get_connected_plc_client(ip: str, rack: int, slot: int) -> snap7.client.Client | None:
    """
    Instantiates and connects a PlcClient, returning the raw snap7.client object.
    """
    plc_instance = PlcClient(ip=ip, rack=rack, slot=slot)
    if plc_instance.connect():
        # Return the underlying snap7 client object for direct use in I/O functions
        return plc_instance.client
    return None


def SetDI(byte: int, bit: int, value: int):
    """Writes a Digital Input (I-zone/EB) bit to the PLC simulator."""
    # We write to the Input (I) zone, which is the EB (Peripheral Inputs) zone in Snap7.
    if WORKING_CLIENT and WORKING_CLIENT.get_connected() and 0 <= byte < len(buffer_DI) and 0 <= bit <= 7:
        
        # 1. Update the local buffer for the specific bit
        if value:
            buffer_DI[byte] |= (1 << bit)
        else:
            buffer_DI[byte] &= ~(1 << bit)
            
        try:
            # 2. Write the entire modified byte back to the PLC.
            # Snap7 doesn't have a direct eb_write_bit, so we write the whole byte.
            data_to_write = buffer_DI[byte:byte+1]
            WORKING_CLIENT.eb_write(start=byte, size=1, data=data_to_write)
            return int(bool(value))
        except Exception as e:
            # print(f"SetDI error: {e}")
            return -1 # Write failed
    return -1


def GetDO(byte: int, bit: int):
    """Reads a Digital Output (Q-zone/AB) bit from the PLC."""
    # We read from the Output (Q) zone, which is the AB (Peripheral Outputs) zone in Snap7.
    if WORKING_CLIENT and WORKING_CLIENT.get_connected() and byte >= 0 and 0 <= bit <= 7:
        try:
            # Read the byte containing the desired bit
            data = WORKING_CLIENT.ab_read(byte, 1)
            # Use s7util to extract the bit value
            return int(s7util.get_bool(data, 0, bit))
        except Exception as e:
            # print(f"GetDO error: {e}")
            return -1
    return -1


def SetAI(byte: int, value: int):
    """Writes an Analog Input (I-zone/EB) as a 16-bit INT."""
    # Check if client is connected and address is valid
    if WORKING_CLIENT and WORKING_CLIENT.get_connected() and byte >= 0:
        if -32768 <= value <= 32767: # Check for 16-bit INT range
            data = bytearray(2)
            s7util.set_int(data, 0, value)
            try:
                # Write 2 bytes (the INT) to the Peripheral Inputs
                WORKING_CLIENT.eb_write(start=byte, size=2, data=data)
                return value
            except Exception as e:
                # print(f"SetAI error: {e}")
                return -1
        print(f"Value {value} out of range for 16-bit INT.")
        return -1
    return -1


def GetAO(byte: int):
    """Reads an Analog Output (Q-zone/AB) as a 16-bit INT."""
    if WORKING_CLIENT and WORKING_CLIENT.get_connected() and byte >= 0:
        try:
            # Read 2 bytes (INT) from the Peripheral Outputs
            data = WORKING_CLIENT.ab_read(start=byte, size=2)
            return s7util.get_int(data, 0)
        except Exception as e:
            # print(f"GetAO error: {e}")
            return -1
    return -1

def print_status():
    """Prints the status of a selection of I/O addresses."""
    if not (WORKING_CLIENT and WORKING_CLIENT.get_connected()):
        print("No connected client available to read status.")
        return

    # --- DIGITAL I/O READS ---
    try:
        # Read two bytes to cover I0.0 through I1.7
        data_di = WORKING_CLIENT.eb_read(start=0, size=2)
        di_vals = [f"I{byte}.{bit}:{int(s7util.get_bool(data_di, byte, bit))}" for byte in range(2) for bit in range(8)]
    except Exception as e: 
        di_vals = [f"DI READ ERROR: {e}"]
    
    try:
        # Read two bytes to cover Q0.0 through Q1.7
        data_do = WORKING_CLIENT.ab_read(start=0, size=2)
        do_vals = [f"Q{byte}.{bit}:{int(s7util.get_bool(data_do, byte, bit))}" for byte in range(2) for bit in range(8)]
    except Exception as e: 
        do_vals = [f"DO READ ERROR: {e}"]

    # --- ANALOG I/O READS ---
    try:
        # Read 8 bytes to cover IW2, IW4, IW6, IW8 (4x INT = 8 bytes)
        data_ai = WORKING_CLIENT.eb_read(start=2, size=8)
        ai_vals = [f"IW{2 + i*2}:{s7util.get_int(data_ai, i*2)}" for i in range(4)]
    except Exception as e: 
        ai_vals = [f"AI READ ERROR: {e}"]
    
    try:
        # Read 8 bytes to cover QW2, QW4, QW6, QW8
        data_ao = WORKING_CLIENT.ab_read(start=2, size=8)
        ao_vals = [f"QW{2 + i*2}:{s7util.get_int(data_ao, i*2)}" for i in range(4)]
    except Exception as e: 
        ao_vals = [f"AO READ ERROR: {e}"]
    
    # --- OUTPUT STATUS ---
    print(f"DI: {' | '.join(di_vals)}")
    print(f"DO: {' | '.join(do_vals)}")
    print(f"AI: {' | '.join(ai_vals)}")
    print(f"AO: {' | '.join(ao_vals)}")
    print('-'*80)

# -------------------------------------------------------------------
# --- MAIN PROGRAM EXECUTION ---

if __name__ == "__main__":
    
    # --- CONFIGURE CONNECTION PARAMETERS ---
    # Note: These parameters are currently overridden by the hardcoded values in PlcClient.__init__
    IP_ADRES = "192.168.2.30"
    RACK = 0
    SLOT = 1 # Default for S7-1500, use 0 for S7-1200

    # 1. Establish the connection once and assign the raw client to the global variable
    WORKING_CLIENT = get_connected_plc_client(ip=IP_ADRES, rack=RACK, slot=SLOT)

    if WORKING_CLIENT:
        try:
            print("\nStarting continuous I/O cycle...")
            while True:
                # --- Digital I/O Writes (Simulating sensor inputs to the PLC's I-zone) ---
                SetDI(0,0,1) # I0.0 = 1 (Simulate a pushbutton press)
                SetDI(1,4,1) # I1.4 = 1
                SetDI(0,5,1) # I0.5 = 1 
                SetDI(1,5,1) # I1.5 = 1

                # --- Analog I/O Writes (Simulating analog sensor values) ---
                SetAI(2, 0)      # IW2 = 0
                SetAI(4, 255)    # IW4 = 255
                SetAI(6, -25000) # IW6 = -25000
                
                # Note: These addresses (IW20, IW32) might be outside the I/O image range 
                # of a standard PLCSIM setup, which will likely cause a Snap7 error
                # handled by returning -1 in the SetAI function.
                SetAI(20, 69) # IW20 = 69
                SetAI(32, 69) # IW32 = 69
                
                print_status()

                time.sleep(1)

        except KeyboardInterrupt:
            print("\nProgram stopped by user (Ctrl+C).")
        except Exception as e:
            print(f"\nA fatal communication error occurred: {e}")
        finally:
            # 3. Disconnect cleanly
            if WORKING_CLIENT and WORKING_CLIENT.get_connected():
                WORKING_CLIENT.disconnect()
                print("Disconnected from PLC.")
    else:
        print("\nCould not start the I/O cycle without a working PLC connection.")