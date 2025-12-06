import subprocess
import os
import sys
import time
import socket
import ctypes

#probleem met de 102 poort overname, V2 is stabieler wegens geen poortovername maar dit kan als tijdelijke backup dienen 
#Werkt niet stabiel momenteel (niet runnen)

# --- Configuratie ---
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_NETTOPLCSIM_DIR = os.path.join(_BASE_DIR, "..", "src", "plcCom", "NetToPLCsim")
NETTOPLCSIM_EXE = os.path.join(_NETTOPLCSIM_DIR, "NetToPLCsim.exe")
NETTOPLCSIM_INI = os.path.join(_NETTOPLCSIM_DIR, "configuration.ini")
PORT_TO_CHECK = 102
# --- Hulpfuncties ---

def is_admin():
    """Controleert of het script draait als Administrator."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin():
    """Start het huidige script opnieuw op met Administrator rechten."""
    script = os.path.abspath(sys.argv[0])
    params = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in sys.argv[1:]) 
    
    print("--- 🛡️ Vraagt om Administrator-rechten (UAC-prompt verschijnt)... ---")

    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, 
            "runas", 
            sys.executable,  
            f'"{script}" {params}', 
            None, 
            1 
        )
        sys.exit(0) 
    except Exception as e:
        print(f"❌ Fout bij het aanvragen van Admin-rechten: {e}")
        sys.exit(1)

# Functie aangepast en hernoemd
def is_port_free(port):
    """
    Controleert of poort beschikbaar is (niet in gebruik) door te proberen te binden.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('0.0.0.0', port))
        s.close()
        return True # Bind is gelukt, poort is vrij
    except socket.error:
        return False # Bind is mislukt, poort is bezet
    finally:
        try:
            if s.fileno() != -1:
                s.close()
        except:
            pass

