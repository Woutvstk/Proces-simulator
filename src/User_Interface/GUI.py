import tkinter as tk

# Maak een nieuw venster
root = tk.Tk()
root.title("PID Regelaar Tank")

# Start het venster fullscreen in plaats van een vaste grootte in te stellen.
# F11 togglet fullscreen, Escape verlaat fullscreen.
is_fullscreen = True
root.attributes('-fullscreen', True)

def toggle_fullscreen(event=None):
	"""Toggle fullscreen (gebonden aan F11)."""
	global is_fullscreen
	is_fullscreen = not is_fullscreen
	root.attributes('-fullscreen', is_fullscreen)

def exit_fullscreen(event=None):
	"""Verlaat fullscreen (gebonden aan Escape)."""
	global is_fullscreen
	is_fullscreen = False
	root.attributes('-fullscreen', False)

# Bind toetsen
root.bind('<F11>', toggle_fullscreen)
root.bind('<Escape>', exit_fullscreen)

root.mainloop()
