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
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QSize, QRectF
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter

logger = logging.getLogger(__name__)

# Color definitions for liquid display
RED = "#FF0000"
ORANGE = "#FFA500"
BLUE = "#1100FF"
GREEN = "#00FF00"

# Global state variables 
heatingCoil = True
liquidVolume = 0
tempVat = 0


class SvgDisplay(QWidget):
    """Widget that only renders the SVG."""

    def __init__(self, renderer):
        super().__init__()
        self.renderer = renderer
        self.setMinimumSize(300, 350)
        self.setMaximumSize(1200, 1400)

    #ensures proper scaling of SVG within widget
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

        self.waterInVat = None
        self.originalY = 0.0
        self.originalHeight = 0.0
        self.maxheightGUI = 80
        self.lowestY = 0.0

        try:
            # Try multiple paths to find SVGVat.svg (handles different architectures)
            possible_paths = [
                Path(__file__).parent.parent.parent / "gui" / "media" / "SVGVat.svg",
                Path(__file__).parent.parent.parent / "gui" / "media" / "icon" / "SVG vat.svg",
            ]
            
            svg_path = None
            for path in possible_paths:
                if path.exists():
                    svg_path = path
                    break
            
            if svg_path is None:
                raise FileNotFoundError(f"SVG file not found in any of the expected locations: {possible_paths}")
            
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

    def rebuild(self):
        """Complete rebuild of the SVG based on current values"""
        global liquidVolume

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
            self.visibilityGroup("levelSwitchMax", "shown")
            self.visibilityGroup("levelSwitchMin", "shown")
        else:
            self.visibilityGroup("levelSwitchMax", "hidden")
            self.visibilityGroup("levelSwitchMin", "hidden")

        if self.analogValueTemp:
            self.visibilityGroup("analogValueTemp", "shown")
        else:
            self.visibilityGroup("analogValueTemp", "hidden")

        # Always show analog valve indicators so PLC-driven values stay visible
        self.visibilityGroup("adjustableValve", "shown")

        if self.adjustableValveInValue == 0:
            self.ValveWidth("waterValveIn", 0)
            self.setGroupColor("valveIn", "#FFFFFF")
        else:
            self.ValveWidth("waterValveIn", self.adjustableValveInValue)
            self.setGroupColor("valveIn", self.waterColor)

        if self.adjustableValveOutValue == 0:
            self.ValveWidth("waterValveOut", 0)
            self.setGroupColor("valveOut", "#FFFFFF")
        else:
            self.ValveWidth("waterValveOut", self.adjustableValveOutValue)
            self.setGroupColor("valveOut", self.waterColor)
        if tempVat == self.powerValue:
            self.setGroupColor("tempVat", GREEN)
        else:
            self.setGroupColor("tempVat", RED)

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

        self.updateSVG()
        self.svg_widget.update()

    def updateSVG(self):
        """Update the renderer with the current SVG"""
        xml_bytes = ET.tostring(self.root, encoding="utf-8")
        self.renderer.load(xml_bytes)

    def LevelChangeVat(self):
        """Fill the tank based on liquidVolume"""
        global liquidVolume

        # Calculate percentage (0-100%) - maxVolume is in liters
        level_percentage = min(100.0, (liquidVolume / self.maxVolume) * 100.0) if self.maxVolume > 0 else 0

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
        realGUIHeight = min(self.maxheightGUI, (level_percentage / 100.0) * self.maxheightGUI)
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
            item.set("y", str(hoogte))

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
                    valve_in_entry.textChanged.connect(self._on_valve_in_entry_changed)
                except Exception:
                    pass
            
            # Valve Out Entry (analog control)
            valve_out_entry = getattr(self.mainwindow, 'valveOutEntry', None)
            if valve_out_entry and hasattr(valve_out_entry, 'textChanged'):
                try:
                    valve_out_entry.textChanged.connect(self._on_valve_out_entry_changed)
                except Exception:
                    pass
            
            # Valve In CheckBox (digital control)
            valve_in_checkbox = getattr(self.mainwindow, 'valveInCheckBox', None)
            if valve_in_checkbox and hasattr(valve_in_checkbox, 'stateChanged'):
                try:
                    valve_in_checkbox.stateChanged.connect(self._on_valve_in_checkbox_changed)
                except Exception:
                    pass
            
            # Valve Out CheckBox (digital control)
            valve_out_checkbox = getattr(self.mainwindow, 'valveOutCheckBox', None)
            if valve_out_checkbox and hasattr(valve_out_checkbox, 'stateChanged'):
                try:
                    valve_out_checkbox.stateChanged.connect(self._on_valve_out_checkbox_changed)
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
            auto_btn = getattr(self.mainwindow, 'pushButton_PidValveAuto', None)
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
        """
        if not hasattr(self, 'mainwindow') or self.mainwindow is None:
            return
        if not hasattr(self.mainwindow, 'tanksim_status') or self.mainwindow.tanksim_status is None:
            return
        
        status = self.mainwindow.tanksim_status
        
        try:
            # Write valve positions from VatWidget adjustable values
            status.valveInOpenFraction = self.adjustableValveInValue / 100.0
            status.valveOutOpenFraction = self.adjustableValveOutValue / 100.0
        except Exception:
            pass
        
        try:
            # Write heater power from slider (if available)
            # Get the first visible heater power slider, or the first available one
            slider_val = None
            try:
                for slider in getattr(self.mainwindow, '_heater_power_sliders', []):
                    if slider is None:
                        continue
                    if slider.isVisible():
                        slider_val = int(slider.value())
                        break
                if slider_val is None:
                    first_slider = next((s for s in getattr(self.mainwindow, '_heater_power_sliders', []) if s is not None), None)
                    if first_slider is not None:
                        slider_val = int(first_slider.value())
            except Exception:
                pass
            
            if slider_val is not None:
                status.heaterPowerFraction = max(0.0, min(1.0, slider_val / 100.0))
        except Exception:
            pass
    
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
            groupbox1 = self.mainwindow.findChild(QGroupBox, 'groupBox_simControls')
            if groupbox1:
                groupbox1.setEnabled(enabled)
            
            # Find and update groupBox_simControls2
            groupbox2 = self.mainwindow.findChild(QGroupBox, 'groupBox_simControls2')
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