Code Examples
=============

Basics
------

Create a parent frame and then add the table to it::

	from tkinter import *
	from pandastable import Table
	#assuming parent is the frame in which you want to place the table
	pt = Table(parent)
	pt.show()

Update the table::

	#alter the DataFrame in some way, then update
	pt.redraw()

Import a csv file::

	pt.importCSV('test.csv')

A class for launching a basic table in a frame::

	from tkinter import *
	from pandastable import Table, TableModel

	class TestApp(Frame):
		"""Basic test frame for the table"""
		def __init__(self, parent=None):
		    self.parent = parent
		    Frame.__init__(self)
		    self.main = self.master
		    self.main.geometry('600x400+200+100')
		    self.main.title('Table app')
		    f = Frame(self.main)
		    f.pack(fill=BOTH,expand=1)
		    df = TableModel.getSampleData()
		    self.table = pt = Table(f, dataframe=df,
		                            showtoolbar=True, showstatusbar=True)
		    pt.show()
		    return

	app = TestApp()
	#launch the app
	app.mainloop()

Table Coloring
--------------

You can set column colors by setting the key in the columncolors dict to a valid hex color code. Then just redraw::

	table.columncolors['mycol'] = '#dcf1fc' #color a specific column
	table.redraw()

You can set row and cell colors in several ways. ``table.rowcolors`` is a pandas dataframe that mirrors the current table and stores a color for each cell. It only adds columns as needed. You can update this manually but it is easiest to use the following methods::

	table.setRowColors(rows, color) #using row numbers
	table.setColorByMask(column, mask, color) #using a pre-defined mask
	table.redraw()

To color by column values::

	table.multiplecollist = [cols] #set the selected columns
	table.setColorbyValue()
	table.redraw()

To clear formatting::

	table.clearFormatting()
	table.redraw()

Writing DataExplore Plugins
---------------------------

Plugins are for adding custom functionality that is not present in the main application. They are implemented by sub-classing the Plugin class in the plugin module. This is a python script that can generally contain any code you wish. Usually the idea will be to implement a dialog that the user interacts with. But this could also be a single method that runs on the current table or all sheets at once.

Implementing a plugin
+++++++++++++++++++++

Plugins should inherit from the Plugin class. Though this is not strictly necessary for the plugin to function. 

``from pandastable.plugin import Plugin``

You can simply copy the example plugin to get started.  All plugins need to have a `main()` method which is called by the application to launch them. By default this method contains the `_doFrame()` method which constructs a main frame as part of the current table frame. Usually you override main() and call _doFrame then add your own custom code with your widgets.

_doFrame method has the following lines which are always needed unless it is a non GUI plugin::

	self.table = self.parent.getCurrentTable() #get the current table
	#add the plugin frame to the table parent
	self.mainwin = Frame(self.table.parentframe) 
	#pluginrow is 6 to make the frame appear below other widgets
	self.mainwin.grid(row=pluginrow,column=0,columnspan=2,sticky='news')

You can also override the quit() and about() methods.

Non-table based plugins
+++++++++++++++++++++++

Plugins that don't rely on using the table directly do not need to use the above method and can have essentially anything in them as long as there is a main() method present. The Batch File Rename plugin is an example. This is a standalone utility launched in a separate toplevel window. 

see https://github.com/dmnfarrell/pandastable/blob/master/pandastable/plugins/rename.py



