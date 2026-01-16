from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer

# Import for address updates
from gui.customWidgets import ReadOnlyTableWidgetItem

# Import conveyor widget
from simulations.conveyor.gui import ConveyorWidget


class ProcessSettingsMixin:
    """
    Mixin class for GENERAL process settings functionality
    Only contains settings that apply to ALL simulations
    Combined with MainWindow via multiple inheritance
    """

    def init_process_settings_page(self):
        """Initialize general process settings (controller selection only)"""
        self._init_controller_dropdown()
        self._init_network_port_combobox()
        self._init_conveyor_widget()
        # Initialize label after controller dropdown so it shows correct initial value
        self._init_active_method_label()

    def _init_active_method_label(self):
        """Initialize the active method label to show current protocol"""
        try:
            if hasattr(self, 'ActiveMethodLabel'):
                # Set initial text based on current protocol
                if hasattr(self, 'mainConfig') and self.mainConfig:
                    protocol = self.mainConfig.plcProtocol
                    self._update_active_method_label(protocol)
        except AttributeError:
            pass

    def _update_active_method_label(self, protocol):
        """Update the active method label text
        
        Args:
            protocol: The protocol name to display
        """
        try:
            if hasattr(self, 'ActiveMethodLabel'):
                self.ActiveMethodLabel.setText(f"Active: {protocol}")
        except AttributeError:
            pass

    def _init_controller_dropdown(self):
        """Initialize controller dropdown"""
        try:
            self.controlerDropDown.clear()
            controllers = [
                "GUI (MIL)",
                "logo! (HIL)",
                "PLC S7-1500/1200/400/300/ET 200SP (HIL)",
                "PLCSim S7-1500 advanced (SIL)",
                "PLCSim S7-1500/1200/400/300/ET 200SP (SIL)"
            ]

            for controller in controllers:
                self.controlerDropDown.addItem(controller)

            self.controlerDropDown.setCurrentText("GUI (MIL)")
            
            # Update mainConfig to match initial GUI selection
            if hasattr(self, 'mainConfig') and self.mainConfig:
                self.mainConfig.plcProtocol = "GUI"
                self.mainConfig.plcGuiControl = "gui"
            
            self.controlerDropDown.currentTextChanged.connect(
                self.on_controller_changed)

            # Disable connect button in GUI mode
            initial_controller = self.controlerDropDown.currentText()
            initial_mode = self._get_controller_name(initial_controller)
            if initial_mode == "GUI":
                try:
                    self.pushButton_connect.setEnabled(False)
                    self.lineEdit_IPAddress.setEnabled(False)
                except AttributeError:
                    pass

        except AttributeError as e:
            pass

    def _get_controller_name(self, controller_str):
        """Extract base controller name from 'name (MODE)' format
        
        Args:
            controller_str: Controller dropdown text like "GUI (MIL)" or "logo! (HIL)"
            
        Returns:
            Base controller name like "GUI" or "logo!"
        """
        if '(' in controller_str:
            return controller_str[:controller_str.rfind('(')].strip()
        return controller_str

    def _init_network_port_combobox(self):
        """Initialize network adapter combobox"""
        try:
            import socket
            self.comboBox_networkPort.clear()
            self.comboBox_networkPort.addItem("Auto (System Default)", "auto")

            adapters_found = False

            try:
                import wmi
                c = wmi.WMI()
                for interface in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
                    if interface.IPAddress:
                        ipv4_addr = None
                        for ip in interface.IPAddress:
                            if '.' in ip and not ip.startswith('127.'):
                                ipv4_addr = ip
                                break
                        if ipv4_addr:
                            adapter_name = interface.Description
                            display_name = f"{adapter_name} ({ipv4_addr})"
                            self.comboBox_networkPort.addItem(display_name, adapter_name)
                            adapters_found = True
            except:
                pass

            if not adapters_found:
                try:
                    import psutil
                    net_if_addrs = psutil.net_if_addrs()
                    net_if_stats = psutil.net_if_stats()

                    for interface_name, addresses in net_if_addrs.items():
                        if interface_name in net_if_stats:
                            if not net_if_stats[interface_name].isup:
                                continue

                        ipv4_addr = None
                        for addr in addresses:
                            if addr.family == socket.AF_INET:
                                ipv4_addr = addr.address
                                break

                        if ipv4_addr and ipv4_addr != '127.0.0.1':
                            display_name = f"{interface_name} ({ipv4_addr})"
                            self.comboBox_networkPort.addItem(display_name, interface_name)
                            adapters_found = True
                except:
                    pass

            if not adapters_found:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    s.close()
                    self.comboBox_networkPort.addItem(f"Primary Adapter ({local_ip})", "primary")
                except:
                    pass

            self.comboBox_networkPort.currentIndexChanged.connect(self._on_network_port_changed)
        except:
            pass

    def _init_conveyor_widget(self):
        """Initialize ConveyorWidget"""
        try:
            self.conveyor_widget = ConveyorWidget()
            container = self.findChild(QWidget, "conveyorWidgetContainer")

            if container:
                # Clear existing layout items (spacers, etc)
                existing_layout = container.layout()
                if existing_layout is not None:
                    while existing_layout.count():
                        item = existing_layout.takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                    container_layout = existing_layout
                else:
                    container_layout = QVBoxLayout(container)
                
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(0)
                container_layout.addWidget(self.conveyor_widget, 1)
        except Exception as e:
            pass  # Silently fail if widget container is missing

    def _on_network_port_changed(self, index):
        """Handle network port change"""
        try:
            selected_adapter = self.comboBox_networkPort.currentData()
            if hasattr(self, 'mainConfig') and self.mainConfig:
                self.mainConfig.selectedNetworkAdapter = selected_adapter
        except:
            pass

    def on_controller_changed(self):
        """Callback when controller dropdown changes"""
        new_controller = self.controlerDropDown.currentText()
        new_controller_name = self._get_controller_name(new_controller)

        if hasattr(self, 'mainConfig') and self.mainConfig:
            old_protocol = self.mainConfig.plcProtocol
            self.mainConfig.plcProtocol = new_controller_name
            
            # Update the active method label
            self._update_active_method_label(new_controller_name)

            if new_controller_name == "GUI":
                self.mainConfig.plcGuiControl = "gui"
                try:
                    self.pushButton_connect.setEnabled(False)
                    self.lineEdit_IPAddress.setEnabled(False)
                except:
                    pass
            else:
                self.mainConfig.plcGuiControl = "plc"
                try:
                    self.pushButton_connect.setEnabled(True)
                    self.lineEdit_IPAddress.setEnabled(True)
                except:
                    pass

            # Auto-set IP based on protocol
            if "PLCSim" in new_controller_name:
                self.mainConfig.plcIpAdress = "127.0.0.1"
                try:
                    if hasattr(self, 'lineEdit_IPAddress'):
                        self.lineEdit_IPAddress.blockSignals(True)
                        self.lineEdit_IPAddress.setText("127.0.0.1")
                        self.lineEdit_IPAddress.blockSignals(False)
                except:
                    pass
            elif new_controller_name in ["PLC S7-1500/1200/400/300/ET 200SP", "logo!"]:
                self.mainConfig.plcIpAdress = "192.168.0.1"
                try:
                    if hasattr(self, 'lineEdit_IPAddress'):
                        self.lineEdit_IPAddress.blockSignals(True)
                        self.lineEdit_IPAddress.setText("192.168.0.1")
                        self.lineEdit_IPAddress.blockSignals(False)
                except:
                    pass

            # Disconnect if connection is active and protocol is being changed
            if hasattr(self, 'validPlcConnection') and self.validPlcConnection:
                if hasattr(self, 'plc') and self.plc:
                    try:
                        self.plc.disconnect()
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
            if (old_protocol == "logo!" or new_controller_name == "logo!") and old_protocol != new_controller_name:
                self._update_addresses_for_controller_change(
                    old_protocol, new_controller_name)

        # Update tank widget controller mode if it exists
        if hasattr(self, 'vat_widget'):
            self.vat_widget.controler = new_controller
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

            table.blockSignals(False)

            # Save configuration
            if hasattr(self, 'io_screen'):
                self.io_screen.save_configuration()

        except Exception as e:
            table.blockSignals(False)