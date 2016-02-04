#!/usr/bin/env python
"""
    Implements tests for pandastable.
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

from __future__ import absolute_import, print_function
import sys, os
try:
    from tkinter import *
    from tkinter.ttk import *
except:
    from Tkinter import *
    from ttk import *
import pandas as pd
from .core import Table
from .data import TableModel
from .app import DataExplore
import unittest
import threading

class clickThread(threading.Thread):
    def __init__(self, root):
        threading.Thread.__init__(self)
        self.root = root

    def getButton(self, root):
        print(self.root.children)

    def run(self):
        button = lambda a: isinstance(a, Button)
        self.getButton(self.root)
        print ("clicked")

class App(Frame):
    """Test frame for table"""
    def __init__(self, parent=None):
        self.parent = parent
        Frame.__init__(self)
        self.main = self.master
        self.main.geometry('600x400+200+100')
        f = Frame(self.main)
        f.pack(fill=BOTH,expand=1)
        df = TableModel.getSampleData()
        self.table = pt = Table(f, dataframe=df)
        pt.show()
        return

class TableTests(unittest.TestCase):
    """Pandastable tests - test anything involving table manipulation
       but avoid actions that trigger dialogs"""
    def setUp(self):
        self.app = app = App()
        #thread = clickThread(self.table.parentframe)
        #thread.start()
        return

    def testA(self):
        """Simple table tests"""

        #app.mainloop()
        table = self.app.table
        model = table.model
        table.setSelectedRow(10)
        model.deleteRows(table.multiplerowlist)
        table.redraw()
        model.deleteColumns(table.multiplecollist)
        table.redraw()
        table.autoResizeColumns()
        df = TableModel.getSampleData()
        table.createChildTable(df)
        return

    def testB(self):
        """Sorting and adding"""

        table = self.app.table
        table.sortTable(0, ascending=1)
        table.sortTable(4, ascending=0)
        table.setSelectedCol(2)
        table.drawSelectedCol()
        table.getSelectedDataFrame()
        table.setindex()
        table.resetIndex()
        table.addRows(2)
        return

    def testC(self):
        """Table manipulation"""

        table = self.app.table
        table.groupby(0)
        table.transpose()
        table.sortTable(0, ascending=1)
        table.transpose()
        table.sortTable(0, ascending=1)
        table.deleteCells([2],[3],answer=1)
        #print (table.model.df)
        return

    def testD(self):
        """Load/save test"""

        df = TableModel.getSampleData(rows=10000)
        model = TableModel(df)
        table = self.app.table
        table.updateModel(model)
        table.saveAs('temp.mpk')
        table.load('temp.mpk')
        return

    '''def testE(self):
        """Plugins test"""

        from . import plugin
        for plg in plugin.get_plugins_classes('gui'):
            p = plg()
            print (p)
        return'''

    def quit(self):
        self.app.quit()

class DataExploreTests(unittest.TestCase):
    def setUp(self):
        return

    '''def testApp(self):
        """Basic dataexplore app test"""
        app = DataExplore()
        table = app.getCurrentTable()
        app.deleteSheet()
        app.sampleData()
        table.selectAll()
        table.plotSelected()
        app.quit()'''

if __name__ == '__main__':
    unittest.main()
