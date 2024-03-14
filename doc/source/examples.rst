Code Examples
=============

This section is for python programmers you want to use the table widget in their own programs.

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
	from pandastable import Table, TableModel, config

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
				#set some options
				options = {'colheadercolor':'green','floatprecision': 5}
				config.apply_options(options, pt)
		    pt.show()
		    return

	app = TestApp()
	#launch the app
	app.mainloop()

Sub-class the Table
-------------------

Override the right click popup menu::

	class MyTable(Table):
	    """Custom table class inherits from Table. You can then override required methods"""
	    def __init__(self, parent=None, **kwargs):
	        Table.__init__(self, parent, **kwargs)
        	return

		  def handle_left_click(self, event):
	        """Example - override left click"""

	        Table.handle_left_click(self, event)
          #do custom code here
	        return

	    def popupMenu(self, event, rows=None, cols=None, outside=None):
	        """Custom right click menu"""

	        popupmenu = Menu(self, tearoff = 0)
	        def popupFocusOut(event):
	            popupmenu.unpost()
					# add commands here
            # self.app is a reference to the parent app
	        popupmenu.add_command(label='do stuff', command=self.app.stuff)
	        popupmenu.bind("<FocusOut>", popupFocusOut)
	        popupmenu.focus_set()
	        popupmenu.post(event.x_root, event.y_root)
	        return popupmenu

Table methods
-------------

You can use the Table class methods to directly access data and perform many more functions. Check the API for all the methods. Some examples are given here::

	#add 10 empty columns
	table.autoAddColumns(10)
	#resize the columns to fit the data better
	table.autoResizeColumns()
	#clear the current formatting
	table.clearFormatting()
	#reduce column witdths proportionally
	table.contractColumns()
	#get selected column
	table.getSelectedColumn()
	#sort by column index 0
	table.sortTable(0)
	#enlarge all table elements
	table.zoomIn()
	#set row colors
	table.setRowColors(rows=range(2,100,2), clr='lightblue', cols='all')
	#delete selected rows
	table.setSelectedRows([[4,6,8,10]])
	#delete current row
	table.deleteRow()
	#set current row
	table.setSelectedRow(10)
	#insert below current row
	table.insertRow()

Accessing and modifying data directly
-------------------------------------

The tables use a pandas DataFrame object for storing the underlying data. If you are not familiar with pandas you should learn the basics if you need to access or manipulate the table data. See http://pandas.pydata.org/pandas-docs/stable/10min.html

Each table has an object called model with has the dataframe inside it. The dataframe is referred to as df. So to access the data on a table you can use::

	df = table.model.df

Examples of simple dataframe operations. Remember when you update the dataframe you will need to call table.redraw() to see the changes reflected::

	df.drop(0) #delete column with this index
	df.T #transpose the DataFrame
	df.drop(columns=['x'])

Set table attributes
--------------------

You can set table attributes directly such as these examples::

	table.textcolor = 'blue'
	table.cellbackgr = 'white'
	table.boxoutlinecolor = 'black'
	#display formats
	table.floatprecision = 2
	table.timeformat = "%Y-%m-%d"
	#set header colors
	self.table.rowheader.bgcolor = 'orange'
	self.table.colheader.bgcolor = 'lightgreen'
	self.table.colheader.textcolor = 'black'
	#make editable or not
	table.editable = False

Set Preferences
---------------

Preferences are used to save config settings so they can be re-used. These are normally loaded from a configuration file that can be edited manually or via the menu. You can also programmatically set these preferences using the config module::

	#load from a config file if you need to (done by default when tables are created)
	options = config.load_options()
	#options is a dict that you can set yourself
	options = {'floatprecision': 2}
	config.apply_options(options, table)

You can set the following configuration values::

	{'align': 'w',
	'cellbackgr': '#F4F4F3',
	'cellwidth': 80,
	'floatprecision': 2,
	'timeformat': "%Y-%m-%d",
	'thousandseparator': '',
	'font': 'Arial',
	'fontsize': 12,
	'fontstyle': '',
	'grid_color': '#ABB1AD',
	'linewidth': 1,
	'rowheight': 22,
	'rowselectedcolor': '#E4DED4',
	'textcolor': 'black'}

The preferences are saved to a default.conf file in the home folder config folder. The location depends on the system. On Ubuntu this is under ~/.config/pandastable.

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

Note: You should generally use a simple integer index for the table when using colors as there may be inconsistencies otherwise.

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

Freezing the app
----------------

Dataexplore is available as an exe with msi installer for Windows. This was created using the cx_freeze package. For anyone wishing to freeze their tkinter app some details are given here. This is a rather hit and miss process as it seems to depend on your installed version of Python. Even when the msi/exe builds you need to check for runtime issues on another copy of windows to make sure it's working.
Steps:

	* Use a recent version of python (>=3.6 recommended) installed as normal and then using pip to install the dependencies that you normally need to run the app.
	* The freeze script is found in the main pandastable folder, freeze.py. You can adopt it for your own app.
	* Run the script using `python freeze.py bdist_msi`
	* The resulting msi is placed in the dist folder. This is a 32 bit binary but should run fine on windows 10.

You can probably use Anaconda to do the same thing but we have not tested this.
