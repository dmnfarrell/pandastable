# pandastable

## Introduction

<img align="right" src=https://raw.githubusercontent.com/dmnfarrell/pandastable/master/img/logo.png width=150px>

The pandastable library provides a table widget for Tkinter with plotting and data manipulation functionality. 
It uses the pandas DataFrame class to store table data. Pandas is an open source Python library providing high-performance data structures and data analysis tools. Tkinter is the standard GUI toolkit for python. It is intended for the following uses:

* for python/tkinter GUI developers who want to include a table in their application that can store and process
large amounts of data
* for non-programmers who are not familiar with Python or the pandas API and want to use
the included DataExplore application to manipulate/view their data
* it may also be useful for data analysts and programmers who want to get an initial interactive look at their tabular data without coding

The DataExplore application using these classes is included in the distribution and is a self-contained application for educational and research use. Currently this focuses on providing a spreadsheet like interface for table manipulation withconfigurable 2D/3D plotting. A windows standalone installer is available that does not require Python installation.

## Installation

Requires python>=3.3 or 2.7 and numpy, matplotlib and pandas. These requirements should be satisfied automatically when using: (You may need to use pip3 or easy_install3 to specify python version 3).

```pip install pandastable```
or
```easy_install pandastable```

see the [wiki page](https://github.com/dmnfarrell/pandastable/wiki/Installation) for more details on installing.

## Current features
* add, remove rows and columns
* spreadsheet-like drag, shift-click, ctrl-click selection
* edit individual cells
* sort by column, rename columns
* reorder columns dynamically by mouse drags
* set some basic formatting such as font, text size and column width
* save the DataFrame to supported pandas formats
* import/export of supported text files
* rendering of very large tables is only memory limited
* interactive plots with matplotlib, mostly using the pandas plot functions
* basic table manipulations like aggregate and pivot
* filter table using built in dataframe functionality
* graphical way to perform split-apply-combine operations

## Future features
* present/manipulate time series data since pandas deals well with this
* animated plotting e.g. time series data
* saving workflows

## FAQ

*What version of Python?*

Python versions >=2.7 and >=3.3 are compatible. However python 3.4 is recommended if possible. For a similar table widget that works without pandas dataframes and has minimal dependencies see the previous incarnation, tkintertable.

*Why use Tkinter?*

Tkinter is still the standard GUI toolkit for python though it is sometimes disliked 
for its outdated appearance (especially on linux) and somewhat limited widget set. However largely
because this library is based on an older one called tkintertable for drawing the table, 
I have stuck with tkinter rather than start from scratch using another toolkit.

*Is this just a half-baked spreadsheet?*

Hopefully not. Some of the basic functions are naturally present since it's a table. 
But there is no point in trying to mimic a proper spreadsheet app. pandas can do
lots of stuff that would be nice for a non-programmer to utilize and that might 
not be available in a spreadsheet application.

*Are there other better tools for dataframe visualization?*

This depends as always on what is required. The ipython notebook is good for interactive use.
bokeh is an advanced interactive plotting tool using modern generation web technologies for in browser 
rendering. This can handle dataframes. The goal of this project is to use DataFrames as the back end
for a table widget that can be used in a desktop appplication.

## The DataExplore application
Installing the package creates a command *dataexplore* in your path. Just run this to open the program. 
This is a standalone application for data manipulation and plotting meant for education and basic data analysis.
See the home page for this application at http://dmnfarrell.github.io/pandastable/

<img src=https://raw.githubusercontent.com/dmnfarrell/pandastable/master/img/viewerapp.png width=600px>

## For programmers.

Here is the *Hello PandasTable World!* example, at the `pandastable/examples` directory, in order to run, execute:

```bash
$ python pandastable/examples/hello_pandastable_world.py
```

What follows are the contents of `pandastable/examples/hello_panadastable_world.py`:

```python
# coding: utf-8


"""
hello_pandastable_world.py
"""


from os import remove as rm
from os.path import isfile

from tkinter import Tk, Frame, TOP
from tkinter.ttk import Notebook

from pandastable import Table    

from textwrap import dedent as dd


TMP_CSV = "hello_pandastable_world.csv"

def setup():
    with open(TMP_CSV, "w") as f:
        f.write(dd(
            """
            ID, Hello
            1, PandasTable
            2, World!
            """
        ))
        

def pandas_gui():
    root = Tk()
    root.title("Hello PandasTable World!")
    
    notebook = Notebook(root)
    
    frame = Frame(notebook)

    table = Table(frame)
    table.show()
    table.importCSV(TMP_CSV)
    table.redraw()
    

notebook.add(frame, text = "Pandas Table",compound = TOP)
    notebook.pack()
    
    root.mainloop()
    

def cleanup(): 
    if isfile(TMP_CSV):
        rm(TMP_CSV)    
        
    
def main():
    setup()
    pandas_gui()
    cleanup()    
    

if __name__ == '__main__':
    main()
```

Which should create a GUI similar to this one (example from Windows):

<img src=https://raw.githubusercontent.com/dmnfarrell/pandastable/master/img/hello_pandastable_world.png width=600px>

Update the table:
```
#alter the DataFrame in some way, then update
table.redraw()
```

Import a csv file:
```
table.importCSV('test.csv')
```

## Links

http://openresearchsoftware.metajnl.com/articles/10.5334/jors.94/

http://dmnfarrell.github.io/pandastable/

https://youtu.be/lA7bhbWOkSw

http://decisionstats.com/2015/12/25/interview-damien-farrell-python-gui-dataexplore-python-rstats-pydata/

http://jakevdp.github.io/blog/2013/03/23/matplotlib-and-the-future-of-visualization-in-python/

## Citation

If you use this software in your work please cite the following article:

Farrell, D 2016 DataExplore: An Application for General Data Analysis in Research and Education.
Journal of Open Research Software, 4: e9, DOI: http://dx.doi.org/10.5334/jors.94
