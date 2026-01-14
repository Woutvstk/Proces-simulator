"""
Trend Graph Window - Displays real-time temperature and level trends in floating windows
"""

from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSpinBox, QPushButton
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from collections import deque
import logging

logger = logging.getLogger(__name__)


class TrendGraphWindow(QMainWindow):
    """Floating window for displaying real-time trends"""
    
    def __init__(self, title="Trend Graph", parent=None, max_points=300, y_min=0, y_max=100):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(800, 550)
        
        # Graph data storage (max 300 points = ~30 seconds at 10Hz)
        self.max_points = max_points
        self.timestamps = deque(maxlen=max_points)
        self.values = deque(maxlen=max_points)
        self.counter = 0
        
        # Y-axis limits (customizable)
        self.y_min = y_min
        self.y_max = y_max
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.figure.patch.set_facecolor('#1a1a1a')
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#2d2d2d')
        self.ax.grid(True, alpha=0.2, color='#3d3d3d')
        
        # Labels
        self.ax.set_xlabel('Time (samples)', color='#c9d1d9', fontsize=10)
        self.ax.set_ylabel('Value', color='#c9d1d9', fontsize=10)
        self.ax.tick_params(colors='#c9d1d9')
        
        # Line
        self.line, = self.ax.plot([], [], color='#58a6ff', linewidth=2, label='Live Data')
        self.ax.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='#3d3d3d', 
                      labelcolor='#c9d1d9')
        self.ax.set_ylim([self.y_min, self.y_max])
        
        # Create canvas
        self.canvas = FigureCanvas(self.figure)
        
        # Controls toolbar
        self.setup_toolbar()
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(self.toolbar_layout)
        main_layout.addWidget(self.canvas, 1)
        
        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.update_timer.start(100)  # Update every 100ms
    
    def setup_toolbar(self):
        """Setup control toolbar with Y-axis adjustments"""
        self.toolbar_layout = QHBoxLayout()
        
        # Y-Min label and spinbox
        self.toolbar_layout.addWidget(QLabel("Y Min:"))
        self.spinbox_y_min = QSpinBox()
        self.spinbox_y_min.setMinimum(-9999)
        self.spinbox_y_min.setMaximum(9999)
        self.spinbox_y_min.setValue(int(self.y_min))
        self.spinbox_y_min.setMaximumWidth(80)
        self.spinbox_y_min.valueChanged.connect(self.on_y_min_changed)
        self.toolbar_layout.addWidget(self.spinbox_y_min)
        
        # Y-Max label and spinbox
        self.toolbar_layout.addWidget(QLabel("Y Max:"))
        self.spinbox_y_max = QSpinBox()
        self.spinbox_y_max.setMinimum(-9999)
        self.spinbox_y_max.setMaximum(9999)
        self.spinbox_y_max.setValue(int(self.y_max))
        self.spinbox_y_max.setMaximumWidth(80)
        self.spinbox_y_max.valueChanged.connect(self.on_y_max_changed)
        self.toolbar_layout.addWidget(self.spinbox_y_max)
        
        # Clear button
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setMaximumWidth(80)
        self.btn_clear.clicked.connect(self.clear_data)
        self.toolbar_layout.addWidget(self.btn_clear)
        
        # Stretch to fill remaining space
        self.toolbar_layout.addStretch()
    
    def on_y_min_changed(self, value):
        """Handle Y-min change"""
        self.y_min = value
        if self.y_min < self.y_max:
            self.ax.set_ylim([self.y_min, self.y_max])
            self.canvas.draw_idle()
    
    def on_y_max_changed(self, value):
        """Handle Y-max change"""
        self.y_max = value
        if self.y_max > self.y_min:
            self.ax.set_ylim([self.y_min, self.y_max])
            self.canvas.draw_idle()
    
    def add_value(self, value):
        """Add a new data point to the trend"""
        try:
            self.values.append(float(value))
            self.timestamps.append(self.counter)
            self.counter += 1
        except Exception as e:
            logger.error(f"Error adding trend value: {e}")
    
    def update_plot(self):
        """Update the plot with current data"""
        try:
            if len(self.values) > 0:
                self.line.set_data(list(self.timestamps), list(self.values))
                self.ax.relim()
                self.ax.autoscale_view()
                self.canvas.draw_idle()
        except Exception as e:
            logger.error(f"Error updating trend plot: {e}")
    
    def clear_data(self):
        """Clear all stored data"""
        self.values.clear()
        self.timestamps.clear()
        self.counter = 0
        self.line.set_data([], [])
        self.canvas.draw_idle()
    
    def closeEvent(self, event):
        """Handle window close"""
        self.update_timer.stop()
        event.accept()


