import clr
import os

# Connects to the softbus of a Siemens PLC simulator via an API DLL

class plcSimAPI:

    """Class for communication with a Siemens S7 PLC simulator via Simatic.Simulation.Runtime API"""

    def __init__(self):
        """Initialize the PLC simulator manager."""
        # Directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Path to the DLL from script_dir
        dll_path = os.path.join(script_dir, "Siemens.Simatic.Simulation.Runtime.Api.x64.dll")

        print(f"Trying to load DLL from: {dll_path}")
        if not os.path.exists(dll_path):
            raise FileNotFoundError(f"DLL not found: {dll_path}")

        # Import DLL
        clr.AddReference(dll_path)

        from Siemens.Simatic.Simulation.Runtime import SimulationRuntimeManager #type: ignore

        self.manager = SimulationRuntimeManager()
        self.simulation_instance = None

    def connect(self, instance_name: str | None = None) -> bool:
        """
        Connect to a PLC simulation instance.

        Parameters:
        instance_name (str | None): Name of the instance to connect to. If None, the first available instance will be used.

        Returns:
        bool: True if connected successfully, False otherwise.
        """
        instances = self.manager.RegisteredInstanceInfo

        if instance_name is not None:
            # Search for a specific instance
            for inst in instances:
                if inst.Name == instance_name:
                    try:
                        self.simulation_instance = self.manager.CreateInterface(inst.Name)
                        print(f"Interface created for instance: {inst.Name}")
                        print(f"OperatingState: {self.simulation_instance.OperatingState}")
                        return True
                    except Exception as e:
                        print(f"Error creating interface for {instance_name}: {e}")
                        return False
            print(f"Instance '{instance_name}' not found.")
            return False
        else:
            # No name specified: try the first available instance
            print(f"{'-'*10} No instance_name defined, trying first available instance {'-'*10}")
            for inst in instances:
                try:
                    self.simulation_instance = self.manager.CreateInterface(inst.Name)
                    if str(self.simulation_instance.OperatingState) == "Run":
                        print(f"{inst.Name} OperatingState = {self.simulation_instance.OperatingState}, connected successfully.")
                        return True
                    else:
                        print(f"{inst.Name} OperatingState = {self.simulation_instance.OperatingState}... trying next instance.") 
                except Exception:
                    continue
            print("No running instances found. Please check if a PLC simulator is running.")
            return False

    def isConnected(self) -> bool:
        """
        Check if a PLC simulation instance is connected.

        Returns:
        bool: True if connected, False otherwise.
        """
        try:
            if self.simulation_instance is not None:
                return True
            else:
                print("No simulation instance connected.")
                return False
        except Exception as e:
            print("Connection error:", e)
            return False
        
    def Disconnect(self, instance_name: str | None = None) -> bool:
        """
        Disconnect a PLC simulation instance.

        Parameters:
        instance_name (str | None): Name of the instance to disconnect. If None, all instances will be disconnected.

        Returns:
        bool: True if successfully disconnected, False otherwise.
        """
        instances = self.manager.RegisteredInstanceInfo

        if instance_name is not None:
            # Search for a specific instance
            for inst in instances:
                if inst.Name == instance_name:
                    try:
                        if hasattr(self, "simulation_instance") and self.simulation_instance is not None:
                            self.simulation_instance.Dispose()
                            self.simulation_instance = None
                        print(f"Interface disconnected for instance: {inst.Name}")
                        return True
                    except Exception as e:
                        print(f"Error disconnecting the interface for {instance_name}: {e}")
                        return False
            print(f"Instance '{instance_name}' not found.")
            return False
        else:
            # No name specified: try all available instances
            print(f"{'-'*10} No instance defined, disconnecting all interfaces {'-'*10}")
            success = False
            for inst in instances:
                try:
                    if hasattr(self, "simulation_instance") and self.simulation_instance is not None:
                        self.simulation_instance.Dispose()
                        self.simulation_instance = None
                    print(f"Disconnected instance: {inst.Name}")
                    success = True
                except Exception as e:
                    print(f"Could not disconnect {inst.Name}: {e}")
                    continue
            if not success:
                print("No running instances found. Please check if a PLC simulator is running.")
            return success     

    def SetDI(self, startByte: int, bit: int, value: int):
        """
        Set a digital input (DI) bit in the PLC input process image.

        Parameters:
        startByte (int): Byte index in the PLC input area (E/I).  
        bit (int): Bit position (0-7) within the byte.  
        value (int): Value to set (0 or 1, False or True).

        Returns:
        int: 0 or 1 if successful, -1 on error.
        """
        if self.isConnected():
            if startByte >= 0 and 0 <= bit < 8:
                self.simulation_instance.InputArea.WriteBit(startByte, bit, bool(value))
                return int(bool(value))
            return -1
        return -1
    
    def GetDO(self, startByte: int, bit: int) -> int:
        """
        Read a digital output (DO) bit from the PLC output process image.

        Parameters:
        startByte (int): Byte index in the PLC output area (A/Q).  
        bit (int): Bit position (0-7) within the byte.

        Returns:
        int: 0 or 1 if successful, -1 on error.
        """
        if self.isConnected():
            if startByte >= 0 and 0 <= bit <= 7:
                data = self.simulation_instance.OutputArea.ReadBit(startByte, bit)
                return int(data)
            return -1
        return -1

    def SetAI(self, byte: int, value: int) -> int:
        """
        Set an analog input (AI) value in the PLC input process image.

        Parameters:
        byte (int): Byte index in the PLC input area (E/I).  
        value (int | float): Analog value to set (0-65535).

        Returns:
        int: Value set, or -1 on error.
        """
        if self.isConnected():
            buffer_AI = bytearray(2)
            if byte >= 0:
                if isinstance(value, float):
                    val_int = int(round(value))
                else:
                    val_int = int(value)
                lowByte = val_int & 0xFF
                highByte = (val_int >> 8) & 0xFF
                buffer_AI[0] = highByte
                buffer_AI[1] = lowByte
                self.simulation_instance.InputArea.WriteBytes(byte, 2, buffer_AI)
                return val_int
            return -1
        return -1

    def GetAO(self, startByte: int) -> int:
        """
        Read an analog output (AO) value from the PLC output process image.

        Parameters:
        startByte (int): Byte index in the PLC output area (A/Q).

        Returns:
        int: Signed 16-bit value (-32768 to 32767).
        Returns -1 on error.
        """
        if self.isConnected():
            if startByte >= 0:
                data = self.simulation_instance.OutputArea.ReadBytes(startByte, 2)
                value = int.from_bytes(data, byteorder='big', signed=True)
                return value
        return -1

    def resetSendInputs(self, startByte: int, endByte: int):
        """
        Reset all input data sent to the PLC (DI, AI).

        Parameters:
        startByte (int): Start byte index to reset.  
        endByte (int): End byte index to reset.
        """
        if self.isConnected():
            if startByte >= 0 and endByte > startByte:
                size = endByte - startByte + 1
                empty_buffer = bytearray(size)
                self.simulation_instance.InputArea.WriteBytes(startByte, size, empty_buffer)
