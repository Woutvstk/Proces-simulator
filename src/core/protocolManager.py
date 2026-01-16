"""
Protocol Manager - Manages PLC protocol activation and lifecycle.

This module is responsible for:
- Activating specific protocol (Logo S7, PLC S7, PLCSimAPI)
- Switching between protocol control and GUI control
- Managing protocol lifecycle and connections
"""
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class ProtocolManager:
    """
    Manages PLC protocol instances and connections.
    Handles switching between different protocol types and GUI control.
    """
    
    def __init__(self):
        """Initialize the protocol manager."""
        self._active_protocol: Optional[Any] = None
        self._protocol_type: Optional[str] = None
        self._is_connected: bool = False
        
    def activate_protocol(self, protocol_type: str, protocol_instance: Any) -> bool:
        """
        Activate a protocol instance.
        
        Args:
            protocol_type: Type identifier (e.g., "PLC S7", "Logo S7", "PLCSimAPI")
            protocol_instance: Instance of the protocol communication class
            
        Returns:
            True if activated successfully, False otherwise
        """
        try:
            # Disconnect existing protocol if any
            if self._active_protocol and self._is_connected:
                self.disconnect()
            
            self._active_protocol = protocol_instance
            self._protocol_type = protocol_type
            self._is_connected = False
            
            logger.info(f"Activated protocol: {protocol_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to activate protocol '{protocol_type}': {e}")
            return False
    
    def connect(self) -> bool:
        """
        Connect to the active protocol.
        
        Returns:
            True if connected successfully, False otherwise
        """
        if not self._active_protocol:
            logger.warning("No active protocol to connect")
            return False
        
        try:
            if hasattr(self._active_protocol, 'connect'):
                result = self._active_protocol.connect()
                self._is_connected = bool(result)
                
                if self._is_connected:
                    logger.info(f"Connected to {self._protocol_type}")
                else:
                    logger.warning(f"Failed to connect to {self._protocol_type}")
                    
                return self._is_connected
            else:
                logger.error(f"Protocol {self._protocol_type} has no connect method")
                return False
                
        except Exception as e:
            logger.error(f"Connection error for {self._protocol_type}: {e}")
            self._is_connected = False
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect from the active protocol.
        
        Returns:
            True if disconnected successfully, False otherwise
        """
        if not self._active_protocol:
            logger.warning("No active protocol to disconnect")
            return False
        
        try:
            if hasattr(self._active_protocol, 'disconnect'):
                self._active_protocol.disconnect()
                self._is_connected = False
                logger.info(f"Disconnected from {self._protocol_type}")
                return True
            else:
                logger.warning(f"Protocol {self._protocol_type} has no disconnect method")
                return False
                
        except Exception as e:
            logger.error(f"Disconnect error for {self._protocol_type}: {e}")
            return False
    
    def is_connected(self) -> bool:
        """
        Check if protocol is connected.
        
        Returns:
            True if connected, False otherwise
        """
        if not self._active_protocol:
            return False
        
        # Check protocol's own connection state if available
        if hasattr(self._active_protocol, 'isConnected'):
            try:
                return self._active_protocol.isConnected()
            except:
                pass
        
        return self._is_connected
    
    def get_active_protocol(self) -> Optional[Any]:
        """
        Get the active protocol instance.
        
        Returns:
            Active protocol instance or None
        """
        return self._active_protocol
    
    def get_protocol_type(self) -> Optional[str]:
        """
        Get the type of active protocol.
        
        Returns:
            Protocol type string or None
        """
        return self._protocol_type
    
    def reset_inputs(self, lowest_byte: int, highest_byte: int) -> bool:
        """
        Reset PLC inputs (simulator outputs).
        
        Args:
            lowest_byte: Start of byte range
            highest_byte: End of byte range
            
        Returns:
            True if reset successfully, False otherwise
        """
        if not self._active_protocol or not self._is_connected:
            return False
        
        try:
            if hasattr(self._active_protocol, 'resetSendInputs'):
                result = self._active_protocol.resetSendInputs(lowest_byte, highest_byte)
                return bool(result)  # Return the actual result from protocol
            else:
                logger.warning(f"Protocol {self._protocol_type} has no resetSendInputs method")
                return False
        except Exception as e:
            logger.error(f"Failed to reset inputs: {e}")
            return False
    
    def reset_outputs(self, lowest_byte: int, highest_byte: int) -> bool:
        """
        Reset PLC outputs (simulator inputs).
        
        Args:
            lowest_byte: Start of byte range
            highest_byte: End of byte range
            
        Returns:
            True if reset successfully, False otherwise
        """
        if not self._active_protocol or not self._is_connected:
            return False
        
        try:
            if hasattr(self._active_protocol, 'resetSendOutputs'):
                result = self._active_protocol.resetSendOutputs(lowest_byte, highest_byte)
                return bool(result)  # Return the actual result from protocol
            else:
                logger.warning(f"Protocol {self._protocol_type} has no resetSendOutputs method")
                return False
        except Exception as e:
            logger.error(f"Failed to reset outputs: {e}")
            return False
    
    def deactivate(self) -> bool:
        """
        Deactivate current protocol (disconnect and clear).
        
        Returns:
            True if deactivated successfully, False otherwise
        """
        try:
            if self._is_connected:
                self.disconnect()
            
            self._active_protocol = None
            self._protocol_type = None
            self._is_connected = False
            
            logger.info("Protocol deactivated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deactivate protocol: {e}")
            return False

    # ---------------------------------------------------------------------
    # Convenience helpers to build, activate, connect and prime protocols
    # ---------------------------------------------------------------------
    def build_protocol_from_config(self, config: Any) -> Optional[Any]:
        """
        Build a protocol instance from configuration.

        Expected config attributes:
        - plcProtocol: str
        - plcIpAdress: str
        - plcRack: int
        - plcSlot: int
        - tsapLogo: int
        - tsapServer: int
        - selectedNetworkAdapter: str (optional, default "auto")
        """
        try:
            protocol_type = getattr(config, 'plcProtocol', None)
            if not protocol_type:
                logger.warning("No plcProtocol specified in configuration")
                return None

            # Get network adapter setting, default to "auto"
            network_adapter = getattr(config, 'selectedNetworkAdapter', 'auto')

            # Lazy imports to avoid hard dependencies when unused
            if protocol_type == "PLC S7-1500/1200/400/300/ET 200SP":
                from IO.protocols.plcS7 import plcS7
                return plcS7(config.plcIpAdress, config.plcRack, config.plcSlot, network_adapter=network_adapter)
            elif protocol_type == "logo!":
                from IO.protocols.logoS7 import logoS7
                return logoS7(config.plcIpAdress, config.tsapLogo, config.tsapServer, network_adapter=network_adapter)
            elif protocol_type == "PLCSim S7-1500 advanced":
                from IO.protocols.PLCSimAPI.PLCSimAPI import plcSimAPI
                return plcSimAPI(network_adapter=network_adapter)
            elif protocol_type == "PLCSim S7-1500/1200/400/300/ET 200SP":
                # PLCSim protocols only work with local simulators - prevent connection to real PLC
                ip_address = getattr(config, 'plcIpAdress', '')
                if ip_address and ip_address != '127.0.0.1' and ip_address != 'localhost':
                    logger.error(f"PLCSim protocol cannot connect to remote IP '{ip_address}'. PLCSim only works with local simulators (127.0.0.1).")
                    return None
                from IO.protocols.PLCSimS7 import plcSimS7
                return plcSimS7(config.plcIpAdress, config.plcRack, config.plcSlot, network_adapter=network_adapter)
            else:
                logger.error(f"Unsupported plcProtocol: {protocol_type}")
                return None
        except Exception as e:
            logger.error(f"Error building protocol from config: {e}")
            return None

    def initialize_and_connect(self, config: Any, lowest_byte: int, highest_byte: int) -> bool:
        """
        Build protocol from config, activate and connect it, then verify IO operations.
        
        Connection is defined as:
        1. TCP connection successful (isConnected() returns True)
        2. Reset input operations successful 
        3. Reset output operations successful
        
        Returns True only if ALL three conditions are met; False otherwise.
        """
        protocol_instance = self.build_protocol_from_config(config)
        if not protocol_instance:
            self.deactivate()
            return False

        if not self.activate_protocol(getattr(config, 'plcProtocol', 'UNKNOWN'), protocol_instance):
            return False

        # Attempt TCP connection
        if not self.connect():
            logger.error("TCP connection failed")
            self.deactivate()
            return False

        # Verify communication by attempting to reset IO ranges
        # This ensures the protocol actually works with the hardware
        try:
            reset_inputs_ok = self.reset_inputs(lowest_byte, highest_byte)
            if not reset_inputs_ok:
                logger.error("Failed to reset inputs - protocol mismatch or communication error")
                self.disconnect()
                self.deactivate()
                return False
            
            reset_outputs_ok = self.reset_outputs(lowest_byte, highest_byte)
            if not reset_outputs_ok:
                logger.error("Failed to reset outputs - protocol mismatch or communication error")
                self.disconnect()
                self.deactivate()
                return False
            
            logger.info("Connection verified: isConnected=True AND reset operations successful")
            return True
            
        except Exception as e:
            logger.error(f"Exception during IO verification: {e}")
            self.disconnect()
            self.deactivate()
            return False
