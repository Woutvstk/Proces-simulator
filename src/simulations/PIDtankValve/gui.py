"""
Tank Visualization Widget - SVG-based graphical display for PID tank simulation.

Provides real-time visual representation of:
- Liquid level and color in tank
- Heating coil activation
- Valve positions (inlet/outlet)
- Level switches and temperature sensors

External Libraries Used:
- PyQt5 (GPL v3) - GUI framework for widgets, SVG rendering, and painting
- xml.etree.ElementTree (Python Standard Library) - XML manipulation for dynamic SVG updates
"""

import os
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PyQt5.QtCore import QSize, QRectF
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter

logger = logging.getLogger(__name__)

# Color definitions for liquid display
RED = "#FF0000"
ORANGE = "#FFA500"
BLUE = "#1100FF"
GREEN = "#00FF00"

# Warning thresholds
BOILING_TEMPERATURE = 100.0  # °C

# Global state variables (deprecated - kept for backwards compatibility)
heatingCoil = True
liquidVolume = 0
tempVat = 0
simRunning = False  # Track if simulation is running


class SvgDisplay(QWidget):
    """Widget that only renders the SVG."""

    def __init__(self, renderer):
        super().__init__()
        self.renderer = renderer
        self.setMinimumSize(300, 350)
        self.setMaximumSize(1200, 1400)

    def sizeHint(self):
        return QSize(300, 350)

    def paintEvent(self, event):
        painter = QPainter(self)
        svg_size = self.renderer.defaultSize()
        if svg_size.width() > 0 and svg_size.height() > 0:
            widget_rect = self.rect()
            svg_ratio = svg_size.width() / svg_size.height()
            widget_ratio = widget_rect.width() / widget_rect.height()

            if widget_ratio > svg_ratio:
                new_width = int(widget_rect.height() * svg_ratio)
                x_offset = (widget_rect.width() - new_width) // 2
                target_rect = widget_rect.adjusted(x_offset, 0, -x_offset, 0)
            else:
                new_height = int(widget_rect.width() / svg_ratio)
                y_offset = (widget_rect.height() - new_height) // 2
                target_rect = widget_rect.adjusted(0, y_offset, 0, -y_offset)

            target_rectf = QRectF(target_rect)
            self.renderer.render(painter, target_rectf)
        else:
            self.renderer.render(painter)


class VatWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # Default attribute values
        self.valveInMaxFlowValue = 0
        self.valveOutMaxFlowValue = 0
        self.powerValue = 15000.0
        self.adjustableValve = False
        self.adjustableHeatingCoil = False
        self.levelSwitches = False
        self.analogValueTemp = False
        self.adjustableValveInValue = 0
        self.adjustableValveOutValue = 0
        self.waterColor = BLUE
        self.controler = "GUI"
        self.maxVolume = 200.0  # Tank capacity in liters
        self.levelSwitchMaxHeight = 90.0
        self.levelSwitchMinHeight = 10.0
        self.heaterPowerFraction = 0.0
        self._initialization_complete = False  # Track if initialization is done
        # Track last warning to avoid spam (instance variable)
        self._last_warning_shown = None
        # Track last checked state to prevent duplicate warnings
        self._last_checked_state = None
        # Boiling temp snooze timer (timestamp when warning can be shown again)
        self._boiling_temp_snooze_until = 0

        self.waterInVat = None
        self.originalY = 0.0
        self.originalHeight = 0.0
        self.maxheightGUI = 85
        self.lowestY = 0.0

        try:
            # Try multiple paths to find SVGVat.svg (handles different architectures)
            possible_paths = [
                Path(__file__).parent.parent.parent /
                "gui" / "media" / "SVGVat.svg",
                Path(__file__).parent.parent /
                "guiCommon" / "media" / "SVGVat.svg",
                Path(__file__).parent.parent.parent /
                "gui" / "media" / "icon" / "SVG vat.svg",
                Path(__file__).parent.parent.parent /
                "guiCommon" / "media" / "SVGVat.svg",
            ]

            svg_path = None
            for path in possible_paths:
                if path.exists():
                    svg_path = path
                    break

            if svg_path is None:
                raise FileNotFoundError(
                    f"SVG file not found in any of the expected locations: {possible_paths}")

            self.tree = ET.parse(svg_path)
            self.root = self.tree.getroot()
            self.ns = {"svg": "http://www.w3.org/2000/svg"}
        except Exception as e:
            raise RuntimeError("Cannot load 'SVGVat.svg': " + str(e))

        self.renderer = QSvgRenderer()
        self.svg_widget = SvgDisplay(self.renderer)
        layout.addWidget(self.svg_widget)

        self.rebuild()

    def set_controller_mode(self, mode):
        """Set controller mode and update visibility of controls"""
        self.controler = mode
        self.updateControlsVisibility()

    def updateControlsVisibility(self):
        """Update visibility of GUI controls based on controller mode"""
        # Show analog indicators in both GUI and PLC modes so users can see live PLC values
        if self.adjustableValve:
            self.visibilityGroup("adjustableValve", "shown")

        if self.adjustableHeatingCoil:
            self.visibilityGroup("adjustableHeatingCoil", "shown")

        self.updateSVG()
        self.svg_widget.update()
        self._initialization_complete = True  # Mark initialization as complete

    def rebuild(self):
        """Complete rebuild of the SVG based on current values"""
        global liquidVolume

        # Check for warnings
        self._check_heating_warnings()

        self.setGroupColor("WaterGroup", self.waterColor)

        # Heating coil color: black (0%) → red (100%) based on heater power fraction (0.0-1.0)
        # 0.0 = black (#000000), 1.0 = full red (#FF0000)
        try:
            intensity = float(self.heaterPowerFraction)
        except Exception:
            intensity = 0.0

        # Clamp to 0.0..1.0 range
        intensity = max(0.0, min(1.0, intensity))

        # Convert to red channel 0..255, keep G=B=0
        red_val = int(round(255 * intensity))
        red_hex = f"#{red_val:02X}0000"
        self.setGroupColor("heatingCoil", red_hex)
        if self.levelSwitches:
            self.visibilityGroup("tagLevelSwitchMax", "shown")
            self.visibilityGroup("tagLevelSwitchMin", "shown")
        else:
            self.visibilityGroup("tagLevelSwitchMax", "hidden")
            self.visibilityGroup("tagLevelSwitchMin", "hidden")

        if self.analogValueTemp:
            self.visibilityGroup("analogValueTemp", "shown")
        else:
            self.visibilityGroup("analogValueTemp", "hidden")

        # Always show analog valve indicators so PLC-driven values stay visible
        self.visibilityGroup("adjustableValve", "shown")
        if not self.adjustableHeatingCoil:
            self.visibilityGroup("adjustableHeatingCoil", "hidden")
            if heatingCoil:
                self.setGroupColor("tagHeater", GREEN)
            elif not heatingCoil:
                self.setGroupColor("tagHeater", RED)
            else:
                self.setGroupColor("tagHeater", "#FFFFFF")
        else:
            # Keep visible even in PLC mode to reflect live heater power
            self.visibilityGroup("adjustableHeatingCoil", "shown")

        # Control water pipe visibility - show when tank has water
        waterPipe = self.root.find(f".//svg:*[@id='waterPipe']", self.ns)
        if waterPipe is not None:
            if liquidVolume > 0:
                waterPipe.set("visibility", "visible")
            else:
                waterPipe.set("visibility", "hidden")

        # Control inlet water visibility - show when inlet valve is open
        waterValveIn = self.root.find(f".//svg:*[@id='waterValveIn']", self.ns)
        if waterValveIn is not None:
            if self.adjustableValveInValue > 0:
                waterValveIn.set("visibility", "visible")
                waterValveIn.set(
                    "style", f"fill:{BLUE};fill-opacity:1;stroke:{BLUE}")
                self.setGroupColor("valveIn", BLUE)
                self.setGroupColor("tagValveIn", BLUE)
                # Set the inlet water width based on actual flow
                if liquidVolume > 0:
                    # Normal case: tank has water, scale by inlet valve opening
                    self.ValveWidth(
                        "waterValveIn", self.adjustableValveInValue)
                else:
                    # No water in tank but inlet is open: scale by actual inlet flow
                    actual_flow = (self.adjustableValveInValue /
                                   100.0) * self.valveInMaxFlowValue
                    equivalent_inlet_opening = (
                        actual_flow / self.valveInMaxFlowValue) * 100.0
                    equivalent_inlet_opening = min(
                        100.0, equivalent_inlet_opening)
                    self.ValveWidth("waterValveIn", equivalent_inlet_opening)
            else:
                waterValveIn.set("visibility", "hidden")
                waterValveIn.set(
                    "style", "fill:#FFFFFF;fill-opacity:0;stroke:#FFFFFF")
                self.setGroupColor("valveIn", "#FFFFFF")
                self.setGroupColor("tagValveIn", "#FFFFFF")

        # Control outlet water visibility and width - show when:
        # 1. There IS water AND outlet valve is open, OR
        # 2. There is NO water AND BOTH inlet AND outlet valves are open (water through from inlet to outlet)
        waterValveOut = self.root.find(
            f".//svg:*[@id='waterValveOut']", self.ns)
        if waterValveOut is not None:
            if (liquidVolume > 0 and self.adjustableValveOutValue > 0) or \
               (liquidVolume <= 0 and self.adjustableValveInValue > 0 and self.adjustableValveOutValue > 0):
                # Set the outlet water width based on actual flow FIRST
                if liquidVolume > 0:
                    # Normal case: tank has water, scale by outlet valve opening
                    self.ValveWidth("waterValveOut",
                                    self.adjustableValveOutValue)
                else:
                    # No water in tank but both valves open: scale by actual inlet flow
                    # Actual flow = (inlet opening % × inlet max flow)
                    # Convert to equivalent outlet valve opening = (actual flow / outlet max flow) × 100
                    actual_flow = (self.adjustableValveInValue /
                                   100.0) * self.valveInMaxFlowValue
                    equivalent_outlet_opening = (
                        actual_flow / self.valveOutMaxFlowValue) * 100.0
                    # Cap at 100% to avoid overflow
                    equivalent_outlet_opening = min(
                        100.0, equivalent_outlet_opening)
                    self.ValveWidth("waterValveOut", equivalent_outlet_opening)

                # Then set visibility and color
                waterValveOut.set("visibility", "visible")
                waterValveOut.set(
                    "style", f"fill:{BLUE};fill-opacity:1;stroke:{BLUE}")
                self.setGroupColor("valveOut", BLUE)
                self.setGroupColor("tagValveOut", BLUE)
            else:
                waterValveOut.set("visibility", "hidden")
                waterValveOut.set(
                    "style", "fill:#FFFFFF;fill-opacity:0;stroke:#FFFFFF")
                self.setGroupColor("valveOut", "#FFFFFF")
                self.setGroupColor("tagValveOut", "#FFFFFF")

        if tempVat == self.powerValue:
            self.setGroupColor("tagTempValue", GREEN)
        else:
            self.setGroupColor("tagTempValue", RED)

        self.setSVGText("adjustableValveInValue", str(
            self.adjustableValveInValue) + "%")
        self.setSVGText("adjustableValveOutValue", str(
            self.adjustableValveOutValue) + "%")
        self.setSVGText("valveInMaxFlowValue", str(
            self.valveInMaxFlowValue) + "l/s")
        self.setSVGText("valveOutMaxFlowValue", str(
            self.valveOutMaxFlowValue) + "l/s")
        self.setSVGText("levelSwitchMinHeight", str(
            self.levelSwitchMinHeight) + "%")
        self.setSVGText("levelSwitchMaxHeight", str(
            self.levelSwitchMaxHeight) + "%")
        # Calculate actual power delivered to heating coil (0 to max)
        actual_power = self.powerValue * self.heaterPowerFraction
        self.setSVGText("powerValue",
                        f"{actual_power:.1f}W")
        # Show tank water temperature with max 2 decimals
        try:
            self.setSVGText("tempVatValue", f"{float(tempVat):.2f}°C")
        except Exception:
            # Fallback to string conversion if formatting fails
            self.setSVGText("tempVatValue", str(tempVat) + "°C")

        # Update tag labels from configured IO
        self.update_tag_labels()

        self.waterInVat = self.root.find(
            f".//svg:*[@id='waterInVat']", self.ns)

        if self.waterInVat is not None:
            try:
                self.originalY = float(self.waterInVat.get("y"))
                self.originalHeight = float(self.waterInVat.get("height"))
            except Exception:
                self.originalY = 0.0
                self.originalHeight = 0.0

            self.lowestY = self.originalY + self.originalHeight
            self.LevelChangeVat()

        # Hide water height indicator when there is no water AND outgoing valve is open
        if liquidVolume <= 0 and self.adjustableValveOutValue > 0:
            self.visibilityGroup("tagLevelSensor", "hidden")
        else:
            self.visibilityGroup("tagLevelSensor", "visible")

        self.updateSVG()
        self.svg_widget.update()
        # Mark initialization as complete after first rebuild
        self._initialization_complete = True

    def updateSVG(self):
        """Update the renderer with the current SVG"""
        # Register the namespace to preserve it in the output
        ET.register_namespace('svg', 'http://www.w3.org/2000/svg')
        ET.register_namespace(
            'inkscape', 'http://www.inkscape.org/namespaces/inkscape')
        xml_bytes = ET.tostring(self.root, encoding="utf-8")
        self.renderer.load(xml_bytes)

    def update_tag_labels(self):
        """Update SVG tag labels from current IO signal names configuration.

        This can be called independently to refresh tags when signal names change,
        without rebuilding the entire SVG (which is computationally expensive).
        """
        # Set tag names/labels from configured IO
        # These display the PLC variable names associated with each tag
        if hasattr(self, 'config') and self.config:
            try:
                # Set tag labels with signal names from IO configuration
                tag_mapping = {
                    'tagValveOut': 'AQValveOutFraction',
                    'tagValveIn': 'AQValveInFraction',
                    'tagHeater': 'AQHeaterFraction',
                    'tagLevelSwitchMax': 'DILevelSensorHigh',
                    'tagLevelSwitchMin': 'DILevelSensorLow',
                    'tagLevelSensor': 'AILevelSensor',
                    'tagTempValue': 'AITemperatureSensor'
                }

                # Apply signal names from config using get_signal_name_for_attribute
                for tag_id, attr_name in tag_mapping.items():
                    # Try to get custom signal name from IO configuration
                    signal_name = None

                    # First check custom_signal_names
                    if hasattr(self.config, 'custom_signal_names') and attr_name in self.config.custom_signal_names:
                        signal_name = self.config.custom_signal_names[attr_name]
                    # Then check reverse_io_mapping
                    elif hasattr(self.config, 'reverse_io_mapping') and attr_name in self.config.reverse_io_mapping:
                        signal_name = self.config.reverse_io_mapping[attr_name]
                    # Finally use get_signal_name_for_attribute if available
                    elif hasattr(self.config, 'get_signal_name_for_attribute'):
                        signal_name = self.config.get_signal_name_for_attribute(
                            attr_name)

                    # If we got a signal name, use it; otherwise use default
                    if signal_name:
                        self.setSVGText(tag_id, signal_name)
                    else:
                        # Fallback to default names
                        if attr_name == 'AQValveOutFraction':
                            self.setSVGText(tag_id, "ValveOut")
                        elif attr_name == 'AQValveInFraction':
                            self.setSVGText(tag_id, "ValveIn")
                        elif attr_name == 'AQHeaterFraction':
                            self.setSVGText(tag_id, "Heater")
                        elif attr_name == 'DILevelSensorHigh':
                            self.setSVGText(tag_id, "LevelMax")
                        elif attr_name == 'DILevelSensorLow':
                            self.setSVGText(tag_id, "LevelMin")
                        elif attr_name == 'AILevelSensor':
                            self.setSVGText(tag_id, "LevelSensor")
                        elif attr_name == 'AITemperatureSensor':
                            self.setSVGText(tag_id, "TempSensor")

                # Update the SVG renderer to reflect changes
                self.updateSVG()
                self.svg_widget.update()
            except Exception as e:
                logger.debug(f"Could not update tag labels: {e}")

    def _check_heating_warnings(self):
        """Check for heating-related warnings and show dialogs"""
        global liquidVolume, tempVat, simRunning

        # Skip warnings during initialization
        if not self._initialization_complete:
            return

        # Only show warnings when simulation is running
        if not simRunning:
            # Reset warning tracker when simulation stops
            self._last_warning_shown = None
            self._last_checked_state = None
            return

        warning_key = None

        # Determine current state
        if self.heaterPowerFraction > 0 and liquidVolume <= 0:
            warning_key = "no_water_heating"
        elif tempVat >= BOILING_TEMPERATURE:
            warning_key = "boiling_temperature"

        # Only trigger warning on STATE CHANGE (when warning_key differs from last check)
        if warning_key != self._last_checked_state:
            self._last_checked_state = warning_key

            # Show warning only if there IS a warning condition
            if warning_key == "no_water_heating":
                try:
                    QMessageBox.warning(
                        None,
                        "Tank Warning",
                        "⚠️ Warning: Heating element is on but there is no water in the tank!",
                        QMessageBox.Ok
                    )
                except Exception as e:
                    logger.error(f"Error showing warning dialog: {e}")
            elif warning_key == "boiling_temperature":
                # Check if snooze is still active
                import time
                current_time = time.time()
                if current_time < self._boiling_temp_snooze_until:
                    # Snooze is active, don't show warning
                    return
                
                try:
                    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
                    from PyQt5.QtCore import Qt
                    
                    # Create custom dialog with Snooze button
                    dialog = QDialog(None)
                    dialog.setWindowTitle("Tank Warning")
                    dialog.setModal(True)
                    
                    layout = QVBoxLayout(dialog)
                    
                    label = QLabel(
                        f"⚠️ Warning: Water temperature ({tempVat:.1f}°C) exceeds boiling point ({BOILING_TEMPERATURE}°C)!")
                    layout.addWidget(label)
                    
                    button_layout = QHBoxLayout()
                    
                    ok_btn = QPushButton("OK")
                    snooze_btn = QPushButton("Snooze 5 min")
                    
                    def on_ok():
                        dialog.accept()
                    
                    def on_snooze():
                        self._boiling_temp_snooze_until = current_time + (5 * 60)  # 5 minutes
                        dialog.accept()
                    
                    ok_btn.clicked.connect(on_ok)
                    snooze_btn.clicked.connect(on_snooze)
                    
                    button_layout.addWidget(ok_btn)
                    button_layout.addWidget(snooze_btn)
                    layout.addLayout(button_layout)
                    
                    dialog.exec_()
                except Exception as e:
                    logger.error(f"Error showing custom warning dialog: {e}")

    def LevelChangeVat(self):
        """Fill the tank based on liquidVolume"""
        global liquidVolume

        # Calculate percentage (0-100%) - maxVolume is in liters
        level_percentage = min(
            100.0, (liquidVolume / self.maxVolume) * 100.0) if self.maxVolume > 0 else 0

        # Level switches trigger at percentage of tank
        level_fraction = liquidVolume / self.maxVolume if self.maxVolume > 0 else 0
        if level_fraction * 100.0 >= self.levelSwitchMaxHeight:
            self.setGroupColor("levelSwitchMax", GREEN)
        else:
            self.setGroupColor("levelSwitchMax", RED)
        if level_fraction * 100.0 >= self.levelSwitchMinHeight:
            self.setGroupColor("levelSwitchMin", GREEN)
        else:
            self.setGroupColor("levelSwitchMin", RED)

        # Calculate GUI height: percentage (0-100) mapped to max GUI height
        realGUIHeight = min(self.maxheightGUI,
                            (level_percentage / 100.0) * self.maxheightGUI)
        newY = self.lowestY - realGUIHeight

        if self.waterInVat is not None:
            self.waterInVat.set("height", str(realGUIHeight))
            self.waterInVat.set("y", str(newY))
        self.setHightIndicator("levelIndicator", newY)
        self.setHightIndicator("levelValue", newY + 2)
        self.setSVGText("levelValue", str(int(level_percentage)) + "%")

    def setHightIndicator(self, itemId, hoogte):
        """Set the Y-position of an indicator"""
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is not None:
            item.set("y", str(hoogte-3))

    def setGroupColor(self, groupId, kleur):
        """Set the color of an SVG group"""
        group = self.root.find(f".//svg:g[@id='{groupId}']", self.ns)
        if group is not None:
            for element in group:
                element.set("fill", kleur)

    def visibilityGroup(self, groupId, visibility):
        """Set the visibility of a group"""
        group = self.root.find(f".//svg:g[@id='{groupId}']", self.ns)
        if group is not None:
            group.set("visibility", visibility)

    def ValveWidth(self, itemId, KlepStand):
        """Adjust the width of a valve based on its position"""
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is not None:
            new_width = (KlepStand * 0.0645)
            new_x = 105.745 - (KlepStand * 0.065) / 2
            item.set("width", str(new_width))
            item.set("x", str(new_x))

    def setSVGText(self, itemId, value):
        """Set the text of an SVG text element"""
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is not None:
            tspan = item.find("svg:tspan", self.ns)
            if tspan is not None:
                tspan.text = value
            else:
                item.text = value

    def connect_pidvalve_controls(self):
        """Connect PID valve control widgets (called from parent window setup)."""
        # Note: Auto/Manual toggle buttons are initialized in settingsGui.py
        # where they are accessible as part of MainWindow
        # Connect digital buttons
        for btn_name in [
            'pushButton_PidValveStart', 'pushButton_PidValveStop',
            'radioButton_PidTankValveAItemp', 'radioButton_PidTankValveDItemp',
                'radioButton_PidTankValveAIlevel', 'radioButton_PidTankValveDIlevel']:
            btn = getattr(self, btn_name, None)
            if btn:
                btn.setCheckable(True)
                # Optionally: connect to a slot to update IO state

    def init_mainwindow_controls(self, mainwindow):
        """Initialize all MainWindow controls (buttons, toggles) from gui.py.

        This centralizes all simulation screen logic in gui.py to maintain architecture.
        Called from settingsGui.py with MainWindow reference.

        Args:
            mainwindow: Reference to MainWindow object containing the buttons
        """
        self.mainwindow = mainwindow
        self._init_pidvalve_mode_toggle()
        self._init_valve_control_handlers()

    def _init_valve_control_handlers(self):
        """Connect valve control widgets to event handlers for real-time SVG updates."""
        if not hasattr(self, 'mainwindow') or self.mainwindow is None:
            return

        try:
            # Valve In Entry (analog control)
            valve_in_entry = getattr(self.mainwindow, 'valveInEntry', None)
            if valve_in_entry and hasattr(valve_in_entry, 'textChanged'):
                try:
                    valve_in_entry.textChanged.connect(
                        self._on_valve_in_entry_changed)
                except Exception:
                    pass

            # Valve Out Entry (analog control)
            valve_out_entry = getattr(self.mainwindow, 'valveOutEntry', None)
            if valve_out_entry and hasattr(valve_out_entry, 'textChanged'):
                try:
                    valve_out_entry.textChanged.connect(
                        self._on_valve_out_entry_changed)
                except Exception:
                    pass

            # Valve In CheckBox (digital control)
            valve_in_checkbox = getattr(
                self.mainwindow, 'valveInCheckBox', None)
            if valve_in_checkbox and hasattr(valve_in_checkbox, 'stateChanged'):
                try:
                    valve_in_checkbox.stateChanged.connect(
                        self._on_valve_in_checkbox_changed)
                except Exception:
                    pass

            # Valve Out CheckBox (digital control)
            valve_out_checkbox = getattr(
                self.mainwindow, 'valveOutCheckBox', None)
            if valve_out_checkbox and hasattr(valve_out_checkbox, 'stateChanged'):
                try:
                    valve_out_checkbox.stateChanged.connect(
                        self._on_valve_out_checkbox_changed)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_valve_in_entry_changed(self, text):
        """Handle valve in entry text change - update SVG immediately."""
        try:
            value = int(text) if text else 0
            self.adjustableValveInValue = max(0, min(100, value))
            self.rebuild()
        except (ValueError, AttributeError):
            pass

    def _on_valve_out_entry_changed(self, text):
        """Handle valve out entry text change - update SVG immediately."""
        try:
            value = int(text) if text else 0
            self.adjustableValveOutValue = max(0, min(100, value))
            self.rebuild()
        except (ValueError, AttributeError):
            pass

    def _on_valve_in_checkbox_changed(self, state):
        """Handle valve in checkbox state change - digital control."""
        try:
            self.adjustableValveInValue = 100 if state else 0
            self.rebuild()
        except AttributeError:
            pass

    def _on_valve_out_checkbox_changed(self, state):
        """Handle valve out checkbox state change - digital control."""
        try:
            self.adjustableValveOutValue = 100 if state else 0
            self.rebuild()
        except AttributeError:
            pass

    def _init_pidvalve_mode_toggle(self):
        """Initialize Auto/Manual flip-flop toggle."""
        if not hasattr(self, 'mainwindow') or self.mainwindow is None:
            return

        try:
            auto_btn = getattr(
                self.mainwindow, 'pushButton_PidValveAuto', None)
            man_btn = getattr(self.mainwindow, 'pushButton_PidValveMan', None)

            if auto_btn:
                auto_btn.setCheckable(True)
                auto_btn.clicked.connect(self._toggle_auto_mode)

            if man_btn:
                man_btn.setCheckable(True)
                man_btn.clicked.connect(self._toggle_manual_mode)

            # Start with Auto active
            if auto_btn:
                auto_btn.setChecked(True)
                auto_btn.setStyleSheet("""
                    QPushButton {
                        background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                                          stop:0 rgba(140, 140, 140, 255), 
                                                          stop:1 rgba(120, 120, 120, 255));
                        color: black;
                        border: none;
                        border-radius: 4px;
                        font-weight: 600;
                        padding: 8px 12px;
                    }
                """)

            if man_btn:
                man_btn.setChecked(False)
                man_btn.setStyleSheet("""
                    QPushButton {
                        background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                                          stop:0 rgba(200, 200, 200, 255), 
                                                          stop:1 rgba(180, 180, 180, 255));
                        color: black;
                        border: none;
                        border-radius: 4px;
                        font-weight: 600;
                        padding: 8px 12px;
                    }
                    QPushButton:hover {
                        background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, 
                                                          stop:0 rgba(200, 200, 200, 255), 
                                                          stop:0.5 rgba(180, 180, 180, 255), 
                                                          stop:1 rgba(170, 170, 170, 255));
                    }
                    QPushButton:pressed {
                        background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, 
                                                          stop:0 rgba(170, 170, 170, 255), 
                                                          stop:0.5 rgba(140, 140, 140, 255), 
                                                          stop:1 rgba(120, 120, 120, 255));
                    }
                """)

            # Gray out controls on startup if in Auto mode AND PLC control mode
            # Use QTimer to delay the check until mainConfig is fully initialized
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self._apply_startup_control_state)
        except Exception as e:
            logger.error(f"Error initializing PID valve mode toggle: {e}")

    def _apply_startup_control_state(self):
        """Apply control groupbox state after mainConfig is initialized."""
        try:
            gui_mode = (hasattr(self.mainwindow, 'mainConfig') and
                        self.mainwindow.mainConfig and
                        hasattr(self.mainwindow.mainConfig, 'plcGuiControl') and
                        self.mainwindow.mainConfig.plcGuiControl == "gui")
            if not gui_mode:
                # In PLC control mode, gray out controls in Auto mode (default)
                self._update_control_groupboxes(enabled=False)
        except Exception as e:
            logger.error(f"Error applying startup control state: {e}")

    def _toggle_auto_mode(self):
        """Set Auto as active, Manual as inactive."""
        if not hasattr(self, 'mainwindow') or self.mainwindow is None:
            return

        auto_btn = getattr(self.mainwindow, 'pushButton_PidValveAuto', None)
        man_btn = getattr(self.mainwindow, 'pushButton_PidValveMan', None)

        if auto_btn:
            auto_btn.blockSignals(True)
            auto_btn.setChecked(True)
            auto_btn.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                                      stop:0 rgba(140, 140, 140, 255), 
                                                      stop:1 rgba(120, 120, 120, 255));
                    color: black;
                    border: none;
                    border-radius: 4px;
                    font-weight: 600;
                    padding: 8px 12px;
                }
            """)
            auto_btn.blockSignals(False)

        if man_btn:
            man_btn.blockSignals(True)
            man_btn.setChecked(False)
            man_btn.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                                      stop:0 rgba(200, 200, 200, 255), 
                                                      stop:1 rgba(180, 180, 180, 255));
                    color: black;
                    border: none;
                    border-radius: 4px;
                    font-weight: 600;
                    padding: 8px 12px;
                }
                QPushButton:hover {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, 
                                                      stop:0 rgba(200, 200, 200, 255), 
                                                      stop:0.5 rgba(180, 180, 180, 255), 
                                                      stop:1 rgba(170, 170, 170, 255));
                }
                QPushButton:pressed {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, 
                                                      stop:0 rgba(170, 170, 170, 255), 
                                                      stop:0.5 rgba(140, 140, 140, 255), 
                                                      stop:1 rgba(120, 120, 120, 255));
                }
            """)
            man_btn.blockSignals(False)

        # Update status
        if hasattr(self.mainwindow, 'tanksim_status') and self.mainwindow.tanksim_status:
            self.mainwindow.tanksim_status.pidPidValveAutoCmd = True
            self.mainwindow.tanksim_status.pidPidValveManCmd = False

        # Gray out control groupboxes in Auto mode ONLY if in PLC control mode
        gui_mode = (hasattr(self.mainwindow, 'mainConfig') and
                    self.mainwindow.mainConfig and
                    self.mainwindow.mainConfig.plcGuiControl == "gui")
        if not gui_mode:
            self._update_control_groupboxes(enabled=False)

    def _toggle_manual_mode(self):
        """Set Manual as active, Auto as inactive."""
        if not hasattr(self, 'mainwindow') or self.mainwindow is None:
            return

        auto_btn = getattr(self.mainwindow, 'pushButton_PidValveAuto', None)
        man_btn = getattr(self.mainwindow, 'pushButton_PidValveMan', None)

        if man_btn:
            man_btn.blockSignals(True)
            man_btn.setChecked(True)
            man_btn.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                                      stop:0 rgba(140, 140, 140, 255), 
                                                      stop:1 rgba(120, 120, 120, 255));
                    color: black;
                    border: none;
                    border-radius: 4px;
                    font-weight: 600;
                    padding: 8px 12px;
                }
            """)
            man_btn.blockSignals(False)

        if auto_btn:
            auto_btn.blockSignals(True)
            auto_btn.setChecked(False)
            auto_btn.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                                                      stop:0 rgba(200, 200, 200, 255), 
                                                      stop:1 rgba(180, 180, 180, 255));
                    color: black;
                    border: none;
                    border-radius: 4px;
                    font-weight: 600;
                    padding: 8px 12px;
                }
                QPushButton:hover {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, 
                                                      stop:0 rgba(200, 200, 200, 255), 
                                                      stop:0.5 rgba(180, 180, 180, 255), 
                                                      stop:1 rgba(170, 170, 170, 255));
                }
                QPushButton:pressed {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, 
                                                      stop:0 rgba(170, 170, 170, 255), 
                                                      stop:0.5 rgba(140, 140, 140, 255), 
                                                      stop:1 rgba(120, 120, 120, 255));
                }
            """)
            auto_btn.blockSignals(False)

        # Update status
        if hasattr(self.mainwindow, 'tanksim_status') and self.mainwindow.tanksim_status:
            self.mainwindow.tanksim_status.pidPidValveAutoCmd = False
            self.mainwindow.tanksim_status.pidPidValveManCmd = True

        # IMPORTANT: Force write of manual control values to status on mode switch
        # This ensures that if the user already set values in manual mode, they are immediately active
        try:
            self._write_manual_control_values_to_status()
        except Exception:
            pass

        # Enable control groupboxes in Manual mode (allows override of PLC)
        self._update_control_groupboxes(enabled=True)

    def _write_manual_control_values_to_status(self):
        """Write current manual control values (valve positions, heater) to status.

        Called when switching from Auto to Manual mode to ensure already-set manual
        values are immediately active without requiring a user change.
        
        This reads from:
        - valveInEntry and valveOutEntry fields (analog control)
        - valveInCheckBox and valveOutCheckBox (digital control)
        - heater power sliders (coil W)
        """
        if not hasattr(self, 'mainwindow') or self.mainwindow is None:
            return
        if not hasattr(self.mainwindow, 'tanksim_status') or self.mainwindow.tanksim_status is None:
            return

        status = self.mainwindow.tanksim_status

        # Read valve positions from entry fields (analog control)
        try:
            valve_in_entry = getattr(self.mainwindow, 'valveInEntry', None)
            if valve_in_entry and hasattr(valve_in_entry, 'text'):
                try:
                    valve_in_value = int(valve_in_entry.text()) if valve_in_entry.text() else 0
                    self.adjustableValveInValue = max(0, min(100, valve_in_value))
                    status.valveInOpenFraction = self.adjustableValveInValue / 100.0
                except (ValueError, AttributeError):
                    status.valveInOpenFraction = self.adjustableValveInValue / 100.0
            else:
                status.valveInOpenFraction = self.adjustableValveInValue / 100.0
        except Exception:
            status.valveInOpenFraction = self.adjustableValveInValue / 100.0

        try:
            valve_out_entry = getattr(self.mainwindow, 'valveOutEntry', None)
            if valve_out_entry and hasattr(valve_out_entry, 'text'):
                try:
                    valve_out_value = int(valve_out_entry.text()) if valve_out_entry.text() else 0
                    self.adjustableValveOutValue = max(0, min(100, valve_out_value))
                    status.valveOutOpenFraction = self.adjustableValveOutValue / 100.0
                except (ValueError, AttributeError):
                    status.valveOutOpenFraction = self.adjustableValveOutValue / 100.0
            else:
                status.valveOutOpenFraction = self.adjustableValveOutValue / 100.0
        except Exception:
            status.valveOutOpenFraction = self.adjustableValveOutValue / 100.0

        # Read heater power from slider (if available)
        try:
            slider_val = None
            
            # Try to find heater power sliders in mainwindow
            heater_sliders = getattr(self.mainwindow, '_heater_power_sliders', [])
            
            if heater_sliders:
                # Look for visible slider first
                for slider in heater_sliders:
                    if slider is None:
                        continue
                    try:
                        if hasattr(slider, 'isVisible') and slider.isVisible():
                            slider_val = int(slider.value())
                            break
                    except Exception:
                        pass
                
                # If no visible slider found, use first available
                if slider_val is None:
                    for slider in heater_sliders:
                        if slider is not None:
                            try:
                                slider_val = int(slider.value())
                                break
                            except Exception:
                                pass
            
            # Default to 0 if nothing found
            if slider_val is None:
                slider_val = 0
            
            heater_fraction = max(0.0, min(1.0, slider_val / 100.0))
            status.heaterPowerFraction = heater_fraction
            # Also update VatWidget's own heaterPowerFraction so SVG display reflects it
            self.heaterPowerFraction = heater_fraction
        except Exception as e:
            logger.debug(f"Error reading heater slider in manual mode init: {e}")
        
        # Refresh SVG display to show updated values (coil color, heater label, etc.)
        try:
            self.rebuild()
        except Exception as e:
            logger.debug(f"Error refreshing SVG display in manual mode: {e}")

    def _update_control_groupboxes(self, enabled):
        """Enable or disable control groupboxes based on Auto/Manual mode.

        Args:
            enabled: True for Manual mode (controls enabled), False for Auto mode (grayed out)
        """
        if not hasattr(self, 'mainwindow') or self.mainwindow is None:
            return

        try:
            from PyQt5.QtWidgets import QGroupBox

            # Find and update groupBox_simControls
            groupbox1 = self.mainwindow.findChild(
                QGroupBox, 'groupBox_simControls')
            if groupbox1:
                groupbox1.setEnabled(enabled)

            # Find and update groupBox_simControls2
            groupbox2 = self.mainwindow.findChild(
                QGroupBox, 'groupBox_simControls2')
            if groupbox2:
                groupbox2.setEnabled(enabled)
        except Exception:
            pass

    def is_manual_mode(self):
        """Check if currently in Manual mode.

        Returns:
            bool: True if Manual mode is active, False if Auto mode
        """
        if not hasattr(self, 'mainwindow') or self.mainwindow is None:
            return False

        man_btn = getattr(self.mainwindow, 'pushButton_PidValveMan', None)
        if man_btn:
            return man_btn.isChecked()
        return False

    def set_plc_pidcontrol_index(self, gui_mode: bool):
        """Set PLCControl_PIDControl index: 0 for PLC mode, 1 for GUI mode."""
        # This assumes the parent or main window exposes these widgets
        parent = self.parent()
        # Try to find the PLCControl_PIDControl widget in the parent hierarchy
        plc_control = None
        w = self
        while w is not None:
            plc_control = getattr(w, 'PLCControl_PIDControl', None)
            if plc_control is not None:
                break
            w = getattr(w, 'parent', lambda: None)()
        if plc_control is not None:
            if gui_mode:
                plc_control.setCurrentIndex(1)  # GUI mode shows PID controls
            else:
                plc_control.setCurrentIndex(0)  # PLC mode shows PLC controls
