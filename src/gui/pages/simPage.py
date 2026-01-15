import logging
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QPushButton, QDialog, QVBoxLayout

logger = logging.getLogger(__name__)


class SimPageMixin:
    def connect_navigation_buttons(self):
        """Connect all navigation buttons to page handlers."""
        try:
            self.pushButton_settingsPage.toggled.connect(lambda checked: self._nav_settings(checked, "settings"))
            self.pushButton_IOPage.toggled.connect(lambda checked: self._nav_io(checked, "io"))
            self.pushButton_simPage.toggled.connect(lambda checked: self._nav_sim(checked, "sim"))
            
            # Connect simulation-specific settings buttons
            try:
                self.pushButton_SimulationSettingsSingleTank.clicked.connect(self.toggle_single_tank_settings)
            except AttributeError:
                pass
            try:
                self.pushButton_SimulationSettingsDualTank.clicked.connect(self.toggle_dual_tank_settings)
            except AttributeError:
                pass
            try:
                self.pushButton_SimulationSettingsConveyor.clicked.connect(self.toggle_conveyor_settings)
            except AttributeError:
                pass
            
            try:
                self.pushButton_generalControls.toggled.connect(self.go_to_general_controls)
            except AttributeError:
                pass
            # Connect the big sidebar buttons (*2 versions)
            try:
                self.pushButton_settingsPage2.toggled.connect(lambda checked: self._nav_settings(checked, "settings"))
            except AttributeError:
                pass
            try:
                self.pushButton_IOPage2.toggled.connect(lambda checked: self._nav_io(checked, "io"))
            except AttributeError:
                pass
            try:
                self.pushButton_simPage2.toggled.connect(lambda checked: self._nav_sim(checked, "sim"))
            except AttributeError:
                pass
            try:
                self.pushButton_generalControls2.toggled.connect(self.go_to_general_controls)
            except AttributeError:
                pass
        except AttributeError:
            pass

    def go_to_settings(self, checked):
        """Navigate to general settings page."""
        if checked:
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
        if checked:
            # Auto-reload IO config before leaving current page
            self._auto_reload_before_page_change()
            self.go_to_settings(True)
            # Auto-close sidebar when navigating
            self._auto_close_sidebar()

    def go_to_io(self, checked):
        """Navigate to I/O page."""
        if checked:
            # Auto-reload IO config before leaving current page
            self._auto_reload_before_page_change()
            self.MainScreen.setCurrentIndex(4)
            # Trigger automatic configuration reload when entering IO page
            # This ensures all communication uses the latest tag addresses
            try:
                io_page = self.findChild(QWidget, "IOPage")
                if io_page and hasattr(io_page, '_auto_reload_io_config'):
                    # Auto-reload without confirmation dialog
                    io_page._auto_reload_io_config()
            except Exception:
                pass

    def _nav_io(self, checked, source):
        if checked:
            # Auto-reload IO config before leaving current page
            self._auto_reload_before_page_change()
            self.go_to_io(True)
            # Auto-close sidebar when navigating
            self._auto_close_sidebar()

    def _nav_sim(self, checked, source):
        if checked:
            # Auto-reload IO config before leaving current page
            self._auto_reload_before_page_change()
            self.go_to_sim_or_selection(True)
            # Auto-close sidebar when navigating
            self._auto_close_sidebar()
    
    def _auto_reload_before_page_change(self):
        """
        Automatically reload IO configuration before leaving a page.
        This ensures all pages have the latest tag addresses when they're accessed.
        """
        try:
            # Find the IO config page
            from PyQt5.QtWidgets import QWidget
            io_page = self.findChild(QWidget, "IOPage")
            if io_page and hasattr(io_page, '_auto_reload_io_config'):
                # Silent auto-reload without user confirmation
                io_page._auto_reload_io_config()
        except Exception:
            pass  # Silently fail if auto-reload not available
    
    def _auto_close_sidebar(self):
        """Auto-close the sidebar after navigation"""
        try:
            if hasattr(self, 'pushButton_menu') and self.pushButton_menu:
                if self.pushButton_menu.isChecked():
                    self.pushButton_menu.setChecked(False)
        except Exception:
            pass
    
    def _start_sim_and_close_sidebar(self, sim_index):
        """Start simulation and auto-close sidebar"""
        self.start_simulation(sim_index)
        self._auto_close_sidebar()
    
    def _close_sim_and_close_sidebar(self):
        """Close simulation and auto-close sidebar"""
        self.close_simulation()
        self._auto_close_sidebar()
    
    def connect_simulation_buttons(self):
        """Connect all simulation related buttons across sidebar and pages."""
        try:
            buttons_PIDtankValve = self.findChildren(QPushButton, "pushButton_PIDtankValve")
            for btn in buttons_PIDtankValve:
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, b=btn: self._start_sim_and_close_sidebar(0))
        except AttributeError:
            pass

        try:
            buttons_dualTank = self.findChildren(QPushButton, "pushButton_dualTank")
            for btn in buttons_dualTank:
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, b=btn: self._start_sim_and_close_sidebar(1))
        except AttributeError:
            pass

        try:
            buttons_conveyor = self.findChildren(QPushButton, "pushButton_conveyor")
            for btn in buttons_conveyor:
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, b=btn: self._start_sim_and_close_sidebar(2))
        except AttributeError:
            pass

        # Close simulation buttons
        try:
            close_btn = self.findChild(QPushButton, "pushButton_PIDtankValve_2")
            if close_btn:
                close_btn.clicked.connect(self._close_sim_and_close_sidebar)
        except AttributeError:
            pass

        try:
            close_btn = self.findChild(QPushButton, "pushButton_closeDualTank")
            if close_btn:
                close_btn.clicked.connect(self._close_sim_and_close_sidebar)
        except AttributeError:
            pass

        try:
            close_btn = self.findChild(QPushButton, "pushButton_closeConveyor")
            if close_btn:
                close_btn.clicked.connect(self._close_sim_and_close_sidebar)
        except AttributeError:
            pass

        # Float buttons per page
        try:
            float_btn = self.singleTankPage.findChild(QPushButton, "pushButton_FloatPIDTankValve")
            if float_btn:
                float_btn.setEnabled(True)
                float_btn.clicked.connect(lambda: self.toggle_float(0))
        except AttributeError:
            pass

        try:
            float_btn = self.dualTankPage.findChild(QPushButton, "pushButton_FloatDualTank")
            if float_btn:
                float_btn.setEnabled(True)
                float_btn.clicked.connect(lambda: self.toggle_float(1))
        except AttributeError:
            pass

        try:
            float_btn = self.conveyorPage.findChild(QPushButton, "pushButton_FloatConveyor")
            if float_btn:
                float_btn.setEnabled(True)
                float_btn.clicked.connect(lambda: self.toggle_float(2))
        except AttributeError:
            pass

        # Ensure any float buttons (in full menu or page) are enabled and wired
        try:
            for btn in self.findChildren(QPushButton, "pushButton_FloatPIDTankValve"):
                btn.setEnabled(True)
                btn.clicked.connect(lambda: self.toggle_float(0))
            for btn in self.findChildren(QPushButton, "pushButton_FloatDualTank"):
                btn.setEnabled(True)
                btn.clicked.connect(lambda: self.toggle_float(1))
            for btn in self.findChildren(QPushButton, "pushButton_FloatConveyor"):
                btn.setEnabled(True)
                btn.clicked.connect(lambda: self.toggle_float(2))
        except Exception:
            pass

    def go_to_sim_or_selection(self, checked):
        """Navigate to active simulation or selection page."""
        if checked:
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
                self.MainScreen.setCurrentIndex(self.current_sim_page)
            else:
                self.MainScreen.setCurrentIndex(5)
            # Prevent sidebar from opening when sim page is clicked
            # try:
            #     if self.fullMenuWidget.maximumWidth() == 0:
            #         self.pushButton_menu.setChecked(True)
            # except Exception:
            #     pass

    def start_simulation(self, sim_index):
        """Start a specific simulation and refresh IO tree."""
        self.current_sim_page = sim_index
        self.MainScreen.setCurrentIndex(sim_index)
        
        # Reset stacked widgets to index 0 (simulation view, not settings)
        try:
            if sim_index == 0:  # Single Tank
                widget = getattr(self, 'ContentStackedWidgetsSingleTank', None)
                if widget:
                    widget.setCurrentIndex(0)
            elif sim_index == 1:  # Dual Tank
                widget = getattr(self, 'ContentStackedWidgetDualTank', None)
                if widget:
                    widget.setCurrentIndex(0)
            elif sim_index == 2:  # Conveyor
                widget = getattr(self, 'ContentStackedWidgetConveyor', None)
                if widget:
                    widget.setCurrentIndex(0)
        except Exception as e:
            logger.error(f"Error resetting stacked widget index: {e}")
        
        try:
            sim_map = {0: "PIDtankValve", 1: "conveyor", 2: "conveyor"}
            sim_name = sim_map.get(sim_index)
            if sim_name and hasattr(self, 'mainConfig') and hasattr(self.mainConfig, 'simulationManager'):
                sm = self.mainConfig.simulationManager
                if sim_name == "PIDtankValve":
                    sm._active_simulation_name = sim_name
                elif sim_name in sm.get_registered_simulations():
                    sm.load_simulation(sim_name)
                else:
                    sm._active_simulation_name = sim_name
            # Load IO tree after simulation name is set
            if hasattr(self, 'load_io_tree'):
                self.load_io_tree()
        except Exception as e:
            logger.error(f"Error starting simulation: {e}", exc_info=True)
        try:
            for btn in self.findChildren(QPushButton, "pushButton_PIDtankValve"):
                btn.blockSignals(True)
                btn.setChecked(sim_index == 0)
                btn.blockSignals(False)
            for btn in self.findChildren(QPushButton, "pushButton_dualTank"):
                btn.blockSignals(True)
                btn.setChecked(sim_index == 1)
                btn.blockSignals(False)
            for btn in self.findChildren(QPushButton, "pushButton_conveyor"):
                btn.blockSignals(True)
                btn.setChecked(sim_index == 2)
                btn.blockSignals(False)
        except Exception:
            pass

    def close_simulation(self):
        """Close current simulation and return to selection page."""
        self.current_sim_page = None
        self.MainScreen.setCurrentIndex(5)
        try:
            for btn in self.findChildren(QPushButton, "pushButton_PIDtankValve"):
                btn.blockSignals(True)
                btn.setChecked(False)
                btn.blockSignals(False)
            for btn in self.findChildren(QPushButton, "pushButton_dualTank"):
                btn.blockSignals(True)
                btn.setChecked(False)
                btn.blockSignals(False)
            for btn in self.findChildren(QPushButton, "pushButton_conveyor"):
                btn.blockSignals(True)
                btn.setChecked(False)
                btn.blockSignals(False)
        except Exception:
            pass
        try:
            if not self.pushButton_simPage.isChecked():
                self.pushButton_simPage.setChecked(True)
        except Exception:
            pass

    def toggle_float(self, sim_index):
        """Float or dock the simulation window."""
        if getattr(self, 'floated_window', None) is None:
            self.float_simulation(sim_index)
        else:
            self.dock_simulation()

    def float_simulation(self, sim_index):
        """Create a floating window for the simulation."""
        print(f"Floating simulation {sim_index}")
        self.floated_window = QDialog(self)
        self.floated_window.setWindowTitle("Simulation - Floating")
        self.floated_window.setWindowFlags(Qt.Window)
        self.floated_window.resize(1000, 800)
        layout = QVBoxLayout(self.floated_window)
        layout.setContentsMargins(0, 0, 0, 0)
        if sim_index == 0:
            page = self.singleTankPage
        elif sim_index == 1:
            page = self.dualTankPage
        else:
            page = self.conveyorPage
        page.setParent(self.floated_window)
        layout.addWidget(page)
        try:
            if sim_index == 0:
                float_btn = page.findChild(QPushButton, "pushButton_FloatPIDTankValve")
            elif sim_index == 1:
                float_btn = page.findChild(QPushButton, "pushButton_FloatDualTank")
            else:
                float_btn = page.findChild(QPushButton, "pushButton_FloatConveyor")
            if float_btn:
                float_btn.setText("⧈ DOCK")
        except Exception:
            pass
        self.floated_window.show()
        self.floated_window.finished.connect(self.dock_simulation)

    def dock_simulation(self):
        """Dock the floating window back."""
        if not getattr(self, 'floated_window', None):
            return
        print(f"Docking simulation {self.current_sim_page}")
        sim_index = self.current_sim_page
        if sim_index == 0:
            page = self.singleTankPage
        elif sim_index == 1:
            page = self.dualTankPage
        else:
            page = self.conveyorPage
        if page:
            self.MainScreen.insertWidget(sim_index, page)
            try:
                if sim_index == 0:
                    float_btn = page.findChild(QPushButton, "pushButton_FloatPIDTankValve")
                elif sim_index == 1:
                    float_btn = page.findChild(QPushButton, "pushButton_FloatDualTank")
                else:
                    float_btn = page.findChild(QPushButton, "pushButton_FloatConveyor")
                if float_btn:
                    float_btn.setText("⧉ FLOAT")
            except Exception:
                pass
        if self.floated_window:
            self.floated_window.close()
            self.floated_window.deleteLater()
            self.floated_window = None

    def toggle_single_tank_settings(self):
        """Toggle ContentStackedWidgetsSingleTank between index 0 and 1."""
        try:
            widget = getattr(self, 'ContentStackedWidgetsSingleTank', None)
            if widget:
                current_index = widget.currentIndex()
                new_index = 1 if current_index == 0 else 0
                widget.setCurrentIndex(new_index)
        except Exception as e:
            logger.error(f"Error toggling single tank settings: {e}")
    
    def toggle_dual_tank_settings(self):
        """Toggle ContentStackedWidgetDualTank between index 0 and 1."""
        try:
            widget = getattr(self, 'ContentStackedWidgetDualTank', None)
            if widget:
                current_index = widget.currentIndex()
                new_index = 1 if current_index == 0 else 0
                widget.setCurrentIndex(new_index)
        except Exception as e:
            logger.error(f"Error toggling dual tank settings: {e}")
    
    def toggle_conveyor_settings(self):
        """Toggle ContentStackedWidgetConveyor between index 0 and 1."""
        try:
            widget = getattr(self, 'ContentStackedWidgetConveyor', None)
            if widget:
                current_index = widget.currentIndex()
                new_index = 1 if current_index == 0 else 0
                widget.setCurrentIndex(new_index)
        except Exception as e:
            logger.error(f"Error toggling conveyor settings: {e}")
