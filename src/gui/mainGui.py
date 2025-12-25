# mainGui.py - Main GUI entry point and navigation
# Alternative version with absolute imports

import sys
import os
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout, QPushButton, QDockWidget
from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve
from PyQt5 import uic

# ============================================================================
# ABSOLUTE IMPORTS - Add src directory to path
# ============================================================================
current_dir = Path(__file__).parent

# Import from same directory using relative imports
from .pages.generalSettings import ProcessSettingsMixin
from .pages.ioConfigPage import IOConfigMixin
from .pages.generalControls import GeneralControlsMixin
from .pages.simPage import SimPageMixin
# Tank simulation settings mixin from simulations package
from simulations.PIDtankValve.settingsGui import TankSimSettingsMixin

# Import from new structure
from simulations.PIDtankValve.gui import VatWidget
# TODO: conveyor simulation not yet migrated
# from simulations.conveyorSim.SimGui import TransportbandWidget
from core.configuration import configuration

# =============================================================================
# Resource and UI compilation (dynamic)
# =============================================================================
gui_media_dir = current_dir / "media"

qrc_file = gui_media_dir / "Resource.qrc"
rc_py_file = gui_media_dir / "Resource_rc.py"

if qrc_file.exists():
    try:
        subprocess.run(
            ["pyrcc5", str(qrc_file), "-o", str(rc_py_file)],
            check=True
        )

        if str(gui_media_dir) not in sys.path:
            sys.path.insert(0, str(gui_media_dir))

        try:
            import Resource_rc  # type: ignore[import-not-found]
        except ImportError as e:
            pass

    except subprocess.CalledProcessError as e:
        pass
    except Exception as e:
        pass

# Ensure gui_media_dir is in path so Resource_rc can be found
if str(gui_media_dir) not in sys.path:
    sys.path.insert(0, str(gui_media_dir))

# Load UI
ui_file = gui_media_dir / "mainWindowPIDRegelaarSim.ui"

if ui_file.exists():
    Ui_MainWindow, QtBaseClass = uic.loadUiType(str(ui_file))
else:
    raise FileNotFoundError(f"Cannot find {ui_file}! Searched in: {ui_file}")



