import sys, os
from cx_Freeze import setup, Executable
PYTHON_INSTALL_DIR = os.path.dirname(os.path.dirname(os.__file__))

sys.path.append('pandastable')

#currently requires changing line 548 of hooks.py to make scipy work
#see https://bitbucket.org/anthony_tuininga/cx_freeze/issues/43

includes = ["pandastable"]
includefiles = ["pandastable/dataexplore.gif","pandastable/datasets",
                "pandastable/plugins",
                os.path.join(PYTHON_INSTALL_DIR, 'DLLs', 'tk86t.dll'),
                os.path.join(PYTHON_INSTALL_DIR, 'DLLs', 'tcl86t.dll')
                ]

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": ["os","numpy","matplotlib","pandas",
                                  #"scipy","seaborn","IPython","statsmodels",
                                  "pandastable"],
                     "excludes": ['scipy','seaborn','statsmodels'],
                     "namespace_packages": ['mpl_toolkits'],
                     "include_msvcr": True,
                     "includes": includes,
                     "include_files": includefiles}

base = None
if sys.platform == "win32":
    base = "Win32GUI"

executables = [Executable("main.py", base=base,
                          #copyDependentFiles = True,
                          targetName='DataExplore.exe',
                          shortcutName="DataExplore",
                          shortcutDir="DesktopFolder",
                          icon="img/dataexplore.ico")]

setup(  name = "DataExplore",
	version = "0.12.1",
	description = "Data analysis and plotter",
    options = {"build_exe": build_exe_options},
    executables = executables)
