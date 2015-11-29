#!/usr/bin/env python
"""
    Implements a configuration class for pandastable
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

import math, time
import os, types
import string, copy
from configparser import ConfigParser

class Prefs():
    """This class implements a preferences system using configparser """

    def __init__(self, filename=None):

        homepath = os.path.join(os.path.expanduser('~'))
        path = '.pandastable'
        self.defaultpath = os.path.join(homepath, path)
        if not os.path.exists(self.defaultpath):
            os.mkdir(self.defaultpath)
        if filename == None:
            filename = os.path.join(self.defaultpath, 'default.conf')
        if not os.path.exists(filename):
            self.createConfig(filename)
            self.writeConfig()
        else:
            self.parseConfig(filename)
        self.filename = filename
        return

    def createConfig(self, conffile='default.conf', **kwargs):
        """Create a basic config file with default options and/or custom values"""

        c = ConfigParser()
        wdir = os.path.join(self.defaultpath,'workingdir')
        functionsconf = os.path.join(self.defaultpath,'functions.conf')
        sections = ['table','plotting']
        defaults = {'table': [('horizlines', 'True') ],
                    'plotting': [('saveplots', 'False'), ('fontsize','12'),]
                            #('alpha',0.8),
                            #('font','monospace'), ('markersize',25), ('linewidth',1),
                            #('dpi', 80), ('marker','o'),
                            #('legend',0)]
                    }

        cp = createConfigParserfromDict(defaults, sections ,**kwargs)
        cp.write(open(conffile,'w'))
        self.parseConfig(conffile)
        return cp

    def parseConfig(self, conffile=None):
        """Parse the config file"""

        f = open(conffile,'r')
        cp = ConfigParser()
        try:
            cp.read(conffile)
        except Exception as e:
            print('failed to read config file! check format')
            print('error returned:', e)
            return
        self.filename = conffile
        #as attributes
        setAttributesfromConfigParser(self, cp)
        print('parsed config file ok')
        return

    def writeConfig(self, filename=None):
        """Save a config file from the current object"""

        if filename == None:
            filename = self.configurationfile
        data = self.__dict__
        cp = createConfigParserfromDict(data, self.configsections)
        cp.write(open(filename,'w'))
        return

def setAttributesfromConfigParser(obj, cp):
    """A helper method that makes the options in a ConfigParser object
       attributes of obj"""

    for s in cp.sections():
        obj.__dict__[s] = cp.items(s)
        for f in cp.items(s):
            try: val=int(f[1])
            except: val=f[1]
            obj.__dict__[f[0]] = val

def createConfigParserfromDict(data, sections, **kwargs):
    """Helper method to create a ConfigParser from a dict and/or keywords"""

    cp = ConfigParser()
    for s in sections:
        cp.add_section(s)
        if not s in data:
            continue
        for i in data[s]:
            name,val = i
            print(s,name,val)
            cp.set(s, name, val)

    #use kwargs to create specific settings in the appropriate section
    for s in cp.sections():
        opts = cp.options(s)
        for k in kwargs:
            if k in opts:
                cp.set(s, k, kwargs[k])

    return cp

def getDialog():
    dialog, self.tkvars, self.widgets = dialogFromOptions(parent, opts, groups)


from tkinter import *
from tkinter.ttk import *
from .core import Table
from .data import TableModel

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

if __name__ == '__main__':
    p = Prefs()
    #app=App()
    #app.mainloop()
