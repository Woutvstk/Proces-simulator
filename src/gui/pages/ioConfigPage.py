# ioConfigPage.py - I/O Configuration Page
# Handles:
# - Custom table and tree widgets (drag & drop)
# - IOScreen class for I/O management
# - Load/Save I/O configuration
# - Force mode for testing
# - Byte offset management
# - Real-time I/O status display

import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QMenu, QAction, QApplication, QInputDialog, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag, QColor

logger = logging.getLogger(__name__)


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
            
            if signal_name not in self.signal_data:
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
        self.forced_rows = {}
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
        """Callback when a cell changes - update address or name"""
        row = item.row()
        col = item.column()
        
        # Handle name changes (column 0)
        if col == 0:
            old_name = self.row_data.get(row, {}).get(0, "")
            # Validate name: no empty, trim whitespace
            name = item.text().strip()
            if not name:
                # Restore previous name if empty
                if row in self.row_data and 'name' in self.row_data[row]:
                    self.blockSignals(True)
                    item.setText(self.row_data[row]['name'])
                    self.blockSignals(False)
                return
            
            # Save the name change
            self._save_row_data(row)
            # Mark IO configuration as dirty
            if hasattr(self, 'parent') and hasattr(self.parent(), '_io_config_dirty'):
                self.parent()._io_config_dirty = True
            # Propagate rename to main window so labels/tree stay in sync
            try:
                mw = getattr(self, 'io_screen', None).main_window if getattr(self, 'io_screen', None) else None
                if mw and hasattr(mw, "handle_io_signal_rename"):
                    # Use old name as canonical fallback; mixin will add alias
                    mw.handle_io_signal_rename(old_name, old_name, name)
            except Exception:
                pass
            return
        
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
            # Mark IO configuration as dirty in main window
            try:
                if self.io_screen and hasattr(self.io_screen, 'main_window') and hasattr(self.io_screen.main_window, '_mark_io_dirty'):
                    self.io_screen.main_window._mark_io_dirty()
            except Exception:
                pass
            
        except ValueError:
            pass # Removed print
    
    def handle_sort_click(self, logical_index):
        """Manual sorting - toggle asc/desc"""
        current_order = self.sort_order.get(logical_index, None)
        next_order = 'desc' if current_order == 'asc' else 'asc'
        
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

    def mouseDoubleClickEvent(self, event):
        """Double-click on status column to show force menu"""
        item = self.itemAt(event.pos())
        
        if not item or item.column() != 5:
            super().mouseDoubleClickEvent(event)
            return
        
        if not self.force_enabled:
            super().mouseDoubleClickEvent(event)
            return
        
        row = item.row()
        
        name_item = self.item(row, 0)
        type_item = self.item(row, 1)
        if not name_item or not name_item.text() or not type_item:
            super().mouseDoubleClickEvent(event)
            return
        
        signal_name = name_item.text()
        data_type = type_item.text()
        
        self.show_force_menu(row, signal_name, data_type, event.globalPos())
        event.accept()

    def show_force_menu(self, row, signal_name, data_type, position):
        """Show force menu at given position"""
        menu = QMenu(self)
        
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                color: black;
                border: 1px solid #cccccc;
            }
            QMenu::item {
                color: black;
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QMenu::item:hover {
                background-color: #e5f1fb;
                color: black;
            }
        """)
        
        if row in self.forced_rows:
            remove_action = QAction(f"[U] Remove Force from '{signal_name}'", self)
            remove_action.triggered.connect(lambda: self.remove_force(row))
            menu.addAction(remove_action)
        else:
            if data_type == 'bool':
                force_true = QAction(f"[F] Force '{signal_name}' = TRUE", self)
                force_true.triggered.connect(lambda: self.apply_force(row, True))
                menu.addAction(force_true)
                
                force_false = QAction(f"[F] Force '{signal_name}' = FALSE", self)
                force_false.triggered.connect(lambda: self.apply_force(row, False))
                menu.addAction(force_false)
            else:
                force_value = QAction(f"[F] Force '{signal_name}' to value...", self)
                force_value.triggered.connect(lambda: self.apply_force_analog(row, signal_name))
                menu.addAction(force_value)
        
        menu.exec_(position)
    
    def manual_sort(self, column, order):
        """Sort rows manually"""
        rows_data = []
        for row in range(self.rowCount()):
            row_content = {}
            for col in range(self.columnCount()):
                item = self.item(row, col)
                row_content[col] = item.text() if item else ""
            rows_data.append(row_content)
        
        def parse_address(addr):
            """Parse an address string (e.g., 'I0.5', 'IW10', 'Q2.3') into sortable components.
            Returns: (prefix_char, number, bit_or_empty)
            Examples: 'I0.5' -> ('I', 0, 5), 'IW10' -> ('I', 10, -1), 'Q2' -> ('Q', 2, -1)
            """
            if not addr:
                return ('Z', float('inf'), -1)  # Sort empty to end
            
            addr = addr.strip()
            # Try to match patterns like I0.5, IW10, Q2.3, etc.
            import re
            
            # Pattern 1: Digital address with bit (I0.5, Q2.3, etc.)
            match = re.match(r'^([DIQA])(\d+)\.(\d+)$', addr)
            if match:
                prefix, byte_num, bit_num = match.groups()
                return (prefix, int(byte_num), int(bit_num))
            
            # Pattern 2: Word address (IW10, QW5, AW20, etc.)
            match = re.match(r'^([DIQA])W(\d+)$', addr)
            if match:
                prefix, word_num = match.groups()
                return (prefix, int(word_num), -1)  # -1 indicates word, not bit
            
            # Pattern 3: Just byte number (I0, Q2, etc.)
            match = re.match(r'^([DIQA])(\d+)$', addr)
            if match:
                prefix, byte_num = match.groups()
                return (prefix, int(byte_num), -1)
            
            # Fallback: treat as string
            return (addr[0] if addr else 'Z', float('inf'), -1)
        
        def sort_key(row_dict):
            val = row_dict.get(column, "")
            if not val:
                return (1, "", 0, -1)  # Empty rows sort last
            
            # Try numeric sort first (for columns 2, 3 - byte/bit numbers)
            try:
                num_val = float(val)
                return (0, "", num_val, -1)
            except (ValueError, TypeError):
                pass
            
            # For address column (column 4), use smart address parsing
            if column == 4:
                prefix, num, bit = parse_address(val)
                return (0, prefix, num, bit)
            
            # Otherwise treat as string
            return (0, "", float('inf'), val)
        
        rows_data.sort(key=sort_key, reverse=False)
        
        if order == 'desc':
            non_empty = [r for r in rows_data if r.get(column, "")]
            empty = [r for r in rows_data if not r.get(column, "")]
            rows_data = list(reversed(non_empty)) + empty
        
        self.blockSignals(True)
        for display_row, row_content in enumerate(rows_data):
            for col in range(self.columnCount()):
                text = row_content.get(col, "")
                # Column 0 (name) and columns 2,3 (byte/bit) are editable
                if col in [0, 2, 3]:
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
            if row in self.forced_rows:
                del self.forced_rows[row]  # Also clear force when clearing data
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
                        except Exception:
                            signal_data = None
                    
                    self.blockSignals(True)
                    self.setItem(row, 0, EditableTableWidgetItem(dropped_text))
                    
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
                        # Always create a status item with blue background (default display color)
                        status_text = signal_data.get('status', 'FALSE')
                        status_item = ReadOnlyTableWidgetItem(status_text)
                        status_item.setBackground(QColor(200, 230, 245))  # Blue
                        self.setItem(row, 5, status_item)
                        try:
                            if data_type == 'bool':
                                value = status_text.strip().upper() == 'TRUE'
                            else:
                                value = int(status_text)
                        except Exception:
                            value = 0
                        self.update_status_column(row, value)
                        # Guarantee color even if update_status_column replaced the item
                        status_item = self.item(row, 5)
                        if status_item:
                            status_item.setBackground(QColor(200, 230, 245))  # Blue
                        if 'description' in signal_data:
                            self.setItem(row, 6, ReadOnlyTableWidgetItem(signal_data['description']))
                        if 'range' in signal_data:
                            self.setItem(row, 7, ReadOnlyTableWidgetItem(signal_data['range']))
                        self._save_row_data(row)
                    else:
                        # No signal_data (e.g., plain text) – still ensure status column gets default blue
                        data_type_item = self.item(row, 1)
                        data_type = data_type_item.text() if data_type_item else 'bool'
                        self.update_status_column(row, False if data_type == 'bool' else 0)
                        status_item = self.item(row, 5)
                        if status_item:
                            status_item.setBackground(QColor(200, 230, 245))  # Blue
                        self._save_row_data(row)
                    
                    self.blockSignals(False)
                    
                    if self.io_screen:
                        self.io_screen.save_configuration()
                        # Mark IO configuration as dirty in main window
                        try:
                            if self.io_screen and hasattr(self.io_screen, 'main_window') and hasattr(self.io_screen.main_window, '_mark_io_dirty'):
                                self.io_screen.main_window._mark_io_dirty()
                        except Exception:
                            pass
                    
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
            # The calling function clear_all_forces() handles clearing of forced_rows and colors.
            # We only clear forced_rows here if it hasn't been handled already (e.g. if set_force_mode is called directly with False)
            # The clear_all_forces logic in IOConfigMixin is more robust for external events (like connection).
            # Keeping the original logic here for completeness.
            for row in list(self.forced_rows.keys()):
                self.remove_force(row)


    def apply_force(self, row, value):
        """Apply force to a signal"""
        self.forced_rows[row] = {"value": value}
        
        # Only highlight the Status cell (column 5), not the entire row
        item = self.item(row, 5)
        if item:
            item.setBackground(Qt.yellow)

    def apply_force_analog(self, row, signal_name):
        """Apply force to an analog signal with dialog"""
        max_value = 27648
        if self.io_screen and hasattr(self.io_screen, 'main_window'):
            main_window = self.io_screen.main_window
            if (hasattr(main_window, 'validPlcConnection') and 
                main_window.validPlcConnection and 
                hasattr(main_window, 'plc') and 
                main_window.plc):
                max_value = main_window.plc.analogMax
        
        current_value = 0
        status_item = self.item(row, 5)
        if status_item and status_item.text():
            try:
                text = status_item.text().replace("[F]", "").strip()
                current_value = int(text)
            except ValueError:
                current_value = 0
        
        value, ok = QInputDialog.getInt(
            self,
            "Force Analog Value",
            f"Enter value for '{signal_name}':\n(Range: 0 - {max_value})",
            current_value,
            0,
            max_value,
            1
        )
        
        if ok:
            self.apply_force(row, value)

    def remove_force(self, row):
        """Remove force from a signal"""
        if row in self.forced_rows:
            del self.forced_rows[row]
            
            # Only reset the Status cell (column 5)
            item = self.item(row, 5)
            if item:
                # Restore green if force mode is still enabled, blue if disabled
                if self.force_enabled:
                    item.setBackground(QColor(200, 255, 200))  # Light green
                else:
                    item.setBackground(QColor(200, 230, 245))  # Blue

    def get_forced_value(self, row):
        """Get forced value for a row, or None if not forced"""
        if row in self.forced_rows:
            return self.forced_rows[row]["value"]
        return None

    def is_row_forced(self, row):
        """Check if a row is currently forced"""
        return row in self.forced_rows

    def update_status_column(self, row, value):
        """Update the status column with visual feedback"""
        status_item = self.item(row, 5)
        type_item = self.item(row, 1)
        
        if not type_item:
            return
        
        data_type = type_item.text()
        
        if data_type == 'bool':
            display_text = "TRUE" if value else "FALSE"
        elif data_type in ['int', 'word']:
            display_text = str(int(value))
        else:
            display_text = str(value)
        
        is_forced = self.is_row_forced(row)
        if is_forced:
            display_text = f"[F] {display_text}"  # Lock icon instead of [LOCKED]
        
        if status_item:
            status_item.setText(display_text)
            
            if is_forced:
                status_item.setBackground(Qt.yellow)
            elif self.force_enabled:
                # In force mode but not forced - use green to show available for forcing
                status_item.setBackground(QColor(200, 255, 200))  # Light green
            else:
                # Normal display - use blue
                status_item.setBackground(QColor(200, 230, 245))
        else:
            new_item = ReadOnlyTableWidgetItem(display_text)
            if is_forced:
                new_item.setBackground(Qt.yellow)
            elif self.force_enabled:
                new_item.setBackground(QColor(200, 255, 200))  # Light green
            else:
                new_item.setBackground(QColor(200, 230, 245))  # Blue
            self.setItem(row, 5, new_item)



"""
ioConfigPage.py - I/O Configuration Page
Handles:
- Custom table and tree widgets (drag & drop)
- IOScreen class for I/O management
- Load/Save I/O configuration
- Force mode for testing
- Byte offset management
- Real-time I/O status display
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QMenu, QAction, QApplication, QInputDialog, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag, QColor

# Import custom widgets from separate file
# NOTE: The original file had a self-import issue. Since we are merging/cleaning,
# we comment out the import that refers to a non-existent 'customWidgets' file
# and assume the widgets defined above are used.
# from mainGui.customWidgets import (
#     DraggableTreeWidget, DroppableTableWidget,
#     EditableTableWidgetItem, ReadOnlyTableWidgetItem
# )


# =============================================================================
# IOScreen class for IO configuration
# =============================================================================
class IOScreen:
    def __init__(self, main_window):
        """IOScreen class that writes to the MainWindow"""
        self.main_window = main_window
        
        self.byte_offsets = {
            'BoolInput': 0,
            'BoolOutput': 0,
            'DWORDInput': 2,
            'DWORDOutput': 2
        }
        
        self.config_file = Path("io_config.json")
        self.loading_config = False  # Flag to prevent auto-resolution during config loads

    def get_offset(self, offset_type):
        """Get a byte offset"""
        return self.byte_offsets.get(offset_type, 0)
    
    @property
    def offsets(self):
        """Alias for byte_offsets"""
        return self.byte_offsets
    
    def set_offset(self, offset_type, value):
        """Set a byte offset"""
        self.byte_offsets[offset_type] = value
    
    def is_address_in_use(self, address, exclude_row=None):
        """Check if an address is already in use"""
        table = self.main_window.tableWidget_IO
        
        for row in range(table.rowCount()):
            if exclude_row is not None and row == exclude_row:
                continue
            
            addr_item = table.item(row, 4)
            if addr_item and addr_item.text() == address:
                return True, row
        
        return False, None

    def find_first_free_address(self, io_prefix, data_type, exclude_row=None):
        """Find the first available address for the given prefix and data type, respecting byte offsets"""
        table = self.main_window.tableWidget_IO
        
        # Determine the offset type and stepping based on data type and io_prefix
        if data_type == 'bool':
            offset_type = f"Bool{('Input' if io_prefix == 'I' else 'Output')}"
            step = 1
            start_byte = self.byte_offsets.get(offset_type, 0)
            max_byte = 256
            
            for byte_num in range(start_byte, max_byte, step):
                for bit_num in range(8):
                    address = f"{io_prefix}{byte_num}.{bit_num}"
                    in_use, _ = self.is_address_in_use(address, exclude_row=exclude_row)
                    if not in_use:
                        return address, byte_num, bit_num
        
        elif data_type in ['int', 'word']:
            # For WORD/DWORD, the offset is in bytes, so we need to convert to word addresses
            offset_type = f"DWORD{('Input' if io_prefix == 'I' else 'Output')}"
            byte_offset = self.byte_offsets.get(offset_type, 0)
            # Convert byte offset to word address (divide by 2 since each word is 2 bytes)
            start_byte = byte_offset
            step = 2  # WORD addresses are 2 bytes apart
            max_byte = 256
            
            for byte_num in range(start_byte, max_byte, step):
                address = f"{io_prefix}W{byte_num}"
                in_use, _ = self.is_address_in_use(address, exclude_row=exclude_row)
                if not in_use:
                    return address, byte_num, -1
        
        return None, None, None
    
    def validate_and_fix_manual_address(self, row):
        """Validate a manually entered address and resolve conflicts automatically"""
        # Don't auto-resolve during config loads - just validate
        if getattr(self, 'loading_config', False):
            table = self.main_window.tableWidget_IO
            table._save_row_data(row)
            return
        
        table = self.main_window.tableWidget_IO
        
        byte_item = table.item(row, 2)
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
            
            if data_type == 'bool':
                bit_item = table.item(row, 3)
                bit_num = int(bit_item.text()) if bit_item and bit_item.text() else 0
                proposed_address = f"{io_prefix}{byte_num}.{bit_num}"
            elif data_type in ['int', 'word']:
                proposed_address = f"{io_prefix}W{byte_num}"
            else:
                return
            
            in_use, conflict_row = self.is_address_in_use(proposed_address, exclude_row=row)
            
            if in_use and conflict_row is not None:
                # Address is in use by another tag - find first free address for conflicting tag
                table.blockSignals(True)
                
                # Get the conflicting tag's data type to find appropriate free address
                conflict_type_item = table.item(conflict_row, 1)
                conflict_type = conflict_type_item.text() if conflict_type_item else 'bool'
                conflict_signal = table.item(conflict_row, 0).text() if table.item(conflict_row, 0) else "unknown"
                
                # Find first free address for the conflicting tag
                free_addr, free_byte, free_bit = self.find_first_free_address(io_prefix, conflict_type, exclude_row=conflict_row)
                
                if free_addr:
                    # Move the conflicting tag to the free address
                    conflict_byte_item = table.item(conflict_row, 2)
                    conflict_addr_item = table.item(conflict_row, 4)
                    
                    # Update byte column (make sure it's an EditableTableWidgetItem)
                    if not isinstance(conflict_byte_item, EditableTableWidgetItem):
                        conflict_byte_item = EditableTableWidgetItem(str(free_byte))
                        table.setItem(conflict_row, 2, conflict_byte_item)
                    else:
                        conflict_byte_item.setText(str(free_byte))
                    
                    # Update bit column if bool
                    if conflict_type == 'bool' and free_bit >= 0:
                        conflict_bit_item = table.item(conflict_row, 3)
                        if not isinstance(conflict_bit_item, EditableTableWidgetItem):
                            conflict_bit_item = EditableTableWidgetItem(str(free_bit))
                            table.setItem(conflict_row, 3, conflict_bit_item)
                        else:
                            conflict_bit_item.setText(str(free_bit))
                    
                    # Update address column (make sure it's a ReadOnlyTableWidgetItem)
                    if not isinstance(conflict_addr_item, ReadOnlyTableWidgetItem):
                        conflict_addr_item = ReadOnlyTableWidgetItem(free_addr)
                        table.setItem(conflict_row, 4, conflict_addr_item)
                    else:
                        conflict_addr_item.setText(free_addr)
                    
                    # Update current row's address to the proposed address (which is now free)
                    if not isinstance(addr_item, ReadOnlyTableWidgetItem):
                        addr_item = ReadOnlyTableWidgetItem(proposed_address)
                        table.setItem(row, 4, addr_item)
                    else:
                        addr_item.setText(proposed_address)
                    
                    # Save both rows
                    table._save_row_data(conflict_row)
                    table._save_row_data(row)
                    
                    table.blockSignals(False)
                    self.save_configuration()
                    
                    # Mark config as dirty to trigger reload
                    try:
                        if hasattr(self.main_window, '_io_config_dirty'):
                            self.main_window._io_config_dirty = True
                    except:
                        pass
                    
                    print(f"[AUTO-RESOLVE] Moved '{conflict_signal}' from {proposed_address} to {free_addr}")
                else:
                    # No free address found, revert the change
                    old_address = old_row_data.get(4, "")
                    table.blockSignals(True)
                    if addr_item:
                        addr_item.setText(old_address)
                    table.blockSignals(False)
            else:
                # No conflict, just save the new address
                table._save_row_data(row)
                self.save_configuration()
            
        except (ValueError, AttributeError) as e:
            pass
    
    def save_configuration(self):
        """Save the current IO configuration in JSON"""
        root_dir = Path(__file__).resolve().parent
        tank_dir = root_dir.parent 
        tank_dir.mkdir(exist_ok=True)

        self.config_file = tank_dir / "IO" / "IO_configuration.json"
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
            pass # Removed print
    
    def readdress_all_signals(self):
        """Re-address all signals"""
        table = self.main_window.tableWidget_IO
        table.blockSignals(True)
        
        signals_to_readdress = []
        for row in range(table.rowCount()):
            name_item = table.item(row, 0)
            type_item = table.item(row, 1)
            
            if name_item and name_item.text() and type_item and type_item.text():
                addr_item = table.item(row, 4)
                if addr_item and addr_item.text():
                    signals_to_readdress.append({
                        'row': row,
                        'type': type_item.text(),
                        'io_prefix': addr_item.text()[0]
                    })
        
        # Clear existing address info to free up space
        for signal in signals_to_readdress:
            row = signal['row']
            table.setItem(row, 2, EditableTableWidgetItem(""))
            table.setItem(row, 3, EditableTableWidgetItem(""))
            table.setItem(row, 4, ReadOnlyTableWidgetItem(""))
        
        # Re-address using the current offsets and used addresses
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
        self.save_configuration()

    def reset_offsets_to_default(self):
        """Reset all offsets to defaults"""
        self.byte_offsets = {
            'BoolInput': 0,
            'BoolOutput': 0,
            'DWORDInput': 2,
            'DWORDOutput': 2
        }
        self.readdress_all_signals()


# =============================================================================
# IOConfigMixin - All I/O config functionality
# =============================================================================
class IOConfigMixin:
    """
    Mixin class for I/O configuration functionality
    Is combined with MainWindow via multiple inheritance
    """
    
    def init_io_config_page(self):
        """Initialize all I/O config page components"""
        self.io_screen = IOScreen(self)
        # Dirty-state flags for IO configuration changes
        self._io_config_dirty = False
        self._io_dirty_prompt_shown = False
        
        self._replace_table_widget()
        self._replace_tree_widget()
        self._connect_offset_buttons()
        self._connect_io_buttons()
        self._connect_force_button()
        self._init_force_state_label()
        
        # Don't load tree at startup - only load when simulation is started
        # Tree will be loaded when start_simulation() is called
    
    def _replace_table_widget(self):
        """Replace standard table widget with custom DroppableTableWidget"""
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
            pass # Removed print
    
    def _replace_tree_widget(self):
        """Replace tree widget with draggable version"""
        try:
            old_tree = self.treeWidget_IO
            parent = old_tree.parent()
            layout = old_tree.parent().layout()
            old_tree.hide()
            
            self.treeWidget_IO = DraggableTreeWidget(parent)
            self.treeWidget_IO.setHeaderLabel("IN/OUTPUTS")
            self.treeWidget_IO.setMinimumSize(0, 0)
            self.treeWidget_IO.setMaximumWidth(300)
            
            if layout:
                layout.replaceWidget(old_tree, self.treeWidget_IO)
                old_tree.deleteLater()
        except Exception as e:
            pass # Removed print
    
    def _connect_offset_buttons(self):
        """Connect offset buttons"""
        try:
            self.pushButton_ApplyOffset.clicked.connect(self.apply_offsets)
            self.pushButton_DefaultOffset.clicked.connect(self.default_offsets)
        except AttributeError:
            pass # Removed print
    
    def _connect_io_buttons(self):
        """Connect I/O save/load buttons"""
        try:
            self.pushButton_SaveIO.clicked.connect(self.save_io_configuration)
            self.pushButton_LoadIO.clicked.connect(self.load_io_configuration)
            self.pushButton_ReloadConfig.clicked.connect(self.reload_io_config)
            self.QPushButtonLoadAllTags.clicked.connect(self.load_all_tags_to_table)
        except AttributeError:
            pass # Removed print
    
    def _connect_force_button(self):
        """Connect force button"""
        try:
            self.pushButton_AllowForce.toggled.connect(self.toggle_force_mode)
            self.pushButton_AllowForce.setCheckable(True)
        except AttributeError:
            pass # Removed print
    
    def _init_force_state_label(self):
        """Initialize the force state label on startup"""
        if hasattr(self, 'Label_Forcestate'):
            self.Label_Forcestate.setText("● Forcing OFF")
            self.Label_Forcestate.setStyleSheet("""QLabel {
    background-color: #f5f5f5;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 8px;
    color: #333333;
}""")
    
    def load_io_tree(self):
        """Load IO signals from XML file based on active simulation"""
        if not hasattr(self, 'treeWidget_IO') or self.treeWidget_IO is None:
            logger.warning("treeWidget_IO not initialized")
            return
        
        # Clear existing tree
        self.treeWidget_IO.clear()
        
        # Get active simulation name from simulationManager
        active_sim = None
        try:
            if hasattr(self, 'mainConfig') and self.mainConfig and hasattr(self.mainConfig, 'simulationManager'):
                active_sim = self.mainConfig.simulationManager.get_active_simulation_name()
            else:
                logger.warning("mainConfig or simulationManager not available")
                return
        except Exception as e:
            logger.error(f"Error getting active simulation: {e}")
            return
        
        # Determine which XML file to load
        current_dir = Path(__file__).parent
        io_dir = current_dir.parent.parent / "IO"  # Go from pages -> gui -> src -> IO
        
        xml_file = None
        if active_sim == "PIDtankValve":
            xml_file = io_dir / "IO_treeList_PIDtankValve.xml"
        elif active_sim == "conveyor":
            xml_file = io_dir / "IO_treeList_conveyor.xml"
        
        # If no active simulation or file doesn't exist, don't load anything
        if xml_file is None:
            logger.warning(f"No XML file mapping for simulation: {active_sim}")
            return
        
        if not xml_file.exists():
            logger.warning(f"IO tree XML file not found: {xml_file}")
            return
        
        try:
            logger.info(f"Loading IO tree from: {xml_file}")
            tree = ET.parse(str(xml_file))
            root = tree.getroot()
            
            # Load simulation-specific signals (original format)
            pidtank = root.find('PIDtankValve')
            if pidtank is not None:
                self._load_simulation_signals(pidtank, "PIDtankValve")
            
            # Load split PIDtankValve sections (sensors and controls)
            pidtank_sensors = root.find('PIDtankValve_Sensors_Actuators')
            if pidtank_sensors is not None:
                self._load_simulation_signals(pidtank_sensors, "PIDtankValve_Sensors_Actuators")
            
            pidtank_controls = root.find('PIDtankValve_PLC_Controls')
            if pidtank_controls is not None:
                self._load_simulation_signals(pidtank_controls, "PIDtankValve_PLC_Controls")
            
            conveyor = root.find('ConveyorSim')
            if conveyor is not None:
                self._load_simulation_signals(conveyor, "ConveyorSim")
            
            # Legacy support for old format
            tanksim = root.find('TankSim')
            if tanksim is not None:
                self._load_tanksim_signals(tanksim)
            
            # Load GeneralControls last
            general = root.find('GeneralControls')
            if general is not None:
                self._load_generalcontrols_signals(general)
            
            self.treeWidget_IO.expandAll()
            logger.info(f"IO tree loaded successfully from {active_sim}")

            # Refresh labels if custom names exist
            try:
                if hasattr(self, '_refresh_general_control_labels_from_mapping'):
                    self._refresh_general_control_labels_from_mapping()
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Error loading IO tree: {e}", exc_info=True)
    
    def _load_tanksim_signals(self, tanksim):
        """Load TankSim signals"""
        if not hasattr(self, 'treeWidget_IO') or self.treeWidget_IO is None:
            return
        
        tanksim_item = QTreeWidgetItem(self.treeWidget_IO, ["TankSim"])
        
        inputs_root = tanksim.find('Inputs')
        if inputs_root is not None:
            inputs_item = QTreeWidgetItem(tanksim_item, ["Inputs"])
            self._load_signal_category(inputs_root, inputs_item)
        
        outputs_root = tanksim.find('Outputs')
        if outputs_root is not None:
            outputs_item = QTreeWidgetItem(tanksim_item, ["Outputs"])
            self._load_signal_category(outputs_root, outputs_item)
    
    def _load_simulation_signals(self, sim_element, sim_name):
        """Load simulation-specific signals (generic for any simulation)"""
        if not hasattr(self, 'treeWidget_IO') or self.treeWidget_IO is None:
            return
        
        sim_item = QTreeWidgetItem(self.treeWidget_IO, [sim_name])
        
        inputs_root = sim_element.find('Inputs')
        if inputs_root is not None:
            inputs_item = QTreeWidgetItem(sim_item, ["Inputs"])
            self._load_signal_category(inputs_root, inputs_item)
        
        outputs_root = sim_element.find('Outputs')
        if outputs_root is not None:
            outputs_item = QTreeWidgetItem(sim_item, ["Outputs"])
            self._load_signal_category(outputs_root, outputs_item)
    
    def _load_conveyorsim_signals(self, conveyorsim):
        """Load ConveyorSim signals"""
        if not hasattr(self, 'treeWidget_IO') or self.treeWidget_IO is None:
            return
        
        conveyorsim_item = QTreeWidgetItem(self.treeWidget_IO, ["ConveyorSim"])
        note = conveyorsim.find('Note')
        if note is not None and note.text:
            QTreeWidgetItem(conveyorsim_item, [note.text.strip()])

    def _load_generalcontrols_signals(self, general):
        """Load General Controls signals"""
        if not hasattr(self, 'treeWidget_IO') or self.treeWidget_IO is None:
            return
        
        general_item = QTreeWidgetItem(self.treeWidget_IO, ["GeneralControls"])

        inputs_root = general.find('Inputs')
        if inputs_root is not None:
            inputs_item = QTreeWidgetItem(general_item, ["Inputs"])
            self._load_signal_category(inputs_root, inputs_item)

        outputs_root = general.find('Outputs')
        if outputs_root is not None:
            outputs_item = QTreeWidgetItem(general_item, ["Outputs"])
            self._load_signal_category(outputs_root, outputs_item)
    
    def _load_signal_category(self, category_root, parent_item):
        """Load a category (Digital/Analog) of signals"""
        if not hasattr(self, 'treeWidget_IO') or self.treeWidget_IO is None:
            return
        
        for signal_type in ['Digital', 'Analog']:
            signals = category_root.find(signal_type)
            if signals is not None:
                type_item = QTreeWidgetItem(parent_item, [signal_type])
                for signal in signals.findall('Signal'):
                    signal_name = signal.text.strip() if signal.text else "Unknown"
                    QTreeWidgetItem(type_item, [signal_name])
                    
                    signal_info = {
                        'type': signal.get('type', 'bool' if signal_type == 'Digital' else 'int'),
                        'io_prefix': signal.get('io_prefix', 'I'),
                        'status': signal.get('status', ''),
                        'description': signal.get('description', ''),
                        'range': signal.get('range', '')
                    }
                    # Ensure signal_data exists
                    if hasattr(self.treeWidget_IO, 'signal_data'):
                        self.treeWidget_IO.signal_data[signal_name] = signal_info
    
    def load_all_tags_to_table(self):
        """Load all draggable tags from tree into table"""
        if not hasattr(self, 'treeWidget_IO') or self.treeWidget_IO is None:
            QMessageBox.warning(self, "Error", "No tags available to load")
            return
        
        if not hasattr(self, 'tableWidget_IO') or self.tableWidget_IO is None:
            QMessageBox.warning(self, "Error", "Table not initialized")
            return
        
        # Update byte offsets from UI before loading tags
        try:
            bool_input = int(self.QLineEdit_BoolInput.text())
            bool_output = int(self.QLineEdit_BoolOutput.text())
            dword_input = int(self.QLineEdit_DWORDInput.text())
            dword_output = int(self.QLineEdit_DWORDOutput.text())
            
            self.io_screen.byte_offsets = {
                'BoolInput': bool_input,
                'BoolOutput': bool_output,
                'DWORDInput': dword_input,
                'DWORDOutput': dword_output
            }
        except (ValueError, AttributeError):
            pass
        
        # Prevent auto-conflict resolution while loading all tags
        self.io_screen.loading_config = True
        
        try:
            # Get all signal items from the tree (leaf nodes only)
            all_signals = []
            
            def collect_signals(item):
                """Recursively collect all leaf items (signals)"""
                if item.childCount() == 0:
                    # This is a leaf node (actual signal)
                    signal_name = item.text(0)
                    # Skip category labels and empty items
                    if signal_name and signal_name not in ['Inputs', 'Outputs', 'Digital', 'Analog', 'TankSim', 'ConveyorSim', 'GeneralControls']:
                        # Get signal data if available
                        signal_data = None
                        if hasattr(self.treeWidget_IO, 'signal_data') and signal_name in self.treeWidget_IO.signal_data:
                            signal_data = self.treeWidget_IO.signal_data[signal_name].copy()
                        all_signals.append((signal_name, signal_data))
                else:
                    # Recurse through children
                    for i in range(item.childCount()):
                        collect_signals(item.child(i))
            
            # Start from root
            root = self.treeWidget_IO.invisibleRootItem()
            for i in range(root.childCount()):
                collect_signals(root.child(i))

            # Deduplicate by name to avoid blank rows when duplicates exist in the tree
            seen = set()
            dedup_signals = []
            for name, sd in all_signals:
                if name in seen:
                    continue
                seen.add(name)
                dedup_signals.append((name, sd))
            all_signals = dedup_signals
            
            if not all_signals:
                QMessageBox.information(self, "No Tags", "No tags found to load")
                return
            
            # Replace table contents from scratch to avoid leading empty rows
            table = self.tableWidget_IO
            table.blockSignals(True)
            table.setRowCount(0)
            table.setRowCount(len(all_signals))

            # Add all signals to table
            for current_row, (signal_name, signal_data) in enumerate(all_signals):
                # Remove duplicates first (defensive if table had prior entries)
                table.remove_duplicate_signals(signal_name, exclude_row=current_row)

                # Set signal name
                table.setItem(current_row, 0, EditableTableWidgetItem(signal_name))

                # If signal_data is missing (shouldn't happen), fall back to a safe default
                if not signal_data:
                    signal_data = {
                        'type': 'bool',
                        'io_prefix': 'I',
                        'status': 'FALSE',
                        'description': '',
                        'range': ''
                    }

                data_type = signal_data.get('type', 'bool')
                table.setItem(current_row, 1, ReadOnlyTableWidgetItem(data_type))

                io_prefix = signal_data.get('io_prefix', 'I')
                byte_num, bit_num, full_address = table.find_free_address(io_prefix, data_type)
                table.setItem(current_row, 2, EditableTableWidgetItem(str(byte_num)))
                if bit_num is not None:
                    table.setItem(current_row, 3, EditableTableWidgetItem(str(bit_num)))
                else:
                    table.setItem(current_row, 3, EditableTableWidgetItem(""))
                table.setItem(current_row, 4, ReadOnlyTableWidgetItem(full_address))

                # Status column with blue background (default display color)
                status_text = signal_data.get('status', 'FALSE')
                status_item = ReadOnlyTableWidgetItem(status_text)
                status_item.setBackground(QColor(200, 230, 245))  # Blue
                table.setItem(current_row, 5, status_item)

                # Update status value
                try:
                    if data_type == 'bool':
                        value = status_text.strip().upper() == 'TRUE'
                    else:
                        value = int(status_text)
                except Exception:
                    value = 0
                table.update_status_column(current_row, value)

                # Ensure blue background is maintained
                status_item = table.item(current_row, 5)
                if status_item:
                    status_item.setBackground(QColor(200, 230, 245))  # Blue

                if 'description' in signal_data:
                    table.setItem(current_row, 6, ReadOnlyTableWidgetItem(signal_data['description']))
                if 'range' in signal_data:
                    table.setItem(current_row, 7, ReadOnlyTableWidgetItem(signal_data['range']))

                table._save_row_data(current_row)
            
            table.blockSignals(False)
            
            # Save configuration
            if self.io_screen:
                self.io_screen.save_configuration()
                # Mark IO configuration as dirty
                try:
                    if hasattr(self, '_mark_io_dirty'):
                        self._mark_io_dirty()
                except Exception:
                    pass
            
            QMessageBox.information(self, "Success", f"Loaded {len(all_signals)} tags into table")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load tags: {str(e)}")
            logger.error(f"Error loading all tags: {e}", exc_info=True)
        finally:
            # Re-enable auto-conflict resolution after loading
            self.io_screen.loading_config = False
    
    def apply_offsets(self):
        """Apply offset values"""
        try:
            new_bool_input = int(self.QLineEdit_BoolInput.text())
            new_bool_output = int(self.QLineEdit_BoolOutput.text())
            new_dword_input = int(self.QLineEdit_DWORDInput.text())
            new_dword_output = int(self.QLineEdit_DWORDOutput.text())
            
            new_bool_input = max(0, min(255, new_bool_input))
            new_bool_output = max(0, min(255, new_bool_output))
            new_dword_input = max(0, min(254, new_dword_input))
            new_dword_output = max(0, min(254, new_dword_output))
            
            if new_dword_input % 2 != 0:
                new_dword_input -= 1
            if new_dword_output % 2 != 0:
                new_dword_output -= 1
            
            self.QLineEdit_BoolInput.setText(str(new_bool_input))
            self.QLineEdit_BoolOutput.setText(str(new_bool_output))
            self.QLineEdit_DWORDInput.setText(str(new_dword_input))
            self.QLineEdit_DWORDOutput.setText(str(new_dword_output))
            
            self.io_screen.byte_offsets = {
                'BoolInput': new_bool_input,
                'BoolOutput': new_bool_output,
                'DWORDInput': new_dword_input,
                'DWORDOutput': new_dword_output
            }
            
            self.io_screen.readdress_all_signals()
            # Mark dirty due to offset changes
            try:
                self._mark_io_dirty()
            except Exception:
                pass
                
        except Exception as e:
            pass # Removed print

    def default_offsets(self):
        """Reset offsets to defaults"""
        self.QLineEdit_BoolInput.setText("0")
        self.QLineEdit_BoolOutput.setText("0")
        self.QLineEdit_DWORDInput.setText("4")
        self.QLineEdit_DWORDOutput.setText("4")
        
        self.io_screen.reset_offsets_to_default()
        # Mark dirty due to offset changes
        try:
            self._mark_io_dirty()
        except Exception:
            pass

    def save_io_configuration(self):
        """Save IO configuration"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save IO Configuration", "io_configuration.json",
                "JSON Files (*.json);;All Files (*)")
            
            if not file_path:
                return
            
            table = self.tableWidget_IO
            config_data = {
                'offsets': self.io_screen.byte_offsets.copy(),
                'signals': []
            }

            # Persist custom signal name overrides (e.g., Control/Indicator aliases)
            try:
                if hasattr(self, 'tanksim_config') and hasattr(self.tanksim_config, 'custom_signal_names'):
                    config_data['custom_signal_names'] = self.tanksim_config.custom_signal_names.copy()
            except Exception:
                pass
            
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
            
            QMessageBox.information(self, "Success", f"IO Configuration saved")
            # Saving does not activate; keep dirty so leave-prompt still warns
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")

    def load_io_configuration(self):
        """Load IO configuration"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Load IO Configuration", "",
                "JSON Files (*.json);;All Files (*)")
            
            if not file_path:
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            if 'signals' not in config_data:
                QMessageBox.warning(self, "Invalid File", "Invalid configuration")
                return

            # Restore custom signal names into mapping before applying table data
            if hasattr(self, 'tanksim_config') and 'custom_signal_names' in config_data:
                for attr, custom_name in config_data['custom_signal_names'].items():
                    # Find all existing keys pointing to this attr and add alias
                    if hasattr(self.tanksim_config, 'io_signal_mapping'):
                        for default_name, attr_name in list(self.tanksim_config.io_signal_mapping.items()):
                            if attr_name == attr:
                                self.tanksim_config.io_signal_mapping[custom_name] = attr
                                if hasattr(self.tanksim_config, 'reverse_io_mapping'):
                                    self.tanksim_config.reverse_io_mapping[attr] = custom_name
                        # Persist in config
                        if hasattr(self.tanksim_config, 'custom_signal_names'):
                            self.tanksim_config.custom_signal_names[attr] = custom_name
            
            reply = QMessageBox.question(
                self, "Confirm Load",
                f"Replace current configuration with {len(config_data['signals'])} signals?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.No:
                return
            
            # Prevent auto-conflict resolution while loading config
            self.io_screen.loading_config = True
            
            try:
                table = self.tableWidget_IO
                table.blockSignals(True)
                
                # Clear all current data
                for row in range(table.rowCount()):
                    table._clear_row_data(row)
                
                if 'offsets' in config_data:
                    self.io_screen.byte_offsets = config_data['offsets'].copy()
                    self.QLineEdit_BoolInput.setText(str(config_data['offsets'].get('BoolInput', 0)))
                    self.QLineEdit_BoolOutput.setText(str(config_data['offsets'].get('BoolOutput', 0)))
                    self.QLineEdit_DWORDInput.setText(str(config_data['offsets'].get('DWORDInput', 2)))
                    self.QLineEdit_DWORDOutput.setText(str(config_data['offsets'].get('DWORDOutput', 2)))
                
                for idx, signal in enumerate(config_data['signals']):
                    if idx >= table.rowCount():
                        break
                    
                    # Column 0 (name) should be editable, all others read-only except byte/bit
                    table.setItem(idx, 0, EditableTableWidgetItem(signal.get('name', '')))
                    table.setItem(idx, 1, ReadOnlyTableWidgetItem(signal.get('type', '')))
                    table.setItem(idx, 2, EditableTableWidgetItem(signal.get('byte', '')))
                    table.setItem(idx, 3, EditableTableWidgetItem(signal.get('bit', '')))
                    table.setItem(idx, 4, ReadOnlyTableWidgetItem(signal.get('address', '')))
                    table.setItem(idx, 5, ReadOnlyTableWidgetItem(signal.get('status', '')))
                    table.setItem(idx, 6, ReadOnlyTableWidgetItem(signal.get('description', '')))
                    table.setItem(idx, 7, ReadOnlyTableWidgetItem(signal.get('range', '')))
                    table._save_row_data(idx)
                
                table.blockSignals(False)
            finally:
                # Re-enable auto-conflict resolution after loading
                self.io_screen.loading_config = False
            QMessageBox.information(self, "Success", "Configuration loaded")
            self.io_screen.save_configuration()
            # Loading does not activate; mark dirty
            try:
                self._mark_io_dirty()
            except Exception:
                pass
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load: {str(e)}")

    def reload_io_config(self, skip_confirmation=False):
        """Reload IO configuration - saves current table first, then reloads from file"""
        try:
            if not hasattr(self, 'tanksim_config') or self.tanksim_config is None:
                QMessageBox.warning(self, "Error", "TankSim config unavailable")
                return
            
            # __file__ is in src/gui/pages/ioConfigPage.py
            # .parent = src/gui/pages
            # .parent.parent = src/gui
            # .parent.parent.parent = src
            project_root = Path(__file__).resolve().parent.parent.parent
            io_config_path = project_root / "IO" / "IO_configuration.json"
            
            # Ensure IO directory exists
            io_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Skip confirmation dialog if skip_confirmation=True
            if not skip_confirmation:
                reply = QMessageBox.question(
                    self, "Confirm Activation",
                    "Activate and reload configuration?\n\n"
                    "This will:\n"
                    "1. Save current table to IO_configuration.json\n"
                    "2. Reload configuration from file\n"
                    "3. Disconnect active PLC connections if needed",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
                if reply == QMessageBox.No:
                    return
            
            # STEP 1: Save the current table to the default JSON location
            try:
                table = self.tableWidget_IO
                config_data = {
                    'offsets': self.io_screen.byte_offsets.copy(),
                    'signals': []
                }
                
                # Persist custom signal name overrides
                try:
                    if hasattr(self.tanksim_config, 'custom_signal_names'):
                        config_data['custom_signal_names'] = self.tanksim_config.custom_signal_names.copy()
                except Exception:
                    pass
                
                # Save all signals from table
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
                
                # Write to JSON file
                with open(io_config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                    
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save configuration: {str(e)}")
                return
            
            # STEP 2: Disconnect PLC if connected
            if hasattr(self, 'validPlcConnection') and self.validPlcConnection:
                if hasattr(self, 'plc') and self.plc:
                    try:
                        self.plc.disconnect()
                    except Exception:
                        pass
                
                self.validPlcConnection = False
                self.plc = None
                self.update_connection_status_icon()
                
                try:
                    self.pushButton_connect.blockSignals(True)
                    self.pushButton_connect.setChecked(False)
                    self.pushButton_connect.blockSignals(False)
                except Exception:
                    pass
            
            # STEP 3: Load config from file into main object
            self.tanksim_config.load_io_config_from_file(io_config_path)
            
            # STEP 4: Update GUI offsets from loaded config
            try:
                with open(io_config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                if 'offsets' in config_data:
                    self.io_screen.byte_offsets = config_data['offsets'].copy()
                    self.QLineEdit_BoolInput.setText(str(config_data['offsets'].get('BoolInput', 0)))
                    self.QLineEdit_BoolOutput.setText(str(config_data['offsets'].get('BoolOutput', 0)))
                    self.QLineEdit_DWORDInput.setText(str(config_data['offsets'].get('DWORDInput', 2)))
                    self.QLineEdit_DWORDOutput.setText(str(config_data['offsets'].get('DWORDOutput', 2)))
            except Exception as e:
                pass
            
            # STEP 5: Update table from reloaded config
            # Prevent auto-conflict resolution while loading config
            self.io_screen.loading_config = True
            try:
                self._update_table_from_config()
            finally:
                self.io_screen.loading_config = False
            
            # STEP 5.5: Start forced write period (500ms) to initialize all IO states
            try:
                if hasattr(self, 'mainConfig') and hasattr(self.mainConfig, 'ioHandler'):
                    self.mainConfig.ioHandler.start_force_write_period()
                    logger.info("Configuration reloaded - starting 500ms IO initialization period")
            except Exception as e:
                logger.warning(f"Could not start force write period: {e}")
            
            QMessageBox.information(self, "Success", "Configuration activated and reloaded successfully")
            # Reload activates config; clear dirty state
            try:
                self._io_config_dirty = False
            except Exception:
                pass
            
            # STEP 6: Auto-connect after successful configuration load
            try:
                # Only auto-connect if not in GUI mode
                if (hasattr(self, 'mainConfig') and self.mainConfig and 
                    self.mainConfig.plcGuiControl != "gui" and
                    hasattr(self, 'pushButton_connect') and self.pushButton_connect):
                    
                    self.pushButton_connect.blockSignals(True)
                    self.pushButton_connect.setChecked(True)
                    self.pushButton_connect.blockSignals(False)
                    
                    # Trigger the connect action
                    if hasattr(self, 'mainConfig'):
                        self.mainConfig.tryConnect = True
            except Exception as e:
                pass  # Silently fail if auto-connect fails
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to activate/reload: {str(e)}")
        
    def _reload_io_config_without_confirmation(self):
        """Reload IO configuration without showing confirmation dialog - same as reload_io_config but skips dialog"""
        
        try:
            if not hasattr(self, 'tanksim_config') or self.tanksim_config is None:
                # If tanksim_config not available here, try calling reload directly
                self.reload_io_config()
                return
            
            # __file__ is in src/gui/pages/ioConfigPage.py
            project_root = Path(__file__).resolve().parent.parent.parent
            io_config_path = project_root / "IO" / "IO_configuration.json"
            
            # Ensure IO directory exists
            io_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # STEP 1: Save the current table to the default JSON location
            try:
                table = self.tableWidget_IO
                config_data = {
                    'offsets': self.io_screen.byte_offsets.copy(),
                    'signals': []
                }
                
                # Persist custom signal name overrides
                try:
                    if hasattr(self.tanksim_config, 'custom_signal_names'):
                        config_data['custom_signal_names'] = self.tanksim_config.custom_signal_names.copy()
                except Exception:
                    pass
                
                # Save all signals from table
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
                
                # Write to JSON file
                with open(io_config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                    
            except Exception as e:
                return
            
            # STEP 2: Disconnect PLC if connected
            if hasattr(self, 'validPlcConnection') and self.validPlcConnection:
                if hasattr(self, 'plc') and self.plc:
                    try:
                        self.plc.disconnect()
                    except Exception:
                        pass
                
                self.validPlcConnection = False
                self.plc = None
                self.update_connection_status_icon()
                
                try:
                    self.pushButton_connect.blockSignals(True)
                    self.pushButton_connect.setChecked(False)
                    self.pushButton_connect.blockSignals(False)
                except Exception:
                    pass
            
            # STEP 3: Load config from file into main object
            self.tanksim_config.load_io_config_from_file(io_config_path)
            
            # STEP 4: Update GUI offsets from loaded config
            try:
                with open(io_config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                if 'offsets' in config_data:
                    self.io_screen.byte_offsets = config_data['offsets'].copy()
                    self.QLineEdit_BoolInput.setText(str(config_data['offsets'].get('BoolInput', 0)))
                    self.QLineEdit_BoolOutput.setText(str(config_data['offsets'].get('BoolOutput', 0)))
                    self.QLineEdit_DWORDInput.setText(str(config_data['offsets'].get('DWORDInput', 2)))
                    self.QLineEdit_DWORDOutput.setText(str(config_data['offsets'].get('DWORDOutput', 2)))
            except Exception as e:
                pass
            
            # STEP 5: Update table from reloaded config
            self.io_screen.loading_config = True
            try:
                self._update_table_from_config()
            finally:
                self.io_screen.loading_config = False
            
            # Clear dirty state
            try:
                self._io_config_dirty = False
            except Exception:
                pass
            
            # STEP 6: Auto-connect after successful configuration load
            try:
                if (hasattr(self, 'mainConfig') and self.mainConfig and 
                    self.mainConfig.plcGuiControl != "gui" and
                    hasattr(self, 'pushButton_connect') and self.pushButton_connect):
                    
                    self.pushButton_connect.blockSignals(True)
                    self.pushButton_connect.setChecked(True)
                    self.pushButton_connect.blockSignals(False)
                    
                    if hasattr(self, 'mainConfig'):
                        self.mainConfig.tryConnect = True
            except Exception as e:
                pass
            
        except Exception as e:
            pass
        
    def _auto_reload_io_config(self):
        """
        Automatically reload IO configuration without user confirmation.
        Called when navigating to IO page to ensure communication uses latest tag addresses.
        Only reloads if configuration has been modified (dirty flag set).
        """
        try:
            if not hasattr(self, 'tanksim_config') or self.tanksim_config is None:
                return  # Silent fail for auto-reload
            
            # Only reload if config is dirty (has unsaved changes)
            if not getattr(self, '_io_config_dirty', False):
                return  # No changes to reload
            
            project_root = Path(__file__).resolve().parent.parent.parent
            io_config_path = project_root / "IO" / "IO_configuration.json"
            
            # Ensure IO directory exists
            io_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if IO config file exists
            if not io_config_path.exists():
                return  # Silent fail - no file to reload from
            
            # STEP 1: Save the current table to JSON
            try:
                table = self.tableWidget_IO
                config_data = {
                    'offsets': self.io_screen.byte_offsets.copy(),
                    'signals': []
                }
                
                # Persist custom signal name overrides
                try:
                    if hasattr(self.tanksim_config, 'custom_signal_names'):
                        config_data['custom_signal_names'] = self.tanksim_config.custom_signal_names.copy()
                except Exception:
                    pass
                
                # Save all signals from table
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
                
                # Write to JSON file
                with open(io_config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                    
            except Exception as e:
                return  # Silent fail for auto-reload
            
            # STEP 2: Disconnect PLC if connected
            if hasattr(self, 'validPlcConnection') and self.validPlcConnection:
                if hasattr(self, 'plc') and self.plc:
                    try:
                        self.plc.disconnect()
                    except Exception:
                        pass
                
                self.validPlcConnection = False
                self.plc = None
                self.update_connection_status_icon()
                
                try:
                    self.pushButton_connect.blockSignals(True)
                    self.pushButton_connect.setChecked(False)
                    self.pushButton_connect.blockSignals(False)
                except Exception:
                    pass
            
            # STEP 3: Load config from file into main object
            # Prevent auto-conflict resolution while loading config
            self.io_screen.loading_config = True
            try:
                self.tanksim_config.load_io_config_from_file(io_config_path)
                
                # STEP 4: Update GUI offsets from loaded config
                try:
                    with open(io_config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    if 'offsets' in config_data:
                        self.io_screen.byte_offsets = config_data['offsets'].copy()
                        self.QLineEdit_BoolInput.setText(str(config_data['offsets'].get('BoolInput', 0)))
                        self.QLineEdit_BoolOutput.setText(str(config_data['offsets'].get('BoolOutput', 0)))
                        self.QLineEdit_DWORDInput.setText(str(config_data['offsets'].get('DWORDInput', 2)))
                        self.QLineEdit_DWORDOutput.setText(str(config_data['offsets'].get('DWORDOutput', 2)))
                except Exception as e:
                    return  # Silent fail
                
                # STEP 5: Update table from reloaded config
                self._update_table_from_config()
            finally:
                self.io_screen.loading_config = False
            
            # Auto-reload activates config; clear dirty state (silent success)
            try:
                self._io_config_dirty = False
            except Exception:
                pass
            
            # STEP 6: Auto-connect after successful configuration load
            try:
                # Only auto-connect if not in GUI mode
                if (hasattr(self, 'mainConfig') and self.mainConfig and 
                    self.mainConfig.plcGuiControl != "gui" and
                    hasattr(self, 'pushButton_connect') and self.pushButton_connect):
                    
                    self.pushButton_connect.blockSignals(True)
                    self.pushButton_connect.setChecked(True)
                    self.pushButton_connect.blockSignals(False)
                    
                    # Trigger the connect action
                    if hasattr(self, 'mainConfig'):
                        self.mainConfig.tryConnect = True
            except Exception as e:
                pass  # Silently fail if auto-connect fails
            
        except Exception as e:
            return  # Silent fail for auto-reload
        
    def _update_table_from_config(self):
        """Update the GUI table with addresses from the config"""
        try:
            table = self.tableWidget_IO
            config = self.tanksim_config
            
            table.blockSignals(True)
            
            # Determine correct address prefix based on controller type
            is_logo = False
            if hasattr(self, 'mainConfig') and self.mainConfig:
                is_logo = (self.mainConfig.plcProtocol == "logo!")
            
            for row in range(table.rowCount()):
                name_item = table.item(row, 0)
                if not name_item or not name_item.text():
                    continue
                
                signal_name = name_item.text()
                
                if signal_name not in config.io_signal_mapping:
                    continue
                
                attr_name = config.io_signal_mapping[signal_name]
                attr_value = getattr(config, attr_name, None)
                
                if attr_value is None:
                    continue
                
                if "bit" in attr_value:
                    byte_num = attr_value["byte"]
                    bit_num = attr_value["bit"]
                    
                    # Use V for LOGO!, I/Q for other controllers
                    if is_logo:
                        address = f"V{byte_num}.{bit_num}"
                    else:
                        io_prefix = "Q" if attr_name.startswith(("DQ", "AQ")) else "I"
                        address = f"{io_prefix}{byte_num}.{bit_num}"
                    
                    table.setItem(row, 2, EditableTableWidgetItem(str(byte_num)))
                    table.setItem(row, 3, EditableTableWidgetItem(str(bit_num)))
                    table.setItem(row, 4, ReadOnlyTableWidgetItem(address))
                    
                else:
                    byte_num = attr_value["byte"]
                    
                    # Use VW for LOGO!, IW/QW for other controllers
                    if is_logo:
                        address = f"VW{byte_num}"
                    else:
                        io_prefix = "Q" if attr_name.startswith(("DQ", "AQ")) else "I"
                        address = f"{io_prefix}W{byte_num}"
                    
                    table.setItem(row, 2, EditableTableWidgetItem(str(byte_num)))
                    table.setItem(row, 3, EditableTableWidgetItem(""))
                    table.setItem(row, 4, ReadOnlyTableWidgetItem(address))
                
                table._save_row_data(row)
            
            table.blockSignals(False)
            
        except Exception as e:
            pass # Removed print

    def toggle_force_mode(self, checked):
        """Toggle force mode on/off"""
        self.tableWidget_IO.set_force_mode(checked)
        
        # Update the force state label dynamically
        if hasattr(self, 'Label_Forcestate'):
            if checked:
                self.Label_Forcestate.setText(
                    "● Forcing ON: Double-click any cell in Status column to force values\n"
                    "● Yellow = Forced | ● Green = Available to force"
                )
                self.Label_Forcestate.setStyleSheet("""QLabel {
    background-color: #e3f2fd;
    border: 1px solid #64b5f6;
    border-radius: 4px;
    padding: 8px;
    color: #0d47a1;
}""")
            else:
                self.Label_Forcestate.setText("● Forcing OFF")
                self.Label_Forcestate.setStyleSheet("""QLabel {
    background-color: #f5f5f5;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 8px;
    color: #333333;
}""")
        
        if not checked:
            self.clear_all_forces()
        
    def clear_all_forces(self):
        """
        Clear all forced values and disable force mode
        Called when connecting to PLC to ensure clean state
        """
        try:
            if hasattr(self, 'tableWidget_IO'):
                # Clear all forced rows
                # Note: Calling remove_force for each row ensures color reset
                for row in list(self.tableWidget_IO.forced_rows.keys()):
                    self.tableWidget_IO.remove_force(row)
                
                # Disable force mode
                self.tableWidget_IO.force_enabled = False
                
                # Untoggle force button if it exists
                try:
                    if self.pushButton_AllowForce.isChecked():
                        self.pushButton_AllowForce.blockSignals(True)
                        self.pushButton_AllowForce.setChecked(False)
                        self.pushButton_AllowForce.blockSignals(False)
                except AttributeError:
                    pass
                
                # Removed print
        except Exception as e:
            pass # Removed print
            
    def update_io_status_display(self):
        """Update status column with current IO values"""
        try:
            if not hasattr(self, 'tanksim_config') or not hasattr(self, 'tanksim_status'):
                return
            
            table = self.tableWidget_IO
            config = self.tanksim_config
            status = self.tanksim_status
            
            has_plc = (hasattr(self, 'validPlcConnection') and 
                    self.validPlcConnection and 
                    hasattr(self, 'plc') and 
                    self.plc)
            
            for row in range(table.rowCount()):
                name_item = table.item(row, 0)
                if not name_item or not name_item.text():
                    continue
                
                signal_name = name_item.text()
                is_forced = table.is_row_forced(row)
                
                if signal_name not in config.io_signal_mapping:
                    continue
                
                attr_name = config.io_signal_mapping[signal_name]
                attr_value = getattr(config, attr_name, None)
                
                if attr_value is None:
                    continue
                
                value = None
                
                if is_forced:
                    value = table.get_forced_value(row)
                elif has_plc:
                    try:
                        if "bit" in attr_value:
                            byte_addr = attr_value["byte"]
                            bit_addr = attr_value["bit"]
                            
                            if attr_name.startswith("DQ"):
                                value = self.plc.GetDO(byte_addr, bit_addr)
                            else:
                                value = self.plc.GetDI(byte_addr, bit_addr)
                        else:
                            byte_addr = attr_value["byte"]
                            
                            if attr_name.startswith("AQ"):
                                value = self.plc.GetAO(byte_addr)
                            else:
                                value = self.plc.GetAI(byte_addr)
                    except Exception:
                        pass
                
                if value is None:
                    # Fallback to simulation status if not forced and not from PLC
                    plc_analog_max = self.plc.analogMax if has_plc and hasattr(self.plc, 'analogMax') else 27648
                    
                    if attr_name == "DQValveIn":
                        value = (status.valveInOpenFraction > 0)
                    elif attr_name == "AQValveInFraction":
                        value = int(status.valveInOpenFraction * plc_analog_max)
                    elif attr_name == "DQValveOut":
                        value = (status.valveOutOpenFraction > 0)
                    elif attr_name == "AQValveOutFraction":
                        value = int(status.valveOutOpenFraction * plc_analog_max)
                    elif attr_name == "DQHeater":
                        value = (status.heaterPowerFraction > 0)
                    elif attr_name == "AQHeaterFraction":
                        value = int(status.heaterPowerFraction * plc_analog_max)
                    # General Controls - PLC Inputs (commands from GUI to PLC)
                    elif attr_name == "DIStart":
                        value = bool(getattr(status, 'generalStartCmd', False))
                    elif attr_name == "DIStop":
                        value = bool(getattr(status, 'generalStopCmd', False))
                    elif attr_name == "DIReset":
                        value = bool(getattr(status, 'generalResetCmd', False))
                    elif attr_name == "AIControl1":
                        value = int(getattr(status, 'generalControl1Value', 0))
                    elif attr_name == "AIControl2":
                        value = int(getattr(status, 'generalControl2Value', 0))
                    elif attr_name == "AIControl3":
                        value = int(getattr(status, 'generalControl3Value', 0))
                    # Sensor Inputs (from simulation to PLC)
                    elif attr_name == "DILevelSensorHigh":
                        value = status.digitalLevelSensorHighTriggered
                    elif attr_name == "DILevelSensorLow":
                        value = status.digitalLevelSensorLowTriggered
                    elif attr_name == "AILevelSensor":
                        value = int((status.liquidVolume / config.tankVolume) * plc_analog_max)
                    elif attr_name == "AITemperatureSensor":
                        value = int(((status.liquidTemperature + 50) / 300) * plc_analog_max)
                    # General Controls - PLC Outputs (from PLC to GUI indicators)
                    elif attr_name == "DQIndicator1":
                        value = bool(getattr(status, 'indicator1', False))
                    elif attr_name == "DQIndicator2":
                        value = bool(getattr(status, 'indicator2', False))
                    elif attr_name == "DQIndicator3":
                        value = bool(getattr(status, 'indicator3', False))
                    elif attr_name == "DQIndicator4":
                        value = bool(getattr(status, 'indicator4', False))
                    elif attr_name == "AQAnalog1":
                        value = int(getattr(status, 'analog1', 0))
                    elif attr_name == "AQAnalog2":
                        value = int(getattr(status, 'analog2', 0))
                    elif attr_name == "AQAnalog3":
                        value = int(getattr(status, 'analog3', 0))
                    # PID Valve Controls - Specific handling for known PID controls
                    elif attr_name == "DIPidValveStart":
                        value = bool(getattr(status, 'pidPidValveStartCmd', False))
                    elif attr_name == "DIPidValveStop":
                        value = bool(getattr(status, 'pidPidValveStopCmd', False))
                    elif attr_name == "DIPidValveReset":
                        value = bool(getattr(status, 'pidPidValveResetCmd', False))
                    elif attr_name == "DIPidValveAuto":
                        value = bool(getattr(status, 'pidPidValveAutoCmd', True))
                    elif attr_name == "DIPidValveMan":
                        value = bool(getattr(status, 'pidPidValveManCmd', False))
                    elif attr_name == "DIPidTankValveAItemp":
                        value = bool(getattr(status, 'pidPidTankValveAItempCmd', False))
                    elif attr_name == "DIPidTankValveDItemp":
                        value = bool(getattr(status, 'pidPidTankValveDItempCmd', False))
                    elif attr_name == "DIPidTankValveAIlevel":
                        value = bool(getattr(status, 'pidPidTankValveAIlevelCmd', False))
                    elif attr_name == "DIPidTankValveDIlevel":
                        value = bool(getattr(status, 'pidPidTankValveDIlevelCmd', False))
                    elif attr_name == "AIPidTankTempSP":
                        value = int(getattr(status, 'pidPidTankTempSPValue', 0))
                    elif attr_name == "AIPidTankLevelSP":
                        value = int(getattr(status, 'pidPidTankLevelSPValue', 0))
                    # PID Controls and other dynamic signals - Try to get value from dynamic attributes created by handler
                    # Handler creates attributes like pidPidValveStartCmd for digital, pidPidTankTempSPValue for analog
                    elif attr_name.startswith("DI") or attr_name.startswith("AI"):
                        # Try to get the attribute dynamically - handler may have created it
                        # Handler creates: attr = f"pid{name}Cmd" where name is like "PidValveStart"
                        # So for DIPidValveStart, it would create pidPidValveStartCmd
                        type_item = table.item(row, 1)
                        data_type = type_item.text() if type_item else 'bool'
                        
                        attr_to_check = f"pid{attr_name[2:]}Cmd" if attr_name.startswith("DI") else f"pid{attr_name[2:]}Value"
                        value = getattr(status, attr_to_check, None)
                        
                        if value is None:
                            # Default value: False for bool, 0 for int
                            # This ensures the status column gets updated with green background
                            value = False if data_type == 'bool' else 0
                    else:
                        # For any other signal types (DQ, AQ not matched above), use default values
                        type_item = table.item(row, 1)
                        data_type = type_item.text() if type_item else 'bool'
                        value = False if data_type == 'bool' else 0
                
                # Ensure value is always set before updating status column
                if value is None:
                    type_item = table.item(row, 1)
                    data_type = type_item.text() if type_item else 'bool'
                    value = False if data_type == 'bool' else 0
                
                table.update_status_column(row, value)
                
        except Exception as e:
            pass # Removed print
    
    def get_forced_io_values(self):
        """Collect all forced IO values"""
        forced_values = {}
        
        if not hasattr(self, 'tableWidget_IO'):
            return forced_values
        
        table = self.tableWidget_IO
        
        if not hasattr(self, 'tanksim_config'):
            return forced_values
        
        config = self.tanksim_config
        
        for row, force_data in table.forced_rows.items():
            name_item = table.item(row, 0)
            type_item = table.item(row, 1)
            addr_item = table.item(row, 4)
            
            if not name_item or not type_item or not addr_item:
                continue
            
            signal_name = name_item.text()
            address = addr_item.text()
            forced_value = force_data["value"]
            
            if signal_name not in config.io_signal_mapping:
                continue
            
            attr_name = config.io_signal_mapping[signal_name]
            
            is_digital = '.' in address
            is_analog = 'W' in address
            
            if is_digital:
                forced_values[attr_name] = bool(forced_value)
            elif is_analog:
                forced_values[attr_name] = int(forced_value)
        
        return forced_values

    # ----- Rename propagation from General Controls or table -----
    def handle_io_signal_rename(self, canonical: str, old_display: str, new_display: str):
        """Synchronize renamed signals across tree, table and config mapping.

        canonical: stable mapping key (e.g., Control1, Start)
        old_display: previous shown name
        new_display: new shown name
        """
        if not canonical or not new_display or old_display == new_display:
            return

        # Update tree widget text (match either old_display or canonical)
        try:
            def _rename_tree_item(item):
                if item.text(0) in (old_display, canonical):
                    item.setText(0, new_display)
                for i in range(item.childCount()):
                    _rename_tree_item(item.child(i))
            if hasattr(self, 'treeWidget_IO') and self.treeWidget_IO:
                tree = self.treeWidget_IO
                for i in range(tree.topLevelItemCount()):
                    _rename_tree_item(tree.topLevelItem(i))
                
                # Update signal_data dictionary to maintain drag-and-drop functionality
                if hasattr(tree, 'signal_data'):
                    if old_display in tree.signal_data:
                        tree.signal_data[new_display] = tree.signal_data[old_display]
                        del tree.signal_data[old_display]
                    elif canonical in tree.signal_data:
                        tree.signal_data[new_display] = tree.signal_data[canonical]
                        # Keep canonical as well for compatibility
        except Exception:
            pass

        # Update table entries
        try:
            if hasattr(self, 'tableWidget_IO') and self.tableWidget_IO:
                table = self.tableWidget_IO
                table.blockSignals(True)
                for row in range(table.rowCount()):
                    item = table.item(row, 0)
                    if item and item.text() in (old_display, canonical):
                        item.setText(new_display)
                        table._save_row_data(row)
                table.blockSignals(False)
        except Exception:
            pass

        # Update config mapping and reverse mapping
        try:
            cfg = getattr(self, 'tanksim_config', None)
            if cfg and hasattr(cfg, 'io_signal_mapping'):
                if canonical in cfg.io_signal_mapping:
                    attr = cfg.io_signal_mapping[canonical]
                    # Keep canonical mapping, add alias
                    cfg.io_signal_mapping[new_display] = attr
                    if hasattr(cfg, 'reverse_io_mapping'):
                        cfg.reverse_io_mapping[attr] = new_display
                    if hasattr(cfg, 'custom_signal_names'):
                        cfg.custom_signal_names[attr] = new_display
            # Mark dirty so user is prompted to apply
            self._mark_io_dirty()
        except Exception:
            pass

        # Refresh General Controls labels if they depend on this signal
        try:
            if hasattr(self, '_refresh_general_control_labels_from_mapping'):
                self._refresh_general_control_labels_from_mapping()
        except Exception:
            pass

    # ----- Dirty-state helper -----
    def _mark_io_dirty(self):
        """Mark IO configuration as dirty to trigger leave-page confirmation."""
        try:
            self._io_config_dirty = True
            # One-time heads-up could be shown here if desired; keeping UX minimal.
        except Exception:
            pass
