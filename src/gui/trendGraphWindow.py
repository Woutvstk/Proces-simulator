"""
Trend Graph Window - Displays real-time simulation trends in floating windows.

Provides temperature and level trend visualization with:
- Live mode (last 300 samples)
- History mode (all samples from start)
- Subplot displays for related metrics (heating power, valve positions)
- Configurable Y-axis limits and data clearing

External Libraries Used:
- PyQt5 (GPL v3) - GUI framework for window management and widgets
- matplotlib (PSF License) - Plotting library for real-time trend graphs
"""

from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSpinBox, QPushButton, QComboBox, QFileDialog
from PyQt5.QtCore import Qt, QTimer, QSize, QPoint
from PyQt5.QtGui import QIcon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from collections import deque
import logging
from datetime import datetime

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

        # Scroll state
        self.scroll_offset = 0  # Offset to scroll back in time

        # Pause state
        self.is_paused = False
        self.y_min = y_min
        self.y_max = y_max

        # Mouse coordinate tracking
        self.mouse_x = None
        self.mouse_y = None
        self.mouse_label = None

        # Create matplotlib figure
        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.figure.patch.set_facecolor('white')
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('white')
        self.ax.grid(True, alpha=0.3, color='#cccccc')

        # Labels
        self.ax.set_xlabel('Time', color='black', fontsize=10)
        self.ax.set_ylabel('Value', color='black', fontsize=10)
        self.ax.tick_params(colors='black')

        # Line
        self.line, = self.ax.plot(
            [], [], color='#0066cc', linewidth=2, label='Live Data')
        self.ax.legend(loc='upper left', facecolor='white', edgecolor='#cccccc',
                       labelcolor='black')

        # Calculate padded Y-max: 20% of range + 20 units
        # This provides automatic headroom for realistic visualization
        y_range = max(1, self.y_max - self.y_min)
        self.y_padding = y_range * 0.2 + 20
        padded_y_max = self.y_max + self.y_padding

        self.ax.set_ylim([self.y_min, padded_y_max])

        # Create canvas
        self.canvas = FigureCanvas(self.figure)

        # Connect mouse motion event
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

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

        # Left arrow button (scroll back)
        self.btn_scroll_left = QPushButton("◀")
        self.btn_scroll_left.setMaximumWidth(50)
        self.btn_scroll_left.clicked.connect(self.on_scroll_left)
        self.toolbar_layout.addWidget(self.btn_scroll_left)

        # Right arrow button (scroll forward)
        self.btn_scroll_right = QPushButton("▶")
        self.btn_scroll_right.setMaximumWidth(50)
        self.btn_scroll_right.clicked.connect(self.on_scroll_right)
        self.toolbar_layout.addWidget(self.btn_scroll_right)

        # Save button
        self.btn_save = QPushButton("💾 Save PNG")
        self.btn_save.setMaximumWidth(100)
        self.btn_save.clicked.connect(self.on_save_png)
        self.toolbar_layout.addWidget(self.btn_save)

        # Pause button
        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setMaximumWidth(100)
        self.btn_pause.clicked.connect(self.on_pause_toggle)
        self.toolbar_layout.addWidget(self.btn_pause)

        self.toolbar_layout.addSpacing(20)

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

        # Mouse coordinates display
        self.label_mouse = QLabel("X: -- Y: --")
        self.label_mouse.setStyleSheet("color: black;")
        self.toolbar_layout.addWidget(self.label_mouse)

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

    def on_scroll_left(self):
        """Scroll trends to the left (view older data)"""
        if len(self.timestamps) > 0:
            self.scroll_offset = min(
                self.scroll_offset + 10, len(self.timestamps) - 1)
            self.update_plot()

    def on_scroll_right(self):
        """Scroll trends to the right (view newer data)"""
        self.scroll_offset = max(self.scroll_offset - 10, 0)
        self.update_plot()

    def on_mouse_move(self, event):
        """Handle mouse movement on the plot - show nearest data point value"""
        if event.inaxes == self.ax and len(self.values) > 0:
            self.mouse_x = event.xdata
            self.mouse_y = event.ydata

            if self.mouse_x is not None:
                # Find nearest data point
                timestamps_list = list(self.timestamps)
                if len(timestamps_list) > 0:
                    # Find index of nearest x coordinate
                    nearest_idx = min(range(len(timestamps_list)),
                                      key=lambda i: abs(timestamps_list[i] - self.mouse_x))

                    # Get the actual data value at that point
                    values_list = list(self.values)
                    actual_value = values_list[nearest_idx]
                    actual_x = timestamps_list[nearest_idx]

                    self.label_mouse.setText(
                        f"X: {actual_x:.0f} Y: {actual_value:.2f}")
                else:
                    self.label_mouse.setText("X: -- Y: --")
            else:
                self.label_mouse.setText("X: -- Y: --")
        else:
            self.label_mouse.setText("X: -- Y: --")

    def on_save_png(self):
        """Save the trend graph as PNG file with file dialog"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            window_title = self.windowTitle().replace(" ", "_")
            filename = f"trend_{window_title}_{timestamp}.png"

            # Open file dialog
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Trend Graph",
                filename,
                "PNG Images (*.png);;All Files (*)"
            )

            if save_path:  # Only save if user didn't cancel
                self.figure.savefig(
                    save_path, facecolor='#1a1a1a', dpi=150, bbox_inches='tight')
                logger.info(f"Trend saved to: {save_path}")

                # Show save notification in label
                import os
                short_name = os.path.basename(save_path)
                self.label_mouse.setText(f"Saved: {short_name}")

                # Reset label after 3 seconds
                QTimer.singleShot(3000, lambda: self.label_mouse.setText(
                    "X: -- Y: --") if self.mouse_x is None else None)
        except Exception as e:
            logger.error(f"Error saving trend PNG: {e}")
            self.label_mouse.setText("Save failed!")
            QTimer.singleShot(3000, lambda: self.label_mouse.setText(
                "X: -- Y: --") if self.mouse_x is None else None)

    def on_pause_toggle(self):
        """Toggle pause/resume state"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.setText("▶ Resume")
        else:
            self.btn_pause.setText("⏸ Pause")
        self.update_plot()

    def on_samples_changed(self, value):
        """Handle live mode time window change (in seconds)"""
        # Convert seconds to samples (10Hz = 10 samples per second)
        self.max_points = int(value * 10)
        # Update combo box text (only if it exists)
        if hasattr(self, 'combo_mode') and self.combo_mode is not None:
            self.combo_mode.setItemText(0, f"Live (Last {value:.1f}s)")
        self.update_plot()

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
        """Add a new data point to the trend (only if not paused)"""
        try:
            if not self.is_paused:
                self.values.append(float(value))
                self.timestamps.append(self.counter)
                self.counter += 1
        except Exception as e:
            logger.error(f"Error adding trend value: {e}")

    def update_plot(self):
        """Update the plot with current data"""
        try:
            timestamps_list = list(self.timestamps)
            values_list = list(self.values)

            if len(values_list) > 0:
                # Apply scroll offset
                if self.scroll_offset > 0:
                    start_idx = max(
                        0, len(timestamps_list) - self.max_points - self.scroll_offset)
                    end_idx = len(timestamps_list) - self.scroll_offset
                    end_idx = max(start_idx + 1, end_idx)
                else:
                    start_idx = max(0, len(timestamps_list) - self.max_points)
                    end_idx = len(timestamps_list)

                visible_timestamps = timestamps_list[start_idx:end_idx]
                visible_values = values_list[start_idx:end_idx]

                self.line.set_data(visible_timestamps, visible_values)

                # Update X-axis limits
                if len(visible_timestamps) > 0:
                    self.ax.set_xlim(
                        [min(visible_timestamps), max(visible_timestamps) + 1])

                    # Update Y-axis limits but keep the user-set min/max
                    y_range = max(1, self.y_max - self.y_min)
                    padding = y_range * 0.2 + 20
                    padded_y_max = self.y_max + padding
                    self.ax.set_ylim([self.y_min, padded_y_max])
            else:
                # Clear plot if no data
                self.line.set_data([], [])

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
        super().__init__(title="Temperature Trend", parent=parent,
                         max_points=300, y_min=0, y_max=boiling_temp+10)
        self.setWindowTitle("Temperature Trend (°C)")
        self.boiling_temp = boiling_temp

        # Store all temperature and power data for history switching
        self.all_temperatures = deque(maxlen=10000)  # Store full history
        self.all_power = deque(maxlen=10000)
        self.all_setpoints = deque(maxlen=10000)  # Store setpoint history
        self.sample_counter = 0

        # Mode: 'live' for last 300 samples, 'history' for all samples from start
        self.view_mode = 'live'  # Default to live mode

        # Setpoint tracking
        self.setpoint_value = 50.0
        self.setpoint_line = None

        # Replace old single axis with subplots
        self.figure.clear()
        self.figure.patch.set_facecolor('white')

        # Create GridSpec with height ratios (temperature 30% larger than power)
        gs = GridSpec(2, 1, figure=self.figure, height_ratios=[1.3, 1.0])

        # Temperature subplot (top, 56% of height)
        self.ax = self.figure.add_subplot(gs[0])
        self.ax.set_facecolor('white')
        self.ax.grid(True, alpha=0.3, color='#cccccc')
        self.ax.set_ylabel('Temperature (°C)', color='black', fontsize=10)
        self.ax.tick_params(colors='black')

        # Temperature line
        self.line, = self.ax.plot(
            [], [], color='#d9534f', linewidth=2, label='Temperature (°C)')

        # Setpoint line (horizontal)
        self.setpoint_line, = self.ax.plot(
            [], [], color='#f0ad4e', linewidth=2, linestyle='--', label='Setpoint')

        # Power subplot (bottom, 44% of height)
        self.ax_power = self.figure.add_subplot(gs[1])
        self.ax_power.set_facecolor('white')
        self.ax_power.grid(True, alpha=0.3, color='#cccccc')
        self.ax_power.set_xlabel('Time', color='black', fontsize=10)
        self.ax_power.set_ylabel(
            'Heating Power (%)', color='black', fontsize=10)
        self.ax_power.tick_params(colors='black')
        self.ax_power.set_ylim([0, 110])

        # Power line
        self.line_power, = self.ax_power.plot(
            [], [], color='#e67e22', linewidth=2, label='Heating Power (%)')

        # Legends
        self.ax.legend(loc='upper left', facecolor='white',
                       edgecolor='#cccccc', labelcolor='black')
        self.ax_power.legend(loc='upper left', facecolor='white',
                             edgecolor='#cccccc', labelcolor='black')

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

        # Left arrow button (scroll back)
        self.btn_scroll_left = QPushButton("◀")
        self.btn_scroll_left.setMaximumWidth(50)
        self.btn_scroll_left.clicked.connect(self.on_scroll_left)
        self.toolbar_layout.addWidget(self.btn_scroll_left)

        # Right arrow button (scroll forward)
        self.btn_scroll_right = QPushButton("▶")
        self.btn_scroll_right.setMaximumWidth(50)
        self.btn_scroll_right.clicked.connect(self.on_scroll_right)
        self.toolbar_layout.addWidget(self.btn_scroll_right)

        # Save button
        self.btn_save = QPushButton("💾 Save PNG")
        self.btn_save.setMaximumWidth(100)
        self.btn_save.clicked.connect(self.on_save_png)
        self.toolbar_layout.addWidget(self.btn_save)

        # Pause button
        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setMaximumWidth(100)
        self.btn_pause.clicked.connect(self.on_pause_toggle)
        self.toolbar_layout.addWidget(self.btn_pause)

        self.toolbar_layout.addSpacing(20)

        # View Mode selector
        self.toolbar_layout.addWidget(QLabel("View Mode:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Live (Last 30.0s)", "live")
        self.combo_mode.addItem("History (All)", "history")
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        self.toolbar_layout.addWidget(self.combo_mode)

        # Live mode samples control (now in seconds)
        self.toolbar_layout.addWidget(QLabel("Seconds:"))
        self.spinbox_samples = QSpinBox()
        self.spinbox_samples.setMinimum(1)
        self.spinbox_samples.setMaximum(100)
        self.spinbox_samples.setValue(30)
        self.spinbox_samples.setMaximumWidth(80)
        self.spinbox_samples.setSuffix(" s")
        self.spinbox_samples.valueChanged.connect(self.on_samples_changed)
        self.toolbar_layout.addWidget(self.spinbox_samples)

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

        # Mouse coordinates display
        self.label_mouse = QLabel("X: -- Y: --")
        self.label_mouse.setStyleSheet("color: black;")
        self.toolbar_layout.addWidget(self.label_mouse)

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

    def on_mouse_move(self, event):
        """Handle mouse movement - show time and Y value at mouse position"""
        if len(self.all_temperatures) == 0:
            self.label_mouse.setText("Time: -- Y: --")
            return

        # Check if mouse is on any of the subplots
        if event.inaxes not in [self.ax, self.ax_power]:
            self.label_mouse.setText("Time: -- Y: --")
            return

        self.mouse_x = event.xdata
        self.mouse_y = event.ydata

        if self.mouse_x is None or self.mouse_y is None:
            self.label_mouse.setText("Time: -- Y: --")
            return

        if self.view_mode == 'live':
            timestamps = list(self.timestamps)
        else:
            timestamps = list(range(len(self.all_temperatures)))

        if len(timestamps) > 0:
            # Mouse x is already in seconds (converted in update_plot)
            time_sec = self.mouse_x
            y_value = self.mouse_y

            # Format based on which subplot
            if event.inaxes == self.ax:
                # Temperature subplot
                self.label_mouse.setText(
                    f"Time: {time_sec:.2f}s  Y: {y_value:.2f}°C")
            else:
                # Power subplot
                self.label_mouse.setText(
                    f"Time: {time_sec:.2f}s  Y: {y_value:.2f}%")
        else:
            self.label_mouse.setText("Time: -- Y: -- T: -- P: --")

    def add_value(self, value, power_fraction=0.0, setpoint=None):
        """Add temperature, power, and setpoint data point (only if not paused)"""
        try:
            if not self.is_paused:
                self.values.append(float(value))
                self.timestamps.append(self.counter)
                self.counter += 1

                # Store in full history (always store)
                self.all_temperatures.append(float(value))
                # Store power percentage (already in % from data source)
                self.all_power.append(float(power_fraction))
                # Store setpoint (use current value if not provided)
                sp = float(
                    setpoint) if setpoint is not None else self.setpoint_value
                self.all_setpoints.append(sp)

        except Exception as e:
            logger.error(f"Error adding trend value: {e}")

    def set_setpoint(self, sp_value):
        """Update the setpoint value for display"""
        self.setpoint_value = float(sp_value)

    def update_plot(self):
        """Update both temperature and power plots"""
        try:
            # Check if we have temperature data (in history mode use all_temperatures)
            has_temp_data = len(self.all_temperatures) > 0

            if has_temp_data:
                if self.view_mode == 'live':
                    # Show only last 300 samples
                    x_data = list(self.timestamps)
                    y_temp = list(self.values)
                    # Use same x-axis length for power and setpoint
                    num_samples = len(self.timestamps)
                    power_data = list(self.all_power)[-num_samples:] if len(
                        self.all_power) >= num_samples else list(self.all_power)
                    setpoint_data = list(self.all_setpoints)[-num_samples:] if len(
                        self.all_setpoints) >= num_samples else list(self.all_setpoints)
                else:  # history mode
                    # Show all samples from sample 0
                    x_data = list(range(len(self.all_temperatures)))
                    y_temp = list(self.all_temperatures)
                    power_data = list(self.all_power)
                    setpoint_data = list(self.all_setpoints)

                # Apply scroll offset
                if self.scroll_offset > 0:
                    start_idx = max(
                        0, len(x_data) - self.max_points - self.scroll_offset)
                    end_idx = len(x_data) - self.scroll_offset
                    end_idx = max(start_idx + 1, end_idx)
                else:
                    start_idx = max(0, len(x_data) - self.max_points)
                    end_idx = len(x_data)

                x_data = x_data[start_idx:end_idx]
                y_temp = y_temp[start_idx:end_idx]
                power_data = power_data[start_idx:end_idx] if power_data else [
                ]
                setpoint_data = setpoint_data[start_idx:end_idx] if setpoint_data else [
                ]

                # Convert x_data from samples to seconds (10Hz)
                x_data = [x / 10.0 for x in x_data]

                # Update temperature line
                self.line.set_data(x_data, y_temp)

                # Update setpoint line (as trend line, not horizontal)
                if len(setpoint_data) > 0 and len(x_data) > 0:
                    self.setpoint_line.set_data(x_data, setpoint_data)

                # Update X-axis limits
                if len(x_data) > 0:
                    self.ax.set_xlim([min(x_data), max(x_data) + 1])

                # Update power line
                if len(power_data) > 0:
                    self.line_power.set_data(x_data, power_data)
                    # Set x-axis limits for power subplot
                    self.ax_power.set_xlim([min(x_data), max(x_data) + 1])

                # Keep temperature Y-axis limits
                t_min = self.spinbox_t_min.value() if hasattr(self, 'spinbox_t_min') else 0
                t_max = self.spinbox_t_max.value() if hasattr(
                    self, 'spinbox_t_max') else self.boiling_temp + 10
                y_range = max(1, t_max - t_min)
                padding = y_range * 0.2 + 20
                padded_y_max = t_max + padding
                self.ax.set_ylim([t_min, padded_y_max])

                self.ax_power.set_ylim([0, 110])
            else:
                # Clear plot if no data
                self.line.set_data([], [])
                self.setpoint_line.set_data([], [])
                self.line_power.set_data([], [])

            self.canvas.draw_idle()
        except Exception as e:
            logger.error(f"Error updating trend plot: {e}")

    def clear_data(self):
        """Clear all stored data"""
        self.values.clear()
        self.timestamps.clear()
        self.all_temperatures.clear()
        self.all_power.clear()
        self.all_setpoints.clear()
        self.counter = 0
        self.line.set_data([], [])
        self.setpoint_line.set_data([], [])
        self.line_power.set_data([], [])
        self.canvas.draw_idle()


class LevelTrendWindow(TrendGraphWindow):
    """Specialized window for level/volume trends with valve position subplots"""

    def __init__(self, parent=None, y_max=100):
        super().__init__(title="Level Trend", parent=parent,
                         max_points=300, y_min=0, y_max=200)  # 200 liters max
        self.setWindowTitle("Level Trend (liters)")
        self.tank_volume_max = y_max  # Store tank volume in liters

        # Store all data for history switching
        self.all_levels = deque(maxlen=10000)
        self.all_valve_in = deque(maxlen=10000)
        self.all_valve_out = deque(maxlen=10000)
        self.all_setpoints = deque(maxlen=10000)  # Store setpoint history

        # Mode: 'live' for last 300 samples, 'history' for all samples from start
        self.view_mode = 'live'

        # Setpoint tracking
        self.setpoint_value = 100.0
        self.setpoint_line = None

        # Replace old single axis with subplots using GridSpec
        self.figure.clear()
        self.figure.patch.set_facecolor('white')
        gs = GridSpec(2, 2, figure=self.figure, height_ratios=[
                      1.5, 1.0], width_ratios=[1.0, 1.0])

        # Level subplot (top, full width, larger)
        self.ax = self.figure.add_subplot(gs[0, :])
        self.ax.set_facecolor('white')
        self.ax.grid(True, alpha=0.3, color='#cccccc')
        self.ax.set_ylabel('Level (%)', color='black', fontsize=10)
        self.ax.tick_params(colors='black')
        self.line = self.ax.plot(
            [], [], color='#27ae60', linewidth=2, label='Level (%)')[0]
        # Setpoint line
        self.setpoint_line, = self.ax.plot(
            [], [], color='#f0ad4e', linewidth=2, linestyle='--', label='Setpoint (%)')
        self.ax.legend(loc='upper left', facecolor='white',
                       edgecolor='#cccccc', labelcolor='black')

        # Set level axis limits (0 to 110%)
        level_max_display = 110
        self.ax.set_ylim([0, level_max_display])

        # Valve In subplot (bottom left)
        self.ax_valve_in = self.figure.add_subplot(gs[1, 0])
        self.ax_valve_in.set_facecolor('white')
        self.ax_valve_in.grid(True, alpha=0.3, color='#cccccc')
        self.ax_valve_in.set_ylabel(
            'Valve In (%)', color='black', fontsize=9)
        self.ax_valve_in.tick_params(colors='black')
        self.ax_valve_in.set_ylim([0, 110])
        self.line_valve_in, = self.ax_valve_in.plot(
            [], [], color='#3498db', linewidth=2, label='Valve In (%)')
        self.ax_valve_in.legend(
            loc='upper left', facecolor='white', edgecolor='#cccccc', labelcolor='black')

        # Valve Out subplot (bottom right)
        self.ax_valve_out = self.figure.add_subplot(gs[1, 1])
        self.ax_valve_out.set_facecolor('white')
        self.ax_valve_out.grid(True, alpha=0.3, color='#cccccc')
        self.ax_valve_out.set_ylabel(
            'Valve Out (%)', color='black', fontsize=9)
        self.ax_valve_out.tick_params(colors='black')
        self.ax_valve_out.set_ylim([0, 110])
        self.line_valve_out, = self.ax_valve_out.plot(
            [], [], color='#e74c3c', linewidth=2, label='Valve Out (%)')
        self.ax_valve_out.legend(
            loc='upper left', facecolor='white', edgecolor='#cccccc', labelcolor='black')

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

        # Left arrow button (scroll back)
        self.btn_scroll_left = QPushButton("◀")
        self.btn_scroll_left.setMaximumWidth(50)
        self.btn_scroll_left.clicked.connect(self.on_scroll_left)
        self.toolbar_layout.addWidget(self.btn_scroll_left)

        # Right arrow button (scroll forward)
        self.btn_scroll_right = QPushButton("▶")
        self.btn_scroll_right.setMaximumWidth(50)
        self.btn_scroll_right.clicked.connect(self.on_scroll_right)
        self.toolbar_layout.addWidget(self.btn_scroll_right)

        # Save button
        self.btn_save = QPushButton("💾 Save PNG")
        self.btn_save.setMaximumWidth(100)
        self.btn_save.clicked.connect(self.on_save_png)
        self.toolbar_layout.addWidget(self.btn_save)

        # Pause button
        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setMaximumWidth(100)
        self.btn_pause.clicked.connect(self.on_pause_toggle)
        self.toolbar_layout.addWidget(self.btn_pause)

        self.toolbar_layout.addSpacing(20)

        # View Mode selector
        self.toolbar_layout.addWidget(QLabel("View Mode:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Live (Last 30.0s)", "live")
        self.combo_mode.addItem("History (All)", "history")
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        self.toolbar_layout.addWidget(self.combo_mode)

        # Live mode samples control (now in seconds)
        self.toolbar_layout.addWidget(QLabel("Seconds:"))
        self.spinbox_samples = QSpinBox()
        self.spinbox_samples.setMinimum(1)
        self.spinbox_samples.setMaximum(100)
        self.spinbox_samples.setValue(30)
        self.spinbox_samples.setMaximumWidth(80)
        self.spinbox_samples.setSuffix(" s")
        self.spinbox_samples.valueChanged.connect(self.on_samples_changed)
        self.toolbar_layout.addWidget(self.spinbox_samples)

        self.toolbar_layout.addSpacing(20)

        # Level limits (in percent)
        self.toolbar_layout.addWidget(QLabel("L Min (%):"))
        self.spinbox_l_min = QSpinBox()
        self.spinbox_l_min.setMinimum(0)
        self.spinbox_l_min.setMaximum(110)
        self.spinbox_l_min.setValue(0)
        self.spinbox_l_min.setMaximumWidth(80)
        self.spinbox_l_min.valueChanged.connect(self.on_level_limits_changed)
        self.toolbar_layout.addWidget(self.spinbox_l_min)

        self.toolbar_layout.addWidget(QLabel("L Max (%):"))
        self.spinbox_l_max = QSpinBox()
        self.spinbox_l_max.setMinimum(0)
        self.spinbox_l_max.setMaximum(110)
        self.spinbox_l_max.setValue(110)
        self.spinbox_l_max.setMaximumWidth(80)
        self.spinbox_l_max.valueChanged.connect(self.on_level_limits_changed)
        self.toolbar_layout.addWidget(self.spinbox_l_max)

        self.toolbar_layout.addSpacing(20)

        # Clear button
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setMaximumWidth(80)
        self.btn_clear.clicked.connect(self.clear_data)
        self.toolbar_layout.addWidget(self.btn_clear)

        # Mouse coordinates display
        self.label_mouse = QLabel("X: -- Y: --")
        self.label_mouse.setStyleSheet("color: black;")
        self.toolbar_layout.addWidget(self.label_mouse)

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
            self.ax.set_ylim([l_min, l_max])
            self.canvas.draw_idle()

    def on_mouse_move(self, event):
        """Handle mouse movement - show time and Y value at mouse position"""
        if len(self.all_levels) == 0:
            self.label_mouse.setText("Time: -- Y: --")
            return

        # Check if mouse is on any of the subplots
        if event.inaxes not in [self.ax, self.ax_valve_in, self.ax_valve_out]:
            self.label_mouse.setText("Time: -- Y: --")
            return

        self.mouse_x = event.xdata
        self.mouse_y = event.ydata

        if self.mouse_x is None or self.mouse_y is None:
            self.label_mouse.setText("Time: -- Y: --")
            return

        if self.view_mode == 'live':
            timestamps = list(self.timestamps)
        else:
            timestamps = list(range(len(self.all_levels)))

        if len(timestamps) > 0:
            # Mouse x is already in seconds (converted in update_plot)
            time_sec = self.mouse_x
            y_value = self.mouse_y

            # Format based on which subplot
            if event.inaxes == self.ax:
                # Level subplot - show as percentage
                self.label_mouse.setText(
                    f"Time: {time_sec:.2f}s  Y: {y_value:.1f}%")
            else:
                # Valve subplots - show as percentage
                self.label_mouse.setText(
                    f"Time: {time_sec:.2f}s  Y: {y_value:.1f}%")

    def add_value(self, level_value, setpoint_value=0.0, valve_in_fraction=0.0, valve_out_fraction=0.0):
        """Add level, setpoint, and valve data point (only if not paused)"""
        try:
            if not self.is_paused:
                self.values.append(float(level_value))
                self.timestamps.append(self.counter)
                self.counter += 1

                # Store in full history (always store)
                self.all_levels.append(float(level_value))
                # Store valve percentages (already in % from data source)
                self.all_valve_in.append(float(valve_in_fraction))
                self.all_valve_out.append(float(valve_out_fraction))
                # Store setpoint history
                self.all_setpoints.append(float(setpoint_value))

        except Exception as e:
            logger.error(f"Error adding trend value: {e}")

    def set_setpoint(self, sp_value):
        """Update the setpoint value for display"""
        self.setpoint_value = float(sp_value)

    def update_plot(self):
        """Update all three plots (level, valve in, valve out)"""
        try:
            # Check if we have level data (in history mode use all_levels)
            has_level_data = len(self.all_levels) > 0

            if has_level_data:
                if self.view_mode == 'live':
                    # Show only last 300 samples
                    x_data = list(self.timestamps)
                    y_level = list(self.values)
                    num_samples = len(self.timestamps)
                    valve_in_data = list(self.all_valve_in)[-num_samples:] if len(
                        self.all_valve_in) >= num_samples else list(self.all_valve_in)
                    valve_out_data = list(self.all_valve_out)[-num_samples:] if len(
                        self.all_valve_out) >= num_samples else list(self.all_valve_out)
                    setpoint_data = list(self.all_setpoints)[-num_samples:] if len(
                        self.all_setpoints) >= num_samples else list(self.all_setpoints)
                else:  # history mode
                    # Show all samples from sample 0
                    x_data = list(range(len(self.all_levels)))
                    y_level = list(self.all_levels)
                    valve_in_data = list(self.all_valve_in)
                    valve_out_data = list(self.all_valve_out)
                    setpoint_data = list(self.all_setpoints)

                # Level is already in percentage - no conversion needed

                # Apply scroll offset
                if self.scroll_offset > 0:
                    start_idx = max(
                        0, len(x_data) - self.max_points - self.scroll_offset)
                    end_idx = len(x_data) - self.scroll_offset
                    end_idx = max(start_idx + 1, end_idx)
                else:
                    start_idx = max(0, len(x_data) - self.max_points)
                    end_idx = len(x_data)

                x_data = x_data[start_idx:end_idx]
                y_level = y_level[start_idx:end_idx]
                valve_in_data = valve_in_data[start_idx:end_idx] if valve_in_data else [
                ]
                valve_out_data = valve_out_data[start_idx:end_idx] if valve_out_data else [
                ]
                setpoint_data = setpoint_data[start_idx:end_idx] if setpoint_data else [
                ]

                # Convert x_data from samples to seconds (10Hz)
                x_data = [x / 10.0 for x in x_data]

                # Update level line
                self.line.set_data(x_data, y_level)

                # Update setpoint line (as trend line, not horizontal)
                if len(setpoint_data) > 0 and len(x_data) > 0:
                    self.setpoint_line.set_data(x_data, setpoint_data)

                # Update valve lines
                if len(valve_in_data) > 0:
                    self.line_valve_in.set_data(x_data, valve_in_data)
                if len(valve_out_data) > 0:
                    self.line_valve_out.set_data(x_data, valve_out_data)

                # Adjust axes with proper limits
                if len(x_data) > 0:
                    self.ax.set_xlim([min(x_data), max(x_data) + 1])
                    self.ax_valve_in.set_xlim([min(x_data), max(x_data) + 1])
                    self.ax_valve_out.set_xlim([min(x_data), max(x_data) + 1])

                # Keep level Y-axis limits (in percent)
                l_min = self.spinbox_l_min.value() if hasattr(self, 'spinbox_l_min') else 0
                l_max = self.spinbox_l_max.value() if hasattr(self, 'spinbox_l_max') else 110
                self.ax.set_ylim([l_min, l_max])

                self.ax_valve_in.set_ylim([0, 110])
                self.ax_valve_out.set_ylim([0, 110])
            else:
                # Clear plot if no data
                self.line.set_data([], [])
                self.setpoint_line.set_data([], [])
                self.line_valve_in.set_data([], [])
                self.line_valve_out.set_data([], [])

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
        self.all_setpoints.clear()
        self.counter = 0
        self.line.set_data([], [])
        self.setpoint_line.set_data([], [])
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
                    self.temp_window.spinbox_t_max.setMaximum(
                        int(self.boiling_temp) + 20)
                    self.temp_window.spinbox_t_max.setValue(
                        int(self.boiling_temp) + 10)
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
                self.temp_window = TemperatureTrendWindow(
                    parent, boiling_temp=self.boiling_temp)
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
                self.level_window = LevelTrendWindow(
                    parent, y_max=self.tank_volume_max)
                self.level_window.show()
            else:
                self.level_window.raise_()
                self.level_window.activateWindow()
            return self.level_window
        except Exception as e:
            logger.error(f"Error showing level trend: {e}")
            self.level_window = None
            return None

    def add_temperature(self, pv_value=None, setpoint_value=None, output_value=None, value=None, power_fraction=0.0):
        """Add temperature and power data to trend if window is open

        Supports both old-style (value, power_fraction) and new-style (pv_value, setpoint_value, output_value) parameters
        """
        try:
            if self._is_window_valid(self.temp_window):
                # Use new-style parameters if provided, otherwise fall back to old-style
                if pv_value is not None:
                    self.temp_window.add_value(
                        pv_value,
                        output_value if output_value is not None else 0.0,
                        setpoint_value if setpoint_value is not None else None)
                elif value is not None:
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

    def set_level_setpoint(self, sp_value):
        """Set the setpoint value for level trend display"""
        try:
            if self._is_window_valid(self.level_window) and isinstance(self.level_window, LevelTrendWindow):
                self.level_window.set_setpoint(sp_value)
        except RuntimeError:
            self.level_window = None

    def add_level(self, pv_value=None, setpoint_value=None, valve_in_fraction=0.0, valve_out_fraction=0.0, value=None):
        """Add level, setpoint, and valve position data to trend if window is open

        Parameters:
        - pv_value: Process value (level in %)
        - setpoint_value: Setpoint value (level setpoint in %)
        - valve_in_fraction: Inlet valve position (%)
        - valve_out_fraction: Outlet valve position (%)
        - value: Legacy parameter for backward compatibility
        """
        try:
            if self._is_window_valid(self.level_window):
                if isinstance(self.level_window, LevelTrendWindow):
                    # Use new-style parameters if provided, otherwise fall back to old-style
                    if pv_value is not None:
                        self.level_window.add_value(
                            pv_value,
                            setpoint_value if setpoint_value is not None else 0.0,
                            valve_in_fraction,
                            valve_out_fraction)
                    elif value is not None:
                        self.level_window.add_value(
                            value, 0.0, valve_in_fraction, valve_out_fraction)
                else:
                    # Fallback for basic TrendGraphWindow
                    if pv_value is not None:
                        self.level_window.add_value(pv_value)
                    elif value is not None:
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
