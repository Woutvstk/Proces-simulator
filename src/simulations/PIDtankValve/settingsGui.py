"""
Tank Simulation Settings Page - GUI page mixin for PID tank simulation settings.

Handles:
- VatWidget (tank visualization) integration
- Tank-specific UI elements (valves, heater, color selection)
- Reading from simulation status
- Writing GUI inputs to simulation status
- PID valve mode controls (Auto/Manual)
- Trend graph management

External Libraries Used:
- PyQt5 (GPL v3) - GUI framework for widgets, layouts, and button groups
"""

from IO.buttonPulseManager import get_button_pulse_manager
from gui.trendGraphWindow import TrendGraphManager
from simulations.PIDtankValve.gui import VatWidget
import sys
import logging
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QStackedWidget, QButtonGroup

logger = logging.getLogger(__name__)

# Add src to path for imports
src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


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
        self._init_pidvalve_control_buttons()  # ADD THIS LINE
        self._init_trend_graphs()

        # Always use analog valve control now (digital removed)
        # Defer control state update until mainConfig is available
        # This will be called in update_tanksim_display which runs in the main loop

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
            logger.error(f"Error initializing vat_widget: {e}")
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
            # Only connect level and temp checkboxes (valve and heating control removed)
            self.levelSwitchesCheckBox.toggled.connect(
                self.on_tank_config_changed)
            self.analogValueTempCheckBox.toggled.connect(
                self.on_tank_config_changed)

            # Set default checked state
            self.levelSwitchesCheckBox.setChecked(True)
            self.analogValueTempCheckBox.setChecked(True)
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
                self.powerHeatingCoilEntry2
            ]

            for group in (self.entryGroupFlowIn, self.entryGroupFlowOut, self.entryGroupPower):
                for field in group:
                    field.textChanged.connect(
                        lambda text, g=group: self.syncFields(text, g))

            # Connect flow entries to update config
            for field in self.entryGroupFlowIn:
                field.textChanged.connect(self._on_flow_in_changed)
            for field in self.entryGroupFlowOut:
                field.textChanged.connect(self._on_flow_out_changed)

            # Connect volume entry to update maxVolume
            if hasattr(self, 'volumeEntry'):
                self.volumeEntry.textChanged.connect(self._on_volume_changed)

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
                        lambda v, s=slider: self._on_heater_power_any_changed(
                            v, s)
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
                        lambda v, sp=spin: self._on_heater_power_any_changed(
                            v, sp)
                    )
        except Exception:
            pass

    def _on_heater_power_any_changed(self, value, source=None):
        """Keep all heater power controls in sync and update labels (0-100%)."""
        try:
            # Clamp to 0..100 (slider is 0-100%)
            value = max(0, min(100, int(value)))

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
                    lbl.setText(f"{value}%")
            except Exception:
                pass

            # Sync all spinboxes
            for spin in getattr(self, '_heater_power_spinboxes', []):
                if spin is None or spin is source:
                    continue
                spin.blockSignals(True)
                spin.setValue(value)
                spin.blockSignals(False)

            # Reflect immediately in status for snappier PLC export
            if hasattr(self, 'tanksim_status') and self.tanksim_status is not None:
                # Convert percentage (0..100) to fraction (0..1)
                self.tanksim_status.heaterPowerFraction = value / 100.0

            # Update vat_widget WITHOUT rebuild - let main loop handle rebuild
            if hasattr(self, 'vat_widget') and self.vat_widget is not None:
                self.vat_widget.heaterPowerFraction = value / 100.0
                # Mark as dirty but don't rebuild - rebuilds are expensive
                self.vat_widget._needs_rebuild = True
        except Exception:
            pass

    def _on_volume_changed(self, text):
        """Handle tank volume entry change"""
        try:
            m3 = float(text)
            if m3 >= 0:
                liters = m3 * 1000.0

                # Update config
                if hasattr(self, 'tanksim_config') and self.tanksim_config:
                    self.tanksim_config.tankVolume = liters

                # Update trend manager with new tank volume
                if hasattr(self, 'trend_manager') and self.trend_manager:
                    self.trend_manager.set_config(tank_volume_max=liters)

                # Update vat_widget maxVolume (in absolute liters)
                if hasattr(self, 'vat_widget') and self.vat_widget:
                    self.vat_widget.maxVolume = liters
        except (ValueError, AttributeError):
            pass

    def _on_flow_in_changed(self, text):
        """Handle max flow in entry change"""
        try:
            flow = float(text)
            if flow >= 0:
                if hasattr(self, 'tanksim_config') and self.tanksim_config:
                    self.tanksim_config.valveInMaxFlow = flow
                if hasattr(self, 'vat_widget') and self.vat_widget:
                    self.vat_widget.valveInMaxFlowValue = int(flow)
        except (ValueError, AttributeError):
            pass

    def _on_flow_out_changed(self, text):
        """Handle max flow out entry change"""
        try:
            flow = float(text)
            if flow >= 0:
                if hasattr(self, 'tanksim_config') and self.tanksim_config:
                    self.tanksim_config.valveOutMaxFlow = flow
                if hasattr(self, 'vat_widget') and self.vat_widget:
                    self.vat_widget.valveOutMaxFlowValue = int(flow)
        except (ValueError, AttributeError):
            pass

    def _init_simulation_button(self):
        """Initialize simulation start/stop button"""
        try:
            self.pushButton_startSimulation.setCheckable(True)
            self.pushButton_startSimulation.toggled.connect(
                self.toggle_simulation)
            self.pushButton_startSimulation.setText("START SIMULATION")
        except AttributeError:
            pass

    def _init_pidvalve_mode_toggle(self):
        """Initialize Auto/Manual toggle - delegates to VatWidget (gui.py) to maintain architecture."""
        try:
            if hasattr(self, 'vat_widget') and self.vat_widget:
                self.vat_widget.init_mainwindow_controls(self)
        except Exception as e:
            logger.error(f"Error initializing PID valve mode toggle: {e}")

    def _init_pidvalve_control_buttons(self):
        """Initialize PID valve control buttons with press/release handlers."""
        try:
            self._button_pulse_manager = get_button_pulse_manager(
                pulse_duration_ms=200)
            button_manager = self._button_pulse_manager

            # Get status object or use None (will be set later)
            status_obj = getattr(self, 'tanksim_status', None)

            # Start button - Uses pidPidValveStartCmd (separate from General Controls)
            btn_start = getattr(self, 'pushButton_PidValveStart', None)
            if btn_start:
                button_manager.register_button(
                    'PidStart', status_obj, 'pidPidValveStartCmd')
                btn_start.pressed.connect(
                    lambda: button_manager.on_button_pressed('PidStart'))
                btn_start.released.connect(
                    lambda: button_manager.on_button_released('PidStart'))
            else:
                pass

            # Stop button - Uses pidPidValveStopCmd (separate from General Controls)
            btn_stop = getattr(self, 'pushButton_PidValveStop', None)
            if btn_stop:
                button_manager.register_button(
                    'PidStop', status_obj, 'pidPidValveStopCmd')
                btn_stop.pressed.connect(
                    lambda: button_manager.on_button_pressed('PidStop'))
                btn_stop.released.connect(
                    lambda: button_manager.on_button_released('PidStop'))
            else:
                pass

            # Reset button - Uses pidPidValveResetCmd (separate from General Controls)
            btn_reset = getattr(self, 'pushButton_PidValveReset', None)
            if btn_reset:
                button_manager.register_button(
                    'PidReset', status_obj, 'pidPidValveResetCmd')
                btn_reset.pressed.connect(
                    lambda: button_manager.on_button_pressed('PidReset'))
                btn_reset.released.connect(
                    lambda: button_manager.on_button_released('PidReset'))
            else:
                pass

            # Radio buttons for temp control - create separate button group for mutual exclusivity
            self._temp_button_group = QButtonGroup()
            self._temp_button_group.setExclusive(True)

            radio_ai_temp = getattr(
                self, 'radioButton_PidTankValveAItemp', None)
            if radio_ai_temp:
                self._temp_button_group.addButton(radio_ai_temp)
                radio_ai_temp.toggled.connect(
                    lambda checked: self._on_radio_toggled('AItemp', checked))
                radio_ai_temp.setChecked(True)  # Set analog as default

            radio_di_temp = getattr(
                self, 'radioButton_PidTankValveDItemp', None)
            if radio_di_temp:
                self._temp_button_group.addButton(radio_di_temp)
                radio_di_temp.toggled.connect(
                    lambda checked: self._on_radio_toggled('DItemp', checked))

            # Radio buttons for level control - create separate button group for mutual exclusivity
            self._level_button_group = QButtonGroup()
            self._level_button_group.setExclusive(True)

            radio_ai_level = getattr(
                self, 'radioButton_PidTankValveAIlevel', None)
            if radio_ai_level:
                self._level_button_group.addButton(radio_ai_level)
                radio_ai_level.toggled.connect(
                    lambda checked: self._on_radio_toggled('AIlevel', checked))
                radio_ai_level.setChecked(True)  # Set analog as default

            radio_di_level = getattr(
                self, 'radioButton_PidTankValveDIlevel', None)
            if radio_di_level:
                self._level_button_group.addButton(radio_di_level)
                radio_di_level.toggled.connect(
                    lambda checked: self._on_radio_toggled('DIlevel', checked))

            # Sliders for setpoints with labels
            slider_temp = getattr(self, 'slider_PidTankTempSP', None)
            label_temp = getattr(self, 'label_PidTankTempSP', None)

            if slider_temp:
                slider_temp.setMinimum(0)
                slider_temp.setMaximum(27648)
                # Set initial value to 20°C (which is 5529 in the 0-27648 range: 0 to 100°C)
                slider_temp.setValue(5529)
                slider_temp.valueChanged.connect(self._on_temp_sp_changed)
                if label_temp:
                    slider_temp.valueChanged.connect(
                        lambda v: self._update_temp_label(label_temp, v))
                    self._update_temp_label(label_temp, slider_temp.value())

            slider_level = getattr(self, 'slider_PidTankLevelSP', None)
            label_level = getattr(self, 'label_PidTankLevelSP', None)

            if slider_level:
                slider_level.setMinimum(0)
                slider_level.setMaximum(27648)
                slider_level.valueChanged.connect(self._on_level_sp_changed)
                if label_level:
                    slider_level.valueChanged.connect(
                        lambda v: self._update_level_label(label_level, v))
                    self._update_level_label(label_level, slider_level.value())
        except Exception as e:
            logger.error(f"Exception in _init_pidvalve_control_buttons: {e}")

    def update_button_manager_status(self):
        """Update button pulse manager with current status object. Call when tanksim_status becomes available."""
        if hasattr(self, '_button_pulse_manager') and self.tanksim_status is not None:
            button_manager = self._button_pulse_manager
            button_manager.set_button_status_obj(
                'PidStart', self.tanksim_status)
            button_manager.set_button_status_obj(
                'PidStop', self.tanksim_status)
            button_manager.set_button_status_obj(
                'PidReset', self.tanksim_status)

    def _on_pid_start_pressed(self):
        """Deprecated - now handled by pulse manager."""
        pass

    def _on_pid_start_released(self):
        """Deprecated - now handled by pulse manager."""
        pass

    def _on_pid_stop_pressed(self):
        """Deprecated - now handled by pulse manager."""
        pass

    def _on_pid_stop_released(self):
        """Deprecated - now handled by pulse manager."""
        pass

    def _on_pid_reset_pressed(self):
        """Deprecated - now handled by pulse manager."""
        pass

    def _on_pid_reset_released(self):
        """Deprecated - now handled by pulse manager."""
        pass

    def _on_radio_toggled(self, radio_type, checked):
        """Handle radio button toggles for temp/level control selection."""
        if not checked:
            return

        try:
            if hasattr(self, 'tanksim_status') and self.tanksim_status:
                # Reset only the group that this radio belongs to
                if radio_type in ['AItemp', 'DItemp']:
                    # Temperature group
                    self.tanksim_status.pidPidTankValveAItempCmd = False
                    self.tanksim_status.pidPidTankValveDItempCmd = False
                elif radio_type in ['AIlevel', 'DIlevel']:
                    # Level group
                    self.tanksim_status.pidPidTankValveAIlevelCmd = False
                    self.tanksim_status.pidPidTankValveDIlevelCmd = False

                # Set the selected one
                if radio_type == 'AItemp':
                    self.tanksim_status.pidPidTankValveAItempCmd = True
                elif radio_type == 'DItemp':
                    self.tanksim_status.pidPidTankValveDItempCmd = True
                elif radio_type == 'AIlevel':
                    self.tanksim_status.pidPidTankValveAIlevelCmd = True
                elif radio_type == 'DIlevel':
                    self.tanksim_status.pidPidTankValveDIlevelCmd = True
        except Exception:
            pass

    def _on_temp_sp_changed(self, value):
        """Handle temperature setpoint slider change."""
        try:
            if hasattr(self, 'tanksim_status') and self.tanksim_status:
                self.tanksim_status.pidPidTankTempSPValue = int(value)
        except Exception as e:
            pass

    def _update_temp_label(self, label, analog_value):
        """Update temperature label from analog slider value (0-27648)."""
        try:
            # Map analog 0-27648 to temperature 0..boilingTemp °C
            boiling_temp = 100.0
            if hasattr(self, 'boilingTempEntry'):
                try:
                    boiling_temp = float(self.boilingTempEntry.text() or 100.0)
                except (ValueError, AttributeError):
                    boiling_temp = 100.0
            elif hasattr(self, 'tanksim_config') and self.tanksim_config:
                boiling_temp = getattr(
                    self.tanksim_config, 'liquidBoilingTemp', 100.0)

            # Map: analog 0-27648 → temp 0 to boiling_temp
            temp_range = boiling_temp - 0
            temp_celsius = 0 + (analog_value / 27648.0) * temp_range
            label.setText(f"{int(round(temp_celsius))}°C")
        except Exception as e:
            label.setText("--")

    def _on_level_sp_changed(self, value):
        """Handle level setpoint slider change."""
        try:
            if hasattr(self, 'tanksim_status') and self.tanksim_status:
                self.tanksim_status.pidPidTankLevelSPValue = int(value)
        except Exception as e:
            pass

    def _update_level_label(self, label, analog_value):
        """Update level label from analog slider value (0-27648 → 0-100%)."""
        try:
            if label is None:
                return
            # Map analog 0-27648 → percentage 0-100%
            level_percent = (analog_value / 27648.0) * 100.0
            label.setText(f"{int(round(level_percent))}%")
        except Exception as e:
            try:
                label.setText("--")
            except:
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

        # Check if vat_widget exists, if not try to initialize it
        if not hasattr(self, 'vat_widget') or self.vat_widget is None:
            try:
                self._init_vat_widget()
            except Exception as e:
                logger.warning(f"Could not initialize vat_widget: {e}")
                return

        gui_mode = False
        try:
            gui_mode = (self.mainConfig.plcGuiControl == "gui") if hasattr(
                self, 'mainConfig') else False
        except Exception:
            gui_mode = False

        # Check manual mode
        manual_mode = False
        try:
            manual_mode = self.vat_widget.is_manual_mode() if hasattr(
                self.vat_widget, 'is_manual_mode') else False
        except Exception:
            manual_mode = False

        # Effective GUI control: either pure GUI mode OR manual override mode
        effective_gui_control = gui_mode or manual_mode

        # Step 1: Read simulation values from status object
        from simulations.PIDtankValve import gui as gui_module
        gui_module.liquidVolume = self.tanksim_status.liquidVolume
        gui_module.tempVat = self.tanksim_status.liquidTemperature
        gui_module.simRunning = self.tanksim_status.simRunning

        # Pass config to VatWidget so it can display signal names from IO configuration
        if hasattr(self, 'tanksim_config') and self.tanksim_config:
            self.vat_widget.config = self.tanksim_config

        # Pass heater power fraction to the VatWidget for coil color
        # BUT only in PLC mode - in manual/GUI mode, keep the user's checkbox value
        if not effective_gui_control:
            try:
                self.vat_widget.heaterPowerFraction = float(
                    self.tanksim_status.heaterPowerFraction)
            except Exception:
                self.vat_widget.heaterPowerFraction = 0.0

        # Step 2: Update VatWidget configuration
        try:
            # Use GUI fields in GUI mode; otherwise use live config/status values
            if gui_mode:
                if hasattr(self, 'maxFlowInEntry'):
                    self.vat_widget.valveInMaxFlowValue = int(
                        self.maxFlowInEntry.text() or 5)
                if hasattr(self, 'maxFlowOutEntry'):
                    self.vat_widget.valveOutMaxFlowValue = int(
                        self.maxFlowOutEntry.text() or 2)
                if hasattr(self, 'powerHeatingCoilEntry'):
                    self.vat_widget.powerValue = float(
                        self.powerHeatingCoilEntry.text() or 10000.0)

                try:
                    if hasattr(self, 'volumeEntry'):
                        volume_text = self.volumeEntry.text()
                        m3_val = float(volume_text or 2.0)
                    else:
                        m3_val = 2.0
                except Exception:
                    m3_val = 2.0

                if hasattr(self, 'levelSwitchMaxHeightEntry'):
                    self.vat_widget.levelSwitchMaxHeight = float(
                        self.levelSwitchMaxHeightEntry.text() or 90.0)
                if hasattr(self, 'levelSwitchMinHeightEntry'):
                    self.vat_widget.levelSwitchMinHeight = float(
                        self.levelSwitchMinHeightEntry.text() or 10.0)
            else:
                cfg = getattr(self, 'tanksim_config', None)
                self.vat_widget.valveInMaxFlowValue = int(
                    cfg.valveInMaxFlow) if cfg and cfg.valveInMaxFlow is not None else 5
                self.vat_widget.valveOutMaxFlowValue = int(
                    cfg.valveOutMaxFlow) if cfg and cfg.valveOutMaxFlow is not None else 2
                self.vat_widget.powerValue = float(
                    cfg.heaterMaxPower) if cfg and cfg.heaterMaxPower is not None else 10000.0
                m3_val = (cfg.tankVolume / 1000.0) if cfg and getattr(cfg,
                                                                      'tankVolume', None) is not None else 2.0
                self.vat_widget.levelSwitchMaxHeight = (
                    cfg.digitalLevelSensorHighTriggerLevel / cfg.tankVolume * 100.0) if cfg and cfg.tankVolume else 90.0
                self.vat_widget.levelSwitchMinHeight = (
                    cfg.digitalLevelSensorLowTriggerLevel / cfg.tankVolume * 100.0) if cfg and cfg.tankVolume else 10.0

            # UI volume is in m³; simulation uses liters. VatWidget expects maxVolume in absolute liters.
            total_volume_liters = max(0.0, m3_val * 1000.0)
            self.vat_widget.maxVolume = total_volume_liters if total_volume_liters > 0 else 200.0
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

            # Checkbox states (visibility) - only update if checkboxes exist
            if hasattr(self, 'adjustableValveCheckBox'):
                self.vat_widget.adjustableValve = self.adjustableValveCheckBox.isChecked()
            else:
                # Always True (analog mode)
                self.vat_widget.adjustableValve = True

            if hasattr(self, 'adjustableHeatingCoilCheckBox'):
                self.vat_widget.adjustableHeatingCoil = self.adjustableHeatingCoilCheckBox.isChecked()
            else:
                # Always True (analog mode)
                self.vat_widget.adjustableHeatingCoil = True

            if hasattr(self, 'levelSwitchesCheckBox'):
                self.vat_widget.levelSwitches = self.levelSwitchesCheckBox.isChecked()
            else:
                self.vat_widget.levelSwitches = True

            if hasattr(self, 'analogValueTempCheckBox'):
                self.vat_widget.analogValueTemp = self.analogValueTempCheckBox.isChecked()
            else:
                self.vat_widget.analogValueTemp = True

            # Valve positions: in GUI mode use UI fields; in PLC mode reflect status values
            if effective_gui_control:
                # leave as set elsewhere (processSettingsPage) – nothing to override here
                # In manual/GUI mode, keep vat_widget values set by event handlers
                pass
            else:
                try:
                    self.vat_widget.adjustableValveInValue = int(
                        round(self.tanksim_status.valveInOpenFraction * 100.0))
                    self.vat_widget.adjustableValveOutValue = int(
                        round(self.tanksim_status.valveOutOpenFraction * 100.0))
                    # Also update heater power from status
                    self.vat_widget.heaterPowerFraction = self.tanksim_status.heaterPowerFraction
                except Exception:
                    pass

                # Update setpoint slider positions and labels in PLC mode
                try:
                    # Update temperature setpoint slider and label
                    slider_temp = getattr(self, 'slider_PidTankTempSP', None)
                    label_temp = getattr(self, 'label_PidTankTempSP', None)
                    if slider_temp and hasattr(self.tanksim_status, 'pidPidTankTempSPValue'):
                        temp_sp_value = int(
                            self.tanksim_status.pidPidTankTempSPValue)
                        # Prevent triggering valueChanged
                        slider_temp.blockSignals(True)
                        slider_temp.setValue(temp_sp_value)
                        slider_temp.blockSignals(False)
                        if label_temp:
                            self._update_temp_label(label_temp, temp_sp_value)

                    # Update level setpoint slider and label
                    slider_level = getattr(self, 'slider_PidTankLevelSP', None)
                    label_level = getattr(self, 'label_PidTankLevelSP', None)
                    if slider_level and hasattr(self.tanksim_status, 'pidPidTankLevelSPValue'):
                        level_sp_value = int(
                            self.tanksim_status.pidPidTankLevelSPValue)
                        # Prevent triggering valueChanged
                        slider_level.blockSignals(True)
                        slider_level.setValue(level_sp_value)
                        slider_level.blockSignals(False)
                        if label_level:
                            self._update_level_label(
                                label_level, level_sp_value)
                except Exception as e:
                    logger.debug(
                        f"Error updating setpoint sliders in PLC mode: {e}")

            # Water color
            self.vat_widget.waterColor = self.colorDropDown.currentData()

            # Controller mode (from general settings)
            if hasattr(self, 'mainConfig') and self.mainConfig:
                controller_mode = self.mainConfig.plcProtocol
                self.vat_widget.controler = controller_mode

            # Step 3: Update GUI panel visibility
            self._update_gui_panel_visibility()

            # Step 4: Read valve positions from GUI only in pure GUI mode
            # (In manual mode, event handlers already update vat_widget values directly)
            if gui_mode and not manual_mode:
                self._read_valve_positions()

        except Exception as e:
            logger.error(f"Error in update_tanksim_display: {e}")
            pass

        # Step 5: Rebuild SVG with new values
        self.vat_widget.rebuild()

        # Step 6: Gray out controls based on mode
        # Gray out if: NOT in GUI mode AND NOT in manual mode (i.e., in PLC auto mode)
        # Otherwise enable controls
        try:
            controls_enabled = gui_mode or manual_mode
            if hasattr(self, 'vat_widget') and hasattr(self.vat_widget, '_update_control_groupboxes'):
                self.vat_widget._update_control_groupboxes(
                    enabled=controls_enabled)
        except Exception as e:
            logger.debug(f"Error updating control visibility: {e}")

        # Step 7: Feed data to trend graphs if they're open
        try:
            if hasattr(self, 'trend_manager'):
                # Calculate temperature setpoint
                temp_setpoint = None
                slider_temp = getattr(self, 'slider_PidTankTempSP', None)
                if slider_temp:
                    # Convert analog value to temperature (0-27648 → 0 to boilingTemp)
                    boiling_temp = getattr(self.tanksim_config, 'liquidBoilingTemp', 100.0) if hasattr(
                        self, 'tanksim_config') else 100.0
                    analog_value = slider_temp.value()
                    temp_range = boiling_temp - 0
                    temp_setpoint = 0 + (analog_value / 27648.0) * temp_range

                # Get tank volume max for level percentage calculation
                tank_volume_max = getattr(self.tanksim_config, 'tankVolume', 200.0) if hasattr(
                    self, 'tanksim_config') else 200.0

                # Add temperature data with PV (%), Setpoint (%), and OP (%)
                # Convert all to percentages: liquidTemperature and setpoint as % of boiling temp
                temp_pv_percent = (self.tanksim_status.liquidTemperature /
                                   boiling_temp * 100.0) if boiling_temp > 0 else 0
                temp_sp_percent = (temp_setpoint / boiling_temp *
                                   100.0) if boiling_temp > 0 and temp_setpoint is not None else 0
                heater_op_percent = self.tanksim_status.heaterPowerFraction * 100.0

                self.trend_manager.add_temperature(
                    pv_value=temp_pv_percent,
                    setpoint_value=temp_sp_percent,
                    output_value=heater_op_percent
                )

                # Update temperature setpoint display
                self.trend_manager.set_temperature_setpoint(temp_sp_percent)

                # Get level setpoint (from slider or status)
                level_setpoint = self.tanksim_status.levelSetpoint if hasattr(
                    self.tanksim_status, 'levelSetpoint') else 100.0
                level_sp_percent = (level_setpoint / tank_volume_max *
                                    100.0) if tank_volume_max > 0 else 0

                # Add level data with PV (%), valve positions (%)
                level_pv_percent = (self.tanksim_status.liquidVolume /
                                    tank_volume_max * 100.0) if tank_volume_max > 0 else 0
                valve_in_percent = self.tanksim_status.valveInOpenFraction * 100.0
                valve_out_percent = self.tanksim_status.valveOutOpenFraction * 100.0

                self.trend_manager.add_level(
                    pv_value=level_pv_percent,
                    setpoint_value=level_sp_percent,
                    valve_in_fraction=valve_in_percent,
                    valve_out_fraction=valve_out_percent
                )

                # Update level setpoint display
                self.trend_manager.set_level_setpoint(level_sp_percent)
        except Exception as e:
            logger.debug(f"Error updating trend graphs: {e}")

    def _update_gui_panel_visibility(self):
        """Show GUI control panels based on controller mode, but never hide them."""
        try:
            is_gui_mode = (hasattr(self, 'mainConfig') and
                           self.mainConfig and
                           self.mainConfig.plcGuiControl == "gui")

            # Always show analog valve controls (digital removed)
            if is_gui_mode:
                self.adjustableVavleGUISim.show()
        except AttributeError:
            pass

    def _read_valve_positions(self):
        """Read valve positions from GUI controls (always analog now)"""
        # Always use analog control (0-100%) - digital removed
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
        # Make sure vat_widget is initialized
        if not hasattr(self, 'vat_widget') or self.vat_widget is None:
            try:
                self._init_vat_widget()
            except Exception:
                return
        # If PLC is in control, do not overwrite runtime status, but still propagate UI config changes (max flows, power, etc.)
        gui_mode = (self.mainConfig.plcGuiControl == "gui")

        # Check if Manual mode is active (even in PLC mode, Manual mode allows GUI control)
        manual_mode = False
        if hasattr(self, 'vat_widget') and self.vat_widget:
            try:
                manual_mode = self.vat_widget.is_manual_mode()
            except Exception:
                manual_mode = False

        # Effective control: GUI mode OR Manual mode allows writing valve/heater values
        effective_gui_control = gui_mode or manual_mode

        # Update PLCControl_PIDControl widget based on GUI mode
        if hasattr(self, 'vat_widget') and self.vat_widget:
            self.vat_widget.set_plc_pidcontrol_index(gui_mode)

        # Update temp slider max based on boiling point from config
        try:
            slider_temp = getattr(self, 'slider_PidTankTempSP', None)
            label_temp = getattr(self, 'label_PidTankTempSP', None)
            if slider_temp and hasattr(self, 'tanksim_config') and self.tanksim_config:
                # Get boiling point and convert to PLC analog range
                boiling_temp = getattr(
                    self.tanksim_config, 'liquidBoilingTemp', 100.0)
                # Temperature range: -50 to boiling_temp, mapped to 0-27648
                # max_analog = ((boiling_temp - (-50)) / 300) * 27648 is WRONG
                # Actually: max_analog should always be 27648 (max analog value)
                # The range -50..boiling_temp is the USER range, not the analog range
                slider_temp.setMaximum(27648)
                # Update label display if slider is at a value
                if label_temp:
                    self._update_temp_label(label_temp, slider_temp.value())
        except Exception:
            pass

        # In GUI mode OR Manual mode, write values from GUI to status
        # This ensures the simulation sees the values the user is inputting
        # In Manual mode with PLC: GUI controls override PLC outputs, but sensors still go to PLC
        if effective_gui_control:
            # Write PID temperature setpoint
            try:
                slider_temp = getattr(self, 'slider_PidTankTempSP', None)
                if slider_temp:
                    self.tanksim_status.temperatureSetpoint = float(
                        slider_temp.value())
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
                        self.tanksim_status.levelSetpoint = (
                            level_percent / 100.0) * tank_volume
            except Exception:
                pass

            # Write valve positions - CRITICAL: Always write these in GUI mode or Manual mode
            try:
                self.tanksim_status.valveInOpenFraction = self.vat_widget.adjustableValveInValue / 100.0
                self.tanksim_status.valveOutOpenFraction = self.vat_widget.adjustableValveOutValue / 100.0
            except Exception as e:
                logger.error(f"Error writing valve positions: {e}")

            # Write heater state (always analog mode now)
            try:
                # Analog mode: Use the first visible heater slider; fallback to first available
                slider_val = None
                try:
                    for slider in getattr(self, '_heater_power_sliders', []):
                        if slider is None:
                            continue
                        if slider.isVisible():
                            slider_val = int(slider.value())
                            break
                    if slider_val is None:
                        first_slider = next(
                            (s for s in getattr(self, '_heater_power_sliders', []) if s is not None), None)
                        if first_slider is not None:
                            slider_val = int(first_slider.value())
                    if slider_val is None:
                        slider_val = 0
                    # Convert from percentage (0-100) to fraction (0-1)
                    self.tanksim_status.heaterPowerFraction = max(
                        0.0, min(1.0, slider_val / 100.0))
                except Exception:
                    self.tanksim_status.heaterPowerFraction = 0.0
            except Exception as e:
                logger.error(f"Error writing heater state: {e}")
        else:
            # In PLC mode (automatic), convert IO value to levelSetpoint
            # The IO handler reads pidPidTankLevelSPValue from PLC (0-27648)
            # Convert it to levelSetpoint in liters for simulation
            try:
                if hasattr(self.tanksim_status, 'pidPidTankLevelSPValue') and hasattr(self, 'tanksim_config') and self.tanksim_config:
                    level_analog = float(
                        self.tanksim_status.pidPidTankLevelSPValue)
                    # Convert 0-27648 to 0-100% then to liters
                    level_percent = (level_analog / 27648.0) * 100.0
                    tank_volume = self.tanksim_config.tankVolume
                    self.tanksim_status.levelSetpoint = (
                        level_percent / 100.0) * tank_volume
            except Exception as e:
                logger.debug(f"Error converting PLC level setpoint: {e}")

        # Also push key limits from GUI into the simulation configuration
        # so changes to max flows and heater power affect the physics.
        try:
            if hasattr(self, 'tanksim_config') and self.tanksim_config is not None:
                # Max incoming flow
                try:
                    val_in = float(self.maxFlowInEntry.text()) if hasattr(
                        self, 'maxFlowInEntry') else None
                    if val_in is not None and val_in >= 0:
                        self.tanksim_config.valveInMaxFlow = val_in
                except Exception:
                    pass

                # Max outgoing flow
                try:
                    val_out = float(self.maxFlowOutEntry.text()) if hasattr(
                        self, 'maxFlowOutEntry') else None
                    if val_out is not None and val_out >= 0:
                        self.tanksim_config.valveOutMaxFlow = val_out
                except Exception:
                    pass

                # Heating coil max power (W)
                try:
                    power = float(self.powerHeatingCoilEntry.text()) if hasattr(
                        self, 'powerHeatingCoilEntry') else None
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
                        self.tanksim_config.digitalLevelSensorHighTriggerLevel = max(
                            0.0, (hi_pct / 100.0) * tv)
                    if lo_pct is not None and tv is not None:
                        self.tanksim_config.digitalLevelSensorLowTriggerLevel = max(
                            0.0, (lo_pct / 100.0) * tv)
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
        # Always use analog valve control (digital mode removed)
        try:
            stacked_widget = self.findChild(QStackedWidget, "regelingSimGui")
            if stacked_widget is not None:
                stacked_widget.setCurrentIndex(0)  # Always analog
        except Exception as e:
            pass

        # Update vat_widget settings and rebuild SVG
        if hasattr(self, 'vat_widget') and self.vat_widget:
            try:
                # Always analog valve control, always analog heating coil (digital removed)
                self.vat_widget.adjustableValve = True
                self.vat_widget.levelSwitches = self.levelSwitchesCheckBox.isChecked()
                self.vat_widget.analogValueTemp = self.analogValueTempCheckBox.isChecked()
                self.vat_widget.adjustableHeatingCoil = True
                self.vat_widget.updateControlsVisibility()
                self.vat_widget.rebuild()  # Rebuild SVG to show changes
            except Exception as e:
                logger.error(f"Error updating vat_widget config: {e}")

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
        else:
            # Stop simulation engine
            if hasattr(self, 'tanksim_status') and self.tanksim_status:
                self.tanksim_status.simRunning = False

            self.pushButton_startSimulation.setText("START SIMULATION")

    def _init_trend_graphs(self):
        """Initialize trend graph buttons and manager"""
        try:
            # Initialize trend graph manager
            self.trend_manager = TrendGraphManager()

            # Update trend manager with current configuration
            # Try to get tank volume from GUI field first, fall back to config
            tank_volume_liters = 200.0
            try:
                if hasattr(self, 'volumeEntry') and self.volumeEntry:
                    volume_m3 = float(self.volumeEntry.text() or 0.2)
                    tank_volume_liters = volume_m3 * 1000.0  # Convert m³ to liters
                elif hasattr(self, 'tanksim_config') and self.tanksim_config:
                    tank_volume_liters = self.tanksim_config.tankVolume
            except (ValueError, AttributeError):
                if hasattr(self, 'tanksim_config') and self.tanksim_config:
                    tank_volume_liters = self.tanksim_config.tankVolume

            boiling_temp = 100.0
            if hasattr(self, 'tanksim_config') and self.tanksim_config:
                boiling_temp = getattr(
                    self.tanksim_config, 'liquidBoilingTemp', 100.0)

            self.trend_manager.set_config(
                tank_volume_max=tank_volume_liters,
                temp_max=boiling_temp,
                boiling_temp=boiling_temp
            )

            # Connect temperature trend button
            if hasattr(self, 'pushButton_TempTrend'):
                self.pushButton_TempTrend.clicked.connect(
                    self._show_temperature_trend)

            # Connect level trend button
            if hasattr(self, 'pushButton_LevelTrend'):
                self.pushButton_LevelTrend.clicked.connect(
                    self._show_level_trend)
        except Exception as e:
            logger.error(f"Error initializing trend graphs: {e}")

    def _show_temperature_trend(self):
        """Show temperature trend window"""
        try:
            self.trend_manager.show_temperature_trend(self)
        except Exception as e:
            logger.error(f"Error showing temperature trend: {e}")

    def _show_level_trend(self):
        """Show level trend window"""
        try:
            self.trend_manager.show_level_trend(self)
        except Exception as e:
            logger.error(f"Error showing level trend: {e}")
