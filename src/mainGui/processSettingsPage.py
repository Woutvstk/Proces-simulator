from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer

from tankSim.gui import VatWidget
from conveyor.gui import TransportbandWidget

# Import for address updates
from mainGui.customWidgets import ReadOnlyTableWidgetItem

class ProcessSettingsMixin:
    """
    Mixin class for process settings functionality
    Combined with MainWindow via multiple inheritance
    """
    
    def init_process_settings_page(self):
        """Initialize all process settings page components"""
        self._init_vat_widget()
        self._init_transportband_widget()
        self._init_color_dropdown()
        self._init_controller_dropdown()
        self._init_checkboxes()
        self._init_entry_fields()
        self._init_simulation_button()
    
    def _init_vat_widget(self):
        """Initialize VatWidget"""
        try:
            self.vat_widget = VatWidget()
            container = self.findChild(QWidget, "vatWidgetContainer")
            
            if container:
                existing_layout = container.layout()
                
                if existing_layout is None:
                    container_layout = QVBoxLayout(container)
                    container_layout.setContentsMargins(0, 0, 0, 0)
                else:
                    container_layout = existing_layout
                    container_layout.setContentsMargins(0, 0, 0, 0)
                
                container_layout.addWidget(self.vat_widget)
                # Removed unnecessary print
        except Exception as e:
            # Removed unnecessary print
            pass # Silently fail if widget container is missing
    
    def _init_transportband_widget(self):
        """Initialize TransportbandWidget (Conveyor Belt Widget)"""
        try:
            self.transportband_widget = TransportbandWidget()
            container_transportband = self.findChild(QWidget, "transportbandWidgetContainer")
            
            if container_transportband:
                existing_layout = container_transportband.layout()
                if existing_layout is None:
                    container_layout = QVBoxLayout(container_transportband)
                    container_layout.setContentsMargins(0, 0, 0, 0)
                else:
                    container_layout = existing_layout
                    container_layout.setContentsMargins(0, 0, 0, 0)
                
                container_layout.addWidget(self.transportband_widget)
                # Removed unnecessary print
        except Exception as e:
            # Removed unnecessary print
            pass # Silently fail if widget container is missing
    
    def _init_color_dropdown(self):
        """Initialize color dropdown"""
        try:
            self.kleurDropDown.clear()
            colors = [
                ("Blue", "#0000FF"),
                ("Red", "#FB5C5C"),
                ("Green", "#00FF00"),
                ("Yellow", "#FAFA2B"),
                ("Orange", "#FFB52B"),
                ("Purple", "#800080"),
                ("Gray", "#808080"),
            ]
            for name, hexcode in colors:
                self.kleurDropDown.addItem(name, hexcode)
            
            self.kleurDropDown.currentIndexChanged.connect(self.on_kleur_changed)
            # Removed unnecessary print
        except AttributeError as e:
            # Removed unnecessary print
            pass
    
    def _init_controller_dropdown(self):
        """Initialize controller dropdown"""
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
            
            self.controlerDropDown.setCurrentText("GUI")
            self.controlerDropDown.currentIndexChanged.connect(self.on_controller_changed)
            
            # Disable connect button in GUI mode
            initial_mode = self.controlerDropDown.currentText()
            if initial_mode == "GUI":
                try:
                    self.pushButton_connect.setEnabled(False)
                except AttributeError:
                    pass
            
            # Removed unnecessary print
        except AttributeError as e:
            # Removed unnecessary print
            pass
    
    def _init_checkboxes(self):
        """Connect all checkboxes"""
        try:
            self.regelbareKlepenCheckBox.toggled.connect(self.on_config_changed)
            self.regelbareWeerstandCheckBox.toggled.connect(self.on_config_changed)
            self.niveauschakelaarCheckBox.toggled.connect(self.on_config_changed)
            self.analogeWaardeTempCheckBox.toggled.connect(self.on_config_changed)
        except AttributeError as e:
            # Removed unnecessary print
            pass
    
    def _init_entry_fields(self):
        """Synchronize entry fields (flow and temp)"""
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
            # Removed unnecessary print
            pass
    
    def _init_simulation_button(self):
        """Initialize simulation start/stop button"""
        try:
            self.pushButton_startSimulatie.setCheckable(True)
            self.pushButton_startSimulatie.toggled.connect(self.toggle_simulation)
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
            # Removed unnecessary print
            pass
    
    def update_process_values(self):
        """
        Update all values from UI to vat widget
        Called from the main update loop
        """
        try:
            # Read values from UI
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
            
            # Water color
            self.vat_widget.kleurWater = self.kleurDropDown.currentData()
            
            # UI Elements visibility
            is_gui_mode = (controller_mode == "GUI")
            
            try:
                if is_gui_mode and self.vat_widget.regelbareKleppen:
                    if not self.regelbareKlepenGUISim.isVisible():
                        self.GUiSim.hide()
                        self.regelbareKlepenGUISim.show()
                elif is_gui_mode and not self.vat_widget.regelbareKleppen:
                    if not self.GUiSim.isVisible():
                        self.regelbareKlepenGUISim.hide()
                        self.GUiSim.show()
                else:
                    if self.GUiSim.isVisible() or self.regelbareKlepenGUISim.isVisible():
                        self.GUiSim.hide()
                        self.regelbareKlepenGUISim.hide()
            except AttributeError:
                pass
            
            # Valve positions (Klep standen)
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
                    top_checked = self.klepstandBovenCheckBox.isChecked()
                    bottom_checked = self.klepstandBenedenCheckBox.isChecked()
                    self.vat_widget.KlepStandBoven = 100 if top_checked else 0
                    self.vat_widget.KlepStandBeneden = 100 if bottom_checked else 0
                except AttributeError:
                    pass
        
        except Exception as e:
            pass  # Silently ignore during init or minor update issues
        
        # Write to status object (GUI MODE)
        if not hasattr(self, 'tanksim_status') or self.tanksim_status is None:
            return
        
        if not hasattr(self, 'mainConfig') or self.mainConfig is None:
            return
        
        if self.mainConfig.plcGuiControl == "gui":
            self.tanksim_status.valveInOpenFraction = self.vat_widget.KlepStandBoven / 100.0
            self.tanksim_status.valveOutOpenFraction = self.vat_widget.KlepStandBeneden / 100.0
            
            if self.vat_widget.regelbareWeerstand:
                # Assuming 0.5 is a placeholder for a controllable value not yet implemented
                self.tanksim_status.heaterPowerFraction = 0.5 
            else:
                try:
                    heater_on = self.weerstandCheckBox.isChecked()
                    self.tanksim_status.heaterPowerFraction = 1.0 if heater_on else 0.0
                except:
                    self.tanksim_status.heaterPowerFraction = 0.0
        
        # Read back status for visual feedback
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            import tankSim.gui as gui_module
            gui_module.currentHoogteVat = self.tanksim_status.liquidVolume
            gui_module.tempVat = self.tanksim_status.liquidTemperature
        
        # Rebuild SVG
        self.vat_widget.rebuild()
    
    def on_kleur_changed(self):
        """Callback when color dropdown changes"""
        new_color = self.kleurDropDown.currentData()
        self.vat_widget.kleurWater = new_color
    
    def on_config_changed(self):
        """Callback when configuration checkbox changes"""
        pass  # Force rebuild via update_values (handled by main loop)
    
    def syncFields(self, text, group):
        """Synchronize linked entry fields"""
        for field in group:
            if field.text() != text:
                field.blockSignals(True)
                field.setText(text)
                field.blockSignals(False)
    
    def start_simulation(self):
        """Start the simulation"""
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.simRunning = True

    def stop_simulation(self):
        """Stop the simulation"""
        if hasattr(self, 'tanksim_status') and self.tanksim_status:
            self.tanksim_status.simRunning = False

    def toggle_simulation(self, checked):
        """Toggle simulation on/off with visual feedback"""
        if checked:
            self.start_simulation()
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

    def on_controller_changed(self):
        """Callback when controller dropdown changes"""
        new_controller = self.controlerDropDown.currentText()
        self.vat_widget.controler = new_controller
        
        if hasattr(self, 'mainConfig') and self.mainConfig:
            old_protocol = self.mainConfig.plcProtocol
            self.mainConfig.plcProtocol = new_controller
            
            if new_controller == "GUI":
                self.mainConfig.plcGuiControl = "gui"
                try:
                    self.pushButton_connect.setEnabled(False)
                    # Removed unnecessary print
                except:
                    pass
            else:
                self.mainConfig.plcGuiControl = "plc"
                try:
                    self.pushButton_connect.setEnabled(True)
                    # Removed unnecessary print
                except:
                    pass
            
            # Disconnect if switching to GUI mode
            if new_controller == "GUI" and hasattr(self, 'validPlcConnection') and self.validPlcConnection:
                if hasattr(self, 'plc') and self.plc:
                    try:
                        self.plc.disconnect()
                        # Removed unnecessary print
                    except:
                        pass
                self.validPlcConnection = False
                self.plc = None
                self.update_connection_status_icon()
                try:
                    self.pushButton_connect.blockSignals(True)
                    self.pushButton_connect.setChecked(False)
                    self.pushButton_connect.blockSignals(False)
                except:
                    pass
            
            # Update addresses if switching to/from LOGO!
            if (old_protocol == "logo!" or new_controller == "logo!") and old_protocol != new_controller:
                self._update_addresses_for_controller_change(old_protocol, new_controller)
        
        self.vat_widget.rebuild()

    def _update_addresses_for_controller_change(self, old_protocol, new_protocol):
        """Update all addresses when switching to/from LOGO!"""
        try:
            if not hasattr(self, 'io_screen') or not hasattr(self, 'tableWidget_IO'):
                return
            
            table = self.tableWidget_IO
            table.blockSignals(True)
            
            # Determine if switching to or from LOGO!
            to_logo = (new_protocol == "logo!")
            from_logo = (old_protocol == "logo!")
            
            # Removed unnecessary print
            
            # Update all addresses in the table
            for row in range(table.rowCount()):
                addr_item = table.item(row, 4)
                if not addr_item or not addr_item.text():
                    continue
                
                current_address = addr_item.text()
                
                # Skip if address is empty
                if not current_address:
                    continue
                
                new_address = current_address
                
                if to_logo:
                    # Replace I or Q with V
                    if current_address[0] in ['I', 'Q']:
                        new_address = 'V' + current_address[1:]
                elif from_logo:
                    # Replace V with I or Q (determine from signal type)
                    if current_address[0] == 'V':
                        name_item = table.item(row, 0)
                        if name_item and name_item.text():
                            signal_name = name_item.text()
                            # Determine if it is input or output
                            if hasattr(self, 'tanksim_config') and self.tanksim_config:
                                if signal_name in self.tanksim_config.io_signal_mapping:
                                    attr_name = self.tanksim_config.io_signal_mapping[signal_name]
                                    # Outputs start with DQ or AQ
                                    if attr_name.startswith(('DQ', 'AQ')):
                                        new_address = 'Q' + current_address[1:]
                                    else:
                                        new_address = 'I' + current_address[1:]
                
                # Update only if there is a change
                if new_address != current_address:
                    table.setItem(row, 4, ReadOnlyTableWidgetItem(new_address))
                    try:
                        table._save_row_data(row)
                    except AttributeError:
                        pass
                    # Removed unnecessary print
            
            table.blockSignals(False)
            
            # Save configuration
            if hasattr(self, 'io_screen'):
                self.io_screen.save_configuration()
            
            # Removed unnecessary print
            
        except Exception as e:
            # Removed unnecessary print
            table.blockSignals(False)