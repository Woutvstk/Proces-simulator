# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Hidden imports
hiddenimports = [
    'PyQt5.sip',
]
hiddenimports += collect_submodules("pymodbus")
hiddenimports += collect_submodules("asyncio")
hiddenimports += collect_submodules("core")
hiddenimports += collect_submodules("IO")
hiddenimports += collect_submodules("gui")
hiddenimports += collect_submodules("simulations")

# Data files - verzamel ALLES
datas = [
    ('src/gui/media', 'gui/media'),
    ('src/IO/IO_treeList_conveyor.xml', 'IO'),
    ('src/IO/IO_treeList_PIDtankValve.xml', 'IO'),
    ('src/IO/IO_configuration.json', 'IO'),
    ('src/gui', 'gui'),
    ('src/core', 'core'),
    ('src/IO', 'IO'),
    ('src/simulations', 'simulations'),
]

# Binaries
import sys
snap7_dll_path = os.path.join(sys.prefix, 'Lib', 'site-packages', 'snap7', 'lib', 'snap7.dll')
binaries = [
    (snap7_dll_path, "."),
]

# Analysis
a = Analysis(
    ["src/main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pandas", "scipy"],
    noarchive=False,
)

# Python archive
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PLC_Modbus_Proces_Simulator",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)
