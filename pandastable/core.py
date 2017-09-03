#!/usr/bin/env python
"""
    Implements the core pandastable classes.
    Created Jan 2014
    Copyright (C) Damien Farrell

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 3
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from __future__ import absolute_import, division, print_function
try:
    from tkinter import *
    from tkinter.ttk import *
    from tkinter import filedialog, messagebox, simpledialog
except:
    from Tkinter import *
    from ttk import *
    import tkFileDialog as filedialog
    import tkSimpleDialog as simpledialog
    import tkMessageBox as messagebox
from tkinter import font
import math, time
import os, types
import string, copy
import platform
import numpy as np
import pandas as pd
from .data import TableModel
from .headers import ColumnHeader, RowHeader, IndexHeader
from .plotting import MPLBaseOptions, PlotViewer
from .prefs import Preferences
from .dialogs import ImportDialog
from . import images, util
from .dialogs import *

class Table(Canvas):
    """A tkinter class for providing table functionality.
        Args:
            parent: parent Frame
            model: a TableModel with some data
            dataframe: a pandas DataFrame
            width: width of frame
            height: height of frame
            rows: number of rows if creating empty table
            cols: number of columns if creating empty table
            showtoolbar: whether to show the toolbar, default False
            showstatusbar: whether to show the statusbar
    """

    def __init__(self, parent=None, model=None, dataframe=None,
                   width=None, height=None,
                   rows=20, cols=5, showtoolbar=False, showstatusbar=False,
                   **kwargs):

        Canvas.__init__(self, parent, bg='white',
                         width=width, height=height,
                         relief=GROOVE,
                         scrollregion=(0,0,300,200))
        self.parentframe = parent
        #get platform into a variable
        self.ostyp = util.checkOS()
        self.platform = platform.system()
        self.width = width
        self.height = height
        self.filename = None
        self.showtoolbar = showtoolbar
        self.showstatusbar = showstatusbar
        self.set_defaults()

        self.currentpage = None
        self.navFrame = None
        self.currentrow = 0
        self.currentcol = 0
        self.reverseorder = 0
        self.startrow = self.endrow = None
        self.startcol = self.endcol = None
        self.allrows = False
        self.multiplerowlist=[]
        self.multiplecollist=[]
        self.col_positions=[]
        self.mode = 'normal'
        self.editable = True
        self.filtered = False
        self.child = None
        self.queryrow = 4
        self.childrow = 5
        self.loadPrefs()
        self.currentdir = os.path.expanduser('~')
        #set any options passed in kwargs to overwrite defaults and prefs
        for key in kwargs:
            self.__dict__[key] = kwargs[key]

        if dataframe is not None:
            self.model = TableModel(dataframe=dataframe)
        elif model != None:
            self.model = model
        else:
            self.model = TableModel(rows=rows,columns=cols)

        self.rows = self.model.getRowCount()
        self.cols = self.model.getColumnCount()
        self.tablewidth = (self.cellwidth)*self.cols
        self.doBindings()

        #column specific actions, define for every column type in the model
        #when you add a column type you should edit this dict
        self.columnactions = {'text' : {"Edit":  'drawCellEntry' },
                              'number' : {"Edit": 'drawCellEntry' }}
        self.setFontSize()
        self.plotted = False
        self.importpath = None
        self.prevdf = None
        return

    def set_defaults(self):
        """Set default settings"""

        self.cellwidth = 60
        self.maxcellwidth=300
        self.mincellwidth = 30
        self.rowheight=20
        self.horizlines=1
        self.vertlines=1
        self.autoresizecols = 1
        self.inset=2
        self.x_start=0
        self.y_start=1
        self.linewidth=1.0
        self.rowheaderwidth=50
        self.showkeynamesinheader=False
        self.thefont = ('Arial',12)
        self.cellbackgr = '#F4F4F3'
        self.entrybackgr = 'white'
        self.grid_color = '#ABB1AD'
        self.rowselectedcolor = '#E4DED4'
        self.multipleselectioncolor = '#E0F2F7'
        self.boxoutlinecolor = '#084B8A'
        self.colselectedcolor = '#e4e3e4'
        self.floatprecision = 0
        self.columncolors = {}
        self.rowcolors = pd.DataFrame()
        self.bg = Style().lookup('TLabel.label', 'background')
        return

    def setFontSize(self):
        """Set font size to match font, we need to get rid of `size as
            a separate variable?"""

        if hasattr(self, 'thefont') and type(self.thefont) is tuple:
            self.fontsize = self.thefont[1]
        return

    def mouse_wheel(self, event):
        """Handle mouse wheel scroll for windows"""

        if event.num == 5 or event.delta == -120:
            event.widget.yview_scroll(1, UNITS)
            self.rowheader.yview_scroll(1, UNITS)
        if event.num == 4 or event.delta == 120:
            if self.canvasy(0) < 0:
                return
            event.widget.yview_scroll(-1, UNITS)
            self.rowheader.yview_scroll(-1, UNITS)
        self.redrawVisible()
        return

    def doBindings(self):
        """Bind keys and mouse clicks, this can be overriden"""

        self.bind("<Button-1>",self.handle_left_click)
        self.bind("<Double-Button-1>",self.handle_double_click)
        self.bind("<Control-Button-1>", self.handle_left_ctrl_click)
        self.bind("<Shift-Button-1>", self.handle_left_shift_click)

        self.bind("<ButtonRelease-1>", self.handle_left_release)
        if self.ostyp=='mac':
            #For mac we bind Shift, left-click to right click
            self.bind("<Button-2>", self.handle_right_click)
            self.bind('<Shift-Button-1>',self.handle_right_click)
        else:
            self.bind("<Button-3>", self.handle_right_click)

        self.bind('<B1-Motion>', self.handle_mouse_drag)
        #self.bind('<Motion>', self.handle_motion)

        self.bind("<Control-c>", self.copy)
        #self.bind("<Control-x>", self.deleteRow)
        #self.bind_all("<Control-n>", self.addRow)
        self.bind("<Delete>", self.clearData)
        self.bind("<Control-v>", self.paste)
        self.bind("<Control-a>", self.selectAll)

        self.bind("<Right>", self.handle_arrow_keys)
        self.bind("<Left>", self.handle_arrow_keys)
        self.bind("<Up>", self.handle_arrow_keys)
        self.bind("<Down>", self.handle_arrow_keys)
        self.parentframe.master.bind_all("<KP_8>", self.handle_arrow_keys)
        self.parentframe.master.bind_all("<Return>", self.handle_arrow_keys)
        self.parentframe.master.bind_all("<Tab>", self.handle_arrow_keys)
        #if 'windows' in self.platform:
        self.bind("<MouseWheel>", self.mouse_wheel)
        self.bind('<Button-4>', self.mouse_wheel)
        self.bind('<Button-5>', self.mouse_wheel)
        self.focus_set()
        return

    def show(self, callback=None):
        """Adds column header and scrollbars and combines them with
           the current table adding all to the master frame provided in constructor.
           Table is then redrawn."""

        #Add the table and header to the frame
        self.rowheader = RowHeader(self.parentframe, self, width=self.rowheaderwidth)
        self.tablecolheader = ColumnHeader(self.parentframe, self)
        self.rowindexheader = IndexHeader(self.parentframe, self)
        self.Yscrollbar = AutoScrollbar(self.parentframe,orient=VERTICAL,command=self.set_yviews)
        self.Yscrollbar.grid(row=1,column=2,rowspan=1,sticky='news',pady=0,ipady=0)
        self.Xscrollbar = AutoScrollbar(self.parentframe,orient=HORIZONTAL,command=self.set_xviews)
        self.Xscrollbar.grid(row=2,column=1,columnspan=1,sticky='news')
        self['xscrollcommand'] = self.Xscrollbar.set
        self['yscrollcommand'] = self.Yscrollbar.set
        self.tablecolheader['xscrollcommand'] = self.Xscrollbar.set
        self.rowheader['yscrollcommand'] = self.Yscrollbar.set
        self.parentframe.rowconfigure(1,weight=1)
        self.parentframe.columnconfigure(1,weight=1)

        self.rowindexheader.grid(row=0,column=0,rowspan=1,sticky='news')
        self.tablecolheader.grid(row=0,column=1,rowspan=1,sticky='news')
        self.rowheader.grid(row=1,column=0,rowspan=1,sticky='news')
        self.grid(row=1,column=1,rowspan=1,sticky='news',pady=0,ipady=0)

        self.adjustColumnWidths()
        self.parentframe.bind("<Configure>", self.redrawVisible)
        self.tablecolheader.xview("moveto", 0)
        self.xview("moveto", 0)
        if self.showtoolbar == True:
            self.toolbar = ToolBar(self.parentframe, self)
            self.toolbar.grid(row=0,column=3,rowspan=2,sticky='news')
        if self.showstatusbar == True:
            self.statusbar = statusBar(self.parentframe, self)
            self.statusbar.grid(row=3,column=0,columnspan=2,sticky='ew')
        self.redraw(callback=callback)
        if hasattr(self, 'pf'):
            self.pf.updateData()
        return

    def remove(self):
        """Close table frame"""

        if hasattr(self, 'parenttable'):
            self.parenttable.child.destroy()
            self.parenttable.child = None
            self.parenttable.plotted = 'main'
        self.parentframe.destroy()
        return

    def getVisibleRegion(self):
        """Get visible region of canvas"""

        x1, y1 = self.canvasx(0), self.canvasy(0)
        #w, h = self.winfo_width(), self.winfo_height()
        #if w <= 1.0 or h <= 1.0:
        w, h = self.master.winfo_width(), self.master.winfo_height()
        x2, y2 = self.canvasx(w), self.canvasy(h)
        return x1, y1, x2, y2

    def getRowPosition(self, y):
        """Set row position"""

        h = self.rowheight
        y_start = self.y_start
        row = (int(y)-y_start)/h
        if row < 0:
            return 0
        if row > self.rows:
            row = self.rows
        return int(row)

    def getColPosition(self, x):
        """Get column position at coord"""

        x_start = self.x_start
        w = self.cellwidth
        i=0
        col=0
        for c in self.col_positions:
            col = i
            if c+w>=x:
                break
            i+=1
        return int(col)

    def getVisibleRows(self, y1, y2):
        """Get the visible row range"""

        start = self.getRowPosition(y1)
        end = self.getRowPosition(y2)+1
        if end > self.rows:
            end = self.rows
        return start, end

    def getVisibleCols(self, x1, x2):
        """Get the visible column range"""

        start = self.getColPosition(x1)
        end = self.getColPosition(x2)+1
        if end > self.cols:
            end = self.cols
        return start, end

    def redrawVisible(self, event=None, callback=None):
        """Redraw the visible portion of the canvas"""

        model = self.model
        self.rows = len(self.model.df.index)
        self.cols = len(self.model.df.columns)
        if self.cols == 0 or self.rows == 0:
            self.delete('entry')
            self.delete('rowrect','colrect')
            self.delete('currentrect','fillrect')
            self.delete('gridline','text')
            self.delete('multicellrect','multiplesel')
            self.delete('colorrect')
            self.setColPositions()
            if self.cols == 0:
                self.tablecolheader.redraw()
            if self.rows == 0:
                self.visiblerows = []
                self.rowheader.redraw()
            return
        self.tablewidth = (self.cellwidth) * self.cols
        self.configure(bg=self.cellbackgr)
        self.setColPositions()

        #are we drawing a filtered subset of the recs?
        if self.filtered == True:
            self.delete('colrect')

        self.rowrange = list(range(0,self.rows))
        self.configure(scrollregion=(0,0, self.tablewidth+self.x_start,
                        self.rowheight*self.rows+10))

        x1, y1, x2, y2 = self.getVisibleRegion()
        startvisiblerow, endvisiblerow = self.getVisibleRows(y1, y2)
        self.visiblerows = list(range(startvisiblerow, endvisiblerow))
        startvisiblecol, endvisiblecol = self.getVisibleCols(x1, x2)
        self.visiblecols = list(range(startvisiblecol, endvisiblecol))

        self.drawGrid(startvisiblerow, endvisiblerow)
        align = self.align
        self.delete('fillrect')
        bgcolor = self.cellbackgr
        df = self.model.df

        #st=time.time()
        def set_precision(x, p):
            if not pd.isnull(x):
                if x<1:
                    x = '{:.{}g}'.format(x, p)
                else:
                    x = '{:.{}f}'.format(x, p)
            return x

        prec = self.floatprecision
        rows = self.visiblerows
        for col in self.visiblecols:
            coldata = df.iloc[rows,col]
            #print (col, coldata.dtype)
            if prec != 0:
                if coldata.dtype == 'float64':
                    coldata = coldata.apply(lambda x: set_precision(x, prec), 1)
                    #print (coldata)
            coldata = coldata.astype(object).fillna('')
            offset = rows[0]
            for row in self.visiblerows:
                text = coldata.iloc[row-offset]
                self.drawText(row, col, text, align)
            colname = df.columns[col]

        self.colorColumns()
        self.colorRows()
        self.tablecolheader.redraw()
        self.rowheader.redraw(align=self.align)
        self.rowindexheader.redraw()
        self.drawSelectedRow()
        self.drawSelectedRect(self.currentrow, self.currentcol)
        if len(self.multiplerowlist)>1:
            self.rowheader.drawSelectedRows(self.multiplerowlist)
            self.drawMultipleRows(self.multiplerowlist)
            self.drawMultipleCells()

        return

    def redraw(self, event=None, callback=None):
        """Redraw table"""

        self.redrawVisible(event, callback)
        if hasattr(self, 'statusbar'):
            self.statusbar.update()
        return

    def redrawCell(self, row=None, col=None, recname=None, colname=None):
        """Redraw a specific cell only"""

        text = self.model.getValueAt(row,col)
        self.delete('celltext'+str(col)+'_'+str(row))
        self.drawText(row, col, text)
        return

    def setColumnColors(self, cols=None, clr=None):
        """Set a column color and store it"""

        if clr is None:
            clr = self.getaColor('#dcf1fc')
        if clr == None:
            return
        if cols == None:
            cols = self.multiplecollist
        colnames = self.model.df.columns[cols]
        for c in colnames:
            self.columncolors[c] = clr
        self.redraw()
        return

    def colorColumns(self, cols=None, color='gray'):
        """Color visible columns"""

        if cols is None:
            cols = self.visiblecols
        self.delete('colorrect')
        for c in cols:
            colname = self.model.df.columns[c]
            if colname in self.columncolors:
                clr = self.columncolors[colname]
                self.drawSelectedCol(c, delete=0, color=clr, tag='colorrect')
        return

    def setColorByMask(self, col, mask, clr):
        """Color individual cells in a column using a mask."""

        df = self.model.df
        if len(self.rowcolors) == 0:
            self.rowcolors = pd.DataFrame(index=range(len(df)))
        rc = self.rowcolors
        if col not in rc.columns:
            rc[col] = pd.Series()
        rc[col] = rc[col].where(-mask, clr)
        #print (rc)
        return

    def colorRows(self):
        """Color individual cells in column(s). Requires that the rowcolors
         dataframe has been set. This needs to be updatedif the index is reset"""

        #if len(self.rowcolors==0):
        #    return
        df = self.model.df
        rc = self.rowcolors
        rows = self.visiblerows
        offset = rows[0]
        idx = df.index[rows]
        for col in self.visiblecols:
            colname = df.columns[col]
            if colname in list(rc.columns):
                colors = rc[colname].ix[idx]
                for row in rows:
                    clr = colors.iloc[row-offset]
                    if not pd.isnull(clr):
                        self.drawRect(row, col, color=clr, tag='colorrect', delete=1)
        return

    def setRowColors(self, rows=None, clr=None):
        """Set rows color from menu"""

        if clr is None:
            clr = self.getaColor('#dcf1fc')
        if clr == None:
            return
        if rows == None:
            rows = self.multiplerowlist
        df = self.model.df
        idx = df.index[rows]
        rc = self.rowcolors
        colnames = df.columns[self.multiplecollist]
        for c in colnames:
            if c not in rc.columns:
                rc[c] = pd.Series(np.nan,index=df.index)
            rc[c][idx] = clr
        self.redraw()
        return

    def setColorbyValue(self):
        """Set row colors in a column by values"""

        import pylab as plt
        cmaps = sorted(m for m in plt.cm.datad if not m.endswith("_r"))
        cols = self.multiplecollist
        d = MultipleValDialog(title='color by value',
                                initialvalues=[cmaps,1.0],
                                labels=['colormap:','alpha:'],
                                types=['combobox','string'],
                                parent = self.parentframe)
        if d.result == None:
            return
        cmap = d.results[0]
        alpha =float(d.results[1])
        df = self.model.df
        for col in cols:
            colname = df.columns[col]
            x = df[colname]
            clrs = self.values_to_colors(x, cmap, alpha)
            clrs = pd.Series(clrs,index=df.index)
            rc = self.rowcolors
            rc[colname] = clrs
        self.redraw()
        return

    def values_to_colors(self, x, cmap='jet', alpha=1):
        """Convert columnn values to colors"""

        import pylab as plt
        import matplotlib as mpl
        cmap = plt.cm.get_cmap(cmap)
        #if x.dtype in ['int','float64']:
        if x.dtype in ['object']:#,'category']:
            x = pd.Categorical(x).codes
        x = (x-x.min())/(x.max()-x.min())
        clrs = cmap(x)
        clrs = mpl.colors.to_rgba_array(clrs, alpha)
        clrs = [mpl.colors.rgb2hex(i) for i in clrs]
        return clrs

    def getScale(self):
        try:
            fontsize = self.thefont[1]
        except:
            fontsize = self.fontsize
        scale = 8.5 * float(fontsize)/9
        return scale

    def adjustColumnWidths(self):
        """Optimally adjust col widths to accomodate the longest entry
            in each column - usually only called on first redraw"""

        try:
            fontsize = self.thefont[1]
        except:
            fontsize = self.fontsize
        scale = self.getScale()
        for col in range(self.cols):
            colname = self.model.getColumnName(col)
            if colname in self.model.columnwidths:
                w = self.model.columnwidths[colname]
            else:
                w = self.cellwidth
            l = self.model.getlongestEntry(col)
            txt = ''.join(['X' for i in range(l+1)])
            tw,tl = util.getTextLength(txt, self.maxcellwidth,
                                       font=self.thefont)
            #print (col,txt,l,tw)
            if tw >= self.maxcellwidth:
                tw = self.maxcellwidth
            elif tw < self.cellwidth:
                tw = self.cellwidth
            self.model.columnwidths[colname] = tw
        return

    def autoResizeColumns(self):
        """Automatically set nice column widths and draw"""

        self.adjustColumnWidths()
        self.redraw()
        return

    def setColPositions(self):
        """Determine current column grid positions"""

        df = self.model.df
        self.col_positions=[]
        w = self.cellwidth
        x_pos = self.x_start
        self.col_positions.append(x_pos)
        for col in range(self.cols):
            colname = str(df.columns[col])
            if colname in self.model.columnwidths:
                x_pos = x_pos+self.model.columnwidths[colname]
            else:
                x_pos = x_pos+w
            self.col_positions.append(x_pos)
        self.tablewidth = self.col_positions[len(self.col_positions)-1]
        return

    def sortTable(self, columnIndex=None, ascending=1, index=False):
        """Set up sort order dict based on currently selected field"""

        df = self.model.df
        if columnIndex == None:
            columnIndex = self.multiplecollist
        if isinstance(columnIndex, int):
            columnIndex = [columnIndex]
        #assert len(columnIndex) < len(df.columns)
        if index == True:
            df.sort_index(inplace=True)
        else:
            colnames = list(df.columns[columnIndex])
            try:
                df.sort_values(by=colnames, inplace=True, ascending=ascending)
            except Exception as e:
                print('could not sort')
                print(e)
        self.redraw()
        return

    def sortColumnIndex(self):
        """Sort the column header by the current rows values"""

        cols = self.model.df.columns
        #get only sortable cols
        temp = self.model.df.convert_objects(convert_numeric=True)
        temp = temp.select_dtypes(include=['int','float'])
        rowindex = temp.index[self.currentrow]
        row = temp.ix[rowindex]
        #add unsortable cols to end of new ordered ones
        newcols = list(temp.columns[row.argsort()])
        a = list(set(cols) - set(newcols))
        newcols.extend(a)
        self.model.df = self.model.df.reindex(columns=newcols)
        self.redraw()
        return

    def groupby(self, colindex):
        """Group by"""

        grps = self.model.groupby(colindex)
        return

    def setindex(self):
        """Set indexes"""

        cols = self.multiplecollist
        self.model.setindex(cols)
        if self.model.df.index.name is not None:
            self.showIndex()
        self.setSelectedCol(0)
        self.update_rowcolors()
        self.redraw()
        self.drawSelectedCol()
        if hasattr(self, 'pf'):
            self.pf.updateData()
        return

    def resetIndex(self):
        """Reset index and redraw row header"""

        self.model.resetIndex()
        self.update_rowcolors()
        self.redraw()
        self.drawSelectedCol()
        if hasattr(self, 'pf'):
            self.pf.updateData()
        return

    def flattenIndex(self):
        """FLatten multiindex"""

        df = self.model.df
        df.columns = df.columns.get_level_values(0)
        #self.model.df
        self.redraw()
        if hasattr(self, 'pf'):
            self.pf.updateData()
        return

    def copyIndex(self):
        """Copy index to a column"""

        self.model.copyIndex()
        self.redraw()
        return

    def renameIndex(self, ):
        """Rename the row index"""

        n = self.model.df.index.name
        name = simpledialog.askstring("New index name",
                                      "New name:",initialvalue=n,
                                       parent=self.parentframe)
        if name:
            self.model.df.index.name = name
            self.rowindexheader.redraw()
        return

    def showIndex(self):
        """Show the row index"""

        self.rowheader.showindex = True
        return

    def update_rowcolors(self):
        """Update row colors if present"""

        df = self.model.df
        if len(self.rowcolors) == len(df):
            self.rowcolors.set_index(df.index, inplace=True)
        return

    def set_xviews(self,*args):
        """Set the xview of table and col header"""

        self.xview(*args)
        self.tablecolheader.xview(*args)
        self.redrawVisible()
        return

    def set_yviews(self,*args):
        """Set the xview of table and row header"""

        self.yview(*args)
        self.rowheader.yview(*args)
        self.redrawVisible()
        return

    def addRow(self):
        """Insert a new row"""

        row = self.getSelectedRow()
        key = self.model.addRow(row)
        self.redraw()
        return

    def addRows(self, num=None):
        """Add new rows"""

        if num == None:
            num = simpledialog.askinteger("Now many rows?",
                                            "Number of rows:",initialvalue=1,
                                             parent=self.parentframe)
        if not num:
            return
        self.storeCurrent()
        keys = self.model.autoAddRows(num)
        self.redraw()
        return

    def addColumn(self, newname=None):
        """Add a new column"""

        if newname == None:
            coltypes = ['object','float64']
            d = MultipleValDialog(title='New Column',
                                    initialvalues=(coltypes, ''),
                                    labels=('Column Type','Name'),
                                    types=('combobox','string'),
                                    parent = self.parentframe)
            if d.result == None:
                return
            else:
                dtype = d.results[0]
                newname = d.results[1]

        df = self.model.df
        if newname != None:
            if newname in self.model.df.columns:
                messagebox.showwarning("Name exists",
                                        "Name already exists!",
                                        parent=self.parentframe)
            else:
                self.storeCurrent()
                self.model.addColumn(newname, dtype)
                self.parentframe.configure(width=self.width)
                self.redraw()
                self.tableChanged()
        return

    def deleteRow(self):
        """Delete a row"""

        if len(self.multiplerowlist)>1:
            n = messagebox.askyesno("Delete",
                                      "Delete selected rows?",
                                      parent=self.parentframe)
            if n == True:
                self.storeCurrent()
                rows = self.multiplerowlist
                self.model.deleteRows(rows)
                self.setSelectedRow(0)
                self.clearSelected()
                self.redraw()
        else:
            n = messagebox.askyesno("Delete",
                                      "Delete this row?",
                                      parent=self.parentframe)
            if n:
                self.storeCurrent()
                row = self.getSelectedRow()
                self.model.deleteRow(row)
                self.setSelectedRow(row-1)
                self.clearSelected()
                self.redraw()
        return

    def deleteColumn(self):
        """Delete currently selected column(s)"""

        n =  messagebox.askyesno("Delete",
                                   "Delete Column(s)?",
                                   parent=self.parentframe)
        if not n:
            return
        self.storeCurrent()
        cols = self.multiplecollist
        self.model.deleteColumns(cols)
        self.setSelectedCol(0)
        self.redraw()
        self.drawSelectedCol()
        self.tableChanged()
        return

    def tableChanged(self):
        """Callback to be used when dataframe changes so that other
            widgets and data can be updated"""

        self.updateFunctions()
        if hasattr(self, 'pf'):
            self.pf.updateData()
        return

    def storeCurrent(self):
        """Store current version of the table before a major change is made"""

        self.prevdf = self.model.df.copy()
        return

    def undo(self):
        """Undo last major table change"""

        if self.prevdf is None:
            return
        self.model.df = self.prevdf
        self.redraw()
        self.prevdf = None
        return

    def deleteCells(self, rows, cols, answer=None):
        """Clear the cell contents"""

        if answer == None:
            answer =  messagebox.askyesno("Clear Confirm",
                                    "Clear this data?",
                                    parent=self.parentframe)
        if not answer:
            return
        self.storeCurrent()
        self.model.deleteCells(rows, cols)
        self.redraw()
        return

    def clearData(self, evt=None):
        """Delete cells from gui event"""

        if self.allrows == True:
            self.deleteColumn()
            return
        rows = self.multiplerowlist
        cols = self.multiplecollist
        self.deleteCells(rows, cols)
        return

    def clearTable(self):
        """Make an empty table"""
        n =  messagebox.askyesno("Clear Confirm",
                                   "This will clear the entire table.\nAre you sure?",
                                   parent=self.parentframe)
        if not n:
            return
        self.storeCurrent()
        model = TableModel(pd.DataFrame())
        self.updateModel(model)
        self.redraw()
        self.tableChanged()
        return

    def fillColumn(self):
        """Fill a column with a data range"""

        dists = ['normal','gamma','uniform','random integer','logistic']
        d = MultipleValDialog(title='New Column',
                                initialvalues=(0,1,False,dists,1.0,1.0),
                                labels=('Low','High','Random Noise','Distribution','Mean','Std'),
                                types=('string','string','checkbutton','combobox','float','float'),
                                tooltips=('start value if filling with data',
                                          'end value if filling with data',
                                          'create random noise data in the ranges',
                                          'sampling distribution for noise',
                                          'mean/scale of distribution',
                                          'std dev./shape of distribution'),
                                parent = self.parentframe)
        if d.result == None:
            return
        else:
            low = d.results[0]
            high = d.results[1]
            random = d.results[2]
            dist = d.results[3]
            param1 = float(d.results[4])
            param2 = float(d.results[5])

        df = self.model.df
        if low != '' and high != '':
            try:
                low=float(low); high=float(high)
            except:
                return
        if random == True:
            if dist == 'normal':
                data = np.random.normal(param1, param2, len(df))
            elif dist == 'gamma':
                data = np.random.gamma(param1, param2, len(df))
            elif dist == 'uniform':
                data = np.random.uniform(low, high, len(df))
            elif dist == 'random integer':
                data = np.random.randint(low, high, len(df))
            elif dist == 'logistic':
                data = np.random.logistic(low, high, len(df))
        else:
            step = (high-low)/len(df)
            data = pd.Series(np.arange(low,high,step))
        col = df.columns[self.currentcol]
        df[col] = data
        self.redraw()
        return

    def autoAddColumns(self, numcols=None):
        """Automatically add x number of cols"""

        if numcols == None:
            numcols = simpledialog.askinteger("Auto add rows.",
                                                "How many empty columns?",
                                                parent=self.parentframe)
        self.model.auto_AddColumns(numcols)
        self.parentframe.configure(width=self.width)
        self.redraw()
        return

    def setColumnType(self):
        """Change the column dtype"""

        df = self.model.df
        col = df.columns[self.currentcol]
        coltypes = ['object','str','int','float64','category']
        curr = df[col].dtype
        d = MultipleValDialog(title='current type is %s' %curr,
                                initialvalues=[coltypes],
                                labels=['Type:'],
                                types=['combobox'],
                                parent = self.parentframe)
        if d.result == None:
            return
        t = d.results[0]
        try:
            self.model.df[col] = df[col].astype(t)
            self.redraw()
        except:
            print('failed')
        return

    def cleanData(self):
        """Deal with missing data"""

        df = self.model.df
        cols = df.columns
        fillopts = ['','fill scalar','ffill','bfill','interpolate']
        d = MultipleValDialog(title='Clean Data',
                                initialvalues=(fillopts,'-','10',0,0,['any','all'],0,0,0),
                                labels=('Fill missing method:',
                                        'Fill symbol:',
                                        'Limit gaps:',
                                        'Drop columns with null data:',
                                        'Drop rows with null data:',
                                        'Drop method:',
                                        'Drop duplicate rows:',
                                        'Drop duplicate columns:',
                                        'Round numbers:'),
                                types=('combobox','string','string','checkbutton',
                                       'checkbutton','combobox','checkbutton','checkbutton','string'),
                                parent = self.parentframe)
        if d.result == None:
            return
        self.storeCurrent()
        method = d.results[0]
        symbol = d.results[1]
        limit = int(d.results[2])
        dropcols = d.results[3]
        droprows = d.results[4]
        how = d.results[5]
        dropdups = d.results[6]
        dropdupcols = d.results[7]
        rounddecimals = int(d.results[8])
        if method == '':
            pass
        elif method == 'fill scalar':
            df = df.fillna(symbol)
        elif method == 'interpolate':
            df = df.interpolate()
        else:
            df = df.fillna(method=method, limit=limit)
        if dropcols == 1:
            df = df.dropna(axis=1,how=how)
        if droprows == 1:
            df = df.dropna(axis=0,how=how)
        if dropdups == 1:
            df = df.drop_duplicates()
        if dropdupcols == 1:
            df = df.loc[:,~df.columns.duplicated()]
        if rounddecimals != 0:
            df = df.round(rounddecimals)
        self.model.df = df
        self.redraw()
        return

    def createCategorical(self):
        """Get a categorical column from selected"""

        df = self.model.df
        col = df.columns[self.currentcol]

        d = MultipleValDialog(title='Categorical data',
                                initialvalues=(0,'',0,'','',''),
                                labels=('Convert to integer codes:','Name:',
                                        'Get dummies:','Dummies prefix:',
                                        'Numerical bins:','Labels:'),
                                types=('checkbutton','string','checkbutton',
                                       'string','string','string'),
                                tooltips=(None, 'name if new column',
                                         'get dummy columns for fitting',None,
                                         'define bins edges for numerical data',
                                         'labels for bins'),
                                parent = self.parentframe)
        if d.result == None:
            return
        self.storeCurrent()
        convert = d.results[0]
        name = d.results[1]
        dummies = d.results[2]
        prefix = d.results[3]
        bins = d.results[4]
        binlabels = d.results[5]

        if name == '':
            name = col
        if prefix == '':
            prefix=None
        if dummies == 1:
            new = pd.get_dummies(df[col], prefix=prefix)
            new.columns = new.columns.astype(str)
            self.model.df = pd.concat([df,new],1)
        elif convert == 1:
            df[name] = pd.Categorical(df[col]).codes
        elif bins != '':
            bins = [int(i) for i in bins.split(',')]
            if len(bins)==1:
                bins = int(bins[0])
                binlabels = list(string.ascii_uppercase[:bins])
            else:
                binlabels = binlabels.split(',')
            if name == col:
                name = col+'_binned'
            df[name] = pd.cut(df[col], bins, labels=binlabels)
        else:
            df[name] = df[col].astype('category')
        if name != col:
            self.placeColumn(name, col)
        else:
            self.redraw()
        return

    def applyColumnWise(self, evt=None):
        """Apply col wise function"""

        df = self.model.df
        cols = list(df.columns[self.multiplecollist])

        funcs = ['mean','std','max','min','log','exp','log10','log2',
                 'round','floor','ceil','trunc',
                 'sum','subtract','divide','mod','remainder','convolve',
                 'negative','sign','power',
                 'sin','cos','tan','degrees','radians']

        d = MultipleValDialog(title='Apply Function',
                                initialvalues=(funcs,'',False,'_x'),
                                labels=('Function:',
                                        'New column name:',
                                        'In place:',
                                        'New column suffix:'),
                                types=('combobox','string','checkbutton','string'),
                                tooltips=(None,
                                          'New column name',
                                          'Update in place',
                                          'suffix for new columns'),
                                parent = self.parentframe)
        if d.result == None:
            return
        self.storeCurrent()
        funcname = d.results[0]
        newcol = d.results[1]
        inplace = d.results[2]
        suffix = d.results[3]

        func = getattr(np, funcname)
        if newcol == '':
            newcol = funcname + '(%s)' %(','.join(cols))
        if funcname in ['subtract','divide','mod','remainder','convolve']:
            newcol = cols[0]+' '+ funcname +' '+cols[1]
            df[newcol] = df[cols[0]].combine(df[cols[1]], func=func)
        else:
            if inplace == True:
                newcol = cols[0]
            df[newcol] = df[cols].apply(func, 1)
        if inplace == False:
            self.placeColumn(newcol,cols[-1])
        else:
            self.redraw()
        return

    def applyFunction(self, evt=None):
        """Apply row-wise functions on a column/Series"""

        df = self.model.df
        cols = list(df.columns[self.multiplecollist])

        funcs = ['value_counts','rolling_mean','rolling_count',
                 'resample','shift']

        d = MultipleValDialog(title='Apply Function',
                                initialvalues=(funcs,'',False,False,'_x'),
                                labels=('Function:','or Function name:',
                                        'Add as new column(s):',
                                        'Replace table:',
                                        'New column suffix:'),
                                types=('combobox','string','checkbutton',
                                       'checkbutton','string'),
                                tooltips=(None,'Manually enter a pandas function name',
                                          'Add the result to the table',
                                          'Replace current table or open in subtable',
                                          'suffix for new columns'),
                                parent = self.parentframe)
        if d.result == None:
            return

        funcname = d.results[1]
        addcols = d.results[2]
        replace = d.results[3]
        suffix = d.results[4]
        if funcname == '':
            funcname = d.results[0]

        new = self._callFunction(df[cols], funcname)
        if new is None:
            return
        #if isinstance(new, pd.Series):
        #    new = pd.DataFrame(new)
        if addcols == True:
            new = df.merge(new, left_index=1,right_index=1,suffixes=['',suffix])
        if replace == True:
            self.model.df = new
            self.showIndex()
            self.redraw()
        else:
            self.createChildTable(new, index=True)
        return

    def resample(self):
        """table resampling dialog"""

        df = self.model.df
        if not isinstance(df.index, pd.DatetimeIndex):
            messagebox.showwarning("No datetime index", 'Index should be a datetime',
                                   parent=self.parentframe)
            return

        conv = ['start','end']
        freqs = ['M','W','D','H','min','S','Q','A','AS','L','U']
        funcs = ['mean','sum','count','max','min','std','first','last']
        d = MultipleValDialog(title='Resample',
                                initialvalues=(freqs,1,funcs,conv),
                                labels=('Frequency:','Periods','Function'),
                                types=('combobox','string','combobox'),
                                tooltips=('Unit of time e.g. M for months',
                                          'How often to group e.g. every 2 months',
                                          'Function to apply'),
                                parent = self.parentframe)
        if d.result == None:
            return
        freq = d.results[0]
        period = d.results[1]
        func = d.results[2]
        #conv = d.results[3]

        rule = str(period)+freq
        new = df.resample(rule).apply(func)
        self.createChildTable(new, index=True)
        #df.groupby(pd.TimeGrouper(freq='M'))
        return

    def _callFunction(self, df, funcname):
        """Get function from a string as a module level or dataframe method and
        apply it to the dataframe. Pops up a dialog allowing entry of arguments as some
        functions will not run without non kw args. This is meant to be a general
        solution to applying functions without the need to custom dialogs.
        Returns the new DataFrame"""

        col = df.columns[0]
        import inspect
        if hasattr(pd, funcname):
            func = getattr(pd, funcname)
            obj = pd
        elif hasattr(df, funcname):
            func = getattr(df, funcname)
            obj = df
        elif hasattr(df[col].str, funcname):
            #string methods object
            func = getattr(df[col].str, funcname)
            obj = df[col].str
        else:
            return

        a = inspect.getfullargspec(func)
        args = a.args
        if a.defaults is None:
            p={}
        else:
            defaults = list(a.defaults)
            print (args[0])
            if args[0] not in ['values','self','data']:
                defaults.insert(0,a.varargs)
            print(defaults)
            labels = a.args[-len(defaults):]
            types=[]
            for d in defaults:
                if isinstance(d, bool):
                    t='checkbutton'
                elif isinstance(d, int):
                    t='int'
                else:
                    t='string'
                types.append(t)

            #print(labels)
            print(types)
            #auto populate a dialog with function parameters
            d = MultipleValDialog(title='Parameters',
                                  initialvalues=defaults,
                                  labels=labels,
                                  types=types,
                                  parent = self.parentframe)
            p = d.getResults(null='')
            print(p)

        #print (obj)
        if obj is pd:
            new = df.apply(func, **p)
        elif obj is df:
            new = func(**p)
        else:
            new = func(**p)
        return new

    def applyStringMethod(self):
        """Apply string operation to column(s)"""

        df = self.model.df
        cols = list(df.columns[self.multiplecollist])
        col = cols[0]
        funcs = ['','split','strip','lstrip','lower','upper','title','swapcase','len',
                 'slice','replace','concat']
        d = MultipleValDialog(title='Apply Function',
                                initialvalues=(funcs,',',0,1,'','',0),
                                labels=('Function:',
                                        'Split sep:',
                                        'Slice start:',
                                        'Slice end:',
                                        'Pattern:',
                                        'Replace with:',
                                        'Add as new column(s):'),
                                types=('combobox','string','int',
                                       'int','string','string','checkbutton'),
                                tooltips=(None,'separator for split or concat',
                                          'start index for slice',
                                          'end index for slice',
                                          'characters or regular expression for replace',
                                          'characters to replace with',
                                          'do not replace column'),
                                parent = self.parentframe)
        if d.result == None:
            return
        self.storeCurrent()
        func = d.results[0]
        sep = d.results[1]
        start = d.results[2]
        end = d.results[3]
        pat = d.results[4]
        repl = d.results[5]
        newcol = d.results[6]
        if func == 'split':
            new = df[col].str.split(sep).apply(pd.Series)
            new.columns = [col+'_'+str(i) for i in new.columns]
            self.model.df = pd.concat([df,new],1)
            self.redraw()
            return
        elif func == 'strip':
            x = df[col].str.strip()
        elif func == 'lstrip':
            x = df[col].str.lstrip(pat)
        elif func == 'upper':
            x = df[col].str.upper()
        elif func == 'lower':
            x = df[col].str.lower()
        elif func == 'title':
            x = df[col].str.title()
        elif func == 'swapcase':
            x = df[col].str.swapcase()
        elif func == 'len':
            x = df[col].str.len()
        elif func == 'slice':
            x = df[col].str.slice(start,end)
        elif func == 'replace':
            x = df[col].replace(pat, repl, regex=True)
        elif func == 'concat':
            x = df[col].str.cat(df[cols[1]].astype(str), sep=sep)
        if newcol == 1:
            col = col+'_'+func
        df[col] = x
        self.redraw()
        return

    def convertDates(self):
        """Convert single or multiple columns into datetime"""

        df = self.model.df
        cols = list(df.columns[self.multiplecollist])
        if len(cols) == 1:
            colname = cols[0]
            temp = df[colname]
        else:
            colname = '-'.join(cols)
            temp = df[cols]

        if len(cols) == 1 and temp.dtype == 'datetime64[ns]':
            title = 'Date->string extract'
        else:
            title = 'String->datetime convert'
        timeformats = ['infer','%d%m%Y','%Y%m%d']
        props = ['day','month','minute','second','year',
                 'dayofyear','weekofyear','quarter']
        d = MultipleValDialog(title=title,
                                initialvalues=['',timeformats,props,True],
                                labels=['Column name:','Convert to date:',
                                        'Extract from datetime:','In place:'],
                                types=['string','combobox','combobox','checkbutton'],
                                parent = self.parentframe)

        if d.result == None:
            return
        self.storeCurrent()
        newname = d.results[0]
        if newname != '':
            colname = newname
        fmt = d.results[1]
        prop = d.results[2]
        inplace = d.results[3]
        if fmt == 'infer':
            fmt = None

        if len(cols) == 1 and temp.dtype == 'datetime64[ns]':
            if newname == '':
                colname = prop
            df[colname] = getattr(temp.dt, prop)
        else:
            try:
                df[colname] = pd.to_datetime(temp, format=fmt, errors='coerce')
            except Exception as e:
                messagebox.showwarning("Convert error", e,
                                        parent=self.parentframe)
        if inplace == False or len(cols)>1:
            #print (cols[-1])
            self.placeColumn(colname, cols[-1])

        self.redraw()
        self.tableChanged()
        return

    def showAll(self):
        """Re-show unfiltered"""

        if hasattr(self, 'dataframe'):
            self.model.df = self.dataframe
        self.filtered = False
        self.redraw()
        return

    def statsViewer(self):
        """Show model fitting dialog"""

        from .stats import StatsViewer
        if StatsViewer._doimport() == 0:
            messagebox.showwarning("no such module",
                                    "statsmodels is not installed.",
                                    parent=self.parentframe)
            return

        if not hasattr(self, 'sv') or self.sv == None:
            sf = self.statsframe = Frame(self.parentframe)
            sf.grid(row=self.queryrow+1,column=0,columnspan=3,sticky='news')
            self.sv = StatsViewer(table=self,parent=sf)
        return self.sv

    def getRowsFromIndex(self, idx=None):
        """Get row positions from index values"""

        df = self.model.df
        if idx is not None:
            return [df.index.get_loc(i) for i in idx]
        return []

    def getRowsFromMask(self, mask):
        df = self.model.df
        if mask is not None:
            idx = df.ix[mask].index
        return self.getRowsFromIndex(idx)

    def query(self, evt=None):
        """Do query"""

        self.qframe.query()
        return

    def queryBar(self, evt=None):
        """Query/filtering dialog"""

        if hasattr(self, 'qframe') and self.qframe != None:
            return
        self.qframe = QueryDialog(self)
        self.qframe.grid(row=self.queryrow,column=0,columnspan=3,sticky='news')
        return

    def _eval(self, df, ex):
        """Evaluate an expression using numexpr"""

        #uses assignments to globals() - check this is ok
        import numexpr as ne
        for c in df:
            globals()[c] = df[c].as_matrix()
        a = ne.evaluate(ex)
        return a

    def evalFunction(self, evt=None):
        """Apply a string based function to create new columns"""

        self.convertNumeric()
        s = self.evalvar.get()

        if s=='':
            return
        df = self.model.df
        vals = s.split('=')
        if len(vals)==1:
            ex = vals[0]
            n = ex
        else:
            n, ex = vals
        if n == '':
            return
        #evaluate
        try:
            df[n] = self._eval(df, ex)
            self.functionentry.configure(style="White.TCombobox")
        except Exception as e:
            print ('function parse error')
            print (e)
            self.functionentry.configure(style="Red.TCombobox")
            return
        #keep track of which cols are functions?
        self.formulae[n] = ex

        if self.placecolvar.get() == 1:
            cols = df.columns
            self.placeColumn(n,cols[0])
        if self.recalculatevar.get() == 1:
            self.recalculateFunctions(omit=n)
        else:
            self.redraw()
        if hasattr(self, 'pf') and self.updateplotvar.get()==1:
            self.plotSelected()
        #update functions list in dropdown
        funclist = ['='.join(i) for i in self.formulae.items()]
        self.functionentry['values'] = funclist
        return

    def recalculateFunctions(self, omit=None):
        """Re evaluate any columns that were derived from functions
        and dependent on other columns (except self derived?)"""

        df = self.model.df
        for n in self.formulae:
            if n==omit: continue
            ex = self.formulae[n]
            #need to check if self calculation here...
            try:
                df[n] = self._eval(df, ex)
            except:
                print('could not calculate %s' %ex)
        self.redraw()
        return

    def updateFunctions(self):
        """Remove functions if a column has been deleted"""

        if not hasattr(self, 'formulae'):
            return
        df = self.model.df
        cols = list(df.columns)
        for n in list(self.formulae.keys()):
            if n not in cols:
                del(self.formulae[n])
        return

    def functionsBar(self, evt=None):
        """Apply python functions from a pre-defined set, this is
        for stuff that can't be done with eval strings"""

        def reset():
            self.evalframe.destroy()
            self.evalframe = None
            self.showAll()

        def apply():
            self.convertNumeric()
            f = self.funcvar.get()
            print (f)
            df = self.model.df
            z = df['filename'].apply(lambda x: x.replace('fa',''))
            print (z)
            return

        if hasattr(self, 'funcsframe') and self.funcsframe != None:
            return
        ef = self.funcsframe = Frame(self.parentframe)
        ef.grid(row=self.queryrow,column=1,sticky='news')
        #self.evalvar = StringVar()
        #e = Entry(ef, textvariable=self.evalvar, font="Courier 13 bold")
        #e.bind('<Return>', self.evalFunction)
        funcs = ['replace']
        self.funcvar = StringVar()
        f = Combobox(ef, values=funcs,
                       textvariable=self.funcvar)
        f.pack(fill=BOTH,side=LEFT,expand=1,padx=2,pady=2)
        b = Button(ef,text='apply',width=5,command=apply)
        b.pack(fill=BOTH,side=LEFT,padx=2,pady=2)
        b = Button(ef,text='close',width=5,command=reset)
        b.pack(fill=BOTH,side=LEFT,padx=2,pady=2)

        return

    def evalBar(self, evt=None):
        """Use pd.eval to apply a function colwise or preset funcs."""

        def reset():
            self.evalframe.destroy()
            self.evalframe = None
            self.showAll()
        def clear():
            n = messagebox.askyesno("Clear formulae",
                                    "This will clear stored functions.\nProceed?",
                                    parent=self.parentframe)
            if n == None:
                return
            self.formulae = {}
            self.functionentry['values'] = []
            return
        def addcolname(evt):
            self.functionentry.insert(END,colvar.get())
            return

        self.estyle = Style()
        self.estyle.configure("White.TCombobox",
                         fieldbackground="white")
        self.estyle.configure("Red.TCombobox",
                         fieldbackground="#ffcccc")

        if hasattr(self, 'evalframe') and self.evalframe != None:
            return
        if not hasattr(self, 'formulae'):
            self.formulae = {}
        ef = self.evalframe = Frame(self.parentframe)
        ef.grid(row=self.queryrow,column=0,columnspan=3,sticky='news')
        bf = Frame(ef)
        bf.pack(side=TOP, fill=BOTH)
        self.evalvar = StringVar()
        funclist = ['='.join(i) for i in self.formulae.items()]
        self.functionentry = e = Combobox(bf, values=funclist,
                                    textvariable=self.evalvar,width=34,
                                    font="Courier 13 bold",
                                    style="White.TCombobox")
        e.bind('<Return>', self.evalFunction)
        e.pack(fill=BOTH,side=LEFT,expand=1,padx=2,pady=2)
        addButton(bf, 'apply', self.evalFunction, images.accept(), 'apply', side=LEFT)
        addButton(bf, 'preset', self.applyColumnWise, images.function(), 'preset function', side=LEFT)
        addButton(bf, 'clear', clear, images.delete(), 'clear stored functions', side=LEFT)
        addButton(bf, 'close', reset, images.cross(), 'close', side=LEFT)

        bf = Frame(ef)
        bf.pack(side=TOP, fill=BOTH)
        columns = list(self.model.df.columns)
        colvar = StringVar()
        Label(bf, text='insert column:').pack(side=LEFT,fill=BOTH)
        c = Combobox(bf, values=columns,textvariable=colvar,width=14)
        c.bind("<<ComboboxSelected>>", addcolname)
        c.pack(side=LEFT,fill=BOTH)

        self.updateplotvar = IntVar()
        self.placecolvar = IntVar()
        self.recalculatevar = IntVar()
        Checkbutton(bf, text="Update plot", variable=self.updateplotvar).pack(side=LEFT)
        Checkbutton(bf, text="Place new columns", variable=self.placecolvar).pack(side=LEFT)
        Checkbutton(bf, text="Recalculate all", variable=self.recalculatevar).pack(side=LEFT)
        return

    def resizeColumn(self, col, width):
        """Resize a column by dragging"""

        colname = self.model.getColumnName(col)
        self.model.columnwidths[colname] = width
        self.setColPositions()
        self.delete('colrect')
        #self.drawSelectedCol(self.currentcol)
        self.redraw()
        return

    def get_row_clicked(self, event):
        """Get row where event on canvas occurs"""

        h=self.rowheight
        #get coord on canvas, not window, need this if scrolling
        y = int(self.canvasy(event.y))
        y_start=self.y_start
        rowc = int((int(y)-y_start)/h)
        return rowc

    def get_col_clicked(self,event):
        """Get column where event on the canvas occurs"""

        w = self.cellwidth
        x = int(self.canvasx(event.x))
        x_start = self.x_start
        for colpos in self.col_positions:
            try:
                nextpos = self.col_positions[self.col_positions.index(colpos)+1]
            except:
                nextpos = self.tablewidth
            if x > colpos and x <= nextpos:
                #print 'x=', x, 'colpos', colpos, self.col_positions.index(colpos)
                return self.col_positions.index(colpos)
        return

    def setSelectedRow(self, row):
        """Set currently selected row and reset multiple row list"""

        self.currentrow = row
        self.multiplerowlist = []
        self.multiplerowlist.append(row)
        return

    def setSelectedCol(self, col):
        """Set currently selected column"""

        self.currentcol = col
        self.multiplecollist = []
        self.multiplecollist.append(col)
        return

    def setSelectedCells(self, startrow, endrow, startcol, endcol):
        """Set a block of cells selected"""

        self.currentrow = startrow
        self.currentcol = startcol
        if startrow < 0 or startcol < 0:
            return
        if endrow > self.rows or endcol > self.cols:
            return
        for r in range(startrow, endrow):
            self.multiplerowlist.append(r)
        for c in range(startcol, endcol):
            self.multiplecollist.append(c)
        return

    def getSelectedRow(self):
        """Get currently selected row"""
        return self.currentrow

    def getSelectedColumn(self):
        """Get currently selected column"""
        return self.currentcol

    def selectAll(self, evt=None):
        """Select all rows and cells"""

        self.startrow = 0
        self.endrow = self.rows
        self.multiplerowlist = list(range(self.startrow,self.endrow))
        self.drawMultipleRows(self.multiplerowlist)
        self.startcol = 0
        self.endcol = self.cols
        self.multiplecollist = list(range(self.startcol, self.endcol))
        self.drawMultipleCells()
        return

    def selectNone(self):
        """Deselect current, called when table is redrawn with
        completely new cols and rows e.g. after model is updated."""

        self.multiplecollist = []
        self.multiplerowlist = []
        self.startrow = self.endrow = 0
        self.delete('multicellrect','multiplesel','colrect')
        return

    def getCellCoords(self, row, col):
        """Get x-y coordinates to drawing a cell in a given row/col"""

        colname=self.model.getColumnName(col)
        if colname in self.model.columnwidths:
            w=self.model.columnwidths[colname]
        else:
            w=self.cellwidth
        h=self.rowheight
        x_start=self.x_start
        y_start=self.y_start

        #get nearest rect co-ords for that row/col
        x1=self.col_positions[col]
        y1=y_start+h*row
        x2=x1+w
        y2=y1+h
        return x1,y1,x2,y2

    def getCanvasPos(self, row, col):
        """Get the cell x-y coords as a fraction of canvas size"""

        if self.rows==0:
            return None, None
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        cx=float(x1)/self.tablewidth
        cy=float(y1)/(self.rows*self.rowheight)
        return cx, cy

    def isInsideTable(self,x,y):
        """Returns true if x-y coord is inside table bounds"""

        if self.x_start < x < self.tablewidth and self.y_start < y < self.rows*self.rowheight:
            return 1
        else:
            return 0
        return answer

    def setRowHeight(self, h):
        """Set the row height"""
        self.rowheight = h
        return

    def clearSelected(self):
        """Clear selections"""

        self.delete('rect')
        self.delete('entry')
        self.delete('tooltip')
        self.delete('searchrect')
        self.delete('colrect')
        self.delete('multicellrect')
        return

    def gotoprevRow(self):
        """Programmatically set previous row - eg. for button events"""

        self.clearSelected()
        current = self.getSelectedRow()
        self.setSelectedRow(current-1)
        self.startrow = current-1
        self.endrow = current-1
        #reset multiple selection list
        self.multiplerowlist=[]
        self.multiplerowlist.append(self.currentrow)
        self.drawSelectedRect(self.currentrow, self.currentcol)
        self.drawSelectedRow()
        coltype = self.model.getColumnType(self.currentcol)
        if coltype == 'text' or coltype == 'number':
            self.drawCellEntry(self.currentrow, self.currentcol)
        return

    def gotonextRow(self):
        """Programmatically set next row - eg. for button events"""

        self.clearSelected()
        current = self.getSelectedRow()
        self.setSelectedRow(current+1)
        self.startrow = current+1
        self.endrow = current+1
        #reset multiple selection list
        self.multiplerowlist=[]
        self.multiplerowlist.append(self.currentrow)
        self.drawSelectedRect(self.currentrow, self.currentcol)
        self.drawSelectedRow()
        coltype = self.model.getColumnType(self.currentcol)
        if coltype == 'text' or coltype == 'number':
            self.drawCellEntry(self.currentrow, self.currentcol)
        return

    def handle_left_click(self, event):
        """Respond to a single press"""

        self.clearSelected()
        self.allrows = False
        #which row and column is the click inside?
        rowclicked = self.get_row_clicked(event)
        colclicked = self.get_col_clicked(event)
        if colclicked == None:
            return
        self.focus_set()

        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()
        #ensure popup menus are removed if present
        if hasattr(self, 'rightmenu'):
            self.rightmenu.destroy()
        if hasattr(self.tablecolheader, 'rightmenu'):
            self.tablecolheader.rightmenu.destroy()

        self.startrow = rowclicked
        self.endrow = rowclicked
        self.startcol = colclicked
        self.endcol = colclicked
        #reset multiple selection list
        self.multiplerowlist=[]
        self.multiplerowlist.append(rowclicked)
        if 0 <= rowclicked < self.rows and 0 <= colclicked < self.cols:
            self.setSelectedRow(rowclicked)
            self.setSelectedCol(colclicked)
            self.drawSelectedRect(self.currentrow, self.currentcol)
            self.drawSelectedRow()
            self.rowheader.drawSelectedRows(rowclicked)
            self.tablecolheader.delete('rect')
        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()
        return

    def handle_left_release(self,event):
        self.endrow = self.get_row_clicked(event)
        return

    def handle_left_ctrl_click(self, event):
        """Handle ctrl clicks for multiple row selections"""

        rowclicked = self.get_row_clicked(event)
        colclicked = self.get_col_clicked(event)
        if 0 <= rowclicked < self.rows and 0 <= colclicked < self.cols:
            if rowclicked not in self.multiplerowlist:
                self.multiplerowlist.append(rowclicked)
            else:
                self.multiplerowlist.remove(rowclicked)
            self.drawMultipleRows(self.multiplerowlist)
            if colclicked not in self.multiplecollist:
                self.multiplecollist.append(colclicked)
            self.drawMultipleCells()
        return

    def handle_left_shift_click(self, event):
        """Handle shift click, for selecting multiple rows"""

        self.handle_mouse_drag(event)
        return

    def handle_mouse_drag(self, event):
        """Handle mouse moved with button held down, multiple selections"""

        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()
        rowover = self.get_row_clicked(event)
        colover = self.get_col_clicked(event)
        if colover == None or rowover == None:
            return

        if rowover >= self.rows or self.startrow > self.rows:
            return
        else:
            self.endrow = rowover
        #do columns
        if colover > self.cols or self.startcol > self.cols:
            return
        else:
            self.endcol = colover
            if self.endcol < self.startcol:
                self.multiplecollist=list(range(self.endcol, self.startcol+1))
            else:
                self.multiplecollist=list(range(self.startcol, self.endcol+1))
            #print self.multiplecollist
        #draw the selected rows
        if self.endrow != self.startrow:
            if self.endrow < self.startrow:
                self.multiplerowlist=list(range(self.endrow, self.startrow+1))
            else:
                self.multiplerowlist=list(range(self.startrow, self.endrow+1))
            self.drawMultipleRows(self.multiplerowlist)
            self.rowheader.drawSelectedRows(self.multiplerowlist)
            #draw selected cells outline using row and col lists
            self.drawMultipleCells()
        else:
            self.multiplerowlist = []
            self.multiplerowlist.append(self.currentrow)
            if len(self.multiplecollist) >= 1:
                self.drawMultipleCells()
            self.delete('multiplesel')
        return

    def handle_arrow_keys(self, event):
        """Handle arrow keys press"""
        #print event.keysym

        row = self.get_row_clicked(event)
        col = self.get_col_clicked(event)
        x,y = self.getCanvasPos(self.currentrow, 0)
        if x == None:
            return

        if event.keysym == 'Up':
            if self.currentrow == 0:
                return
            else:
                #self.yview('moveto', y)
                #self.rowheader.yview('moveto', y)
                self.currentrow  = self.currentrow -1
        elif event.keysym == 'Down':
            if self.currentrow >= self.rows-1:
                return
            else:
                #self.yview('moveto', y)
                #self.rowheader.yview('moveto', y)
                self.currentrow  = self.currentrow +1
        elif event.keysym == 'Right' or event.keysym == 'Tab':
            if self.currentcol >= self.cols-1:
                if self.currentrow < self.rows-1:
                    self.currentcol = 0
                    self.currentrow  = self.currentrow +1
                else:
                    return
            else:
                self.currentcol  = self.currentcol +1
        elif event.keysym == 'Left':
            self.currentcol  = self.currentcol -1
        self.drawSelectedRect(self.currentrow, self.currentcol)
        coltype = self.model.getColumnType(self.currentcol)
        #if coltype == 'text' or coltype == 'number':
        #    self.delete('entry')
        #    self.drawCellEntry(self.currentrow, self.currentcol)
        return

    def handle_double_click(self, event):
        """Do double click stuff. Selected row/cols will already have
           been set with single click binding"""

        row = self.get_row_clicked(event)
        col = self.get_col_clicked(event)
        self.drawCellEntry(self.currentrow, self.currentcol)
        return

    def handle_right_click(self, event):
        """respond to a right click"""

        self.delete('tooltip')
        self.rowheader.clearSelected()
        if hasattr(self, 'rightmenu'):
            self.rightmenu.destroy()
        rowclicked = self.get_row_clicked(event)
        colclicked = self.get_col_clicked(event)
        if colclicked == None:
            self.rightmenu = self.popupMenu(event, outside=1)
            return

        if (rowclicked in self.multiplerowlist or self.allrows == True) and colclicked in self.multiplecollist:
            self.rightmenu = self.popupMenu(event, rows=self.multiplerowlist, cols=self.multiplecollist)
        else:
            if 0 <= rowclicked < self.rows and 0 <= colclicked < self.cols:
                self.clearSelected()
                self.allrows = False
                self.setSelectedRow(rowclicked)
                self.setSelectedCol(colclicked)
                self.drawSelectedRect(self.currentrow, self.currentcol)
                self.drawSelectedRow()
            if self.isInsideTable(event.x,event.y) == 1:
                self.rightmenu = self.popupMenu(event,rows=self.multiplerowlist, cols=self.multiplecollist)
            else:
                self.rightmenu = self.popupMenu(event, outside=1)
        return

    def placeColumn(self, col1, col2):
        """Move col2 next to col1, useful for placing a new column
        made from the first one next to it so user can see it easily"""

        ind1 = self.model.df.columns.get_loc(col1)
        ind2 = self.model.df.columns.get_loc(col2)
        self.model.moveColumn(ind1, ind2+1)
        self.redraw()
        return

    def gotonextCell(self):
        """Move highlighted cell to next cell in row or a new col"""

        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()
        self.currentrow = self.currentrow+1
        #if self.currentcol >= self.cols-1:
        #    self.currentcol = self.currentcol+1
        self.drawSelectedRect(self.currentrow, self.currentcol)
        return

    def movetoSelectedRow(self, row=None, recname=None):
        """Move to selected row, updating table"""

        row=self.model.getRecordIndex(recname)
        self.setSelectedRow(row)
        self.drawSelectedRow()
        x,y = self.getCanvasPos(row, 0)
        self.yview('moveto', y-0.01)
        self.tablecolheader.yview('moveto', y)
        return

    def copyTable(self, event=None):
        """Copy from the clipboard"""

        df = self.model.df.copy()
        #flatten multi-index
        df.columns = df.columns.get_level_values(0)
        df.to_clipboard(sep=',')
        return

    def pasteTable(self, event=None):
        """Paste a new table from the clipboard"""

        self.storeCurrent()
        try:
            df = pd.read_clipboard(sep=',',error_bad_lines=False)
        except Exception as e:
            messagebox.showwarning("Could not read data", e,
                                    parent=self.parentframe)
            return
        if len(df) == 0:
            return
        df = pd.read_clipboard(sep=',', index_col=0, error_bad_lines=False)
        model = TableModel(df)
        self.updateModel(model)
        return

    def paste(self, event=None):
        """Paste selections - not implemented"""

        #df = pd.read_clipboard()
        return

    def copy(self, rows, cols=None):
        """Copy cell contents to clipboard"""

        data = self.getSelectedDataFrame()
        try:
            if len(data) == 1 and len(data.columns)==1:
                data.to_clipboard(index=False,header=False)
            else:
                data.to_clipboard()
        except:
            messagebox.showwarning("Warning",
                                   "No clipboard software.\nInstall xclip",
                                   parent=self.parentframe)
        return

    def transpose(self):
        """Transpose table"""

        self.model.transpose()
        self.updateModel(self.model)
        self.setSelectedRow(0)
        self.redraw()
        return

    def transform(self):
        """Apply element-wise transform"""

        df = self.model.df
        cols = list(df.columns[self.multiplecollist])
        rows = self.multiplerowlist
        funcs = ['log','exp','log10','log2',
                 'round','floor','ceil','trunc',
                 'subtract','divide','mod',
                 'negative','power',
                 'sin','cos','tan','degrees','radians']

        d = MultipleValDialog(title='Apply Function',
                                initialvalues=(funcs,1,False),
                                labels=('Function:','Constant:','Use Selected'),
                                types=('combobox','string','checkbutton'),
                                tooltips=(None,'value to apply with arithmetic operations',
                                          'apply to selected data only'),
                                parent = self.parentframe)
        if d.result == None:
            return
        self.storeCurrent()
        funcname = d.results[0]
        func = getattr(np, funcname)
        const = float(d.results[1])
        use_sel = float(d.results[2])

        if funcname in ['round']:
            const = int(const)

        if funcname in ['subtract','divide','mod','power','round']:
            if use_sel == True:
                df.ix[rows, cols] = df.ix[rows, cols].applymap(lambda x: func(x, const))
            else:
                df = df.applymap( lambda x: func(x, const))
        else:
            if use_sel == True:
                df.ix[rows, cols] = df.ix[rows, cols].applymap(func)
            else:
                df = df.applymap(func)

        self.model.df = df
        self.redraw()
        return

    def aggregate(self):
        """Show aggregate dialog"""

        df = self.model.df
        from .dialogs import AggregateDialog
        dlg = AggregateDialog(self, df=self.model.df)
        g = dlg.result
        if g is None:
            return
        replace = False
        #replace or make new table
        if replace == True:
            self.model.df = g
            self.showIndex()
            self.redraw()
        else:
            self.createChildTable(g, 'aggregated', index=True)
        return

    def melt(self):
        """Melt table"""

        df = self.model.df
        cols = list(df.columns)
        valcols = list(df.select_dtypes(include=[np.float64,np.int32]))
        d = MultipleValDialog(title='Melt',
                                initialvalues=(cols,valcols,'var'),
                                labels=('ID vars:', 'Value vars:', 'var name:'),
                                types=('combobox','listbox','entry'),
                                tooltips=('Column(s) to use as identifier variables',
                                          'Column(s) to unpivot',
                                          'name of variable column'),
                                parent = self.parentframe)
        idvars = d.results[0]
        valuevars = d.results[1]
        varname = d.results[2]
        if valuevars == '':
            valuevars = None
        elif len(valuevars) == 1:
            valuevars = valuevars[0]
        t = pd.melt(df, id_vars=idvars, value_vars=valuevars,
                 var_name=varname,value_name='value')
        #print(t)
        self.createChildTable(t, '', index=True)
        return

    def pivot(self):
        """Pivot table"""

        self.convertNumeric()
        df = self.model.df
        cols = list(df.columns)
        valcols = list(df.select_dtypes(include=[np.float64,np.int32]))
        funcs = ['mean','sum','count','max','min','std','first','last']
        d = MultipleValDialog(title='Pivot',
                                initialvalues=(cols,cols,valcols,funcs),
                                labels=('Index:', 'Column:', 'Values:','Agg Function:'),
                                types=('combobox','combobox','listbox','combobox'),
                                tooltips=('a unique index to reshape on','column with variables',
                                    'selecting no values uses all remaining cols',
                                    'function to aggregate on'),
                                parent = self.parentframe)
        if d.result == None:
            return
        index = d.results[0]
        column = d.results[1]
        values = d.results[2]
        func = d.results[3]
        if values == '': values = None
        elif len(values) == 1: values = values[0]

        p = pd.pivot_table(df, index=index, columns=column, values=values, aggfunc=func)
        print (p)
        if type(p) is pd.Series:
            p = pd.DataFrame(p)
        self.createChildTable(p, 'pivot-%s-%s' %(index,column), index=True)
        return

    def doCombine(self):
        """Do combine/merge operation"""

        if self.child == None:
            return
        self.storeCurrent()
        from .dialogs import CombineDialog
        cdlg = CombineDialog(self, df1=self.model.df, df2=self.child.model.df)
        #df = cdlg.merged
        #if df is None:
        #    return
        #model = TableModel(dataframe=df)
        #self.updateModel(model)
        #self.redraw()
        return

    def merge(self, table):
        """Merge with another table."""

        df1 = self.model.df
        df2 = table.model.df
        new = pd.merge(df1,df2,left_on=c1,right_on=c2,how=how)
        model = TableModel(new)
        self.updateModel(model)
        self.redraw()
        return

    def describe(self):
        """Create table summary"""

        g = self.model.df.describe()
        self.createChildTable(g)
        return

    def convertColumnNames(self, s='_'):
        """Convert col names so we can use numexpr"""

        d = MultipleValDialog(title='Convert col names',
                                initialvalues=['','','',0,0],
                                labels=['replace','with:',
                                        'add symbol to start:',
                                        'make lowercase','make uppercase'],
                                types=('string','string','string','checkbutton','checkbutton'),
                                parent = self.parentframe)
        if d.result == None:
            return
        pattern = d.results[0]
        repl = d.results[1]
        start = d.results[2]
        lower = d.results[3]
        upper = d.results[4]
        df = self.model.df
        if start != '':
            df.columns = start + df.columns
        if pattern != '':
            df.columns = [i.replace(pattern,repl) for i in df.columns]
        if lower == 1:
            df.columns = df.columns.str.lower()
        elif upper == 1:
            df.columns = df.columns.str.upper()
        self.redraw()
        self.tableChanged()
        return

    def convertNumeric(self):
        """Convert cols to numeric if possible"""

        df = self.model.df
        self.model.df = df.convert_objects(convert_numeric='force')
        self.redraw()
        return

    def corrMatrix(self):
        """Correlation matrix"""

        df = self.model.df
        corr = df.corr()
        self.createChildTable(corr)
        return

    def createChildTable(self, df, title=None, index=False, out=False):
        """Add the child table"""

        self.closeChildTable()
        if out == True:
            win = Toplevel()
            x,y,w,h = self.getGeometry(self.master)
            win.geometry('+%s+%s' %(int(x+w/2),int(y+h/2)))
            if title != None:
                win.title(title)
        else:
            win = Frame(self.parentframe)
            win.grid(row=self.childrow,column=0,columnspan=2,sticky='news')
        self.childframe = win
        newtable = self.__class__(win, dataframe=df, showtoolbar=0, showstatusbar=1)
        newtable.parenttable = self
        newtable.adjustColumnWidths()
        newtable.show()
        toolbar = ChildToolBar(win, newtable)
        toolbar.grid(row=0,column=3,rowspan=2,sticky='news')
        self.child = newtable
        if hasattr(self, 'pf'):
            newtable.pf = self.pf
        if index==True:
            newtable.showIndex()
        return

    def closeChildTable(self):
        """Close the child table"""

        if self.child != None:
            self.child.destroy()
        if hasattr(self, 'childframe'):
            self.childframe.destroy()
        return

    def tableFromSelection(self):
        """Create a new table from the selected cells"""

        df = self.getSelectedDataFrame()
        if len(df) <=1:
            df = pd.DataFrame()
        self.createChildTable(df, 'selection')
        return

    '''def pasteChildTable(self):
        """Paste child table back into main one"""

        answer =  messagebox.askyesno("Confirm",
                                "This will overwrite the main table.\n"+\
                                "Are you sure?",
                                parent=self.parentframe)
        if not answer:
            return
        table = self.parenttable
        model = TableModel(self.model.df)
        table.updateModel(model)
        return'''

    def showInfo(self):
        """Show dataframe info"""

        df = self.model.df
        import io
        buf = io.StringIO()
        df.info(verbose=True,buf=buf,memory_usage=True)
        from .dialogs import SimpleEditor
        w = Toplevel(self.parentframe)
        w.grab_set()
        w.transient(self)
        ed = SimpleEditor(w, height=25)
        ed.pack(in_=w, fill=BOTH, expand=Y)
        ed.text.insert(END, buf.getvalue())
        return

    def get_memory(self, ):
        """memory usage of current table"""

        df = self.model.df
        return df.memory_usage()

    def showasText(self):
        """Get table as formatted text - for printing"""

        d = MultipleValDialog(title='Table to Text',
                                initialvalues=(['left','right'],1,1,0,'',0,0),
                                labels=['justify:','header ','include index:',
                                        'sparsify:','na_rep:','max_cols','use selected'],
                                types=('combobox','checkbutton','checkbutton',
                                       'checkbutton','string','int','checkbutton'),
                                parent = self.parentframe)
        if d.result == None:
            return
        justify = d.results[0]
        header = d.results[1]
        index = d.results[2]
        sparsify = d.results[3]
        na_rep = d.results[4]
        max_cols = d.results[5]
        selected = d.results[6]

        if max_cols == 0:
            max_cols=None
        if selected == True:
            df = self.getSelectedDataFrame()
        else:
            df = self.model.df
        s = df.to_string(justify=justify,header=header,index=index,
                         sparsify=sparsify,na_rep=na_rep,max_cols=max_cols)
        #from tkinter.scrolledtext import ScrolledText
        from .dialogs import SimpleEditor
        w = Toplevel(self.parentframe)
        w.grab_set()
        w.transient(self)
        ed = SimpleEditor(w)
        ed.pack(in_=w, fill=BOTH, expand=Y)
        ed.text.insert(END, s)
        return

    # --- Some cell specific actions here ---

    def popupMenu(self, event, rows=None, cols=None, outside=None):
        """Add left and right click behaviour for canvas, should not have to override
            this function, it will take its values from defined dicts in constructor"""

        defaultactions = {
                        "Copy" : lambda: self.copy(rows, cols),
                        "Undo" : lambda: self.undo(),
                        #"Paste" : lambda: self.paste(rows, cols),
                        "Fill Down" : lambda: self.fillDown(rows, cols),
                        #"Fill Right" : lambda: self.fillAcross(cols, rows),
                        "Add Row(s)" : lambda: self.addRows(),
                        #"Delete Row(s)" : lambda: self.deleteRow(),
                        "Add Column(s)" : lambda: self.addColumn(),
                        "Delete Column(s)" : lambda: self.deleteColumn(),
                        "Clear Data" : lambda: self.deleteCells(rows, cols),
                        "Select All" : self.selectAll,
                        #"Auto Fit Columns" : self.autoResizeColumns,
                        "Table Info" : self.showInfo,
                        "Set Color" : self.setRowColors,
                        "Show as Text" : self.showasText,
                        "Filter Rows" : self.queryBar,
                        "New": self.new,
                        "Load": self.load,
                        "Save": self.save,
                        "Save as": self.saveAs,
                        "Import csv": lambda: self.importCSV(dialog=True),
                        "Export": self.doExport,
                        "Plot Selected" : self.plotSelected,
                        "Hide plot" : self.hidePlot,
                        "Show plot" : self.showPlot,
                        "Preferences" : self.showPrefs,
                        "Table to Text" : self.showasText,
                        "Clean Data" : self.cleanData,
                        "Clear Formatting" : self.clearFormatting}

        main = ["Copy", "Undo", "Fill Down", #"Fill Right",
                "Clear Data", "Set Color"]
        general = ["Select All", "Filter Rows",
                   "Show as Text", "Table Info", "Preferences"]

        filecommands = ['New','Load','Import csv','Save','Save as','Export']
        plotcommands = ['Plot Selected','Hide plot','Show plot']
        tablecommands = ['Table to Text','Clean Data','Clear Formatting']

        def createSubMenu(parent, label, commands):
            menu = Menu(parent, tearoff = 0)
            popupmenu.add_cascade(label=label,menu=menu)
            for action in commands:
                menu.add_command(label=action, command=defaultactions[action])
            applyStyle(menu)
            return menu

        def add_commands(fieldtype):
            """Add commands to popup menu for column type and specific cell"""
            functions = self.columnactions[fieldtype]
            for f in list(functions.keys()):
                func = getattr(self, functions[f])
                popupmenu.add_command(label=f, command= lambda : func(row,col))
            return

        popupmenu = Menu(self, tearoff = 0)
        def popupFocusOut(event):
            popupmenu.unpost()

        if outside == None:
            #if outside table, just show general items
            row = self.get_row_clicked(event)
            col = self.get_col_clicked(event)
            coltype = self.model.getColumnType(col)
            def add_defaultcommands():
                """now add general actions for all cells"""
                for action in main:
                    if action == 'Fill Down' and (rows == None or len(rows) <= 1):
                        continue
                    if action == 'Fill Right' and (cols == None or len(cols) <= 1):
                        continue
                    if action == 'Undo' and self.prevdf is None:
                        continue
                    else:
                        popupmenu.add_command(label=action, command=defaultactions[action])
                return

            if coltype in self.columnactions:
                add_commands(coltype)
            add_defaultcommands()

        for action in general:
            popupmenu.add_command(label=action, command=defaultactions[action])

        popupmenu.add_separator()
        createSubMenu(popupmenu, 'File', filecommands)
        createSubMenu(popupmenu, 'Plot', plotcommands)
        createSubMenu(popupmenu, 'Table', tablecommands)
        popupmenu.bind("<FocusOut>", popupFocusOut)
        popupmenu.focus_set()
        popupmenu.post(event.x_root, event.y_root)
        applyStyle(popupmenu)
        return popupmenu

    # --- spreadsheet type functions ---

    def fillDown(self, rowlist, collist):
        """Fill down a column, or multiple columns"""

        self.storeCurrent()
        df = self.model.df
        val = df.iloc[rowlist[0],collist[0]]
        #remove first element as we don't want to overwrite it
        rowlist.remove(rowlist[0])
        df.iloc[rowlist,collist] = val
        self.redraw()
        return

    def fillAcross(self, collist, rowlist):
        """Fill across a row, or multiple rows"""

        self.storeCurrent()
        model = self.model
        frstcol = collist[0]
        collist.remove(frstcol)
        self.redraw()
        return

    def getSelectionValues(self):
        """Get values for current multiple cell selection"""

        if len(self.multiplerowlist) == 0 or len(self.multiplecollist) == 0:
            return None
        rows = self.multiplerowlist
        cols = self.multiplecollist
        model = self.model
        if len(rows)<1 or len(cols)<1:
            return None
        #if only one row selected we plot whole col
        if len(rows) == 1:
            rows = self.rowrange
        lists = []

        for c in cols:
            x=[]
            for r in rows:
                #absr = self.get_AbsoluteRow(r)
                val = model.getValueAt(r,c)
                if val == None or val == '':
                    continue
                x.append(val)
            lists.append(x)
        return lists

    def showPlotViewer(self, parent=None, layout='horizontal'):
        """Create plot frame"""

        if not hasattr(self, 'pf'):
            self.pf = PlotViewer(table=self, parent=parent, layout=layout)
        if hasattr(self, 'child') and self.child is not None:
            self.child.pf = self.pf
        return self.pf

    def hidePlot(self):
        """Hide plot frame"""

        if hasattr(self, 'pf'):
            self.pf.hide()
            #self.pf = None
        return

    def showPlot(self):
        if hasattr(self, 'pf'):
            self.pf.show()
        return

    def getSelectedDataFrame(self):
        """Return a sub-dataframe of the selected cells"""

        df = self.model.df
        rows = self.multiplerowlist
        if not type(rows) is list:
            rows = list(rows)
        if len(rows)<1 or self.allrows == True:
            rows = list(range(self.rows))
        cols = self.multiplecollist
        try:
            data = df.iloc[list(rows),cols]
        except Exception as e:
            print ('error indexing data')
            return pd.DataFrame()
        return data

    def getPlotData(self):
        """Plot data from selection"""

        data = self.getSelectedDataFrame()
        #data = data.convert_objects(convert_numeric='force')
        return data

    def plotSelected(self):
        """Plot the selected data in the associated plotviewer"""

        if not hasattr(self, 'pf') or self.pf == None:
            self.pf = PlotViewer(table=self)
        else:
            if type(self.pf.main) is Toplevel:
                self.pf.main.deiconify()
        #plot could be hidden
        self.showPlot()
        #data = self.getPlotData()
        #self.pf.data = data
        self.pf.table = self
        self.pf.replot() #calls getPlotData on the table
        if hasattr(self, 'parenttable'):
            self.parenttable.plotted = 'child'
        else:
            self.plotted = 'main'
        return

    def plot3D(self):

        if not hasattr(self, 'pf'):
            self.pf = PlotViewer(table=self)

        data = self.getPlotData()
        self.pf.data = data
        self.pf.plot3D()
        return

    #--- Drawing stuff ---

    def drawGrid(self, startrow, endrow):
        """Draw the table grid lines"""
        self.delete('gridline','text')
        rows=len(self.rowrange)
        cols=self.cols
        w = self.cellwidth
        h = self.rowheight
        x_start=self.x_start
        y_start=self.y_start
        x_pos=x_start

        if self.vertlines==1:
            for col in range(cols+1):
                x=self.col_positions[col]
                self.create_line(x,y_start,x,y_start+rows*h, tag='gridline',
                                     fill=self.grid_color, width=self.linewidth)
        if self.horizlines==1:
            for row in range(startrow, endrow+1):
                y_pos=y_start+row*h
                self.create_line(x_start,y_pos,self.tablewidth,y_pos, tag='gridline',
                                    fill=self.grid_color, width=self.linewidth)
        return

    def drawRowHeader(self):
        """User has clicked to select a cell"""

        self.delete('rowheader')
        x_start=self.x_start
        y_start=self.y_start
        h=self.rowheight
        rowpos=0
        for row in self.rowrange:
            x1,y1,x2,y2 = self.getCellCoords(rowpos,0)
            self.create_rectangle(0,y1,x_start-2,y2,
                                      fill='gray75',
                                      outline='white',
                                      width=1,
                                      tag='rowheader')
            self.create_text(x_start/2,y1+h/2,
                                      text=row+1,
                                      fill='black',
                                      font=self.thefont,
                                      tag='rowheader')
            rowpos+=1
        return

    def drawSelectedRect(self, row, col, color=None):
        """User has clicked to select a cell"""

        if col >= self.cols:
            return
        self.delete('currentrect')
        #bg = self.selectedcolor
        if color == None:
            color = 'gray25'
        w=2
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        rect = self.create_rectangle(x1+w/2+1,y1+w/2+1,x2-w/2,y2-w/2,
                                  outline=color,
                                  width=w,
                                  tag='currentrect')
        #raise text above all
        self.lift('celltext'+str(col)+'_'+str(row))
        return

    def drawRect(self, row, col, color=None, tag=None, delete=1):
        """Cell is colored"""

        if delete==1:
            self.delete('cellbg'+str(row)+str(col))
        if color==None or color==self.cellbackgr:
            return
        else:
            bg=color
        if tag==None:
            recttag='fillrect'
        else:
            recttag=tag
        w=1
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        rect = self.create_rectangle(x1+w/2,y1+w/2,x2-w/2,y2-w/2,
                                  fill=bg,
                                  outline=bg,
                                  width=w,
                                  tag=(recttag,'cellbg'+str(row)+str(col)))
        self.lower(recttag)
        return

    def handleCellEntry(self, row, col):
        """Callback for cell entry"""

        value = self.cellentryvar.get()
        self.model.setValueAt(value,row,col)
        self.drawText(row, col, value, align=self.align)
        self.delete('entry')
        self.gotonextCell()
        return

    def drawCellEntry(self, row, col, text=None):
        """When the user single/double clicks on a text/number cell,
          bring up entry window and allow edits."""

        if self.editable == False:
            return
        h = self.rowheight
        model = self.model
        text = self.model.getValueAt(row, col)
        if pd.isnull(text):
            text = ''
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        w=x2-x1
        self.cellentryvar = txtvar = StringVar()
        txtvar.set(text)

        self.cellentry = Entry(self.parentframe,width=20,
                        textvariable=txtvar,
                        takefocus=1,
                        font=self.thefont)
        self.cellentry.icursor(END)
        self.cellentry.bind('<Return>', lambda x: self.handleCellEntry(row,col))
        self.cellentry.focus_set()
        self.entrywin = self.create_window(x1,y1,
                                width=w,height=h,
                                window=self.cellentry,anchor='nw',
                                tag='entry')
        return

    def checkDataEntry(self,event=None):
        """do validation checks on data entry in a widget"""

        value=event.widget.get()
        if value!='':
            try:
                value=re.sub(',','.', value)
                value=float(value)
            except ValueError:
                event.widget.configure(bg='red')
                return 0
        elif value == '':
            return 1
        return 1

    def drawText(self, row, col, celltxt, align=None):
        """Draw the text inside a cell area"""

        self.delete('celltext'+str(col)+'_'+str(row))
        h = self.rowheight
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        w=x2-x1
        wrap = False
        pad=5
        #if type(celltxt) is np.float64:
        #    celltxt = np.round(celltxt,3)
        celltxt = str(celltxt)
        length = len(celltxt)
        if length == 0:
            return

        if w<=10:
            return
        if w < 18:
            celltxt = '.'
            return

        fgcolor = 'black'
        if align == None:
            align = 'center'
        elif align == 'w':
            x1 = x1-w/2+pad
        elif align == 'e':
            x1 = x1+w/2-pad

        tw,newlength = util.getTextLength(celltxt, w-pad, font=self.thefont)
        width=0
        celltxt = celltxt[0:int(newlength)]
        y=y1+h/2
        rect = self.create_text(x1+w/2,y,
                                  text=celltxt,
                                  fill=fgcolor,
                                  font=self.thefont,
                                  anchor=align,
                                  tag=('text','celltext'+str(col)+'_'+str(row)),
                                  width=width)
        return

    def drawSelectedRow(self):
        """Draw a highlight rect for the currently selected rows"""

        self.delete('rowrect')
        row = self.currentrow
        x1,y1,x2,y2 = self.getCellCoords(row,0)
        x2 = self.tablewidth
        rect = self.create_rectangle(x1,y1,x2,y2,
                                  fill=self.rowselectedcolor,
                                  outline=self.rowselectedcolor,
                                  tag='rowrect')
        self.lower('rowrect')
        self.lower('fillrect')
        self.lower('colorrect')
        self.rowheader.drawSelectedRows(self.currentrow)
        return

    def drawSelectedCol(self, col=None, delete=1, color=None, tag='colrect'):
        """Draw a highlight rect for the current column selection"""

        if color == None:
            color = self.colselectedcolor
        if delete == 1:
            self.delete(tag)
        if len(self.model.df.columns) == 0:
            return
        if col == None:
            col = self.currentcol
        w=2
        x1,y1,x2,y2 = self.getCellCoords(0,col)
        y2 = self.rows * self.rowheight
        rect = self.create_rectangle(x1+w/2,y1+w/2,x2,y2+w/2,
                                     width=w,fill=color,outline='',
                                     tag=tag)
        self.lower('rowrect')
        self.lower('colrect')
        return

    def drawMultipleRows(self, rowlist):
        """Draw more than one row selection"""

        self.delete('multiplesel')
        self.delete('rowrect')
        cols = self.visiblecols
        for col in cols:
            colname = self.model.df.columns[col]
            #if col is colored we darken it
            if colname in self.columncolors:
                clr = self.columncolors[colname]
                clr = util.colorScale(clr, -30)
            else:
                clr = self.rowselectedcolor
            for r in rowlist:
                if r not in self.visiblerows or r > self.rows-1:
                    continue
                x1,y1,x2,y2 = self.getCellCoords(r,col)
                #x2 = self.tablewidth
                rect = self.create_rectangle(x1,y1,x2,y2,
                                          fill=clr,
                                          outline=self.rowselectedcolor,
                                          tag=('multiplesel','rowrect'))

        self.lower('multiplesel')
        self.lower('fillrect')
        self.lower('colorrect')
        return

    def drawMultipleCols(self):
        """Draw multiple column selections"""

        for c in self.multiplecollist:
            self.drawSelectedCol(c, delete=False)
        return

    def drawMultipleCells(self):
        """Draw an outline box for multiple cell selection"""

        self.delete('currentrect')
        self.delete('multicellrect')
        rows = self.multiplerowlist
        cols = self.multiplecollist
        if len(rows) == 0 or len(cols) == 0:
            return
        w=2
        x1,y1,a,b = self.getCellCoords(rows[0],cols[0])
        c,d,x2,y2 = self.getCellCoords(rows[len(rows)-1],cols[len(cols)-1])
        rect = self.create_rectangle(x1+w/2,y1+w/2,x2,y2,
                             outline=self.boxoutlinecolor, width=w,
                             tag='multicellrect')
        return

    def setcellbackgr(self):
        clr = self.getaColor(self.cellbackgr)
        if clr != None:
            self.cellbackgr = clr
        return

    def setgrid_color(self):
        clr = self.getaColor(self.grid_color)
        if clr != None:
            self.grid_color = clr
        return

    def setrowselectedcolor(self):
        """Set selected row color"""

        clr = self.getaColor(self.rowselectedcolor)
        if clr != None:
            self.rowselectedcolor = clr
        return

    def getaColor(self, oldcolor):

        import tkinter.colorchooser
        ctuple, newcolor = tkinter.colorchooser.askcolor(title='pick a color',
                                                         initialcolor=oldcolor,
                                                         parent=self.parentframe)
        if ctuple == None:
            return None
        return str(newcolor)

    #--- Preferences stuff ---

    def showPrefs(self, prefs=None):
        """Show table options dialog using an instance of prefs"""

        if self.prefs == None:
            self.loadPrefs()
        self.prefswindow=Toplevel()
        x,y,w,h = self.getGeometry(self.master)
        #self.prefswindow.geometry('+%s+%s' %(x+w/2,y+h/2))
        self.prefswindow.title('Preferences')
        self.prefswindow.resizable(width=FALSE, height=FALSE)
        self.prefswindow.grab_set()
        self.prefswindow.transient(self)

        frame1=Frame(self.prefswindow)
        frame1.pack(side=LEFT)
        frame2=Frame(self.prefswindow)
        frame2.pack()
        def close_prefsdialog():
            self.prefswindow.destroy()
        row=0
        Checkbutton(frame1, text="Show horizontal lines", variable=self.horizlinesvar,
                    onvalue=1, offvalue=0).grid(row=row,column=0, columnspan=2, sticky='news')
        row=row+1
        Checkbutton(frame1, text="Show vertical lines", variable=self.vertlinesvar,
                    onvalue=1, offvalue=0).grid(row=row,column=0, columnspan=2, sticky='news')
        row=row+1
        Checkbutton(frame1, text="Auto resize columns", variable=self.autoresizecolsvar,
                    onvalue=1, offvalue=0).grid(row=row,column=0, columnspan=2, sticky='news')
        row=row+1
        lblrowheight = Label(frame1,text='Row Height:')
        lblrowheight.grid(row=row,column=0,padx=3,pady=2)
        rowheightentry = Scale(frame1,from_=12,to=50,resolution=1,orient='horizontal',
                            variable=self.rowheightvar)
        rowheightentry.configure(fg='black', bg=self.bg)
        rowheightentry.grid(row=row,column=1)
        row=row+1
        lblcellwidth = Label(frame1,text='Cell Width:')
        lblcellwidth.grid(row=row,column=0,padx=3,pady=2)
        cellwidthentry = Scale(frame1,from_=20,to=500,resolution=10,orient='horizontal',
                            variable=self.cellwidthvar)
        cellwidthentry.configure(fg='black', bg=self.bg)
        cellwidthentry.grid(row=row,column=1)
        row=row+1

        lbllinewidth = Label(frame1,text='Line Width:')
        lbllinewidth.grid(row=row,column=0,padx=3,pady=2)
        linewidthentry = Scale(frame1,from_=0,to=10,resolution=1,orient='horizontal',
                            variable=self.linewidthvar)
        linewidthentry.configure(fg='black', bg=self.bg)
        linewidthentry.grid(row=row,column=1)
        row=row+1

        rowhdrwidth=Label(frame1,text='Row Header Width:')
        rowhdrwidth.grid(row=row,column=0,padx=3,pady=2)
        rowhdrentry = Scale(frame1,from_=0,to=300,resolution=10,orient='horizontal',
                                    variable=self.rowheaderwidthvar)
        rowhdrentry.configure(fg='black', bg=self.bg)
        rowhdrentry.grid(row=row,column=1)
        row=row+1

        #fonts
        fts = self.getFonts()
        Label(frame2,text='font').grid(row=row,column=0)
        fb = Combobox(frame2, values=fts,
                       textvariable=self.fontvar)
        #currfont = self.prefs.get('celltextfont')
        fb.grid(row=row,column=1, columnspan=2, sticky='nes', padx=3,pady=2)
        row=row+1

        lblfontsize = Label(frame2,text='Text Size:')
        lblfontsize.grid(row=row,column=0,padx=3,pady=2)
        fontsizeentry = Scale(frame2,from_=6,to=50,resolution=1,orient='horizontal',
                                variable=self.celltextsizevar)
        fontsizeentry.configure(fg='black', bg=self.bg)
        fontsizeentry.grid(row=row,column=1, sticky='wens',padx=3,pady=2)
        row=row+1

        #cell alignment
        lbl=Label(frame2,text='Alignment:')
        lbl.grid(row=row,column=0,padx=3,pady=2)

        alignments=['center','w','e']
        alignentry_button = Combobox(frame2, values=alignments,
                              textvariable=self.cellalignvar)
        alignentry_button.grid(row=row,column=1, sticky='nes', padx=3,pady=2)
        row=row+1

        #float precision
        lbl=Label(frame2,text='Float precision:')
        lbl.grid(row=row,column=0,padx=3,pady=2)
        fpentry = Entry(frame2, textvariable=self.floatprecvar, width=10)
        fpentry.grid(row=row,column=1, sticky='nes', padx=3,pady=2)
        row=row+1

        #colors
        style = Style()
        style.configure("cb.TButton", background=self.cellbackgr)
        cellbackgrbutton = Button(frame2, text='table background',style="cb.TButton",
                                  command=self.setcellbackgr)

        cellbackgrbutton.grid(row=row,column=0,columnspan=2, sticky='news')
        row=row+1
        style = Style()
        style.configure("gc.TButton", background=self.grid_color)
        grid_colorbutton = Button(frame2, text='grid color', style="gc.TButton",
                                command=self.setgrid_color)
        grid_colorbutton.grid(row=row,column=0,columnspan=2, sticky='news')
        row=row+1
        style = Style()
        style.configure("rhc.TButton", background=self.rowselectedcolor)
        rowselectedcolorbutton = Button(frame2, text='row highlight color', style="rhc.TButton",
                                command=self.setrowselectedcolor)
        rowselectedcolorbutton.grid(row=row,column=0,columnspan=2, sticky='news')
        row=row+1

        frame=Frame(self.prefswindow)
        frame.pack(fill=BOTH,expand=1)
        # Apply Button
        b = Button(frame, text="Apply Settings", command=self.applyPrefs)
        b.pack(side=LEFT,expand=1)

        # Close button
        c=Button(frame,text='Close', command=close_prefsdialog)
        c.pack(side=LEFT,expand=1)
        self.prefswindow.focus_set()
        self.prefswindow.grab_set()
        self.prefswindow.wait_window()
        return self.prefswindow

    def getFonts(self):

        fonts = set(list(font.families()))
        fonts = sorted(list(fonts))
        return fonts

    def loadPrefs(self, prefs=None):
        """Load table specific prefs from the prefs instance used
           if they are not present, create them."""

        if prefs==None:
            prefs=Preferences('Table',{'check_for_update':1})
        self.prefs = prefs
        defaultprefs = {'horizlines':self.horizlines, 'vertlines':self.vertlines,
                        'rowheight':self.rowheight,
                        'cellwidth':80,
                        'autoresizecols': self.autoresizecols,
                        'align': 'w',
                        'floatprecision': self.floatprecision,
                        'celltextsize':10, 'celltextfont':'Arial',
                        'cellbackgr': self.cellbackgr, 'grid_color': self.grid_color,
                        'linewidth' : self.linewidth,
                        'rowselectedcolor': self.rowselectedcolor,
                        'rowheaderwidth': self.rowheaderwidth}

        for prop in list(defaultprefs.keys()):
            try:
                self.prefs.get(prop);
            except:
                self.prefs.set(prop, defaultprefs[prop])
        self.defaultprefs = defaultprefs

        #Create tkvars for dialog
        self.fontvar = StringVar()
        self.fontvar.set(self.prefs.get('celltextfont'))
        self.rowheightvar = IntVar()
        self.rowheightvar.set(self.prefs.get('rowheight'))
        self.rowheight = self.rowheightvar.get()
        self.cellwidthvar = IntVar()
        self.cellwidthvar.set(self.prefs.get('cellwidth'))
        self.cellwidth = self.cellwidthvar.get()
        self.cellalignvar = StringVar()
        self.cellalignvar.set(self.prefs.get('align'))
        self.align = self.cellalignvar.get()
        self.floatprecvar = IntVar()
        self.floatprecvar.set(self.prefs.get('floatprecision'))
        self.linewidthvar = StringVar()
        self.linewidthvar.set(self.prefs.get('linewidth'))
        self.horizlinesvar = IntVar()
        self.horizlinesvar.set(self.prefs.get('horizlines'))
        self.vertlinesvar = IntVar()
        self.vertlinesvar.set(self.prefs.get('vertlines'))
        self.autoresizecolsvar = IntVar()
        self.autoresizecolsvar.set(self.prefs.get('autoresizecols'))
        self.celltextsizevar = IntVar()
        self.celltextsizevar.set(self.prefs.get('celltextsize'))
        self.cellbackgr = self.prefs.get('cellbackgr')
        self.grid_color = self.prefs.get('grid_color')
        self.rowselectedcolor = self.prefs.get('rowselectedcolor')
        self.fontsize = self.celltextsizevar.get()
        self.thefont = (self.prefs.get('celltextfont'), self.prefs.get('celltextsize'))
        self.rowheaderwidthvar = IntVar()
        self.rowheaderwidthvar.set(self.prefs.get('rowheaderwidth'))
        self.rowheaderwidth = self.rowheaderwidthvar.get()
        return

    def savePrefs(self):
        """Save and set the prefs"""
        try:
            self.prefs.set('horizlines', self.horizlinesvar.get())
            self.horizlines = self.horizlinesvar.get()
            self.prefs.set('vertlines', self.vertlinesvar.get())
            self.vertlines = self.vertlinesvar.get()
            self.prefs.set('autoresizecols', self.autoresizecolsvar.get())
            self.autoresizecols = self.autoresizecolsvar.get()
            self.prefs.set('rowheight', self.rowheightvar.get())
            self.rowheight = self.rowheightvar.get()
            self.prefs.set('cellwidth', self.cellwidthvar.get())
            self.cellwidth = self.cellwidthvar.get()
            self.prefs.set('align', self.cellalignvar.get())
            self.align = self.cellalignvar.get()
            self.floatprecision = self.floatprecvar.get()
            self.prefs.set('floatprecision', self.floatprecvar.get())
            self.prefs.set('linewidth', self.linewidthvar.get())
            self.linewidth = self.linewidthvar.get()
            self.prefs.set('celltextsize', self.celltextsizevar.get())
            self.prefs.set('celltextfont', self.fontvar.get())
            self.prefs.set('cellbackgr', self.cellbackgr)
            self.prefs.set('grid_color', self.grid_color)
            self.prefs.set('rowselectedcolor', self.rowselectedcolor)
            self.prefs.set('rowheaderwidth', self.rowheaderwidth)
            self.rowheaderwidth = self.rowheaderwidthvar.get()
            self.thefont = (self.prefs.get('celltextfont'), self.prefs.get('celltextsize'))
            self.fontsize = self.prefs.get('celltextsize')

        except ValueError:
            pass
        self.prefs.save_prefs()
        return

    def applyPrefs(self):
        """Apply prefs to the table by redrawing"""

        self.savePrefs()
        self.autoResizeColumns()
        #self.show()
        self.redraw()
        return

    def show_progressbar(self,message=None):
        """Show progress bar window for loading of data"""

        progress_win=Toplevel() # Open a new window
        progress_win.title("Please Wait")
        #progress_win.geometry('+%d+%d' %(self.parentframe.rootx+200,self.parentframe.rooty+200))
        #force on top
        progress_win.grab_set()
        progress_win.transient(self.parentframe)
        if message==None:
            message='Working'
        lbl = Label(progress_win,text=message,font='Arial 16')

        lbl.grid(row=0,column=0,columnspan=2,sticky='news',padx=6,pady=4)
        progrlbl = Label(progress_win,text='Progress:')
        progrlbl.grid(row=1,column=0,sticky='news',padx=2,pady=4)
        import ProgressBar
        self.bar = ProgressBar.ProgressBar(progress_win)
        self.bar.frame.grid(row=1,column=1,columnspan=2,padx=2,pady=4)

        return progress_win

    def updateModel(self, model):
        """Should call this method when a new table model is loaded.
           Recreates widghets and redraws the table."""

        self.model = model
        self.rows = self.model.getRowCount()
        self.cols = self.model.getColumnCount()
        self.tablewidth = (self.cellwidth)*self.cols
        if hasattr(self, 'tablecolheader'):
            self.tablecolheader.destroy()
            self.rowheader.destroy()
            self.selectNone()
        self.show()
        return

    def new(self):
        """Clears all the data and makes a new table"""

        mpDlg = MultipleValDialog(title='Create new table',
                                    initialvalues=(50, 10),
                                    labels=('rows','columns'),
                                    types=('int','int'),
                                    parent=self.parentframe)
        if mpDlg.result == True:
            rows = mpDlg.results[0]
            cols = mpDlg.results[1]
            model = TableModel(rows=rows,columns=cols)
            self.updateModel(model)
        return

    def load(self, filename=None):
        """load from a file"""
        if filename == None:
            filename = filedialog.askopenfilename(parent=self.master,
                                                      defaultextension='.mpk',
                                                      initialdir=os.getcwd(),
                                                      filetypes=[("msgpack","*.mpk"),
                                                                 ("pickle","*.pickle"),
                                                        ("All files","*.*")])
        if not os.path.exists(filename):
            print('file does not exist')
            return
        if filename:
            filetype = os.path.splitext(filename)[1]
            model = TableModel()
            model.load(filename, filetype)
            self.updateModel(model)
            self.filename = filename
            self.adjustColumnWidths()
            self.redraw()
        return

    def saveAs(self, filename=None):
        """Save dataframe to file"""

        if filename == None:
            filename = filedialog.asksaveasfilename(parent=self.master,
                                                     #defaultextension='.mpk',
                                                     initialdir = self.currentdir,
                                                     filetypes=[("msgpack","*.mpk"),
                                                                ("pickle","*.pickle"),
                                                                ("All files","*.*")])
        if filename:
            self.model.save(filename)
            self.filename = filename
            self.currentdir = os.path.basename(filename)
        return

    def save(self):
        """Save current file"""

        self.saveAs(self.filename)
        return

    def importCSV(self, filename=None, dialog=False, **kwargs):
        """Import from csv file"""

        if self.importpath == None:
            self.importpath = os.getcwd()
        if filename == None:
            filename = filedialog.askopenfilename(parent=self.master,
                                                          defaultextension='.csv',
                                                          initialdir=self.importpath,
                                                          filetypes=[("csv","*.csv"),
                                                                     ("tsv","*.tsv"),
                                                                     ("txt","*.txt"),
                                                            ("All files","*.*")])
        if not filename:
            return
        if dialog == True:
            impdialog = ImportDialog(self, filename=filename)
            df = impdialog.df
            if df is None:
                return
        else:
            df = pd.read_csv(filename, **kwargs)
        model = TableModel(dataframe=df)
        self.updateModel(model)
        self.redraw()
        self.importpath = os.path.dirname(filename)
        return

    def loadExcel(self, filename=None):
        """Load excel file"""

        if filename == None:
            filename = filedialog.askopenfilename(parent=self.master,
                                                          defaultextension='.xls',
                                                          initialdir=os.getcwd(),
                                                          filetypes=[("xls","*.xls"),
                                                                     ("xlsx","*.xlsx"),
                                                            ("All files","*.*")])
        if not filename:
            return

        df = pd.read_excel(filename,sheetname=0)
        model = TableModel(dataframe=df)
        self.updateModel(model)
        return

    def doExport(self, filename=None):
        """Do a simple export of the cell contents to csv"""

        if filename == None:
            filename = filedialog.asksaveasfilename(parent=self.master,
                                                      defaultextension='.csv',
                                                      initialdir = os.getcwd(),
                                                      filetypes=[("csv","*.csv"),
                                                           ("excel","*.xls"),
                                                           ("html","*.html"),
                                                        ("All files","*.*")])
        if filename:
            self.model.save(filename)
        return

    def getGeometry(self, frame):
        """Get frame geometry"""
        return frame.winfo_rootx(), frame.winfo_rooty(), frame.winfo_width(), frame.winfo_height()

    def clearFormatting(self):
        self.set_defaults()
        self.columncolors = {}
        self.rowcolors = pd.DataFrame()
        return

class ToolBar(Frame):
    """Uses the parent instance to provide the functions"""
    def __init__(self, parent=None, parentapp=None):

        Frame.__init__(self, parent, width=600, height=40)
        self.parentframe = parent
        self.parentapp = parentapp
        img = images.open_proj()
        addButton(self, 'Load table', self.parentapp.load, img, 'load table')
        img = images.save_proj()
        addButton(self, 'Save', self.parentapp.save, img, 'save')
        img = images.importcsv()
        func = lambda: self.parentapp.importCSV(dialog=1)
        addButton(self, 'Import', func, img, 'import csv')
        img = images.excel()
        addButton(self, 'Load excel', self.parentapp.loadExcel, img, 'load excel file')
        img = images.copy()
        addButton(self, 'Copy', self.parentapp.copyTable, img, 'copy table to clipboard')
        img = images.paste()
        addButton(self, 'Paste', self.parentapp.pasteTable, img, 'paste table')
        img = images.plot()
        addButton(self, 'Plot', self.parentapp.plotSelected, img, 'plot selected')
        img = images.transpose()
        addButton(self, 'Transpose', self.parentapp.transpose, img, 'transpose')
        img = images.aggregate()
        addButton(self, 'Aggregate', self.parentapp.aggregate, img, 'aggregate')
        img = images.pivot()
        addButton(self, 'Pivot', self.parentapp.pivot, img, 'pivot')
        img = images.melt()
        addButton(self, 'Melt', self.parentapp.melt, img, 'melt')
        img = images.merge()
        addButton(self, 'Merge', self.parentapp.doCombine, img, 'merge, concat or join')
        img = images.table_multiple()
        addButton(self, 'Table from selection', self.parentapp.tableFromSelection,
                    img, 'sub-table from selection')
        img = images.filtering()
        addButton(self, 'Query', self.parentapp.queryBar, img, 'filter table')
        img = images.calculate()
        addButton(self, 'Evaluate function', self.parentapp.evalBar, img, 'calculate')
        img = images.fit()
        addButton(self, 'Stats models', self.parentapp.statsViewer, img, 'model fitting')

        img = images.table_delete()
        addButton(self, 'Clear', self.parentapp.clearTable, img, 'clear table')
        #img = images.prefs()
        #addButton(self, 'Prefs', self.parentapp.showPrefs, img, 'table preferences')
        return

class ChildToolBar(ToolBar):
    """Smaller toolbar for child table"""
    def __init__(self, parent=None, parentapp=None):
        Frame.__init__(self, parent, width=600, height=40)
        self.parentframe = parent
        self.parentapp = parentapp
        img = images.open_proj()
        addButton(self, 'Load table', self.parentapp.load, img, 'load table')
        img = images.importcsv()
        func = lambda: self.parentapp.importCSV(dialog=1)
        addButton(self, 'Import', func, img, 'import csv')
        img = images.plot()
        addButton(self, 'Plot', self.parentapp.plotSelected, img, 'plot selected')
        img = images.transpose()
        addButton(self, 'Transpose', self.parentapp.transpose, img, 'transpose')
        img = images.copy()
        addButton(self, 'Copy', self.parentapp.copyTable, img, 'copy to clipboard')
        img = images.paste()
        addButton(self, 'Paste', self.parentapp.pasteTable, img, 'paste table')
        img = images.table_delete()
        addButton(self, 'Clear', self.parentapp.clearTable, img, 'clear table')
        img = images.cross()
        addButton(self, 'Close', self.parentapp.remove, img, 'close')
        return

class statusBar(Frame):
    """Status bar class"""
    def __init__(self, parent=None, parentapp=None):

        Frame.__init__(self, parent)
        self.parentframe = parent
        self.parentapp = parentapp
        sfont = ("Helvetica bold", 10)
        clr = '#A10000'
        self.rowsvar = StringVar()
        l=Label(self,textvariable=self.rowsvar,font=sfont,foreground=clr)
        l.pack(fill=X, side=LEFT)
        Label(self,text='rows x',font=sfont,foreground=clr).pack(side=LEFT)
        self.colsvar = StringVar()
        self.colsvar.set(len(self.parentapp.model.df))
        l=Label(self,textvariable=self.colsvar,font=sfont,foreground=clr)
        l.pack(fill=X, side=LEFT)
        Label(self,text='columns',font=sfont,foreground=clr).pack(side=LEFT)
        self.filenamevar = StringVar()
        l=Label(self,textvariable=self.filenamevar,font=sfont)
        l.pack(fill=X, side=RIGHT)
        return

    def update(self):
        """Update status bar"""

        model = self.parentapp.model
        self.rowsvar.set(len(model.df))
        self.colsvar.set(len(model.df.columns))
        if self.parentapp.filename != None:
            self.filenamevar.set(self.parentapp.filename)
        return
