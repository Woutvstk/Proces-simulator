import tkinter as tk

# Maak een nieuw venster
root = tk.Tk()
root.title("PID Regelaar Tank")


# Gebruik windowed fullscreen (maximized) in plaats van echte fullscreen.
# Dit houdt de titelbalk en taakbalk-gedrag meer zoals een normaal venster,
# maar het venster vult wel het scherm (geschikt voor Windows).
# F11 togglet gemaximaliseerd, Escape zet terug naar normaal.
is_maximized = True
root.state('zoomed')  # 'zoomed' werkt op Windows om het venster te maximaliseren

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
