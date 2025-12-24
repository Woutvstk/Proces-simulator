from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QPushButton, QDialog, QVBoxLayout


class SimPageMixin:
    def connect_navigation_buttons(self):
        """Connect all navigation buttons to page handlers."""
        try:
            self.pushButton_settingsPage.toggled.connect(lambda checked: self._nav_settings(checked, "settings"))
            self.pushButton_IOPage.toggled.connect(lambda checked: self._nav_io(checked, "io"))
            self.pushButton_simPage.toggled.connect(lambda checked: self._nav_sim(checked, "sim"))
            try:
                self.pushButton_simSettings.toggled.connect(self.go_to_sim_settings)
            except AttributeError:
                pass
            try:
                self.pushButton_generalControls.toggled.connect(self.go_to_general_controls)
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
            self.go_to_settings(True)

    def go_to_io(self, checked):
        """Navigate to I/O page."""
        if checked:
            self.MainScreen.setCurrentIndex(4)

    def _nav_io(self, checked, source):
        if checked:
            self.go_to_io(True)

    def _nav_sim(self, checked, source):
        if checked:
            self.go_to_sim_or_selection(True)
    def connect_simulation_buttons(self):
        """Connect all simulation related buttons across sidebar and pages."""
        try:
            buttons_PIDtankValve = self.findChildren(QPushButton, "pushButton_PIDtankValve")
            for btn in buttons_PIDtankValve:
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, b=btn: self.start_simulation(0))
        except AttributeError:
            pass

        try:
            buttons_dualTank = self.findChildren(QPushButton, "pushButton_dualTank")
            for btn in buttons_dualTank:
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, b=btn: self.start_simulation(1))
        except AttributeError:
            pass

        try:
            buttons_conveyor = self.findChildren(QPushButton, "pushButton_conveyor")
            for btn in buttons_conveyor:
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, b=btn: self.start_simulation(2))
        except AttributeError:
            pass

        # Close simulation buttons
        try:
            close_btn = self.findChild(QPushButton, "pushButton_PIDtankValve_2")
            if close_btn:
                close_btn.clicked.connect(self.close_simulation)
        except AttributeError:
            pass

        try:
            close_btn = self.findChild(QPushButton, "pushButton_closeDualTank")
            if close_btn:
                close_btn.clicked.connect(self.close_simulation)
        except AttributeError:
            pass

        try:
            close_btn = self.findChild(QPushButton, "pushButton_closeConveyor")
            if close_btn:
                close_btn.clicked.connect(self.close_simulation)
        except AttributeError:
            pass

        # Float buttons per page
        try:
            float_btn = self.singleTankPage.findChild(QPushButton, "pushButton_FloatPIDTankValve")
            if float_btn:
                float_btn.clicked.connect(lambda: self.toggle_float(0))
        except AttributeError:
            pass

        try:
            float_btn = self.dualTankPage.findChild(QPushButton, "pushButton_FloatDualTank")
            if float_btn:
                float_btn.clicked.connect(lambda: self.toggle_float(1))
        except AttributeError:
            pass

        try:
            float_btn = self.conveyorPage.findChild(QPushButton, "pushButton_FloatConveyor")
            if float_btn:
                float_btn.clicked.connect(lambda: self.toggle_float(2))
        except AttributeError:
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
            try:
                if self.fullMenuWidget.maximumWidth() == 0:
                    self.pushButton_menu.setChecked(True)
            except Exception:
                pass

    def start_simulation(self, sim_index):
        """Start a specific simulation and refresh IO tree."""
        self.current_sim_page = sim_index
        self.MainScreen.setCurrentIndex(sim_index)
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
            if hasattr(self, 'load_io_tree'):
                self.load_io_tree()
        except Exception:
            pass
        try:
            if hasattr(self, 'load_io_tree'):
                self.load_io_tree()
        except Exception:
            pass
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

    def go_to_sim_settings(self, checked):
        """Navigate to simulation settings page (ActiveSimSettings page)."""
        if checked:
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
            self.MainScreen.setCurrentIndex(6)
            if hasattr(self, 'stackedWidget_SimSettings'):
                if self.current_sim_page == 0 or self.current_sim_page == 1:
                    self.stackedWidget_SimSettings.setCurrentIndex(1)
                elif self.current_sim_page == 2:
                    self.stackedWidget_SimSettings.setCurrentIndex(2)
                else:
                    self.stackedWidget_SimSettings.setCurrentIndex(0)