class TemperatureTrendWindow(TrendGraphWindow):
    """Specialized window for temperature trends"""
    
    def __init__(self, parent=None):
        super().__init__(title="Temperature Trend", parent=parent, max_points=300, y_min=0, y_max=100)
        self.setWindowTitle("Temperature Trend (°C)")
        self.ax.set_ylabel('Temperature (°C)', color='#c9d1d9', fontsize=10)
        self.line.set_color('#ff6b6b')  # Red for temperature
        self.line.set_label('Temperature (°C)')
        self.ax.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='#3d3d3d', 
                      labelcolor='#c9d1d9')
        # Update spinbox labels and limits
        self.spinbox_y_min.setMinimum(-50)
        self.spinbox_y_min.setMaximum(150)
        self.spinbox_y_max.setMinimum(-50)
        self.spinbox_y_max.setMaximum(150)


class LevelTrendWindow(TrendGraphWindow):
    """Specialized window for level/volume trends"""
    
    def __init__(self, parent=None):
        super().__init__(title="Level Trend", parent=parent, max_points=300, y_min=0, y_max=200)
        self.setWindowTitle("Level Trend (liters)")
        self.ax.set_ylabel('Level (liters)', color='#c9d1d9', fontsize=10)
        self.line.set_color('#51cf66')  # Green for level
        self.line.set_label('Level (liters)')
        self.ax.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='#3d3d3d', 
                      labelcolor='#c9d1d9')
        # Update spinbox labels and limits
        self.spinbox_y_min.setMinimum(-100)
        self.spinbox_y_min.setMaximum(500)
        self.spinbox_y_max.setMinimum(-100)
        self.spinbox_y_max.setMaximum(500)


class TrendGraphManager:
    """Manages multiple trend graph windows"""
    
    def __init__(self):
        self.temp_window = None
        self.level_window = None
    
    def _is_window_valid(self, window):
        """Check if window is still valid and not deleted"""
        try:
            if window is None:
                return False
            # Try to access a property to see if the C++ object still exists
            _ = window.isVisible()
            return True
        except RuntimeError:
            # Object has been deleted
            return False
    
    def show_temperature_trend(self, parent=None):
        """Show or bring to front temperature trend window"""
        try:
            # Check if existing window is still valid
            if not self._is_window_valid(self.temp_window):
                self.temp_window = None
            
            # Create new window if needed
            if self.temp_window is None:
                self.temp_window = TemperatureTrendWindow(parent)
                self.temp_window.show()
            else:
                self.temp_window.raise_()
                self.temp_window.activateWindow()
            return self.temp_window
        except Exception as e:
            logger.error(f"Error showing temperature trend: {e}")
            self.temp_window = None
            return None
    
    def show_level_trend(self, parent=None):
        """Show or bring to front level trend window"""
        try:
            # Check if existing window is still valid
            if not self._is_window_valid(self.level_window):
                self.level_window = None
            
            # Create new window if needed
            if self.level_window is None:
                self.level_window = LevelTrendWindow(parent)
                self.level_window.show()
            else:
                self.level_window.raise_()
                self.level_window.activateWindow()
            return self.level_window
        except Exception as e:
            logger.error(f"Error showing level trend: {e}")
            self.level_window = None
            return None
    
    def add_temperature(self, value):
        """Add temperature data to trend if window is open"""
        try:
            if self._is_window_valid(self.temp_window):
                self.temp_window.add_value(value)
        except RuntimeError:
            self.temp_window = None
    
    def add_level(self, value):
        """Add level data to trend if window is open"""
        try:
            if self._is_window_valid(self.level_window):
                self.level_window.add_value(value)
        except RuntimeError:
            self.level_window = None
    
    def close_all(self):
        """Close all trend windows"""
        try:
            if self.temp_window and self._is_window_valid(self.temp_window):
                self.temp_window.close()
        except RuntimeError:
            pass
        finally:
            self.temp_window = None
        
        try:
            if self.level_window and self._is_window_valid(self.level_window):
                self.level_window.close()
        except RuntimeError:
            pass
        finally:
            self.level_window = None
