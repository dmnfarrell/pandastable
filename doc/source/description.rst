Introduction
============

The pandastable library provides a table widget for Tkinter with
plotting and data manipulation functionality. It uses the pandas
DataFrame class to store table data. Pandas is an open source Python
library providing high-performance data structures and data analysis
tools. Tkinter is the standard GUI toolkit for python. It is intended
for the following uses:

-  for python/tkinter GUI developers who want to include a table in
   their application that can store and process large amounts of data
-  for non-programmers who are not familiar with Python or the pandas
   API and want to use the included DataExplore application to
   manipulate/view their data
-  it may also be useful for data analysts and programmers who want to
   get an initial interactive look at their tabular data without coding

Current Features
================

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

The DataExplore application
===========================

Installing the package creates a command *dataexplore* in your path. Just run this to open the program. This is a standalone application for data manipulation and plotting meant for education and basic data analysis. More details are in the 'Using dataexplore' section. Also see the home page for this application at http://dmnfarrell.github.io/pandastable/

Links
=====

http://openresearchsoftware.metajnl.com/articles/10.5334/jors.94/

http://dmnfarrell.github.io/pandastable/

https://youtu.be/Ss0QIFywt74

Citation
========

If you use this software in your work please cite the following article:

Farrell, D 2016 DataExplore: An Application for General Data Analysis in Research and Education. Journal of Open Research Software, 4: e9, DOI: http://dx.doi.org/10.5334/jors.94

Installation
============

For Dataexplore
---------------

For **Windows users** there is an MSI installer for the DataExplore application. This is recommended for anyone using windows not using the library directly as a widget.

pandastable library
-------------------

On all operating systems installations of Python should include the pip tool. If not use your distributions package manager to install pip first. Then a simple call as follows should install all dependencies::

    pip install pandastable

This might not work well in some cases because matplotlib has library dependencies that users might find confusing. Though it should work ok on recent versions of Ubuntu. Advice for each OS is given below.

**Dependencies**

* numpy
* pandas
* matplotlib
* numexpr

**Optional dependencies**

* statsmodels
* seaborn (requires scipy)

Linux
-----

For the python linbrary using easy_install or pip should work well but for matplotlib might require more packages such as python headers for compiling the extension. You need the tk8.6-dev package to provide the tkagg backend.

Otherwise, to use the package manager in Ubuntu/Debian based distributions you can issue the command::

    sudo apt install python-matplotlib

You should install pandas with pip as it will provide the most recent version. This will likely be done automatically anyway:

For python 3 installs

You need to use the command pip3 instead if python 2 is also on your system, like in Ubuntu. When installing packages with apt you likely need to specify python 3. e.g. python3-numpy instead of python-numpy.

For python 2.7 ONLY

You will also need the future package. Run `pip install future` to install them. Python 2.6 has NOT been tested and probably won't work.

Windows
-------

It is much easier to install matplotlib in windows using the binary installer rather than using pip. You can download this [here](http://matplotlib.org/downloads.html). Pick the appropriate file for your python version  e.g. 'matplotlib-1.4.3.win32-py3.4.exe' for python 3.4.

pandas should install ok with the pip installer. In windows pip.exe is located under C:\Python34\Scripts. The future package is needed for python 2.7.

Note that the Python pydata stack can also be installed at once using miniconda, http://conda.pydata.org/miniconda.html. This includes a version of Python itself.

Mac OSX
-------

There are multiple packaged installers for scientific Python, the best of which is probably anaconda. Miniconda is a smaller version if you don't want all the packages. To use it download and run the Mac OS X installer from http://conda.pydata.org/miniconda.html. The installer will automatically configure your system to use the Anaconda Python. You can then use pip to install the package.

If using macports::

   sudo port install py34-pip
   sudo pip-3.4 install matplotlib numpy pandas numexpr

Using the source distribution file

You can download the latest tar.gz file [here](https://github.com/dmnfarrell/pandastable/releases/latest/) and do the following::

	tar -xzvf pandastable.version.tar.gz
	cd pandastable
	sudo python3 setup.py install

Note that you still need to have installed the dependencies as above.
