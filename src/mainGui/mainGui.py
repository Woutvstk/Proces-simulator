# mainGui.py - Main GUI entry point and navigation
# Handles:
# - Resource compilation
# - UI loading
# - Basic window initialization
# - Navigation between pages
# - PLC connection handling
# - Main update timers

import sys
import os
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer, Qt
from PyQt5 import uic

# Import split modules
from mainGui.processSettingsPage import ProcessSettingsMixin
from mainGui.ioConfigPage import IOConfigMixin

from tankSim.gui import VatWidget
from conveyor.gui import TransportbandWidget
from configuration import configuration

# =============================================================================
# Resource and UI compilation (dynamic)
# =============================================================================
current_dir = Path(__file__).parent
gui_common_dir = current_dir.parent / "guiCommon"

qrc_file = gui_common_dir / "Resource.qrc"
rc_py_file = gui_common_dir / "Resource_rc.py"

if qrc_file.exists():
    try:
        subprocess.run(
            ["pyrcc5", str(qrc_file), "-o", str(rc_py_file)], 
            check=True
        )
        # Removed unnecessary print
        
        if str(gui_common_dir) not in sys.path:
            sys.path.insert(0, str(gui_common_dir))
        
        try:
            import Resource_rc  # type: ignore[import-not-found]
            # Removed unnecessary print
        except ImportError as e:
            # Removed unnecessary print
            pass
        
    except subprocess.CalledProcessError as e:
        # Removed unnecessary print
        pass
    except Exception as e:
        # Removed unnecessary print
        pass
else:
    # Removed unnecessary print
    pass

# Load UI
ui_file = gui_common_dir / "mainWindowPIDRegelaarSim.ui"

if ui_file.exists():
    Ui_MainWindow, QtBaseClass = uic.loadUiType(str(ui_file))
    # Removed unnecessary print
else:
    raise FileNotFoundError(f"Cannot find {ui_file}! Searched in: {ui_file}")


