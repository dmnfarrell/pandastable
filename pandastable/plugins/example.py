#!/usr/bin/env python
"""
    DataExplore Application plugin example.
    Created Oct 2015
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
from tkinter import *
import tkinter
try:
    from tkinter.ttk import *
except:
    from ttk import *
from pandastable.plugin import Plugin

class ExamplePlugin(Plugin):
    """Template plugin for DataExplore"""

    #uncomment capabilities list to appear in menu
    capabilities = [] # ['gui','uses_sidepane']
    requires = ['']
    menuentry = 'Example Plugin'
    pluginrow = 6 #row to add plugin frame beneath table

    def main(self, parent):
        """Customise this or _doFrame for your widgets"""

        if parent==None:
            return
        self.parent = parent
        self.parentframe = None
        self._doFrame()
        return

    def _doFrame(self):

        if 'uses_sidepane' in self.capabilities:
            self.table = self.parent.getCurrentTable()
            self.mainwin = Frame(self.table.parentframe)
            self.mainwin.grid(row=pluginrow,column=0,columnspan=2,sticky='news')
        else:
            self.mainwin=Toplevel()
            self.mainwin.title('A DataExplore Plugin')
            self.mainwin.geometry('600x600+200+100')

        self.ID='Basic Plugin'
        #self._createMenuBar()

        l=Label(self.mainwin, text='This is a template plugin')
        l.pack(side=TOP,fill=BOTH)
        self.mainwin.bind("<Destroy>", self.quit)
        return

    def _createMenuBar(self):
        """Create the menu bar for the application. """

        self.menu=Menu(self.mainwin)
        self.file_menu={ '01Quit':{'cmd':self.quit}}
        self.file_menu=self.create_pulldown(self.menu,self.file_menu)
        self.menu.add_cascade(label='File',menu=self.file_menu['var'])
        self.mainwin.config(menu=self.menu)
        return

    def quit(self, evt=None):
        """Override this to handle pane closing"""
        return

    def about(self):
        """About this plugin"""

        txt = "This plugin implements ...\n"+\
               "version: %s" %self.version
        return txt
