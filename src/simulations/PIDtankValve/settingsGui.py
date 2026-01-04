# tankSimSettingsPage.py - Tank Simulation Specific Settings
# Handles:
# - VatWidget (tank visualization)
# - Tank-specific UI elements (valves, heater, color, etc.)
# - Reading from simulation status
# - Writing GUI inputs to simulation status

import sys
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QStackedWidget

# Add src to path for imports
src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from simulations.PIDtankValve.gui import VatWidget


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
        self._init_pidvalve_mode_toggle()

        # Ensure correct tab index for analog/digital valve control on startup
        # If adjustableValveCheckBox is not checked, set index to 1 (digital)
        try:
            # Find the QStackedWidget for valve control
            stacked_widget = self.findChild(QStackedWidget, "regelingSimGui")
            if stacked_widget is not None and hasattr(self, 'adjustableValveCheckBox'):
                if not self.adjustableValveCheckBox.isChecked():
                    stacked_widget.setCurrentIndex(1)  # Digital
                else:
                    stacked_widget.setCurrentIndex(0)  # Analog
        except Exception as e:
            print(f"Error setting regelingSimGui index: {e}")

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
            else:
                # If container doesn't exist in UI, still create widget
                # It just won't be displayed
                pass
        except Exception as e:
            print(f"Error initializing vat_widget: {e}")
            self.vat_widget = None
            raise

    def _init_color_dropdown(self):
        """Initialize water color dropdown"""
        try:
            self.colorDropDown.clear()
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
                self.colorDropDown.addItem(name, hexcode)

            self.colorDropDown.currentIndexChanged.connect(
                self.on_color_changed)
        except AttributeError:
            pass

    def _init_checkboxes(self):
        """Connect all tank-specific checkboxes"""
        try:
            self.adjustableValveCheckBox.toggled.connect(
                self.on_tank_config_changed)
            self.adjustableHeatingCoilCheckBox.toggled.connect(
                self.on_tank_config_changed)
            self.levelSwitchesCheckBox.toggled.connect(
                self.on_tank_config_changed)
            self.analogValueTempCheckBox.toggled.connect(
                self.on_tank_config_changed)
        except AttributeError:
            pass

    def _init_entry_fields(self):
        """Synchronize entry fields (flow and temp)"""
        try:
            self.entryGroupFlowIn = [
                self.maxFlowInEntry,
                self.maxFlowInEntry1,
                self.maxFlowInEntry2
            ]
            self.entryGroupFlowOut = [
                self.maxFlowOutEntry,
                self.maxFlowOutEntry1,
                self.maxFlowOutEntry2
            ]
            self.entryGroupPower = [
                self.powerHeatingCoilEntry,
                self.powerHeatingCoilEntry1,
                self.powerHeatingCoilEntry2
            ]

            for group in (self.entryGroupFlowIn, self.entryGroupFlowOut, self.entryGroupPower):
                for field in group:
                    field.textChanged.connect(
                        lambda text, g=group: self.syncFields(text, g))
        except AttributeError:
            pass

        # Wire heater power sliders/spinboxes (supports multiple copies in different stacks)
        try:
            self._heater_power_sliders = []
            self._heater_power_value_labels = []
            self._heater_power_spinboxes = []

            # Collect all heater controls that might exist in various pages
            for name in (
                'heaterPowerSlider',
                'heaterPowerSlider_1',
                'heaterPowerSlider_2',
                'heaterPowerSlider_3',
            ):
                slider = getattr(self, name, None)
                if slider is not None:
                    self._heater_power_sliders.append(slider)
                    slider.valueChanged.connect(
                        lambda v, s=slider: self._on_heater_power_any_changed(v, s)
                    )

            for name in (
                'heaterPowerSpinBox',
                'heaterPowerSpinBox_3',
                'heaterPowerSpinBox_4',
            ):
                spin = getattr(self, name, None)
                if spin is not None:
                    self._heater_power_spinboxes.append(spin)
                    spin.valueChanged.connect(
                        lambda v, sp=spin: self._on_heater_power_any_changed(v, sp)
                    )
        except Exception:
            pass

    def _on_heater_power_any_changed(self, value, source=None):
        """Keep all heater power controls in sync and update labels (0-32747)."""
        try:
            # Clamp for safety to 0..32747
            value = max(0, min(32747, int(value)))

            # Sync all sliders
            for slider in getattr(self, '_heater_power_sliders', []):
                if slider is None or slider is source:
                    continue
                slider.blockSignals(True)
                slider.setValue(value)
                slider.blockSignals(False)

            # Update value labels
            try:
                # Collect labels lazily to avoid missing widgets
                if not self._heater_power_value_labels:
                    for name in (
                        'heaterPowerValueLabel',
                        'heaterPowerValueLabel_2',
                        'heaterPowerValueLabel_3',
                    ):
                        lbl = getattr(self, name, None)
                        if lbl is not None:
                            self._heater_power_value_labels.append(lbl)
                for lbl in self._heater_power_value_labels:
                    lbl.setText(str(value))
            except Exception:
                pass

            # Sync all spinboxes
            for spin in getattr(self, '_heater_power_spinboxes', []):
                if spin is None or spin is source:
                    continue
                spin.blockSignals(True)
                spin.setValue(value)
                spin.blockSignals(False)

            # Optionally reflect immediately in status for snappier PLC export
            if hasattr(self, 'tanksim_status') and self.tanksim_status is not None:
                # Map slider value (0..32747) to fraction (0..1)
                self.tanksim_status.heaterPowerFraction = (value / 32747.0) if value > 0 else 0.0
        except Exception:
            pass

    def _init_simulation_button(self):
        """Initialize simulation start/stop button"""
        try:
            self.pushButton_startSimulation.setCheckable(True)
            self.pushButton_startSimulation.toggled.connect(
                self.toggle_simulation)
            self.pushButton_startSimulation.setText("START SIMULATION")
            self.pushButton_startSimulation.setStyleSheet("""
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

    def _init_pidvalve_mode_toggle(self):
        """Initialize PID valve Auto/Manual mode toggle buttons"""
        try:
            # Connect PID valve controls (sliders, buttons, etc.)
            if hasattr(self, 'vat_widget') and self.vat_widget:
                # The VatWidget has the connect_pidvalve_controls method
                # We need to bind it to the main window's widgets
                self._connect_pidvalve_controls_to_main_window()
            
            # Setup Auto/Manual button mutual exclusivity and mode switching
            auto_buttons = []
            man_buttons = []
            
            # Collect all Auto and Manual buttons (there may be duplicates)
            for name in ['pushButton_PidValveAuto', 'pushButton_PidValveAuto_2']:
                btn = getattr(self, name, None)
                if btn:
                    btn.setCheckable(True)
                    auto_buttons.append(btn)
            
            for name in ['pushButton_PidValveMan', 'pushButton_PidValveMan_2']:
                btn = getattr(self, name, None)
                if btn:
                    btn.setCheckable(True)
                    man_buttons.append(btn)
            
            # Default to Auto mode (Manual = PLC mode disabled)
            for btn in auto_buttons:
                btn.setChecked(True)
            for btn in man_buttons:
                btn.setChecked(False)
            
            # Connect all Auto buttons
            for btn in auto_buttons:
                btn.toggled.connect(lambda checked, b=btn: self._on_auto_mode_toggled(checked))
            
            # Connect all Manual buttons
            for btn in man_buttons:
                btn.toggled.connect(lambda checked, b=btn: self._on_manual_mode_toggled(checked))
            
            # Initialize control widget states based on current mode
            self._update_pidvalve_control_states()
            
        except Exception as e:
            print(f"Error initializing PID valve mode toggle: {e}")

    def _connect_pidvalve_controls_to_main_window(self):
        """Connect PID valve sliders and labels at the main window level"""
        try:
            # Connect temperature setpoint slider to label
            slider_temp = getattr(self, 'slider_PidTankTempSP', None)
            label_temp = getattr(self, 'label_PidTankTempSP', None)
            if slider_temp and label_temp:
                # Set range (0-100°C typical for tank temperature)
                slider_temp.setMinimum(0)
                slider_temp.setMaximum(100)
                # Initial display
                label_temp.setText(f"{slider_temp.value()}°C")
                # Connect for live update
                slider_temp.valueChanged.connect(
                    lambda val: label_temp.setText(f"{val}°C")
                )
            
            # Connect level setpoint slider to label
            slider_level = getattr(self, 'slider_PidTankLevelSP', None)
            label_level = getattr(self, 'label_PidTankLevelSP', None)
            if slider_level and label_level:
                # Set range (0-100%)
                slider_level.setMinimum(0)
                slider_level.setMaximum(100)
                # Initial display
                label_level.setText(f"{slider_level.value()}%")
                # Connect for live update
                slider_level.valueChanged.connect(
                    lambda val: label_level.setText(f"{val}%")
                )
        except Exception as e:
            print(f"Error connecting PID valve controls: {e}")

    def _on_auto_mode_toggled(self, checked):
        """Handle Auto mode button toggle"""
        if not checked:
            return  # Ignore unchecking
        
        try:
            # Ensure all Manual buttons are unchecked
            for name in ['pushButton_PidValveMan', 'pushButton_PidValveMan_2']:
                btn = getattr(self, name, None)
                if btn:
                    btn.blockSignals(True)
                    btn.setChecked(False)
                    btn.blockSignals(False)
            
            # Ensure all Auto buttons are checked
            for name in ['pushButton_PidValveAuto', 'pushButton_PidValveAuto_2']:
                btn = getattr(self, name, None)
                if btn:
                    btn.blockSignals(True)
                    btn.setChecked(True)
                    btn.blockSignals(False)
            
            # Update control states (Auto = Manual GUI control enabled)
            self._update_pidvalve_control_states()
        except Exception as e:
            print(f"Error in auto mode toggle: {e}")

    def _on_manual_mode_toggled(self, checked):
        """Handle Manual mode button toggle"""
        if not checked:
            return  # Ignore unchecking
        
        try:
            # Ensure all Auto buttons are unchecked
            for name in ['pushButton_PidValveAuto', 'pushButton_PidValveAuto_2']:
                btn = getattr(self, name, None)
                if btn:
                    btn.blockSignals(True)
                    btn.setChecked(False)
                    btn.blockSignals(False)
            
            # Ensure all Manual buttons are checked
            for name in ['pushButton_PidValveMan', 'pushButton_PidValveMan_2']:
                btn = getattr(self, name, None)
                if btn:
                    btn.blockSignals(True)
                    btn.setChecked(True)
                    btn.blockSignals(False)
            
            # Update control states (Manual = PLC control, GUI disabled)
            self._update_pidvalve_control_states()
        except Exception as e:
            print(f"Error in manual mode toggle: {e}")

    def _update_pidvalve_control_states(self):
        """Enable/disable PID control widgets based on Auto/Manual mode"""
        try:
            # Determine current mode: Auto = True means GUI controls enabled
            is_auto_mode = False
            auto_btn = getattr(self, 'pushButton_PidValveAuto', None)
            if auto_btn:
                is_auto_mode = auto_btn.isChecked()
            
            # List of control widgets that should be disabled in Manual (PLC) mode
            control_widget_names = [
                'slider_PidTankTempSP',
                'slider_PidTankLevelSP',
                'spinBox_PidTempKp',
                'spinBox_PidTempKi', 
                'spinBox_PidTempKd',
                'spinBox_PidLevelKp',
                'spinBox_PidLevelKi',
                'spinBox_PidLevelKd',
                'pushButton_PidValveStart',
                'pushButton_PidValveStop',
                'pushButton_PidValveReset',
            ]
            
            # Enable controls in Auto mode, disable in Manual mode
            for widget_name in control_widget_names:
                widget = getattr(self, widget_name, None)
                if widget:
                    widget.setEnabled(is_auto_mode)
            
            # Update visual styling for mode indication
            self._update_mode_button_styling(is_auto_mode)
            
        except Exception as e:
            print(f"Error updating PID valve control states: {e}")

    def _update_mode_button_styling(self, is_auto_mode):
        """Update button styling to indicate active mode"""
        try:
            active_style = """
                QPushButton {
                    background-color: #10b981;
                    color: white;
                    font-weight: bold;
                    border: 2px solid #059669;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
            """
            inactive_style = """
                QPushButton {
                    background-color: #e5e7eb;
                    color: #6b7280;
                    border: 1px solid #cbd5e0;
                }
                QPushButton:hover {
                    background-color: #d1d5db;
                }
            """
            
            # Apply styling to Auto buttons
            for name in ['pushButton_PidValveAuto', 'pushButton_PidValveAuto_2']:
                btn = getattr(self, name, None)
                if btn:
                    btn.setStyleSheet(active_style if is_auto_mode else inactive_style)
            
            # Apply styling to Manual buttons
            for name in ['pushButton_PidValveMan', 'pushButton_PidValveMan_2']:
                btn = getattr(self, name, None)
                if btn:
                    btn.setStyleSheet(inactive_style if is_auto_mode else active_style)
        except Exception as e:
            print(f"Error updating mode button styling: {e}")

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

        # Check if vat_widget exists, if not try to initialize it
        if not hasattr(self, 'vat_widget') or self.vat_widget is None:
            try:
                self._init_vat_widget()
            except Exception as e:
                print(f"Warning: Could not initialize vat_widget: {e}")
                return

        gui_mode = False
        try:
            gui_mode = (self.mainConfig.plcGuiControl == "gui") if hasattr(self, 'mainConfig') else False
        except Exception:
            gui_mode = False

        # Step 1: Read simulation values from status object
        from simulations.PIDtankValve import gui as gui_module
        gui_module.liquidVolume = self.tanksim_status.liquidVolume
        gui_module.tempVat = self.tanksim_status.liquidTemperature
        # Pass heater power fraction to the VatWidget for coil color
        try:
            self.vat_widget.heaterPowerFraction = float(self.tanksim_status.heaterPowerFraction)
        except Exception:
            self.vat_widget.heaterPowerFraction = 0.0

        # Step 2: Update VatWidget configuration
        try:
            # Use GUI fields in GUI mode; otherwise use live config/status values
            if gui_mode:
                self.vat_widget.valveInMaxFlowValue = int(self.maxFlowInEntry.text() or 5)
                self.vat_widget.valveOutMaxFlowValue = int(self.maxFlowOutEntry.text() or 2)
                self.vat_widget.powerValue = float(self.powerHeatingCoilEntry.text() or 10000.0)
                try:
                    m3_val = float(self.volumeEntry.text() or 2.0)
                except Exception:
                    m3_val = 2.0
                self.vat_widget.levelSwitchMaxHeight = float(self.levelSwitchMaxHeightEntry.text() or 2.0)
                self.vat_widget.levelSwitchMinHeight = float(self.levelSwitchMinHeightEntry.text() or 2.0)
            else:
                cfg = getattr(self, 'tanksim_config', None)
                self.vat_widget.valveInMaxFlowValue = int(cfg.valveInMaxFlow) if cfg and cfg.valveInMaxFlow is not None else 5
                self.vat_widget.valveOutMaxFlowValue = int(cfg.valveOutMaxFlow) if cfg and cfg.valveOutMaxFlow is not None else 2
                self.vat_widget.powerValue = float(cfg.heaterMaxPower) if cfg and cfg.heaterMaxPower is not None else 10000.0
                m3_val = (cfg.tankVolume / 1000.0) if cfg and getattr(cfg, 'tankVolume', None) is not None else 2.0
                self.vat_widget.levelSwitchMaxHeight = (cfg.digitalLevelSensorHighTriggerLevel / cfg.tankVolume * 100.0) if cfg and cfg.tankVolume else 90.0
                self.vat_widget.levelSwitchMinHeight = (cfg.digitalLevelSensorLowTriggerLevel / cfg.tankVolume * 100.0) if cfg and cfg.tankVolume else 10.0

            # UI volume is in m³; simulation uses liters. VatWidget expects maxVolume as liters-per-percent.
            total_volume_liters = max(0.0, m3_val * 1000.0)
            self.vat_widget.maxVolume = total_volume_liters / 100.0 if total_volume_liters > 0 else 1.0
            """ self.timeDelayFilling = float(
                self.timeDelayfillingEntry.text() or 0.0)
            self.ambientTemp = float(self.ambientTempEntry.text() or 21.0)
            self.heatLoss = float(self.heatLossVatEntry.text() or 150.0)
            self.timeDelayTemp = float(self.timeDelayTempEntry.text() or 0.0)
            self.specificWeight = float(
                self.specificWeightEntry.text() or 4186.0)
            self.specificHeatCapacity = float(
                self.specificHeatCapacityEntry.text() or 0.997)
            self.boilingTemp = float(self.boilingTempEntry.text() or 100.0)"""

            # Checkbox states (visibility)
            self.vat_widget.adjustableValve = self.adjustableValveCheckBox.isChecked()
            self.vat_widget.adjustableHeatingCoil = self.adjustableHeatingCoilCheckBox.isChecked()
            self.vat_widget.levelSwitches = self.levelSwitchesCheckBox.isChecked()
            self.vat_widget.analogValueTemp = self.analogValueTempCheckBox.isChecked()

            # Valve positions: in GUI mode use UI fields; in PLC mode reflect status values
            if gui_mode:
                # leave as set elsewhere (processSettingsPage) – nothing to override here
                pass
            else:
                try:
                    self.vat_widget.adjustableValveInValue = int(round(self.tanksim_status.valveInOpenFraction * 100.0))
                    self.vat_widget.adjustableValveOutValue = int(round(self.tanksim_status.valveOutOpenFraction * 100.0))
                except Exception:
                    pass

            # Water color
            self.vat_widget.waterColor = self.colorDropDown.currentData()

            # Controller mode (from general settings)
            if hasattr(self, 'mainConfig') and self.mainConfig:
                controller_mode = self.mainConfig.plcProtocol
                self.vat_widget.controler = controller_mode

            # Step 3: Update GUI panel visibility
            self._update_gui_panel_visibility()

            # Step 4: Read valve positions from GUI only when GUI controls are in charge
            if gui_mode:
                self._read_valve_positions()

        except Exception:
            pass

        # Step 5: Rebuild SVG with new values
        self.vat_widget.rebuild()

    def _update_gui_panel_visibility(self):
        """Show GUI control panels based on controller mode, but never hide them."""
        try:
            is_gui_mode = (hasattr(self, 'mainConfig') and
                           self.mainConfig and
                           self.mainConfig.plcGuiControl == "gui")

            if is_gui_mode and self.vat_widget.adjustableValve:
                self.adjustableVavleGUISim.show()
            elif is_gui_mode and not self.vat_widget.adjustableValve:
                self.GUiSim.show()
            # Do not hide any panels in any case
        except AttributeError:
            pass

    def _read_valve_positions(self):
        """Read valve positions from GUI controls"""
        if self.vat_widget.adjustableValve:
            # Analog control (0-100%)
            try:
                self.vat_widget.adjustableValveInValue = int(
                    self.valveInEntry.text() or 0)
            except (ValueError, AttributeError):
                self.vat_widget.adjustableValveInValue = 0
            try:
                self.vat_widget.adjustableValveOutValue = int(
                    self.valveOutEntry.text() or 0)
            except (ValueError, AttributeError):
                self.vat_widget.adjustableValveOutValue = 0
        else:
            # Digital control (ON/OFF)
            try:
                top_checked = self.valveInCheckBox.isChecked()
                bottom_checked = self.valveOutCheckBox.isChecked()
                self.vat_widget.adjustableValveInValue = 100 if top_checked else 0
                self.vat_widget.adjustableValveOutValue = 100 if bottom_checked else 0
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

        # If PLC is in control, do not overwrite runtime status, but still propagate UI config changes (max flows, power, etc.)
        gui_mode = (self.mainConfig.plcGuiControl == "gui")
        
        # Determine if Auto mode is active (controls enabled)
        is_auto_mode = False
        try:
            auto_btn = getattr(self, 'pushButton_PidValveAuto', None)
            if auto_btn:
                is_auto_mode = auto_btn.isChecked()
        except Exception:
            is_auto_mode = True  # Default to Auto

        # Update PLCControl_PIDControl widget based on GUI mode
        if hasattr(self, 'vat_widget') and self.vat_widget:
            self.vat_widget.set_plc_pidcontrol_index(gui_mode)

        if gui_mode and is_auto_mode:
            # Only write GUI values when in GUI mode AND Auto mode (controls enabled)
            
            # Write PID temperature setpoint
            try:
                slider_temp = getattr(self, 'slider_PidTankTempSP', None)
                if slider_temp:
                    self.tanksim_status.temperatureSetpoint = float(slider_temp.value())
            except Exception:
                pass
            
            # Write PID level setpoint
            try:
                slider_level = getattr(self, 'slider_PidTankLevelSP', None)
                if slider_level:
                    # Convert percentage to actual volume (liters)
                    level_percent = float(slider_level.value())
                    if hasattr(self, 'tanksim_config') and self.tanksim_config:
                        tank_volume = self.tanksim_config.tankVolume
                        self.tanksim_status.levelSetpoint = (level_percent / 100.0) * tank_volume
            except Exception:
                pass
            
            # Write valve positions
            self.tanksim_status.valveInOpenFraction = self.vat_widget.adjustableValveInValue / 100.0
            self.tanksim_status.valveOutOpenFraction = self.vat_widget.adjustableValveOutValue / 100.0

            # Write heater state
            if self.vat_widget.adjustableHeatingCoil:
                # Use the first visible heater slider; fallback to first available
                slider_val = None
                try:
                    for slider in getattr(self, '_heater_power_sliders', []):
                        if slider is None:
                            continue
                        if slider.isVisible():
                            slider_val = int(slider.value())
                            break
                    if slider_val is None:
                        first_slider = next((s for s in getattr(self, '_heater_power_sliders', []) if s is not None), None)
                        if first_slider is not None:
                            slider_val = int(first_slider.value())
                    if slider_val is None:
                        slider_val = 0
                    # Fraction from 0..32747
                    self.tanksim_status.heaterPowerFraction = max(0.0, min(1.0, slider_val / 32747.0))
                except Exception:
                    self.tanksim_status.heaterPowerFraction = 0.0
            else:
                try:
                    heater_on = self.adjustableHeatingCoil.isChecked()
                    self.tanksim_status.heaterPowerFraction = 1.0 if heater_on else 0.0
                except:
                    self.tanksim_status.heaterPowerFraction = 0.0

        # Also push key limits from GUI into the simulation configuration
        # so changes to max flows and heater power affect the physics.
        try:
            if hasattr(self, 'tanksim_config') and self.tanksim_config is not None:
                # Max incoming flow
                try:
                    val_in = float(self.maxFlowInEntry.text()) if hasattr(self, 'maxFlowInEntry') else None
                    if val_in is not None and val_in >= 0:
                        self.tanksim_config.valveInMaxFlow = val_in
                except Exception:
                    pass

                # Max outgoing flow
                try:
                    val_out = float(self.maxFlowOutEntry.text()) if hasattr(self, 'maxFlowOutEntry') else None
                    if val_out is not None and val_out >= 0:
                        self.tanksim_config.valveOutMaxFlow = val_out
                except Exception:
                    pass

                # Heating coil max power (W)
                try:
                    power = float(self.powerHeatingCoilEntry.text()) if hasattr(self, 'powerHeatingCoilEntry') else None
                    if power is not None and power >= 0:
                        self.tanksim_config.heaterMaxPower = power
                except Exception:
                    pass

                # Tank volume (UI in m³) → config in liters
                try:
                    if hasattr(self, 'volumeEntry'):
                        m3 = float(self.volumeEntry.text())
                        if m3 >= 0:
                            self.tanksim_config.tankVolume = m3 * 1000.0
                except Exception:
                    pass

                # Ambient temperature (°C)
                try:
                    if hasattr(self, 'ambientTempEntry'):
                        amb = float(self.ambientTempEntry.text())
                        self.tanksim_config.ambientTemp = amb
                except Exception:
                    pass

                # Tank heat loss (arbitrary units consistent with model)
                try:
                    if hasattr(self, 'heatLossVatEntry'):
                        loss = float(self.heatLossVatEntry.text())
                        if loss >= 0:
                            self.tanksim_config.tankHeatLoss = loss
                except Exception:
                    pass

                # Time delays (sec)
                try:
                    if hasattr(self, 'timeDelayfillingEntry'):
                        td_fill = float(self.timeDelayfillingEntry.text())
                        if td_fill >= 0:
                            self.tanksim_config.liquidVolumeTimeDelay = td_fill
                except Exception:
                    pass
                try:
                    if hasattr(self, 'timeDelayTempEntry'):
                        td_temp = float(self.timeDelayTempEntry.text())
                        if td_temp >= 0:
                            self.tanksim_config.liquidTempTimeDelay = td_temp
                except Exception:
                    pass

                # Level switch triggers (% of tank volume)
                try:
                    if hasattr(self, 'levelSwitchMaxHeightEntry'):
                        hi_pct = float(self.levelSwitchMaxHeightEntry.text())
                    else:
                        hi_pct = None
                except Exception:
                    hi_pct = None

                try:
                    if hasattr(self, 'levelSwitchMinHeightEntry'):
                        lo_pct = float(self.levelSwitchMinHeightEntry.text())
                    else:
                        lo_pct = None
                except Exception:
                    lo_pct = None

                try:
                    tv = self.tanksim_config.tankVolume
                    if hi_pct is not None and tv is not None:
                        self.tanksim_config.digitalLevelSensorHighTriggerLevel = max(0.0, (hi_pct / 100.0) * tv)
                    if lo_pct is not None and tv is not None:
                        self.tanksim_config.digitalLevelSensorLowTriggerLevel = max(0.0, (lo_pct / 100.0) * tv)
                except Exception:
                    pass

                # Liquid properties
                try:
                    # Specific heat capacity (J/kg*K)
                    if hasattr(self, 'specificHeatCapacity'):
                        c = float(self.specificHeatCapacity.text())
                        if c > 0:
                            self.tanksim_config.liquidSpecificHeatCapacity = c
                except Exception:
                    pass

                try:
                    # Density (kg/m³) mapped as specific weight (kg/L) if needed
                    # UI provides kg/m³; convert to kg/L by dividing by 1000
                    if hasattr(self, 'specificWeightEntry'):
                        rho_m3 = float(self.specificWeightEntry.text())
                        if rho_m3 > 0:
                            self.tanksim_config.liquidSpecificWeight = rho_m3 / 1000.0
                except Exception:
                    pass

                try:
                    # Boiling temperature (°C)
                    if hasattr(self, 'boilingTempEntry'):
                        t_boil = float(self.boilingTempEntry.text())
                        if t_boil > 0:
                            self.tanksim_config.liquidBoilingTemp = t_boil
                except Exception:
                    pass
        except Exception:
            # Be resilient to missing widgets during early init
            pass

    # =========================================================================
    # UI CALLBACKS
    # =========================================================================

    def on_color_changed(self):
        """Callback when water color changes"""
        new_color = self.colorDropDown.currentData()
        self.vat_widget.waterColor = new_color

    def on_tank_config_changed(self):
        """Callback when tank configuration changes"""
        # Update the regelingSimGui stacked widget index based on adjustableValveCheckBox
        try:
            stacked_widget = self.findChild(QStackedWidget, "regelingSimGui")
            if stacked_widget is not None and hasattr(self, 'adjustableValveCheckBox'):
                if not self.adjustableValveCheckBox.isChecked():
                    stacked_widget.setCurrentIndex(1)  # Digital
                else:
                    stacked_widget.setCurrentIndex(0)  # Analog
        except Exception as e:
            print(f"Error setting regelingSimGui index: {e}")
        
        # Update vat_widget adjustableValve setting
        if hasattr(self, 'vat_widget'):
            self.vat_widget.adjustableValve = self.adjustableValveCheckBox.isChecked()
            self.vat_widget.updateControlsVisibility()

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

            self.pushButton_startSimulation.setText("STOP SIMULATION")
            self.pushButton_startSimulation.setStyleSheet("""
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

            self.pushButton_startSimulation.setText("START SIMULATION")
            self.pushButton_startSimulation.setStyleSheet("""
                QPushButton {
                    background-color: #44FF44;
                    color: black;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #00CC00;
                }
            """)
