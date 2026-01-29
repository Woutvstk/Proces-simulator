"""
IO Handler - Reads configuration and simulation status, writes to PLC/GUI.

This module is responsible for:
- Reading IO_configuration.json for IO mapping
- Getting current simulation status from core.simulationManager
- Writing inputs/outputs to PLC or GUI based on active protocol
- Bridge between protocol layer and simulation layer

External Libraries Used:
- time (Python Standard Library) - Timing for button debouncing (TON logic)
- logging (Python Standard Library) - Error and debug logging
- typing (Python Standard Library) - Type hints for method signatures
"""
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class IOHandler:
    """
    Generic IO handler that bridges between protocols and simulations.
    Works with any simulation via the simulationManager interface.
    """
    
    def __init__(self):
        """Initialize the IO handler."""
        self.debug_counter = 0
        self.last_forced_values = {}
        self.outputs_reset = False
        self.button_ton_window_s = 0.03  # debounce/TON window for button writes
        self._button_ton_state = {}
        self._conflict_warned = set()
        self._last_sent_di = {}
        self._last_sent_ai = {}
        self._first_update = True  # Track first update to force initial analog writes
        self._force_write_until = None  # Timestamp until which all writes are forced (500ms period)
    
    def mapValue(self, oldMin: int, oldMax: int, newMin: int, newMax: int, old: float) -> float:
        """
        Map value from one range to another.
        
        Args:
            oldMin: Minimum of old range
            oldMax: Maximum of old range
            newMin: Minimum of new range
            newMax: Maximum of new range
            old: Value to map
            
        Returns:
            Mapped value in new range
        """
        if oldMax == oldMin:
            return float(newMin)
        return round((old - oldMin) * (newMax - newMin) / (oldMax - oldMin) + newMin, 2)
    
    def start_force_write_period(self):
        """Start a 500ms period where all IO values are force-written regardless of change."""
        self._force_write_until = time.monotonic() + 0.5  # 500ms from now
    
    def reset_io_state_for_connection(self):
        """Reset IO state after connection to ensure sensors send initial values.
        
        This ensures that digital/analog inputs that are already in their "true" state
        are written to the PLC immediately, rather than waiting for a change.
        """
        self._first_update = True  # Force all values to be written on next updateIO
        self.start_force_write_period()  # Also enable 500ms force write period
    
    def _should_force_write(self) -> bool:
        """Check if we're in the forced write period (500ms after init/connect/reload)."""
        if self._force_write_until is None:
            return False
        return time.monotonic() < self._force_write_until
    
    def _ton_ready(self, key: str, desired: bool) -> bool:
        """
        Timer-On-Delay (TON) for button debouncing.
        
        Args:
            key: Unique identifier for the button
            desired: Desired button state
            
        Returns:
            True if TON window has passed, False otherwise
        """
        state = self._button_ton_state.get(key)
        now = time.monotonic()
        if state is None:
            self._button_ton_state[key] = {"last_value": desired, "last_change": now}
            return False
        if desired != state["last_value"]:
            state["last_value"] = desired
            state["last_change"] = now
            return False
        return (now - state["last_change"]) >= self.button_ton_window_s
    
    def _addr_eq(self, a: Optional[dict], b: Optional[dict]) -> bool:
        """Check if two IO addresses are equal."""
        return bool(a and b and a.get("byte") == b.get("byte") and a.get("bit") == b.get("bit"))
    
    def _has_conflict(self, name: str, addr: Optional[dict], others: list) -> bool:
        """
        Check for IO address conflicts.
        
        Args:
            name: Signal name
            addr: Address to check
            others: List of other addresses to check against
            
        Returns:
            True if conflict detected, False otherwise
        """
        if not addr:
            return False
        for other in others:
            if self._addr_eq(addr, other):
                key = f"conflict_{name}_{addr.get('byte')}_{addr.get('bit')}"
                if key not in self._conflict_warned:
                    logger.warning(
                        f"IO address conflict: {name} shares I{addr.get('byte')}.{addr.get('bit')} "
                        f"with another signal. Adjust io_configuration.json."
                    )
                    self._conflict_warned.add(key)
                return True
        return False
    
    def _is_enabled(self, config: Any, attr_name: str) -> bool:
        """
        Check if an IO attribute is enabled in configuration.
        
        Args:
            config: Configuration object
            attr_name: Attribute name to check
            
        Returns:
            True if enabled, False otherwise
        """
        try:
            return hasattr(config, 'enabled_attrs') and (attr_name in config.enabled_attrs)
        except Exception:
            return True  # Fallback to previous behavior if not available
    
    def updateIO(self, plc: Any, mainConfig: Any, config: Any,
                 status: Any, forced_values: Optional[Dict[str, Any]] = None,
                 manual_mode: bool = False) -> None:
        """
        Bidirectional IO with force support.
        
        This method handles:
        - PLC mode: read PLC outputs and write to status (WITH FORCE OVERRIDE)
        - GUI mode: use forced values for simulator inputs
        - Manual mode: skip reading valve/heater from PLC (GUI controls those)
        - ALWAYS: write status to PLC inputs (sensors)
        - Force values have priority when writing to PLC inputs AND reading outputs
        
        Args:
            plc: Protocol communication instance
            mainConfig: Main configuration object
            config: Simulation-specific configuration
            status: Simulation-specific status
            forced_values: Dict with {attr_name: forced_value} for forced values
            manual_mode: If True, don't read valve/heater from PLC (GUI controls them)
        """
        if forced_values is None:
            forced_values = {}
        
        # Reset flag when connection is restored
        if mainConfig.plcGuiControl == "plc":
            self.outputs_reset = False
        
        self.debug_counter += 1
        debug_this_cycle = (self.debug_counter % 50 == 0)
        
        # Read PLC outputs (actuators) with force override
        # In Manual mode, skip reading valve/heater from PLC - GUI controls those
        
        if not manual_mode:
            # Valve In
            if "DQValveIn" in forced_values:
                status.valveInOpenFraction = float(1 if forced_values["DQValveIn"] else 0)
            elif "AQValveInFraction" in forced_values:
                status.valveInOpenFraction = self.mapValue(
                    0, 27648, 0, 1, forced_values["AQValveInFraction"])
            elif (mainConfig.plcGuiControl == "plc") and (config.DQValveIn or config.AQValveInFraction):
                if config.AQValveInFraction:
                    status.valveInOpenFraction = self.mapValue(
                        0, 27648, 0, 1, plc.GetAO(config.AQValveInFraction["byte"]))
                elif config.DQValveIn and plc.GetDO(config.DQValveIn["byte"], config.DQValveIn["bit"]):
                    status.valveInOpenFraction = float(1)
            
            # Valve Out
            if "DQValveOut" in forced_values:
                status.valveOutOpenFraction = float(1 if forced_values["DQValveOut"] else 0)
            elif "AQValveOutFraction" in forced_values:
                status.valveOutOpenFraction = self.mapValue(
                    0, 27648, 0, 1, forced_values["AQValveOutFraction"])
            elif (mainConfig.plcGuiControl == "plc") and (config.DQValveOut or config.AQValveOutFraction):
                # If digital output is TRUE, set to 100% (force open). Otherwise use analog value.
                if config.DQValveOut and plc.GetDO(config.DQValveOut["byte"], config.DQValveOut["bit"]):
                    status.valveOutOpenFraction = 1.0
                elif config.AQValveOutFraction:
                    status.valveOutOpenFraction = self.mapValue(
                        0, 27648, 0, 1, plc.GetAO(config.AQValveOutFraction["byte"]))
            
            # Heater
            if "DQHeater" in forced_values:
                status.heaterPowerFraction = float(1 if forced_values["DQHeater"] else 0)
            elif "AQHeaterFraction" in forced_values:
                status.heaterPowerFraction = self.mapValue(
                    0, 27648, 0, 1, forced_values["AQHeaterFraction"])
            elif (mainConfig.plcGuiControl == "plc") and (config.DQHeater or config.AQHeaterFraction):
                if config.AQHeaterFraction:
                    status.heaterPowerFraction = self.mapValue(
                        0, 27648, 0, 1, plc.GetAO(config.AQHeaterFraction["byte"]))
                elif config.DQHeater and plc.GetDO(config.DQHeater["byte"], config.DQHeater["bit"]):
                    status.heaterPowerFraction = 1
        
        # General Controls - PLC outputs: Indicators and analog values (read into status)
        self._update_indicators(plc, mainConfig, config, status, forced_values)
        self._update_analog_outputs(plc, mainConfig, config, status, forced_values)
        
        # Always write to PLC inputs (sensors) with force support
        self._write_digital_sensors(plc, mainConfig, config, status, forced_values)
        self._write_analog_sensors(plc, mainConfig, config, status, forced_values)
        
        # IMPORTANT: Write General Controls commands to PLC BEFORE reading them back
        # This ensures GUI/forced values override PLC outputs
        self._write_general_controls_commands(plc, mainConfig, config, status, forced_values)
        
        # General Controls - READ PLC inputs (Start, Stop, Reset, Sliders)
        self._read_plc_commands(plc, mainConfig, config, status, forced_values)
        
        # PIDtankValve controls
        self._write_pidvalve_controls(plc, mainConfig, config, status, forced_values)
        
        # Reset first_update flag after first successful update
        if self._first_update:
            self._first_update = False
    
    def _update_indicators(self, plc, mainConfig, config, status, forced_values):
        """Update indicator status from PLC outputs."""
        # Indicators 1..4
        for i in range(1, 5):
            key = f"DQIndicator{i}"
            attr = f"indicator{i}"
            if key in forced_values:
                setattr(status, attr, bool(forced_values[key]))
            elif (mainConfig.plcGuiControl == "plc") and hasattr(config, key):
                try:
                    addr = getattr(config, key)
                    if addr:
                        setattr(status, attr, plc.GetDO(addr["byte"], addr["bit"]))
                except Exception:
                    pass
    
    def _update_analog_outputs(self, plc, mainConfig, config, status, forced_values):
        """Update analog output values from PLC."""
        for i in range(1, 4):
            key = f"AQAnalog{i}"
            attr = f"analog{i}"
            if key in forced_values:
                setattr(status, attr, int(forced_values[key]) if forced_values[key] is not None else 0)
            elif (mainConfig.plcGuiControl == "plc") and hasattr(config, key):
                try:
                    addr = getattr(config, key)
                    if addr:
                        setattr(status, attr, int(plc.GetAO(addr["byte"])))
                except Exception:
                    pass
    
    def _write_digital_sensors(self, plc, mainConfig, config, status, forced_values):
        """Write digital sensor values to PLC inputs."""
        # Digital Level Sensor High
        if "DILevelSensorHigh" in forced_values:
            value = bool(forced_values["DILevelSensorHigh"])
        else:
            value = status.digitalLevelSensorHighTriggered if hasattr(status, 'digitalLevelSensorHighTriggered') else False
        
        if self._is_enabled(config, 'DILevelSensorHigh') and hasattr(config, 'DILevelSensorHigh'):
            addr = config.DILevelSensorHigh
            if addr and not self._has_conflict("DILevelSensorHigh", addr, 
                                              [getattr(config, 'DIStart', None), 
                                               getattr(config, 'DIStop', None), 
                                               getattr(config, 'DIReset', None)]):
                key = "DILevelSensorHigh"
                # On first update, force write even if value seems unchanged
                if self._first_update or self._last_sent_di.get(key) != value:
                    plc.SetDI(addr["byte"], addr["bit"], value)
                    self._last_sent_di[key] = value
        
        # Digital Level Sensor Low
        if "DILevelSensorLow" in forced_values:
            value = bool(forced_values["DILevelSensorLow"])
        else:
            value = status.digitalLevelSensorLowTriggered if hasattr(status, 'digitalLevelSensorLowTriggered') else False
        
        if self._is_enabled(config, 'DILevelSensorLow') and hasattr(config, 'DILevelSensorLow'):
            addr = config.DILevelSensorLow
            if addr and not self._has_conflict("DILevelSensorLow", addr,
                                              [getattr(config, 'DIStart', None),
                                               getattr(config, 'DIStop', None),
                                               getattr(config, 'DIReset', None)]):
                key = "DILevelSensorLow"
                # On first update, force write even if value seems unchanged
                if self._first_update or self._last_sent_di.get(key) != value:
                    plc.SetDI(addr["byte"], addr["bit"], value)
                    self._last_sent_di[key] = value
    
    def _write_analog_sensors(self, plc, mainConfig, config, status, forced_values):
        """Write analog sensor values to PLC inputs. Writes on change OR during 500ms init period."""
        
        # Check if we're in the forced write period
        do_force_write = self._should_force_write()
        
        # Analog Level Sensor - forced write period + change
        if "AILevelSensor" in forced_values:
            value = int(forced_values["AILevelSensor"])
        else:
            if hasattr(status, 'liquidVolume') and hasattr(config, 'tankVolume'):
                # Map tank volume (0 to tankVolume liters) to analog range 0-27648
                value = int(self.mapValue(0, config.tankVolume, 0, 27648, status.liquidVolume))
            else:
                value = 0
        
        if self._is_enabled(config, 'AILevelSensor') and hasattr(config, 'AILevelSensor'):
            addr = config.AILevelSensor
            if addr:
                key = "AILevelSensor"
                # Write if: in forced period OR first update OR value changed
                if do_force_write or self._first_update or self._last_sent_ai.get(key) != value:
                    plc.SetAI(addr["byte"], value)
                    self._last_sent_ai[key] = value
        
        # Analog Temperature Sensor - forced write period + change
        if "AITemperatureSensor" in forced_values:
            value = int(forced_values["AITemperatureSensor"])
        else:
            if hasattr(status, 'liquidTemperature'):
                # Map temperature 0 to boilingTemp (°C) to analog 0-27648
                boiling_temp = getattr(config, 'liquidBoilingTemp', 100.0)
                value = int(self.mapValue(0, boiling_temp, 0, 27648, status.liquidTemperature))
            else:
                value = 0
        
        if self._is_enabled(config, 'AITemperatureSensor') and hasattr(config, 'AITemperatureSensor'):
            addr = config.AITemperatureSensor
            if addr:
                key = "AITemperatureSensor"
                # Write if: in forced period OR first update OR value changed
                if do_force_write or self._first_update or self._last_sent_ai.get(key) != value:
                    plc.SetAI(addr["byte"], value)
                    self._last_sent_ai[key] = value
    
    
    def _write_general_controls_commands(self, plc, mainConfig, config, status, forced_values):
        """Write General Controls (Start/Stop/Reset buttons and sliders) to PLC inputs."""
        
        # Check if we're in the forced write period (500ms after init/connect/reload)
        do_force_write = self._should_force_write()
        
        # Write digital command buttons (Start, Stop, Reset) to PLC inputs
        for cmd in ['Start', 'Stop', 'Reset']:
            key = f"DI{cmd}"
            attr = f"general{cmd}Cmd"
            
            # Determine value to write
            if key in forced_values:
                desired = bool(forced_values[key])
            elif hasattr(status, attr):
                desired = bool(getattr(status, attr, False))
            else:
                continue
            
            # Write to PLC if address is configured - all buttons write on change or forced period
            if self._is_enabled(config, key) and hasattr(config, key):
                addr = getattr(config, key)
                if addr:
                    cache_key = key
                    # Write on change or during forced period
                    if do_force_write or self._first_update or self._last_sent_di.get(cache_key) != desired:
                        plc.SetDI(addr["byte"], addr["bit"], desired)
                        self._last_sent_di[cache_key] = desired
        
        # Write analog control sliders (Control1, Control2, Control3) to PLC inputs
        for i in range(1, 4):
            key = f"AIControl{i}"
            attr = f"generalControl{i}Value"
            
            # Determine value to write
            if key in forced_values:
                value = int(forced_values[key]) if forced_values[key] is not None else 0
            elif hasattr(status, attr):
                value = int(getattr(status, attr, 0))
            else:
                continue
            
            # Write to PLC if address is configured
            if self._is_enabled(config, key) and hasattr(config, key):
                addr = getattr(config, key)
                if addr:
                    cache_key = key
                    # Write on change or during forced period
                    if do_force_write or self._first_update or self._last_sent_ai.get(cache_key) != value:
                        plc.SetAI(addr["byte"], value)
                        self._last_sent_ai[cache_key] = value
                        self._last_sent_ai[cache_key] = value
    
    def _read_plc_commands(self, plc, mainConfig, config, status, forced_values):
        """Read command buttons and sliders from PLC."""
        # Start/Stop/Reset
        for cmd in ['Start', 'Stop', 'Reset']:
            key = f"DI{cmd}"
            attr = f"general{cmd}Cmd"
            if key in forced_values:
                setattr(status, attr, bool(forced_values[key]))
            elif (mainConfig.plcGuiControl == "plc") and hasattr(config, key):
                try:
                    addr = getattr(config, key)
                    if addr:
                        setattr(status, attr, plc.GetDI(addr["byte"], addr["bit"]))
                except Exception:
                    pass
        
        # Control sliders 1..3
        for i in range(1, 4):
            key = f"AIControl{i}"
            attr = f"generalControl{i}Value"
            if key in forced_values:
                setattr(status, attr, int(forced_values[key]) if forced_values[key] is not None else 0)
            elif (mainConfig.plcGuiControl == "plc") and hasattr(config, key):
                try:
                    addr = getattr(config, key)
                    if addr:
                        setattr(status, attr, int(plc.GetAI(addr["byte"])))
                except Exception:
                    pass
    
    def _read_pidvalve_controls(self, plc, mainConfig, config, status, forced_values):
        # Read PIDValve buttons and radios from PLC
        for name in [
            'PidValveStart', 'PidValveStop', 'PidValveReset',
            'PidValveAuto', 'PidValveMan',
            'PidTankValveAItemp', 'PidTankValveDItemp',
            'PidTankValveAIlevel', 'PidTankValveDIlevel'
        ]:
            key = f"DI{name}"
            attr = f"pid{name}Cmd"
            if key in forced_values:
                setattr(status, attr, bool(forced_values[key]))
            elif (mainConfig.plcGuiControl == "plc") and hasattr(config, key):
                try:
                    addr = getattr(config, key)
                    if addr:
                        setattr(status, attr, plc.GetDI(addr["byte"], addr["bit"]))
                except Exception:
                    pass
        # Read sliders
        for name in ['PidTankTempSP', 'PidTankLevelSP']:
            key = f"AI{name}"
            attr = f"pid{name}Value"
            if key in forced_values:
                setattr(status, attr, int(forced_values[key]) if forced_values[key] is not None else 0)
            elif (mainConfig.plcGuiControl == "plc") and hasattr(config, key):
                try:
                    addr = getattr(config, key)
                    if addr:
                        setattr(status, attr, int(plc.GetAI(addr["byte"])))
                except Exception:
                    pass

    def _write_pidvalve_controls(self, plc, mainConfig, config, status, forced_values):
        """Write GUI values to PLC inputs for PIDValve controls (Start/Stop/Reset, Mode, SP).
        Non-button signals write on change OR during 500ms forced write period."""
        
        # Check if we're in the forced write period (500ms after init/connect/reload)
        do_force_write = self._should_force_write()
        
        # Write digital control radios (Auto, Man, Temp increment, Level increment) - forced period + change
        mode_signals = ['PidValveAuto', 'PidValveMan', 'PidTankValveAItemp', 'PidTankValveDItemp', 'PidTankValveAIlevel', 'PidTankValveDIlevel']
        for name in mode_signals:
            key = f"DI{name}"
            attr = f"pid{name}Cmd"
            
            # Determine value to write
            if key in forced_values:
                desired = bool(forced_values[key])
            elif hasattr(config, key) and hasattr(status, attr):
                desired = bool(getattr(status, attr, False))
            else:
                continue
            
            # Write to PLC if address is configured - forced period OR on change OR first update
            is_enabled = self._is_enabled(config, key)
            has_attr = hasattr(config, key)
            if is_enabled and has_attr:
                addr = getattr(config, key)
                if addr:
                    ton_ready = self._first_update or self._ton_ready(key, desired)
                    if ton_ready:
                        cache_key = key
                        # Write if: in forced period OR first update OR value changed
                        if do_force_write or self._first_update or self._last_sent_di.get(cache_key) != desired:
                            plc.SetDI(addr["byte"], addr["bit"], desired)
                            self._last_sent_di[cache_key] = desired
        
        # Write button commands on change only (not cyclic)
        # NOTE: PidValve buttons use pidPidValveStartCmd/Stop/ResetCmd (separate from General Controls)
        button_signals = [
            ('PidValveStart', 'DIPidValveStart', 'pidPidValveStartCmd'),
            ('PidValveStop', 'DIPidValveStop', 'pidPidValveStopCmd'),
            ('PidValveReset', 'DIPidValveReset', 'pidPidValveResetCmd')
        ]
        for name, key_di, status_attr in button_signals:
            # Determine value to write
            if key_di in forced_values:
                desired = bool(forced_values[key_di])
            elif hasattr(status, status_attr):
                desired = bool(getattr(status, status_attr, False))
            else:
                continue
            
            # Write to PLC if address is configured - on change only
            is_enabled = self._is_enabled(config, key_di)
            has_attr = hasattr(config, key_di)
            if is_enabled and has_attr:
                addr = getattr(config, key_di)
                if addr:
                    cache_key = key_di
                    # For buttons, write on change only (not cyclic)
                    if self._last_sent_di.get(cache_key) != desired:
                        plc.SetDI(addr["byte"], addr["bit"], desired)
                        self._last_sent_di[cache_key] = desired
        
        # Write analog setpoint sliders (TempSP, LevelSP) to PLC inputs - forced period + change
        for name in ['PidTankTempSP', 'PidTankLevelSP']:
            key = f"AI{name}"
            attr = f"pid{name}Value"
            
            # Determine value to write
            if key in forced_values:
                value = int(forced_values[key]) if forced_values[key] is not None else 0
            elif hasattr(config, key) and hasattr(status, attr):
                value = int(getattr(status, attr, 0))
            else:
                continue
            
            # Write to PLC if address is configured - forced period OR on change
            is_enabled = self._is_enabled(config, key)
            has_attr = hasattr(config, key)
            if is_enabled and has_attr:
                addr = getattr(config, key)
                if addr:
                    cache_key = key
                    # Write if: in forced period OR value changed
                    if do_force_write or self._last_sent_ai.get(cache_key) != value:
                        plc.SetAI(addr["byte"], value)
                        self._last_sent_ai[cache_key] = value

    def resetOutputs(self, mainConfig: Any, config: Any, status: Any) -> None:
        """
        Reset actuators when PLC connection is lost.
        
        Args:
            mainConfig: Main configuration object
            config: Simulation-specific configuration
            status: Simulation-specific status
        """
        if mainConfig.plcGuiControl == "plc":
            # Reset actuators
            if hasattr(status, 'valveInOpenFraction'):
                status.valveInOpenFraction = float(0)
            if hasattr(status, 'valveOutOpenFraction'):
                status.valveOutOpenFraction = float(0)
            if hasattr(status, 'heaterPowerFraction'):
                status.heaterPowerFraction = float(0)
            
            # Reset general controls commands/sliders
            if hasattr(status, 'generalStartCmd'):
                status.generalStartCmd = False
            if hasattr(status, 'generalStopCmd'):
                status.generalStopCmd = False
            if hasattr(status, 'generalResetCmd'):
                status.generalResetCmd = False
            if hasattr(status, 'generalControl1Value'):
                status.generalControl1Value = 0
            if hasattr(status, 'generalControl2Value'):
                status.generalControl2Value = 0
            if hasattr(status, 'generalControl3Value'):
                status.generalControl3Value = 0
            
            if not self.outputs_reset:
                logger.info("PLC outputs reset (no connection)")
                self.outputs_reset = True
