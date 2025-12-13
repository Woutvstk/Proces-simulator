import csv


class status:
    def __init__(self):
        # Valve IN status (written by: plc, gui or import)
        self.valveInOpenFraction: float = 0.0

        # Valve OUT status (written by: plc, gui or import)
        self.valveOutOpenFraction: float = 0.0

        # Heating element status (written by: plc, gui or import)
        self.heaterPowerFraction: float = 0.0

        # Digital level sensor status (written by: simulation)
        self.digitalLevelSensorLowTriggered: bool = False
        self.digitalLevelSensorHighTriggered: bool = False

        # Liquid parameters (written by: simulation, import)
        self.liquidVolume: float = 100.0
        self.liquidTemperature: float = 0.0

        # Simulation status (written by: gui)
        self.simRunning = False

        # Flow rates (written by simulation)
        self.flowRateIn: float = 0.0
        self.flowRateOut: float = 0.0

        self.importExportVariableList = ["liquidVolume", "liquidTemperature",
                                         "valveInOpenFraction", "valveOutOpenFraction", "heaterPowerFraction"]

    def saveToFile(self, exportFileName, createFile: bool = False):
        """Save status to a CSV file"""
        print(f"Exporting status to: {exportFileName}")
        openMode: str
        if (createFile):
            openMode = "w"
        else:
            openMode = "a"

        with open(exportFileName, openMode, newline="") as file:
            writer = csv.writer(file)
            if (createFile):
                writer.writerow(["variable", "value"])
            for variable in self.importExportVariableList:
                writer.writerow([variable, getattr(self, variable)])
            file.close

    def loadFromFile(self, importFileName: str):
        """Read status back from the CSV file"""
        with open(importFileName, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                for variable in self.importExportVariableList:
                    if row["variable"] == variable:
                        setattr(self, variable, type(
                            getattr(self, variable))(row["value"]))
        print(f"Status loaded from: {importFileName}")
