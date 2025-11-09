import csv


class configurationClass:

    """
    Contructor: create configuration object with default parameters
    """

    def __init__(self):

        # control process trough gui or plc
        # written by: gui, import
        self.plcGuiControl = "gui"  # options: gui/plc
        self.doExit = False
        """
        Plc connection settings
        """
        # written by: gui, import
        self.plcProtocol: str = "logoS7"  # options: Gui/ModBusTCP/plcS7/logoS7
        self.plcIpAdress: str = "192.168.0.1"
        self.plcPort: int = 502
        self.plcRack: int = 0
        self.plcSlot: int = 1
        self.tsapLogo: int = 0x0300
        self.tsapServer: int = 0x2000
        # set True by gui, set False by main
        self.tryConnect: bool = False
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
        self.simulationInterval = 0.2  # in seconds
        """
        process settings
        """
        # written by: gui, import
        self.tankVolume: float = 200.0
        self.valveInMaxFlow: float = 5.0
        self.valveOutMaxFlow: float = 2.0
        self.ambientTemp: float = 21.0
        # default at 90%
        self.digitalLevelSensorHighTriggerLevel: float = 0.9 * self.tankVolume
        # default at 10%
        self.digitalLevelSensorLowTriggerLevel: float = 0.1 * self.tankVolume
        # heater power in watts
        self.heaterMaxPower: float = 10000.0
        # tank heat loss
        self.tankHeatLoss: float = 150.0
        # specific heat capacity in Joeles/Kg*°C (4186 for water)
        self.liquidSpecificHeatCapacity: float = 4186.0
        # specific weight in kg per liter (water: 1)
        self.liquidSpecificWeight: float = 0.997
        # boiling temperature of liquid (water: 100)
        self.liquidBoilingTemp: float = 100.0

        self.importExportVariableList = ["tankVolume", "valveInMaxFlow", "valveOutMaxFlow", "ambientTemp", "digitalLevelSensorHighTriggerLevel", "digitalLevelSensorLowTriggerLevel", "heaterMaxPower", "tankHeatLoss",
                                         "liquidSpecificHeatCapacity", "liquidBoilingTemp", "liquidSpecificWeight"]

    # Save config to a CSV file
    def saveToFile(self, exportFileName, createFile: bool = False):
        print(f"Exporting config to: {exportFileName}")
        openMode: str
        if (createFile):
            openMode = "w"  # if creating new file, open in Write mode
        else:
            openMode = "a"  # if adding to existing file, open in append mode

        with open(exportFileName, openMode, newline="") as file:
            writer = csv.writer(file)
            if (createFile):
                # if creating new file, add csv header first
                writer.writerow(["variable", "value"])
            # write all variables from list with value to csv
            for variable in self.importExportVariableList:
                writer.writerow([variable, getattr(self, variable)])
            file.close

    # Read config back from the CSV file
    def loadFromFile(self, importFileName: str):
        with open(importFileName, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                for variable in self.importExportVariableList:
                    if row["variable"] == variable:
                        setattr(self, variable, type(
                            getattr(self, variable))(row["value"]))
        print(f"Config loaded from: {importFileName}")
