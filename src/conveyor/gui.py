import os
import xml.etree.ElementTree as ET
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QLabel
from PyQt5.QtCore import QSize, QRectF
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter


class SvgDisplay(QWidget):
    """Widget that only renders the SVG."""
    # Scales the SVG proportionally within the widget

    def __init__(self, renderer):
        super().__init__()
        self.renderer = renderer
        # Set size policy to expand and fill available space
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(50, 50)

    def sizeHint(self):
        return QSize(600, 400)

    def paintEvent(self, event):
        painter = QPainter(self)
        # Calculate aspect ratio
        svg_size = self.renderer.defaultSize()
        if svg_size.width() > 0 and svg_size.height() > 0:
            widget_rect = self.rect()
            if widget_rect.width() > 0 and widget_rect.height() > 0:
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
        else:
            self.renderer.render(painter)


class TransportbandWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setStretchFactor(layout, 1)

        # Load SVG
        svg_path = None
        try:
            # Get path to the SVG file
            current_dir = Path(__file__).resolve().parent
            gui_common_dir = current_dir.parent / "guiCommon"
            svg_path = gui_common_dir / "media" / "transportband.svg"

            # Verify file exists
            if not svg_path.exists():
                svg_path = current_dir / "media" / "transportband.svg"
                if not svg_path.exists():
                    raise FileNotFoundError(f"SVG file not found at {svg_path}")

            # Renderer
            self.renderer = QSvgRenderer(str(svg_path))
            if not self.renderer.isValid():
                raise RuntimeError(f"SVG file is invalid: {svg_path}")
            
            self.svg_widget = SvgDisplay(self.renderer)
            layout.addWidget(self.svg_widget, 1)
        except Exception as e:
            # Create empty widget with error message
            error_label = QLabel(f"Error loading SVG: {str(e)}")
            layout.addWidget(error_label)
