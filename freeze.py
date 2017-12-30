import sys, os
from cx_Freeze import setup, Executable

sys.path.append('pandastable')

#currently requires changing line 548 of hooks.py to make scipy work
#see https://bitbucket.org/anthony_tuininga/cx_freeze/issues/43

includes = ["pandastable"]#,"scipy.integrate.vode","scipy.integrate.lsoda","scipy.linalg"]
includefiles = ["pandastable/dataexplore.gif","pandastable/datasets",
                "pandastable/plugins"]

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": ["os","numpy","matplotlib","pandas",
                                  "scipy","seaborn","IPython",
                                  "statsmodels","pandastable"],
                     "excludes": [],
                     "namespace_packages": ['mpl_toolkits'],
                     "include_msvcr": True,
                     "includes": includes,
                     "include_files": includefiles}

base = None
if sys.platform == "win32":
    #base = None
    base = "Win32GUI"

executables = [Executable("main.py", base=base,
                          copyDependentFiles = True,
                          targetName='DataExplore.exe',
                          shortcutName="DataExplore",
                          shortcutDir="DesktopFolder",
                          icon="img/dataexplore.ico")]

setup(  name = "DataExplore",
	version = "0.9.0",
	description = "Data analysis and plotter",
    options = {"build_exe": build_exe_options},
    executables = executables)
