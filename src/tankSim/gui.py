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

from QtDesignerLayout import Ui_MainWindow

red = "#FF0000"
orange = "#FFA500"
blue = "#1100FF"
green = "#00FF00"
kleurWater = blue
niveauschakelaars = True
analogeWaardeTemp = False
regelbareKleppen = True
regelbaareWeerstand = True
weerstand = True

tempVat = 100
maxHoogteVat = 2000
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
    def __init__(self, KlepStandBoven, KlepStandBeneden, toekomendDebiet, tempWeerstand):
        super().__init__()
        self.KlepStandBoven = KlepStandBoven
        self.KlepStandBeneden = KlepStandBeneden
        self.toekomendDebiet = toekomendDebiet
        self.tempWeerstand = tempWeerstand

        layout = QVBoxLayout(self)

        # SVG inladen
        try:
            self.tree = ET.parse("SVG vat.svg")
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
        self.set_group_color("waterTotaal", kleurWater)

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
        if not niveauschakelaars:
            self.hide_group("niveauschakelaars")
        if not analogeWaardeTemp:
            self.hide_group("analogeWaardeTemp")
        if not regelbareKleppen:
            self.hide_group("regelbareKleppen")
        if not regelbaareWeerstand:
            self.hide_group("regelbareweerstand")
            if weerstand:
                self.set_group_color("weerstandStand", green)
            elif not weerstand:
                self.set_group_color("weerstandStand", red)
            else:
                self.set_group_color("weerstandStand", "#FFFFFF")

        # Klep boven
        if self.KlepStandBoven == 0:
            self.hide_item("waterval")
        else:
            self.klep_breete("waterval", self.KlepStandBoven)
            self.set_group_color("KlepBoven", kleurWater)

        # Klep beneden
        if self.KlepStandBeneden == 0:
            self.hide_item("waterBeneden")
        else:
            self.klep_breete("waterBeneden", self.KlepStandBeneden)
            self.set_group_color("KlepBeneden", kleurWater)

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
        self.set_svg_text("analogeWaardeTemp", str(tempVat) + "°C")

        # water element
        self.waterInVat = self.root.find(
            f".//svg:*[@id='waterInVat']", self.ns)

        if self.waterInVat is not None:
            self.originalY = float(self.waterInVat.get("y"))
            self.originalHoogte = float(self.waterInVat.get("height"))
            self.maxHoogteGUI = 85
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
        self.set_hoogte_indicator("hoogteTekst", nieuweY)
        self.set_svg_text("hoogteTekst", str(int(currentHoogteVat)) + "mm")

    def set_hoogte_indicator(self, itemId, hoogte):
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is not None:
            item.set("y", str(hoogte))

    def set_group_color(self, groupId, kleur):
        group = self.root.find(f".//svg:g[@id='{groupId}']", self.ns)
        if group is not None:
            for element in group:
                element.set("fill", kleur)

    def hide_group(self, groupId):
        group = self.root.find(f".//svg:g[@id='{groupId}']", self.ns)
        if group is not None:
            group.set("visibility", "hidden")

    def hide_item(self, itemId):
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is not None:
            item.set("display", "none")

    def klep_breete(self, itemId, extra_width):
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is None:
            return

        x = float(item.get("x"))
        w = float(item.get("width"))
        new_width = w + (extra_width * 0.0645)
        new_x = x - (extra_width * 0.065) / 2
        item.set("width", str(new_width))
        item.set("x", str(new_x))

    def set_svg_text(self, itemId, value):
        item = self.root.find(f".//svg:*[@id='{itemId}']", self.ns)
        if item is None:
            return

        tspan = item.find("svg:tspan", self.ns)
        if tspan is not None:
            tspan.text = value
        else:
            item.text = value


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.fullMenuWidget.hide()
        self.ui.stackedWidget.setCurrentIndex(0)
        self.ui.pushButton_simPage2.setChecked(True)

        # timer voor automatische updates
        self.timer = QTimer()
        self.timer.setInterval(100)   # 10x per seconde
        self.timer.timeout.connect(self.update_values)
        self.timer.start()

        # veilige lees van QLineEdits
        KlepStandBoven = int(self.ui.klepstandBovenEntry.text() or 0)
        KlepStandBeneden = int(self.ui.klepstandBenedenEntry.text() or 0)
        toekomendDebiet = int(self.ui.toekomendDebietEntry.text() or 0)
        tempWeerstand = float(self.ui.tempWeerstandEntry.text() or 20.0)

        container = self.ui.vatWidgetContainer
        self.vat_widget = VatWidget(
            KlepStandBoven,
            KlepStandBeneden,
            toekomendDebiet,
            tempWeerstand
        )
        layout = container.layout()
        layout.addWidget(self.vat_widget)

    def update_values(self):
        try:
            self.vat_widget.KlepStandBoven = int(
                self.ui.klepstandBovenEntry.text() or 0)
            self.vat_widget.KlepStandBeneden = int(
                self.ui.klepstandBenedenEntry.text() or 0)
            self.vat_widget.toekomendDebiet = int(
                self.ui.toekomendDebietEntry.text() or 0)
            self.vat_widget.tempWeerstand = float(
                self.ui.tempWeerstandEntry.text() or 20.0)

        except:
            pass

        # volledig opnieuw doorlopen van VatWidget
        self.vat_widget.rebuild()

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    base_path = os.path.dirname(os.path.abspath(__file__))
    style_path = os.path.join(base_path, "style.qss")

    if os.path.exists(style_path):
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())
    else:
        print("style.qss niet gevonden")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
