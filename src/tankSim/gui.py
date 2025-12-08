from tkinter import filedialog
import tkinter as tk
import pathlib
import os
from PIL import Image, ImageTk
import math

# import class definition of mainConfig
from configuration import configuration as mainConfigClass

# tankSim specific imports
from tankSim.status import status as tankSimStatusClass
from tankSim.configuration import configuration as tankSimConfigurationClass


defaultStatus = tankSimStatusClass()
defaultConfig = tankSimConfigurationClass()


# Global state variables
inlet_valve = defaultStatus.valveInOpenFraction*100  # 0-100%
outlet_valve = defaultStatus.valveOutOpenFraction*100  # 0-100%
heating_power = defaultStatus.heaterPowerFraction*100  # 0-100%
water_level = defaultStatus.liquidVolume  # liters
target_level = 1000  # liters - gewenste waterniveau
temperature = defaultStatus.liquidTemperature  # °C - water temperature
tank_volume = defaultConfig.tankVolume  # liters
flow_rate_in = defaultStatus.flowRateIn


SaveKleur = "blue"
SaveBreedte = 1000
SaveHoogte = 2000
SaveDebietMaxIn = defaultConfig.valveInMaxFlow
SaveDebietMaxOut = defaultConfig.valveOutMaxFlow
SaveDichtheid = defaultConfig.liquidSpecificWeight*1000
SaveKlepen = 1
SaveWeerstand = 1
SaveHoogtemeting = 1

# flag for updateData to also export config/status
exportCommand: bool = False
importCommand: bool = False


kleuren = [
    "Blue",
    "Yellow",
    "Gold",
    "Green",
    "Cyan",
    "Orange",
    "Red",
    "Purple",
    "Pink"
]


def get_heating_color(power):
    """Return color based on heating power - from gray to orange/red"""
    if power == 0:
        return "#CCCCCC"
    elif power < 30:
        return "#FFB366"
    elif power < 60:
        return "#FF8C42"
    else:
        return "#FF6B35"


