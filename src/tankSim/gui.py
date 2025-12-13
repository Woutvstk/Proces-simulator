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
        self.toekomendDebiet = 0
        self.tempWeerstand = 20.0
        self.regelbareKleppen = False
        self.regelbareWeerstand = False
        self.niveauschakelaar = False
        self.analogeWaardeTemp = False
        self.KlepStandBoven = 0
        self.KlepStandBeneden = 0
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

        if self.regelbareKleppen:
            self.visibility_group("regelbareKleppen", visibility)

        if self.regelbareWeerstand:
            self.visibility_group("regelbareweerstand", visibility)

        self.update_svg()
        self.svg_widget.update()

    def rebuild(self):
        """Complete rebuild of the SVG based on current values"""
        global currentHoogteVat, maxHoogteVat

        self.set_group_color("waterTotaal", self.kleurWater)

        if self.tempWeerstand == 0:
            tempVatProcent = 0.0
        else:
            tempVatProcent = (tempVat * 100.0) / self.tempWeerstand

        tempVatProcent = max(0.0, min(100.0, tempVatProcent))

        match tempVatProcent:
            case x if 20 < x <= 40:
                self.set_group_color("warmteweerstand", green)
            case x if 40 < x <= 60:
                self.set_group_color("warmteweerstand", blue)
            case x if 60 < x <= 80:
                self.set_group_color("warmteweerstand", orange)
            case x if 80 < x < 100:
                self.set_group_color("warmteweerstand", green)
            case x if x >= 100:
                self.set_group_color("warmteweerstand", red)
            case _:
                self.set_group_color("warmteweerstand", "#808080")

        if self.niveauschakelaar:
            self.visibility_group("niveauschakelaar", "shown")
        else:
            self.visibility_group("niveauschakelaar", "hidden")

        if self.analogeWaardeTemp:
            self.visibility_group("analogeWaardeTemp", "shown")
        else:
            self.visibility_group("analogeWaardeTemp", "hidden")

        is_gui_mode = (self.controler == "GUI")

        if self.regelbareKleppen:
            visibility = "shown" if is_gui_mode else "hidden"
            self.visibility_group("regelbareKleppen", visibility)
        else:
            self.visibility_group("regelbareKleppen", "hidden")

        if not self.regelbareWeerstand:
            self.visibility_group("regelbareweerstand", "hidden")
            if weerstand:
                self.set_group_color("weerstandStand", green)
            elif not weerstand:
                self.set_group_color("weerstandStand", red)
            else:
                self.set_group_color("weerstandStand", "#FFFFFF")
        else:
            visibility = "shown" if is_gui_mode else "hidden"
            self.visibility_group("regelbareweerstand", visibility)

        if self.KlepStandBoven == 0:
            self.klep_breete("waterval", 0)
            self.set_group_color("KlepBoven", "#FFFFFF")
        else:
            self.klep_breete("waterval", self.KlepStandBoven)
            self.set_group_color("KlepBoven", self.kleurWater)

        if self.KlepStandBeneden == 0:
            self.klep_breete("waterBeneden", 0)
            self.set_group_color("KlepBeneden", "#FFFFFF")
        else:
            self.klep_breete("waterBeneden", self.KlepStandBeneden)
            self.set_group_color("KlepBeneden", self.kleurWater)

        if tempVat == self.tempWeerstand:
            self.set_group_color("temperatuurVat", green)
        else:
            self.set_group_color("temperatuurVat", red)

        self.set_svg_text("klepstandBoven", str(self.KlepStandBoven) + "%")
        self.set_svg_text("KlepstandBeneden", str(self.KlepStandBeneden) + "%")
        self.set_svg_text("debiet", str(self.toekomendDebiet) + "l/s")
        self.set_svg_text("temperatuurWarmteweerstand",
                          str(self.tempWeerstand) + "°C")
        self.set_svg_text("temperatuurVatWaarde", str(tempVat) + "°C")

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
            self.set_group_color("niveauschakelaar", green)
        else:
            self.set_group_color("niveauschakelaar", red)

        hoogteVatGui = currentHoogteVat / maxHoogteVat * self.maxHoogteGUI
        nieuweY = self.ondersteY - hoogteVatGui

        if self.waterInVat is not None:
            self.waterInVat.set("height", str(hoogteVatGui))
            self.waterInVat.set("y", str(nieuweY))

        self.set_hoogte_indicator("hoogteIndicator", nieuweY)
        self.set_hoogte_indicator("hoogteTekst", nieuweY + 2)
        self.set_svg_text("hoogteTekst", str(int(currentHoogteVat)) + "mm")

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
