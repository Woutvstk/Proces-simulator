import csv


class configuration:

    """
    Contructor: create configuration object with default parameters
    """

    def __init__(self):
        """
        IO settings
        """

        # PLC OUTPUTS
        # DIGITAL
        self.DQValveIn = {"byte": 0, "bit": 0}   # False = Closed
        self.DQValveOut = {"byte": 0, "bit": 1}  # False = Closed
        self.DQHeater = {"byte": 0, "bit": 2}    # False = Off
        # ANALOG
        self.AQValveInFraction = {"byte": 2}     # 0 = Closed, MAX = full open
        self.AQValveOutFraction = {"byte": 4}    # 0 = Closed, MAX = full open
        self.AQHeaterFraction = {"byte": 6}      # 0 = Off, MAX = full power

        # PLC INPUTS
        # DIGITAL
        # False = liquid below sensor
        self.DILevelSensorHigh = {"byte": 0, "bit": 0}
        # False = liquid below sensor
        self.DILevelSensorLow = {"byte": 0, "bit": 1}
        # ANALOG
        # 0 = empty tank, MAX = full tank
        self.AILevelSensor = {"byte": 2}
        # 0 = -50°C, MAX = 250°C
        self.AITemperatureSensor = {"byte": 4}

        self.lowestByte, self.highestByte = self.get_byte_range()

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
        self.liquidVolumeTimeDelay: float = 0.0
        self.ambientTemp: float = 21.0
        # default at 90%
        self.digitalLevelSensorHighTriggerLevel: float = 0.9 * self.tankVolume
        # default at 10%
        self.digitalLevelSensorLowTriggerLevel: float = 0.1 * self.tankVolume
        # heater power in watts
        self.heaterMaxPower: float = 10000.0
        # tank heat loss
        self.tankHeatLoss: float = 150.0
        # time in seconds between the change of the actor (heater/cooling) and the measured change
        self.liquidTempTimeDelay: float = 0.0
        # specific heat capacity in Joeles/Kg*°C (4186 for water)
        self.liquidSpecificHeatCapacity: float = 4186.0
        # specific weight in kg per liter (water: 1)
        self.liquidSpecificWeight: float = 0.997
        # boiling temperature of liquid (water: 100)

        self.liquidBoilingTemp: float = 100.0

        self.importExportVariableList = ["tankVolume", "valveInMaxFlow", "valveOutMaxFlow", "liquidVolumeTimeDelay", "ambientTemp", "digitalLevelSensorHighTriggerLevel", "digitalLevelSensorLowTriggerLevel", "heaterMaxPower", "tankHeatLoss", "liquidTempTimeDelay",
                                         "liquidSpecificHeatCapacity", "liquidBoilingTemp", "liquidSpecificWeight"]

    # Save configuration to CSV file
    def saveToFile(self, exportFileName, createFile: bool = False):
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

    # Read configuration from CSV file
    def loadFromFile(self, importFileName: str):
        with open(importFileName, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                for variable in self.importExportVariableList:
                    if row["variable"] == variable:
                        setattr(self, variable, type(
                            getattr(self, variable))(row["value"]))
        print(f"Config loaded from: {importFileName}")

     # ----------------------------------------------------------
    def get_byte_range(self):
        """
        Return the lowest and highest byte used in all IO definitions.
        Scans all dicts in the current object that have a 'byte' key.
        """
        # function used for resetSendInputs in plcCom
        bytes_used = []

        for _, value in self.__dict__.items():
            # Controleer of de waarde een dictionary is met een 'byte'-sleutel
            if isinstance(value, dict) and "byte" in value:
                # Voeg de byte-waarde toe aan de lijst met gebruikte bytes
                bytes_used.append(value["byte"])

        # If at least one byte is found → determine lowest and highest byte
        if bytes_used:
            lowestByte = min(bytes_used)
            highestByte = max(bytes_used)
            return lowestByte, highestByte
        else:
            return None, None

    # ----------------------------------------------------------
    def update_io_range(self):
        """
        Call this when IO data changes (e.g. GUI edits addresses).
        """
        self.lowestByte, self.highestByte = self.get_byte_range()
