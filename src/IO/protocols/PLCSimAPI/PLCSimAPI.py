import clr
import os

# Connects to the softbus of a Siemens PLC simulator via an API DLL
# Only for 1500 simulated PLC's with an advanced license!


class plcSimAPI:
    analogMax = 32767  # Max value for signed 16-bit integer

    """
    Class for communication with a Siemens S7 PLC simulator via the
    Simatic.Simulation.Runtime API (requires IronPython/Python .NET for clr import).
    """

    def __init__(self):
        """
        Initialize the PLC simulator manager and attempt to load the required DLL.
        """
        self.manager = None
        self.simulation_instance = None

        try:
            # Determine the directory of the current script
            script_dir = os.path.dirname(os.path.abspath(__file__))

            # Construct the absolute path to the API DLL
            dll_path = os.path.join(
                script_dir, "Siemens.Simatic.Simulation.Runtime.Api.x64.dll")

            print(f"Attempting to load DLL from: {dll_path}")
            if not os.path.exists(dll_path):
                raise FileNotFoundError(f"Required DLL not found: {dll_path}")

            # Import the DLL using the Common Language Runtime (CLR) bridge
            clr.AddReference(dll_path)

            # Import the necessary class after the assembly is loaded
            from Siemens.Simatic.Simulation.Runtime import SimulationRuntimeManager  # type: ignore

            self.manager = SimulationRuntimeManager()

        except ImportError as e:
            # This error is common if not running in a CLR-compatible environment (e.g., standard CPython without pythonnet)
            print(f"ImportError: Could not import 'clr'. This module requires pythonnet (clr) to bridge to the C# DLL.")
            print(f"Original error: {e}")
        except Exception as e:
            print(f"Error during initialization or DLL loading: {e}")

    # --- Connection Management ---

    def connect(self, instance_name: str | None = None) -> bool:
        """
        Connect to a running PLC simulation instance using the SimulationRuntimeManager.

        Parameters:
        instance_name (str | None): The specific name of the instance to connect to. 
                                    If None, tries to connect to the first running instance.

        Returns:
        bool: True if connected successfully, False otherwise.
        """
        if self.manager is None:
            print("Manager is not initialized. Check DLL loading errors.")
            return False

        try:
            instances = self.manager.RegisteredInstanceInfo

            if instance_name is not None:
                # Search for a specific instance name
                for inst in instances:
                    if inst.Name == instance_name:
                        try:
                            self.simulation_instance = self.manager.CreateInterface(
                                inst.Name)
                            print(
                                f"Interface created for instance: {inst.Name}")
                            print(
                                f"Operating State: {self.simulation_instance.OperatingState}")
                            return True
                        except Exception as e:
                            print(
                                f"Error creating interface for {instance_name}: {e}")
                            return False
                print(f"Instance '{instance_name}' not found.")
                return False
            else:
                # Try connecting to the first available running instance
                print(
                    "-" * 10 + " No instance_name provided, trying first available instance " + "-" * 10)
                for inst in instances:
                    try:
                        self.simulation_instance = self.manager.CreateInterface(
                            inst.Name)

                        # Only connect if the PLC is in Run state for reliable I/O
                        if str(self.simulation_instance.OperatingState) == "Run":
                            print(
                                f"{inst.Name} OperatingState = Run, connected successfully.")
                            return True
                        else:
                            print(
                                f"{inst.Name} OperatingState = {self.simulation_instance.OperatingState}... skipping and trying next instance.")
                            self.simulation_instance = None  # Dispose of non-Run interface
                    except Exception as e:
                        print(
                            f"Error in connection loop for instance {inst.Name}: {e}")
                        self.simulation_instance = None
                        continue
                print(
                    "No running instances found. Please ensure a PLC simulator is active.")
                return False
        except Exception as e:
            print(f"Error in connect procedure: {e}")
            return False

    def isConnected(self) -> bool:
        """
        Check if the connection to the simulation instance interface is active.

        Returns:
        bool: True if connected, False otherwise.
        """
        try:
            if self.simulation_instance is not None:
                # Can optionally check simulation_instance.OperatingState here for Run mode
                return True
            else:
                # print("No simulation instance connected.")
                return False
        except Exception as e:
            print(f"Error in isConnected check: {e}")
            return False

    def disconnect(self, instance_name: str | None = None) -> bool:
        """
        Dispose of the active simulation interface. 
        Note: The underlying simulation (PLCSIM) remains running.

        Parameters:
        instance_name (str | None): (Ignored if no specific instance needed for disposal).

        Returns:
        bool: True if disconnection was successful or if no connection was active, False on error.
        """
        if self.simulation_instance is None:
            return True  # Already disconnected

        try:
            # Dispose of the COM/API object
            self.simulation_instance.Dispose()
            self.simulation_instance = None
            print("Successfully disconnected and disposed of the simulation interface.")
            return True
        except Exception as e:
            print(f"Error disconnecting the interface: {e}")
            return False

    # --- Data Access Methods (Based on Snap7 style for consistency) ---

    def SetDI(self, byte: int, bit: int, value: int) -> int:
        """
        Set a digital input (DI) bit in the PLC input area (I/E).

        Parameters:
        byte (int): Byte index (start byte).
        bit (int): Bit position (0–7).
        value (int): 1 (True) or 0 (False) to set the bit.

        Returns:
        int: The value set (1/0), or -1 on error.
        """
        try:
            if self.isConnected():
                if byte >= 0 and 0 <= bit < 8:
                    # The API method takes a boolean
                    self.simulation_instance.InputArea.WriteBit(
                        byte, bit, bool(value))
                    return int(bool(value))
                return -1
            return -1
        except Exception as e:
            print(f"Error in SetDI: {e}")
            return -1

    def GetDO(self, byte: int, bit: int) -> int:
        """
        Read a digital output (DO) bit from the PLC output area (Q/A).

        Parameters:
        byte (int): Byte index (start byte).
        bit (int): Bit position (0–7).

        Returns:
        int: 1 or 0 if successful, or -1 on error.
        """
        try:
            if self.isConnected():
                if byte >= 0 and 0 <= bit <= 7:
                    # The API method returns a boolean
                    data = self.simulation_instance.OutputArea.ReadBit(
                        byte, bit)
                    return int(data)
                return -1
            return -1
        except Exception as e:
            print(f"Error in GetDO: {e}")
            return -1

    def SetAI(self, byte: int, value: int) -> int:
        """
        Set an analog input (AI) value as a 16-bit word in the PLC input area (I/E).
        The value is converted to a byte array (Big Endian) before writing.

        Parameters:
        byte (int): Start byte index.
        value (int | float): Analog value (typically 0–27648 or 0-32767).

        Returns:
        int: The integer value set, or -1 on error.
        """
        try:
            if self.isConnected():
                if byte >= 0:

                    # Round and cast to integer
                    val_int = int(round(value)) if isinstance(
                        value, float) else int(value)

                    # Manually convert integer to S7 Big Endian bytearray (UINT/INT format)
                    buffer_AI = bytearray(2)
                    lowByte = val_int & 0xFF
                    highByte = (val_int >> 8) & 0xFF
                    buffer_AI[0] = highByte  # S7 uses high byte first
                    buffer_AI[1] = lowByte

                    # The API takes a byte array
                    self.simulation_instance.InputArea.WriteBytes(
                        byte, 2, buffer_AI)
                    return val_int
                return -1
            return -1
        except Exception as e:
            print(f"Error in SetAI: {e}")
            return -1

    def GetAO(self, startByte: int) -> int:
        """
        Read an analog output (AO) value as a 16-bit word (INT) from the PLC output area (Q/A).

        Parameters:
        startByte (int): Start byte index.

        Returns:
        int: Signed 16-bit value (-32768–32767), or -1 on error.
        """
        try:
            if self.isConnected():
                if startByte >= 0:
                    # The API returns a CLR byte array (System.Array[System.Byte])
                    data = self.simulation_instance.OutputArea.ReadBytes(
                        startByte, 2)

                    # Convert the CLR byte array back to a Python byte object
                    # and then interpret it as a signed integer (Big Endian)
                    python_data = bytes(data)
                    value = int.from_bytes(
                        python_data, byteorder='big', signed=True)
                    return value
                return -1
            return -1
        except Exception as e:
            print(f"Error in GetAO: {e}")
            return -1

    def SetDO(self, byte: int, bit: int, value: int) -> int:
        """
        Set a digital output (DO) bit in the PLC output area (Q/A).

        Parameters:
        byte (int): Byte index (start byte).
        bit (int): Bit position (0–7).
        value (int): 1 (True) or 0 (False) to set the bit.

        Returns:
        int: The value set (1/0), or -1 on error.
        """
        try:
            if self.isConnected():
                if byte >= 0 and 0 <= bit < 8:
                    self.simulation_instance.OutputArea.WriteBit(
                        byte, bit, bool(value))
                    return int(bool(value))
                return -1
            return -1
        except Exception as e:
            print(f"Error in SetDO: {e}")
            return -1

    def SetAO(self, byte: int, value: int) -> int:
        """
        Set an analog output (AO) value as a 16-bit word in the PLC output area (Q/A).
        The value is converted to a byte array (Big Endian) before writing.

        Parameters:
        byte (int): Start byte index.
        value (int | float): Analog value (typically -32768–32767).

        Returns:
        int: The integer value set, or -1 on error.
        """
        try:
            if self.isConnected():
                if byte >= 0:
                    # Round and cast to integer
                    val_int = int(round(value)) if isinstance(
                        value, float) else int(value)

                    # Handle negative values (two's complement)
                    if val_int < 0:
                        val_int = val_int & 0xFFFF

                    # Manually convert integer to S7 Big Endian bytearray
                    buffer_AO = bytearray(2)
                    lowByte = val_int & 0xFF
                    highByte = (val_int >> 8) & 0xFF
                    buffer_AO[0] = highByte  # S7 uses high byte first
                    buffer_AO[1] = lowByte

                    self.simulation_instance.OutputArea.WriteBytes(
                        byte, 2, buffer_AO)
                    return val_int
                return -1
            return -1
        except Exception as e:
            print(f"Error in SetAO: {e}")
            return -1

    def resetSendInputs(self, startByte: int, endByte: int) -> bool:
        """
        Reset a range of input bytes (DI/AI) by writing zero to the entire range.

        Parameters:
        startByte (int): Start byte index to reset.
        endByte (int): End byte index to reset (inclusive).

        Returns:
        bool: True if successful, False otherwise.
        """
        try:
            if self.isConnected():
                if startByte >= 0 and endByte >= startByte:
                    size = endByte - startByte + 1
                    empty_buffer = bytearray(size)
                    self.simulation_instance.InputArea.WriteBytes(
                        startByte, size, empty_buffer)
                    return True
                return False
            return False
        except Exception as e:
            print(f"Error in resetSendInputs: {e}")
            return False

    def resetSendOutputs(self, startByte: int, endByte: int) -> bool:
        """
        Reset a range of output bytes (DO/AO) by writing zero to the entire range.

        Parameters:
        startByte (int): Start byte index to reset.
        endByte (int): End byte index to reset (inclusive).

        Returns:
        bool: True if successful, False otherwise.
        """
        try:
            if self.isConnected():
                if startByte >= 0 and endByte >= startByte:
                    size = endByte - startByte + 1
                    empty_buffer = bytearray(size)
                    self.simulation_instance.OutputArea.WriteBytes(
                        startByte, size, empty_buffer)
                    print(f"Output area reset: bytes {startByte}-{endByte}")
                    return True
                return False
            return False
        except Exception as e:
            print(f"Error in resetSendOutputs: {e}")
            return False
