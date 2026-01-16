import snap7
import snap7.util as s7util
import subprocess
import os
import time
import socket
import configparser
import sys # Required for PyInstaller compatibility

#Code succesfully tested with S7-1500/1200(G1-G2)/400/300/ET200 CPU in standard and advanced license(for the S7-1500)

class plcSimS7:
    analogMax = 32767  # Max value for signed 16-bit integer
    """
    Class for communication with a Siemens S7 PLC using Snap7,
    integrated with NetToPLCSim server management for simulation environments.
    """

    # --- Static Helper Methods ---

    def _get_base_dir(self):
        """
        Determines the base directory for file paths.
        Uses sys._MEIPASS when running as a compiled PyInstaller EXE.
        """
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running in a PyInstaller bundle
            return os.path.dirname(sys.executable) # Assume same directory as the main EXE
        else:
            # Running as a normal Python script
            return os.path.dirname(os.path.abspath(__file__))

    # --- Class-level Configuration for NetToPLCSim ---

    # Call the static method once via None to get the base path
    _BASE_DIR = _get_base_dir(None) 
    _NETTOPLCSIM_DIR = os.path.join(_BASE_DIR, "NetToPLCsim")
    NETTOPLCSIM_EXE = os.path.join(_NETTOPLCSIM_DIR, "NetToPLCsim.exe")
    NETTOPLCSIM_INI = os.path.join(_NETTOPLCSIM_DIR, "configuration.ini")
    
    # Configuration for port retry logic
    START_PORT = 1024 
    PORT_TRY_LIMIT = 3 
    
    # Wait time for server startup verification
    MAX_SERVER_START_WAIT = 2.0
    POLL_INTERVAL = 0.05 

    # --- Initialization ---

    def __init__(self, ip: str, rack: int, slot: int, tcpport: int = 1024, network_adapter: str = "auto"):
        """
        Initialize the PLC client with IP, rack, slot, and TCP port.

        Parameters:
        ip (str): IP address of the PLC (Note: Hardcoded to 127.0.0.1 for NetToPLCSim communication)
        rack (int): Rack number of the PLC
        slot (int): Slot number of the PLC
        tcpport (int): TCP port for the connection (default: 1024, will be dynamically set by NetToPLCSim)
        network_adapter (str): Network adapter to use ("auto" or adapter name)
        """
        # Snap7 connects to the NetToPLCSim proxy, which is always local
        self.ip = "127.0.0.1" 
        self.rack = rack
        self.slot = slot
        # Initial port, will be updated by _start_server with the actual listening port
        self.tcpport = plcSimS7.START_PORT 
        self.network_adapter = network_adapter
        self.client = snap7.client.Client()
        self._server_process = None
        self.actual_server_port = None 

    # --- Internal Server Management Methods ---

    def _is_server_listening(self, port: int, timeout: float = 0.05) -> bool:
        """Checks if a service is listening on the specified port."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect(('127.0.0.1', port))
            return True
        except (socket.error, ConnectionRefusedError):
            return False
        finally:
            try:
                s.close()
            except:
                pass

    def _update_ini_file(self, plcsim_ip: str = "192.168.0.1") -> bool:
        """
        Dynamically writes the NetToPLCSim configuration, including the port range, to the INI file.
        """
        try:
            ini_dir = os.path.dirname(self.NETTOPLCSIM_INI)
            if not os.path.exists(ini_dir):
                print(f"Creating directory: {ini_dir}")
                os.makedirs(ini_dir, exist_ok=True)
            
            config = configparser.ConfigParser()
            
            ini_config = {
                'NetToPLCsim': {
                    'NumberOfStations': 1,
                    # Configure the port range for NetToPLCSim to try
                    'StartPort': self.START_PORT, 
                    'PortTryLimit': self.PORT_TRY_LIMIT 
                },
                'Station1': {
                    'Name': 'PLC#001',
                    'LocalIp': '127.0.0.1',
                    'PlcsimIp': plcsim_ip,
                    'Rack': self.rack,
                    'Slot': self.slot,
                    'TsapCheckEnabled': 1
                }
            }
            
            for section, options in ini_config.items():
                if not config.has_section(section):
                    config.add_section(section)
                
                for key, value in options.items():
                    config.set(section, key, str(value))
            
            with open(self.NETTOPLCSIM_INI, 'w') as configfile:
                config.write(configfile)
            
            print(f"INI configured: Port range {self.START_PORT} to {self.START_PORT + self.PORT_TRY_LIMIT - 1}")
            return True
            
        except Exception as e:
            print(f"Error configuring INI file: {e}")
            return False

    def _start_server(self) -> bool:
        """
        Starts the NetToPLCSim server and robustly waits for the listening port.
        Updates self.tcpport with the actual port found.
        """
        # Check if server is already running
        if self._server_process and self._server_process.poll() is None:
            print("NetToPLCSim server is already running.")
            if self.actual_server_port:
                self.tcpport = self.actual_server_port
            return True
        
        # Check if EXE exists
        if not os.path.exists(self.NETTOPLCSIM_EXE):
            print(f"NetToPLCsim.exe not found at: {self.NETTOPLCSIM_EXE}")
            return False
        
        # 1. Update INI file
        if not self._update_ini_file():
            return False
        
        # 2. Start server process
        exe_dir = os.path.dirname(self.NETTOPLCSIM_EXE)
        command_list = [
            self.NETTOPLCSIM_EXE,
            self.NETTOPLCSIM_INI,
            '-autostart',
        ]
        
        try:
            print("Starting NetToPLCSim server...")
            # Start the process hidden
            self._server_process = subprocess.Popen(
                command_list,
                cwd=exe_dir,
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            time.sleep(0.1) # Short initial pause
            
            # 3. Robust Verification of the Listening Port
            start_time = time.time()
            
            print(f"Waiting for NetToPLCSim listening port (max {self.MAX_SERVER_START_WAIT}s)...")
            
            while time.time() - start_time < self.MAX_SERVER_START_WAIT:
                
                # Check if process is still active
                if self._server_process.poll() is not None:
                    print(f"NetToPLCSim crashed during startup with exit code: {self._server_process.poll()}")
                    self._server_process = None
                    return False

                # Check all ports in parallel using threading for speed
                import threading
                found_port = None
                lock = threading.Lock()
                
                def check_port_threaded(port):
                    nonlocal found_port
                    if self._is_server_listening(port, timeout=0.05):
                        with lock:
                            if found_port is None:  # Only set if not already found
                                found_port = port
                
                # Start threads for all ports
                threads = []
                for offset in range(self.PORT_TRY_LIMIT):
                    current_port = self.START_PORT + offset
                    t = threading.Thread(target=check_port_threaded, args=(current_port,), daemon=True)
                    threads.append(t)
                    t.start()
                
                # Wait for all threads with timeout
                for t in threads:
                    t.join(timeout=0.1)
                
                # Check if we found a port
                if found_port is not None:
                    self.tcpport = found_port
                    self.actual_server_port = found_port
                    print(f"NetToPLCSim server running on port {found_port} after {time.time() - start_time:.2f}s.")
                    return True
                
                time.sleep(self.POLL_INTERVAL)

            # After the loop: server not found within the time limit
            print(f"Timeout. No listening port found within {self.MAX_SERVER_START_WAIT} seconds.")
            self._stop_server() 
            return False
                
        except FileNotFoundError:
            print(f"NetToPLCsim.exe not found: {self.NETTOPLCSIM_EXE}")
            return False
        except Exception as e:
            print(f"Error starting server: {e}")
            return False

    def _stop_server(self) -> bool:
        """Stop the NetToPLCSim server process."""
        if self._server_process and self._server_process.poll() is None:
            try:
                print("Stopping NetToPLCSim server...")
                self._server_process.terminate()
                self._server_process.wait(timeout=5)
                print("NetToPLCSim server stopped.")
                self._server_process = None
                self.actual_server_port = None
                return True
            except subprocess.TimeoutExpired:
                print("Timeout - forcing kill...")
                self._server_process.kill()
                self._server_process = None
                self.actual_server_port = None
                return True
            except Exception as e:
                print(f"Error stopping server: {e}")
                return False
        return True

    # --- Connection Methods ---

    def connect(self, instance_name: str | None = None) -> bool:
        """
        Connect to the PLC. Starts NetToPLCSim server automatically if needed.

        Returns:
        bool: True if connected successfully, False otherwise.
        """
        # Start server first. The server finds the correct port and sets self.tcpport.
        if not self._start_server():
            return False
        
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                self.client.connect(self.ip, self.rack, self.slot, self.tcpport)
                if self.client.get_connected():
                    return True
            except Exception as e:
                pass
            
            if attempt < max_retries:
                time.sleep(0.1)
        
        # VERWIJDER de hele "alternative slots" sectie
        print("No PLCSim connection - check if PLCSim is running")
        return False

    def disconnect(self) -> bool:
        """
        Disconnect from the PLC and stop the NetToPLCSim server.
        """
        try:
            if self.client.get_connected():
                self.client.disconnect()
                print("Disconnected from PLC")
            
            # Always try to stop server
            self._stop_server()
            
            # Extra cleanup: kill any remaining NetToPLCSim processes
            try:
                import subprocess
                subprocess.run(['taskkill', '/F', '/IM', 'NetToPLCSim.exe'], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             timeout=2)
            except:
                pass
            
            return True
        except Exception as e:
            print(f"Error disconnecting: {e}")
            # Still try cleanup
            try:
                import subprocess
                subprocess.run(['taskkill', '/F', '/IM', 'NetToPLCSim.exe'], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             timeout=2)
            except:
                pass
            return False
        
    def isConnected(self) -> bool:
        """
        Check if the connection to the PLC is alive.

        Returns:
        bool: True if connected, False otherwise.
        """
        if not self.client.get_connected():
            print("Connection lost to the PLC!")
            return False
        return True

    # --- Data Read/Write Functions (consistent with plcS7 reference) ---

    def SetDI(self, byte: int, bit: int, value: int) -> int:
        """
        Set a digital input (DI) bit in the PLC input process image.

        Parameters:
        byte (int): Byte index in the PLC input area (E/I)
        bit (int): Bit position (0–7) within the byte
        value (int): 1/0 or True/False to set or clear the bit

        Returns:
        int: The value set (1/0), -1 on error
        """
        if self.isConnected():
            if byte >= 0 and 0 <= bit <= 7:
                try:
                    # Read current byte data to preserve other bits
                    current_data = self.client.eb_read(start=byte, size=1)
                    buffer_DI = bytearray(current_data)
                    if value:
                        # Set bit
                        buffer_DI[0] |= (1 << bit)
                    else:
                        # Clear bit
                        buffer_DI[0] &= ~(1 << bit)
                    self.client.eb_write(start=byte, size=1, data=buffer_DI)
                    return int(bool(value))
                except Exception as e:
                    # Raise to allow upper layers to disconnect on error
                    raise
            return -1
        return -1

    def GetDO(self, byte: int, bit: int) -> int:
        """
        Read a digital output (DO) bit from the PLC output process image.

        Parameters:
        byte (int): Byte index in the PLC output area (A/Q)
        bit (int): Bit position (0–7) within the byte

        Returns:
        int: 0 or 1 if successful, -1 on error
        """
        if self.isConnected():
            if byte >= 0 and 0 <= bit <= 7:
                try:
                    data = self.client.ab_read(byte, 1)
                    return int(s7util.get_bool(data, 0, bit))
                except Exception as e:
                    # Raise to allow upper layers to disconnect on error
                    raise
            return -1
        return -1

    def SetAI(self, startByte: int, value: int) -> int:
        """
        Set an analog input (AI) value as a 16-bit UNSIGNED INTEGER in the PLC input process image.

        Parameters:
        startByte (int): Byte index in the PLC input area (E/I)
        value (int | float): Analog value (0–65535)

        Returns:
        int: Value set, -1 on error
        """
        if self.isConnected():
            # Snap7 functions handle SIGNED INT, but PLC AI/AQ are often used as UINT in simulation
            if startByte >= 0 and 0 <= value <= 65535: 
                try:
                    buffer_AI = bytearray(2)
                    # Ensure value is an integer and within range
                    val_int = int(round(value)) if isinstance(value, float) else int(value)
                    
                    # Manual byte-swapping for Big Endian (S7 format) to simulate UINT
                    lowByte = val_int & 0xFF
                    highByte = (val_int >> 8) & 0xFF
                    buffer_AI[0] = highByte
                    buffer_AI[1] = lowByte
                    
                    self.client.eb_write(start=startByte, size=2, data=buffer_AI)
                    return val_int
                except Exception as e:
                    # Raise to allow upper layers to disconnect on error
                    raise
            return -1
        return -1

    def GetAO(self, startByte: int) -> int:
        """
        Read an analog output (AO) value as a 16-bit SIGNED INTEGER from the PLC output process image.

        Parameters:
        startByte (int): Byte index in the PLC output area (A/Q)

        Returns:
        int: Signed 16-bit value (-32768–32767), -1 on error
        """
        if self.isConnected():
            if startByte >= 0:
                try:
                    data = self.client.ab_read(start=startByte, size=2)
                    return s7util.get_int(data, 0) # Get as signed integer
                except Exception as e:
                    # Raise to allow upper layers to disconnect on error
                    raise
            return -1
        return -1
    
    def SetDO(self, byte: int, bit: int, value: int) -> int:
        """
        Set a digital output (DO) bit in the PLC output process image.

        Parameters:
        byte (int): Byte index in the PLC output area (A/Q)
        bit (int): Bit position (0–7) within the byte
        value (int): 1/0 or True/False to set or clear the bit

        Returns:
        int: The value set (1/0), -1 on error
        """
        if self.isConnected():
            if byte >= 0 and 0 <= bit <= 7:
                try:
                    # Read current byte data to preserve other bits
                    current_data = self.client.ab_read(start=byte, size=1)
                    buffer_DO = bytearray(current_data)
                    if value:
                        # Set bit
                        buffer_DO[0] |= (1 << bit)
                    else:
                        # Clear bit
                        buffer_DO[0] &= ~(1 << bit)
                    self.client.ab_write(start=byte, data=buffer_DO)
                    return int(bool(value))
                except Exception as e:
                    # Raise to allow upper layers to disconnect on error
                    raise
            return -1
        return -1

    def SetAO(self, startByte: int, value: int) -> int:
        """
        Set an analog output (AO) value as a 16-bit SIGNED INTEGER in the PLC output process image.

        Parameters:
        startByte (int): Byte index in the PLC output area (A/Q)
        value (int | float): Analog value (-32768–32767)

        Returns:
        int: Value set, -1 on error
        """
        if self.isConnected():
            if startByte >= 0 and -32768 <= value <= 32767:
                try:
                    buffer_AO = bytearray(2)
                    val_int = int(round(value)) if isinstance(value, float) else int(value)
                    
                    # Convert to signed 16-bit and then to bytes (Big Endian)
                    if val_int < 0:
                        val_int = val_int & 0xFFFF  # Two's complement
                    
                    lowByte = val_int & 0xFF
                    highByte = (val_int >> 8) & 0xFF
                    buffer_AO[0] = highByte
                    buffer_AO[1] = lowByte
                    
                    self.client.ab_write(start=startByte, data=buffer_AO)
                    return val_int
                except Exception as e:
                    # Raise to allow upper layers to disconnect on error
                    raise
            return -1
        return -1

    def resetSendInputs(self, startByte: int, endByte: int) -> bool:
        """
        Reset all input data sent to the PLC (DI, AI) by writing zeros.

        Parameters:
        startByte (int): Start byte index to reset
        endByte (int): End byte index to reset

        Returns:
        bool: True if successful, False otherwise
        """
        if self.isConnected():
            if startByte >= 0 and endByte >= startByte:
                try:
                    size = endByte - startByte + 1
                    bufferEmpty = bytearray(size)
                    self.client.eb_write(start=startByte, size=size, data=bufferEmpty)
                    return True
                except Exception as e:
                    # Raise to allow upper layers to disconnect on error
                    raise
            return False
        return False
    
    def resetSendOutputs(self, startByte: int, endByte: int) -> bool:
        """
        Reset all output data sent to the PLC (DO, AO) by writing zeros.

        Parameters:
        startByte (int): Start byte index to reset
        endByte (int): End byte index to reset

        Returns:
        bool: True if successful, False otherwise
        """
        if self.isConnected():
            if startByte >= 0 and endByte >= startByte:
                try:
                    size = endByte - startByte + 1
                    bufferEmpty = bytearray(size)
                    self.client.ab_write(start=startByte, data=bufferEmpty)
                    print(f"Output area reset: bytes {startByte}-{endByte}")
                    return True
                except Exception as e:
                    # Raise to allow upper layers to disconnect on error
                    raise
            return False
        return False

    def __del__(self):
        """Cleanup upon object deletion."""
        try:
            self.disconnect()
        except:
            pass
        