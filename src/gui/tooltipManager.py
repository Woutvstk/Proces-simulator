# tooltipManager.py - Manage dynamic tooltips for the GUI

from PyQt5.QtWidgets import QPushButton, QLineEdit, QComboBox
from PyQt5.QtCore import Qt

class TooltipManager:
    """
    Manages dynamic tooltips that change based on application state.
    """
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.initial_tooltips = {}
        self._setup_dynamic_tooltips()
    
    def _setup_dynamic_tooltips(self):
        """Initialize dynamic tooltip handlers."""
        # Connect state change signals
        try:
            if hasattr(self.main_window, 'controlerDropDown'):
                self.main_window.controlerDropDown.currentTextChanged.connect(
                    self._update_connect_button_tooltip
                )
        except Exception as e:
            pass
        
        # Monitor when buttons become disabled
        self._check_button_states()
    
    def _update_connect_button_tooltip(self, comm_mode):
        """Update connect button tooltip based on communication mode."""
        try:
            connect_btn = self.main_window.pushButton_connect
            if connect_btn is None:
                return
            
            if comm_mode == "GUI":
                # When in GUI mode, explain why it's unavailable
                tooltip = "Connect button disabled - GUI communication mode does not support direct PLC connection.\n" \
                          "Switch to a different communication mode to enable PLC connection."
                connect_btn.setEnabled(False)
                connect_btn.setToolTip(tooltip)
            else:
                # Enable and set normal tooltip
                connect_btn.setEnabled(True)
                base_tooltip = connect_btn.toolTip() or \
                    "Connect to or disconnect from the PLC"
                if "disabled" not in base_tooltip.lower():
                    connect_btn.setToolTip(base_tooltip)
        except Exception as e:
            pass
    
    def update_disabled_button_tooltips(self):
        """Update tooltips for disabled buttons to explain why."""
        try:
            # IP address field only editable when not connected
            if hasattr(self.main_window, 'lineEdit_IPAddress'):
                ip_field = self.main_window.lineEdit_IPAddress
                if not ip_field.isEnabled():
                    ip_field.setToolTip(
                        "IP address cannot be changed while connected to PLC.\n"
                        "Disconnect first to change the IP address."
                    )
        except Exception:
            pass
        
        try:
            # Communication mode only changeable when not connected
            if hasattr(self.main_window, 'controlerDropDown'):
                ctrl_combo = self.main_window.controlerDropDown
                if not ctrl_combo.isEnabled():
                    ctrl_combo.setToolTip(
                        "Communication mode cannot be changed while connected to PLC.\n"
                        "Disconnect first to change the communication mode."
                    )
        except Exception:
            pass
        
        try:
            # Port selector only changeable when not connected
            if hasattr(self.main_window, 'comboBox_networkPort'):
                port_combo = self.main_window.comboBox_networkPort
                if not port_combo.isEnabled():
                    port_combo.setToolTip(
                        "Communication port cannot be changed while connected to PLC.\n"
                        "Disconnect first to change the port."
                    )
        except Exception:
            pass
    
    def _check_button_states(self):
        """Periodically check and update button tooltips based on state."""
        self.update_disabled_button_tooltips()

def setup_tooltip_manager(main_window):
    """Initialize tooltip manager for the main window."""
    return TooltipManager(main_window)
