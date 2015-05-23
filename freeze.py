import sys, os
from cx_Freeze import setup, Executable

sys.path.append('pandastable')

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": ["os","numpy","matplotlib","pandas","pandastable"],
                     "excludes": [],
                     "namespace_packages": ['mpl_toolkits'],
                     "include_msvcr": True }

base = None
if sys.platform == "win32":
    base = "Win32GUI"

executables = [Executable("pandastable/app.py", base=base,
                          copyDependentFiles = True,
                          targetName='DataViewer.exe',
                          icon="img/dataviewer.ico")]

setup(  name = "DataViewer",
        version = "0.2",
        description = "Data analysis and plotter",
        options = {"build_exe": build_exe_options},
        executables = executables)
