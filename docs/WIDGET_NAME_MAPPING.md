# Widget Name Mapping - Dutch to English

This document tracks the widget naming convention updates from Dutch to English in the PLC-Modbus Process Simulator UI.

## Status
The codebase analysis shows that most widget names are already in English. The following Dutch terms appear in the UI and may be candidates for future renaming:

## Current Widget Names (Mixed Dutch/English)

### Partially Dutch Names
| Current Name (Dutch) | Suggested English Name | Location | Priority |
|---------------------|------------------------|----------|----------|
| `vat1Page` | `tank1Page` or `vessel1Page` | mainWindowPIDRegelaarSim.ui | Low |
| `vatten2Page` | `tanks2Page` or `vessels2Page` | mainWindowPIDRegelaarSim.ui | Low |
| `vatWidgetContainer` | `tankWidgetContainer` | mainWindowPIDRegelaarSim.ui | Low |
| `pushButton_startSimulatie` | `pushButton_startSimulation` | mainWindowPIDRegelaarSim.ui | Low |
| `pushButton_2Vatten` | `pushButton_2Tanks` | mainWindowPIDRegelaarSim.ui | Low |
| `pushButton_1Vat` | `pushButton_1Tank` | mainWindowPIDRegelaarSim.ui | Low |
| `heatLossVatEntry` | `heatLossTankEntry` | mainWindowPIDRegelaarSim.ui | Low |

### Already English
The following widgets already use English names:
- `pushButton_settingsPage`
- `pushButton_IOPage`
- `pushButton_simPage`
- `pushButton_simSettings`
- `pushButton_generalControls`
- `pushButton_Exit`
- `pushButton_menu`
- `pushButton_connect`
- `pushButton_closePIDValves`
- `lineEdit_IPAddress`
- `comboBox_networkPort`
- `Label_connectStatus`
- `MainScreen` (QStackedWidget)
- `iconOnlyWidget`
- `fullMenuWidget`
- `headerWidget`

## Naming Conventions

### Standard Naming Pattern
Widgets follow this naming convention:
- **Format**: `{widgetType}_{descriptiveName}`
- **Examples**:
  - `pushButton_settingsPage` - Button to navigate to settings page
  - `lineEdit_IPAddress` - Line edit for IP address input
  - `Label_connectStatus` - Label showing connection status

### Alternative Naming (Camel Case)
Some newer widgets may use camel case without prefix:
- `connectionButton` instead of `pushButton_connect`
- `ipAddressInput` instead of `lineEdit_IPAddress`
- `networkAdapterCombo` instead of `comboBox_networkPort`

## Implementation Notes

### Impact Assessment
Renaming these widgets would require updates in:
1. `src/gui/media/mainWindowPIDRegelaarSim.ui` - UI file widget definitions
2. `src/gui/mainGui.py` - Main window widget references
3. `src/gui/pages/generalSettings.py` - Settings page references
4. `src/gui/pages/ioConfigPage.py` - IO configuration references
5. `src/simulations/PIDtankValve/settingsGui.py` - Tank simulation settings
6. `src/simulations/PIDtankValve/gui.py` - Tank widget references

### Current Status
✅ **PySide6 Migration Complete** - All imports updated, dynamic UI loading working
✅ **Modern Theme System** - Dark and light themes implemented with PyDracula-inspired design
✅ **Improved Animations** - Sidebar toggle with smooth InOutQuart easing
⏸️ **Widget Renaming** - Deferred (low priority, minimal Dutch terms remaining)

### Recommendation
Given that:
1. Most widgets already use English names
2. The few Dutch terms are domain-specific and well-understood (vat = tank/vessel)
3. The impact would be significant for minimal benefit
4. The migration to PySide6 and theme modernization are complete

**Decision**: Keep existing names for stability. Focus on new functionality (Phase 2: General Controls System).

## Future Considerations
If widget renaming becomes necessary:
1. Create a comprehensive search-and-replace script
2. Test all affected pages and mixins
3. Update any documentation or configuration files
4. Consider backward compatibility with saved configurations

## Translation Reference
Common Dutch-to-English translations in industrial/process control context:
- **vat** → tank, vessel, container
- **klep** → valve
- **simulatie** → simulation
- **verbinding/connectie** → connection
- **instellingen** → settings
- **regeling** → control, regulation
- **temperatuur** → temperature
- **niveau** → level
- **pomp** → pump
- **verwarming** → heating
