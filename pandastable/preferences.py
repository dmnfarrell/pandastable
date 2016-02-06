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

from __future__ import absolute_import, division, print_function
import math, time
import os, types
import string, copy
from configparser import ConfigParser
try:
    from tkinter import *
    from tkinter.ttk import *
except:
    from Tkinter import *
    from ttk import *
from .core import Table
from .data import TableModel

class Prefs():
    """This class implements a preferences system using configparser """

    def __init__(self, path= '.pandastable', opts={}):

        homepath = os.path.join(os.path.expanduser('~'))
        self.defaultpath = os.path.join(homepath, path)
        if not os.path.exists(self.defaultpath):
            os.mkdir(self.defaultpath)

        filename = os.path.join(self.defaultpath, 'default.conf')
        self.filename = filename
        if not os.path.exists(filename):
            self.createConfig(opts, filename)
            self.writeConfig()
        else:
            self.parseConfig(filename)
        return

    def createConfig(self, opts={}, conffile='default.conf'):
        """Create a basic config file with default options and/or custom values"""

        c = ConfigParser()
        wdir = os.path.join(self.defaultpath,'workingdir')
        cp = createConfigParserfromOptions(opts, 'default')
        cp.write(open(conffile,'w'))
        self.cp = cp
        #self.parseConfig(conffile)
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
            filename = self.filename

        #cp = createConfigParserfromOptions(opts, 'default')
        self.cp.write(open(filename,'w'))
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

def createConfigParserfromOptions(opts, section):
    """Helper method to create a ConfigParser from a dict of options"""

    cp = ConfigParser()
    s='default'
    cp.add_section(s)
    for name in opts:
        val = opts[name]['default']
        print(name,val)
        cp.set(s, name, str(val))
    #cp.write(open(filename,'w'))
    return cp


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

    p = Prefs('.dataexplore')
    a=App()
    #from .plotting import MPLBaseOptions
    #opts = MPLBaseOptions(a).opts
    opts = {'layout':{'type':'checkbutton','default':'horizontal'},
            }
    p.createConfig(opts)

    #app=App()
    #app.mainloop()
