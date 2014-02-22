#!/usr/bin/env python
"""
    Module for import dialogs.

    Created Feb 2014
    Copyright (C) Damien Farrell

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import types
from tkinter import *
from tkinter.ttk import *
import numpy as np
import pandas as pd
from pandastable.data import TableModel
from pandastable.dialogs import *

class ImportDialog(Frame):
    """Provides a frame for figure canvas and MPL settings"""

    def __init__(self, parent=None, filename=None):

        self.parent = parent
        self.filename = filename
        self.df = None
        self.main = Toplevel()
        self.master = self.main
        self.main.title('Text Import')
        self.main.protocol("WM_DELETE_WINDOW", self.quit)
        self.main.grab_set()
        self.main.transient(parent)

        opts = self.opts = {'delimiter':{'type':'combobox','default':',',
                        'items':[',',' ',';'], 'tooltip':'seperator'},
                     'header':{'type':'combobox','default':'infer','items':['infer'],
                                'tooltip':'position of column header'},
                     'decimal':{'type':'combobox','default':'.','items':['.',','],
                                'tooltip':'decimal point symbol'},
                     'comment':{'type':'entry','default':'#','label':'comment',
                                'tooltip':'comment symbol'},
                     'skipinitialspace':{'type':'checkbutton','default':0,'label':'skipinitialspace',
                                'tooltip':'skip initial space'},
                     }
        optsframe, self.tkvars = dialogFromOptions(self.main, opts)

        ''' escapechar=None, quotechar='"',
            skipinitialspace=False,
            lineterminator=None, index_col=None,
            names=None, prefix=None,
            skiprows=None, delimiter=None,
            delim_whitespace=False,
            '''
        tf = Frame(self.main)
        tf.pack(side=TOP,fill=BOTH,expand=1)
        from pandastable.core import Table
        self.previewtable = Table(tf,rows=0,columns=0)
        self.previewtable.show()
        self.update()

        optsframe.pack(side=TOP,fill=BOTH)
        bf = Frame(self.main)
        bf.pack(side=TOP,fill=BOTH)
        b = Button(bf, text="Update preview", command=self.update)
        b.pack(side=LEFT,fill=X,expand=1)
        b = Button(bf, text="Import", command=self.doImport)
        b.pack(side=LEFT,fill=X,expand=1)
        b = Button(bf, text="Cancel", command=self.quit)
        b.pack(side=LEFT,fill=X,expand=1)
        self.main.wait_window()
        return

    def update(self):
        kwds = {}
        for i in self.opts:
            kwds[i] = self.tkvars[i].get()
        self.kwds = kwds
        f = pd.read_csv(self.filename, chunksize=100, **kwds)
        df = f.get_chunk(100)
        model = TableModel(dataframe=df)
        self.previewtable.updateModel(model)
        self.previewtable.redraw()
        return

    def doImport(self):
        self.df = pd.read_csv(self.filename)
        self.quit()
        return

    def quit(self):
        self.main.destroy()
        return

