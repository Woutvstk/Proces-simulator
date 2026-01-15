import subprocess
import os
import sys
import time
import socket
import configparser
from typing import Optional, Tuple

#Code succesfully tested with S7-1500/1200(G1-G2)/400/300/ET200 CPU in standard and advanced license(for the S7-1500)

# --- Global Configuration (Relative Paths) ---

# Determines the base directory of the script file
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the NetToPLCSim directory (adjusted for the relative structure)
_NETTOPLCSIM_DIR = os.path.join(_BASE_DIR, "..", "src", "plcCom", "NetToPLCsim")

# Full path to the NetToPLCSim executable and configuration file
NETTOPLCSIM_EXE = os.path.join(_NETTOPLCSIM_DIR, "NetToPLCsim.exe")
NETTOPLCSIM_INI = os.path.join(_NETTOPLCSIM_DIR, "configuration.ini")

# Time delay to allow the server to fully start and listen on the port
DRIVER_STABILIZATION_TIME = 1.5 

# --- Dynamic INI Configuration Dictionary ---
# These values are automatically written to the NetToPLCSim INI file before startup.
INI_CONFIG = {
    'NetToPLCsim': {
        'NumberOfStations': 1,
        'StartPort': 1024,      # Initial TCP port to attempt binding to
        'PortTryLimit': 5       # Number of ports to try (e.g., 1024 through 1028)
    },
    'Station1': {
        'Name': 'PLC#001',
        'LocalIp': '127.0.0.1', # IP address NetToPLCSim listens on (for Snap7 clients)
        'PlcsimIp': '192.168.0.1', # IP address of the PLCSIM Virtual Interface
        'Rack': 0,
        'Slot': 1,
        'TsapCheckEnabled': 1
    }
}

# --- Utility Functions ---

def update_ini_file(ini_path: str, config_dict: dict) -> bool:
    """
    Dynamically writes the configuration dictionary to the NetToPLCSim INI file.
    """
    try:
        config = configparser.ConfigParser()
        
        # Check if file exists for logging
        if os.path.exists(ini_path):
            print(f"Existing INI file found: {ini_path}")
        else:
            print(f"New INI file will be created: {ini_path}")
        
        # Write configuration sections and options
        for section, options in config_dict.items():
            if not config.has_section(section):
                config.add_section(section)
            
            for key, value in options.items():
                config.set(section, key, str(value))
        
        # Save to file
        with open(ini_path, 'w') as configfile:
            config.write(configfile)
        
        print("INI file successfully updated with configuration:")
        for section, options in config_dict.items():
            print(f"  [{section}]")
            for key, value in options.items():
                print(f"    {key} = {value}")
        
        return True
        
    except Exception as e:
        print(f"Error updating INI file: {e}")
        return False


def is_port_free(port: int) -> bool:
    """
    Checks if a TCP port is currently available (not in use) by attempting to bind to it.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Try to bind to the port on all interfaces
        s.bind(('0.0.0.0', port))
        s.close()
        return True 
    except socket.error:
        # Binding failed, port is likely in use
        return False 
    finally:
        try:
            # Ensure socket is closed
            if s.fileno() != -1:
                s.close()
        except:
            pass


def is_server_listening(port: int, timeout: float = 1.0) -> bool:
    """
    Checks if a service is actively listening on the specified port by attempting a TCP connection.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        # Attempt to connect locally
        s.connect(('127.0.0.1', port))
        return True 
    except (socket.error, ConnectionRefusedError):
        return False 
    finally:
        s.close()


