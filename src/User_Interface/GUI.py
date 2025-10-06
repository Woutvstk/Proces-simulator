import tkinter as tk
import pathlib
import os
from tkinter import *
from PIL import Image, ImageTk


def getAbsolutePath(relativePath: str) -> str:
    current_dir = pathlib.Path(__file__).parent.resolve()
    return os.path.join(current_dir, relativePath)


# Maak een nieuw venster
root = tk.Tk()
root.title("PID Regelaar Tank")
# toolbar
root.frame = Frame(root, height=50, bg="lightgrey")
root.frame.pack(fill=X)

# hamburger menu button
# Replace with your image file path
hamburgerImage = Image.open(getAbsolutePath("media\\HamburgerIcon.png"))
resizedHamburgerImage = hamburgerImage.resize((45, 45))
imgHamburger = ImageTk.PhotoImage(resizedHamburgerImage)
Hamburger = tk.Button(root, border=0, width=50, height=48,
                      background="lightgrey", image=imgHamburger)
Hamburger.place(relx=0.0, rely=0.0)


# connection button
# Replace with your image file path
connectionImage = Image.open(getAbsolutePath("media\\connect.png"))
resizedConnectionImage = connectionImage.resize((35, 20))
imgConection = ImageTk.PhotoImage(resizedConnectionImage)
Connect = tk.Button(root, image=imgConection, command=root.destroy)
Connect.place(relx=0.82, rely=0.02)
# IP address Input
ip_address_label = tk.Label(root, text="IP Address:", background="lightgrey")
ip_address_label.place(relx=0.86, rely=0.02)
ip_address_entry = tk.Entry(root)
ip_address_entry.place(relx=0.91, rely=0.02)
is_maximized = True
# 'zoomed' werkt op Windows om het venster te maximaliseren
root.state('zoomed')


def toggle_fullscreen(event=None):
    """Toggle windowed fullscreen / maximize (gebonden aan F11)."""
    global is_maximized
    if is_maximized:
        root.state('normal')
        is_maximized = False
    else:
        root.state('zoomed')
        is_maximized = True


def exit_fullscreen(event=None):
    """Zet het venster terug naar normaal (gebonden aan Escape)."""
    global is_maximized
    root.state('normal')
    is_maximized = False


# Bind toetsen
root.bind('<F11>', toggle_fullscreen)
root.bind('<Escape>', exit_fullscreen)


root.mainloop()
