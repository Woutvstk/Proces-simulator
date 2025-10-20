
class configuration:

    """
    Contructor: create configuration object with default parameters
    """

    def __init__(self):
        """
        Plc connection settings
        """
        self.plcProtocol: str = "logoS7"
        self.plcIpAdress: str = "192.168.111.01"
        self.plcPort: int = 502
        self.plcRack: int = 0
        self.plcSlot: int = 1
        self.taspLogo: int = 0x0300
        self.taspServer: int = 0x2000
        """
        IO settings
        """

        # PLC OUTPUTS
        # DIGITAL
        self.DQValveIn: int = 0  # False = Closed
        self.DQValveOut: int = 1  # False = Closed
        self.DQHeater: int = 2  # False = Off
        # ANALOG
        self.AQValveInFraction: int = 0  # 0 = Closed, MAX = full open
        self.AQValveOutFraction: int = 1  # 0 = Closed, MAX = full open
        self.AQHeaterFraction: int = 2  # 0 = Off, MAX = full power

        # PLC INPUTS
        # DIGITAL
        self.DILevelSensorHigh: int = 0  # False = liquid below sensor
        self.DILevelSensorLow: int = 1  # False = liquid below sensor
        # ANALOG
        self.AILevelSensor: int = 0  # 0 = empty tank, MAX = full tank
        self.AITemperatureSensor: int = 1  # 0 = -50°C, MAX = 250°C

        """
        Simulation settings
        """

        """
        UI settings
        """
