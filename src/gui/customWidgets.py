"""
Custom PyQt5 Widgets - Enhanced table and tree widgets for IO configuration.

Contains:
- CustomTableWidgetItem (smart sorting for PLC addresses)
- EditableTableWidgetItem and ReadOnlyTableWidgetItem
- DraggableTreeWidget (drag support for IO signals)
- DroppableTableWidget (drop support with force functionality for IO testing)

External Libraries Used:
- PyQt5 (GPL v3) - GUI framework for custom widgets, drag-drop, and table/tree functionality
- json (Python Standard Library) - MIME data serialization for drag-drop operations
"""

import json
from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QMenu, QAction, QApplication, QInputDialog
)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag, QColor


# =============================================================================
# Custom Table Widget Items
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


# =============================================================================
# Draggable Tree Widget
# =============================================================================
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


# =============================================================================
# Droppable Table Widget with Force Functionality
# =============================================================================
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
    
    # =========================================================================
    # Cell Editing & Validation
    # =========================================================================
    def on_item_changed(self, item):
        """Callback when a cell changes - update address"""
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
        
        # Determine original IO type (I or Q) from current address
        original_prefix = current_address[0] if current_address else 'I'
        
        # Converteer naar V voor LOGO! indien nodig
        io_prefix = self.get_address_prefix(original_prefix)
        
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
            pass

    # =========================================================================
    # Sorting & Selection
    # =========================================================================
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

    # =========================================================================
    # Force Functionality
    # =========================================================================
    def mouseDoubleClickEvent(self, event):
        """Handle double clicks for force menu (status col) and rename (name col)."""
        item = self.itemAt(event.pos())
        if not item:
            super().mouseDoubleClickEvent(event)
            return

        col = item.column()
        row = item.row()

        # Rename when double-clicking the Name column (col 0)
        if col == 0:
            old_name = item.text().strip()
            if not old_name:
                super().mouseDoubleClickEvent(event)
                return

            new_name, ok = QInputDialog.getText(self, "Rename signal", "New name:", text=old_name)
            if not ok or not new_name.strip():
                super().mouseDoubleClickEvent(event)
                return

            new_name = new_name.strip()
            self.blockSignals(True)
            item.setText(new_name)
            self._save_row_data(row)
            self.blockSignals(False)

            # Propagate rename to main window (tree/labels)
            try:
                mw = getattr(self, 'io_screen', None).main_window if getattr(self, 'io_screen', None) else None
                if mw and hasattr(mw, "handle_io_signal_rename"):
                    mw.handle_io_signal_rename(old_name, old_name, new_name)
            except Exception:
                pass

            # Mark dirty
            try:
                if self.io_screen and hasattr(self.io_screen, 'main_window') and hasattr(self.io_screen.main_window, '_mark_io_dirty'):
                    self.io_screen.main_window._mark_io_dirty()
            except Exception:
                pass
            event.accept()
            return

        # Force dialog on Status column (col 5)
        if col != 5:
            super().mouseDoubleClickEvent(event)
            return
        
        if not self.force_enabled:
            super().mouseDoubleClickEvent(event)
            return
        
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
        """Toon force menu op gegeven positie"""
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
    
    def set_force_mode(self, enabled):
        """Enable or disable force mode with visual feedback"""
        self.force_enabled = enabled
        
        if enabled:
            # Change header text to indicate force mode is active
            header_item = self.horizontalHeaderItem(5)
            if header_item:
                # Add indicator to header text
                header_item.setText("Status [*]")  # Add lightning bolt to show active
                header_item.setToolTip("Status column - Double-click a row to force/change values")
                
                # Set header background to light blue
                from PyQt5.QtGui import QBrush
                brush = QBrush(QColor(173, 216, 230))  # Light blue
                header_item.setBackground(brush)
            
            # Add green tint to all Status column cells to show they're available for forcing
            for row in range(self.rowCount()):
                item = self.item(row, 5)
                if item:
                    # Light green background to indicate available for forcing
                    brush = QBrush(QColor(200, 255, 200))  # Light green
                    item.setBackground(brush)
        else:
            # Disable force mode - reset colors and clear forced values
            self.forced_rows.clear()
            
            # Reset header
            header_item = self.horizontalHeaderItem(5)
            if header_item:
                header_item.setText("Status")  # Remove indicator
                header_item.setBackground(Qt.white)
                header_item.setToolTip("")
            
            # Reset only Status column (column 5) to blue when force mode disabled
            for row in range(self.rowCount()):
                item = self.item(row, 5)
                if item:
                    item.setBackground(QColor(200, 230, 245))  # Blue
            
            # Refresh the table display
            self.viewport().update()

    def apply_force(self, row, value):
        """Apply force to a signal"""
        self.forced_rows[row] = {"value": value}
        
        # Only highlight the Status cell (column 5), not the entire row
        item = self.item(row, 5)
        if item:
            item.setBackground(Qt.yellow)

    def apply_force_analog(self, row, signal_name):
        """Apply force to an analog signal with dialog"""
        max_value = 27648  # All analog signals use 0-27648 range
        
        current_value = 0
        status_item = self.item(row, 5)
        if status_item and status_item.text():
            try:
                text = status_item.text().replace("[F] ", "")
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
        """Update de status column met visuele feedback"""
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
        
        if self.is_row_forced(row):
            display_text = f"[F] {display_text}"  # Lock icon instead of [LOCKED]
        
        if status_item:
            status_item.setText(display_text)
            
            if self.is_row_forced(row):
                status_item.setBackground(Qt.yellow)
            elif self.force_enabled:
                # In force mode but not forced - use green to show available for forcing
                status_item.setBackground(QColor(200, 255, 200))  # Light green
            else:
                # Normal display - use blue
                status_item.setBackground(QColor(200, 230, 245))
        else:
            new_item = ReadOnlyTableWidgetItem(display_text)
            if self.is_row_forced(row):
                new_item.setBackground(Qt.yellow)
            elif self.force_enabled:
                # In force mode but not forced - use green to show available for forcing
                new_item.setBackground(QColor(200, 255, 200))  # Light green
            else:
                # Normal display - use blue
                new_item.setBackground(QColor(200, 230, 245))  # Blue
            self.setItem(row, 5, new_item)

    # =========================================================================
    # Drag & Drop
    # =========================================================================
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
    
    def dropEvent(self, event):
        """Process drop only in column 0"""
        if event.mimeData().hasText():
            dropped_text = event.mimeData().text()
            position = event.pos()
            row = self.rowAt(position.y())
            col = self.columnAt(position.x())
            
            if row >= 0 and col == 0:
                try:
                    self.remove_duplicate_signals(dropped_text, exclude_row=row)
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
                            status_text = signal_data['status']
                            status_item = ReadOnlyTableWidgetItem(status_text)
                            status_item.setBackground(QColor(200, 230, 245))  # Blue
                            self.setItem(row, 5, status_item)
                            # Convert status text to value and call update to ensure consistency
                            data_type = signal_data.get('type', 'bool')
                            if data_type == 'bool':
                                value = status_text.upper() == 'TRUE'
                            else:
                                try:
                                    value = int(status_text)
                                except:
                                    value = 0
                            self.update_status_column(row, value)
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

    # =========================================================================
    # Helper Methods
    # =========================================================================
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
                if col in [2, 3]:
                    self.setItem(display_row, col, EditableTableWidgetItem(text))
                else:
                    self.setItem(display_row, col, ReadOnlyTableWidgetItem(text))
            self._save_row_data(display_row)
        self.blockSignals(False)
    
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
        
        # Convert prefix to LOGO format if needed
        address_prefix = self.get_address_prefix(prefix)
        
        if data_type == 'bool':
            for byte_num in range(offset, 256):
                byte_key = f"{address_prefix}{byte_num}"
                used_bits = used.get(byte_key, set())
                for bit in range(8):
                    if bit not in used_bits:
                        return (byte_num, bit, f"{address_prefix}{byte_num}.{bit}")
            return (offset, 0, f"{address_prefix}{offset}.0")
        
        elif data_type in ['int', 'word']:
            start_byte = offset if offset % 2 == 0 else offset + 1
            for byte_num in range(start_byte, 254, 2):
                byte1_key = f"{address_prefix}{byte_num}"
                byte2_key = f"{address_prefix}{byte_num + 1}"
                is_byte1_free = byte1_key not in used or len(used[byte1_key]) == 0
                is_byte2_free = byte2_key not in used or len(used[byte2_key]) == 0
                if is_byte1_free and is_byte2_free:
                    return (byte_num, None, f"{address_prefix}W{byte_num}")
            return (start_byte, None, f"{address_prefix}W{start_byte}")
        
        return (offset, 0, f"{address_prefix}{offset}.0")

    def get_address_prefix(self, io_type):
        """
        Get the correct address prefix based on controller type
        
        Args:
            io_type: 'I' for input or 'Q' for output
        
        Returns:
            'V' for LOGO!, 'I' or 'Q' for other controllers
        """
        if not self.io_screen or not hasattr(self.io_screen, 'main_window'):
            return io_type
        
        main_window = self.io_screen.main_window
        
        # Check if we're using LOGO! controller
        if hasattr(main_window, 'mainConfig') and main_window.mainConfig:
            if main_window.mainConfig.plcProtocol == "logo!":
                return 'V'  # LOGO! uses V for both inputs and outputs
        
        return io_type  # Return original prefix for non-LOGO controllers
