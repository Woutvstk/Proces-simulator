# Application Themes

This directory contains QSS (Qt Style Sheets) theme files for the PLC-Modbus Process Simulator.

## Available Themes

### Dark Theme (`dark_theme.qss`)
PyDracula-inspired dark theme with modern aesthetics.

**Color Palette:**
- Background: `#282c34` (dark gray)
- Sidebar: `#21252b` (darker gray)  
- Primary Accent: `#bd93f9` (purple)
- Secondary Accent: `#ff79c6` (pink)
- Success: `#50fa7b` (green)
- Error: `#ff5555` (red)
- Text: `#dcdcdc` (light gray)

**Best For:**
- Reduced eye strain in low-light environments
- Modern, professional appearance
- Extended work sessions

### Light Theme (`light_theme.qss`)
Clean, professional light theme with blue accents.

**Color Palette:**
- Background: `#f0f4f8` (light blue-gray)
- Sidebar: `#ffffff` (white)
- Primary Accent: `#3b82f6` (blue)
- Success: `#10b981` (green)
- Error: `#ef4444` (red)
- Text: `#1e293b` (dark gray)

**Best For:**
- Bright environments
- Traditional professional appearance
- High ambient lighting conditions

## Usage

### In Code
```python
from gui.theme_manager import ThemeManager
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

# Apply dark theme (default)
ThemeManager.apply_theme(app, "dark")

# Apply light theme
ThemeManager.apply_theme(app, "light")

# Toggle between themes
ThemeManager.toggle_theme(app)
```

### Default Theme
The application uses the **dark theme** by default, as configured in `src/main.py`.

## Styled Components

Both themes provide comprehensive styling for:

### Navigation & Layout
- Sidebar menus (collapsed and expanded states)
- Menu toggle button
- Header/top bar
- Stacked widget (main content area)
- Dock widgets

### Buttons & Controls
- Push buttons (normal, hover, pressed, checked, disabled)
- Connection button (with connected state)
- Exit button
- Simulation control buttons

### Input Widgets
- Line edits (text input)
- Spin boxes (numeric input)
- Combo boxes (dropdowns)
- Check boxes
- Radio buttons
- Sliders (horizontal and vertical)

### Data Display
- Tables with alternating row colors
- Tree widgets
- Header views
- Labels (including status labels)

### Visual Elements
- Scrollbars (modern thin style)
- Progress bars
- Tooltips
- Tab widgets
- Group boxes

### Special Components
- Tank/vessel widget container
- IO configuration tables
- General controls panel

## Customization

### Creating a New Theme

1. Copy an existing theme file as a template
2. Modify the color values to your preference
3. Save with a descriptive name (e.g., `blue_theme.qss`)
4. Add to `ThemeManager.THEMES` dictionary:
   ```python
   THEMES = {
       "dark": "themes/dark_theme.qss",
       "light": "themes/light_theme.qss",
       "blue": "themes/blue_theme.qss",  # Your new theme
   }
   ```

### Color Scheme Guidelines

When creating a new theme, maintain these principles:

1. **Sufficient Contrast:** Text must be readable against backgrounds
2. **Consistent Accent:** Use 1-2 accent colors throughout
3. **State Indication:** Different colors for hover, pressed, selected states
4. **Error/Success Colors:** Use red/green for clear status indication
5. **Visual Hierarchy:** Important elements should stand out

### Testing Your Theme

```python
# Test in main.py
ThemeManager.apply_theme(app, "your_theme_name")
```

## File Structure

```
themes/
├── dark_theme.qss      # PyDracula-inspired dark theme (default)
├── light_theme.qss     # Professional light theme
└── README.md           # This file
```

## Technical Details

### QSS Syntax
Qt Style Sheets use CSS-like syntax:
```css
QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    border-radius: 6px;
    padding: 10px 20px;
}

QPushButton:hover {
    background-color: #2563eb;
}
```

### Widget Selectors
- `QWidget` - All widgets of this type
- `#widgetName` - Specific widget by object name
- `QWidget:hover` - Pseudo-state selectors
- `QWidget::sub-control` - Sub-control styling

### Important Notes

1. **Performance:** QSS is applied once at startup - no runtime performance impact
2. **Override Order:** More specific selectors override general ones
3. **Resource Usage:** Minimal memory footprint (~100KB per theme)
4. **Hot Reload:** Call `apply_theme()` again to switch themes at runtime

## Credits

- **Dark Theme:** Inspired by [PyDracula](https://github.com/Wanderson-Magalhaes/Modern_GUI_PyDracula_PySide6_or_PyQt6) by Wanderson Magalhães
- **Light Theme:** Original design for this application
- **Implementation:** Part of PyQt5 to PySide6 migration project

## Related Files

- `src/gui/theme_manager.py` - Theme management logic
- `src/gui/ui_functions.py` - Animation and UI utilities
- `src/main.py` - Default theme application

## Version History

- **v1.0** (2024): Initial dark and light themes created as part of PySide6 migration
- Comprehensive styling for all Qt widgets
- PyDracula-inspired design language
