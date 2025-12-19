import time

from configuration import configuration as mainConfigClass
from tankSim.configurationTS import configuration as configurationClass
from tankSim.status import status as statusClass
from plcCom.logoS7 import logoS7


class ioHandler:

    def __init__(self):
        self.debug_counter = 0
        self.last_forced_values = {}
        self.outputs_reset = False
        self.button_ton_window_s = 0.03  # debounce/TON window for button writes
        self._button_ton_state = {}
        self._conflict_warned = set()
        self._last_sent_di = {}
        self._last_sent_ai = {}

    def mapValue(self, oldMin: int, oldMax: int, newMin: int, newMax: int, old: float) -> float:
        """Map value from one range to another"""
        if oldMax == oldMin:
            return float(newMin)
        return round((old-oldMin)*(newMax-newMin)/(oldMax-oldMin)+newMin, 2)

    def _ton_ready(self, key: str, desired: bool) -> bool:
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

    def _addr_eq(self, a: dict | None, b: dict | None) -> bool:
        return bool(a and b and a.get("byte") == b.get("byte") and a.get("bit") == b.get("bit"))

    def _has_conflict(self, name: str, addr: dict | None, others: list[dict | None]) -> bool:
        if not addr:
            return False
        for other in others:
            if self._addr_eq(addr, other):
                key = f"conflict_{name}_{addr.get('byte')}_{addr.get('bit')}"
                if key not in self._conflict_warned:
                    print(f"IO address conflict: {name} shares I{addr.get('byte')}.{addr.get('bit')} with another signal. Adjust io_configuration.json.")
                    self._conflict_warned.add(key)
                return True
        return False

    def _is_enabled(self, config: configurationClass, attr_name: str) -> bool:
        try:
            return hasattr(config, 'enabled_attrs') and (attr_name in config.enabled_attrs)
        except Exception:
            return True  # fallback to previous behavior if not available

    def updateIO(self, plc: logoS7, mainConfig: mainConfigClass, config: configurationClass,
                 status: statusClass, forced_values: dict = None):
        """
        Bidirectional IO with force support:
        - PLC mode: read PLC outputs and write to status (WITH FORCE OVERRIDE)
        - GUI mode: use forced values for simulator inputs
        - ALWAYS: write status to PLC inputs (sensors)
        - Force values have priority when writing to PLC inputs AND reading outputs

        Args:
            forced_values: Dict with {attr_name: forced_value} for forced values
        """
        if forced_values is None:
            forced_values = {}


        # Reset flag when connection is restored
        if mainConfig.plcGuiControl == "plc":
            self.outputs_reset = False

        self.debug_counter += 1
        debug_this_cycle = (self.debug_counter % 50 == 0)

        # Read PLC outputs (actuators) with force override

        # Valve In
        if "DQValveIn" in forced_values:
            status.valveInOpenFraction = float(
                1 if forced_values["DQValveIn"] else 0)
        elif "AQValveInFraction" in forced_values:
            status.valveInOpenFraction = self.mapValue(
                0, plc.analogMax, 0, 1, forced_values["AQValveInFraction"])
        elif (mainConfig.plcGuiControl == "plc") and (config.DQValveIn or config.AQValveInFraction):
            if config.DQValveIn and plc.GetDO(config.DQValveIn["byte"], config.DQValveIn["bit"]):
                status.valveInOpenFraction = float(1)
            elif config.AQValveInFraction:
                status.valveInOpenFraction = self.mapValue(
                    0, plc.analogMax, 0, 1, plc.GetAO(config.AQValveInFraction["byte"]))

        # Valve Out
        if "DQValveOut" in forced_values:
            status.valveOutOpenFraction = float(
                1 if forced_values["DQValveOut"] else 0)
        elif "AQValveOutFraction" in forced_values:
            status.valveOutOpenFraction = self.mapValue(
                0, plc.analogMax, 0, 1, forced_values["AQValveOutFraction"])
        elif (mainConfig.plcGuiControl == "plc") and (config.DQValveOut or config.AQValveOutFraction):
            if config.DQValveOut and plc.GetDO(config.DQValveOut["byte"], config.DQValveOut["bit"]):
                status.valveOutOpenFraction = 1
            elif config.AQValveOutFraction:
                status.valveOutOpenFraction = self.mapValue(
                    0, plc.analogMax, 0, 1, plc.GetAO(config.AQValveOutFraction["byte"]))

        # Heater
        if "DQHeater" in forced_values:
            status.heaterPowerFraction = float(
                1 if forced_values["DQHeater"] else 0)
        elif "AQHeaterFraction" in forced_values:
            status.heaterPowerFraction = self.mapValue(
                0, plc.analogMax, 0, 1, forced_values["AQHeaterFraction"])
        elif (mainConfig.plcGuiControl == "plc") and (config.DQHeater or config.AQHeaterFraction):
            if config.DQHeater and plc.GetDO(config.DQHeater["byte"], config.DQHeater["bit"]):
                status.heaterPowerFraction = 1
            elif config.AQHeaterFraction:
                status.heaterPowerFraction = self.mapValue(
                    0, plc.analogMax, 0, 1, plc.GetAO(config.AQHeaterFraction["byte"]))

        # General Controls - PLC outputs: Indicators and analog values (read into status)
        # Indicators 1..4
        if "DQIndicator1" in forced_values:
            status.indicator1 = bool(forced_values["DQIndicator1"])
        elif (mainConfig.plcGuiControl == "plc") and config.DQIndicator1:
            try:
                status.indicator1 = plc.GetDO(config.DQIndicator1["byte"], config.DQIndicator1["bit"])
            except Exception:
                pass

        if "DQIndicator2" in forced_values:
            status.indicator2 = bool(forced_values["DQIndicator2"])
        elif (mainConfig.plcGuiControl == "plc") and config.DQIndicator2:
            try:
                status.indicator2 = plc.GetDO(config.DQIndicator2["byte"], config.DQIndicator2["bit"])
            except Exception:
                pass

        if "DQIndicator3" in forced_values:
            status.indicator3 = bool(forced_values["DQIndicator3"])
        elif (mainConfig.plcGuiControl == "plc") and config.DQIndicator3:
            try:
                status.indicator3 = plc.GetDO(config.DQIndicator3["byte"], config.DQIndicator3["bit"])
            except Exception:
                pass

        if "DQIndicator4" in forced_values:
            status.indicator4 = bool(forced_values["DQIndicator4"])
        elif (mainConfig.plcGuiControl == "plc") and config.DQIndicator4:
            try:
                status.indicator4 = plc.GetDO(config.DQIndicator4["byte"], config.DQIndicator4["bit"])
            except Exception:
                pass

        # Analog values 1..3 (PLC outputs)
        if "AQAnalog1" in forced_values:
            status.analog1 = int(forced_values["AQAnalog1"]) if forced_values["AQAnalog1"] is not None else 0
        elif (mainConfig.plcGuiControl == "plc") and config.AQAnalog1:
            try:
                status.analog1 = int(plc.GetAO(config.AQAnalog1["byte"]))
            except Exception:
                pass

        if "AQAnalog2" in forced_values:
            status.analog2 = int(forced_values["AQAnalog2"]) if forced_values["AQAnalog2"] is not None else 0
        elif (mainConfig.plcGuiControl == "plc") and config.AQAnalog2:
            try:
                status.analog2 = int(plc.GetAO(config.AQAnalog2["byte"]))
            except Exception:
                pass

        if "AQAnalog3" in forced_values:
            status.analog3 = int(forced_values["AQAnalog3"]) if forced_values["AQAnalog3"] is not None else 0
        elif (mainConfig.plcGuiControl == "plc") and config.AQAnalog3:
            try:
                status.analog3 = int(plc.GetAO(config.AQAnalog3["byte"]))
            except Exception:
                pass

        # Note: Forced output values are NOT written back to PLC
        # Forcing is only for overriding what the simulator reads from PLC
        # Writing forced outputs back would create a feedback loop

        # Always write to PLC inputs (sensors) with force support

        # Digital Level Sensor High
        if "DILevelSensorHigh" in forced_values:
            value = bool(forced_values["DILevelSensorHigh"])
        else:
            value = status.digitalLevelSensorHighTriggered

        if self._is_enabled(config, 'DILevelSensorHigh') and config.DILevelSensorHigh and not self._has_conflict("DILevelSensorHigh", config.DILevelSensorHigh, [config.DIStart, config.DIStop, config.DIReset]):
            key = "DILevelSensorHigh"
            if self._last_sent_di.get(key) != value:
                plc.SetDI(config.DILevelSensorHigh["byte"], config.DILevelSensorHigh["bit"], value)
                self._last_sent_di[key] = value

        # Digital Level Sensor Low
        if "DILevelSensorLow" in forced_values:
            value = bool(forced_values["DILevelSensorLow"])
        else:
            value = status.digitalLevelSensorLowTriggered

        if self._is_enabled(config, 'DILevelSensorLow') and config.DILevelSensorLow and not self._has_conflict("DILevelSensorLow", config.DILevelSensorLow, [config.DIStart, config.DIStop, config.DIReset]):
            key = "DILevelSensorLow"
            if self._last_sent_di.get(key) != value:
                plc.SetDI(config.DILevelSensorLow["byte"], config.DILevelSensorLow["bit"], value)
                self._last_sent_di[key] = value

        # Analog Level Sensor
        if "AILevelSensor" in forced_values:
            value = int(forced_values["AILevelSensor"])
        else:
            value = int(self.mapValue(0, config.tankVolume, 0,
                        plc.analogMax, status.liquidVolume))
        if self._is_enabled(config, 'AILevelSensor') and config.AILevelSensor:
            key = "AILevelSensor"
            if self._last_sent_ai.get(key) != value:
                plc.SetAI(config.AILevelSensor["byte"], value)
                self._last_sent_ai[key] = value

        # Analog Temperature Sensor
        if "AITemperatureSensor" in forced_values:
            value = int(forced_values["AITemperatureSensor"])
        else:
            value = int(self.mapValue(-50, 250, 0,
                        plc.analogMax, status.liquidTemperature))
        if self._is_enabled(config, 'AITemperatureSensor') and config.AITemperatureSensor:
            key = "AITemperatureSensor"
            if self._last_sent_ai.get(key) != value:
                plc.SetAI(config.AITemperatureSensor["byte"], value)
                self._last_sent_ai[key] = value

        # General Controls - READ PLC inputs (Start/Stop/Reset and Control sliders from PLC)
        # Start/Stop/Reset: Read from PLC (these are pushed TO the PLC by GUI; we read them back)
        if "DIStart" in forced_values:
            status.generalStartCmd = bool(forced_values["DIStart"])
        elif (mainConfig.plcGuiControl == "plc"):
            try:
                status.generalStartCmd = plc.GetDI(config.DIStart["byte"], config.DIStart["bit"]) if config.DIStart else False
            except Exception:
                pass

        if "DIStop" in forced_values:
            status.generalStopCmd = bool(forced_values["DIStop"])
        elif (mainConfig.plcGuiControl == "plc"):
            try:
                status.generalStopCmd = plc.GetDI(config.DIStop["byte"], config.DIStop["bit"]) if config.DIStop else False
            except Exception:
                pass

        if "DIReset" in forced_values:
            status.generalResetCmd = bool(forced_values["DIReset"])
        elif (mainConfig.plcGuiControl == "plc"):
            try:
                status.generalResetCmd = plc.GetDI(config.DIReset["byte"], config.DIReset["bit"]) if config.DIReset else False
            except Exception:
                pass

        # Control sliders 1..3 as PLC analog inputs: READ from PLC
        if "AIControl1" in forced_values:
            status.generalControl1Value = int(forced_values["AIControl1"]) if forced_values["AIControl1"] is not None else 0
        elif (mainConfig.plcGuiControl == "plc"):
            try:
                status.generalControl1Value = int(plc.GetAI(config.AIControl1["byte"])) if config.AIControl1 else 0
            except Exception:
                pass

        if "AIControl2" in forced_values:
            status.generalControl2Value = int(forced_values["AIControl2"]) if forced_values["AIControl2"] is not None else 0
        elif (mainConfig.plcGuiControl == "plc"):
            try:
                status.generalControl2Value = int(plc.GetAI(config.AIControl2["byte"])) if config.AIControl2 else 0
            except Exception:
                pass

        if "AIControl3" in forced_values:
            status.generalControl3Value = int(forced_values["AIControl3"]) if forced_values["AIControl3"] is not None else 0
        elif (mainConfig.plcGuiControl == "plc"):
            try:
                status.generalControl3Value = int(plc.GetAI(config.AIControl3["byte"])) if config.AIControl3 else 0
            except Exception:
                pass

        # Write GUI slider values to PLC inputs (so PLC receives them)
        if "AIControl1" not in forced_values and config.AIControl1:
            key = "AIControl1"
            val = int(getattr(status, 'generalControl1Value', 0))
            if self._last_sent_ai.get(key) != val:
                plc.SetAI(config.AIControl1["byte"], val)
                self._last_sent_ai[key] = val
        if "AIControl2" not in forced_values and config.AIControl2:
            key = "AIControl2"
            val = int(getattr(status, 'generalControl2Value', 0))
            if self._last_sent_ai.get(key) != val:
                plc.SetAI(config.AIControl2["byte"], val)
                self._last_sent_ai[key] = val
        if "AIControl3" not in forced_values and config.AIControl3:
            key = "AIControl3"
            val = int(getattr(status, 'generalControl3Value', 0))
            if self._last_sent_ai.get(key) != val:
                plc.SetAI(config.AIControl3["byte"], val)
                self._last_sent_ai[key] = val

        # Write GUI commands to PLC inputs - continuously while pressed
        if "DIStart" not in forced_values and config.DIStart:
            desired = bool(getattr(status, 'generalStartCmd', False))
            if self._ton_ready("DIStart", desired):
                key = "DIStart"
                if self._last_sent_di.get(key) != desired:
                    plc.SetDI(config.DIStart["byte"], config.DIStart["bit"], desired)
                    self._last_sent_di[key] = desired
        if "DIStop" not in forced_values and config.DIStop:
            desired = bool(getattr(status, 'generalStopCmd', False))
            if self._ton_ready("DIStop", desired):
                key = "DIStop"
                if self._last_sent_di.get(key) != desired:
                    plc.SetDI(config.DIStop["byte"], config.DIStop["bit"], desired)
                    self._last_sent_di[key] = desired
        if "DIReset" not in forced_values and config.DIReset:
            desired = bool(getattr(status, 'generalResetCmd', False))
            if self._ton_ready("DIReset", desired):
                key = "DIReset"
                if self._last_sent_di.get(key) != desired:
                    plc.SetDI(config.DIReset["byte"], config.DIReset["bit"], desired)
                    self._last_sent_di[key] = desired

    def resetOutputs(self, mainConfig: mainConfigClass, config: configurationClass, status: statusClass):
        """Reset actuators when PLC connection is lost"""
        if (mainConfig.plcGuiControl == "plc"):
            status.valveInOpenFraction = float(0)
            status.valveOutOpenFraction = float(0)
            status.heaterPowerFraction = float(0)
            # Reset general controls commands/sliders
            status.generalStartCmd = False
            status.generalStopCmd = False
            status.generalResetCmd = False
            status.generalControl1Value = 0
            status.generalControl2Value = 0
            status.generalControl3Value = 0

            if not self.outputs_reset:
                print("PLC outputs reset (no connection)")
                self.outputs_reset = True

