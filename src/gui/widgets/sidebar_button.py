"""
SidebarButton - Custom QPushButton for collapsible sidebar

This widget provides a unified button with icon and text that supports
expanded/collapsed states with smooth animations and hover effects.

Libraries used:
- PyQt5: GPL v3 License (https://www.riverbankcomputing.com/software/pyqt/)

Full license information available in LICENSE.txt
"""

from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import pyqtProperty, Qt


class SidebarButton(QPushButton):
    """
    Custom QPushButton for sidebar navigation with expanded/collapsed states.
    
    Features:
    - Supports 'expanded' property for QSS styling
    - Icon + text layout
    - Smooth hover and active state transitions
    - Integrates with sidebar animation system
    """
    
    def __init__(self, text="", icon=None, parent=None):
        """
        Initialize sidebar button.
        
        Args:
            text: Button text label
            icon: QIcon for the button
            parent: Parent widget
        """
        super().__init__(text, parent)
        self._expanded = False
        
        if icon:
            self.setIcon(icon)
        
        # Default properties
        self.setCheckable(True)
        self.setMinimumHeight(50)
        
    @pyqtProperty(bool)
    def expanded(self):
        """Get expanded state for QSS styling."""
        return self._expanded
    
    @expanded.setter
    def expanded(self, value):
        """
        Set expanded state and update styling.
        
        Args:
            value: True if expanded, False if collapsed
        """
        if self._expanded != value:
            self._expanded = value
            # Force style update
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
