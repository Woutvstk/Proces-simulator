from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer

# Import for address updates
from gui.customWidgets import ReadOnlyTableWidgetItem


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
            self.controlerDropDown.currentIndexChanged.connect(
                self.on_controller_changed)

            # Disable connect button in GUI mode
            initial_mode = self.controlerDropDown.currentText()
            if initial_mode == "GUI":
                try:
                    self.pushButton_connect.setEnabled(False)
                except AttributeError:
                    pass

        except AttributeError as e:
            pass

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

        if hasattr(self, 'mainConfig') and self.mainConfig:
            old_protocol = self.mainConfig.plcProtocol
            self.mainConfig.plcProtocol = new_controller

            if new_controller == "GUI":
                self.mainConfig.plcGuiControl = "gui"
                try:
                    self.pushButton_connect.setEnabled(False)
                except:
                    pass
            else:
                self.mainConfig.plcGuiControl = "plc"
                try:
                    self.pushButton_connect.setEnabled(True)
                except:
                    pass

            # Disconnect if switching to GUI mode
            if new_controller == "GUI" and hasattr(self, 'validPlcConnection') and self.validPlcConnection:
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
            if (old_protocol == "logo!" or new_controller == "logo!") and old_protocol != new_controller:
                self._update_addresses_for_controller_change(
                    old_protocol, new_controller)

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