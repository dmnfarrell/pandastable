#!/usr/bin/env python
"""
    Implements the pandastable headers classes.
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

from tkinter import *
from tkinter.ttk import *
import math, time
import os, types, string
import numpy as np
import pandas as pd
from . import util

class ColumnHeader(Canvas):
    """Class that takes it's size and rendering from a parent table
        and column names from the table model."""

    def __init__(self, parent=None, table=None):
        Canvas.__init__(self, parent, bg='gray25', width=500, height=40)
        self.thefont='Arial 14'
        if table != None:
            self.table = table
            self.model = self.table.model
            if util.check_multiindex(self.model.df.columns) == 1:
                self.height = 40
            else:
                self.height = 20
            self.config(width=self.table.width, height=self.height)
            self.columnlabels = self.model.df.columns
            self.draggedcol = None
            self.bind('<Button-1>',self.handle_left_click)
            self.bind("<ButtonRelease-1>", self.handle_left_release)
            self.bind('<B1-Motion>', self.handle_mouse_drag)
            self.bind('<Motion>', self.handle_mouse_move)
            self.bind('<Shift-Button-1>', self.handle_left_shift_click)
            self.bind('<Control-Button-1>', self.handle_left_ctrl_click)
            self.bind("<Double-Button-1>",self.handle_double_click)
            self.bind('<Leave>', self.leave)
            if self.table.ostyp=='mac':
                #For mac we bind Shift, left-click to right click
                self.bind("<Button-2>", self.handle_right_click)
                self.bind('<Shift-Button-1>',self.handle_right_click)
            else:
                self.bind("<Button-3>", self.handle_right_click)
            self.thefont = self.table.thefont
            self.setDefaults()
        return

    def setDefaults(self):
        self.colselectedcolor = '#0099CC'
        return

    def redraw(self):
        """Redraw column header"""

        df = self.model.df
        cols = self.model.getColumnCount()
        self.tablewidth=self.table.tablewidth
        self.configure(scrollregion=(0,0,
                                     self.table.tablewidth+self.table.x_start,
                                     self.height))
        self.delete('gridline','text')
        self.delete('rect')
        self.delete('dragrect')
        self.atdivider = None
        font = self.thefont
        align = 'w'
        pad = 5
        wrapw = 0
        h = self.height
        y = h/2
        x_start = self.table.x_start
        if cols == 0:
            return

        for col in self.table.visiblecols:
            colname = df.columns[col]
            colstr = str(colname)
            if colstr in self.model.columnwidths:
                w = self.model.columnwidths[colstr]
            else:
                w = self.table.cellwidth
            if w<=8:
                colname=''
            x = self.table.col_positions[col]
            if align == 'w':
                xt = x+pad
            elif align == 'e':
                xt = x+w-pad
            elif align == 'center':
                xt = x-w/2

            if util.check_multiindex(self.model.df.columns) == 1:
                if isinstance(colname, tuple):
                    lens = [util.getTextLength(c, w-pad, font=font)[1] for c in colname]
                    colname = [str(c)[:l] for c,l in zip(colname,lens)]
                colname = '\n'.join(colname)
                #wrapw = w-pad
                xt = x+pad
                align = 'nw'
                y=3
            else:
                colname = str(colname)
                #wrapw = 0
                tw,length = util.getTextLength(colname, w-pad, font=font)
                colname = colname[0:length]

            line = self.create_line(x, 0, x, h, tag=('gridline', 'vertline'),
                                 fill='white', width=1)
            self.create_text(xt,y,
                                text=colname,
                                fill='white',
                                font=self.thefont,
                                tag='text', anchor=align)
        x = self.table.col_positions[col+1]
        self.create_line(x,0, x,h, tag='gridline',
                        fill='white', width=2)
        return

    def handle_left_click(self,event):
        """Does cell selection when left mouse button is clicked"""

        self.delete('rect')
        self.table.delete('entry')
        self.table.delete('multicellrect')
        colclicked = self.table.get_col_clicked(event)
        if colclicked == None:
            return
        #set all rows for plotting if no multi selection
        if len(self.table.multiplerowlist) <= 1 or self.table.startrow == self.table.endrow:
            self.table.allrows = True

        self.table.setSelectedCol(colclicked)
        if self.atdivider == 1:
            return
        self.drawRect(self.table.currentcol)
        #also draw a copy of the rect to be dragged
        self.draggedcol = None
        self.drawRect(self.table.currentcol, tag='dragrect',
                        color='lightblue', outline='white')
        if hasattr(self, 'rightmenu') and self.rightmenu != None:
            self.rightmenu.destroy()
        #finally, draw the selected col on the table
        self.table.drawSelectedCol()
        return

    def handle_left_release(self,event):
        """When mouse released implement resize or col move"""

        self.delete('dragrect')
        #if ctrl selection return
        if len(self.table.multiplecollist) > 1:
            return
        #column resized
        if self.atdivider == 1:
            x = int(self.canvasx(event.x))
            col = self.table.currentcol
            x1,y1,x2,y2 = self.table.getCellCoords(0,col)
            newwidth = x - x1
            if newwidth < 5:
                newwidth=5
            self.table.resizeColumn(col, newwidth)
            self.table.delete('resizeline')
            self.delete('resizeline')
            self.delete('resizesymbol')
            self.atdivider = 0
            return
        self.delete('resizesymbol')
        #move column
        if self.draggedcol != None and self.table.currentcol != self.draggedcol:
            self.model.moveColumn(self.table.currentcol, self.draggedcol)
            self.table.setSelectedCol(self.draggedcol)
            self.table.redraw()
            self.table.drawSelectedCol(self.table.currentcol)
            self.drawRect(self.table.currentcol)
        return

    def handle_right_click(self, event):
        """respond to a right click"""

        colclicked = self.table.get_col_clicked(event)
        multicollist = self.table.multiplecollist
        if len(multicollist) > 1:
            pass
        else:
            self.handle_left_click(event)
        self.rightmenu = self.popupMenu(event)
        return

    def handle_mouse_drag(self, event):
        """Handle column drag, will be either to move cols or resize"""

        x=int(self.canvasx(event.x))
        if self.atdivider == 1:
            self.table.delete('resizeline')
            self.delete('resizeline')
            self.table.create_line(x, 0, x, self.table.rowheight*self.table.rows,
                                width=2, fill='gray', tag='resizeline')
            self.create_line(x, 0, x, self.height,
                                width=2, fill='gray', tag='resizeline')
            return
        else:
            w = self.table.cellwidth
            self.draggedcol = self.table.get_col_clicked(event)
            coords = self.coords('dragrect')
            if len(coords)==0:
                return
            x1, y1, x2, y2 = coords
            x=int(self.canvasx(event.x))
            y = self.canvasy(event.y)
            self.move('dragrect', x-x1-w/2, 0)

        return

    def within(self, val, l, d):
        """Utility funtion to see if val is within d of any
            items in the list l"""

        for v in l:
            if abs(val-v) <= d:
                return 1
        return 0

    def leave(self, event):
        """Mouse left canvas event"""
        self.delete('resizesymbol')
        return

    def handle_mouse_move(self, event):
        """Handle mouse moved in header, if near divider draw resize symbol"""

        if len(self.model.df.columns) == 0:
            return
        self.delete('resizesymbol')
        w=self.table.cellwidth
        h=self.height
        x_start=self.table.x_start
        #x = event.x
        x=int(self.canvasx(event.x))
        if x > self.tablewidth+w:
            return
        #if event x is within x pixels of divider, draw resize symbol
        if x!=x_start and self.within(x, self.table.col_positions, 4):
            col = self.table.get_col_clicked(event)
            if col == None:
                return
            self.draw_resize_symbol(col)
            self.atdivider = 1
        else:
            self.atdivider = 0
        return

    def handle_right_release(self, event):
        self.rightmenu.destroy()
        return

    def handle_left_shift_click(self, event):
        """Handle shift click, for selecting multiple cols"""

        self.table.delete('colrect')
        self.delete('rect')
        currcol = self.table.currentcol
        colclicked = self.table.get_col_clicked(event)
        if colclicked > currcol:
            self.table.multiplecollist = list(range(currcol, colclicked+1))
        elif colclicked < currcol:
            self.table.multiplecollist = list(range(colclicked, currcol+1))
        else:
            return
        for c in self.table.multiplecollist:
            self.drawRect(c, delete=0)
            self.table.drawSelectedCol(c, delete=0)
        return

    def handle_left_ctrl_click(self, event):
        """Handle ctrl clicks - for multiple column selections"""

        currcol = self.table.currentcol
        colclicked = self.table.get_col_clicked(event)
        multicollist = self.table.multiplecollist
        if 0 <= colclicked < self.table.cols:
            if colclicked not in multicollist:
                multicollist.append(colclicked)
            else:
                multicollist.remove(colclicked)
        self.table.delete('colrect')
        self.delete('rect')
        for c in self.table.multiplecollist:
            self.drawRect(c, delete=0)
            self.table.drawSelectedCol(c, delete=0)
        return

    def handle_double_click(self, event):
        """Double click sorts by this column. """

        colclicked = self.table.get_col_clicked(event)
        self.table.sortTable()
        return

    def popupMenu(self, event):
        """Add left and right click behaviour for column header"""

        df = self.table.model.df
        if len(df.columns)==0:
            return
        ismulti = util.check_multiindex(df.columns)
        colname = str(df.columns[self.table.currentcol])
        currcol = self.table.currentcol
        multicols = self.table.multiplecollist
        colnames = list(df.columns[multicols])[:4]
        colnames = [str(i) for i in colnames]
        colnames = ','.join(colnames)
        popupmenu = Menu(self, tearoff = 0)
        def popupFocusOut(event):
            popupmenu.unpost()
        popupmenu.add_command(label="Rename Column", command=self.renameColumn)
        popupmenu.add_command(label="Sort by " + colnames + ' \u2193',
                    command=lambda : self.table.sortTable(ascending=[1 for i in multicols]))
        popupmenu.add_command(label="Sort by " + colnames + ' \u2191',
            command=lambda : self.table.sortTable(ascending=[0 for i in multicols]))
        popupmenu.add_command(label="Set %s as Index" %colnames, command=self.table.setindex)
        if ismulti == True:
            popupmenu.add_command(label="Flatten Index", command=self.table.flattenIndex)
        popupmenu.add_command(label="Delete Column(s)", command=self.table.deleteColumn)
        popupmenu.add_command(label="Set Column Type", command=self.table.setColumnType)
        popupmenu.add_command(label="Create Categorical", command=self.table.createCategorical)
        popupmenu.add_command(label="Apply Function", command=self.table.applyFunction)
        popupmenu.add_command(label="Apply Function Col-wise", command=self.table.applyColumnWise)
        popupmenu.add_command(label="String Operation", command=self.table.applyStringMethod)
        popupmenu.bind("<FocusOut>", popupFocusOut)
        #self.bind("<Button-3>", popupFocusOut)
        popupmenu.focus_set()
        popupmenu.post(event.x_root, event.y_root)
        return popupmenu

    def renameColumn(self):
        """Rename column"""

        col = self.table.currentcol
        df = self.model.df
        name = df.columns[col]
        new = simpledialog.askstring("New column name?", "Enter new name:",
                                     initialvalue=name)
        if new !=None:
            if new == '':
                messagebox.showwarning("Error", "Name should not be blank.")
                return
            else:

                df.rename(columns={df.columns[col]: new}, inplace=True)
                self.redraw()
        return

    def draw_resize_symbol(self, col):
        """Draw a symbol to show that col can be resized when mouse here"""

        self.delete('resizesymbol')
        w=self.table.cellwidth
        h=self.height
        #if x_pos > self.tablewidth:
        #    return
        wdth=1
        hfac1=0.2
        hfac2=0.4
        x_start=self.table.x_start
        x1,y1,x2,y2 = self.table.getCellCoords(0,col)
        self.create_polygon(x2-3,h/4, x2-10,h/2, x2-3,h*3/4, tag='resizesymbol',
            fill='white', outline='gray', width=wdth)
        self.create_polygon(x2+2,h/4, x2+10,h/2, x2+2,h*3/4, tag='resizesymbol',
            fill='white', outline='gray', width=wdth)
        return

    def drawRect(self,col, tag=None, color=None, outline=None, delete=1):
        """User has clicked to select a col"""

        if tag == None:
            tag = 'rect'
        if color == None:
            color = self.colselectedcolor
        if outline == None:
            outline = 'gray25'
        if delete == 1:
            self.delete(tag)
        w=1
        x1,y1,x2,y2 = self.table.getCellCoords(0,col)
        rect = self.create_rectangle(x1,y1-w,x2,self.height,
                                  fill=color,
                                  outline=outline,
                                  width=w,
                                  tag=tag)
        self.lower(tag)
        return

class RowHeader(Canvas):
    """Class that displays the row headings (or DataFrame index).
       Takes it's size and rendering from the parent table.
       This also handles row/record selection as opposed to cell
       selection"""

    def __init__(self, parent=None, table=None, width=40):
        Canvas.__init__(self, parent, bg='gray75', width=width, height=None)
        if table != None:
            self.table = table
            self.width = width
            self.inset = 1
            self.color = '#C8C8C8'
            self.showindex = False
            self.maxwidth = 200
            self.config(height = self.table.height)
            self.startrow = self.endrow = None
            self.model = self.table.model
            self.bind('<Button-1>',self.handle_left_click)
            self.bind("<ButtonRelease-1>", self.handle_left_release)
            self.bind("<Control-Button-1>", self.handle_left_ctrl_click)
            self.bind('<Button-3>',self.handle_right_click)
            self.bind('<B1-Motion>', self.handle_mouse_drag)
            self.bind('<Shift-Button-1>', self.handle_left_shift_click)
        return

    def redraw(self, align='w', showkeys=False):
        """Redraw row header"""

        self.height = self.table.rowheight * self.table.rows+10
        self.configure(scrollregion=(0,0, self.width, self.height))
        self.delete('rowheader','text')
        self.delete('rect')

        xstart = 1
        pad = 5
        maxw = self.maxwidth
        v = self.table.visiblerows
        if len(v) == 0:
            return
        scale = self.table.getScale()
        h = self.table.rowheight
        index = self.model.df.index
        names = index.names

        if self.showindex == True:
            if util.check_multiindex(index) == 1:
                ind = index.values[v]
                cols = [pd.Series(i).astype('object').astype(str) for i in list(zip(*ind))]
                nl = [len(n) if n is not None else 0 for n in names]
                l = [c.str.len().max() for c in cols]
                #pick higher of index names and row data
                l = list(np.maximum(l,nl))
                widths = [i * scale + 6 for i in l]
                xpos = [0]+list(np.cumsum(widths))[:-1]
            else:
                ind = index[v]
                dtype = ind.dtype
                r = ind.astype('object').astype('str')
                l = r.str.len().max()
                widths = [l * scale + 6]
                cols = [r]
                xpos = [xstart]
            w = np.sum(widths)
            if w>maxw:
                w=maxw
            elif w<45:
                w=45
        else:
            rows = [i+1 for i in v]
            cols = [rows]
            w=45
            widths = [w]
            xpos = [xstart]

        if self.width != w:
            self.config(width=w)
            self.width = w

        i=0
        for col in cols:
            r=v[0]
            x = xpos[i]
            i+=1
            for row in col:
                text = row
                x1,y1,x2,y2 = self.table.getCellCoords(r,0)
                self.create_rectangle(x,y1,w-1,y2, fill=self.color,
                                        outline='white', width=1,
                                        tag='rowheader')
                self.create_text(x+pad,y1+h/2, text=text,
                                  fill='black', font=self.table.thefont,
                                  tag='text', anchor=align)
                r+=1
        return

    def setWidth(self, w):
        """Set width"""
        self.width = w
        self.redraw()
        return

    def clearSelected(self):
        """Clear selected rows"""
        self.delete('rect')
        return

    def handle_left_click(self, event):
        """Handle left click"""

        rowclicked = self.table.get_row_clicked(event)
        self.startrow = rowclicked
        if 0 <= rowclicked < self.table.rows:
            self.delete('rect')
            self.table.delete('entry')
            self.table.delete('multicellrect')
            #set row selected
            self.table.setSelectedRow(rowclicked)
            self.table.drawSelectedRow()
            self.drawSelectedRows(self.table.currentrow)
        return

    def handle_left_release(self,event):
        return

    def handle_left_ctrl_click(self, event):
        """Handle ctrl clicks - for multiple row selections"""

        rowclicked = self.table.get_row_clicked(event)
        multirowlist = self.table.multiplerowlist
        if 0 <= rowclicked < self.table.rows:
            if rowclicked not in multirowlist:
                multirowlist.append(rowclicked)
            else:
                multirowlist.remove(rowclicked)
            self.table.drawMultipleRows(multirowlist)
            self.drawSelectedRows(multirowlist)
        return

    def handle_left_shift_click(self, event):
        """Handle shift click"""

        if self.startrow == None:
            self.startrow = self.table.currentrow
        self.handle_mouse_drag(event)
        return

    def handle_right_click(self, event):
        """respond to a right click"""

        self.delete('tooltip')
        if hasattr(self, 'rightmenu'):
            self.rightmenu.destroy()
        self.rightmenu = self.popupMenu(event, outside=1)
        return

    def handle_mouse_drag(self, event):
        """Handle mouse moved with button held down, multiple selections"""

        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()
        rowover = self.table.get_row_clicked(event)
        colover = self.table.get_col_clicked(event)
        if rowover == None:
            return
        if rowover >= self.table.rows or self.startrow > self.table.rows:
            return
        else:
            self.endrow = rowover
        #draw the selected rows
        if self.endrow != self.startrow:
            if self.endrow < self.startrow:
                rowlist=list(range(self.endrow, self.startrow+1))
            else:
                rowlist=list(range(self.startrow, self.endrow+1))
            self.drawSelectedRows(rowlist)
            self.table.multiplerowlist = rowlist
            self.table.drawMultipleRows(rowlist)
            self.table.drawMultipleCells()
            self.table.allrows = False
        else:
            self.table.multiplerowlist = []
            self.table.multiplerowlist.append(rowover)
            self.drawSelectedRows(rowover)
            self.table.drawMultipleRows(self.table.multiplerowlist)
        return

    def toggleIndex(self):
        """Toggle index display"""

        if self.showindex == True:
            self.showindex = False
        else:
            self.showindex = True
        self.redraw()
        return

    def popupMenu(self, event, rows=None, cols=None, outside=None):
        """Add left and right click behaviour for canvas, should not have to override
            this function, it will take its values from defined dicts in constructor"""

        defaultactions = {"Sort by index" : lambda: self.table.sortTable(index=True),
                         "Reset index" : lambda: self.table.resetIndex(),
                         "Toggle index" : lambda: self.toggleIndex(),
                         "Copy index to column" : lambda: self.table.copyIndex(),
                         "Rename index" : lambda: self.table.renameIndex(),
                         "Sort columns by row" : lambda: self.table.sortColumnIndex(),
                         "Select All" : self.table.selectAll}
        main = ["Sort by index","Reset index","Toggle index",
                "Rename index","Sort columns by row","Copy index to column"]

        popupmenu = Menu(self, tearoff = 0)
        def popupFocusOut(event):
            popupmenu.unpost()
        for action in main:
            popupmenu.add_command(label=action, command=defaultactions[action])

        popupmenu.bind("<FocusOut>", popupFocusOut)
        popupmenu.focus_set()
        popupmenu.post(event.x_root, event.y_root)
        return popupmenu

    def drawSelectedRows(self, rows=None):
        """Draw selected rows, accepts a list or integer"""

        self.delete('rect')
        if type(rows) is not list:
            rowlist=[]
            rowlist.append(rows)
        else:
           rowlist = rows
        for r in rowlist:
            if r not in self.table.visiblerows:
                continue
            self.drawRect(r, delete=0)
        return

    def drawRect(self, row=None, tag=None, color=None, outline=None, delete=1):
        """Draw a rect representing row selection"""

        if tag==None:
            tag='rect'
        if color==None:
            color='#0099CC'
        if outline==None:
            outline='gray25'
        if delete == 1:
            self.delete(tag)
        w=0
        i = self.inset
        x1,y1,x2,y2 = self.table.getCellCoords(row, 0)
        rect = self.create_rectangle(0+i,y1+i,self.width-i,y2,
                                      fill=color,
                                      outline=outline,
                                      width=w,
                                      tag=tag)
        self.lift('text')
        return

class IndexHeader(Canvas):
    """Class that displays the row index headings."""

    def __init__(self, parent=None, table=None, width=40, height=20):
        Canvas.__init__(self, parent, bg='gray75', width=width, height=height)
        if table != None:
            self.table = table
            self.width = width
            self.height = height
            self.color = '#C8C8C8'
            self.startrow = self.endrow = None
            self.model = self.table.model
            self.bind('<Button-1>',self.handle_left_click)
        return

    def redraw(self, align='w'):
        """Redraw row index header"""

        rowheader = self.table.rowheader
        if rowheader.showindex == False:
            return
        self.delete('text','rect')
        xstart = 1
        pad = 5
        scale = self.table.getScale()
        h = self.table.rowheight
        index = self.model.df.index
        names = index.names
        if names[0] == None:
            widths = [self.width]
        else:
            l = [len(n) for n in names]
            widths = [i * scale + 6 for i in l]

        i=0; x=1; y=0
        for name in names:
            if name != None:
                self.create_text(x+pad,y+h/2,text=name,
                                    fill='white', font=self.table.thefont,
                                    tag='text', anchor=align)
                x=x+widths[i]
                i+=1
        return

    def handle_left_click(self, event):
        """Handle mouse left mouse click"""
        self.table.selectAll()
        return