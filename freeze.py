import sys, os
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": ["os","numpy","matplotlib","pandas","pandastable"],
                     "excludes": []}

base = None
if sys.platform == "win32":
    base = "Win32GUI"

executables = [Executable("pandastable/app.py", base=base)]
setup(  name = "dataviewer",
        version = "0.2",
        description = "Data analysis and plotter",
        options = {"build_exe": build_exe_options},
        executables = executables)
