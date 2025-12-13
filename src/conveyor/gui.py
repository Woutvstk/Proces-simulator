import os
import xml.etree.ElementTree as ET
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QSize,QRectF
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter

class SvgDisplay(QWidget):
    """Widget that only renders the SVG."""
    # Scales the SVG proportionally within the widget
    def __init__(self, renderer):
        super().__init__()
        self.renderer = renderer
        self.setMinimumSize(300, 350)  
        self.setMaximumSize(1200, 1400) #(maintains ratio 300:350)

    def sizeHint(self):
        return QSize(300, 350)

    def paintEvent(self, event):
        painter = QPainter(self)
        # Calculate aspect ratio
        svg_size = self.renderer.defaultSize()
        if svg_size.width() > 0 and svg_size.height() > 0:
            widget_rect = self.rect()
            svg_ratio = svg_size.width() / svg_size.height()
            widget_ratio = widget_rect.width() / widget_rect.height()
            
            if widget_ratio > svg_ratio:
                # Widget is wider, fit on height
                new_width = int(widget_rect.height() * svg_ratio)
                x_offset = (widget_rect.width() - new_width) // 2
                target_rect = widget_rect.adjusted(x_offset, 0, -x_offset, 0)
            else:
                # Widget is taller, fit on width
                new_height = int(widget_rect.width() / svg_ratio)
                y_offset = (widget_rect.height() - new_height) // 2
                target_rect = widget_rect.adjusted(0, y_offset, 0, -y_offset)
            
            # Convert QRect to QRectF
            target_rectf = QRectF(target_rect)
            self.renderer.render(painter, target_rectf)
        else:
            self.renderer.render(painter)

class TransportbandWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout(self)
        
        # Load SVG
        try:
            # Get path to the SVG file
            current_dir = Path(__file__).resolve().parent
            gui_common_dir = current_dir.parent / "guiCommon" 
            svg_path= gui_common_dir / "media" / "transportband.svg"
            print("gevonden")
            
            # NOTE: ET.parse accepts Path objects since Python 3.9, 
            # but using str() or .as_posix() is safer for compatibility.
            tree = ET.parse(str(svg_path)) 
            root = tree.getroot()
        except Exception as e:
            # Check if the file exists before raising an exception
            if not svg_path.exists():
                raise RuntimeError(f"Cannot load 'transportband.svg': File not found at {svg_path}")
            else:
                raise RuntimeError("Cannot load 'transportband.svg': " + str(e))
        
        # Renderer
        # FIX: Convert the Path object to a string for QSvgRenderer
        self.renderer = QSvgRenderer(str(svg_path)) 
        self.svg_widget = SvgDisplay(self.renderer)
        layout.addWidget(self.svg_widget)