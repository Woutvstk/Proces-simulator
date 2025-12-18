# mainGui.py - Main GUI entry point and navigation
# Alternative version with absolute imports

import sys
import os
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtCore import QTimer, Qt
from PyQt5 import uic

# ============================================================================
# ABSOLUTE IMPORTS - Add mainGui directory to path
# ============================================================================
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Now import from same directory
from GeneralSettings import ProcessSettingsMixin
from ioConfigPage import IOConfigMixin
from TankSimSettings import TankSimSettingsMixin  

from tankSim.gui import VatWidget
from conveyor.gui import TransportbandWidget
from configuration import configuration

# =============================================================================
# Resource and UI compilation (dynamic)
# =============================================================================
gui_common_dir = current_dir.parent / "guiCommon"

qrc_file = gui_common_dir / "Resource.qrc"
rc_py_file = gui_common_dir / "Resource_rc.py"

if qrc_file.exists():
    try:
        subprocess.run(
            ["pyrcc5", str(qrc_file), "-o", str(rc_py_file)],
            check=True
        )

        if str(gui_common_dir) not in sys.path:
            sys.path.insert(0, str(gui_common_dir))

        try:
            import Resource_rc  # type: ignore[import-not-found]
        except ImportError as e:
            pass

    except subprocess.CalledProcessError as e:
        pass
    except Exception as e:
        pass

# Load UI
ui_file = gui_common_dir / "mainWindowPIDRegelaarSim.ui"

if ui_file.exists():
    Ui_MainWindow, QtBaseClass = uic.loadUiType(str(ui_file))
else:
    raise FileNotFoundError(f"Cannot find {ui_file}! Searched in: {ui_file}")


