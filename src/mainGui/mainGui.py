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

        # Sidebar: start collapsed (animate width), keep both widgets available
        try:
            self.fullMenuWidget.setVisible(True)
            self.fullMenuWidget.setMaximumWidth(0)
            self.iconOnlyWidget.setVisible(True)
            self.pushButton_menu.setChecked(False)
            self.pushButton_menu.toggled.connect(self.toggle_menu)
        except Exception:
            pass

        # Ensure General Controls dock is not visible at startup and will float when shown
        try:
            if hasattr(self, 'dockWidget_GeneralControls') and self.dockWidget_GeneralControls:
                # Hide at startup and set to floating mode so it won't dock at bottom when shown
                self.dockWidget_GeneralControls.hide()
                try:
                    # Disallow docking anywhere; keep float-only + closable
                    self.dockWidget_GeneralControls.setAllowedAreas(Qt.NoDockWidgetArea)
                    self.dockWidget_GeneralControls.setFeatures(
                        QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable
                    )
                    self.dockWidget_GeneralControls.setFloating(True)
                except Exception:
                    pass
        except Exception:
            pass

        # Ensure GENERAL CONTROLS sidebar buttons are unchecked initially
        try:
            if hasattr(self, 'pushButton_generalControls') and self.pushButton_generalControls:
                self.pushButton_generalControls.blockSignals(True)
                self.pushButton_generalControls.setChecked(False)
                self.pushButton_generalControls.blockSignals(False)
        except Exception:
            pass
        try:
            if hasattr(self, 'pushButton_generalControls2') and self.pushButton_generalControls2:
                self.pushButton_generalControls2.blockSignals(True)
                self.pushButton_generalControls2.setChecked(False)
                self.pushButton_generalControls2.blockSignals(False)
        except Exception:
            pass

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

        # Initialize General Controls sliders (range + labels)
        self._init_general_controls_sliders()

        # Connect navigation buttons
        self.connect_navigation_buttons()

        # Connect simulation buttons
        self.connect_simulation_buttons()

        # Initialize GUI mode
        QTimer.singleShot(100, self._initialize_gui_mode)

        # Kick off updates and connection icon after init
        try:
            self.update_connection_status_icon()
        except Exception:
            pass
        self.timer.start()
    def _init_general_controls_sliders(self):
        """Set slider ranges to 0..32747 and bind labels to show live value."""
        try:
            slider_label_pairs = [
                (getattr(self, 'slider_control1', None), getattr(self, 'label_sliderValue1', None)),
                (getattr(self, 'slider_control2', None), getattr(self, 'label_sliderValue2', None)),
                (getattr(self, 'slider_control3', None), getattr(self, 'label_sliderValue3', None)),
            ]
            for slider, label in slider_label_pairs:
                if slider:
                    slider.setMinimum(0)
                    slider.setMaximum(32747)
                    if label:
                        # Initialize label text
                        try:
                            label.setText(str(int(slider.value())))
                        except Exception:
                            label.setText("0")
                        # Connect updates
                        slider.valueChanged.connect(lambda v, lbl=label: lbl.setText(str(int(v))))
        except Exception:
            pass
        
        # Initialize and connect Start/Stop/Reset buttons
        self._init_general_controls_buttons()

    def _init_general_controls_buttons(self):
        """Initialize Start/Stop/Reset button event handlers."""
        try:
            # Get button references
            btn_start = getattr(self, 'pushButton_control1', None)
            btn_stop = getattr(self, 'pushButton_control2', None)
            btn_reset = getattr(self, 'pushButton_control3', None)
            
            if btn_start:
                btn_start.pressed.connect(lambda: self._on_start_pressed())
                btn_start.released.connect(lambda: self._on_start_released())
            
            if btn_stop:
                btn_stop.pressed.connect(lambda: self._on_stop_pressed())
                btn_stop.released.connect(lambda: self._on_stop_released())
            
            if btn_reset:
                btn_reset.pressed.connect(lambda: self._on_reset_pressed())
                btn_reset.released.connect(lambda: self._on_reset_released())
        except Exception:
            pass

    def _on_start_pressed(self):
        """Handle START button pressed."""
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.generalStartCmd = True

    def _on_start_released(self):
        """Handle START button released."""
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.generalStartCmd = False

    def _on_stop_pressed(self):
        """Handle STOP button pressed."""
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.generalStopCmd = True

    def _on_stop_released(self):
        """Handle STOP button released."""
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.generalStopCmd = False

    def _on_reset_pressed(self):
        """Handle RESET button pressed."""
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.generalResetCmd = True

    def _on_reset_released(self):
        """Handle RESET button released."""
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.generalResetCmd = False


    def _initialize_gui_mode(self):
        """Initialize GUI mode after mainConfig is available"""
        if hasattr(self, 'mainConfig') and self.mainConfig:
            self.mainConfig.plcGuiControl = "gui"
            self.mainConfig.plcProtocol = "GUI"
        else:
            QTimer.singleShot(100, self._initialize_gui_mode)

    def connect_navigation_buttons(self):
        """Connect all navigation buttons"""
        self.pushButton_settingsPage.toggled.connect(lambda checked: self._nav_settings(checked, "settings"))
        self.pushButton_settingsPage2.toggled.connect(lambda checked: self._nav_settings(checked, "settings2"))

        self.pushButton_IOPage.toggled.connect(lambda checked: self._nav_io(checked, "io"))
        self.pushButton_IOPage2.toggled.connect(lambda checked: self._nav_io(checked, "io2"))

        # SIMULATION page navigation
        self.pushButton_simPage.toggled.connect(lambda checked: self._nav_sim(checked, "sim"))
        self.pushButton_simPage2.toggled.connect(lambda checked: self._nav_sim(checked, "sim2"))

        # Simulation settings page navigation
        try:
            self.pushButton_simSettings.toggled.connect(self.go_to_sim_settings)
            self.pushButton_simSettings2.toggled.connect(self.go_to_sim_settings)
        except AttributeError:
            pass

        # General Controls page navigation
        try:
            self.pushButton_generalControls.toggled.connect(self.go_to_general_controls)
            self.pushButton_generalControls2.toggled.connect(self.go_to_general_controls)
        except AttributeError:
            pass

    def connect_simulation_buttons(self):
        """Connect all simulation related buttons"""
        # START SIMULATION BUTTONS - Connect ALL instances (sidebar and ActiveSimulation page)
        try:
            # Find all buttons with name pushButton_1Vat (in sidebar and ActiveSimulation page)
            buttons_1vat = self.findChildren(QPushButton, "pushButton_1Vat")
            for btn in buttons_1vat:
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, b=btn: self.start_simulation(0))
        except AttributeError:
            pass

        try:
            # Find all buttons with name pushButton_2Vatten
            buttons_2vatten = self.findChildren(QPushButton, "pushButton_2Vatten")
            for btn in buttons_2vatten:
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, b=btn: self.start_simulation(1))
        except AttributeError:
            pass

        try:
            # Find all buttons with name pushButton_transportband
            buttons_transportband = self.findChildren(QPushButton, "pushButton_transportband")
            for btn in buttons_transportband:
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, b=btn: self.start_simulation(2))
        except AttributeError:
            pass

        # CLOSE SIMULATION BUTTONS
        try:
            close_btn = self.findChild(QPushButton, "pushButton_closePIDValves")
            if close_btn:
                close_btn.clicked.connect(self.close_simulation)
        except AttributeError:
            pass

        try:
            close_btn = self.findChild(QPushButton, "pushButton_PIDWithMotor")
            if close_btn:
                close_btn.clicked.connect(self.close_simulation)
        except AttributeError:
            pass

        try:
            close_btn = self.findChild(QPushButton, "pushButton_closeConvSim")
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

    def go_to_settings(self, checked):
        """Navigate to general settings page"""
        if checked:
            # Confirm leaving IO page if there are pending changes
            if not self._maybe_confirm_leave_io():
                try:
                    self.pushButton_settingsPage.blockSignals(True)
                    self.pushButton_settingsPage.setChecked(False)
                    self.pushButton_settingsPage.blockSignals(False)
                    self.pushButton_settingsPage2.blockSignals(True)
                    self.pushButton_settingsPage2.setChecked(False)
                    self.pushButton_settingsPage2.blockSignals(False)
                except Exception:
                    pass
                return
            self.MainScreen.setCurrentIndex(3)

    def _nav_settings(self, checked, source):
        """Navigate wrapper for Settings to avoid double-firing"""
        if checked:
            self.go_to_settings(True)
    
    def _nav_io(self, checked, source):
        """Navigate wrapper for IO to avoid double-firing"""
        if checked:
            self.go_to_io(True)
    
    def _nav_sim(self, checked, source):
        """Navigate wrapper for Sim to avoid double-firing"""
        if checked:
            self.go_to_sim_or_selection(True)

    def go_to_io(self, checked):
        """Navigate to I/O page"""
        if checked:
            self.MainScreen.setCurrentIndex(4)

    def go_to_sim_or_selection(self, checked):
        """Navigate to active sim or selection page"""
        if checked:
            # Confirm leaving IO page if there are pending changes
            if not self._maybe_confirm_leave_io():
                try:
                    self.pushButton_simPage.blockSignals(True)
                    self.pushButton_simPage.setChecked(False)
                    self.pushButton_simPage.blockSignals(False)
                    self.pushButton_simPage2.blockSignals(True)
                    self.pushButton_simPage2.setChecked(False)
                    self.pushButton_simPage2.blockSignals(False)
                except Exception:
                    pass
                return
            if self.current_sim_page is not None:
                # Active simulation - go there
                self.MainScreen.setCurrentIndex(self.current_sim_page)
            else:
                # No active simulation - go to selection page (ActiveSimulation page)
                self.MainScreen.setCurrentIndex(5)
            
            # Ensure menu is open
            try:
                if self.fullMenuWidget.maximumWidth() == 0:
                    self.pushButton_menu.setChecked(True)
            except Exception:
                pass

    def go_to_sim_settings(self, checked):
        """Navigate to simulation settings page (ActiveSimSettings page)"""
        if checked:
            # Confirm leaving IO page if there are pending changes
            if not self._maybe_confirm_leave_io():
                try:
                    self.pushButton_simSettings.blockSignals(True)
                    self.pushButton_simSettings.setChecked(False)
                    self.pushButton_simSettings.blockSignals(False)
                    self.pushButton_simSettings2.blockSignals(True)
                    self.pushButton_simSettings2.setChecked(False)
                    self.pushButton_simSettings2.blockSignals(False)
                except Exception:
                    pass
                return
            # Page 6 is ActiveSimSettings
            self.MainScreen.setCurrentIndex(6)
            
            # Update the settings page based on active simulation
            if hasattr(self, 'stackedWidget_SimSettings'):
                if self.current_sim_page == 0 or self.current_sim_page == 1:
                    # Tank simulations
                    self.stackedWidget_SimSettings.setCurrentIndex(1)
                elif self.current_sim_page == 2:
                    # Conveyor simulation
                    self.stackedWidget_SimSettings.setCurrentIndex(2)
                else:
                    # No active simulation
                    self.stackedWidget_SimSettings.setCurrentIndex(0)

    def go_to_general_controls(self, checked):
        """Navigate to General Controls page and toggle dock visibility"""
        try:
            # Confirm leaving IO page if there are pending changes
            if checked and not self._maybe_confirm_leave_io():
                try:
                    self.pushButton_generalControls.blockSignals(True)
                    self.pushButton_generalControls.setChecked(False)
                    self.pushButton_generalControls.blockSignals(False)
                    self.pushButton_generalControls2.blockSignals(True)
                    self.pushButton_generalControls2.setChecked(False)
                    self.pushButton_generalControls2.blockSignals(False)
                except Exception:
                    pass
                return
            page = self.findChild(QWidget, "page_generalControls")
            if checked and page is not None:
                idx = self.MainScreen.indexOf(page)
                if idx != -1:
                    # Prefer setCurrentWidget to avoid hard-coded indices
                    self.MainScreen.setCurrentWidget(page)
                else:
                    # Fallback: silently ignore if page is not part of the stack to avoid warnings
                    pass
            # Show/hide dock accordingly if present; ensure it floats immediately
            if hasattr(self, 'dockWidget_GeneralControls') and self.dockWidget_GeneralControls:
                if checked:
                    try:
                        self.dockWidget_GeneralControls.setFloating(True)
                    except Exception:
                        pass
                    self.dockWidget_GeneralControls.show()
                    try:
                        self.dockWidget_GeneralControls.raise_()
                    except Exception:
                        pass
                else:
                    self.dockWidget_GeneralControls.hide()
        except Exception:
            pass

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

    def start_simulation(self, sim_index):
        """Start a specific simulation"""
        self.current_sim_page = sim_index
        
        # Navigate to the specific simulation page
        self.MainScreen.setCurrentIndex(sim_index)
        
        # Update button states - ALL instances (sidebar and ActiveSimulation page)
        try:
            # Update all pushButton_1Vat buttons
            for btn in self.findChildren(QPushButton, "pushButton_1Vat"):
                btn.blockSignals(True)
                btn.setChecked(sim_index == 0)
                btn.blockSignals(False)
            
            # Update all pushButton_2Vatten buttons
            for btn in self.findChildren(QPushButton, "pushButton_2Vatten"):
                btn.blockSignals(True)
                btn.setChecked(sim_index == 1)
                btn.blockSignals(False)
            
            # Update all pushButton_transportband buttons
            for btn in self.findChildren(QPushButton, "pushButton_transportband"):
                btn.blockSignals(True)
                btn.setChecked(sim_index == 2)
                btn.blockSignals(False)
        except Exception:
            pass

    def close_simulation(self):
        """Close current simulation and return to selection page"""
        
        # Clear current simulation
        self.current_sim_page = None
        
        # Navigate back to ActiveSimulation selection page (page 5)
        self.MainScreen.setCurrentIndex(5)
        
        # Uncheck ALL start button instances (sidebar and ActiveSimulation page)
        try:
            for btn in self.findChildren(QPushButton, "pushButton_1Vat"):
                btn.blockSignals(True)
                btn.setChecked(False)
                btn.blockSignals(False)
            
            for btn in self.findChildren(QPushButton, "pushButton_2Vatten"):
                btn.blockSignals(True)
                btn.setChecked(False)
                btn.blockSignals(False)
            
            for btn in self.findChildren(QPushButton, "pushButton_transportband"):
                btn.blockSignals(True)
                btn.setChecked(False)
                btn.blockSignals(False)
        except Exception:            pass
        
        # Keep simulation page button checked so we stay on selection
        try:
            if not self.pushButton_simPage.isChecked():
                self.pushButton_simPage.setChecked(True)
        except Exception:            pass

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
        except Exception:            pass
        
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
            except Exception:                pass
        
        if self.floated_window:
            self.floated_window.close()
            self.floated_window.deleteLater()
            self.floated_window = None

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

    def _update_general_controls_ui(self):
        """Update General Controls dock widgets from status/PLC values."""
        try:
            status = getattr(self, 'tanksim_status', None)
            if status is None:
                return

            # Update indicator frames colors based on status.indicatorX
            frame_map = [
                getattr(self, 'frame_indicator1', None),
                getattr(self, 'frame_indicator2', None),
                getattr(self, 'frame_indicator3', None),
                getattr(self, 'frame_indicator4', None),
            ]
            indicators = [
                bool(getattr(status, 'indicator1', False)),
                bool(getattr(status, 'indicator2', False)),
                bool(getattr(status, 'indicator3', False)),
                bool(getattr(status, 'indicator4', False)),
            ]
            for frame, is_on in zip(frame_map, indicators):
                if not frame:
                    continue
                try:
                    if is_on:
                        frame.setStyleSheet('background-color: #10b981; border-radius: 10px; border: 1px solid #059669;')
                    else:
                        frame.setStyleSheet('background-color: #e5e7eb; border-radius: 10px; border: 1px solid #cbd5e0;')
                except Exception:
                    pass

            # Update analog LCDs
            lcds = [
                getattr(self, 'lcdNumber_value1', None),
                getattr(self, 'lcdNumber_value2', None),
                getattr(self, 'lcdNumber_value3', None),
            ]
            analogs = [
                int(getattr(status, 'analog1', 0)),
                int(getattr(status, 'analog2', 0)),
                int(getattr(status, 'analog3', 0)),
            ]
            for lcd, val in zip(lcds, analogs):
                if lcd:
                    try:
                        lcd.display(int(val))
                    except Exception:
                        pass

            # In PLC mode, reflect Control1-3 values onto sliders
            try:
                plc_mode = (self.mainConfig.plcGuiControl == 'plc') if hasattr(self, 'mainConfig') and self.mainConfig else False
            except Exception:
                plc_mode = False
            if plc_mode:
                slider_pairs = [
                    (getattr(self, 'slider_control1', None), int(getattr(status, 'generalControl1Value', 0))),
                    (getattr(self, 'slider_control2', None), int(getattr(status, 'generalControl2Value', 0))),
                    (getattr(self, 'slider_control3', None), int(getattr(status, 'generalControl3Value', 0))),
                ]
                for slider, val in slider_pairs:
                    if slider is None:
                        continue
                    try:
                        slider.blockSignals(True)
                        slider.setValue(int(val))
                        slider.blockSignals(False)
                    except Exception:
                        pass
        except Exception:
            pass

    def _write_general_controls_to_status(self):
        """Write General Controls GUI inputs (buttons + sliders) to status in GUI mode."""
        try:
            if not hasattr(self, 'tanksim_status') or self.tanksim_status is None:
                return
            gui_mode = (self.mainConfig.plcGuiControl == 'gui') if hasattr(self, 'mainConfig') and self.mainConfig else False
            # Commands (Start/Stop/Reset) could be wired to buttons; keep simple: not auto-updated here.
            # Sliders: always reflect GUI position into status; ioHandler will publish to PLC inputs in both modes.
            slider_vals = [
                getattr(self, 'slider_control1', None),
                getattr(self, 'slider_control2', None),
                getattr(self, 'slider_control3', None),
            ]
            values = []
            for s in slider_vals:
                try:
                    values.append(int(s.value()) if s is not None else 0)
                except Exception:
                    values.append(0)
            try:
                self.tanksim_status.generalControl1Value = values[0]
                self.tanksim_status.generalControl2Value = values[1]
                self.tanksim_status.generalControl3Value = values[2]
            except Exception:
                pass
        except Exception:
            pass

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
        else:
            # Disconnect request
            if self.validPlcConnection and hasattr(self, 'plc') and self.plc:
                try:
                    if self.plc.isConnected():
                        self.plc.disconnect()
                        print("\nDisconnected from PLC")
                except Exception as e:
                    print(f"\nError disconnecting: {e}")
                    pass
                
                self.validPlcConnection = False
                self.plc = None
                self.update_connection_status_icon()

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
