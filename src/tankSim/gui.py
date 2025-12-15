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
maxHoogteVat = 200
weerstand = True
currentHoogteVat = 0
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
        self.powerValue = 20.0
        self.adjustableValve = False
        self.adjustableHeatingCoil = False
        self.levelSwitches = False
        self.analogValueTemp = False
        self.adjustableValveInValue = 0
        self.adjustableValveOutValue = 0
        self.kleurWater = blue
        self.controler = "GUI"

        self.waterInVat = None
        self.originalY = 0.0
        self.originalHoogte = 0.0
        self.maxHoogteGUI = 80
        self.ondersteY = 0.0

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
        self.update_controls_visibility()

    def update_controls_visibility(self):
        """Update visibility of GUI controls based on controller mode"""
        is_gui_mode = (self.controler == "GUI")
        visibility = "shown" if is_gui_mode else "hidden"

        if self.adjustableValve:
            self.visibility_group("adjustableValve", visibility)

        if self.adjustableHeatingCoil:
            self.visibility_group("adjustableHeatingCoil", visibility)

        self.update_svg()
        self.svg_widget.update()

    def rebuild(self):
        """Complete rebuild of the SVG based on current values"""
        global currentHoogteVat, maxHoogteVat

        self.set_group_color("WaterGroup", self.kleurWater)

        if self.powerValue == 0:
            tempVatProcent = 0.0
        else:
            tempVatProcent = (tempVat * 100.0) / self.powerValue

        tempVatProcent = max(0.0, min(100.0, tempVatProcent))

        match tempVatProcent:
            case x if 20 < x <= 40:
                self.set_group_color("heatingCoil", green)
            case x if 40 < x <= 60:
                self.set_group_color("heatingCoil", blue)
            case x if 60 < x <= 80:
                self.set_group_color("heatingCoil", orange)
            case x if 80 < x < 100:
                self.set_group_color("heatingCoil", green)
            case x if x >= 100:
                self.set_group_color("heatingCoil", red)
            case _:
                self.set_group_color("heatingCoil", "#808080")
        if self.levelSwitches:
            self.visibility_group("levelSwitchMax", "shown")
            self.visibility_group("levelSwitchMin", "shown")
        else:
            self.visibility_group("levelSwitchMax", "hidden")
            self.visibility_group("levelSwitchMin", "hidden")

        if self.analogValueTemp:
            self.visibility_group("analogValueTemp", "shown")
        else:
            self.visibility_group("analogValueTemp", "hidden")

        is_gui_mode = (self.controler == "GUI")

        if self.adjustableValve:
            visibility = "shown" if is_gui_mode else "hidden"
            self.visibility_group("adjustableValve", visibility)
        else:
            self.visibility_group("adjustableValve", "hidden")
        if not self.adjustableHeatingCoil:
            self.visibility_group("adjustableHeatingCoil", "hidden")
            if weerstand:
                self.set_group_color("heatingCoilValue", green)
            elif not weerstand:
                self.set_group_color("heatingCoilValue", red)
            else:
                self.set_group_color("heatingCoilValue", "#FFFFFF")
        else:
            visibility = "shown" if is_gui_mode else "hidden"
            self.visibility_group("adjustableHeatingCoil", visibility)

        if self.adjustableValveInValue == 0:
            self.klep_breete("waterValveIn", 0)
            self.set_group_color("valveIn", "#FFFFFF")
        else:
            self.klep_breete("waterValveIn", self.adjustableValveInValue)
            self.set_group_color("valveIn", self.kleurWater)

        if self.adjustableValveOutValue == 0:
            self.klep_breete("waterValveOut", 0)
            self.set_group_color("valveOut", "#FFFFFF")
        else:
            self.klep_breete("waterValveOut", self.adjustableValveOutValue)
            self.set_group_color("valveOut", self.kleurWater)
        if tempVat == self.powerValue:
            self.set_group_color("tempVat", green)
        else:
            self.set_group_color("tempVat", red)

        self.set_svg_text("adjustableValveInValue", str(
            self.adjustableValveInValue) + "%")
        self.set_svg_text("adjustableValveOutValue", str(
            self.adjustableValveOutValue) + "%")
        self.set_svg_text("valveInMaxFlowValue", str(
            self.valveInMaxFlowValue) + "l/s")
        self.set_svg_text("valveOutMaxFlowValue", str(
            self.valveOutMaxFlowValue) + "l/s")
        self.set_svg_text("powerValue",
                          str(self.powerValue) + "W")
        self.set_svg_text("tempVatValue", str(tempVat) + "°C")

        self.waterInVat = self.root.find(
            f".//svg:*[@id='waterInVat']", self.ns)

        if self.waterInVat is not None:
            try:
                self.originalY = float(self.waterInVat.get("y"))
                self.originalHoogte = float(self.waterInVat.get("height"))
            except Exception:
                self.originalY = 0.0
                self.originalHoogte = 0.0
            self.maxHoogteGUI = 80
            self.ondersteY = self.originalY + self.originalHoogte
            self.vat_vullen_GUI()

        self.update_svg()
        self.svg_widget.update()

    def update_svg(self):
        """Update the renderer with the current SVG"""
        xml_bytes = ET.tostring(self.root, encoding="utf-8")
        self.renderer.load(xml_bytes)

    def vat_vullen_GUI(self):
        """Fill the tank based on currentHoogteVat"""
        global currentHoogteVat, maxHoogteVat

        if currentHoogteVat >= maxHoogteVat:
            self.set_group_color("levelSwitchMax", green)
        else:
            self.set_group_color("levelSwitchMax", red)
        if currentHoogteVat == 0:
            self.set_group_color("levelSwitchMin", green)
        else:
            self.set_group_color("levelSwitchMin", red)

        hoogteVatGui = currentHoogteVat / maxHoogteVat * self.maxHoogteGUI
        nieuweY = self.ondersteY - hoogteVatGui

        if self.waterInVat is not None:
            self.waterInVat.set("height", str(hoogteVatGui))
            self.waterInVat.set("y", str(nieuweY))

        self.set_hoogte_indicator("levelIndicator", nieuweY)
        self.set_hoogte_indicator("levelValue", nieuweY + 2)
        self.set_svg_text("levelValue", str(int(currentHoogteVat)) + "%")

    def set_hoogte_indicator(self, itemId, hoogte):
        """Set the Y-position of an indicator"""
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is not None:
            item.set("y", str(hoogte))

    def set_group_color(self, groupId, kleur):
        """Set the color of an SVG group"""
        group = self.root.find(f".//svg:g[@id='{groupId}']", self.ns)
        if group is not None:
            for element in group:
                element.set("fill", kleur)

    def visibility_group(self, groupId, visibility):
        """Set the visibility of a group"""
        group = self.root.find(f".//svg:g[@id='{groupId}']", self.ns)
        if group is not None:
            group.set("visibility", visibility)

    def klep_breete(self, itemId, KlepStand):
        """Adjust the width of a valve based on its position"""
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is not None:
            new_width = (KlepStand * 0.0645)
            new_x = 105.745 - (KlepStand * 0.065) / 2
            item.set("width", str(new_width))
            item.set("x", str(new_x))

    def set_svg_text(self, itemId, value):
        """Set the text of an SVG text element"""
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is not None:
            tspan = item.find("svg:tspan", self.ns)
            if tspan is not None:
                tspan.text = value
            else:
                item.text = value