# =============================================================================
# MainWindow class - Combines all functionality via mixins
# =============================================================================
class MainWindow(QMainWindow, Ui_MainWindow, ProcessSettingsMixin, IOConfigMixin):
    """
    Main application window
    Uses mixins for process settings and I/O config functionality
    """
    
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        
        # Removed unnecessary print
        
        # Start with collapsed menu
        self.fullMenuWidget.setVisible(False)
        self.iconOnlyWidget.setVisible(True)
        self.pushButton_menu.setChecked(False)
        
        # Connect exit buttons
        self.pushButton_Exit.clicked.connect(self.close)
        self.pushButton_exit2.clicked.connect(self.close)

        # Store reference to main configuration
        self.mainConfig = None  # Will be set from main.py
        self.tanksim_config = None
        self.tanksim_status = None
        
        # Initialize connection variables
        self.validPlcConnection = False
        self.plc = None

        # IP throttling
        self.ip_change_timer = QTimer()
        self.ip_change_timer.setSingleShot(True)
        self.ip_change_timer.timeout.connect(self._apply_ip_change)
        self.pending_ip = None
        
        # Main update timer
        self.timer = QTimer()
        self.timer.setInterval(100)  # 10x per second
        self.timer.timeout.connect(self.update_all_values)
        self.timer.start()
        
        # Setup connection status icon
        try:
            self.update_connection_status_icon()
        except AttributeError:
            # Removed unnecessary print
            pass
        
        # Connect button
        try:
            self.pushButton_connect.toggled.connect(self.on_connect_toggled)
            self.pushButton_connect.setCheckable(True)
        except AttributeError:
            # Removed unnecessary print
            pass

        try:
            self.lineEdit_IPAddress.textChanged.connect(self.on_ip_changed)
        except AttributeError:
            # Removed unnecessary print
            pass
        
        # Initialize I/O Config Page (from IOConfigMixin)
        self.init_io_config_page()
        
        # Initialize Process Settings Page (from ProcessSettingsMixin)
        self.init_process_settings_page()

        # Initialize network port combobox
        self._init_network_port_combobox()

        # Connect navigation buttons
        self.connect_navigation_buttons()
        
        # Connect simulation selection buttons
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
        
        self.pushButton_simPage.toggled.connect(self.go_to_sim)
        self.pushButton_simPage2.toggled.connect(self.go_to_sim)
    
    def connect_simulation_buttons(self):
        """Connect simulation selection buttons"""
        self.pushButton_1Vat.setAutoExclusive(True)
        self.pushButton_2Vatten.setAutoExclusive(True)
        self.pushButton_transportband.setAutoExclusive(True)

        self.pushButton_1Vat.toggled.connect(lambda checked: checked and self.select_simulation_simple(0))
        self.pushButton_2Vatten.toggled.connect(lambda checked: checked and self.select_simulation_simple(1))
        self.pushButton_transportband.toggled.connect(lambda checked: checked and self.select_simulation_simple(2))
    
    def go_to_settings(self, checked):
        """Navigate to settings page"""
        if checked:
            self.MainScreen.setCurrentIndex(3)
    
    def go_to_io(self, checked):
        """Navigate to I/O page"""
        if checked:
            self.MainScreen.setCurrentIndex(4)
    
    def go_to_sim(self, checked):
        """Navigate to simulation page"""
        if checked:
            self.MainScreen.setCurrentIndex(0)
            if not self.fullMenuWidget.isVisible():
                self.pushButton_menu.setChecked(True)
    
    def select_simulation_simple(self, sim_index):
        """Select simulation via index"""
        self.MainScreen.setCurrentIndex(sim_index)
    
    def update_all_values(self):
        """
        Main update loop - calls sub-updates
        This function is called 10 times per second
        """
        # Update process settings (from ProcessSettingsMixin)
        self.update_process_values()
        
        # Update I/O status display (from IOConfigMixin)
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
        except Exception as e:
            # Removed unnecessary print
            pass
            
    def on_connect_toggled(self, checked):
        """Handle connect button press - trigger connection attempt"""
        if not self.mainConfig:
            # Removed unnecessary print
            return
        
        if checked:
            # Removed unnecessary print
            self.mainConfig.tryConnect = True
        else:
            pass # Disconnect is handled by main loop or _apply_ip_change/on_controller_changed

    def on_ip_changed(self, text):
        """Update IP address with throttling"""
        if not self.mainConfig:
            return
        
        self.mainConfig.plcIpAdress = text
        
        self.pending_ip = text
        self.ip_change_timer.stop()
        self.ip_change_timer.start(500)

    def _apply_ip_change(self):
        """Execute disconnect after throttle delay"""
        if not self.pending_ip:
            return
        
        if self.validPlcConnection and hasattr(self, 'plc') and self.plc:
            try:
                if self.plc.isConnected():
                    self.plc.disconnect()
                    # Removed unnecessary print
            except Exception as e:
                # Removed unnecessary print
                pass
            
            self.validPlcConnection = False
            self.plc = None
            
            try:
                self.pushButton_connect.blockSignals(True)
                self.pushButton_connect.setChecked(False)
                self.pushButton_connect.blockSignals(False)
            except AttributeError:
                pass
            
            self.update_connection_status_icon()
        
        self.pending_ip = None

    def _init_network_port_combobox(self):
        """Initialize network port combobox with network adapter names"""
        try:
            import socket
            
            # Clear existing items
            self.comboBox_networkPort.clear()
            
            # Add default "Auto" option
            self.comboBox_networkPort.addItem("Auto (System Default)", "auto")
            
            adapters_found = False
            
            # METHOD 1: Try using WMI (Windows only - MOST DETAILED)
            # Shows: "Realtek USB FE Family Controller (192.168.1.100)"
            try:
                import wmi
                
                c = wmi.WMI()
                for interface in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
                    if interface.IPAddress:
                        ipv4_addr = None
                        # Get first IPv4 address
                        for ip in interface.IPAddress:
                            if '.' in ip and not ip.startswith('127.'):
                                ipv4_addr = ip
                                break
                        
                        if ipv4_addr:
                            adapter_name = interface.Description
                            display_name = f"{adapter_name} ({ipv4_addr})"
                            # Store the interface description as identifier
                            self.comboBox_networkPort.addItem(display_name, adapter_name)
                            adapters_found = True
                            # Removed unnecessary print
                
                if adapters_found:
                    # Removed unnecessary print
                    pass
                
            except ImportError:
                # Removed unnecessary print
                pass
            except Exception as e:
                # Removed unnecessary print
                pass
            
            # METHOD 2: Try using psutil (cross-platform)
            # Shows: "Ethernet (192.168.1.100)"
            if not adapters_found:
                try:
                    import psutil
                    
                    # Get all network interfaces with their stats
                    net_if_addrs = psutil.net_if_addrs()
                    net_if_stats = psutil.net_if_stats()
                    
                    for interface_name, addresses in net_if_addrs.items():
                        # Skip interfaces that are down
                        if interface_name in net_if_stats:
                            if not net_if_stats[interface_name].isup:
                                continue
                        
                        # Find IPv4 address (for display info only)
                        ipv4_addr = None
                        for addr in addresses:
                            if addr.family == socket.AF_INET:  # IPv4
                                ipv4_addr = addr.address
                                break
                        
                        # Add adapter (show IP for info, but store interface name)
                        if ipv4_addr and ipv4_addr != '127.0.0.1':
                            display_name = f"{interface_name} ({ipv4_addr})"
                            self.comboBox_networkPort.addItem(display_name, interface_name)
                            adapters_found = True
                            # Removed unnecessary print
                    
                    if adapters_found:
                        # Removed unnecessary print
                        pass
                
                except ImportError:
                    # Removed unnecessary print
                    pass
                except Exception as e:
                    # Removed unnecessary print
                    pass
            
            # METHOD 3: Fallback - basic socket method
            if not adapters_found:
                # Removed unnecessary print
                try:
                    # Get local IP for display
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    s.close()
                    
                    self.comboBox_networkPort.addItem(f"Primary Adapter ({local_ip})", "primary")
                    adapters_found = True
                    # Removed unnecessary print
                except Exception as e:
                    # Removed unnecessary print
                    pass
            
            # Connect signal (NO auto-fill of IP address)
            self.comboBox_networkPort.currentIndexChanged.connect(self._on_network_port_changed)
            
            # Removed unnecessary print
            
        except AttributeError:
            # Removed unnecessary print
            pass
        except Exception as e:
            # Removed unnecessary print
            pass

    def _on_network_port_changed(self, index):
        """Called when network port selection changes - only logs selection"""
        try:
            selected_adapter = self.comboBox_networkPort.currentData()
            adapter_name = self.comboBox_networkPort.currentText()
            
            # Just log the selection, DO NOT change IP address field
            # Removed unnecessary print
            
            # Store the selected adapter in config if needed
            if hasattr(self, 'mainConfig') and self.mainConfig:
                if not hasattr(self.mainConfig, 'selectedNetworkAdapter'):
                    self.mainConfig.selectedNetworkAdapter = selected_adapter
                else:
                    self.mainConfig.selectedNetworkAdapter = selected_adapter
        
        except Exception as e:
            # Removed unnecessary print
            pass


# =============================================================================
# Main Application Entry Point
# =============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    current_dir = Path(__file__).parent
    gui_common_dir = current_dir.parent / "guiCommon"
    style_file = gui_common_dir / "style.qss"

    if os.path.exists(style_file):
        try:
            with open(style_file, "r") as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            # Removed unnecessary print
            pass
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())