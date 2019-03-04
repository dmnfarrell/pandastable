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
from collections import OrderedDict
try:
    from tkinter import *
    from tkinter.ttk import *
except:
    from Tkinter import *
    from ttk import *
try:
    import configparser
except:
    import ConfigParser as configparser
from . import util, plotting

baseoptions = OrderedDict()
baseoptions['base'] = {'font': 'Arial','fontsize':12,
                        'float format':'1.2f',
                        'row height':18,'cell width':80, 'line width':1,
                        'alignment':'w'
                        }

def write_default_config():
    """Write a default config to users .config folder. Used to add global settings."""

    fname = os.path.join(config_path, 'default.conf')
    if not os.path.exists(fname):
        try:
            #os.mkdir(config_path)
            os.makedirs(config_path)
        except:
            pass
        write_config(conffile=fname, defaults=baseoptions)
    return fname

def write_config(conffile='default.conf', defaults={}):
    """Write a default config file"""

    if not os.path.exists(conffile):
        cp = create_config_parser_from_dict(defaults, baseoptions.keys())
        cp.write(open(conffile,'w'))
        print ('wrote config file %s' %conffile)
    return conffile

def create_config_parser_from_dict(data=None, sections=['base',], **kwargs):
    """Helper method to create a ConfigParser from a dict of the form shown in
       baseoptions"""

    if data is None:
        data = baseoptions
    #print (data)
    cp = configparser.ConfigParser()
    for s in sections:
        cp.add_section(s)
        if not s in data:
            continue
        for name in sorted(data[s]):
            val = data[s][name]
            if type(val) is list:
                val = ','.join(val)
            cp.set(s, name, str(val))

    #use kwargs to create specific settings in the appropriate section
    for s in cp.sections():
        opts = cp.options(s)
        for k in kwargs:
            if k in opts:
                cp.set(s, k, kwargs[k])
    return cp

def parse_config(conffile=None):
    """Parse a configparser file"""

    f = open(conffile,'r')
    cp = configparser.ConfigParser()
    try:
        cp.read(conffile)
    except Exception as e:
        print ('failed to read config file! check format')
        print ('Error returned:', e)
        return
    f.close()
    return cp

def get_options(cp):
    """Makes sure boolean opts are parsed"""

    from collections import OrderedDict
    options = OrderedDict()
    #options = cp._sections['base']
    for section in cp.sections():
        options.update( (cp._sections[section]) )
    for o in options:
        for section in cp.sections():
            try:
                options[o] = cp.getboolean(section, o)
            except:
                pass
            try:
                options[o] = cp.getint(section, o)
            except:
                pass
    return options

def print_options(options):
    """Print option key/value pairs"""

    for key in options:
        print (key, ':', options[key])
    print ()

def check_options(opts):
    """Check for missing default options in dict. Meant to handle
       incomplete config files"""

    sections = list(baseoptions.keys())
    for s in sections:
        defaults = dict(baseoptions[s])
        for i in defaults:
            if i not in opts:
                opts[i] = defaults[i]
    return opts

def load_options():
    homepath = os.path.join(os.path.expanduser('~'))
    conffile = os.path.join(homepath,'.dataexplore/default.conf')
    if not os.path.exists(conffile):
        write_config(conffile, defaults=baseoptions)
    cp = parse_config(conffile)
    options = get_options(cp)
    options = check_options(options)
    return options

class preferencesDialog(Frame):
    """Preferences dialog from config parser options"""

    def __init__(self, parent, options):

        self.parent = parent
        self.main = Toplevel()
        self.master = self.main
        self.main.title('prefs')
        self.main.grab_set()
        self.main.transient(parent)
        self.main.resizable(width=False, height=False)
        self.createWidgets()
        self.options = options
        return

    def createWidgets(self):
        """create widgets"""

        fonts = util.getFonts()

        opts = {'row height':{'type':'entry','default':18},
                'cell width':{'type':'entry','default':80},
                'line width':{'type':'entry','default':1},
                'alignment':{'type':'combobox','default':'w','items':['w','e','center']},
                'font':{'type':'combobox','default':'Arial','items':fonts},
                'fontsize':{'type':'scale','default':12,'range':(5,40),'interval':1,'label':'font size'},
                'float format':{'type':'entry','default':'.1f'},
                'colormap':{'type':'combobox','default':'Spectral','items':plotting.colormaps},
                'marker':{'type':'combobox','default':'','items':plotting.markers},
                'linestyle':{'type':'combobox','default':'-','items':plotting.linestyles},
                'ms':{'type':'scale','default':5,'range':(1,80),'interval':1,'label':'marker size'},
                'grid':{'type':'checkbutton','default':0,'label':'show grid'},
                }
        sections = {'main':['row height','cell width','line width','font','fontsize','float format'],
                    'plotting':['marker','linestyle','ms','grid','colormap']}

        from . import dialogs
        dialog, tkvars, widgets = dialogs.dialogFromOptions(self.main, opts, sections)
        dialog.pack(side=TOP,fill=BOTH)
        #d = dialogs.getDictfromTkVars(opts, tkvars, widgets)
        print (tkvars)
        #print (d)

        bf=Frame(self.main)
        bf.pack()
        Button(bf, text='Save',  command=self.save).pack(side=LEFT)
        Button(bf, text='Close',  command=self.destroy).pack(side=LEFT)

        return

    def save(self):
        d = dialogs.getDictfromTkVars(opts, tkvars, widgets)
        return

    def quit(self):
        self.destroy()
        return
