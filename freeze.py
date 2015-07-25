import sys, os
from cx_Freeze import setup, Executable

sys.path.append('pandastable')

includes = ["pandastable"]
includefiles = ["pandastable/dataexplore.gif","pandastable/datasets"]

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": ["os","numpy","matplotlib","pandas","pandastable"],
                     "excludes": [],
                     "namespace_packages": ['mpl_toolkits'],
                     "include_msvcr": True,
                     "includes": includes,
                     "include_files": includefiles}

base = None
if sys.platform == "win32":
    base = "Win32GUI"

executables = [Executable("main.py", base=base,
                          copyDependentFiles = True,
                          targetName='DataExplore.exe',
                          shortcutName="DataExplore",
                          shortcutDir="DesktopFolder",
                          icon="img/dataexplore.ico")]

setup(  name = "DataExplore",
        version = "0.4.2",
        description = "Data analysis and plotter",
        options = {"build_exe": build_exe_options},
        executables = executables)
