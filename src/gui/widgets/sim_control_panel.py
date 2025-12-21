"""
SimControlPanel - Standardized control panel for simulation pages

This widget provides a reusable control panel with start/stop/pause/reset buttons,
setpoint sliders, and status indicators for simulation pages.

Libraries used:
- PyQt5: GPL v3 License (https://www.riverbankcomputing.com/software/pyqt/)

Full license information available in LICENSE.txt
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QSlider, QGroupBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPalette


class SimControlPanel(QWidget):
    """
    Standardized control panel for simulation pages.
    
    Provides:
    - Start/Stop/Pause/Reset buttons with colored accents
    - Temperature and water flow setpoint sliders
    - LED-style status indicator
    - Automatic I/O integration support
    
    Signals:
        startClicked: Emitted when Start button is clicked
        stopClicked: Emitted when Stop button is clicked
        pauseClicked: Emitted when Pause button is clicked
        resetClicked: Emitted when Reset button is clicked
        temperatureChanged(int): Emitted when temperature setpoint changes
        waterFlowChanged(int): Emitted when water flow setpoint changes
    """
    
    # Signals
    startClicked = pyqtSignal()
    stopClicked = pyqtSignal()
    pauseClicked = pyqtSignal()
    resetClicked = pyqtSignal()
    temperatureChanged = pyqtSignal(int)
    waterFlowChanged = pyqtSignal(int)
    
    def __init__(self, parent=None, sim_name="Simulation"):
        """
        Initialize simulation control panel.
        
        Args:
            parent: Parent widget
            sim_name: Name of the simulation for ID generation
        """
        super().__init__(parent)
        self.sim_name = sim_name
        self._is_running = False
        self._is_paused = False
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Control buttons group
        control_group = QGroupBox("Simulation Controls")
        control_layout = QHBoxLayout()
        
        # Start button (green accent)
        self.start_btn = QPushButton("▶ Start")
        self.start_btn.setObjectName("startButton")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("""
            QPushButton#startButton {
                background-color: #4CAF50;
                color: white;
                font-weight: 600;
                border-radius: 4px;
            }
            QPushButton#startButton:hover {
                background-color: #45a049;
            }
            QPushButton#startButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#startButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        """)
        
        # Stop button (red accent)
        self.stop_btn = QPushButton("⬛ Stop")
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton#stopButton {
                background-color: #f44336;
                color: white;
                font-weight: 600;
                border-radius: 4px;
            }
            QPushButton#stopButton:hover {
                background-color: #da190b;
            }
            QPushButton#stopButton:pressed {
                background-color: #b71c1c;
            }
            QPushButton#stopButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        """)
        
        # Pause button (yellow accent)
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setObjectName("pauseButton")
        self.pause_btn.setMinimumHeight(40)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setCheckable(True)
        self.pause_btn.setStyleSheet("""
            QPushButton#pauseButton {
                background-color: #ff9800;
                color: white;
                font-weight: 600;
                border-radius: 4px;
            }
            QPushButton#pauseButton:hover {
                background-color: #fb8c00;
            }
            QPushButton#pauseButton:pressed {
                background-color: #f57c00;
            }
            QPushButton#pauseButton:checked {
                background-color: #e65100;
            }
            QPushButton#pauseButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        """)
        
        # Reset button (gray accent)
        self.reset_btn = QPushButton("↻ Reset")
        self.reset_btn.setObjectName("resetButton")
        self.reset_btn.setMinimumHeight(40)
        self.reset_btn.setStyleSheet("""
            QPushButton#resetButton {
                background-color: #757575;
                color: white;
                font-weight: 600;
                border-radius: 4px;
            }
            QPushButton#resetButton:hover {
                background-color: #616161;
            }
            QPushButton#resetButton:pressed {
                background-color: #424242;
            }
        """)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.reset_btn)
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Status indicator
        status_group = QGroupBox("Status")
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Stopped")
        self.status_indicator = QFrame()
        self.status_indicator.setFixedSize(20, 20)
        self.status_indicator.setStyleSheet("""
            background-color: #757575;
            border-radius: 10px;
            border: 2px solid #424242;
        """)
        
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Setpoint sliders group
        setpoint_group = QGroupBox("Setpoints")
        setpoint_layout = QVBoxLayout()
        
        # Temperature slider
        temp_layout = QHBoxLayout()
        temp_label = QLabel("Temperature:")
        temp_label.setMinimumWidth(100)
        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setMinimum(0)
        self.temp_slider.setMaximum(100)
        self.temp_slider.setValue(20)
        self.temp_slider.setTickPosition(QSlider.TicksBelow)
        self.temp_slider.setTickInterval(10)
        self.temp_value_label = QLabel("20°C")
        self.temp_value_label.setMinimumWidth(60)
        self.temp_value_label.setAlignment(Qt.AlignRight)
        
        temp_layout.addWidget(temp_label)
        temp_layout.addWidget(self.temp_slider)
        temp_layout.addWidget(self.temp_value_label)
        setpoint_layout.addLayout(temp_layout)
        
        # Water flow slider
        flow_layout = QHBoxLayout()
        flow_label = QLabel("Water Flow:")
        flow_label.setMinimumWidth(100)
        self.flow_slider = QSlider(Qt.Horizontal)
        self.flow_slider.setMinimum(0)
        self.flow_slider.setMaximum(100)
        self.flow_slider.setValue(50)
        self.flow_slider.setTickPosition(QSlider.TicksBelow)
        self.flow_slider.setTickInterval(10)
        self.flow_value_label = QLabel("50 L/min")
        self.flow_value_label.setMinimumWidth(60)
        self.flow_value_label.setAlignment(Qt.AlignRight)
        
        flow_layout.addWidget(flow_label)
        flow_layout.addWidget(self.flow_slider)
        flow_layout.addWidget(self.flow_value_label)
        setpoint_layout.addLayout(flow_layout)
        
        setpoint_group.setLayout(setpoint_layout)
        layout.addWidget(setpoint_group)
        
        layout.addStretch()
        
    def _connect_signals(self):
        """Connect internal signals."""
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)
        self.pause_btn.clicked.connect(self._on_pause)
        self.reset_btn.clicked.connect(self._on_reset)
        self.temp_slider.valueChanged.connect(self._on_temp_changed)
        self.flow_slider.valueChanged.connect(self._on_flow_changed)
        
    def _on_start(self):
        """Handle start button click."""
        self._is_running = True
        self._is_paused = False
        self._update_button_states()
        self._update_status_indicator("Running", "#4CAF50")
        self.startClicked.emit()
        
    def _on_stop(self):
        """Handle stop button click."""
        self._is_running = False
        self._is_paused = False
        self._update_button_states()
        self._update_status_indicator("Stopped", "#757575")
        self.stopClicked.emit()
        
    def _on_pause(self):
        """Handle pause button click."""
        self._is_paused = self.pause_btn.isChecked()
        if self._is_paused:
            self._update_status_indicator("Paused", "#ff9800")
        else:
            self._update_status_indicator("Running", "#4CAF50")
        self.pauseClicked.emit()
        
    def _on_reset(self):
        """Handle reset button click."""
        self.temp_slider.setValue(20)
        self.flow_slider.setValue(50)
        self.resetClicked.emit()
        
    def _on_temp_changed(self, value):
        """Handle temperature slider change."""
        self.temp_value_label.setText(f"{value}°C")
        self.temperatureChanged.emit(value)
        
    def _on_flow_changed(self, value):
        """Handle water flow slider change."""
        self.flow_value_label.setText(f"{value} L/min")
        self.waterFlowChanged.emit(value)
        
    def _update_button_states(self):
        """Update button enabled/disabled states."""
        self.start_btn.setEnabled(not self._is_running)
        self.stop_btn.setEnabled(self._is_running)
        self.pause_btn.setEnabled(self._is_running)
        
    def _update_status_indicator(self, text, color):
        """Update status indicator LED and text."""
        self.status_label.setText(text)
        self.status_indicator.setStyleSheet(f"""
            background-color: {color};
            border-radius: 10px;
            border: 2px solid {color};
        """)
        
    def set_running(self, running):
        """
        Set the running state externally.
        
        Args:
            running: True if simulation is running, False otherwise
        """
        self._is_running = running
        self._update_button_states()
        if running:
            self._update_status_indicator("Running", "#4CAF50")
        else:
            self._update_status_indicator("Stopped", "#757575")
            
    def get_io_config(self):
        """
        Get I/O configuration entries for this control panel.
        
        Returns:
            List of dicts with I/O configuration for each control
        """
        io_entries = [
            {
                "id": f"SIM_{self.sim_name}_Start_Button",
                "name": f"{self.sim_name} Start",
                "type": "Digital Output",
                "description": "Start simulation command"
            },
            {
                "id": f"SIM_{self.sim_name}_Stop_Button",
                "name": f"{self.sim_name} Stop",
                "type": "Digital Output",
                "description": "Stop simulation command"
            },
            {
                "id": f"SIM_{self.sim_name}_Pause_Button",
                "name": f"{self.sim_name} Pause",
                "type": "Digital Output",
                "description": "Pause simulation command"
            },
            {
                "id": f"SIM_{self.sim_name}_Reset_Button",
                "name": f"{self.sim_name} Reset",
                "type": "Digital Output",
                "description": "Reset simulation command"
            },
            {
                "id": f"SIM_{self.sim_name}_Temperature_Setpoint",
                "name": f"{self.sim_name} Temp Setpoint",
                "type": "Analog Output",
                "description": "Temperature setpoint (0-100°C)",
                "units": "°C",
                "scaling": "0-100"
            },
            {
                "id": f"SIM_{self.sim_name}_WaterFlow_Setpoint",
                "name": f"{self.sim_name} Flow Setpoint",
                "type": "Analog Output",
                "description": "Water flow setpoint (0-100 L/min)",
                "units": "L/min",
                "scaling": "0-100"
            },
            {
                "id": f"SIM_{self.sim_name}_Status_Indicator",
                "name": f"{self.sim_name} Status",
                "type": "Digital Input",
                "description": "Simulation run status"
            }
        ]
        return io_entries
