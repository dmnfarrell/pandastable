#!/usr/bin/env python
"""
    pandastable examples
    Created January 2019
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

try:
    from tkinter import *
    from tkinter.ttk import *
except:
    from Tkinter import *
    from ttk import *
from pandastable.core import Table
from pandastable.data import TableModel
import pandas as pd

class MyTable(Table):
    """
      Custom table class inherits from Table.
      You can then override required methods
     """
    def __init__(self, parent=None, **kwargs):
        Table.__init__(self, parent, **kwargs)
        return

class MyApp(Frame):
    """Basic test frame for the table"""

    def __init__(self, parent=None):
        self.parent = parent
        Frame.__init__(self)
        self.main = self.master
        self.main.geometry('800x600+200+100')
        self.main.title('pandastable examples')
        f = Frame(self.main)
        f.pack(fill=BOTH,expand=1)
        pt = make_table(f)
        bp = Frame(self.main)
        bp.pack(side=TOP)
        b=Button(bp,text='Test1', command=test1)
        b.pack(side=LEFT,fill=BOTH,)
        b=Button(bp,text='Test2', command=select_test)
        b.pack(side=LEFT,fill=BOTH,)
        b=Button(bp,text='Test3', command=multiple_tables)
        b.pack(side=LEFT,fill=BOTH,)
        return

def make_table(frame, **kwds):
    """make a sample table"""

    df = TableModel.getSampleData()
    df['label'] = df.label.astype('category')
    pt = MyTable(frame, dataframe=df, **kwds )
    pt.show()
    return pt

def test1():
    """just make a table"""

    t = Toplevel()
    fr = Frame(t)
    fr.pack(fill=BOTH,expand=1)
    pt = make_table(fr)
    return

def select_test():
    """cell selection and coloring"""

    t = Toplevel()
    fr = Frame(t)
    fr.pack(fill=BOTH,expand=1)
    pt = Table(fr)
    pt.show()
    pt.importCSV('test.csv', index_col=0)
    pt.resetIndex(ask=False)
    pt.columncolors = {'c':'#fbf1b8'}
    df = pt.model.df
    #rows = pt.getRowsFromMask(mask=mask)
    #pt.multiplerowlist = rows

    mask_1 = df.a<7
    pt.setColorByMask('a', mask_1, '#ff9999')
    colors = {'red':'#f34130','blue':'blue'}
    for l in df.label.unique():
    	mask = df['label']==l
    	pt.setColorByMask('label', mask, l) #colors[l])
    pt.redraw()
    return

def multiple_tables():
    """make many tables in one frame"""

    t = Toplevel(height=800)
    r=0;c=0
    for i in range(6):
        fr = Frame(t)
        fr.grid(row=r,column=c)
        pt = make_table(fr, showtoolbar=False, showstatusbar=True)
        c+=1
        if c>2:
            c=0
            r+=1
    return

app = MyApp()
app.mainloop()
