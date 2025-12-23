"""
UI Functions - Animated sidebar and other UI utilities
Based on PyDracula design patterns
"""
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, Qt
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtGui import QColor


class UIFunctions:
    """
    Collection of UI utility functions for animations and effects
    """
    
    @staticmethod
    def toggle_menu(window, enable: bool, animation_duration: int = 500):
        """
        Toggle the sidebar menu with smooth animation
        
        Args:
            window: MainWindow instance
            enable: True to expand, False to collapse
            animation_duration: Duration of animation in milliseconds
        """
        try:
            # Get current and target widths
            if not hasattr(window, 'fullMenuWidget'):
                return
            
            current_width = window.fullMenuWidget.width()
            max_width = 240  # Expanded width
            min_width = 60   # Collapsed width (icon only)
            
            # Determine target width
            if enable:
                target_width = max_width
                # Hide icon-only widget when expanding
                if hasattr(window, 'iconOnlyWidget'):
                    window.iconOnlyWidget.setVisible(False)
            else:
                target_width = min_width
            
            # Create and configure animation
            animation = QPropertyAnimation(window.fullMenuWidget, b"minimumWidth")
            animation.setDuration(animation_duration)
            animation.setStartValue(current_width)
            animation.setEndValue(target_width)
            animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
            
            # Also animate maximum width to prevent glitches
            max_animation = QPropertyAnimation(window.fullMenuWidget, b"maximumWidth")
            max_animation.setDuration(animation_duration)
            max_animation.setStartValue(current_width)
            max_animation.setEndValue(target_width)
            max_animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
            
            # Create parallel animation group
            animation_group = QParallelAnimationGroup(window)
            animation_group.addAnimation(animation)
            animation_group.addAnimation(max_animation)
            
            # Setup completion handler
            def on_animation_finished():
                if not enable and hasattr(window, 'iconOnlyWidget'):
                    # Show icon-only widget after collapse
                    window.iconOnlyWidget.setVisible(True)
                    window.fullMenuWidget.setVisible(False)
                else:
                    window.fullMenuWidget.setVisible(True)
            
            animation_group.finished.connect(on_animation_finished)
            
            # Ensure full menu is visible during animation
            window.fullMenuWidget.setVisible(True)
            
            # Start animation
            animation_group.start()
            
            # Store reference to prevent garbage collection
            window._menu_animation_group = animation_group
            
        except Exception as e:
            print(f"Error in toggle_menu: {e}")
    
    @staticmethod
    def add_shadow_effect(widget, blur_radius: int = 15, x_offset: int = 0, 
                         y_offset: int = 5, color: QColor = None):
        """
        Add drop shadow effect to a widget
        
        Args:
            widget: Widget to add shadow to
            blur_radius: Radius of the blur effect
            x_offset: Horizontal offset of shadow
            y_offset: Vertical offset of shadow
            color: Color of the shadow (default: semi-transparent black)
        """
        if color is None:
            color = QColor(0, 0, 0, 80)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur_radius)
        shadow.setXOffset(x_offset)
        shadow.setYOffset(y_offset)
        shadow.setColor(color)
        widget.setGraphicsEffect(shadow)
    
    @staticmethod
    def maximize_restore(window):
        """
        Toggle between maximized and normal window state
        
        Args:
            window: Window to maximize/restore
        """
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()
    
    @staticmethod
    def animate_widget_opacity(widget, start_value: float = 0.0, 
                               end_value: float = 1.0, duration: int = 300):
        """
        Animate widget opacity (fade in/out)
        
        Args:
            widget: Widget to animate
            start_value: Starting opacity (0.0 = invisible, 1.0 = fully visible)
            end_value: Ending opacity
            duration: Animation duration in milliseconds
        """
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(start_value)
        animation.setEndValue(end_value)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()
        
        # Store reference to prevent garbage collection
        widget._opacity_animation = animation
    
    @staticmethod
    def animate_widget_geometry(widget, start_rect, end_rect, duration: int = 300):
        """
        Animate widget geometry (position and size)
        
        Args:
            widget: Widget to animate
            start_rect: Starting QRect
            end_rect: Ending QRect
            duration: Animation duration in milliseconds
        """
        animation = QPropertyAnimation(widget, b"geometry")
        animation.setDuration(duration)
        animation.setStartValue(start_rect)
        animation.setEndValue(end_rect)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()
        
        # Store reference to prevent garbage collection
        widget._geometry_animation = animation
    
    @staticmethod
    def setup_button_hover_effects(button, normal_color: str, hover_color: str, 
                                   pressed_color: str):
        """
        Setup hover and press effects for a button using stylesheets
        
        Args:
            button: QPushButton to style
            normal_color: Normal background color
            hover_color: Hover background color
            pressed_color: Pressed background color
        """
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {normal_color};
                border-radius: 6px;
                padding: 10px 20px;
                color: #ffffff;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
        """)
