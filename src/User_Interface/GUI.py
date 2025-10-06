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


image = Image.open(getAbsolutePath("media\\connect.png")
                   )  # Replace with your image file path
resized_image = image.resize((35, 20))
img = ImageTk.PhotoImage(resized_image)
connectImage = tk.PhotoImage(file=getAbsolutePath("media\\connect.png"))
Connect = tk.Button(root, image=img, command=root.destroy).pack()
Connect.place(x=50, y=50)

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
