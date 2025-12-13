import sys
import os
import subprocess
import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QPushButton, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem, QLineEdit, QMenu, QAction, QWidget, QVBoxLayout
)
from PyQt5.QtCore import Qt, QMimeData, QTimer
from PyQt5.QtGui import QDrag
from PyQt5 import uic
from tankSim.gui import VatWidget
from conveyor.gui import TransportbandWidget 
from tankSim.configurationTS import configuration
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from configuration import configuration 

# =============================================================================
# Resource and UI compilation (dynamic)
# =============================================================================
from pathlib import Path

# Determine the path to guiCommon directory
current_dir = Path(__file__).parent  # mainGui folder
gui_common_dir = current_dir.parent / "guiCommon"  # src/guiCommon

qrc_file = gui_common_dir / "Resource.qrc"
rc_py_file = gui_common_dir / "Resource_rc.py"

if qrc_file.exists():
    try:
        subprocess.run(
            ["pyrcc5", str(qrc_file), "-o", str(rc_py_file)], 
            check=True
        )
        print(f"Resources compiled: {rc_py_file.name}")
        
        # Add guiCommon to sys.path for import
        if str(gui_common_dir) not in sys.path:
            sys.path.insert(0, str(gui_common_dir))
        
        try:
            import Resource_rc  # type: ignore[import-not-found]
            print("Resource_rc imported")
        except ImportError as e:
            print(f"Resource_rc import failed: {e}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error compiling resources: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
else:
    print(f"{qrc_file.name} not found, resources not compiled")

# Load UI
ui_file = gui_common_dir / "mainWindowPIDRegelaarSim.ui"

if ui_file.exists():
    Ui_MainWindow, QtBaseClass = uic.loadUiType(str(ui_file))
    print(f"UI loaded: {ui_file.name}")
else:
    raise FileNotFoundError(f"Cannot find {ui_file}! Searched in: {ui_file}")


# =============================================================================
# Custom Table/Tree Widgets for IO configuration
# =============================================================================
class CustomTableWidgetItem(QTableWidgetItem):
    """Custom TableWidgetItem with smart sorting for addresses"""
    
    def __init__(self, text, sort_key=None):
        super().__init__(text)
        self._sort_key = sort_key
    
    def __lt__(self, other):
        if self._sort_key is not None and hasattr(other, '_sort_key') and other._sort_key is not None:
            return self._sort_key < other._sort_key
        return super().__lt__(other)


class EditableTableWidgetItem(QTableWidgetItem):
    """Custom item that is editable"""
    def __init__(self, text):
        super().__init__(text)
        self.setFlags(self.flags() | Qt.ItemIsEditable)


class ReadOnlyTableWidgetItem(QTableWidgetItem):
    """Custom item that is NOT editable"""
    def __init__(self, text):
        super().__init__(text)
        self.setFlags(self.flags() & ~Qt.ItemIsEditable)


class DraggableTreeWidget(QTreeWidget):
    """Custom QTreeWidget with drag functionality"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QTreeWidget.DragOnly)
        self.signal_data = {}
    
    def startDrag(self, supportedActions):
        """Start drag operation - only for items with signal data"""
        item = self.currentItem()
        if item:
            signal_name = item.text(0)
            
            # Block parent items without signal data
            if signal_name not in self.signal_data:
                print(f"Cannot drag '{signal_name}': no signal data available")
                return
            
            mime_data = QMimeData()
            mime_data.setText(signal_name)
            
            signal_info = self.signal_data[signal_name]
            mime_data.setData("application/json", 
                              json.dumps(signal_info).encode('utf-8'))
            
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            drag.exec_(Qt.CopyAction)


class DroppableTableWidget(QTableWidget):
    """Custom QTableWidget that accepts drops - only column 0"""
    
    def __init__(self, rows=0, columns=0, parent=None, io_screen=None):
        super().__init__(rows, columns, parent)
        self.setAcceptDrops(True)
        self.original_colors = {}
        self.row_data = {}
        self.sort_order = {}  
        self.io_screen = io_screen
        self.forced_rows = {}  # {row: {"value": forced_value, "original_bg": color}}
        self.force_enabled = False
        
        self.setSortingEnabled(False)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.NoSelection)
        
        self.last_selected_row = None
        
        self.horizontalHeader().sectionClicked.connect(self.handle_sort_click)
        self.verticalHeader().sectionClicked.connect(self.handle_row_click)
        self.itemChanged.connect(self.on_item_changed)
        
        # Column widths
        self.setColumnWidth(0, 180)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 60)
        self.setColumnWidth(3, 60)
        self.setColumnWidth(4, 100)
        self.setColumnWidth(5, 80)
        self.setColumnWidth(6, 250)
        self.setColumnWidth(7, 100)
    
    def on_item_changed(self, item):
        """Callback when a cell changes"""
        row = item.row()
        col = item.column()
        
        if col not in [2, 3]:
            return
        
        type_item = self.item(row, 1)
        byte_item = self.item(row, 2)
        bit_item = self.item(row, 3)
        addr_item = self.item(row, 4)
        
        if not type_item or not addr_item:
            return
        
        data_type = type_item.text()
        current_address = addr_item.text()
        
        if not current_address:
            return
        
        io_prefix = current_address[0] if current_address else 'I'
        
        try:
            if data_type == 'bool':
                if not byte_item or not bit_item or not byte_item.text() or not bit_item.text():
                    return
                
                byte_val = int(byte_item.text())
                bit_val = int(bit_item.text())
                
                if byte_val < 0 or byte_val > 255:
                    self.blockSignals(True)
                    byte_item.setText(str(min(255, max(0, byte_val))))
                    self.blockSignals(False)
                    return
                
                if bit_val < 0 or bit_val > 7:
                    self.blockSignals(True)
                    bit_item.setText(str(min(7, max(0, bit_val))))
                    self.blockSignals(False)
                    return
                
                new_address = f"{io_prefix}{byte_val}.{bit_val}"
                
            elif data_type in ['int', 'word']:
                if not byte_item or not byte_item.text():
                    return
                
                byte_val = int(byte_item.text())
                
                if byte_val < 0 or byte_val > 254:
                    self.blockSignals(True)
                    byte_item.setText(str(min(254, max(0, byte_val))))
                    self.blockSignals(False)
                    return
                
                if byte_val % 2 != 0:
                    byte_val = byte_val - 1
                    self.blockSignals(True)
                    byte_item.setText(str(byte_val))
                    self.blockSignals(False)
                
                if bit_item and bit_item.text():
                    self.blockSignals(True)
                    bit_item.setText("")
                    self.blockSignals(False)
                
                new_address = f"{io_prefix}W{byte_val}"
            else:
                return
            
            if new_address != current_address:
                self.blockSignals(True)
                self.setItem(row, 4, ReadOnlyTableWidgetItem(new_address))
                self.blockSignals(False)
            
            if self.io_screen:
                self.io_screen.validate_and_fix_manual_address(row)
            
            self._save_row_data(row)
            
        except ValueError:
            print(f"Invalid value in row {row}, column {col}")
    
    def handle_sort_click(self, logical_index):
        """Manual sorting - toggle asc/desc"""
        current_order = self.sort_order.get(logical_index, None)
        
        # Toggle between asc and desc
        next_order = 'desc' if current_order == 'asc' else 'asc'
        
        # Reset other columns
        for col in list(self.sort_order.keys()):
            if col != logical_index:
                del self.sort_order[col]
        
        self.sort_order[logical_index] = next_order
        self.manual_sort(logical_index, next_order)
    
    def handle_row_click(self, row):
        """Select rows with modifiers"""
        modifiers = QApplication.keyboardModifiers()
        
        if modifiers & Qt.ShiftModifier and self.last_selected_row is not None:
            self.clearSelection()
            start = min(self.last_selected_row, row)
            end = max(self.last_selected_row, row)
            for r in range(start, end + 1):
                for col in range(self.columnCount()):
                    if self.item(r, col):
                        self.item(r, col).setSelected(True)
            self.last_selected_row = row
        elif modifiers & Qt.ControlModifier:
            cells_in_row = [self.item(row, col) for col in range(self.columnCount()) if self.item(row, col)]
            if not cells_in_row:
                return
            row_is_selected = all(cell.isSelected() for cell in cells_in_row)
            if row_is_selected:
                for cell in cells_in_row:
                    cell.setSelected(False)
            else:
                for cell in cells_in_row:
                    cell.setSelected(True)
            self.last_selected_row = row
        else:
            self.clearSelection()
            cells_in_row = [self.item(row, col) for col in range(self.columnCount()) if self.item(row, col)]
            for cell in cells_in_row:
                cell.setSelected(True)
            self.last_selected_row = row
    
    def mousePressEvent(self, event):
        """Streamline cell selection"""
        index = self.indexAt(event.pos())
        modifiers = QApplication.keyboardModifiers()
        header_width = self.verticalHeader().width()
        is_on_row_header = event.pos().x() < header_width
        
        if index.isValid() and not is_on_row_header and not (modifiers & Qt.ControlModifier) and not (modifiers & Qt.ShiftModifier):
            self.clearSelection()
            super().mousePressEvent(event)
            return
        super().mousePressEvent(event)
    
    def keyPressEvent(self, event):
        """Delete handling"""
        if event.key() == Qt.Key_Delete:
            selected_rows = sorted(set(index.row() for index in self.selectedIndexes()), reverse=True)
            if selected_rows:
                for row in selected_rows:
                    self._clear_row_data(row)
                
                if self.io_screen:
                    self.io_screen.save_configuration()
                
                event.accept()
            else:
                event.ignore()
        elif event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
            for row in range(self.rowCount()):
                if any(self.item(row, col).text() for col in range(self.columnCount()) if self.item(row, col)):
                    for col in range(self.columnCount()):
                        if self.item(row, col):
                            self.item(row, col).setSelected(True)
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def manual_sort(self, column, order):
        """Sort rows manually"""
        rows_data = []
        for row in range(self.rowCount()):
            row_content = {}
            for col in range(self.columnCount()):
                item = self.item(row, col)
                row_content[col] = item.text() if item else ""
            rows_data.append(row_content)
        
        def sort_key(row_dict):
            val = row_dict.get(column, "")
            if not val:
                return (1, "")  # Empty values last
            
            # ✅ FIX: Probeer numeriek te sorteren, maar zorg voor consistente types
            try:
                num_val = float(val)
                return (0, num_val, "")  # Numeric: (priority=0, number, empty_string)
            except (ValueError, TypeError):
                return (0, float('inf'), val)  # String: (priority=0, infinity, string)
        
        rows_data.sort(key=sort_key, reverse=False)
        
        if order == 'desc':
            non_empty = [r for r in rows_data if r.get(column, "")]
            empty = [r for r in rows_data if not r.get(column, "")]
            rows_data = list(reversed(non_empty)) + empty
        
        self.blockSignals(True)
        for display_row, row_content in enumerate(rows_data):
            for col in range(self.columnCount()):
                text = row_content.get(col, "")
                if col in [2, 3]:
                    self.setItem(display_row, col, EditableTableWidgetItem(text))
                else:
                    self.setItem(display_row, col, ReadOnlyTableWidgetItem(text))
            self._save_row_data(display_row)
        self.blockSignals(False)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            for row in range(self.rowCount()):
                for col in range(self.columnCount()):
                    if not self.item(row, col):
                        if col in [2, 3]:
                            self.setItem(row, col, EditableTableWidgetItem(""))
                        else:
                            self.setItem(row, col, ReadOnlyTableWidgetItem(""))
                    item = self.item(row, col)
                    self.original_colors[(row, col)] = item.background()
                    if col == 0:
                        item.setBackground(Qt.white)
                    else:
                        item.setBackground(Qt.lightGray)
    
    def dragLeaveEvent(self, event):
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item and (row, col) in self.original_colors:
                    item.setBackground(self.original_colors[(row, col)])
        self.original_colors.clear()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            position = event.pos()
            col = self.columnAt(position.x())
            if col == 0:
                event.acceptProposedAction()
            else:
                event.ignore()
    
    def _save_row_data(self, row):
        """Save all data of a row"""
        self.row_data[row] = {}
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                self.row_data[row][col] = item.text()
    
    def _clear_row_data(self, row):
        """Clear all data of a row"""
        if row in self.row_data:
            del self.row_data[row]
        for col in range(self.columnCount()):
            if col in [2, 3]:
                self.setItem(row, col, EditableTableWidgetItem(""))
            else:
                self.setItem(row, col, ReadOnlyTableWidgetItem(""))
    
    def remove_duplicate_signals(self, signal_name, exclude_row=None):
        """Remove all instances of a signal"""
        rows_to_clear = []
        for row in range(self.rowCount()):
            if exclude_row is not None and row == exclude_row:
                continue
            item = self.item(row, 0)
            if item and item.text() == signal_name:
                rows_to_clear.append(row)
        for row in rows_to_clear:
            self._clear_row_data(row)
        return len(rows_to_clear)
    
    def get_used_addresses(self):
        """Retrieve all used addresses"""
        used = {}
        for row in range(self.rowCount()):
            addr_item = self.item(row, 4)
            data_type = self.item(row, 1)
            if addr_item and addr_item.text():
                address = addr_item.text()
                if '.' in address:
                    prefix_byte, bit = address.rsplit('.', 1)
                    if prefix_byte not in used:
                        used[prefix_byte] = set()
                    used[prefix_byte].add(int(bit))
                else:
                    if data_type and data_type.text() in ['int', 'word']:
                        try:
                            byte_num = int(address[2:]) if len(address) > 2 and address[1] == 'W' else 0
                        except ValueError:
                            continue
                        prefix = address[:2]
                        base_prefix = prefix[0]
                        for b in [byte_num, byte_num + 1]:
                            byte_key = f"{base_prefix}{b}"
                            if byte_key not in used:
                                used[byte_key] = set(range(8))
                            else:
                                used[byte_key].update(range(8))
        return used
    
    def get_byte_offset(self, prefix, data_type):
        """Retrieve the byte offset"""
        if not self.io_screen:
            return 0
        if data_type == 'bool':
            if prefix == 'I':
                return self.io_screen.get_offset('BoolInput')
            elif prefix == 'Q':
                return self.io_screen.get_offset('BoolOutput')
        elif data_type in ['int', 'word']:
            if prefix == 'I':
                return self.io_screen.get_offset('DWORDInput')
            elif prefix == 'Q':
                return self.io_screen.get_offset('DWORDOutput')
        return 0
    
    def find_free_address(self, prefix, data_type):
        """Find the first free address"""
        used = self.get_used_addresses()
        offset = self.get_byte_offset(prefix, data_type)
        
        if data_type == 'bool':
            for byte_num in range(offset, 256):
                byte_key = f"{prefix}{byte_num}"
                used_bits = used.get(byte_key, set())
                for bit in range(8):
                    if bit not in used_bits:
                        return (byte_num, bit, f"{prefix}{byte_num}.{bit}")
            return (offset, 0, f"{prefix}{offset}.0")
        elif data_type in ['int', 'word']:
            start_byte = offset if offset % 2 == 0 else offset + 1
            for byte_num in range(start_byte, 254, 2):
                byte1_key = f"{prefix}{byte_num}"
                byte2_key = f"{prefix}{byte_num + 1}"
                is_byte1_free = byte1_key not in used or len(used[byte1_key]) == 0
                is_byte2_free = byte2_key not in used or len(used[byte2_key]) == 0
                if is_byte1_free and is_byte2_free:
                    return (byte_num, None, f"{prefix}W{byte_num}")
            return (start_byte, None, f"{prefix}W{start_byte}")
        return (offset, 0, f"{prefix}{offset}.0")
    
    def dropEvent(self, event):
        """Process drop only in column 0"""
        if event.mimeData().hasText():
            dropped_text = event.mimeData().text()
            position = event.pos()
            row = self.rowAt(position.y())
            col = self.columnAt(position.x())
            
            if row >= 0 and col == 0:
                try:
                    removed_count = self.remove_duplicate_signals(dropped_text, exclude_row=row)
                    signal_data = None
                    if event.mimeData().hasFormat("application/json"):
                        try:
                            json_bytes = event.mimeData().data("application/json")
                            signal_data = json.loads(bytes(json_bytes).decode('utf-8'))
                        except:
                            pass
                    
                    self.blockSignals(True)
                    self.setItem(row, 0, ReadOnlyTableWidgetItem(dropped_text))
                    
                    if signal_data:
                        data_type = signal_data.get('type', 'bool')
                        if 'type' in signal_data:
                            self.setItem(row, 1, ReadOnlyTableWidgetItem(data_type))
                        io_prefix = signal_data.get('io_prefix', 'I')
                        byte_num, bit_num, full_address = self.find_free_address(io_prefix, data_type)
                        self.setItem(row, 2, EditableTableWidgetItem(str(byte_num)))
                        if bit_num is not None:
                            self.setItem(row, 3, EditableTableWidgetItem(str(bit_num)))
                        else:
                            self.setItem(row, 3, EditableTableWidgetItem(""))
                        self.setItem(row, 4, ReadOnlyTableWidgetItem(full_address))
                        if 'status' in signal_data:
                            self.setItem(row, 5, ReadOnlyTableWidgetItem(signal_data['status']))
                        if 'description' in signal_data:
                            self.setItem(row, 6, ReadOnlyTableWidgetItem(signal_data['description']))
                        if 'range' in signal_data:
                            self.setItem(row, 7, ReadOnlyTableWidgetItem(signal_data['range']))
                        self._save_row_data(row)
                    else:
                        self._save_row_data(row)
                    
                    self.blockSignals(False)
                    
                    if self.io_screen:
                        self.io_screen.save_configuration()
                    
                    event.acceptProposedAction()
                finally:
                    pass
            else:
                event.ignore()
        self.dragLeaveEvent(event)

    def set_force_mode(self, enabled):
        """Enable or disable force mode"""
        self.force_enabled = enabled
        
        if not enabled:
            # Clear all forces when disabled
            self.forced_rows.clear()
            # Reset all row backgrounds
            for row in range(self.rowCount()):
                for col in range(self.columnCount()):
                    item = self.item(row, col)
                    if item:
                        item.setBackground(Qt.white)

    def contextMenuEvent(self, event):
        """Right-click menu for forcing values"""
        if not self.force_enabled:
            return
        
        item = self.itemAt(event.pos())
        if not item:
            return
        
        row = item.row()
        
        # Check if row has a signal
        name_item = self.item(row, 0)
        type_item = self.item(row, 1)
        if not name_item or not name_item.text() or not type_item:
            return
        
        signal_name = name_item.text()
        data_type = type_item.text()
        
        menu = QMenu(self)
        
        if row in self.forced_rows:
            # Already forced - show remove force option
            remove_action = QAction(f"Remove Force from '{signal_name}'", self)
            remove_action.triggered.connect(lambda: self.remove_force(row))
            menu.addAction(remove_action)
        else:
            # Not forced - show force options
            if data_type == 'bool':
                force_true = QAction(f"Force '{signal_name}' = TRUE", self)
                force_true.triggered.connect(lambda: self.apply_force(row, True))
                menu.addAction(force_true)
                
                force_false = QAction(f"Force '{signal_name}' = FALSE", self)
                force_false.triggered.connect(lambda: self.apply_force(row, False))
                menu.addAction(force_false)
            else:
                # Analog value - show dialog
                force_value = QAction(f"Force '{signal_name}' to value...", self)
                force_value.triggered.connect(lambda: self.apply_force_analog(row, signal_name))
                menu.addAction(force_value)
        
        menu.exec_(event.globalPos())

    def apply_force(self, row, value):
        """Apply force to a boolean signal"""
        self.forced_rows[row] = {"value": value}
        
        # Highlight forced row with yellow background
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                item.setBackground(Qt.yellow)
        
        print(f"Force applied to row {row}: {value}")

    def apply_force_analog(self, row, signal_name):
        """Apply force to an analog signal with dialog"""
        from PyQt5.QtWidgets import QInputDialog
        
        value, ok = QInputDialog.getInt(
            self,
            "Force Analog Value",
            f"Enter value for '{signal_name}':",
            0, -32768, 32767, 1
        )
        
        if ok:
            self.apply_force(row, value)

    def remove_force(self, row):
        """Remove force from a signal"""
        if row in self.forced_rows:
            del self.forced_rows[row]
            
            # Reset background color
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    item.setBackground(Qt.white)
            
            print(f"Force removed from row {row}")

    def get_forced_value(self, row):
        """Get forced value for a row, or None if not forced"""
        if row in self.forced_rows:
            return self.forced_rows[row]["value"]
        return None

    def is_row_forced(self, row):
        """Check if a row is currently forced"""
        return row in self.forced_rows

    def update_status_column(self, row, value):
        """Update the status column (column 5) with current value"""
        status_item = self.item(row, 5)
        type_item = self.item(row, 1)
        
        if not type_item:
            return
        
        data_type = type_item.text()
        
        # Format value based on type
        if data_type == 'bool':
            display_text = "TRUE" if value else "FALSE"
        elif data_type in ['int', 'word']:
            display_text = str(int(value))
        else:
            display_text = str(value)
        
        # Add force indicator if forced
        if self.is_row_forced(row):
            display_text = f"🔒 {display_text}"
        
        if status_item:
            status_item.setText(display_text)
            # Highlight forced cells with light yellow
            if self.is_row_forced(row):
                status_item.setBackground(Qt.yellow)
            else:
                status_item.setBackground(Qt.white)
        else:
            new_item = ReadOnlyTableWidgetItem(display_text)
            if self.is_row_forced(row):
                new_item.setBackground(Qt.yellow)
            self.setItem(row, 5, new_item)

# =============================================================================
# IOScreen class for IO configuration
# =============================================================================
class IOScreen:
    def __init__(self, main_window):
        """IOScreen class that writes to the MainWindow"""
        self.main_window = main_window
        
        # Byte offset dictionary
        self.byte_offsets = {
            'BoolInput': 0,
            'BoolOutput': 0,
            'DWORDInput': 2,
            'DWORDOutput': 2
        }
        
        # File paths for storage
        self.config_file = Path("io_config.json")
        self.csv_export_file = Path("io_config.csv")

    def get_offset(self, offset_type):
        """Get a byte offset"""
        return self.byte_offsets.get(offset_type, 0)
    
    @property
    def offsets(self):
        """Alias for byte_offsets (backwards compatibility)"""
        return self.byte_offsets
    
    def set_offset(self, offset_type, value):
        """Set a byte offset"""
        self.byte_offsets[offset_type] = value
        print(f"Offset {offset_type} set to byte {value}")
    
    def is_address_in_use(self, address, exclude_row=None):
        """
        Check if an address is already in use
        Returns: (in_use, row_number) or (False, None)
        """
        table = self.main_window.tableWidget_IO
        
        for row in range(table.rowCount()):
            if exclude_row is not None and row == exclude_row:
                continue
            
            addr_item = table.item(row, 4)
            if addr_item and addr_item.text() == address:
                return True, row
        
        return False, None
    
    def validate_and_fix_manual_address(self, row):
        """
        Validate a manually entered address and restore the old address upon conflict.
        """
        table = self.main_window.tableWidget_IO
        
        byte_item = table.item(row, 2)
        bit_item = table.item(row, 3)
        type_item = table.item(row, 1)
        addr_item = table.item(row, 4)
        
        if not byte_item or not type_item:
            return
        
        old_row_data = table.row_data.get(row, {})
        
        try:
            data_type = type_item.text()
            current_addr = addr_item.text() if addr_item else ""
            if not current_addr:
                return
            io_prefix = current_addr[0]
            
            byte_num = int(byte_item.text()) if byte_item.text() else 0
            bit_num = None
            
            if data_type == 'bool' and bit_item and bit_item.text():
                bit_num = int(bit_item.text())
            
            if bit_num is not None:
                proposed_address = f"{io_prefix}{byte_num}.{bit_num}"
            elif data_type in ['int', 'word']:
                proposed_address = f"{io_prefix}W{byte_num}"
            else:
                return
            
            in_use, conflict_row = self.is_address_in_use(proposed_address, exclude_row=row)
            
            if in_use:
                print(f"Address {proposed_address} is already in use (row {conflict_row})")
                
                old_byte = old_row_data.get(2, "0")
                old_bit = old_row_data.get(3, "")
                old_address = old_row_data.get(4, "")
                
                table.blockSignals(True)
                byte_item.setText(old_byte)
                
                if bit_item:
                    bit_item.setText(old_bit)
                
                if addr_item:
                    addr_item.setText(old_address)
                else:
                    table.setItem(row, 4, ReadOnlyTableWidgetItem(old_address))
                
                table.blockSignals(False)
                print(f"Address restored to: {old_address}")
            else:
                table._save_row_data(row)
                self.save_configuration()
            
        except (ValueError, AttributeError) as e:
            print(f"Error validating address in row {row}: {e}")
    
    def save_configuration(self):
        """Sla de huidige IO configuratie op in JSON """

        root_dir = Path(__file__).resolve().parent

        tank_dir = root_dir.parent 
        tank_dir.mkdir(exist_ok=True)  # maakt map als ze nog niet bestaat

        self.config_file = tank_dir /"tankSim"/ "io_configuration.json"
        table = self.main_window.tableWidget_IO
            
        config_data = {
            'offsets': self.byte_offsets.copy(),
            'signals': []
        }

        for row in range(table.rowCount()):
            name_item = table.item(row, 0)
            if not name_item or not name_item.text():
                continue

            cfg = {
                'name': table.item(row, 0).text(),
                'type': table.item(row, 1).text() if table.item(row, 1) else "",
                'byte': table.item(row, 2).text() if table.item(row, 2) else "",
                'bit': table.item(row, 3).text() if table.item(row, 3) else "",
                'address': table.item(row, 4).text() if table.item(row, 4) else "",
                'status': table.item(row, 5).text() if table.item(row, 5) else "",
                'description': table.item(row, 6).text() if table.item(row, 6) else "",
                'range': table.item(row, 7).text() if table.item(row, 7) else ""
            }
            config_data['signals'].append(cfg)

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fout bij opslaan JSON: {e}")
            return
    
    def readdress_all_signals(self):
        """Heradresseer alle signalen in de tabel op basis van huidige offsets"""
        table = self.main_window.tableWidget_IO
        
        table.blockSignals(True)
        
        signals_to_readdress = []
        for row in range(table.rowCount()):
            name_item = table.item(row, 0)
            type_item = table.item(row, 1)
            
            if name_item and name_item.text() and type_item and type_item.text():
                addr_item = table.item(row, 4)
                if addr_item and addr_item.text():
                    io_prefix = addr_item.text()[0]
                    signals_to_readdress.append({
                        'row': row,
                        'name': name_item.text(),
                        'type': type_item.text(),
                        'io_prefix': io_prefix
                    })
        
        for signal in signals_to_readdress:
            row = signal['row']
            table.setItem(row, 2, EditableTableWidgetItem(""))
            table.setItem(row, 3, EditableTableWidgetItem(""))
            table.setItem(row, 4, ReadOnlyTableWidgetItem(""))
        
        for signal in signals_to_readdress:
            row = signal['row']
            data_type = signal['type']
            io_prefix = signal['io_prefix']
            
            byte_num, bit_num, full_address = table.find_free_address(io_prefix, data_type)
            
            table.setItem(row, 2, EditableTableWidgetItem(str(byte_num)))
            
            if bit_num is not None:
                table.setItem(row, 3, EditableTableWidgetItem(str(bit_num)))
            else:
                table.setItem(row, 3, EditableTableWidgetItem(""))
            
            table.setItem(row, 4, ReadOnlyTableWidgetItem(full_address))
            table._save_row_data(row)
        
        table.blockSignals(False)
        print(f"{len(signals_to_readdress)} signalen opnieuw geadresseerd")
        
        self.save_configuration()

    def reset_offsets_to_default(self):
        """Reset alle offsets naar hun default waarden"""
        self.byte_offsets = {
            'BoolInput': 0,
            'BoolOutput': 0,
            'DWORDInput': 2,
            'DWORDOutput': 2
        }
        
        print("Offsets gereset naar defaults")
        self.readdress_all_signals()


# =============================================================================
# MainWindow klasse
# =============================================================================
class MainWindow(QMainWindow, Ui_MainWindow):
    """Hoofdvenster van de applicatie"""
    
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        
        print("Initialiseren MainWindow...")
        
        # Start met collapsed menu
        self.fullMenuWidget.setVisible(False)
        self.iconOnlyWidget.setVisible(True)
        self.pushButton_menu.setChecked(False)
        
        # Verbind exit buttons
        self.pushButton_Exit.clicked.connect(self.close)
        self.pushButton_exit2.clicked.connect(self.close)

        self.io_screen = IOScreen(self)

        # Store reference to main configuration
        self.mainConfig = None  # Will be set from main.py
        self.tanksim_config = None
        self.tanksim_status = None
        
        # Initialize connection variables
        self.validPlcConnection = False
        self.plc = None

        # IP throttling
        self.ip_change_timer = QTimer()
        self.ip_change_timer.setSingleShot(True)
        self.ip_change_timer.timeout.connect(self._apply_ip_change)
        self.pending_ip = None
        
        # Main update timer - EENMALIG
        self.timer = QTimer()
        self.timer.setInterval(100)  # 10x per seconde
        self.timer.timeout.connect(self.update_values)
        self.timer.timeout.connect(self.update_io_status_display)
        self.timer.start()
        
        # Setup connection status icon
        try:
            self.update_connection_status_icon()
        except AttributeError:
            print("Label_connectStatus niet gevonden")
        
        # Connect button
        try:
            self.pushButton_connect.toggled.connect(self.on_connect_toggled)
            self.pushButton_connect.setCheckable(True)
        except AttributeError:
            print("pushButton_connect niet gevonden")

        try:
            self.lineEdit_IPAddress.textChanged.connect(self.on_ip_changed)
        except AttributeError:
            print("IP address field niet gevonden")
    
        # Vervang standard table widget met custom DroppableTableWidget
        try:
            old_table = self.tableWidget_IO
            parent = old_table.parent()
            layout = old_table.parent().layout()       
            old_table.hide() 
            self.tableWidget_IO = DroppableTableWidget(50, 8, parent, self.io_screen)
            headers = ["NAME", "TYPE", "BYTE", "BIT", "ADDRESS", "STATUS", "DESCRIPTION", "RANGE"]
            self.tableWidget_IO.setHorizontalHeaderLabels(headers)
            
            if layout:
                layout.replaceWidget(old_table, self.tableWidget_IO)
                old_table.deleteLater()
        except Exception as e:
            print(f"Kon DroppableTableWidget niet installeren: {e}")
        
        # Vervang tree widget met draggable versie
        try:
            old_tree = self.treeWidget_IO
            parent = old_tree.parent()
            layout = old_tree.parent().layout()
            old_tree.hide()     
            self.treeWidget_IO = DraggableTreeWidget(parent)
            self.treeWidget_IO.setHeaderLabel("IN/OUTPUTS")
            self.treeWidget_IO.setMinimumSize(250, 300)
            
            if layout:
                layout.replaceWidget(old_tree, self.treeWidget_IO)
                old_tree.deleteLater()
            
            self.load_io_tree()
        except Exception as e:
            print(f"Kon DraggableTreeWidget niet installeren: {e}")

        try:
            self.controlerDropDown.clear()
            controllers = [
                "GUI",
                "logo!",
                "PLC S7-1500/1200/400/300/ET 200SP",
                "PLCSim S7-1500 advanced",
                "PLCSim S7-1500/1200/400/300/ET 200SP"
            ]
            
            for controller in controllers:
                self.controlerDropDown.addItem(controller)
            
            # Set default to GUI
            self.controlerDropDown.setCurrentText("GUI")
            
        except AttributeError as e:
            print(f"Controller dropdown niet gevonden: {e}")
                
         # VatWidget toevoegen
        try:
            self.vat_widget = VatWidget()
            container = self.findChild(QWidget, "vatWidgetContainer")
            
            if container:
                # Check of layout al bestaat (vanuit Qt Designer)
                existing_layout = container.layout()
                
                if existing_layout is None:
                    # Geen layout, maak nieuwe aan
                    container_layout = QVBoxLayout(container)
                    container_layout.setContentsMargins(0, 0, 0, 0)
                else:
                    # Layout bestaat al, gebruik die
                    container_layout = existing_layout
                    container_layout.setContentsMargins(0, 0, 0, 0)
                
                container_layout.addWidget(self.vat_widget)
        except Exception as e:
            print(f"❌ Kon vatWidgetContainer niet installeren: {e}")

        try:
            self.transportband_widget = TransportbandWidget()
            container_transportband = self.findChild(QWidget, "transportbandWidgetContainer") 
            if container_transportband:
                # Check of layout al bestaat
                existing_layout = container_transportband.layout()
                if existing_layout is None:
                    container_layout = QVBoxLayout(container_transportband)
                    container_layout.setContentsMargins(0, 0, 0, 0)
                else:
                    container_layout = existing_layout
                    container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.addWidget(self.transportband_widget)

        except Exception as e:
            print(f"❌ Kon transportbandWidgetContainer niet installeren: {e}")
        
        try:
            # Kleur dropdown vullen
            self.kleurDropDown.clear()
            kleuren = [
                ("Blue", "#0000FF"),
                ("Red", "#FB5C5C"),
                ("Green", "#00FF00"),
                ("Yellow", "#FAFA2B"),
                ("Orange", "#FFB52B"),
                ("Purple", "#800080"),
                ("Gray", "#808080"),
            ]
            for naam, hexcode in kleuren:
                self.kleurDropDown.addItem(naam, hexcode)
            
            # Connect dropdowns EENMALIG
            self.kleurDropDown.currentIndexChanged.connect(self.on_kleur_changed)
            self.controlerDropDown.currentIndexChanged.connect(self.on_controller_changed)
            
            # Connect checkboxes EENMALIG
            self.regelbareKlepenCheckBox.toggled.connect(self.on_config_changed)
            self.regelbareWeerstandCheckBox.toggled.connect(self.on_config_changed)
            self.niveauschakelaarCheckBox.toggled.connect(self.on_config_changed)
            self.analogeWaardeTempCheckBox.toggled.connect(self.on_config_changed)
            
        except AttributeError as e:
            print(f"Sommige UI elementen niet gevonden: {e}")
        
        # Synchronisatie van entry fields
        try:
            self.entryGroupDebiet = [
                self.toekomendDebietEntry,
                self.toekomendDebietEntry1,
                self.toekomendDebietEntry2
            ]
            self.entryGroupTemp = [
                self.tempWeerstandEntry,
                self.tempWeerstandEntry1
            ]
            
            for group in (self.entryGroupDebiet, self.entryGroupTemp):
                for field in group:
                    field.textChanged.connect(lambda text, g=group: self.syncFields(text, g))
            
        except AttributeError as e:
            print(f"Sommige entry fields niet gevonden: {e}")
        
        # Verbind navigatie buttons
        self.pushButton_settingsPage.toggled.connect(self.go_to_settings)
        self.pushButton_settingsPage2.toggled.connect(self.go_to_settings)
        
        self.pushButton_IOPage.toggled.connect(self.go_to_io)
        self.pushButton_IOPage2.toggled.connect(self.go_to_io)
        
        self.pushButton_simPage.toggled.connect(self.go_to_sim)
        self.pushButton_simPage2.toggled.connect(self.go_to_sim)
        
        # Maak buttons mutual exclusive
        self.pushButton_1Vat.setAutoExclusive(True)
        self.pushButton_2Vatten.setAutoExclusive(True)
        self.pushButton_transportband.setAutoExclusive(True)

        self.pushButton_1Vat.toggled.connect(lambda checked: checked and self.select_simulation_simple(0))
        self.pushButton_2Vatten.toggled.connect(lambda checked: checked and self.select_simulation_simple(1))
        self.pushButton_transportband.toggled.connect(lambda checked: checked and self.select_simulation_simple(2))
        
        # Offset buttons
        try:
            self.pushButton_ApplyOffset.clicked.connect(self.apply_offsets)
            self.pushButton_DefaultOffset.clicked.connect(self.default_offsets)
        except AttributeError:
            print("Offset buttons niet gevonden in UI")

        try:
            self.pushButton_SaveIO.clicked.connect(self.save_io_configuration)
            self.pushButton_LoadIO.clicked.connect(self.load_io_configuration)
            self.pushButton_ReloadConfig.clicked.connect(self.reload_io_config)
        except:
            print("LoadIO/saveIO buttons niet gevonden in UI")

        try:
            self.pushButton_AllowForce.toggled.connect(self.toggle_force_mode)
            self.pushButton_AllowForce.setCheckable(True)
        except AttributeError:
            print("Force button niet gevonden in UI")
        
        try:
            self.pushButton_startSimulatie.setCheckable(True)
            self.pushButton_startSimulatie.toggled.connect(self.toggle_simulation)
            # Set initial state
            self.pushButton_startSimulatie.setText("START SIMULATIE")
            self.pushButton_startSimulatie.setStyleSheet("""
                QPushButton {
                    background-color: #44FF44;
                    color: black;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #00CC00;
                }
            """)
        except AttributeError:
            print("pushButton_startSimulatie not found in UI")

        initial_mode = self.controlerDropDown.currentText()
        if initial_mode == "GUI":
            try:
                self.pushButton_connect.setEnabled(False)
            except AttributeError:
                pass

        QTimer.singleShot(100, self._initialize_gui_mode)

    def _initialize_gui_mode(self):
        """Initialize GUI mode after mainConfig is available"""
        if hasattr(self, 'mainConfig') and self.mainConfig:
            self.mainConfig.plcGuiControl = "gui"
            self.mainConfig.plcProtocol = "GUI"
        else:
            QTimer.singleShot(100, self._initialize_gui_mode)

        

    def update_values(self):
        """Update alle waarden van UI naar vat widget - GEEN CONNECTS HIER!"""
        try:
            # Lees waarden uit UI
            self.vat_widget.toekomendDebiet = int(self.toekomendDebietEntry.text() or 0)
            self.vat_widget.tempWeerstand = float(self.tempWeerstandEntry.text() or 20.0)
            
            # Checkbox states
            self.vat_widget.regelbareKleppen = self.regelbareKlepenCheckBox.isChecked()
            self.vat_widget.regelbareWeerstand = self.regelbareWeerstandCheckBox.isChecked()
            self.vat_widget.niveauschakelaar = self.niveauschakelaarCheckBox.isChecked()
            self.vat_widget.analogeWaardeTemp = self.analogeWaardeTempCheckBox.isChecked()
            
            # Controller mode
            controller_mode = self.controlerDropDown.currentText()
            self.vat_widget.controler = controller_mode
            
            # Kleur water
            self.vat_widget.kleurWater = self.kleurDropDown.currentData()
            
            # UI Elements zichtbaarheid - CHECK STATE VOOR UPDATE ✅
            is_gui_mode = (controller_mode == "GUI")
            
            try:
                if is_gui_mode and self.vat_widget.regelbareKleppen:
                    # Toon regelbare kleppen, verberg standaard
                    if not self.regelbareKlepenGUISim.isVisible():
                        self.GUiSim.hide()
                        self.regelbareKlepenGUISim.show()
                elif is_gui_mode and not self.vat_widget.regelbareKleppen:
                    # Toon standaard, verberg regelbare
                    if not self.GUiSim.isVisible():
                        self.regelbareKlepenGUISim.hide()
                        self.GUiSim.show()
                else:
                    # PLC mode - verberg alles
                    if self.GUiSim.isVisible() or self.regelbareKlepenGUISim.isVisible():
                        self.GUiSim.hide()
                        self.regelbareKlepenGUISim.hide()
            except AttributeError:
                pass  # UI elementen bestaan mogelijk niet
            
            # Klep standen
            if self.vat_widget.regelbareKleppen:
                try:
                    self.vat_widget.KlepStandBoven = int(self.klepstandBovenEntry.text() or 0)
                except (ValueError, AttributeError):
                    self.vat_widget.KlepStandBoven = 0
                try:
                    self.vat_widget.KlepStandBeneden = int(self.klepstandBenedenEntry.text() or 0)
                except (ValueError, AttributeError):
                    self.vat_widget.KlepStandBeneden = 0
            else:
                try:
                    boven_checked = self.klepstandBovenCheckBox.isChecked()
                    beneden_checked = self.klepstandBenedenCheckBox.isChecked()
                    self.vat_widget.KlepStandBoven = 100 if boven_checked else 0
                    self.vat_widget.KlepStandBeneden = 100 if beneden_checked else 0
                except AttributeError:
                    pass
        
        except Exception as e:
            pass  # Silently ignore tijdens init
        
        # === SCHRIJF NAAR STATUS OBJECT (GUI MODE) ✅ ===
        if not hasattr(self, 'tanksim_status') or self.tanksim_status is None:
            return  # Status nog niet beschikbaar
        
        if not hasattr(self, 'mainConfig') or self.mainConfig is None:
            return  # Config nog niet beschikbaar
        
        if self.mainConfig.plcGuiControl == "gui":
            # Schrijf kleppen fractie naar status
            self.tanksim_status.valveInOpenFraction = self.vat_widget.KlepStandBoven / 100.0
            self.tanksim_status.valveOutOpenFraction = self.vat_widget.KlepStandBeneden / 100.0
            
            # Heater staat
            if self.vat_widget.regelbareWeerstand:
                self.tanksim_status.heaterPowerFraction = 0.5  # TODO: voeg slider toe
            else:
                try:
                    heater_on = self.weerstandCheckBox.isChecked()
                    self.tanksim_status.heaterPowerFraction = 1.0 if heater_on else 0.0
                except:
                    self.tanksim_status.heaterPowerFraction = 0.0
        
        # === LEES STATUS TERUG (voor visuele feedback) ===
        # Update GUI global vars vanuit status
        import tankSim.gui as gui_module
        gui_module.currentHoogteVat = self.tanksim_status.liquidVolume
        gui_module.tempVat = self.tanksim_status.liquidTemperature
        
        # Rebuild SVG
        self.vat_widget.rebuild()
        
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            if hasattr(self, 'mainConfig') and self.mainConfig:
                if self.mainConfig.plcGuiControl == "gui":
                    # Schrijf kleppen fractie naar status
                    self.tanksim_status.valveInOpenFraction = self.vat_widget.KlepStandBoven / 100.0
                    self.tanksim_status.valveOutOpenFraction = self.vat_widget.KlepStandBeneden / 100.0
                    
                    # Heater staat
                    if self.vat_widget.regelbareWeerstand:
                        self.tanksim_status.heaterPowerFraction = 0.5  # TODO: voeg slider toe
                    else:
                        try:
                            heater_on = self.weerstandCheckBox.isChecked()
                            self.tanksim_status.heaterPowerFraction = 1.0 if heater_on else 0.0
                        except:
                            self.tanksim_status.heaterPowerFraction = 0.0
        
        # === LEES STATUS TERUG (voor visuele feedback) ===
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            # Update GUI global vars vanuit status
            import tankSim.gui as gui_module
            gui_module.currentHoogteVat = self.tanksim_status.liquidVolume
            gui_module.tempVat = self.tanksim_status.liquidTemperature
        
        # Rebuild SVG (was er al)
        self.vat_widget.rebuild()

        
    
    def update_io_status_display(self):
        """Update status kolom met huidige IO waarden - indien PLC actief"""
        try:
            if not hasattr(self, 'plc') or not hasattr(self, 'tanksim_config'):
                return
            
            # Check if PLC is connected
            if not hasattr(self, 'validPlcConnection') or not self.validPlcConnection:
                return
            
            table = self.tableWidget_IO
            config = self.tanksim_config
            
            # Loop door alle rijen
            for row in range(table.rowCount()):
                name_item = table.item(row, 0)
                if not name_item or not name_item.text():
                    continue
                
                signal_name = name_item.text()
                
                # Check if forced
                is_forced = table.is_row_forced(row)
                
                # Check if this signal is mapped in config
                if signal_name not in config.io_signal_mapping:
                    continue
                
                attr_name = config.io_signal_mapping[signal_name]
                attr_value = getattr(config, attr_name, None)
                
                if attr_value is None:
                    continue
                
                # Get forced value or read from PLC
                if is_forced:
                    value = table.get_forced_value(row)
                else:
                    try:
                        if "bit" in attr_value:  # Digital signal
                            byte_addr = attr_value["byte"]
                            bit_addr = attr_value["bit"]
                            
                            if attr_name.startswith("DQ"):  # PLC Output
                                value = self.plc.GetDO(byte_addr, bit_addr)
                            else:  # DI - PLC Input
                                value = self.plc.GetDI(byte_addr, bit_addr)
                            
                        else:  # Analog signal
                            byte_addr = attr_value["byte"]
                            
                            if attr_name.startswith("AQ"):  # PLC Analog Output
                                value = self.plc.GetAO(byte_addr)
                            else:  # AI - PLC Analog Input
                                value = self.plc.GetAI(byte_addr)
                        
                    except Exception as e:
                        continue  # PLC read error
                
                # Update status column with value and highlight if forced
                table.update_status_column(row, value)
                
        except Exception as e:
            pass  # Silent fail
    
    def on_kleur_changed(self):
        """Callback wanneer kleur dropdown wijzigt"""
        new_color = self.kleurDropDown.currentData()
        self.vat_widget.kleurWater = new_color
        print(f"Kleur: {new_color}")
    
    def on_config_changed(self):
        """Callback wanneer configuratie checkbox wijzigt"""
        # Force rebuild via update_values
        pass
    
    def syncFields(self, text, group):
        """Synchroniseer gelinkte entry velden"""
        for field in group:
            if field.text() != text:
                field.blockSignals(True)
                field.setText(text)
                field.blockSignals(False)
    
    def go_to_settings(self, checked):
        if checked:
            self.MainScreen.setCurrentIndex(3)
    
    def go_to_io(self, checked):
        if checked:
            self.MainScreen.setCurrentIndex(4)
    
    def go_to_sim(self, checked):
        if checked:
            self.MainScreen.setCurrentIndex(0)
            if not self.fullMenuWidget.isVisible():
                self.pushButton_menu.setChecked(True)
    
    def select_simulation_simple(self, sim_index):
        self.MainScreen.setCurrentIndex(sim_index)
    
    def load_io_tree(self):
        """Laad IO signalen van XML bestand"""
        current_dir = Path(__file__).parent  # mainGui folder
        xml_file = current_dir.parent / "guiCommon" / "io_treeList.xml"
        
        try:
            tree = ET.parse(str(xml_file))  # Converteer Path naar string
            root = tree.getroot()
            
            tanksim = root.find('TankSim')
            if tanksim is None:
                print("TankSim niet gevonden in XML")
                return
            
            # INPUTS
            inputs_root = tanksim.find('Inputs')
            if inputs_root is not None:
                inputs_item = QTreeWidgetItem(self.treeWidget_IO, ["Inputs"])
                
                digital = inputs_root.find('Digital')
                if digital is not None:
                    digital_item = QTreeWidgetItem(inputs_item, ["Digital"])
                    for signal in digital.findall('Signal'):
                        signal_name = signal.text.strip() if signal.text else "Unknown"
                        QTreeWidgetItem(digital_item, [signal_name])
                        
                        signal_info = {
                            'type': signal.get('type', 'bool'),
                            'io_prefix': signal.get('io_prefix', 'I'),
                            'status': signal.get('status', ''),
                            'description': signal.get('description', ''),
                            'range': signal.get('range', '')
                        }
                        self.treeWidget_IO.signal_data[signal_name] = signal_info
                
                analog = inputs_root.find('Analog')
                if analog is not None:
                    analog_item = QTreeWidgetItem(inputs_item, ["Analog"])
                    for signal in analog.findall('Signal'):
                        signal_name = signal.text.strip() if signal.text else "Unknown"
                        QTreeWidgetItem(analog_item, [signal_name])
                        
                        signal_info = {
                            'type': signal.get('type', 'int'),
                            'io_prefix': signal.get('io_prefix', 'I'),
                            'status': signal.get('status', ''),
                            'description': signal.get('description', ''),
                            'range': signal.get('range', '')
                        }
                        self.treeWidget_IO.signal_data[signal_name] = signal_info
            
            # OUTPUTS
            outputs_root = tanksim.find('Outputs')
            if outputs_root is not None:
                outputs_item = QTreeWidgetItem(self.treeWidget_IO, ["Outputs"])
                
                digital = outputs_root.find('Digital')
                if digital is not None:
                    digital_item = QTreeWidgetItem(outputs_item, ["Digital"])
                    for signal in digital.findall('Signal'):
                        signal_name = signal.text.strip() if signal.text else "Unknown"
                        QTreeWidgetItem(digital_item, [signal_name])
                        
                        signal_info = {
                            'type': signal.get('type', 'bool'),
                            'io_prefix': signal.get('io_prefix', 'Q'),
                            'status': signal.get('status', ''),
                            'description': signal.get('description', ''),
                            'range': signal.get('range', '')
                        }
                        self.treeWidget_IO.signal_data[signal_name] = signal_info
                
                analog = outputs_root.find('Analog')
                if analog is not None:
                    analog_item = QTreeWidgetItem(outputs_item, ["Analog"])
                    for signal in analog.findall('Signal'):
                        signal_name = signal.text.strip() if signal.text else "Unknown"
                        QTreeWidgetItem(analog_item, [signal_name])
                        
                        signal_info = {
                            'type': signal.get('type', 'int'),
                            'io_prefix': signal.get('io_prefix', 'Q'),
                            'status': signal.get('status', ''),
                            'description': signal.get('description', ''),
                            'range': signal.get('range', '')
                        }
                        self.treeWidget_IO.signal_data[signal_name] = signal_info
            
            self.treeWidget_IO.expandAll()

            
        except Exception as e:
            print(f"Fout bij laden XML: {e}")
            import traceback
            traceback.print_exc()
    
    def apply_offsets(self):
        """Pas offset waarden toe"""
        try:
            new_bool_input = int(self.QLineEdit_BoolInput.text())
            new_bool_output = int(self.QLineEdit_BoolOutput.text())
            new_dword_input = int(self.QLineEdit_DWORDInput.text())
            new_dword_output = int(self.QLineEdit_DWORDOutput.text())
            
            new_bool_input = max(0, min(255, new_bool_input))
            new_bool_output = max(0, min(255, new_bool_output))
            new_dword_input = max(0, min(255, new_dword_input))
            new_dword_output = max(0, min(255, new_dword_output))
            
            if new_dword_input % 2 != 0:
                new_dword_input -= 1
            if new_dword_output % 2 != 0:
                new_dword_output -= 1
            
            self.QLineEdit_BoolInput.setText(str(new_bool_input))
            self.QLineEdit_BoolOutput.setText(str(new_bool_output))
            self.QLineEdit_DWORDInput.setText(str(new_dword_input))
            self.QLineEdit_DWORDOutput.setText(str(new_dword_output))
            
            old_offsets = self.io_screen.byte_offsets.copy()
            
            self.io_screen.byte_offsets = {
                'BoolInput': new_bool_input,
                'BoolOutput': new_bool_output,
                'DWORDInput': new_dword_input,
                'DWORDOutput': new_dword_output
            }
            
            if old_offsets != self.io_screen.byte_offsets:
                print(f"Offsets toegepast")
                self.io_screen.readdress_all_signals()
            else:
                print("ℹGeen wijzigingen")
                
        except Exception as e:
            print(f"Fout bij offsets: {e}")

    def default_offsets(self):
        """Reset offsets naar defaults"""
        self.QLineEdit_BoolInput.setText("0")
        self.QLineEdit_BoolOutput.setText("0")
        self.QLineEdit_DWORDInput.setText("2")
        self.QLineEdit_DWORDOutput.setText("2")
        
        self.io_screen.reset_offsets_to_default()
        print("Offsets gereset")

    def save_io_configuration(self):
        """Sla IO configuratie op naar een JSON bestand"""
        try:
            # Open file dialog voor opslaan
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save IO Configuration",
                "io_configuration.json",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            table = self.tableWidget_IO
            
            config_data = {
                'offsets': self.io_screen.byte_offsets.copy(),
                'signals': []
            }
            
            for row in range(table.rowCount()):
                name_item = table.item(row, 0)
                if not name_item or not name_item.text():
                    continue
                
                cfg = {
                    'name': table.item(row, 0).text(),
                    'type': table.item(row, 1).text() if table.item(row, 1) else "",
                    'byte': table.item(row, 2).text() if table.item(row, 2) else "",
                    'bit': table.item(row, 3).text() if table.item(row, 3) else "",
                    'address': table.item(row, 4).text() if table.item(row, 4) else "",
                    'status': table.item(row, 5).text() if table.item(row, 5) else "",
                    'description': table.item(row, 6).text() if table.item(row, 6) else "",
                    'range': table.item(row, 7).text() if table.item(row, 7) else ""
                }
                config_data['signals'].append(cfg)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "Success", f"IO Configuration saved to:\n{file_path}")
            print(f"IO configuratie opgeslagen: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save IO configuration:\n{str(e)}")
            print(f"Fout bij opslaan: {e}")

    def load_io_configuration(self):
        """Laad IO configuratie vanuit een JSON bestand"""
        try:
            # Open file dialog voor laden
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load IO Configuration",
                "",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Lees en valideer JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            if 'signals' not in config_data:
                QMessageBox.warning(self, "Invalid File", "File does not contain valid IO configuration data.")
                return
            
            # Vraag bevestiging
            reply = QMessageBox.question(
                self,
                "Confirm Load",
                f"This will replace the current IO configuration.\n"
                f"Found {len(config_data['signals'])} signals.\n\n"
                f"Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
            table = self.tableWidget_IO
            
            # Wis huidige tabel
            table.blockSignals(True)
            for row in range(table.rowCount()):
                table._clear_row_data(row)
            table.blockSignals(False)
            
            # Laad offsets indien aanwezig
            if 'offsets' in config_data:
                self.io_screen.byte_offsets = config_data['offsets'].copy()
                
                # Update offset UI fields
                try:
                    self.QLineEdit_BoolInput.setText(str(config_data['offsets'].get('BoolInput', 0)))
                    self.QLineEdit_BoolOutput.setText(str(config_data['offsets'].get('BoolOutput', 0)))
                    self.QLineEdit_DWORDInput.setText(str(config_data['offsets'].get('DWORDInput', 2)))
                    self.QLineEdit_DWORDOutput.setText(str(config_data['offsets'].get('DWORDOutput', 2)))
                except AttributeError:
                    pass
            
            # Laad signalen
            table.blockSignals(True)
            for idx, signal in enumerate(config_data['signals']):
                if idx >= table.rowCount():
                    break
                
                # Kolom 0: NAME (read-only)
                table.setItem(idx, 0, ReadOnlyTableWidgetItem(signal.get('name', '')))
                
                # Kolom 1: TYPE (read-only)
                table.setItem(idx, 1, ReadOnlyTableWidgetItem(signal.get('type', '')))
                
                # Kolom 2: BYTE (editable)
                table.setItem(idx, 2, EditableTableWidgetItem(signal.get('byte', '')))
                
                # Kolom 3: BIT (editable)
                table.setItem(idx, 3, EditableTableWidgetItem(signal.get('bit', '')))
                
                # Kolom 4: ADDRESS (read-only)
                table.setItem(idx, 4, ReadOnlyTableWidgetItem(signal.get('address', '')))
                
                # Kolom 5: STATUS (read-only)
                table.setItem(idx, 5, ReadOnlyTableWidgetItem(signal.get('status', '')))
                
                # Kolom 6: DESCRIPTION (read-only)
                table.setItem(idx, 6, ReadOnlyTableWidgetItem(signal.get('description', '')))
                
                # Kolom 7: RANGE (read-only)
                table.setItem(idx, 7, ReadOnlyTableWidgetItem(signal.get('range', '')))
                
                table._save_row_data(idx)
            
            table.blockSignals(False)
            
            QMessageBox.information(self, "Success", f"IO Configuration loaded from:\n{file_path}")
            print(f"IO configuratie geladen: {file_path}")
            
            # Sla automatisch op naar standaard locatie
            self.io_screen.save_configuration()
            
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error", "Invalid JSON file format.")
            print("Ongeldige JSON file")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load IO configuration:\n{str(e)}")
            print(f"Fout bij laden: {e}")

    def reload_io_config(self):
        """Herlaad IO configuratie vanuit JSON tijdens runtime"""
        try:
            if not hasattr(self, 'tanksim_config') or self.tanksim_config is None:
                QMessageBox.warning(self, "Error", "TankSim configuratie niet beschikbaar.")
                return
            
            # Zoek JSON bestand
            project_root = Path(__file__).resolve().parent.parent
            io_config_path = project_root / "tankSim" / "io_configuration.json"
            
            if not io_config_path.exists():
                QMessageBox.warning(
                    self, 
                    "File Not Found", 
                    f"IO configuratie bestand niet gevonden:\n{io_config_path}"
                )
                return
            
            # Vraag bevestiging
            reply = QMessageBox.question(
                self,
                "Confirm Reload",
                "Dit herlaadt de IO adressen vanuit io_configuration.json.\n"
                "Lopende PLC verbindingen kunnen verstoord worden.\n\n"
                "Doorgaan?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
            # Disconnect PLC als verbonden
            if hasattr(self, 'validPlcConnection') and self.validPlcConnection:
                if hasattr(self, 'plc') and self.plc:
                    try:
                        self.plc.disconnect()
                        print("🔌 PLC disconnected voor config reload")
                    except:
                        pass
                
                self.validPlcConnection = False
                self.plc = None
                self.update_connection_status_icon()
                
                # Untoggle connect button
                try:
                    self.pushButton_connect.blockSignals(True)
                    self.pushButton_connect.setChecked(False)
                    self.pushButton_connect.blockSignals(False)
                except:
                    pass
            
            # Herlaad configuratie
            old_byte_range = (self.tanksim_config.lowestByte, self.tanksim_config.highestByte)
            self.tanksim_config.load_io_config_from_file(io_config_path)
            new_byte_range = (self.tanksim_config.lowestByte, self.tanksim_config.highestByte)
            
            # Update GUI tabel met nieuwe adressen
            self._update_table_from_config()
            
            # Toon resultaat
            QMessageBox.information(
                self,
                "Success",
                f"IO configuratie herladen!\n\n"
                f"Herverbind met PLC indien nodig."
            )
         
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Fout bij herladen configuratie:\n{str(e)}")
            print(f"❌ Reload error: {e}")
            import traceback
            traceback.print_exc()

    def _update_table_from_config(self):
        """Update de GUI tabel met adressen uit de config"""
        try:
            table = self.tableWidget_IO
            config = self.tanksim_config
            
            table.blockSignals(True)
            
            # Loop door alle rijen in de tabel
            for row in range(table.rowCount()):
                name_item = table.item(row, 0)
                if not name_item or not name_item.text():
                    continue
                
                signal_name = name_item.text()
                
                # Check of dit signaal in de mapping zit
                if signal_name not in config.io_signal_mapping:
                    continue
                
                # Haal attribuut naam en waarde op
                attr_name = config.io_signal_mapping[signal_name]
                attr_value = getattr(config, attr_name, None)
                
                if attr_value is None:
                    continue
                
                # Update byte/bit/address in tabel
                if "bit" in attr_value:
                    # Digital signaal
                    byte_num = attr_value["byte"]
                    bit_num = attr_value["bit"]
                    
                    # Bepaal IO prefix (I of Q)
                    if attr_name.startswith("DQ") or attr_name.startswith("AQ"):
                        io_prefix = "Q"
                    else:
                        io_prefix = "I"
                    
                    address = f"{io_prefix}{byte_num}.{bit_num}"
                    
                    table.setItem(row, 2, EditableTableWidgetItem(str(byte_num)))
                    table.setItem(row, 3, EditableTableWidgetItem(str(bit_num)))
                    table.setItem(row, 4, ReadOnlyTableWidgetItem(address))
                    
                else:
                    # Analog signaal
                    byte_num = attr_value["byte"]
                    
                    # Bepaal IO prefix
                    if attr_name.startswith("DQ") or attr_name.startswith("AQ"):
                        io_prefix = "Q"
                    else:
                        io_prefix = "I"
                    
                    address = f"{io_prefix}W{byte_num}"
                    
                    table.setItem(row, 2, EditableTableWidgetItem(str(byte_num)))
                    table.setItem(row, 3, EditableTableWidgetItem(""))
                    table.setItem(row, 4, ReadOnlyTableWidgetItem(address))
                
                table._save_row_data(row)
            
            table.blockSignals(False)
            print(f"Tabel geüpdatet met {table.rowCount()} rijen")
            
        except Exception as e:
            print(f"❌ Fout bij updaten tabel: {e}")
            import traceback
            traceback.print_exc()

    def toggle_force_mode(self, checked):
        """Toggle force mode on/off"""
        self.tableWidget_IO.set_force_mode(checked)
        
        if checked:
            print("Force mode ENABLED - Right-click signals to force values")
        else:
            print("Force mode DISABLED")
            
    def update_connection_status_icon(self):
        """Update connection status icon"""
        try:
            self.Label_connectStatus.setText("")

            current_dir = Path(__file__).parent
            
            if self.validPlcConnection:
                icon_path = current_dir / "media" / "icon" / "status_ok.svg"
            else:
                icon_path = current_dir / "media" / "icon" / "status_nok.svg"
            
            if icon_path.exists():
                from PyQt5.QtGui import QPixmap
                pixmap = QPixmap(str(icon_path))
                self.Label_connectStatus.setPixmap(
                    pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            print(f"Kon status icon niet updaten: {e}")
    
    def on_controller_changed(self):
        """Callback wanneer controller dropdown wijzigt"""
        new_controller = self.controlerDropDown.currentText()
        self.vat_widget.controler = new_controller
        
        # Update main configuration if available
        if hasattr(self, 'mainConfig') and self.mainConfig:
            self.mainConfig.plcProtocol = new_controller
            
            # Set control mode based on controller
            if new_controller == "GUI":
                self.mainConfig.plcGuiControl = "gui"
                # Disable connect button in GUI mode
                try:
                    self.pushButton_connect.setEnabled(False)
                    print("🔒 Connect button disabled (GUI mode)")
                except:
                    pass
            else:
                self.mainConfig.plcGuiControl = "plc"
                # Enable connect button in PLC mode
                try:
                    self.pushButton_connect.setEnabled(True)
                    print("🔓 Connect button enabled (PLC mode)")
                except:
                    pass
            
            # Disconnect PLC if switching to GUI mode
            if new_controller == "GUI" and self.validPlcConnection:
                if hasattr(self, 'plc') and self.plc:
                    try:
                        self.plc.disconnect()
                        print("🔌 Disconnected: Switched to GUI mode")
                    except:
                        pass
                self.validPlcConnection = False
                self.plc = None
                self.update_connection_status_icon()
                # Untoggle connect button
                try:
                    self.pushButton_connect.blockSignals(True)
                    self.pushButton_connect.setChecked(False)
                    self.pushButton_connect.blockSignals(False)
                except:
                    pass
        
        self.vat_widget.rebuild()
            
    def on_connect_toggled(self, checked):
        """Handle connect button press - trigger connection attempt"""
        if not self.mainConfig:
            print("⚠️ mainConfig not available")
            return
        
        if checked:
            # User clicked connect
            print(f"🔌 Starting connection to {self.mainConfig.plcIpAdress}")
            self.mainConfig.tryConnect = True
        else:
            pass

    def on_ip_changed(self, text):
        """Update IP address met throttling - wacht 500ms voordat disconnect wordt getriggerd"""
        if not self.mainConfig:
            return
        
        # Update IP in config meteen
        self.mainConfig.plcIpAdress = text
        
        # Sla pending IP op en reset timer
        self.pending_ip = text
        self.ip_change_timer.stop()
        self.ip_change_timer.start(500)

    def _apply_ip_change(self):
        """Voer disconnect uit na throttle delay"""
        if not self.pending_ip:
            return
        
        # Reset connection alleen als er een actieve verbinding is
        if self.validPlcConnection and hasattr(self, 'plc') and self.plc:
            try:
                if self.plc.isConnected():
                    self.plc.disconnect()
                    print(f"🔌 Verbinding verbroken: IP gewijzigd naar {self.pending_ip}")
            except Exception as e:
                print(f"Fout bij disconnect: {e}")
            
            # Update status
            self.validPlcConnection = False
            self.plc = None
            
            # Untoggle connect button
            try:
                self.pushButton_connect.blockSignals(True)
                self.pushButton_connect.setChecked(False)
                self.pushButton_connect.blockSignals(False)
            except AttributeError:
                pass
            
            # Update UI
            self.update_connection_status_icon()
        
        self.pending_ip = None

    def start_simulation(self):
        """Start de simulatie"""
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.simRunning = True
        print("Simulation STARTED")

    def stop_simulation(self):
        """Stop de simulatie"""
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.simRunning = False
        print("Simulation STOPPED")

    def toggle_simulation(self, checked):
        """Toggle simulatie aan/uit met visuele feedback"""
        if checked:
            self.start_simulation()
            # Update button appearance voor STOP
            self.pushButton_startSimulatie.setText("STOP SIMULATIE")
            self.pushButton_startSimulatie.setStyleSheet("""
                QPushButton {
                    background-color: #FF4444;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #CC0000;
                }
            """)
        else:
            self.stop_simulation()
            # Update button appearance voor START
            self.pushButton_startSimulatie.setText("START SIMULATIE")
            self.pushButton_startSimulatie.setStyleSheet("""
                QPushButton {
                    background-color: #44FF44;
                    color: black;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #00CC00;
                }
            """)

# =============================================================================
# Main Application Entry Point
# =============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    current_dir = Path(__file__).parent
    gui_common_dir = current_dir.parent / "guiCommon"  # src/guiCommon  
    style_file = gui_common_dir / "style.qss"

    if os.path.exists(style_file):
        try:
            with open(style_file, "r") as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            print(f"Kon stylesheet niet laden: {e}")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())