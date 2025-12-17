# tankSimSettingsPage.py - Tank Simulation Specific Settings
# Handles:
# - VatWidget (tank visualization)
# - Tank-specific UI elements (valves, heater, color, etc.)
# - Reading from simulation status
# - Writing GUI inputs to simulation status

from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from tankSim.gui import VatWidget


class TankSimSettingsMixin:
    """
    Mixin class for tank simulation specific functionality
    Combined with MainWindow via multiple inheritance
    """

    def init_tanksim_settings_page(self):
        """Initialize all tank simulation page components"""
        self._init_vat_widget()
        self._init_color_dropdown()
        self._init_checkboxes()
        self._init_entry_fields()
        self._init_simulation_button()

    def _init_vat_widget(self):
        """Initialize VatWidget (tank visualization)"""
        try:
            self.vat_widget = VatWidget()
            container = self.findChild(QWidget, "vatWidgetContainer")

            if container:
                existing_layout = container.layout()
                if existing_layout is None:
                    container_layout = QVBoxLayout(container)
                    container_layout.setContentsMargins(0, 0, 0, 0)
                else:
                    container_layout = existing_layout
                    container_layout.setContentsMargins(0, 0, 0, 0)

                container_layout.addWidget(self.vat_widget)
        except Exception as e:
            pass

    def _init_color_dropdown(self):
        """Initialize water color dropdown"""
        try:
            self.kleurDropDown.clear()
            colors = [
                ("Blue", "#0000FF"),
                ("Red", "#FB5C5C"),
                ("Green", "#00FF00"),
                ("Yellow", "#FAFA2B"),
                ("Orange", "#FFB52B"),
                ("Purple", "#800080"),
                ("Gray", "#808080"),
            ]
            for name, hexcode in colors:
                self.kleurDropDown.addItem(name, hexcode)

            self.kleurDropDown.currentIndexChanged.connect(self.on_kleur_changed)
        except AttributeError:
            pass

    def _init_checkboxes(self):
        """Connect all tank-specific checkboxes"""
        try:
            self.regelbareKlepenCheckBox.toggled.connect(self.on_tank_config_changed)
            self.regelbareWeerstandCheckBox.toggled.connect(self.on_tank_config_changed)
            self.niveauschakelaarCheckBox.toggled.connect(self.on_tank_config_changed)
            self.analogeWaardeTempCheckBox.toggled.connect(self.on_tank_config_changed)
        except AttributeError:
            pass

    def _init_entry_fields(self):
        """Synchronize entry fields (flow and temp)"""
        try:
            self.entryGroupDebiet = [
                self.toekomendDebietEntry,
                self.toekomendDebietEntry1,
                self.toekomendDebietEntry2
            ]
            self.entryGroupTemp = [
                self.tempWeerstandEntry,
                self.tempWeerstandEntry1
            ]

            for group in (self.entryGroupDebiet, self.entryGroupTemp):
                for field in group:
                    field.textChanged.connect(
                        lambda text, g=group: self.syncFields(text, g))
        except AttributeError:
            pass

    def _init_simulation_button(self):
        """Initialize simulation start/stop button"""
        try:
            self.pushButton_startSimulatie.setCheckable(True)
            self.pushButton_startSimulatie.toggled.connect(self.toggle_simulation)
            self.pushButton_startSimulatie.setText("START SIMULATIE")
            self.pushButton_startSimulatie.setStyleSheet("""
                QPushButton {
                    background-color: #44FF44;
                    color: black;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #00CC00;
                }
            """)
        except AttributeError:
            pass

    # =========================================================================
    # UPDATE LOOP - Called from main timer
    # =========================================================================
    
    def update_tanksim_display(self):
        """
        Update tank visualization from simulation status
        Called from main update loop
        
        DATAFLOW: status → GUI display → SVG
        """
        if not hasattr(self, 'tanksim_status') or self.tanksim_status is None:
            return

        # Step 1: Read simulation values from status object
        import tankSim.gui as gui_module
        gui_module.currentHoogteVat = self.tanksim_status.liquidVolume
        gui_module.tempVat = self.tanksim_status.liquidTemperature

        # Step 2: Update VatWidget configuration from UI
        try:
            self.vat_widget.toekomendDebiet = int(self.toekomendDebietEntry.text() or 0)
            self.vat_widget.tempWeerstand = float(self.tempWeerstandEntry.text() or 20.0)
            
            # Checkbox states
            self.vat_widget.regelbareKleppen = self.regelbareKlepenCheckBox.isChecked()
            self.vat_widget.regelbareWeerstand = self.regelbareWeerstandCheckBox.isChecked()
            self.vat_widget.niveauschakelaar = self.niveauschakelaarCheckBox.isChecked()
            self.vat_widget.analogeWaardeTemp = self.analogeWaardeTempCheckBox.isChecked()
            
            # Water color
            self.vat_widget.kleurWater = self.kleurDropDown.currentData()
            
            # Controller mode (from general settings)
            if hasattr(self, 'mainConfig') and self.mainConfig:
                controller_mode = self.mainConfig.plcProtocol
                self.vat_widget.controler = controller_mode
            
            # Step 3: Update GUI panel visibility
            self._update_gui_panel_visibility()
            
            # Step 4: Read valve positions from GUI
            self._read_valve_positions()
            
        except Exception:
            pass

        # Step 5: Rebuild SVG with new values
        self.vat_widget.rebuild()

    def _update_gui_panel_visibility(self):
        """Show/hide GUI control panels based on controller mode"""
        try:
            is_gui_mode = (hasattr(self, 'mainConfig') and 
                          self.mainConfig and 
                          self.mainConfig.plcGuiControl == "gui")
            
            if is_gui_mode and self.vat_widget.regelbareKleppen:
                if not self.regelbareKlepenGUISim.isVisible():
                    self.GUiSim.hide()
                    self.regelbareKlepenGUISim.show()
            elif is_gui_mode and not self.vat_widget.regelbareKleppen:
                if not self.GUiSim.isVisible():
                    self.regelbareKlepenGUISim.hide()
                    self.GUiSim.show()
            else:
                if self.GUiSim.isVisible() or self.regelbareKlepenGUISim.isVisible():
                    self.GUiSim.hide()
                    self.regelbareKlepenGUISim.hide()
        except AttributeError:
            pass

    def _read_valve_positions(self):
        """Read valve positions from GUI controls"""
        if self.vat_widget.regelbareKleppen:
            # Analog control (0-100%)
            try:
                self.vat_widget.KlepStandBoven = int(self.klepstandBovenEntry.text() or 0)
            except (ValueError, AttributeError):
                self.vat_widget.KlepStandBoven = 0
            try:
                self.vat_widget.KlepStandBeneden = int(self.klepstandBenedenEntry.text() or 0)
            except (ValueError, AttributeError):
                self.vat_widget.KlepStandBeneden = 0
        else:
            # Digital control (ON/OFF)
            try:
                top_checked = self.klepstandBovenCheckBox.isChecked()
                bottom_checked = self.klepstandBenedenCheckBox.isChecked()
                self.vat_widget.KlepStandBoven = 100 if top_checked else 0
                self.vat_widget.KlepStandBeneden = 100 if bottom_checked else 0
            except AttributeError:
                pass

    def write_gui_values_to_status(self):
        """
        Write GUI control values to simulation status
        Only in GUI mode - in PLC mode, values come from PLC
        
        DATAFLOW: GUI controls → status → simulation
        """
        if not hasattr(self, 'tanksim_status') or self.tanksim_status is None:
            return
        
        if not hasattr(self, 'mainConfig') or self.mainConfig is None:
            return
        
        # Only write in GUI mode
        if self.mainConfig.plcGuiControl != "gui":
            return
        
        # Write valve positions
        self.tanksim_status.valveInOpenFraction = self.vat_widget.KlepStandBoven / 100.0
        self.tanksim_status.valveOutOpenFraction = self.vat_widget.KlepStandBeneden / 100.0
        
        # Write heater state
        if self.vat_widget.regelbareWeerstand:
            # TODO: Implement analog heater control
            self.tanksim_status.heaterPowerFraction = 0.5
        else:
            try:
                heater_on = self.weerstandCheckBox.isChecked()
                self.tanksim_status.heaterPowerFraction = 1.0 if heater_on else 0.0
            except:
                self.tanksim_status.heaterPowerFraction = 0.0

    # =========================================================================
    # UI CALLBACKS
    # =========================================================================

    def on_kleur_changed(self):
        """Callback when water color changes"""
        new_color = self.kleurDropDown.currentData()
        self.vat_widget.kleurWater = new_color

    def on_tank_config_changed(self):
        """Callback when tank configuration changes"""
        pass  # Handled by update loop

    def syncFields(self, text, group):
        """Synchronize linked entry fields"""
        for field in group:
            if field.text() != text:
                field.blockSignals(True)
                field.setText(text)
                field.blockSignals(False)

    # =========================================================================
    # SIMULATION CONTROL
    # =========================================================================

    def toggle_simulation(self, checked):
        """Toggle simulation on/off with visual feedback"""
        if checked:
            # Start simulation engine
            if hasattr(self, 'tanksim_status') and self.tanksim_status:
                self.tanksim_status.simRunning = True
                
            self.pushButton_startSimulatie.setText("STOP SIMULATIE")
            self.pushButton_startSimulatie.setStyleSheet("""
                QPushButton {
                    background-color: #FF4444;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #CC0000;
                }
            """)
        else:
            # Stop simulation engine
            if hasattr(self, 'tanksim_status') and self.tanksim_status:
                self.tanksim_status.simRunning = False
                
            self.pushButton_startSimulatie.setText("START SIMULATIE")
            self.pushButton_startSimulatie.setStyleSheet("""
                QPushButton {
                    background-color: #44FF44;
                    color: black;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #00CC00;
                }
            """)