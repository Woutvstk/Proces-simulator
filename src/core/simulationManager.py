"""
Simulation Manager - Manages active simulations and provides status info.

This module is responsible for:
- Tracking active simulation(s)
- Providing current simulation status to other modules
- Managing simulation lifecycle (start, stop, pause, reset)
- Interface between core and simulation instances

External Libraries Used:
- typing (Python Standard Library) - Type hints for method signatures
- logging (Python Standard Library) - Error and info logging
"""
from typing import Dict, Optional, Any, List
import logging

from .interface import SimulationInterface

logger = logging.getLogger(__name__)


class SimulationManager:
    """
    Manages simulation instances and their lifecycle.
    Provides interface for other modules to access simulation data.
    """

    def __init__(self):
        """Initialize the simulation manager."""
        self._registered_simulations: Dict[str, type] = {}
        self._active_simulation: Optional[SimulationInterface] = None
        self._active_simulation_name: Optional[str] = None

    def register_simulation(self, name: str, simulation_class: type) -> None:
        """
        Register a simulation type.

        Args:
            name: Unique identifier for the simulation
            simulation_class: Class that implements SimulationInterface
        """
        if not issubclass(simulation_class, SimulationInterface):
            raise ValueError(
                f"Simulation class must implement SimulationInterface")

        self._registered_simulations[name] = simulation_class
        logger.info(f"Registered simulation: {name}")

    def get_registered_simulations(self) -> List[str]:
        """
        Get list of registered simulation names.

        Returns:
            List of simulation names
        """
        return list(self._registered_simulations.keys())

    def load_simulation(self, name: str, *args, **kwargs) -> bool:
        """
        Load and activate a simulation.

        Args:
            name: Name of registered simulation to load
            *args, **kwargs: Arguments to pass to simulation constructor

        Returns:
            True if successfully loaded, False otherwise
        """
        if name not in self._registered_simulations:
            logger.error(f"Simulation '{name}' not registered")
            return False

        try:
            # Stop current simulation if any
            if self._active_simulation:
                self._active_simulation.stop()

            # Create new simulation instance
            simulation_class = self._registered_simulations[name]
            self._active_simulation = simulation_class(*args, **kwargs)
            if not self._active_simulation:
                print("ERROR: simulation manager 83, activ sim is null")
            self._active_simulation_name = name

            logger.info(f"Loaded simulation: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load simulation '{name}': {e}")
            self._active_simulation = None
            self._active_simulation_name = None
            return False

    def get_active_simulation(self) -> Optional[SimulationInterface]:
        """
        Get the currently active simulation instance.

        Returns:
            Active simulation instance or None
        """
        return self._active_simulation

    def get_active_simulation_name(self) -> Optional[str]:
        """
        Get the name of the currently active simulation.

        Returns:
            Name of active simulation or None
        """
        return self._active_simulation_name

    def start_simulation(self) -> bool:
        """
        Start the active simulation.

        Returns:
            True if started successfully, False otherwise
        """
        if not self._active_simulation:
            logger.warning("No active simulation to start")
            return False

        try:
            self._active_simulation.start()
            logger.info(f"Started simulation: {self._active_simulation_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to start simulation: {e}")
            return False

    def stop_simulation(self) -> bool:
        """
        Stop the active simulation.

        Returns:
            True if stopped successfully, False otherwise
        """
        if not self._active_simulation:
            logger.warning("No active simulation to stop")
            return False

        try:
            self._active_simulation.stop()
            logger.info(f"Stopped simulation: {self._active_simulation_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop simulation: {e}")
            return False

    def reset_simulation(self) -> bool:
        """
        Reset the active simulation to initial state.

        Returns:
            True if reset successfully, False otherwise
        """
        if not self._active_simulation:
            logger.warning("No active simulation to reset")
            return False

        try:
            self._active_simulation.reset()
            logger.info(f"Reset simulation: {self._active_simulation_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset simulation: {e}")
            return False

    def update_simulation(self, dt: float, newStatus: any) -> bool:
        """
        Update the active simulation.

        Args:
            dt: Time delta since last update in seconds

        Returns:
            True if updated successfully, False otherwise
        """
        if not self._active_simulation:
            print(
                f"simulation manager 179: self._active_simulation does not exist, returning")
            return False

        try:
            self._active_simulation.set_status_object(newStatus)
            self._active_simulation.update(dt)
            return True
        except Exception as e:
            logger.error(f"Failed to update simulation: {e}")
            return False

    def get_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current status of active simulation.

        Returns:
            Status dictionary or None if no active simulation
        """
        if not self._active_simulation:
            return None

        try:
            return self._active_simulation.get_status()
        except Exception as e:
            logger.error(f"Failed to get simulation status: {e}")
            return None

    def set_input(self, key: str, value: Any) -> bool:
        """
        Set an input value for the active simulation.

        Args:
            key: Input parameter name
            value: Value to set

        Returns:
            True if set successfully, False otherwise
        """
        if not self._active_simulation:
            return False

        try:
            self._active_simulation.set_input(key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set simulation input '{key}': {e}")
            return False

    def get_output(self, key: str) -> Any:
        """
        Get an output value from the active simulation.

        Args:
            key: Output parameter name

        Returns:
            Output value or None if not available
        """
        if not self._active_simulation:
            return None

        try:
            return self._active_simulation.get_output(key)
        except Exception as e:
            logger.error(f"Failed to get simulation output '{key}': {e}")
            return None

    def get_config(self) -> Optional[Dict[str, Any]]:
        """
        Get configuration of active simulation.

        Returns:
            Configuration dictionary or None
        """
        if not self._active_simulation:
            return None

        try:
            return self._active_simulation.get_config()
        except Exception as e:
            logger.error(f"Failed to get simulation config: {e}")
            return None

    def set_config(self, config: Dict[str, Any]) -> bool:
        """
        Update configuration of active simulation.

        Args:
            config: Configuration parameters to update

        Returns:
            True if updated successfully, False otherwise
        """
        if not self._active_simulation:
            return False

        try:
            self._active_simulation.set_config(config)
            return True
        except Exception as e:
            logger.error(f"Failed to set simulation config: {e}")
            return False