def start_nettoplcsim() -> Tuple[Optional[subprocess.Popen], Optional[int]]:
    """
    Starts the NetToPLCSim server process, verifies its startup port, and returns both.

    Returns:
    (subprocess.Popen | None, int | None): The running subprocess object and the port it is listening on.
    """
    
    # STAGE 1: Configure INI file
    print("=" * 60)
    print("🔧 STAGE 1: Configuring INI File")
    print("=" * 60)
    
    if not update_ini_file(NETTOPLCSIM_INI, INI_CONFIG):
        print("❌ Cannot proceed without a valid INI configuration.")
        return None, None
    
    # Retrieve dynamic port settings from the config
    start_port = int(INI_CONFIG['NetToPLCsim']['StartPort'])
    port_try_limit = int(INI_CONFIG['NetToPLCsim']['PortTryLimit'])
    
    print(f"\n--- Port {start_port} Pre-Check (Initial Port) ---")
    if is_port_free(start_port):
        print(f"✅ Port {start_port} is free. NetToPLCSim will attempt to start here.")
    else:
        print(f"⚠️ Port {start_port} is busy. NetToPLCSim will try ports {start_port} through {start_port + port_try_limit - 1}.")

    # Define execution path and command
    exe_dir = os.path.dirname(NETTOPLCSIM_EXE)
    command_list = [
        NETTOPLCSIM_EXE, 
        NETTOPLCSIM_INI,
        '-autostart',
    ]
    
    print(f"\n🚀 Startup Command: {' '.join(command_list)}")
    print(f"📂 Working Directory: {exe_dir}")
    
    nettoplcsim_process = None
    try:
        # STAGE 2: Start the process
        nettoplcsim_process = subprocess.Popen(
            command_list,
            cwd=exe_dir,
            shell=False,
            # Do not redirect stdout/stderr so NetToPLCSim's console output is visible.
        )
        
        print(f"✅ NetToPLCSim started (PID: {nettoplcsim_process.pid}).")
        
        print("  Waiting 2 seconds for initial launch...")
        time.sleep(2) 
        
        exit_code = nettoplcsim_process.poll()
        
        if exit_code is not None:
            # The process crashed immediately
            print(f"\n❌ NetToPLCSim crashed immediately with exit code: {exit_code}")
            print("  ^ CHECK THE OUTPUT ABOVE THIS LINE FOR THE CRASH REASON (C# error message).")
            print("=" * 60)
            return None, None
        else:
            # STAGE 3: Stabilize and verify listening port
            print(f"⏳ Waiting for server stabilization ({DRIVER_STABILIZATION_TIME} seconds)...")
            time.sleep(DRIVER_STABILIZATION_TIME)
            
            print("\n--- Post-Stabilization Verification ---")
            
            # Check all ports in the configured range
            final_port = None
            for i in range(port_try_limit):
                current_port_to_check = start_port + i
                if is_server_listening(current_port_to_check, timeout=0.5): 
                    final_port = current_port_to_check
                    break
            
            if final_port: 
                print(f"✅ NetToPLCSim is successfully listening on port {final_port}.")
                print("✅ Server running successfully in the background. Ready for use.")
                return nettoplcsim_process, final_port
            else:
                print(f"❌ Error: NetToPLCSim is NOT listening on any attempted ports ({start_port} through {start_port + port_try_limit - 1}).")
                print("  The process is running, but the server failed to bind.")
                # Return the process even if binding failed, so it can be terminated later
                return nettoplcsim_process, None
            
    except FileNotFoundError:
        print(f"❌ NetToPLCsim.exe not found: {NETTOPLCSIM_EXE}")
    except Exception as e:
        print(f"❌ Unknown error during startup: {e}")
        
    return None, None # Return None for both process and port on critical error


def main():
    """Main function for process management."""
    nettoplcsim_process: Optional[subprocess.Popen] = None
    final_port: Optional[int] = None
    
    try:
        nettoplcsim_process, final_port = start_nettoplcsim()

        if nettoplcsim_process:
            print("\n" + "=" * 40)
            print("✅ NetToPLCSim is running in the background.")
            if final_port:
                print(f"🔌 Snap7 connection port: {final_port}")
            print("🛑 Press **ENTER** in this window to stop NetToPLCSim.")
            print("=" * 40)
            
            # Keep the script alive until the user presses Enter or the process dies
            while nettoplcsim_process.poll() is None:
                try:
                    input() 
                    break 
                except EOFError: 
                    break
                except KeyboardInterrupt: 
                    raise 
        else:
            print("\n❌ NetToPLCSim could not be started. Session terminated.")

    except KeyboardInterrupt:
        print("\n\nScript session terminated by user (Ctrl+C).")

    except Exception as e:
        print(f"\nUnexpected error during execution: {e}")

    finally:
        # Clean shutdown of the server process
        if nettoplcsim_process and nettoplcsim_process.poll() is None:
            print("\n--- Shutting down NetToPLCSim ---")
            try:
                # Request process termination
                nettoplcsim_process.terminate() 
                print("  Waiting 5 seconds for clean exit...")
                nettoplcsim_process.wait(timeout=5)
                print("  ✅ NetToPLCSim cleanly shut down.")
            except subprocess.TimeoutExpired:
                print("  ⚠️ Timeout - forcing stop (kill)...")
                nettoplcsim_process.kill()

        print("\nScript session finished.")
        
        # Keep the console window open if it was the main process
        if nettoplcsim_process is None or nettoplcsim_process.poll() is not None:
            print("\n🚨 Press ENTER to close this console window...")
            try:
                # This input ensures the console window doesn't immediately close
                input()
            except:
                pass 


if __name__ == "__main__":
    
    # Logic to detach the console window (runs the script in a new console)
    if '--detached' not in sys.argv:
        # Create the command to run this script again with the '--detached' flag
        command = [
            sys.executable,
            sys.argv[0],
            '--detached'
        ]

        try:
            # Start the new process in a separate console window and detach it
            subprocess.Popen(
                command, 
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_CONSOLE
            )
            sys.exit(0) # Exit the current (initial) process
        except Exception:
            # If detaching fails (e.g., on Linux/macOS or a locked environment), 
            # the script will continue in the current console
            main() # Run main directly if detachment fails
    else:
        # Run the main process logic (only executed in the detached console)
        main()