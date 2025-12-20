from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QDockWidget, QPushButton


class GeneralControlsMixin:
    def init_general_controls_page(self):
        """Initialize General Controls dock and sidebar buttons, sliders, and handlers."""
        # Ensure General Controls dock is not visible at startup and floats
        try:
            if hasattr(self, 'dockWidget_GeneralControls') and self.dockWidget_GeneralControls:
                self.dockWidget_GeneralControls.hide()
                try:
                    self.dockWidget_GeneralControls.setAllowedAreas(Qt.NoDockWidgetArea)
                    self.dockWidget_GeneralControls.setFeatures(
                        QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable
                    )
                    self.dockWidget_GeneralControls.setFloating(True)
                except Exception:
                    pass
        except Exception:
            pass

        # Ensure GENERAL CONTROLS sidebar buttons are unchecked initially
        try:
            if hasattr(self, 'pushButton_generalControls') and self.pushButton_generalControls:
                self.pushButton_generalControls.blockSignals(True)
                self.pushButton_generalControls.setChecked(False)
                self.pushButton_generalControls.blockSignals(False)
        except Exception:
            pass
        try:
            if hasattr(self, 'pushButton_generalControls2') and self.pushButton_generalControls2:
                self.pushButton_generalControls2.blockSignals(True)
                self.pushButton_generalControls2.setChecked(False)
                self.pushButton_generalControls2.blockSignals(False)
        except Exception:
            pass

        # Initialize sliders and buttons
        try:
            self._init_general_controls_sliders()
            self._init_general_controls_buttons()
        except Exception:
            pass

    def _init_general_controls_sliders(self):
        """Set slider ranges to 0..32747 and bind labels to show live value."""
        try:
            slider_label_pairs = [
                (getattr(self, 'slider_control1', None), getattr(self, 'label_sliderValue1', None)),
                (getattr(self, 'slider_control2', None), getattr(self, 'label_sliderValue2', None)),
                (getattr(self, 'slider_control3', None), getattr(self, 'label_sliderValue3', None)),
            ]
            for slider, label in slider_label_pairs:
                if slider:
                    slider.setMinimum(0)
                    slider.setMaximum(32747)
                    if label:
                        try:
                            label.setText(str(int(slider.value())))
                        except Exception:
                            label.setText("0")
                        slider.valueChanged.connect(lambda v, lbl=label: lbl.setText(str(int(v))))
        except Exception:
            pass

    def _init_general_controls_buttons(self):
        """Initialize Start/Stop/Reset button event handlers."""
        try:
            btn_start = getattr(self, 'pushButton_control1', None)
            btn_stop = getattr(self, 'pushButton_control2', None)
            btn_reset = getattr(self, 'pushButton_control3', None)

            if btn_start:
                btn_start.pressed.connect(lambda: self._on_start_pressed())
                btn_start.released.connect(lambda: self._on_start_released())

            if btn_stop:
                btn_stop.pressed.connect(lambda: self._on_stop_pressed())
                btn_stop.released.connect(lambda: self._on_stop_released())

            if btn_reset:
                btn_reset.pressed.connect(lambda: self._on_reset_pressed())
                btn_reset.released.connect(lambda: self._on_reset_released())
        except Exception:
            pass

    def _on_start_pressed(self):
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.generalStartCmd = True

    def _on_start_released(self):
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.generalStartCmd = False

    def _on_stop_pressed(self):
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.generalStopCmd = True

    def _on_stop_released(self):
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.generalStopCmd = False

    def _on_reset_pressed(self):
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.generalResetCmd = True

    def _on_reset_released(self):
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.generalResetCmd = False

    def go_to_general_controls(self, checked):
        """Navigate to General Controls page and toggle dock visibility."""
        try:
            if checked and not self._maybe_confirm_leave_io():
                try:
                    self.pushButton_generalControls.blockSignals(True)
                    self.pushButton_generalControls.setChecked(False)
                    self.pushButton_generalControls.blockSignals(False)
                    self.pushButton_generalControls2.blockSignals(True)
                    self.pushButton_generalControls2.setChecked(False)
                    self.pushButton_generalControls2.blockSignals(False)
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
                    try:
                        self.dockWidget_GeneralControls.setFloating(True)
                    except Exception:
                        pass
                    self.dockWidget_GeneralControls.show()
                    try:
                        self.dockWidget_GeneralControls.raise_()
                    except Exception:
                        pass
                else:
                    self.dockWidget_GeneralControls.hide()
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