# Nieuwe, betrouwbaardere verificatiefunctie
def is_server_listening(port, timeout=1):
    """
    Controleert of er een service luistert op de opgegeven poort (TCP connectie proberen).
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        # Probeer verbinding te maken met localhost op de poort
        s.connect(('127.0.0.1', port))
        return True # Verbinding gelukt, server luistert
    except (socket.error, ConnectionRefusedError):
        return False # Verbinding mislukt, server luistert niet
    finally:
        s.close()


def start_nettoplcsim():
    """
    Start NetToPLCSim in headless mode en wacht op driverstabilisatie.
    """
    
    DRIVER_STABILIZATION_TIME = 12 
    
    print("--- Poort 102 Pre-Check ---")
    if is_port_free(PORT_TO_CHECK):
        print(f"✅ Poort {PORT_TO_CHECK} is vrij voor NetToPLCSim.")
    else:
        # De S7DOS service is bezet, NetToPLCSim MOET dit oplossen via -s=YES
        print(f"⚠️ Poort {PORT_TO_CHECK} is bezet. NetToPLCSim zal de overnameprocedure starten.")

    exe_dir = os.path.dirname(NETTOPLCSIM_EXE)
    
    command_list = [
        NETTOPLCSIM_EXE, 
        NETTOPLCSIM_INI,
        '-autostart',
        '-s=YES' 
    ]
    
    print(f"\n🚀 Opstartcommando: {' '.join(command_list)}")
    print(f"📂 Working directory: {exe_dir}")
    
    nettoplcsim_process = None
    try:
        nettoplcsim_process = subprocess.Popen(
            command_list,
            cwd=exe_dir,
            shell=False,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW 
        )
        
        print(f"✅ NetToPLCSim gestart (PID: {nettoplcsim_process.pid}).")
        
        # Stap 1: Korte wachttijd voor de initiële S7DOS stop en poortovername
        print("   Wacht 5 seconden op service stop + poortovername...")
        time.sleep(5) 
        
        exit_code = nettoplcsim_process.poll()
        
        if exit_code is not None:
            print(f"\n❌ NetToPLCSim crashte met exit code: {exit_code}\n")
            
            # --- CRASH LOG (OORZAAK VAN HET PROBLEEM KAN HIER STAAN) ---
            try:
                # Lees de output na de crash
                stdout, stderr = nettoplcsim_process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                stdout, stderr = "(Niet leesbaar)", "(Niet leesbaar)" 

            print("="*60)
            print("--- STDOUT (CRASH LOG) ---")
            print(stdout.strip() if stdout else "(Geen output)")
            print("--- STDERR (CRASH LOG) ---")
            print(stderr.strip() if stderr else "(Geen output)")
            print("="*60)

            return None
        else:
            # STAP 2: DE BELANGRIJKSTE WACHTTIJD!
            print(f"⏳ Wachten op driverstabilisatie ({DRIVER_STABILIZATION_TIME} seconden)...")
            time.sleep(DRIVER_STABILIZATION_TIME)
            
            # --- Post-Stabilisatie Verificatie met de nieuwe functie ---
            print("\n--- Post-Stabilisatie Verificatie ---")
            if is_server_listening(PORT_TO_CHECK): # Check of we kunnen CONNECTEREN
                print(f"✅ NetToPLCSim luistert nu succesvol op poort {PORT_TO_CHECK}.")
                print("✅ Server draait succesvol op de achtergrond. Klaar voor gebruik.")
                return nettoplcsim_process
            else:
                print(f"❌ Fout: NetToPLCSim luistert NIET op poort {PORT_TO_CHECK}.")
                print("   Hoewel het proces draait, is de serverfunctie gefaald.")
                return nettoplcsim_process
            
    except FileNotFoundError:
        print(f"❌ NetToPLCsim.exe niet gevonden: {NETTOPLCSIM_EXE}")
    except Exception as e:
        print(f"❌ Onbekende fout bij starten: {e}")
        
    return None

def main():
    """Hoofdfunctie voor procesbeheer."""
    nettoplcsim_process = None
    
    try:
        nettoplcsim_process = start_nettoplcsim()

        if nettoplcsim_process:
            print("\n========================================")
            print("✅ NetToPLCSim draait op de achtergrond.")
            print("🛑 Druk op **ENTER** om NetToPLCSim te stoppen.")
            print("========================================")
            
            # Wacht op ENTER (of EOF/KeyboardInterrupt)
            while nettoplcsim_process.poll() is None:
                try:
                    input() 
                    break 
                except EOFError: 
                    break
                except KeyboardInterrupt: 
                    raise 
        else:
            print("\n❌ NetToPLCSim kon niet gestart worden. Sessie beëindigd.")

    except KeyboardInterrupt:
        print("\n\nScriptsessie beëindigd door gebruiker (Ctrl+C).")

    except Exception as e:
        print(f"\nOnverwachte fout tijdens uitvoering: {e}")

    finally:
        # Opruiming
        if nettoplcsim_process and nettoplcsim_process.poll() is None:
            print("\n--- NetToPLCSim sluiten ---")
            try:
                nettoplcsim_process.terminate() 
                print("   Wacht 5 seconden op schone afsluiting + service herstart...")
                nettoplcsim_process.wait(timeout=5)
                print("   ✅ NetToPLCSim netjes afgesloten.")
            except subprocess.TimeoutExpired:
                print("   ⚠️ Timeout - dwing stop af (kill)...")
                nettoplcsim_process.kill()

        print("\nScriptsessie beëindigd.")
        
        if nettoplcsim_process is None or nettoplcsim_process.poll() is not None:
            print("\n🚨 Druk op ENTER om dit consolevenster te sluiten...")
            try:
                input()
            except:
                pass 


if __name__ == "__main__":
    print("--- START NETTOPLCSIM Beheer Script ---")
    
    if not is_admin():
        run_as_admin() 
    else:
        print("✅ Script draait met Administrator-rechten.")
        main()