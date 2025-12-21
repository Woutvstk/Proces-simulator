"""
Settings Manager - Application preferences and persistence

Handles application-level settings using QSettings for cross-platform persistence.
Settings include communication parameters, display preferences, file paths, and advanced options.

Libraries used:
- PyQt5: GPL v3 License (https://www.riverbankcomputing.com/software/pyqt/)

Full license information available in LICENSE.txt
"""

from PyQt5.QtCore import QSettings, QObject, pyqtSignal
from pathlib import Path
import json


class SettingsManager(QObject):
    """
    Manages application settings with persistence using QSettings.
    
    Provides centralized access to all application preferences including:
    - Application preferences (language, theme, auto-save)
    - Communication settings (PLC parameters, timeouts)
    - Display settings (update rate, chart history, number format)
    - File paths (project location, backup, export directories)
    - Advanced settings (debug mode, log level, performance mode)
    
    Signals:
        settingsChanged: Emitted when any setting changes
        themeChanged(str): Emitted when theme selection changes
        languageChanged(str): Emitted when language changes
    """
    
    # Signals
    settingsChanged = pyqtSignal()
    themeChanged = pyqtSignal(str)
    languageChanged = pyqtSignal(str)
    
    def __init__(self, organization="PLC-Simulator", application="ProcessSimulator"):
        """
        Initialize settings manager.
        
        Args:
            organization: Organization name for QSettings
            application: Application name for QSettings
        """
        super().__init__()
        self.settings = QSettings(organization, application)
        self._load_defaults()
    
    def _load_defaults(self):
        """Load default settings if not already set."""
        # Application preferences
        if not self.settings.contains("app/language"):
            self.settings.setValue("app/language", "en")
        if not self.settings.contains("app/theme"):
            self.settings.setValue("app/theme", "professional_blue")
        if not self.settings.contains("app/auto_save_interval"):
            self.settings.setValue("app/auto_save_interval", 300)  # 5 minutes
        
        # Communication settings
        if not self.settings.contains("comm/timeout"):
            self.settings.setValue("comm/timeout", 5000)  # 5 seconds
        if not self.settings.contains("comm/retry_attempts"):
            self.settings.setValue("comm/retry_attempts", 3)
        if not self.settings.contains("comm/default_plc_ip"):
            self.settings.setValue("comm/default_plc_ip", "192.168.0.1")
        
        # Display settings
        if not self.settings.contains("display/update_rate"):
            self.settings.setValue("display/update_rate", 100)  # 100ms
        if not self.settings.contains("display/chart_history_length"):
            self.settings.setValue("display/chart_history_length", 1000)
        if not self.settings.contains("display/decimal_places"):
            self.settings.setValue("display/decimal_places", 2)
        if not self.settings.contains("display/units_system"):
            self.settings.setValue("display/units_system", "metric")
        
        # File paths
        if not self.settings.contains("paths/project_location"):
            default_project = str(Path.home() / "Documents" / "PLC-Simulator")
            self.settings.setValue("paths/project_location", default_project)
        if not self.settings.contains("paths/backup_directory"):
            default_backup = str(Path.home() / "Documents" / "PLC-Simulator" / "Backups")
            self.settings.setValue("paths/backup_directory", default_backup)
        if not self.settings.contains("paths/export_directory"):
            default_export = str(Path.home() / "Documents" / "PLC-Simulator" / "Exports")
            self.settings.setValue("paths/export_directory", default_export)
        
        # Advanced settings
        if not self.settings.contains("advanced/debug_mode"):
            self.settings.setValue("advanced/debug_mode", False)
        if not self.settings.contains("advanced/log_level"):
            self.settings.setValue("advanced/log_level", "INFO")
        if not self.settings.contains("advanced/performance_mode"):
            self.settings.setValue("advanced/performance_mode", False)
    
    # =========================================================================
    # Application Preferences
    # =========================================================================
    
    def get_language(self):
        """Get selected language."""
        return self.settings.value("app/language", "en")
    
    def set_language(self, language):
        """Set language and emit signal."""
        self.settings.setValue("app/language", language)
        self.languageChanged.emit(language)
        self.settingsChanged.emit()
    
    def get_theme(self):
        """Get selected theme."""
        return self.settings.value("app/theme", "professional_blue")
    
    def set_theme(self, theme):
        """Set theme and emit signal."""
        self.settings.setValue("app/theme", theme)
        self.themeChanged.emit(theme)
        self.settingsChanged.emit()
    
    def get_auto_save_interval(self):
        """Get auto-save interval in seconds."""
        return int(self.settings.value("app/auto_save_interval", 300))
    
    def set_auto_save_interval(self, seconds):
        """Set auto-save interval in seconds."""
        self.settings.setValue("app/auto_save_interval", seconds)
        self.settingsChanged.emit()
    
    # =========================================================================
    # Communication Settings
    # =========================================================================
    
    def get_timeout(self):
        """Get PLC communication timeout in milliseconds."""
        return int(self.settings.value("comm/timeout", 5000))
    
    def set_timeout(self, timeout_ms):
        """Set PLC communication timeout in milliseconds."""
        self.settings.setValue("comm/timeout", timeout_ms)
        self.settingsChanged.emit()
    
    def get_retry_attempts(self):
        """Get number of retry attempts for PLC communication."""
        return int(self.settings.value("comm/retry_attempts", 3))
    
    def set_retry_attempts(self, attempts):
        """Set number of retry attempts."""
        self.settings.setValue("comm/retry_attempts", attempts)
        self.settingsChanged.emit()
    
    def get_default_plc_ip(self):
        """Get default PLC IP address."""
        return self.settings.value("comm/default_plc_ip", "192.168.0.1")
    
    def set_default_plc_ip(self, ip):
        """Set default PLC IP address."""
        self.settings.setValue("comm/default_plc_ip", ip)
        self.settingsChanged.emit()
    
    # =========================================================================
    # Display Settings
    # =========================================================================
    
    def get_update_rate(self):
        """Get GUI update rate in milliseconds."""
        return int(self.settings.value("display/update_rate", 100))
    
    def set_update_rate(self, rate_ms):
        """Set GUI update rate in milliseconds."""
        self.settings.setValue("display/update_rate", rate_ms)
        self.settingsChanged.emit()
    
    def get_chart_history_length(self):
        """Get chart history length (number of data points)."""
        return int(self.settings.value("display/chart_history_length", 1000))
    
    def set_chart_history_length(self, length):
        """Set chart history length."""
        self.settings.setValue("display/chart_history_length", length)
        self.settingsChanged.emit()
    
    def get_decimal_places(self):
        """Get number of decimal places for number display."""
        return int(self.settings.value("display/decimal_places", 2))
    
    def set_decimal_places(self, places):
        """Set number of decimal places."""
        self.settings.setValue("display/decimal_places", places)
        self.settingsChanged.emit()
    
    def get_units_system(self):
        """Get units system (metric or imperial)."""
        return self.settings.value("display/units_system", "metric")
    
    def set_units_system(self, system):
        """Set units system."""
        self.settings.setValue("display/units_system", system)
        self.settingsChanged.emit()
    
    # =========================================================================
    # File Paths
    # =========================================================================
    
    def get_project_location(self):
        """Get default project location."""
        return self.settings.value("paths/project_location", 
                                   str(Path.home() / "Documents" / "PLC-Simulator"))
    
    def set_project_location(self, path):
        """Set default project location."""
        self.settings.setValue("paths/project_location", path)
        self.settingsChanged.emit()
    
    def get_backup_directory(self):
        """Get backup directory."""
        return self.settings.value("paths/backup_directory",
                                   str(Path.home() / "Documents" / "PLC-Simulator" / "Backups"))
    
    def set_backup_directory(self, path):
        """Set backup directory."""
        self.settings.setValue("paths/backup_directory", path)
        self.settingsChanged.emit()
    
    def get_export_directory(self):
        """Get export directory."""
        return self.settings.value("paths/export_directory",
                                   str(Path.home() / "Documents" / "PLC-Simulator" / "Exports"))
    
    def set_export_directory(self, path):
        """Set export directory."""
        self.settings.setValue("paths/export_directory", path)
        self.settingsChanged.emit()
    
    # =========================================================================
    # Advanced Settings
    # =========================================================================
    
    def get_debug_mode(self):
        """Get debug mode status."""
        return self.settings.value("advanced/debug_mode", False, type=bool)
    
    def set_debug_mode(self, enabled):
        """Set debug mode."""
        self.settings.setValue("advanced/debug_mode", enabled)
        self.settingsChanged.emit()
    
    def get_log_level(self):
        """Get logging level."""
        return self.settings.value("advanced/log_level", "INFO")
    
    def set_log_level(self, level):
        """Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""
        self.settings.setValue("advanced/log_level", level)
        self.settingsChanged.emit()
    
    def get_performance_mode(self):
        """Get performance mode status."""
        return self.settings.value("advanced/performance_mode", False, type=bool)
    
    def set_performance_mode(self, enabled):
        """Set performance mode."""
        self.settings.setValue("advanced/performance_mode", enabled)
        self.settingsChanged.emit()
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def reset_to_defaults(self):
        """Reset all settings to default values."""
        self.settings.clear()
        self._load_defaults()
        self.settingsChanged.emit()
    
    def export_settings(self, file_path):
        """
        Export all settings to a JSON file.
        
        Args:
            file_path: Path to export JSON file
        """
        settings_dict = {}
        for key in self.settings.allKeys():
            settings_dict[key] = self.settings.value(key)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, indent=2)
    
    def import_settings(self, file_path):
        """
        Import settings from a JSON file.
        
        Args:
            file_path: Path to import JSON file
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            settings_dict = json.load(f)
        
        for key, value in settings_dict.items():
            self.settings.setValue(key, value)
        
        self.settingsChanged.emit()
    
    def get_all_settings(self):
        """
        Get all settings as a dictionary.
        
        Returns:
            Dictionary with all settings
        """
        settings_dict = {}
        for key in self.settings.allKeys():
            settings_dict[key] = self.settings.value(key)
        return settings_dict
