from PyQt5.QtCore import Qt, QObject
from PyQt5.QtWidgets import QWidget, QDockWidget, QPushButton, QInputDialog
from PyQt5.QtGui import QIcon
from IO.buttonPulseManager import get_button_pulse_manager
from pathlib import Path


class GeneralControlsMixin:
    def init_general_controls_page(self):
        """Initialize General Controls dock and sidebar buttons, sliders, and handlers."""
        # Configure General Controls dock for right-side docking
        try:
            if hasattr(self, 'dockWidget_GeneralControls') and self.dockWidget_GeneralControls:
                # Hide at startup
                self.dockWidget_GeneralControls.hide()
                
                try:
                    # Allow docking only on the right side
                    self.dockWidget_GeneralControls.setAllowedAreas(Qt.RightDockWidgetArea)
                    
                    # Allow moving, closing, and floating
                    self.dockWidget_GeneralControls.setFeatures(
                        QDockWidget.DockWidgetMovable | 
                        QDockWidget.DockWidgetFloatable | 
                        QDockWidget.DockWidgetClosable
                    )
                    
                    # Initially dock it (not floating)
                    self.dockWidget_GeneralControls.setFloating(False)
                    
                    # Add it to the right dock area
                    self.addDockWidget(Qt.RightDockWidgetArea, self.dockWidget_GeneralControls)
                    
                    # Set a reasonable minimum and maximum width
                    self.dockWidget_GeneralControls.setMinimumWidth(250)
                    self.dockWidget_GeneralControls.setMaximumWidth(500)
                    
                    # Connect close event to update sidebar button state
                    self.dockWidget_GeneralControls.visibilityChanged.connect(
                        self._on_general_controls_visibility_changed
                    )
                    
                except Exception as e:
                    pass
        except Exception:
            pass

        # Ensure GENERAL CONTROLS sidebar buttons are unchecked initially
        try:
            if hasattr(self, 'pushButton_generalControls') and self.pushButton_generalControls:
                self.pushButton_generalControls.blockSignals(True)
                self.pushButton_generalControls.setChecked(False)
                self.pushButton_generalControls.blockSignals(False)
                # Ensure click toggles/hides the dock even if toggled doesn't fire in some layouts
                try:
                    self.pushButton_generalControls.clicked.connect(self._on_general_controls_clicked)
                except Exception:
                    pass
        except Exception:
            pass
        # Connect pushButton_generalControls_2 and pushButton_generalControls_3
        for button_name in ['pushButton_generalControls_2', 'pushButton_generalControls_3']:
            try:
                button = getattr(self, button_name, None)
                if button:
                    button.blockSignals(True)
                    button.setChecked(False)
                    button.blockSignals(False)
                    try:
                        button.clicked.connect(self._on_general_controls_clicked)
                    except Exception:
                        pass
            except Exception:
                pass

        # Initialize sliders and buttons
        try:
            self._init_general_controls_sliders()
            self._init_general_controls_buttons()
            self._install_general_control_renamers()
        except Exception:
            pass
        
        # Load saved dock state if available
        # Removed: Always start docked and hidden, don't restore state

    def _init_general_controls_sliders(self):
        """Set slider ranges to 0..27648 and bind labels to show live value."""
        try:
            slider_label_pairs = [
                (getattr(self, 'slider_control1', None), getattr(self, 'label_sliderValue1', None)),
                (getattr(self, 'slider_control2', None), getattr(self, 'label_sliderValue2', None)),
                (getattr(self, 'slider_control3', None), getattr(self, 'label_sliderValue3', None)),
            ]
            for slider, label in slider_label_pairs:
                if slider:
                    slider.setMinimum(0)
                    slider.setMaximum(27648)
                    if label:
                        try:
                            label.setText(str(int(slider.value())))
                        except Exception:
                            label.setText("0")
                        slider.valueChanged.connect(lambda v, lbl=label: lbl.setText(str(int(v))))
        except Exception:
            pass

    def _init_general_controls_buttons(self):
        """Initialize Start/Stop/Reset button event handlers with pulse manager."""
        try:
            button_manager = get_button_pulse_manager(pulse_duration_ms=200)
            
            btn_start = getattr(self, 'pushButton_control1', None)
            btn_stop = getattr(self, 'pushButton_control2', None)
            btn_reset = getattr(self, 'pushButton_control3', None)

            # Get status object or use None (will be set later)
            status_obj = getattr(self, 'tanksim_status', None)

            if btn_start:
                button_manager.register_button('GeneralStart', status_obj, 'generalStartCmd')
                btn_start.pressed.connect(lambda: button_manager.on_button_pressed('GeneralStart'))
                btn_start.released.connect(lambda: button_manager.on_button_released('GeneralStart'))

            if btn_stop:
                button_manager.register_button('GeneralStop', status_obj, 'generalStopCmd')
                btn_stop.pressed.connect(lambda: button_manager.on_button_pressed('GeneralStop'))
                btn_stop.released.connect(lambda: button_manager.on_button_released('GeneralStop'))

            if btn_reset:
                button_manager.register_button('GeneralReset', status_obj, 'generalResetCmd')
                btn_reset.pressed.connect(lambda: button_manager.on_button_pressed('GeneralReset'))
                btn_reset.released.connect(lambda: button_manager.on_button_released('GeneralReset'))

            
            # Store reference to update status objects later
            self._button_manager = button_manager
        except Exception as e:

            import traceback
            traceback.print_exc()

    # ------------------------------------------------------------------
    # Rename support (double-click labels/buttons)
    # ------------------------------------------------------------------
    def _install_general_control_renamers(self):
        """Attach event filters to labels/buttons to allow rename via double-click."""
        try:
            self._gc_rename_targets = {
                getattr(self, 'label_slider1', None): 'Control1',
                getattr(self, 'label_slider2', None): 'Control2',
                getattr(self, 'label_slider3', None): 'Control3',
                getattr(self, 'pushButton_control1', None): 'Start',
                getattr(self, 'pushButton_control2', None): 'Stop',
                getattr(self, 'pushButton_control3', None): 'Reset',
                getattr(self, 'label_status1', None): 'Indicator1',
                getattr(self, 'label_status2', None): 'Indicator2',
                getattr(self, 'label_status3', None): 'Indicator3',
                getattr(self, 'label_status4', None): 'Indicator4',
                getattr(self, 'label_value1', None): 'Analog1',
                getattr(self, 'label_value2', None): 'Analog2',
                getattr(self, 'label_value3', None): 'Analog3',
            }

            for widget, canonical in list(self._gc_rename_targets.items()):
                if widget is None:
                    self._gc_rename_targets.pop(widget, None)
                    continue
                widget.installEventFilter(self)
        except Exception:
            pass

    def eventFilter(self, obj, event):
        try:
            # Only handle registered rename targets
            if hasattr(self, '_gc_rename_targets') and obj in self._gc_rename_targets:
                if event.type() == event.MouseButtonDblClick:
                    canonical = self._gc_rename_targets[obj]
                    old_text = obj.text().replace(':', '').strip() if hasattr(obj, 'text') else ''
                    
                    # Create input dialog
                    dialog = QInputDialog(self)
                    dialog.setWindowTitle("Rename control")
                    dialog.setLabelText("New name:")
                    dialog.setTextValue(old_text)
                    
                    # Remove question mark button and set icon
                    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                    try:
                        icon_path = Path(__file__).parent.parent / "media" / "icon" / "simulation.ico"
                        if icon_path.exists():
                            dialog.setWindowIcon(QIcon(str(icon_path)))
                    except Exception:
                        pass
                    
                    ok = dialog.exec_()
                    new_text = dialog.textValue()
                    
                    if not ok or not new_text.strip():
                        return True
                    new_text = new_text.strip()

                    # Update label/button text (keep colon if present)
                    suffix = ':' if hasattr(obj, 'text') and obj.text().strip().endswith(':') else ''
                    if hasattr(obj, 'setText'):
                        obj.setText(f"{new_text}{suffix}")

                    # Propagate to IO mapping so table/tree/labels stay in sync
                    try:
                        if hasattr(self, 'handle_io_signal_rename'):
                            # canonical used as stable key; old_display is previous text without colon
                            self.handle_io_signal_rename(canonical, old_text, new_text)
                    except Exception:
                        pass

                    # Mark dirty
                    try:
                        if hasattr(self, '_mark_io_dirty'):
                            self._mark_io_dirty()
                    except Exception:
                        pass
                    return True
        except Exception:
            pass
        # Fallback to base implementation
        return QObject.eventFilter(self, obj, event)

    def _on_start_pressed(self):
        """Deprecated - now handled by pulse manager."""
        pass

    def _on_start_released(self):
        """Deprecated - now handled by pulse manager."""
        pass

    def _on_stop_pressed(self):
        """Deprecated - now handled by pulse manager."""
        pass

    def _on_stop_released(self):
        """Deprecated - now handled by pulse manager."""
        pass

    def _on_reset_pressed(self):
        """Deprecated - now handled by pulse manager."""
        pass

    def _on_reset_released(self):
        """Deprecated - now handled by pulse manager."""
        pass
    
    def _auto_close_sidebar(self):
        """Auto-close the sidebar after navigation (same as SimPageMixin)"""
        try:
            if hasattr(self, 'pushButton_menu') and self.pushButton_menu:
                if self.pushButton_menu.isChecked():
                    self.pushButton_menu.setChecked(False)
        except Exception:
            pass

    def _on_general_controls_clicked(self):
        """Clicked handler to toggle/hide the General Controls dock robustly"""
        try:
            # Get the sender button to check its state
            sender = self.sender()
            if sender and hasattr(sender, 'isChecked'):
                checked = sender.isChecked()
            else:
                # Fallback: toggle based on dock visibility
                checked = not (hasattr(self, 'dockWidget_GeneralControls') and 
                              self.dockWidget_GeneralControls and 
                              self.dockWidget_GeneralControls.isVisible())
            
            # Call the main handler with the checked state
            self.go_to_general_controls(checked)
        except Exception:
            pass

    def go_to_general_controls(self, checked):
        """Navigate to General Controls page and toggle dock visibility."""
        try:
            if checked and not self._maybe_confirm_leave_io():
                # Uncheck all general controls buttons
                for button_name in ['pushButton_generalControls', 'pushButton_generalControls_2', 'pushButton_generalControls_3']:
                    try:
                        button = getattr(self, button_name, None)
                        if button:
                            button.blockSignals(True)
                            button.setChecked(False)
                            button.blockSignals(False)
                    except Exception:
                        pass
                return
            page = self.findChild(QWidget, "page_generalControls")
            if checked and page is not None:
                idx = self.MainScreen.indexOf(page)
                if idx != -1:
                    self.MainScreen.setCurrentWidget(page)
            # Show/hide dock accordingly
            if hasattr(self, 'dockWidget_GeneralControls') and self.dockWidget_GeneralControls:
                if checked:
                    # Force dock to be docked (not floating) before showing
                    self.dockWidget_GeneralControls.setFloating(False)
                    self.dockWidget_GeneralControls.show()
                    try:
                        self.dockWidget_GeneralControls.raise_()
                    except Exception:
                        pass
                else:
                    self.dockWidget_GeneralControls.hide()
            
            # Don't auto-close sidebar when showing general controls
            # Only close it when hiding
            if not checked and hasattr(self, '_auto_close_sidebar'):
                self._auto_close_sidebar()
        except Exception:
            pass

    def _update_general_controls_ui(self):
        """Update General Controls dock widgets from status/PLC values."""
        try:
            status = getattr(self, 'tanksim_status', None)
            if status is None:
                return

            frame_map = [
                getattr(self, 'frame_indicator1', None),
                getattr(self, 'frame_indicator2', None),
                getattr(self, 'frame_indicator3', None),
                getattr(self, 'frame_indicator4', None),
            ]
            indicators = [
                bool(getattr(status, 'indicator1', False)),
                bool(getattr(status, 'indicator2', False)),
                bool(getattr(status, 'indicator3', False)),
                bool(getattr(status, 'indicator4', False)),
            ]
            for frame, is_on in zip(frame_map, indicators):
                if not frame:
                    continue
                try:
                    if is_on:
                        frame.setStyleSheet('background-color: #10b981; border-radius: 10px; border: 1px solid #059669;')
                    else:
                        frame.setStyleSheet('background-color: #e5e7eb; border-radius: 10px; border: 1px solid #cbd5e0;')
                except Exception:
                    pass

            lcds = [
                getattr(self, 'lcdNumber_value1', None),
                getattr(self, 'lcdNumber_value2', None),
                getattr(self, 'lcdNumber_value3', None),
            ]
            analogs = [
                int(getattr(status, 'analog1', 0)),
                int(getattr(status, 'analog2', 0)),
                int(getattr(status, 'analog3', 0)),
            ]
            for lcd, val in zip(lcds, analogs):
                if lcd:
                    try:
                        lcd.display(int(val))
                    except Exception:
                        pass

            try:
                plc_mode = (self.mainConfig.plcGuiControl == 'plc') if hasattr(self, 'mainConfig') and self.mainConfig else False
            except Exception:
                plc_mode = False
            if plc_mode:
                slider_pairs = [
                    (getattr(self, 'slider_control1', None), int(getattr(status, 'generalControl1Value', 0))),
                    (getattr(self, 'slider_control2', None), int(getattr(status, 'generalControl2Value', 0))),
                    (getattr(self, 'slider_control3', None), int(getattr(status, 'generalControl3Value', 0))),
                ]
                for slider, val in slider_pairs:
                    if slider is None:
                        continue
                    try:
                        slider.blockSignals(True)
                        slider.setValue(int(val))
                        slider.blockSignals(False)
                    except Exception:
                        pass
        except Exception:
            pass

    # ----- Name sync helpers -----
    def _refresh_general_control_labels_from_mapping(self):
        """Update label texts to reflect any custom names stored in config mapping."""
        try:
            cfg = getattr(self, 'tanksim_config', None)
            if cfg is None or not hasattr(cfg, 'reverse_io_mapping'):
                return

            label_map = {
                'AIControl1': getattr(self, 'label_slider1', None),
                'AIControl2': getattr(self, 'label_slider2', None),
                'AIControl3': getattr(self, 'label_slider3', None),
                'DQIndicator1': getattr(self, 'label_status1', None),
                'DQIndicator2': getattr(self, 'label_status2', None),
                'DQIndicator3': getattr(self, 'label_status3', None),
                'DQIndicator4': getattr(self, 'label_status4', None),
                'DIStart': getattr(self, 'pushButton_control1', None),
                'DIStop': getattr(self, 'pushButton_control2', None),
                'DIReset': getattr(self, 'pushButton_control3', None),
                'AQAnalog1': getattr(self, 'label_value1', None),
                'AQAnalog2': getattr(self, 'label_value2', None),
                'AQAnalog3': getattr(self, 'label_value3', None),
            }

            for attr, label_widget in label_map.items():
                if label_widget is None:
                    continue
                display_name = cfg.reverse_io_mapping.get(attr, label_widget.text().replace(":", "").strip())
                suffix = ":" if label_widget.text().strip().endswith(":") else ""
                label_widget.setText(f"{display_name}{suffix}")
        except Exception:
            pass

    def _write_general_controls_to_status(self):
        """Write General Controls GUI inputs (buttons + sliders) to status in GUI mode."""
        try:
            if not hasattr(self, 'tanksim_status') or self.tanksim_status is None:
                return
            gui_mode = (self.mainConfig.plcGuiControl == 'gui') if hasattr(self, 'mainConfig') and self.mainConfig else False
            slider_vals = [
                getattr(self, 'slider_control1', None),
                getattr(self, 'slider_control2', None),
                getattr(self, 'slider_control3', None),
            ]
            values = []
            for s in slider_vals:
                try:
                    values.append(int(s.value()) if s is not None else 0)
                except Exception:
                    values.append(0)
            try:
                self.tanksim_status.generalControl1Value = values[0]
                self.tanksim_status.generalControl2Value = values[1]
                self.tanksim_status.generalControl3Value = values[2]
            except Exception:
                pass
        except Exception:
            pass

    def _on_general_controls_visibility_changed(self, visible):
        """Handle General Controls dock visibility changes"""
        try:
            # Update all 3 sidebar button states when dock is shown/hidden
            for button_name in ['pushButton_generalControls', 'pushButton_generalControls_2', 'pushButton_generalControls_3']:
                try:
                    button = getattr(self, button_name, None)
                    if button:
                        button.blockSignals(True)
                        button.setChecked(visible)
                        button.blockSignals(False)
                except Exception:
                    pass
            
            # Save state when visibility changes (removed - don't save state)
        except Exception:
            pass

    # Removed _save_general_controls_dock_state and _load_general_controls_dock_state
    # Dock always starts docked and hidden
