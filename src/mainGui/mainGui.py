import sys
import os
import xml.etree.ElementTree as ET

from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QPushButton, QMenu, QAction,
    QWidget, QVBoxLayout
)
from PyQt5.QtCore import QTimer, QSize
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter

from guiCommon.QtDesignerLayout import *

red = "#FF0000"
orange = "#FFA500"
blue = "#1100FF"
green = "#00FF00"


maxHoogteVat = 2000
weerstand = True
tempVat = 100
currentHoogteVat = 2000


class SvgDisplay(QWidget):
    """Widget dat alleen de SVG rendert."""

    def __init__(self, renderer):
        super().__init__()
        self.renderer = renderer

    def sizeHint(self):
        return QSize(300, 350)

    def paintEvent(self, event):
        painter = QPainter(self)
        self.renderer.render(painter)


class VatWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # DEFAULTS: zorg dat alle gebruikte attributes bestaan
        # (worden later overschreven door MainWindow.update_values)
        self.toekomendDebiet = 0
        self.tempWeerstand = 20.0
        self.regelbareKleppen = False
        self.regelbareWeerstand = False
        self.niveauschakelaar = False
        self.analogeWaardeTemp = False
        self.KlepStandBoven = 0
        self.KlepStandBeneden = 0
        self.kleurWater = blue
        self.controler = "LOGO"

        # extra defaults voor GUI elementen die mogelijk niet in SVG zitten
        self.waterInVat = None
        self.originalY = 0.0
        self.originalHoogte = 0.0
        self.maxHoogteGUI = 80
        self.ondersteY = 0.0

        # SVG inladen
        try:
            svg_path = os.path.join(os.path.dirname(
                __file__), "media", "SVGVat.svg")
            self.tree = ET.parse(svg_path)
            self.root = self.tree.getroot()
            self.ns = {"svg": "http://www.w3.org/2000/svg"}
        except Exception as e:
            raise RuntimeError("Kan 'SVG vat.svg' niet inladen: " + str(e))

        # Renderer
        self.renderer = QSvgRenderer()
        self.svg_widget = SvgDisplay(self.renderer)
        layout.addWidget(self.svg_widget)

        # eerste render
        self.rebuild()

    def rebuild(self):
        global currentHoogteVat, maxHoogteVat

        # Kleur water
        self.set_group_color("waterTotaal", self.kleurWater)

        # veilige ratio berekening voor temperatuurpercent

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

        # Onzichtbaar maken van items
        if self.niveauschakelaar:
            self.visibility_group("niveauschakelaar", "shown")
        else:
            self.visibility_group("niveauschakelaar", "hidden")
        if self.analogeWaardeTemp:
            self.visibility_group("analogeWaardeTemp", "shown")
        else:
            self.visibility_group("analogeWaardeTemp", "hidden")
        if self.regelbareKleppen:
            self.visibility_group("regelbareKleppen", "shown")
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
            self.visibility_group("regelbareweerstand", "shown")

        # Klep boven
        if self.KlepStandBoven == 0:
            self.klep_breete("waterval", 0)
            self.set_group_color("KlepBoven", "#FFFFFF")

        else:
            self.klep_breete("waterval", self.KlepStandBoven)
            self.set_group_color("KlepBoven", self.kleurWater)

        # Klep beneden

        if self.KlepStandBeneden == 0:
            self.klep_breete("waterBeneden", 0)
            self.set_group_color("KlepBeneden", "#FFFFFF")
        else:
            self.klep_breete("waterBeneden", self.KlepStandBeneden)
            self.set_group_color("KlepBeneden", self.kleurWater)

        # temperatuur vat kleur
        if tempVat == self.tempWeerstand:
            self.set_group_color("temperatuurVat", green)
        else:
            self.set_group_color("temperatuurVat", red)

        # Teksten
        self.set_svg_text("klepstandBoven", str(self.KlepStandBoven) + "%")
        self.set_svg_text("KlepstandBeneden", str(self.KlepStandBeneden) + "%")
        self.set_svg_text("debiet", str(self.toekomendDebiet) + "l/s")
        self.set_svg_text("temperatuurWarmteweerstand",
                          str(self.tempWeerstand) + "°C")
        self.set_svg_text("temperatuurVatWaarde", str(tempVat) + "°C")

        # water element
        self.waterInVat = self.root.find(
            f".//svg:*[@id='waterInVat']", self.ns)

        if self.waterInVat is not None:
            # beware: attributes uit SVG zijn strings
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
        xml_bytes = ET.tostring(self.root, encoding="utf-8")
        self.renderer.load(xml_bytes)

    def vat_vullen_GUI(self):
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
        self.set_hoogte_indicator("hoogteTekst", nieuweY+2)
        self.set_svg_text("hoogteTekst", str(int(currentHoogteVat)) + "mm")

    def set_hoogte_indicator(self, itemId, hoogte):
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is not None:
            item.set("y", str(hoogte))
        else:
            print(
                f"Waarschuwing: groep '{itemId}' niet gevonden om hoogte te wijzigen.")

    def set_group_color(self, groupId, kleur):
        group = self.root.find(f".//svg:g[@id='{groupId}']", self.ns)
        if group is not None:
            for element in group:
                element.set("fill", kleur)
        else:
            print(
                f"Waarschuwing: groep '{groupId}' niet gevonden om kleur te wijzigen.")

    def visibility_group(self, groupId, visibility):
        group = self.root.find(f".//svg:g[@id='{groupId}']", self.ns)
        if group is not None:
            group.set("visibility", visibility)
        else:
            print(
                f"Waarschuwing: groep '{groupId}' niet gevonden om te" + visibility + ".")

    def klep_breete(self, itemId, KlepStand):
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is not None:

            new_width = (KlepStand * 0.0645)
            new_x = 105.745 - (KlepStand * 0.065) / 2
            item.set("width", str(new_width))
            item.set("x", str(new_x))
        else:
            print(
                f"Waarschuwing: item '{itemId}' niet gevonden om breedte aan te passen.")

    def set_svg_text(self, itemId, value):
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is not None:

            tspan = item.find("svg:tspan", self.ns)
            if tspan is not None:
                tspan.text = value
            else:
                item.text = value
        else:
            print(
                f"Waarschuwing: item '{itemId}' niet gevonden om tekt te wijzigen.")


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.fullMenuWidget.hide()
        self.ui.stackedWidget.setCurrentIndex(0)
        self.ui.pushButton_simPage2.setChecked(True)
        self.ui.regelingSimGui.setVisible(False)

        # timer voor automatische updates
        self.timer = QTimer()
        self.timer.setInterval(100)   # 10x per seconde
        self.timer.timeout.connect(self.update_values)
        self.timer.start()

        container = self.ui.vatWidgetContainer
        self.vat_widget = VatWidget()
        layout = container.layout()
        layout.addWidget(self.vat_widget)

        # --- Zet hier éénmalig de connecties voor synchronisatie van velden ---
        self.entryGroupDebiet = [
            self.ui.toekomendDebietEntry,
            self.ui.toekomendDebietEntry1,
            self.ui.toekomendDebietEntry2
        ]
        self.entryGroupTemp = [
            self.ui.tempWeerstandEntry,
            self.ui.tempWeerstandEntry1
        ]

        # Connecteer tekstveranderingen éénmalig; gebruik default-argument om groep te binden
        for group in (self.entryGroupDebiet, self.entryGroupTemp):
            for field in group:
                field.textChanged.connect(
                    lambda text, g=group: self.syncFields(text, g))
        self.ui.kleurDropDown.clear()

        kleuren = [
            ("Blue",  "#0000FF"),
            ("Red",   "#FB5C5C"),
            ("Green",  "#00FF00"),
            ("Yellow",   "#FAFA2B"),
            ("Orange", "#FFB52B"),
            ("Purple",  "#800080"),
            ("Gray",  "#808080"),
        ]

        for naam, hexcode in kleuren:
            self.ui.kleurDropDown.addItem(naam, hexcode)

    def update_values(self):
        try:
            # Lees waarden uit UI en zet ze op vat_widget (geef types)
            self.vat_widget.toekomendDebiet = int(
                self.ui.toekomendDebietEntry.text() or 0)
            self.vat_widget.tempWeerstand = float(
                self.ui.tempWeerstandEntry.text() or 20.0)

            self.volume = float(
                self.ui.volumeEntry.text() or 2.0)
            self.IPadress = str(
                self.ui.IPAdress.text() or "192.168.0.1")

            # Is het vat regelbaar?
            regelbaarKleppen = self.ui.regelbareKlepenCheckBox.isChecked()
            self.vat_widget.regelbareKleppen = regelbaarKleppen

            regelbareWeerstand = self.ui.regelbareWeerstandCheckBox.isChecked()
            self.vat_widget.regelbareWeerstand = regelbareWeerstand

            self.ui.regelbareKlepenCheckBox.toggled.connect(
                self.controlerOptie)

            niveauschakelaar = self.ui.niveauschakelaarCheckBox.isChecked()
            self.vat_widget.niveauschakelaar = niveauschakelaar

            analogeWaardeTemp = self.ui.analogeWaardeTempCheckBox.isChecked()
            self.vat_widget.analogeWaardeTemp = analogeWaardeTemp

            if self.vat_widget.controler == "GUI":
                if self.vat_widget.regelbareKleppen:
                    self.ui.GUiSim.hide()
                    self.ui.regelbareKlepenGUISim.show()

                else:
                    self.ui.regelbareKlepenGUISim.hide()
                    self.ui.GUiSim.show()
            else:
                self.ui.GUiSim.hide()
                self.ui.regelbareKlepenGUISim.hide()

            if regelbaarKleppen:
                # Gebruik waardes uit de QLineEdits
                try:
                    self.vat_widget.KlepStandBoven = int(
                        self.ui.klepstandBovenEntry.text() or 0)
                except ValueError:
                    self.vat_widget.KlepStandBoven = 0
                try:
                    self.vat_widget.KlepStandBeneden = int(
                        self.ui.klepstandBenedenEntry.text() or 0)
                except ValueError:
                    self.vat_widget.KlepStandBeneden = 0

            else:
                # Niet regelbaar → kijk naar de andere checkbox
                boven_checked = self.ui.klepstandBovenCheckBox.isChecked()
                beneden_checked = self.ui.klepstandBenedenCheckBox.isChecked()

                self.vat_widget.KlepStandBoven = 100 if boven_checked else 0
                self.vat_widget.KlepStandBeneden = 100 if beneden_checked else 0

            self.ui.kleurDropDown.currentIndexChanged.connect(
                self.kleurOptie)
            self.ui.controlerDropDown.currentIndexChanged.connect(
                self.controlerOptie)

        except Exception as e:
            # log fout zodat je weet wat er mis ging
            print("Fout in update_values:", e)

        # volledig opnieuw doorlopen van VatWidget
        self.vat_widget.rebuild()

    def controlerOptie(self):
        self.vat_widget.controler = self.ui.controlerDropDown.currentText()

    def kleurOptie(self):
        self.vat_widget.kleurWater = self.ui.kleurDropDown.currentData()

    def syncFields(self, text, group):
        for field in group:
            if field.text() != text:
                field.blockSignals(True)
                field.setText(text)
                field.blockSignals(False)

    def on_stackedWidget_currentChanged(self, index):
        btn_list = self.ui.iconOnlyWidget.findChildren(QPushButton) \
            + self.ui.fullMenuWidget.findChildren(QPushButton)
        for btn in btn_list:
            btn.setAutoExclusive(index not in [5, 6])
            if index in [5, 6]:
                btn.setChecked(False)

    # overige toggle handlers blijven hetzelfde
    def on_pushButton_settingsPage1_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(3)

    def on_pushButton_settingsPage2_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(3)

    def on_pushButton_IOPage1_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(4)

    def on_pushButton_IOPage2_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(4)

    def on_pushButton_simPage2_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(0)

    def on_pushButton_simPage_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(0)

    def on_pushButton_1Vat_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(0)

    def on_pushButton_2Vatten_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(1)

    def on_pushButton_transportband_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(2)

    def simOptions(self):
        options = ["PID regelaar 1 vat",
                   "PID regelaar 2 vatten", "Transportband"]
        button = self.ui.pushButton_simPage
        self.showSimoptions(button, options)

    def showSimoptions(self, button, options):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu{
                background-color: #fff;
                color: #000;
            }
            QMenu::item:selected{
                background-color: #ddd;
                color: #000;
            }
        """)
        for optionText in options:
            action = QAction(optionText, self)
            action.triggered.connect(self.HandleOptionsClick)
            menu.addAction(action)
        menu.move(button.mapToGlobal(button.rect().bottomLeft()))
        menu.exec_()

    def HandleOptionsClick(self):
        text = self.sender().text()
        if text == "PID regelaar 1 vat":
            self.ui.stackedWidget.setCurrentIndex(0)
        elif text == "PID regelaar 2 vatten":
            self.ui.stackedWidget.setCurrentIndex(1)
        elif text == "Transportband":
            self.ui.stackedWidget.setCurrentIndex(2)


# pyuic5 -x QtDesignerLayout.ui -o QtDesignerLayout.py
# pyrcc5 Resource.qrc -o Resource_rc.py
