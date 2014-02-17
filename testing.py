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

import sys, os
from tkinter import *
from tkinter.ttk import *
import pandas as pd
from core import Table

class App(Frame):
    def __init__(self, parent=None):
        self.parent=parent
        Frame.__init__(self)
        self.main = self.master
        self.main.geometry('600x400+200+100')
        f=Frame(self.main)
        f.pack(fill=BOTH,expand=1)
        pt = Table(f)
        pt.show()
        pt.load('test.mpk')
        #pt.doImport('test.csv')

def main():
    "Run the application"
    app=App()
    app.mainloop()

    return

if __name__ == '__main__':
    main()
