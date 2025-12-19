import os
import xml.etree.ElementTree as ET
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QSize, QRectF
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter

# Colors
red = "#FF0000"
orange = "#FFA500"
blue = "#1100FF"
green = "#00FF00"

# Global variables

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
        self.powerValue = 750.0
        self.adjustableValve = False
        self.adjustableHeatingCoil = False
        self.levelSwitches = False
        self.analogValueTemp = False
        self.adjustableValveInValue = 0
        self.adjustableValveOutValue = 0
        self.waterColor = blue
        self.controler = "GUI"
        self.maxVolume = 2.0
        self.levelSwitchMaxHeight = 90.0
        self.levelSwitchMinHeight = 10.0
        self.heaterPowerFraction = 0.0

        self.waterInVat = None
        self.originalY = 0.0
        self.originalHeight = 0.0
        self.maxheightGUI = 80
        self.lowestY = 0.0

        try:
            svg_path = Path(__file__).parent.parent / \
                "guiCommon" / "media" / "SVGVat.svg"
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
        if not self.adjustableHeatingCoil:
            self.visibilityGroup("adjustableHeatingCoil", "hidden")
            if heatingCoil:
                self.setGroupColor("heatingCoilValue", green)
            elif not heatingCoil:
                self.setGroupColor("heatingCoilValue", red)
            else:
                self.setGroupColor("heatingCoilValue", "#FFFFFF")
        else:
            # Keep visible even in PLC mode to reflect live heater power
            self.visibilityGroup("adjustableHeatingCoil", "shown")

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
            self.setGroupColor("tempVat", green)
        else:
            self.setGroupColor("tempVat", red)

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
        self.setSVGText("powerValue",
                        str(self.powerValue) + "W")
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

        if liquidVolume/self.maxVolume >= self.levelSwitchMaxHeight:
            self.setGroupColor("levelSwitchMax", green)
        else:
            self.setGroupColor("levelSwitchMax", red)
        if liquidVolume/self.maxVolume >= self.levelSwitchMinHeight:
            self.setGroupColor("levelSwitchMin", green)
        else:
            self.setGroupColor("levelSwitchMin", red)

        realGUIHeight = liquidVolume/(self.maxVolume * 100) * self.maxheightGUI
        newY = self.lowestY - realGUIHeight

        if self.waterInVat is not None:
            self.waterInVat.set("height", str(realGUIHeight))
            self.waterInVat.set("y", str(newY))
        self.setHightIndicator("levelIndicator", newY)
        self.setHightIndicator("levelValue", newY + 2)
        self.setSVGText("levelValue", str(
            int(liquidVolume/self.maxVolume)) + "%")

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
