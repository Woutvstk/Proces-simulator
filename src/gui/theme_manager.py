"""
Theme Manager - Handle theme switching for the application
"""
from pathlib import Path
from PySide6.QtWidgets import QApplication


class ThemeManager:
    """
    Manages application themes (dark/light mode)
    """
    
    THEMES = {
        "dark": "themes/dark_theme.qss",
        "light": "themes/light_theme.qss"
    }
    
    _current_theme = "dark"  # Default theme
    
    @staticmethod
    def apply_theme(app: QApplication, theme_name: str = "dark"):
        """
        Apply a theme to the application
        
        Args:
            app: QApplication instance
            theme_name: Name of the theme ("dark" or "light")
        """
        if theme_name not in ThemeManager.THEMES:
            print(f"Warning: Theme '{theme_name}' not found. Using 'dark' theme.")
            theme_name = "dark"
        
        theme_path = Path(__file__).parent / ThemeManager.THEMES[theme_name]
        
        if not theme_path.exists():
            print(f"Warning: Theme file not found: {theme_path}")
            return False
        
        try:
            with open(theme_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
                app.setStyleSheet(stylesheet)
                ThemeManager._current_theme = theme_name
                print(f"Applied theme: {theme_name}")
                return True
        except Exception as e:
            print(f"Error loading theme: {e}")
            return False
    
    @staticmethod
    def get_current_theme() -> str:
        """Get the currently active theme name"""
        return ThemeManager._current_theme
    
    @staticmethod
    def toggle_theme(app: QApplication):
        """
        Toggle between dark and light themes
        
        Args:
            app: QApplication instance
        """
        new_theme = "light" if ThemeManager._current_theme == "dark" else "dark"
        ThemeManager.apply_theme(app, new_theme)
        return new_theme
    
    @staticmethod
    def get_available_themes():
        """Get list of available theme names"""
        return list(ThemeManager.THEMES.keys())
