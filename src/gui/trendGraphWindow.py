"""
Trend Graph Window - Displays real-time temperature and level trends in floating windows
"""

from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSpinBox, QPushButton, QComboBox
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
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
        self.resize(1040, 715)  # 30% bigger than original 800x550
        
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
        
        # Calculate padded Y-max: 20% of range + 20 units
        # This provides automatic headroom for realistic visualization
        y_range = max(1, self.y_max - self.y_min)
        self.y_padding = y_range * 0.2 + 20
        padded_y_max = self.y_max + self.y_padding
        
        self.ax.set_ylim([self.y_min, padded_y_max])
        
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
        # Calculate padded Y-max to maintain consistent spacing
        y_range = max(1, self.y_max - self.y_min)
        padding = y_range * 0.2 + 20  # 20% of range + 20 units
        padded_y_max = self.y_max + padding
        
        if padded_y_max > self.y_min:
            self.ax.set_ylim([self.y_min, padded_y_max])
            self.canvas.draw_idle()
    
    def on_y_max_changed(self, value):
        """Handle Y-max change"""
        self.y_max = value
        # Calculate padded Y-max: add 20% of the range + 20 units
        # This provides automatic headroom for realistic visualization
        y_range = max(1, self.y_max - self.y_min)  # Avoid division by zero
        padding = y_range * 0.2 + 20  # 20% of range + 20 units
        padded_y_max = self.y_max + padding
        
        if padded_y_max > self.y_min:
            self.ax.set_ylim([self.y_min, padded_y_max])
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
    """Specialized window for temperature trends with setpoint line and heating power subplot"""
    
    def __init__(self, parent=None, boiling_temp=100.0):
        super().__init__(title="Temperature Trend", parent=parent, max_points=300, y_min=0, y_max=boiling_temp+10)
        self.setWindowTitle("Temperature Trend (°C)")
        self.boiling_temp = boiling_temp
        
        # Store all temperature and power data for history switching
        self.all_temperatures = deque(maxlen=10000)  # Store full history
        self.all_power = deque(maxlen=10000)
        self.sample_counter = 0
        
        # Mode: 'live' for last 300 samples, 'history' for all samples from start
        self.view_mode = 'live'  # Default to live mode
        
        # Setpoint tracking
        self.setpoint_value = 50.0
        self.setpoint_line = None
        
        # Replace old single axis with subplots
        self.figure.clear()
        
        # Create GridSpec with height ratios (temperature 30% larger than power)
        gs = GridSpec(2, 1, figure=self.figure, height_ratios=[1.3, 1.0])
        
        # Temperature subplot (top, 56% of height)
        self.ax = self.figure.add_subplot(gs[0])
        self.ax.set_facecolor('#2d2d2d')
        self.ax.grid(True, alpha=0.2, color='#3d3d3d')
        self.ax.set_ylabel('Temperature (°C)', color='#c9d1d9', fontsize=10)
        self.ax.tick_params(colors='#c9d1d9')
        
        # Temperature line
        self.line, = self.ax.plot([], [], color='#ff6b6b', linewidth=2, label='Temperature (°C)')
        
        # Setpoint line (horizontal)
        self.setpoint_line, = self.ax.plot([], [], color='#ffd700', linewidth=2, linestyle='--', label='Setpoint')
        
        # Power subplot (bottom, 44% of height)
        self.ax_power = self.figure.add_subplot(gs[1])
        self.ax_power.set_facecolor('#2d2d2d')
        self.ax_power.grid(True, alpha=0.2, color='#3d3d3d')
        self.ax_power.set_xlabel('Time (samples)', color='#c9d1d9', fontsize=10)
        self.ax_power.set_ylabel('Heating Power (%)', color='#c9d1d9', fontsize=10)
        self.ax_power.tick_params(colors='#c9d1d9')
        self.ax_power.set_ylim([0, 110])
        
        # Power line
        self.line_power, = self.ax_power.plot([], [], color='#ff9999', linewidth=2, label='Heating Power (%)')
        
        # Legends
        self.ax.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='#3d3d3d', labelcolor='#c9d1d9')
        self.ax_power.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='#3d3d3d', labelcolor='#c9d1d9')
        
        # Set temperature axis limits (0 to boiling_temp + 10)
        temp_max_display = boiling_temp + 10
        y_range = max(1, temp_max_display - 0)
        y_padding = y_range * 0.2 + 20
        padded_y_max = temp_max_display + y_padding
        self.ax.set_ylim([0, padded_y_max])
        
        # Recreate canvas
        self.canvas = FigureCanvas(self.figure)
        
        # Update toolbar (call without parameter now, will use self.boiling_temp)
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
        self.update_timer.start(100)
    
    def setup_toolbar(self, boiling_temp=100.0):
        """Setup enhanced toolbar with mode selection and limit controls"""
        from PyQt5.QtWidgets import QComboBox, QLabel, QSpinBox, QPushButton, QHBoxLayout, QCheckBox
        
        # Use boiling_temp from self if available (for TemperatureTrendWindow override)
        if hasattr(self, 'boiling_temp'):
            boiling_temp = self.boiling_temp
        
        self.toolbar_layout = QHBoxLayout()
        
        # View Mode selector
        self.toolbar_layout.addWidget(QLabel("View Mode:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Live (Last 300)", "live")
        self.combo_mode.addItem("History (All)", "history")
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        self.toolbar_layout.addWidget(self.combo_mode)
        
        self.toolbar_layout.addSpacing(20)
        
        # Temperature limits
        self.toolbar_layout.addWidget(QLabel("T Min (°C):"))
        self.spinbox_t_min = QSpinBox()
        self.spinbox_t_min.setMinimum(-50)
        self.spinbox_t_min.setMaximum(150)
        self.spinbox_t_min.setValue(0)
        self.spinbox_t_min.setMaximumWidth(80)
        self.spinbox_t_min.valueChanged.connect(self.on_temp_limits_changed)
        self.toolbar_layout.addWidget(self.spinbox_t_min)
        
        self.toolbar_layout.addWidget(QLabel("T Max (°C):"))
        self.spinbox_t_max = QSpinBox()
        self.spinbox_t_max.setMinimum(-50)
        self.spinbox_t_max.setMaximum(150)
        self.spinbox_t_max.setValue(int(boiling_temp + 10))
        self.spinbox_t_max.setMaximumWidth(80)
        self.spinbox_t_max.valueChanged.connect(self.on_temp_limits_changed)
        self.toolbar_layout.addWidget(self.spinbox_t_max)
        
        self.toolbar_layout.addSpacing(20)
        
        # Clear button
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setMaximumWidth(80)
        self.btn_clear.clicked.connect(self.clear_data)
        self.toolbar_layout.addWidget(self.btn_clear)
        
        # Stretch to fill remaining space
        self.toolbar_layout.addStretch()
    
    def on_mode_changed(self, index):
        """Handle view mode change"""
        self.view_mode = self.combo_mode.currentData()
        self.update_plot()
    
    def on_temp_limits_changed(self):
        """Handle temperature limit changes"""
        t_min = self.spinbox_t_min.value()
        t_max = self.spinbox_t_max.value()
        
        if t_max > t_min:
            y_range = max(1, t_max - t_min)
            padding = y_range * 0.2 + 20
            padded_y_max = t_max + padding
            self.ax.set_ylim([t_min, padded_y_max])
            self.canvas.draw_idle()
    
    def add_value(self, value, power_fraction=0.0):
        """Add temperature and power data point"""
        try:
            self.values.append(float(value))
            self.timestamps.append(self.counter)
            self.counter += 1
            
            # Store in full history
            self.all_temperatures.append(float(value))
            self.all_power.append(float(power_fraction) * 100.0)  # Convert to percentage
            
        except Exception as e:
            logger.error(f"Error adding trend value: {e}")
    
    def set_setpoint(self, sp_value):
        """Update the setpoint value for display"""
        self.setpoint_value = float(sp_value)
    
    def update_plot(self):
        """Update both temperature and power plots"""
        try:
            if len(self.values) > 0:
                if self.view_mode == 'live':
                    # Show only last 300 samples
                    x_data = list(self.timestamps)
                    y_temp = list(self.values)
                    # Use same x-axis length for power
                    num_samples = len(self.timestamps)
                    power_data = list(self.all_power)[-num_samples:] if len(self.all_power) >= num_samples else list(self.all_power)
                else:  # history mode
                    # Show all samples from sample 0
                    x_data = list(range(len(self.all_temperatures)))
                    y_temp = list(self.all_temperatures)
                    power_data = list(self.all_power)
                
                # Update temperature line
                self.line.set_data(x_data, y_temp)
                
                # Update setpoint line (horizontal across entire plot)
                if len(x_data) > 0:
                    self.setpoint_line.set_data([x_data[0], x_data[-1]], [self.setpoint_value, self.setpoint_value])
                
                # Update power line
                if len(power_data) > 0:
                    self.line_power.set_data(x_data[-len(power_data):], power_data)
                
                # Adjust axes
                self.ax.relim()
                self.ax.autoscale_view()
                self.ax_power.relim()
                self.ax_power.autoscale_view()
                
                self.canvas.draw_idle()
        except Exception as e:
            logger.error(f"Error updating trend plot: {e}")
    
    def clear_data(self):
        """Clear all stored data"""
        self.values.clear()
        self.timestamps.clear()
        self.all_temperatures.clear()
        self.all_power.clear()
        self.counter = 0
        self.line.set_data([], [])
        self.setpoint_line.set_data([], [])
        self.line_power.set_data([], [])
        self.canvas.draw_idle()


class LevelTrendWindow(TrendGraphWindow):
    """Specialized window for level/volume trends with valve position subplots"""
    
    def __init__(self, parent=None, y_max=200):
        super().__init__(title="Level Trend", parent=parent, max_points=300, y_min=0, y_max=y_max)
        self.setWindowTitle("Level Trend (liters)")
        self.tank_volume_max = y_max
        
        # Store all data for history switching
        self.all_levels = deque(maxlen=10000)
        self.all_valve_in = deque(maxlen=10000)
        self.all_valve_out = deque(maxlen=10000)
        
        # Mode: 'live' for last 300 samples, 'history' for all samples from start
        self.view_mode = 'live'
        
        # Replace old single axis with subplots using GridSpec
        self.figure.clear()
        gs = GridSpec(2, 2, figure=self.figure, height_ratios=[1.5, 1.0], width_ratios=[1.0, 1.0])
        
        # Level subplot (top, full width, larger)
        self.ax = self.figure.add_subplot(gs[0, :])
        self.ax.set_facecolor('#2d2d2d')
        self.ax.grid(True, alpha=0.2, color='#3d3d3d')
        self.ax.set_ylabel('Level (liters)', color='#c9d1d9', fontsize=10)
        self.ax.tick_params(colors='#c9d1d9')
        self.line = self.ax.plot([], [], color='#51cf66', linewidth=2, label='Level (liters)')[0]
        self.ax.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='#3d3d3d', labelcolor='#c9d1d9')
        
        # Set level axis limits (0 to tank_volume_max + 10%)
        level_max_display = y_max * 1.1
        y_range = max(1, level_max_display - 0)
        y_padding = y_range * 0.2 + 20
        padded_y_max = level_max_display + y_padding
        self.ax.set_ylim([0, padded_y_max])
        
        # Valve In subplot (bottom left)
        self.ax_valve_in = self.figure.add_subplot(gs[1, 0])
        self.ax_valve_in.set_facecolor('#2d2d2d')
        self.ax_valve_in.grid(True, alpha=0.2, color='#3d3d3d')
        self.ax_valve_in.set_ylabel('Valve In (%)', color='#c9d1d9', fontsize=9)
        self.ax_valve_in.tick_params(colors='#c9d1d9')
        self.ax_valve_in.set_ylim([0, 110])
        self.line_valve_in, = self.ax_valve_in.plot([], [], color='#4ecdc4', linewidth=2, label='Valve In (%)')
        self.ax_valve_in.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='#3d3d3d', labelcolor='#c9d1d9')
        
        # Valve Out subplot (bottom right)
        self.ax_valve_out = self.figure.add_subplot(gs[1, 1])
        self.ax_valve_out.set_facecolor('#2d2d2d')
        self.ax_valve_out.grid(True, alpha=0.2, color='#3d3d3d')
        self.ax_valve_out.set_ylabel('Valve Out (%)', color='#c9d1d9', fontsize=9)
        self.ax_valve_out.tick_params(colors='#c9d1d9')
        self.ax_valve_out.set_ylim([0, 110])
        self.line_valve_out, = self.ax_valve_out.plot([], [], color='#f7b731', linewidth=2, label='Valve Out (%)')
        self.ax_valve_out.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='#3d3d3d', labelcolor='#c9d1d9')
        
        # Recreate canvas
        self.canvas = FigureCanvas(self.figure)
        
        # Setup toolbar (will be overridden in the layout setup below)
        self.setup_level_toolbar()
        
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
        self.update_timer.start(100)
    
    def setup_level_toolbar(self):
        """Setup toolbar for level trend with mode selection"""
        from PyQt5.QtWidgets import QComboBox, QLabel
        
        self.toolbar_layout = QHBoxLayout()
        
        # View Mode selector
        self.toolbar_layout.addWidget(QLabel("View Mode:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Live (Last 300)", "live")
        self.combo_mode.addItem("History (All)", "history")
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        self.toolbar_layout.addWidget(self.combo_mode)
        
        self.toolbar_layout.addSpacing(20)
        
        # Level limits
        self.toolbar_layout.addWidget(QLabel("L Min (L):"))
        self.spinbox_l_min = QSpinBox()
        self.spinbox_l_min.setMinimum(0)
        self.spinbox_l_min.setMaximum(10000)
        self.spinbox_l_min.setValue(0)
        self.spinbox_l_min.setMaximumWidth(80)
        self.spinbox_l_min.valueChanged.connect(self.on_level_limits_changed)
        self.toolbar_layout.addWidget(self.spinbox_l_min)
        
        self.toolbar_layout.addWidget(QLabel("L Max (L):"))
        self.spinbox_l_max = QSpinBox()
        self.spinbox_l_max.setMinimum(0)
        self.spinbox_l_max.setMaximum(10000)
        self.spinbox_l_max.setValue(int(self.tank_volume_max * 1.1))
        self.spinbox_l_max.setMaximumWidth(80)
        self.spinbox_l_max.valueChanged.connect(self.on_level_limits_changed)
        self.toolbar_layout.addWidget(self.spinbox_l_max)
        
        self.toolbar_layout.addSpacing(20)
        
        # Clear button
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setMaximumWidth(80)
        self.btn_clear.clicked.connect(self.clear_data)
        self.toolbar_layout.addWidget(self.btn_clear)
        
        # Stretch to fill remaining space
        self.toolbar_layout.addStretch()
    
    def on_mode_changed(self, index):
        """Handle view mode change"""
        self.view_mode = self.combo_mode.currentData()
        self.update_plot()
    
    def on_level_limits_changed(self):
        """Handle level limit changes"""
        l_min = self.spinbox_l_min.value()
        l_max = self.spinbox_l_max.value()
        
        if l_max > l_min:
            y_range = max(1, l_max - l_min)
            padding = y_range * 0.2 + 20
            padded_y_max = l_max + padding
            self.ax.set_ylim([l_min, padded_y_max])
            self.canvas.draw_idle()
    
    def add_value(self, level_value, valve_in_fraction=0.0, valve_out_fraction=0.0):
        """Add level and valve data point"""
        try:
            self.values.append(float(level_value))
            self.timestamps.append(self.counter)
            self.counter += 1
            
            # Store in full history
            self.all_levels.append(float(level_value))
            self.all_valve_in.append(float(valve_in_fraction) * 100.0)  # Convert to percentage
            self.all_valve_out.append(float(valve_out_fraction) * 100.0)
            
        except Exception as e:
            logger.error(f"Error adding trend value: {e}")
    
    def update_plot(self):
        """Update all three plots (level, valve in, valve out)"""
        try:
            if len(self.values) > 0:
                if self.view_mode == 'live':
                    # Show only last 300 samples
                    x_data = list(self.timestamps)
                    y_level = list(self.values)
                    num_samples = len(self.timestamps)
                    valve_in_data = list(self.all_valve_in)[-num_samples:] if len(self.all_valve_in) >= num_samples else list(self.all_valve_in)
                    valve_out_data = list(self.all_valve_out)[-num_samples:] if len(self.all_valve_out) >= num_samples else list(self.all_valve_out)
                else:  # history mode
                    # Show all samples from sample 0
                    x_data = list(range(len(self.all_levels)))
                    y_level = list(self.all_levels)
                    valve_in_data = list(self.all_valve_in)
                    valve_out_data = list(self.all_valve_out)
                
                # Update level line
                self.line.set_data(x_data, y_level)
                
                # Update valve lines
                if len(valve_in_data) > 0:
                    self.line_valve_in.set_data(x_data[-len(valve_in_data):], valve_in_data)
                if len(valve_out_data) > 0:
                    self.line_valve_out.set_data(x_data[-len(valve_out_data):], valve_out_data)
                
                # Adjust axes
                self.ax.relim()
                self.ax.autoscale_view()
                self.ax_valve_in.relim()
                self.ax_valve_in.autoscale_view()
                self.ax_valve_out.relim()
                self.ax_valve_out.autoscale_view()
                
                self.canvas.draw_idle()
        except Exception as e:
            logger.error(f"Error updating trend plot: {e}")
    
    def clear_data(self):
        """Clear all stored data"""
        self.values.clear()
        self.timestamps.clear()
        self.all_levels.clear()
        self.all_valve_in.clear()
        self.all_valve_out.clear()
        self.counter = 0
        self.line.set_data([], [])
        self.line_valve_in.set_data([], [])
        self.line_valve_out.set_data([], [])
        self.canvas.draw_idle()


class TrendGraphManager:
    """Manages multiple trend graph windows"""
    
    def __init__(self):
        self.temp_window = None
        self.level_window = None
        # Store configuration limits for trends
        self.tank_volume_max = 200.0  # Default, can be updated
        self.temp_max = 100.0  # Default, can be updated
        self.boiling_temp = 100.0  # Boiling temperature for temp window
    
    def set_config(self, tank_volume_max: float = None, temp_max: float = None, boiling_temp: float = None):
        """Update configuration limits for trend windows"""
        if tank_volume_max is not None:
            self.tank_volume_max = tank_volume_max
        if temp_max is not None:
            self.temp_max = temp_max
        if boiling_temp is not None:
            self.boiling_temp = boiling_temp
        
        # Update existing temperature window if open
        if self._is_window_valid(self.temp_window) and isinstance(self.temp_window, TemperatureTrendWindow):
            try:
                self.temp_window.boiling_temp = boiling_temp if boiling_temp is not None else self.boiling_temp
                # Update spinbox limits
                if hasattr(self.temp_window, 'spinbox_t_max'):
                    self.temp_window.spinbox_t_max.setMaximum(int(self.boiling_temp) + 20)
                    self.temp_window.spinbox_t_max.setValue(int(self.boiling_temp) + 10)
            except Exception:
                pass
    
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
                self.temp_window = TemperatureTrendWindow(parent, boiling_temp=self.boiling_temp)
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
                # Pass tank volume as Y-max
                self.level_window = LevelTrendWindow(parent, y_max=self.tank_volume_max)
                self.level_window.show()
            else:
                self.level_window.raise_()
                self.level_window.activateWindow()
            return self.level_window
        except Exception as e:
            logger.error(f"Error showing level trend: {e}")
            self.level_window = None
            return None
    
    def add_temperature(self, value, power_fraction=0.0):
        """Add temperature and power data to trend if window is open"""
        try:
            if self._is_window_valid(self.temp_window):
                self.temp_window.add_value(value, power_fraction)
        except RuntimeError:
            self.temp_window = None
    
    def set_temperature_setpoint(self, sp_value):
        """Set the setpoint value for temperature trend display"""
        try:
            if self._is_window_valid(self.temp_window) and isinstance(self.temp_window, TemperatureTrendWindow):
                self.temp_window.set_setpoint(sp_value)
        except RuntimeError:
            self.temp_window = None
    
    def add_level(self, value, valve_in_fraction=0.0, valve_out_fraction=0.0):
        """Add level and valve position data to trend if window is open"""
        try:
            if self._is_window_valid(self.level_window):
                if isinstance(self.level_window, LevelTrendWindow):
                    self.level_window.add_value(value, valve_in_fraction, valve_out_fraction)
                else:
                    # Fallback for basic TrendGraphWindow
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
