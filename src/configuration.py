import csv


class configuration:
    """
    Contructor: create configuration object with default parameters
    """

    def __init__(self):

        # control process trough gui or plc
        # written by: gui, import
        self.plcGuiControl = "plc"  # options: gui/plc
        self.doExit = False
        """
        Plc connection settings
        """
        # written by: gui, import
        # options: "Gui","PLC S7-1500/1200/400/300/ET 200SP","PLC S7-300/400", "logo!",PLCSim S7-1500 advanced,"PLCSim S7-1500/1200/400/300/ET 200SP")
        self.plcProtocol: str = "PLC S7-1500/1200/400/300/ET 200SP"
        self.plcIpAdress: str = "192.168.0.1"
        self.plcPort: int = 502  # ModBusTCP default port
        self.plcRack: int = 0
        self.plcSlot: int = 1
        self.tsapLogo: int = 0x0300 #CLIENT(sim)ZIJDE
        self.tsapServer: int = 0x0200 #LOGO ZIJDE
        # set True by gui, set False by main
        self.tryConnect: bool = False

        self.importExportVariableList = ["plcGuiControl", "plcProtocol",
                                         "plcIpAdress", "plcPort", "plcRack", "plcSlot", "tsapLogo", "tsapServer"]

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
