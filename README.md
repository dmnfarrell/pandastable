# pandastable

## Introduction

Pandas is an open source Python library providing high-performance data structures 
and data analysis tools. Tkinter is the standard GUI toolkit for python. The pandastable
library provides a GUI frontend to the pandas DataFrame class. It is intended for the
following uses:

* for developers who want to include a table in their application that can store and process
large amounts of data
* for non-programmers who are not familiar with Python or the pandas API and want to use
the included table viewer application to manipulate/view their data
* it may also be useful for programmers who want to get an interactive look at their dataframes

The dataframe Viewer application using these classes is included in the distribution. 
Currently this focuses on providing a spreadsheet like interface for table manipulation with 
configurable 2D/3D plotting. A windows standalone installer will be provided to allow this
application to be used without any python knowledge.

## Installation

Requires python>=3.3 and numpy, matplotlib and pandas.
These requirements should be satisfied automatically when using:

```pip install pandastable```
or
```easy_install pandastable```

## Current features
* add, remove rows and columns
* spreadsheet-like drag, shift-click, ctrl-click selection
* edit individual cells
* sort by column, rename columns
* reorder columns dynamically by mouse drags
* set some basic formatting such as font, text size and column width
* save the DataFrame? to supported pandas formats
* import/export of supported text files
* rendering of very large tables is only memory limited
* interactive plots with matplotlib, mostly using the pandas plot functions

## Potential features
* filter table using built in dataframe functionality
* present/manipulate time series data since pandas deals well with this
* graphical way to perform split-apply-combine operations

## FAQ

*What version of Python?*

Python 3 compatible only since upgrading tkinter applications breaks too much for backwards compatibility. 
For a similar table widget that works in Python 2 see the previous incarnation, tkintertable.

*Why use Tkinter?*

Tkinter is still the standard GUI toolkit for python 3 though it is sometimes disliked 
for its outdated appearance (especially on linux) and limited widget set. However largely
because this library is based on an older one called tkintertable for drawing the table, 
I have stuck with tkinter rather than start from scratch using another toolkit.

*Is this just a half-baked spreadsheet?*

Hopefully not. Some of the basic functions are naturally present since it's a table. 
But there is no point in trying to mimic a proper spreadsheet app. pandas can do
lots of stuff that would be nice for a non-programmer to utilize and that might 
not be available in a spreadsheet application.

*Are there other better tools for dataframe visualization?*

This depends as always on what is required. bokeh, for example, is an advanced
interactive plotting tool using modern generation web technologies for in browser 
rendering. This can handle dataframes. The goal of this project is narrower - namely 
to provide a widget in a desktop appplication.

## The Viewer application
Installing the package creates a command pandasviewer in your path. Just run this to open the program. 
This is a standalone application for plotting and also serves as a way of testing the library.
Data can be saved and then re-loaded using the popup menu commands, currently as 
messagepack format. This is supported by pandas>=0.13.

<img src=https://raw.githubusercontent.com/dmnfarrell/pandastable/master/img/viewerapp.png width=600px>

## For programmers. 
The basics for now. More details to be added here.

Create a parent frame and then add the table to it:
```
from tkinter import *
from pandastable import Table
#assuming parent is the frame in which you want to place the table
pt = Table(parent)
pt.show()
```

Update the table:
```
#alter the DataFrame in some way, then update
pt.redraw()
```

Import a csv file:
```
pt.doImport('test.csv')
```

## Links

http://bokeh.pydata.org/

http://stanford.edu/~mwaskom/software/seaborn/

http://jakevdp.github.io/blog/2013/03/23/matplotlib-and-the-future-of-visualization-in-python/

## Screenshots

<img src=https://raw.githubusercontent.com/dmnfarrell/pandastable/master/img/plotviewer.png width=600px>