# =============================================================================
# MainWindow class - Same as before
# =============================================================================
class MainWindow(QMainWindow, Ui_MainWindow, ProcessSettingsMixin, IOConfigMixin, GeneralControlsMixin, SimPageMixin, TankSimSettingsMixin):
    """
    Main application window
    Uses mixins for process settings and I/O config functionality
    """

    def __init__(self, mainConfig=None):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        # Set a smaller default window height
        self.resize(self.width(), 800)
        # Ensure fullscreen action is enabled if present
        if hasattr(self, 'actionFullscreen'):
            self.actionFullscreen.setEnabled(True)
            self.actionFullscreen.setVisible(True)
            self.actionFullscreen.triggered.connect(self.showFullScreen)
        
        # Store reference to main configuration BEFORE initializing mixins
        self.mainConfig = mainConfig
        self.tanksim_config = None
        self.tanksim_status = None

        # Sidebar: start collapsed (animate width), keep both widgets available
        try:
            self.fullMenuWidget.setVisible(True)
            self.fullMenuWidget.setMaximumWidth(0)
            # Restore dual-sidebar behavior
            self.iconOnlyWidget.setVisible(True)
            self.pushButton_menu.setChecked(False)
            self.pushButton_menu.toggled.connect(self.toggle_menu)
        except Exception:
            pass

        # Initialize GENERAL CONTROLS page and dock default state
        try:
            self.init_general_controls_page()
        except Exception:
            pass

        # Connect exit buttons
        self.pushButton_Exit.clicked.connect(self.close)

        # Initialize connection variables
        self.validPlcConnection = False
        self.plc = None

        # Auto-retry connect timer
        self.connect_retry_timer = QTimer()
        self.connect_retry_timer.setInterval(8000)
        self.connect_retry_timer.timeout.connect(self._auto_retry_connect)

        # Float window state
        self.floated_window = None
        self.current_sim_page = None

        # IP throttling
        self.ip_change_timer = QTimer()
        self.ip_change_timer.setSingleShot(True)
        self.ip_change_timer.timeout.connect(self._apply_ip_change)
        self.pending_ip = None

        # Main update timer (start after pages init)
        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_all_values)

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

        # Connect navigation buttons (moved to SimPageMixin)
        self.connect_navigation_buttons()

        # Connect simulation buttons (moved to SimPageMixin)
        self.connect_simulation_buttons()

        # Initialize GUI mode
        QTimer.singleShot(100, self._initialize_gui_mode)

        # Kick off updates and connection icon after init
        try:
            self.update_connection_status_icon()
        except Exception:
            pass
        self.timer.start()
    def _initialize_gui_mode(self):
        """Initialize GUI mode after mainConfig is available"""
        if hasattr(self, 'mainConfig') and self.mainConfig:
            self.mainConfig.plcGuiControl = "gui"
            self.mainConfig.plcProtocol = "GUI"
        else:
            QTimer.singleShot(100, self._initialize_gui_mode)

    def _maybe_confirm_leave_io(self) -> bool:
        """Return True to allow leaving IO page; False if user cancels.
        Triggers when IO config is dirty and current page is IO.
        """
        try:
            # Detect IO page by widget rather than hard-coded index
            io_page = self.findChild(QWidget, "IOPage")
            is_on_io_page = (self.MainScreen.currentWidget() == io_page)
            io_dirty = getattr(self, "_io_config_dirty", False)
            if is_on_io_page and io_dirty:
                from PyQt5.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self,
                    "IO configuration not activated",
                    "You have IO configuration changes that are not activated. Continue without reloading?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                return reply == QMessageBox.Yes
            return True
        except Exception:
            return True

    # Sidebar animation helpers
    def _setup_menu_animation(self):
        try:
            self._menu_anim = QPropertyAnimation(self.fullMenuWidget, b"maximumWidth", self)
            self._menu_anim.setDuration(600)
            self._menu_anim.setEasingCurve(QEasingCurve.OutQuart)
            self._menu_anim.finished.connect(self._on_menu_anim_finished)
        except Exception:
            self._menu_anim = None

    def toggle_menu(self, checked):
        try:
            if not hasattr(self, "_menu_anim") or self._menu_anim is None:
                self._setup_menu_animation()
            target_width = 240 if checked else 0
            # Ensure full menu is visible during animation
            self.fullMenuWidget.setVisible(True)
            # Hide icon-only immediately when opening; show only after close completes
            if checked:
                self.iconOnlyWidget.setVisible(False)
            if hasattr(self, "_menu_anim") and self._menu_anim:
                self._menu_anim.stop()
                self._menu_anim.setStartValue(self.fullMenuWidget.maximumWidth())
                self._menu_anim.setEndValue(target_width)
                self._menu_anim.start()
        except Exception:
            pass

    def _on_menu_anim_finished(self):
        try:
            expanded = self.fullMenuWidget.maximumWidth() > 0
            # Toggle icon-only vs full menu visibility
            self.iconOnlyWidget.setVisible(not expanded)
            self.fullMenuWidget.setVisible(True)
        except Exception:
            pass


    def update_all_values(self):
        """Main update loop"""
        self.update_tanksim_display()  
        self.write_gui_values_to_status() 
        self._write_general_controls_to_status()
        self.update_io_status_display()
        # Sync General Controls dock UI from status/PLC
        self._update_general_controls_ui()
        # Update connection status icon (handles timeout detection)
        self.update_connection_status_icon()


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
        except Exception:            pass

    def on_connect_toggled(self, checked):
        """Handle connect button"""
        if not self.mainConfig:
            return
        if checked:
            # Connect request
            self.mainConfig.tryConnect = True
            if not self.validPlcConnection:
                self.connect_retry_timer.start()
        else:
            # Disconnect request
            self.connect_retry_timer.stop()
            if self.validPlcConnection and hasattr(self, 'plc') and self.plc:
                try:
                    self.iconOnlyWidget.setVisible(False)
                    self.plc.disconnect()
                    print("\nDisconnected from PLC")
                except Exception as e:
                    print(f"\nError disconnecting: {e}")
                    pass
                self.validPlcConnection = False
                self.plc = None
                self.update_connection_status_icon()

    def _auto_retry_connect(self):
        if self.pushButton_connect.isChecked() and not self.validPlcConnection:
            print("Auto-retrying PLC connection...")
            self.mainConfig.tryConnect = True
        else:
            self.connect_retry_timer.stop()

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
            except Exception:                pass

            self.validPlcConnection = False
            self.plc = None

            try:
                self.pushButton_connect.blockSignals(True)
                self.pushButton_connect.setChecked(False)
                self.pushButton_connect.blockSignals(False)
            except Exception:                pass

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
            except Exception:                pass

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
                except Exception:                    pass

            if not adapters_found:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    s.close()
                    self.comboBox_networkPort.addItem(f"Primary Adapter ({local_ip})", "primary")
                except Exception:                    pass

            self.comboBox_networkPort.currentIndexChanged.connect(self._on_network_port_changed)
        except Exception:            pass

    def _on_network_port_changed(self, index):
        """Handle network port change"""
        try:
            selected_adapter = self.comboBox_networkPort.currentData()
            if hasattr(self, 'mainConfig') and self.mainConfig:
                self.mainConfig.selectedNetworkAdapter = selected_adapter
        except Exception:            pass

    def closeEvent(self, event):
        """Handle window close event"""
        # Set exit flag so main loop will terminate
        if hasattr(self, 'mainConfig') and self.mainConfig:
            self.mainConfig.doExit = True
        
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
        except Exception:            pass

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