class process:

    def __init__(main, MainFrame):

        main.MainFrame = MainFrame
        main.canvas = tk.Canvas(
            MainFrame, width=1000, height=700, bg="white", border=0, highlightthickness=0)
        main.canvas.pack(fill=tk.BOTH, expand=True)

        main.is_running = False
        main.update_id = None

        # Create control panel first (permanent widgets)
        main.create_control_panel()

        # Draw the system
        main.draw_system()

    def draw_system(main):
        """Draw the complete tank system"""
        # Only delete canvas items, not the widgets
        for item in main.canvas.find_all():
            if main.canvas.type(item) != "window":
                main.canvas.delete(item)

        # Tank dimensions
        tank_x = 350
        tank_y = 150
        tank_width = 200
        tank_height = 400

        # Calculate water level height in pixels
        water_height_px = (water_level / tank_volume) * tank_height
        water_y = tank_y + tank_height - water_height_px

        # Calculate target level line
        target_height_px = (target_level / tank_volume) * tank_height
        target_y = tank_y + tank_height - target_height_px

        # Get current water color
        water_color = SaveKleur

        # Draw inlet pipe (horizontal from left)
        pipe_y_top = tank_y - 60
        main.canvas.create_line(50, pipe_y_top, tank_x + tank_width//2, pipe_y_top,
                                fill="black", width=4)
        main.canvas.create_line(50, pipe_y_top + 20, tank_x + tank_width//2, pipe_y_top + 20,
                                fill="black", width=4)

        # Water in inlet pipe (if valve open)
        if inlet_valve > 0:
            main.canvas.create_rectangle(50, pipe_y_top + 2, tank_x + tank_width//2, pipe_y_top + 18,
                                         fill=water_color, outline="")
            # Flow arrow
            main.canvas.create_line(150, pipe_y_top + 10, 200, pipe_y_top + 10,
                                    arrow=tk.LAST, fill="black", width=3)
            main.canvas.create_text(120, pipe_y_top - 10, text=f"{flow_rate_in} L/s",
                                    font=("Arial", 9, "bold"))

        # Inlet valve (triangles pointing at each other)
        valve_x = tank_x + tank_width//2
        valve_y_top = pipe_y_top + 20

        # Top triangle (pointing down)
        valve_color_in = water_color if inlet_valve > 0 else "white"
        main.canvas.create_polygon(
            valve_x - 20, valve_y_top,
            valve_x + 20, valve_y_top,
            valve_x, valve_y_top + 25,
            fill=valve_color_in, outline="black", width=3)

        # Bottom triangle (pointing up)
        main.canvas.create_polygon(
            valve_x - 20, valve_y_top + 50,
            valve_x + 20, valve_y_top + 50,
            valve_x, valve_y_top + 25,
            fill=valve_color_in, outline="black", width=3)

        # Vertical pipe from inlet valve to tank
        main.canvas.create_line(valve_x - 10, valve_y_top + 50, valve_x - 10, tank_y,
                                fill="black", width=4)
        main.canvas.create_line(valve_x + 10, valve_y_top + 50, valve_x + 10, tank_y,
                                fill="black", width=4)

        if inlet_valve > 0:
            main.canvas.create_rectangle(valve_x - 8, valve_y_top + 50, valve_x + 8, tank_y,
                                         fill=water_color, outline="")

        # Draw tank outline
        main.canvas.create_rectangle(tank_x, tank_y, tank_x + tank_width, tank_y + tank_height,
                                     outline="black", width=5, fill="white")

        # Draw target level line (dashed green line)
        main.canvas.create_line(tank_x, target_y, tank_x + tank_width, target_y,
                                fill="green", width=2, dash=(5, 5))
        main.canvas.create_text(tank_x - 40, target_y, text="Target",
                                font=("Arial", 8), fill="green", angle=90)

        # Draw water in tank
        if water_level > 0:
            main.canvas.create_rectangle(tank_x + 3, water_y,
                                         tank_x + tank_width - 3, tank_y + tank_height - 3,
                                         fill=water_color, outline="")

        # Draw heating element (spring coil on left inside tank)
        main.draw_heating_coil(tank_x, tank_y, tank_height)

        # Water level indicator (disconnected, on the right)
        level_x = tank_x + tank_width + 80
        main.canvas.create_line(level_x, tank_y, level_x, tank_y + tank_height,
                                fill="gray", width=2)

        # Tick marks
        for i in range(5):
            tick_y = tank_y + (i * tank_height / 4)
            main.canvas.create_line(level_x - 5, tick_y, level_x + 5, tick_y,
                                    fill="gray", width=2)
            level_value = tank_volume - (i * tank_volume / 4)
            main.canvas.create_text(level_x + 30, tick_y, text=f"{int(level_value)}",
                                    font=("Arial", 8))

        # Current level indicator
        main.canvas.create_line(level_x - 10, water_y, level_x + 10, water_y,
                                fill="red", width=3)
        main.canvas.create_text(level_x + 70, water_y, text=f"{int(water_level)} mm",
                                font=("Arial", 10, "bold"), fill="red")

        # Outlet valve at bottom of tank
        outlet_x = tank_x + tank_width//2
        outlet_y_start = tank_y + tank_height

        # Vertical pipe from tank to outlet valve
        main.canvas.create_line(outlet_x - 10, outlet_y_start, outlet_x - 10, outlet_y_start + 50,
                                fill="black", width=4)
        main.canvas.create_line(outlet_x + 10, outlet_y_start, outlet_x + 10, outlet_y_start + 50,
                                fill="black", width=4)

        if outlet_valve > 0 and water_level > 0:
            main.canvas.create_rectangle(outlet_x - 8, outlet_y_start, outlet_x + 8, outlet_y_start + 50,
                                         fill=water_color, outline="")

        # Outlet valve (triangles pointing at each other)
        valve_y_bottom = outlet_y_start + 50
        valve_color_out = water_color if (
            outlet_valve > 0 and water_level > 0) else "white"

        # Top triangle (pointing down)
        main.canvas.create_polygon(
            outlet_x - 20, valve_y_bottom,
            outlet_x + 20, valve_y_bottom,
            outlet_x, valve_y_bottom + 25,
            fill=valve_color_out, outline="black", width=3)

        # Bottom triangle (pointing up)
        main.canvas.create_polygon(
            outlet_x - 20, valve_y_bottom + 50,
            outlet_x + 20, valve_y_bottom + 50,
            outlet_x, valve_y_bottom + 25,
            fill=valve_color_out, outline="black", width=3)

        # Outlet pipe going down
        main.canvas.create_line(outlet_x - 10, valve_y_bottom + 50, outlet_x - 10, valve_y_bottom + 120,
                                fill="black", width=4)
        main.canvas.create_line(outlet_x + 10, valve_y_bottom + 50, outlet_x + 10, valve_y_bottom + 120,
                                fill="black", width=4)

        if outlet_valve > 0 and water_level > 0:
            main.canvas.create_rectangle(outlet_x - 8, valve_y_bottom + 50,
                                         outlet_x + 8, valve_y_bottom + 120,
                                         fill=water_color, outline="")

        # Labels
        main.canvas.create_text(valve_x + 50, valve_y_top + 25,
                                text=f"Inlet\n{inlet_valve}%",
                                font=("Arial", 9, "bold"))

        main.canvas.create_text(outlet_x + 50, valve_y_bottom + 25,
                                text=f"Outlet\n{outlet_valve}%",
                                font=("Arial", 9, "bold"))

    def draw_heating_coil(main, tank_x, tank_y, tank_height):
        """Draw heating coil/spring element on left side of tank"""
        coil_x = tank_x + 30
        coil_top = tank_y + 50
        coil_bottom = tank_y + tank_height - 50
        coil_height = coil_bottom - coil_top

        # Get heating color based on power
        heating_color = get_heating_color(heating_power)

        # Number of coils
        num_turns = 10
        turn_height = coil_height / num_turns
        coil_width = 30

        # Draw spring as series of semicircles
        for i in range(num_turns):
            y_start = coil_top + (i * turn_height)
            y_end = y_start + turn_height
            y_mid = (y_start + y_end) / 2

            # Right semicircle
            main.canvas.create_arc(
                coil_x, y_start, coil_x + coil_width, y_mid,
                start=90, extent=180, style=tk.ARC,
                outline=heating_color, width=4)

            # Left semicircle
            main.canvas.create_arc(
                coil_x, y_mid, coil_x + coil_width, y_end,
                start=270, extent=180, style=tk.ARC,
                outline=heating_color, width=4)

        # Connection lines extending outside tank
        main.canvas.create_line(coil_x, coil_top, tank_x - 5, coil_top,
                                fill=heating_color, width=4)
        main.canvas.create_line(coil_x, coil_bottom, tank_x - 5, coil_bottom,
                                fill=heating_color, width=4)

        # Label outside tank on the left with temperature
        main.canvas.create_text(tank_x - 80, (coil_top + coil_bottom) / 2,
                                text=f"Verwarming\n{heating_power}%\n{int(temperature)}°C",
                                font=("Arial", 9, "bold"), fill=heating_color)

    def create_control_panel(main):
        """Create control panel with input boxes"""
        label_x = 650
        entry_x = 820
        panel_y = 100

        # Title
        main.canvas.create_text((label_x + entry_x) / 2, panel_y - 30, text="Control Panel",
                                font=("Arial", 16, "bold"))

        # Inlet valve
        main.canvas.create_text(label_x, panel_y + 20, text="Inlet Valve:",
                                font=("Arial", 11, "bold"), anchor="w")
        main.inlet_entry = tk.Entry(main.canvas, width=10, font=("Arial", 11))
        main.canvas.create_window(
            entry_x, panel_y + 20, window=main.inlet_entry)
        main.inlet_entry.insert(0, str(inlet_valve))
        main.canvas.create_text(entry_x + 90, panel_y + 20, text="(0-100%)",
                                font=("Arial", 9), anchor="w", fill="gray")

        # Outlet valve
        main.canvas.create_text(label_x, panel_y + 70, text="Outlet Valve:",
                                font=("Arial", 11, "bold"), anchor="w")
        main.outlet_entry = tk.Entry(main.canvas, width=10, font=("Arial", 11))
        main.canvas.create_window(
            entry_x, panel_y + 70, window=main.outlet_entry)
        main.outlet_entry.insert(0, str(outlet_valve))
        main.canvas.create_text(entry_x + 90, panel_y + 70, text="(0-100%)",
                                font=("Arial", 9), anchor="w", fill="gray")

        # Heating power
        main.canvas.create_text(label_x, panel_y + 120, text="Heating Power:",
                                font=("Arial", 11, "bold"), anchor="w")
        main.heating_entry = tk.Entry(
            main.canvas, width=10, font=("Arial", 11))
        main.canvas.create_window(
            entry_x, panel_y + 120, window=main.heating_entry)
        main.heating_entry.insert(0, str(heating_power))
        main.canvas.create_text(entry_x + 90, panel_y + 120, text="(0-100%)",
                                font=("Arial", 9), anchor="w", fill="gray")

        # Target water level
        main.canvas.create_text(label_x, panel_y + 170, text="Target Level:",
                                font=("Arial", 11, "bold"), anchor="w")
        main.target_entry = tk.Entry(main.canvas, width=10, font=("Arial", 11))
        main.canvas.create_window(
            entry_x, panel_y + 170, window=main.target_entry)
        main.target_entry.insert(0, str(target_level))
        main.canvas.create_text(entry_x + 90, panel_y + 170, text="(mm)",
                                font=("Arial", 9), anchor="w", fill="gray")

        # Separator line
        main.canvas.create_line(label_x - 10, panel_y + 215, entry_x + 140, panel_y + 215,
                                fill="gray", width=2)

        # Status section title
        main.canvas.create_text(label_x, panel_y + 240, text="STATUS",
                                font=("Arial", 10, "bold"), anchor="w", fill="gray")

        # Current water level display
        main.canvas.create_text(label_x, panel_y + 275, text="Current Level:",
                                font=("Arial", 11, "bold"), anchor="w")
        main.level_label = main.canvas.create_text(entry_x, panel_y + 275,
                                                   text=f"{int(water_level)} mm",
                                                   font=("Arial", 11, "bold"), fill="blue", anchor="w")

        # Current temperature display
        main.canvas.create_text(label_x, panel_y + 315, text="Temperature:",
                                font=("Arial", 11, "bold"), anchor="w")
        main.temp_label = main.canvas.create_text(entry_x, panel_y + 315,
                                                  text=f"{int(temperature)}°C",
                                                  font=("Arial", 11, "bold"), fill="orange", anchor="w")

        # Apply button
        main.apply_btn = tk.Button(main.canvas, text="Apply Changes", bg="#4CAF50", fg="white",
                                   font=("Arial", 11, "bold"), command=main.apply_changes,
                                   padx=25, pady=8, cursor="hand2")
        main.canvas.create_window(
            (label_x + entry_x) / 2 + 40, panel_y + 375, window=main.apply_btn)

        # Start/Stop button
        main.start_stop_btn = tk.Button(main.canvas, text="Start Simulation", bg="#2196F3", fg="white",
                                        font=("Arial", 11, "bold"), command=main.toggle_simulation,
                                        padx=25, pady=8, cursor="hand2")
        main.canvas.create_window(
            (label_x + entry_x) / 2 + 40, panel_y + 435, window=main.start_stop_btn)

    def apply_changes(main):
        """Apply the control changes and redraw"""
        global inlet_valve, outlet_valve, heating_power, target_level

        try:
            inlet_valve = max(0, min(100, float(main.inlet_entry.get())))
            outlet_valve = max(0, min(100, float(main.outlet_entry.get())))
            heating_power = max(0, min(100, float(main.heating_entry.get())))
            target_level = max(
                0, min(tank_volume, float(main.target_entry.get())))

            # Redraw the system
            main.draw_system()

        except ValueError:
            print("Invalid input - please enter valid numbers")

    def redrawTank(self):
        # Redraw and update displays
        self.draw_system()
        self.canvas.itemconfig(self.level_label, text=f"{int(water_level)} mm")
        self.canvas.itemconfig(self.temp_label, text=f"{int(temperature)}°C")

        # Schedule next update
        self.update_id = self.canvas.after(100, self.redrawTank)

    def toggle_simulation(main):
        """Start or stop the simulation"""
        if main.is_running:
            main.is_running = False
            main.start_stop_btn.config(text="Start Simulation", bg="#2196F3")
            if main.update_id:
                main.canvas.after_cancel(main.update_id)
        else:
            main.is_running = True
            main.start_stop_btn.config(text="Stop Simulation", bg="#F44336")
            main.redrawTank()

    def updateData(self, mainConfig: mainConfigClass, processConfig: tankSimConfigurationClass, processStatus: tankSimStatusClass) -> None:
        global heating_power, inlet_valve, outlet_valve, water_level, temperature, flow_rate_in

        processStatus.simRunning = self.is_running
        water_level = processStatus.liquidVolume
        temperature = processStatus.liquidTemperature
        flow_rate_in = processStatus.flowRateIn

        # only write if guiControl
        if (mainConfig.plcGuiControl == "gui"):
            processStatus.valveInOpenFraction = inlet_valve/100
            processStatus.valveOutOpenFraction = outlet_valve/100
            processStatus.heaterPowerFraction = heating_power/100


