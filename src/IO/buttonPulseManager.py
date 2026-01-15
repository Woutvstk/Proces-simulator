"""
Button Pulse Manager - Handles debouncing and pulse timing for simulation buttons.

Ensures that:
- Brief button clicks are always detected (even <1 frame)
- Buttons stay active for a minimum pulse duration (100ms)
- Modular and scalable across all button types
"""
import time
from typing import Dict, Callable, Any


class ButtonPulseManager:
    """Manages button pulse timing to guarantee registration and minimum duration."""
    
    def __init__(self, pulse_duration_ms: float = 100):
        """
        Initialize the button pulse manager.
        
        Args:
            pulse_duration_ms: Minimum duration button should stay active (default 100ms)
        """
        self.pulse_duration_s = pulse_duration_ms / 1000.0
        self.button_states: Dict[str, Dict[str, Any]] = {}
    
    def register_button(self, button_id: str, status_obj: Any, attr_name: str) -> None:
        """
        Register a button to be managed.
        
        Args:
            button_id: Unique identifier for the button
            status_obj: Status object to write to (e.g., status.pidPidValveStartCmd), can be None initially
            attr_name: Attribute name on status object
        """
        self.button_states[button_id] = {
            "status_obj": status_obj,
            "attr_name": attr_name,
            "is_pressed": False,
            "press_time": None,
            "pulse_active": False,
            "pulse_end_time": None
        }
    
    def set_button_status_obj(self, button_id: str, status_obj: Any) -> None:
        """Update the status object for a button after initialization."""
        if button_id in self.button_states:
            self.button_states[button_id]["status_obj"] = status_obj
    
    def on_button_pressed(self, button_id: str) -> None:
        """
        Call when a button is physically pressed.
        
        Args:
            button_id: Button identifier
        """
        if button_id not in self.button_states:
            return
        
        state = self.button_states[button_id]
        
        # Skip if status object is not yet initialized
        if state["status_obj"] is None:
            return
        
        now = time.monotonic()
        
        state["is_pressed"] = True
        state["press_time"] = now
        state["pulse_active"] = True
        state["pulse_end_time"] = now + self.pulse_duration_s
        
        # Immediately set to True
        setattr(state["status_obj"], state["attr_name"], True)
    
    def on_button_released(self, button_id: str) -> None:
        """
        Call when a button is physically released.
        
        Args:
            button_id: Button identifier
        """
        if button_id not in self.button_states:
            return
        
        state = self.button_states[button_id]
        state["is_pressed"] = False
        # Keep pulse_active=True and pulse_end_time set; update() will handle deactivation
    
    def update(self) -> None:
        """
        Call regularly (e.g., every simulation cycle) to manage pulse timing.
        Should be called from the main loop to deactivate buttons after pulse duration.
        Keeps buttons active while pressed, deactivates after pulse duration only if released.
        """
        now = time.monotonic()
        
        for button_id, state in self.button_states.items():
            if state["pulse_active"] and state["pulse_end_time"] is not None:
                # Only deactivate if: (1) pulse expired AND (2) button is no longer pressed
                if now >= state["pulse_end_time"] and not state["is_pressed"]:
                    # Pulse duration expired and button released, deactivate
                    if state["status_obj"] is not None:
                        setattr(state["status_obj"], state["attr_name"], False)
                    state["pulse_active"] = False
                    state["pulse_end_time"] = None


# Global instance
_button_pulse_manager: ButtonPulseManager | None = None


def get_button_pulse_manager(pulse_duration_ms: float = 100) -> ButtonPulseManager:
    """Get or create the global button pulse manager."""
    global _button_pulse_manager
    if _button_pulse_manager is None:
        _button_pulse_manager = ButtonPulseManager(pulse_duration_ms)
    return _button_pulse_manager