# =============================================================================
# MainWindow class - Same as before
# =============================================================================
class MainWindow(QMainWindow, Ui_MainWindow, ProcessSettingsMixin, IOConfigMixin, TankSimSettingsMixin):
    """
    Main application window
    Uses mixins for process settings and I/O config functionality
    """

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        # Start with collapsed menu
        self.fullMenuWidget.setVisible(False)
        self.iconOnlyWidget.setVisible(True)
        self.pushButton_menu.setChecked(False)

        # Connect exit buttons
        self.pushButton_Exit.clicked.connect(self.close)
        self.pushButton_exit2.clicked.connect(self.close)

        # Store reference to main configuration
        self.mainConfig = None
        self.tanksim_config = None
        self.tanksim_status = None

        # Initialize connection variables
        self.validPlcConnection = False
        self.plc = None

        # Float window state
        self.floated_window = None
        self.current_sim_page = None

        # IP throttling
        self.ip_change_timer = QTimer()
        self.ip_change_timer.setSingleShot(True)
        self.ip_change_timer.timeout.connect(self._apply_ip_change)
        self.pending_ip = None

        # Main update timer
        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_all_values)
        self.timer.start()

        # Setup connection status icon
        try:
            self.update_connection_status_icon()
        except AttributeError:
            pass

        # Connect button
        try:
            self.pushButton_connect.toggled.connect(self.on_connect_toggled)
            self.pushButton_connect.setCheckable(True)
        except AttributeError:
            pass

        try:
            self.lineEdit_IPAddress.textChanged.connect(self.on_ip_changed)
        except AttributeError:
            pass

        # Initialize I/O Config Page
        self.init_io_config_page()

        # Initialize GENERAL Process Settings Page
        self.init_process_settings_page()
        
        # Initialize TANK SIM Settings Page
        self.init_tanksim_settings_page()

        # Initialize network port combobox
        self._init_network_port_combobox()

        # Connect navigation buttons
        self.connect_navigation_buttons()

        # Connect simulation buttons
        self.connect_simulation_buttons()

        # Initialize GUI mode
        QTimer.singleShot(100, self._initialize_gui_mode)

    def _initialize_gui_mode(self):
        """Initialize GUI mode after mainConfig is available"""
        if hasattr(self, 'mainConfig') and self.mainConfig:
            self.mainConfig.plcGuiControl = "gui"
            self.mainConfig.plcProtocol = "GUI"
        else:
            QTimer.singleShot(100, self._initialize_gui_mode)

    def connect_navigation_buttons(self):
        """Connect all navigation buttons"""
        self.pushButton_settingsPage.toggled.connect(self.go_to_settings)
        self.pushButton_settingsPage2.toggled.connect(self.go_to_settings)

        self.pushButton_IOPage.toggled.connect(self.go_to_io)
        self.pushButton_IOPage2.toggled.connect(self.go_to_io)

        # SIMULATION page navigation
        self.pushButton_simPage.toggled.connect(self.go_to_sim_or_selection)
        self.pushButton_simPage2.toggled.connect(self.go_to_sim_or_selection)

        # Simulation settings page navigation
        try:
            self.pushButton_simSettings.toggled.connect(self.go_to_sim_settings)
            self.pushButton_simSettings2.toggled.connect(self.go_to_sim_settings)
        except AttributeError:
            pass

    def connect_simulation_buttons(self):
        """Connect all simulation related buttons"""
        # START SIMULATION BUTTONS
        try:
            self.pushButton_1Vat.setCheckable(True)
            self.pushButton_1Vat.clicked.connect(lambda: self.start_simulation(0))
        except AttributeError:
            pass

        try:
            self.pushButton_2Vatten.setCheckable(True)
            self.pushButton_2Vatten.clicked.connect(lambda: self.start_simulation(1))
        except AttributeError:
            pass

        try:
            self.pushButton_transportband.setCheckable(True)
            self.pushButton_transportband.clicked.connect(lambda: self.start_simulation(2))
        except AttributeError:
            pass

        # CLOSE SIMULATION BUTTONS
        try:
            close_btn = self.vat1Page.findChild(QPushButton, "pushButton_closePIDValves")
            if close_btn:
                close_btn.clicked.connect(self.close_simulation)
        except AttributeError:
            pass

        try:
            close_btn = self.vatten2Page.findChild(QPushButton, "pushButton_ClosePIDMotor")
            if close_btn:
                close_btn.clicked.connect(self.close_simulation)
        except AttributeError:
            pass

        try:
            close_btn = self.transportbandPage.findChild(QPushButton, "pushButton_CloseConveyor")
            if close_btn:
                close_btn.clicked.connect(self.close_simulation)
        except AttributeError:
            pass

        # FLOAT BUTTONS
        try:
            float_btn = self.vat1Page.findChild(QPushButton, "pushButton_FloatPIDValves")
            if float_btn:
                float_btn.clicked.connect(lambda: self.toggle_float(0))
        except AttributeError:
            pass

        try:
            float_btn = self.vatten2Page.findChild(QPushButton, "pushButton_FloatPIDMotor")
            if float_btn:
                float_btn.clicked.connect(lambda: self.toggle_float(1))
        except AttributeError:
            pass

        try:
            float_btn = self.transportbandPage.findChild(QPushButton, "pushButton_FloatConveyor")
            if float_btn:
                float_btn.clicked.connect(lambda: self.toggle_float(2))
        except AttributeError:
            pass

    def start_simulation(self, sim_index):
        """Start a specific simulation"""
        self.current_sim_page = sim_index
        self.MainScreen.setCurrentIndex(sim_index)
        
        # NIEUW: Update stacked widget in simulation settings page
        try:
            if sim_index == 0:  # Tank with valves
                # Show tank settings
                self.stackedWidget_SimSettings.setCurrentIndex(0)
            elif sim_index == 1:  # Tank with motor  
                # Show tank settings (same as index 0 for now)
                self.stackedWidget_SimSettings.setCurrentIndex(0)
            elif sim_index == 2:  # Conveyor
                # Show conveyor settings (placeholder for now)
                self.stackedWidget_SimSettings.setCurrentIndex(1)
        except AttributeError:
            pass
        
        print(f"Started simulation {sim_index}")

    def go_to_sim_settings(self, checked):
        """Navigate to simulation settings page"""
        if checked:
            self.MainScreen.setCurrentIndex(6)
            
            # Update stacked widget based on current active sim
            try:
                if self.current_sim_page is not None:
                    if self.current_sim_page in [0, 1]:  # Tank simulations
                        self.stackedWidget_SimSettings.setCurrentIndex(0)
                    elif self.current_sim_page == 1:  # Conveyor
                        self.stackedWidget_SimSettings.setCurrentIndex(1)
                else:
                    # No active sim - show tank settings by default
                    self.stackedWidget_SimSettings.setCurrentIndex(0)
            except AttributeError:
                pass


    def go_to_settings(self, checked):
        """Navigate to general settings page"""
        if checked:
            # Check IO config when leaving IO page
            if self.MainScreen.currentIndex() == 4:  # Coming from IO page
                self.check_io_config_loaded()
            self.MainScreen.setCurrentIndex(3)

    def go_to_io(self, checked):
        """Navigate to I/O page"""
        if checked:
            self.MainScreen.setCurrentIndex(4)

    def go_to_sim_or_selection(self, checked):
        """Navigate to active sim or selection page"""
        if checked:
            # Check IO config when leaving IO page
            if self.MainScreen.currentIndex() == 4:  # Coming from IO page
                self.check_io_config_loaded()
            
            if self.current_sim_page is not None:
                self.MainScreen.setCurrentIndex(self.current_sim_page)
            else:
                self.MainScreen.setCurrentIndex(5)
            
            if not self.fullMenuWidget.isVisible():
                self.pushButton_menu.setChecked(True)

    def go_to_sim_settings(self, checked):
        """Navigate to simulation settings page"""
        if checked:
            self.MainScreen.setCurrentIndex(6)

    def start_simulation(self, sim_index):
        """Start a specific simulation"""
        self.current_sim_page = sim_index
        self.MainScreen.setCurrentIndex(sim_index)
        print(f"Started simulation {sim_index}")

    def close_simulation(self):
        """Close current simulation and return to selection page"""
        print(f"Closing simulation {self.current_sim_page}")
        
        self.current_sim_page = None
        self.MainScreen.setCurrentIndex(5)
        
        # Uncheck all start buttons
        try:
            self.pushButton_1Vat.setChecked(False)
            self.pushButton_2Vatten.setChecked(False)
            self.pushButton_transportband.setChecked(False)
        except:
            pass

    def toggle_float(self, sim_index):
        """Float or dock the simulation window"""
        if self.floated_window is None:
            self.float_simulation(sim_index)
        else:
            self.dock_simulation()

    def float_simulation(self, sim_index):
        """Create a floating window for the simulation"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout
        
        print(f"Floating simulation {sim_index}")
        
        self.floated_window = QDialog(self)
        self.floated_window.setWindowTitle("Simulation - Floating")
        self.floated_window.setWindowFlags(Qt.Window)
        self.floated_window.resize(1000, 800)
        
        layout = QVBoxLayout(self.floated_window)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Get page
        if sim_index == 0:
            page = self.vat1Page
        elif sim_index == 1:
            page = self.vatten2Page
        else:
            page = self.transportbandPage
        
        # Reparent to floating window
        page.setParent(self.floated_window)
        layout.addWidget(page)
        
        # Update float button
        try:
            if sim_index == 0:
                float_btn = page.findChild(QPushButton, "pushButton_FloatPIDValves")
            elif sim_index == 1:
                float_btn = page.findChild(QPushButton, "pushButton_FloatPIDMotor")
            else:
                float_btn = page.findChild(QPushButton, "pushButton_FloatConveyor")
            
            if float_btn:
                float_btn.setText("⧈ DOCK")
        except:
            pass
        
        self.floated_window.show()
        self.floated_window.finished.connect(self.dock_simulation)

    def dock_simulation(self):
        """Dock the floating window back"""
        if not self.floated_window:
            return
        
        print(f"Docking simulation {self.current_sim_page}")
        
        sim_index = self.current_sim_page
        
        if sim_index == 0:
            page = self.vat1Page
        elif sim_index == 1:
            page = self.vatten2Page
        else:
            page = self.transportbandPage
        
        if page:
            self.MainScreen.insertWidget(sim_index, page)
            
            try:
                if sim_index == 0:
                    float_btn = page.findChild(QPushButton, "pushButton_FloatPIDValves")
                elif sim_index == 1:
                    float_btn = page.findChild(QPushButton, "pushButton_FloatPIDMotor")
                else:
                    float_btn = page.findChild(QPushButton, "pushButton_FloatConveyor")
                
                if float_btn:
                    float_btn.setText("⧉ FLOAT")
            except:
                pass
        
        if self.floated_window:
            self.floated_window.close()
            self.floated_window.deleteLater()
            self.floated_window = None

    def update_all_values(self):
        """Main update loop"""
        self.update_tanksim_display()  
        self.write_gui_values_to_status() 
        self.update_io_status_display()

    def update_connection_status_icon(self):
        """Update connection status icon"""
        try:
            self.Label_connectStatus.setText("")
            current_dir = Path(__file__).parent

            if self.validPlcConnection:
                icon_path = current_dir / "media" / "icon" / "status_ok.svg"
            else:
                icon_path = current_dir / "media" / "icon" / "status_nok.svg"

            if icon_path.exists():
                from PyQt5.QtGui import QPixmap
                pixmap = QPixmap(str(icon_path))
                self.Label_connectStatus.setPixmap(
                    pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except:
            pass

    def on_connect_toggled(self, checked):
        """Handle connect button"""
        if not self.mainConfig:
            return
        
        if checked:
            # User wants to connect
            self.mainConfig.tryConnect = True
        else:
            # User wants to disconnect
            if self.validPlcConnection and hasattr(self, 'plc') and self.plc:
                try:
                    print("Disconnecting from PLC...")
                    self.plc.disconnect()
                except Exception as e:
                    print(f"Error during disconnect: {e}")
                
                self.validPlcConnection = False
                self.plc = None
                self.update_connection_status_icon()
                
                # Clear all forces when disconnecting
                self.clear_all_forces()

    def on_ip_changed(self, text):
        """Update IP with throttling"""
        if not self.mainConfig:
            return
        self.mainConfig.plcIpAdress = text
        self.pending_ip = text
        self.ip_change_timer.stop()
        self.ip_change_timer.start(500)

    def _apply_ip_change(self):
        """Execute disconnect after throttle"""
        if not self.pending_ip:
            return

        if self.validPlcConnection and hasattr(self, 'plc') and self.plc:
            try:
                if self.plc.isConnected():
                    self.plc.disconnect()
            except:
                pass

            self.validPlcConnection = False
            self.plc = None

            try:
                self.pushButton_connect.blockSignals(True)
                self.pushButton_connect.setChecked(False)
                self.pushButton_connect.blockSignals(False)
            except:
                pass

            self.update_connection_status_icon()

        self.pending_ip = None

    def _init_network_port_combobox(self):
        """Initialize network adapter combobox"""
        try:
            import socket
            self.comboBox_networkPort.clear()
            self.comboBox_networkPort.addItem("Auto (System Default)", "auto")

            adapters_found = False

            try:
                import wmi
                c = wmi.WMI()
                for interface in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
                    if interface.IPAddress:
                        ipv4_addr = None
                        for ip in interface.IPAddress:
                            if '.' in ip and not ip.startswith('127.'):
                                ipv4_addr = ip
                                break
                        if ipv4_addr:
                            adapter_name = interface.Description
                            display_name = f"{adapter_name} ({ipv4_addr})"
                            self.comboBox_networkPort.addItem(display_name, adapter_name)
                            adapters_found = True
            except:
                pass

            if not adapters_found:
                try:
                    import psutil
                    net_if_addrs = psutil.net_if_addrs()
                    net_if_stats = psutil.net_if_stats()

                    for interface_name, addresses in net_if_addrs.items():
                        if interface_name in net_if_stats:
                            if not net_if_stats[interface_name].isup:
                                continue

                        ipv4_addr = None
                        for addr in addresses:
                            if addr.family == socket.AF_INET:
                                ipv4_addr = addr.address
                                break

                        if ipv4_addr and ipv4_addr != '127.0.0.1':
                            display_name = f"{interface_name} ({ipv4_addr})"
                            self.comboBox_networkPort.addItem(display_name, interface_name)
                            adapters_found = True
                except:
                    pass

            if not adapters_found:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    s.close()
                    self.comboBox_networkPort.addItem(f"Primary Adapter ({local_ip})", "primary")
                except:
                    pass

            self.comboBox_networkPort.currentIndexChanged.connect(self._on_network_port_changed)
        except:
            pass

    def _on_network_port_changed(self, index):
        """Handle network port change"""
        try:
            selected_adapter = self.comboBox_networkPort.currentData()
            if hasattr(self, 'mainConfig') and self.mainConfig:
                self.mainConfig.selectedNetworkAdapter = selected_adapter
        except:
            pass

    def closeEvent(self, event):
        """Handle window close event with cleanup"""
        print("\n" + "="*60)
        print("Shutting down...")
        print("="*60)
        
        try:
            # 1. Stop simulation
            if hasattr(self, 'tanksim_status') and self.tanksim_status:
                self.tanksim_status.simRunning = False
            
            # 2. Disconnect PLC
            if hasattr(self, 'validPlcConnection') and self.validPlcConnection:
                if hasattr(self, 'plc') and self.plc:
                    try:
                        print("Disconnecting PLC...")
                        self.plc.disconnect()
                    except Exception as e:
                        print(f"Error during PLC disconnect: {e}")
            
            # 3. Stop NetToPLCSim.exe
            try:
                print("Stopping NetToPLCSim.exe...")
                import subprocess
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'NetToPLCSim.exe'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2
                )
            except Exception as e:
                print(f"Note: {e}")
            
            # 4. Signal main loop to exit
            if hasattr(self, 'mainConfig') and self.mainConfig:
                self.mainConfig.doExit = True
            
            print("Cleanup complete")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        # Accept the close event
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    current_dir = Path(__file__).parent
    gui_common_dir = current_dir.parent / "guiCommon"
    style_file = gui_common_dir / "style.qss"

    if os.path.exists(style_file):
        try:
            with open(style_file, "r") as f:
                app.setStyleSheet(f.read())
        except:
            pass

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())