class settings:

    def __init__(main, MainFrame):

        def ApplySettings():
            global SaveBreedte, SaveKleur, SaveDichtheid, SaveHoogtemeting
            global SaveWeerstand, SaveKlepen, SaveDebietMaxIn, SaveHoogte

            SaveBreedte = Breedte.get()
            SaveKleur = KleurVloeistof.get().lower()
            SaveDichtheid = Dichtheid.get()
            SaveHoogtemeting = DigitaleHoogte.get()
            SaveWeerstand = RegelbareWeerstand.get()
            SaveKlepen = RegelbareKlepen.get()
            SaveDebietMaxIn = DebietMaxIn.get()
            SaveHoogte = Hoogte.get()

        SettingsFrame = tk.Frame(MainFrame, bg="white")
        SettingsFrame.place(relwidth=1.0, relheight=1.0, x=50)

        DimensionLabel = tk.Label(
            SettingsFrame, text="Afmetingen Vat:", bg="white", fg="black", font=("Arial", 10))
        DimensionLabel.grid(row=1, column=0, sticky="e", pady=(10, 2))

        BreedteLabel = tk.Label(
            SettingsFrame, text="Breete (mm):", bg="white", fg="black", font=("Arial", 10))
        BreedteLabel.grid(row=2, column=0, sticky="e")
        Breedte = tk.Entry(SettingsFrame)
        Breedte.grid(row=2, column=1)
        Breedte.insert(0, SaveBreedte)

        HoogteLabel = tk.Label(
            SettingsFrame, text="Hoogte (mm):", bg="white", fg="black", font=("Arial", 10))
        HoogteLabel.grid(row=3, column=0, sticky="e")
        Hoogte = tk.Entry(SettingsFrame)
        Hoogte.grid(row=3, column=1)
        Hoogte.insert(0, SaveHoogte)

        DebietMaxInLabel = tk.Label(
            SettingsFrame, text="Toekomend debiet (l/min):", bg="white", fg="black", font=("Arial", 10))
        DebietMaxInLabel.grid(row=4, column=0, sticky="e")
        DebietMaxIn = tk.Entry(SettingsFrame)
        DebietMaxIn.grid(row=4, column=1)
        DebietMaxIn.insert(0, SaveDebietMaxIn)

        RegelingLabel = tk.Label(
            SettingsFrame, text="Regeling:", bg="white", fg="black", font=("Arial", 10))
        RegelingLabel.grid(row=5, column=0, sticky="e", pady=(10, 2))

        RegelbareKlepenLabel = tk.Label(
            SettingsFrame, text="Regelbare klepen:", bg="white", fg="black", font=("Arial", 10))
        RegelbareKlepenLabel.grid(row=6, column=0, sticky="e")
        RegelbareKlepen = tk.BooleanVar()
        RegelbareKlepenCheck = tk.Checkbutton(SettingsFrame,
                                              variable=RegelbareKlepen, onvalue=1, offvalue=0, bg="white")
        RegelbareKlepenCheck.grid(row=6, column=1, sticky="w")
        RegelbareKlepen.set(SaveKlepen)

        RegelbareWeerstandLabel = tk.Label(
            SettingsFrame, text="Regelbare weerstand:", bg="white", fg="black", font=("Arial", 10))
        RegelbareWeerstandLabel.grid(row=7, column=0, sticky="e")
        RegelbareWeerstand = tk.BooleanVar()
        RegelbareWeerstandCheck = tk.Checkbutton(SettingsFrame,
                                                 variable=RegelbareWeerstand, onvalue=1, offvalue=0, bg="white")
        RegelbareWeerstandCheck.grid(row=7, column=1, sticky="w")
        RegelbareWeerstand.set(SaveWeerstand)

        DigitaleHoogteLabel = tk.Label(
            SettingsFrame, text="Digitale hoogte meting:", bg="white", fg="black", font=("Arial", 10))
        DigitaleHoogteLabel.grid(row=8, column=0, sticky="e")
        DigitaleHoogte = tk.BooleanVar()
        DigitaleHoogteCheck = tk.Checkbutton(SettingsFrame,
                                             variable=DigitaleHoogte, onvalue=1, offvalue=0, bg="white")
        DigitaleHoogteCheck.grid(row=8, column=1, sticky="w")
        DigitaleHoogte.set(SaveHoogtemeting)

        SoortVloeistofLabel = tk.Label(
            SettingsFrame, text="Welke Vloeistof zit er in de tank:", bg="white", fg="black", font=("Arial", 10))
        SoortVloeistofLabel.grid(row=9, column=0, sticky="e", pady=(10, 2))

        DichtheidLabel = tk.Label(
            SettingsFrame, text="Dichtheid (kg/m³):", bg="white", fg="black", font=("Arial", 10))
        DichtheidLabel.grid(row=10, column=0, sticky="e")
        Dichtheid = tk.Entry(SettingsFrame)
        Dichtheid.grid(row=10, column=1)
        Dichtheid.insert(0, SaveDichtheid)

        KleurVloeistofLabel = tk.Label(
            SettingsFrame, text="Kleur:", bg="white", fg="black", font=("Arial", 10))
        KleurVloeistofLabel.grid(row=11, column=0, sticky="e")
        KleurVloeistof = tk.StringVar()

        KleurVloeistofMenu = tk.OptionMenu(
            SettingsFrame, KleurVloeistof, *kleuren)
        KleurVloeistofMenu.grid(row=11, column=1, sticky="ew")
        KleurVloeistof.set(SaveKleur.capitalize())

        SaveButton = tk.Button(
            SettingsFrame, text="Apply Settings", bg="white", activebackground="white", command=ApplySettings)
        SaveButton.grid(row=12, column=3, pady=(10, 0))

        ExportButton = tk.Button(
            SettingsFrame, text="Export config", bg="white", activebackground="white", command=main.ExportConfig)
        ExportButton.grid(row=12, column=4, padx=(30, 0), pady=(10, 0))

        LoadButton = tk.Button(
            SettingsFrame, text="Load config", bg="white", activebackground="white", command=main.ImportConfig)
        LoadButton.grid(row=12, column=5, padx=(10, 0), pady=(10, 0))

    def updateData(self, mainConfig: mainConfigClass, processConfig: tankSimConfigurationClass, processStatus: tankSimStatusClass):
        global exportCommand, importCommand, tank_volume, SaveDebietMaxIn, SaveDichtheid
        processConfig.tankVolume = tank_volume

        # define csv fileType for filedialog functions
        csvFileType = [
            ('Comma-separated values', '*.csv'), ('All Files', '*.*'),]

        # overwrite config and status after other changes done by gui
        if (importCommand):
            file = filedialog.askopenfilename(
                filetypes=csvFileType, defaultextension=csvFileType)
            # only try to import when there was a file selected
            if (file):
                processConfig.loadFromFile(file)
                processStatus.loadFromFile(file)
            importCommand = False  # reset import command flag

        # read data from status and config (can include our imported changes)
        # write data to status and config
        tank_volume = processConfig.tankVolume
        SaveDichtheid = processConfig.liquidSpecificWeight*1000
        SaveDebietMaxIn = processConfig.valveInMaxFlow

        # export status and config after all changes are done
        if (exportCommand):
            file = filedialog.asksaveasfilename(
                filetypes=csvFileType, defaultextension=csvFileType)
            # only try to export when the was a file selected
            if (file):
                # create file, add header, add config variables
                processConfig.saveToFile(file, True)
                # add status variables to file
                processStatus.saveToFile(file)
                # reset export command flag
            exportCommand = False

    def ExportConfig(self):
        global exportCommand
        exportCommand = True

    def ImportConfig(self):
        global importCommand
        importCommand = True
