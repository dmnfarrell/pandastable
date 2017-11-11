#!/usr/bin/env python
"""
    DataExplore plugin for seaborn plotting.
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
import os, datetime
from pandastable.plugin import Plugin
from pandastable import plotting, dialogs
try:
    from tkinter import *
    from tkinter.ttk import *
except:
    from Tkinter import *
    from ttk import *
import pandas as pd
import pylab as plt
from collections import OrderedDict
#import seaborn as sns

class DataReaderPlugin(Plugin):
    """Plugin for using pandas datareader for remote data access"""

    capabilities = ['gui']
    requires = ['']
    menuentry = 'Remote Data'
    gui_methods = {}
    version = '0.1'

    def __init__(self):
        return

    def main(self, parent):

        if parent==None:
            return
        self.parent = parent
        self._doFrame(width=400,height=160)
        self.mainwin.title('Remote Data')
        sources = ['Yahoo','Google Finance','OECD','FRED','World Bank','Eurostat','TSP']

        grps = {'sources':['source','dataset'], 'time':['start','end']}
        self.groups = grps = OrderedDict(grps)

        datacols = []
        self.opts = {
                     'source': {'type':'combobox','default':'yahoo','items':sources},
                     'dataset': {'type':'combobox','default':'F','items':['F']},
                     'start': {'type':'entry','default':'','label':'start date'},
                     'end': {'type':'entry','default':'','label':'end date'}
                     }
        fr = self._createWidgets(self.mainwin)
        fr.pack(side=LEFT,fill=BOTH)
        bf = Frame(self.mainwin, padding=2)
        bf.pack(side=LEFT,fill=BOTH)
        b = Button(bf, text="Fetch Data", command=self.fetch)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="Close", command=self.quit)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="About", command=self._aboutWindow)
        b.pack(side=TOP,fill=X,pady=2)

        #self.table = self.parent.getCurrentTable()
        #df = self.table.model.df
        #self.update(df)
        return

    def fetch(self):

        import pandas_datareader as pdr
        import pandas_datareader.data as web
        from pandas_datareader import wb

        self.applyOptions()
        source = self.kwds['source']
        start = datetime.datetime(2013, 1, 1)
        end = datetime.datetime(2016, 1, 27)
        if source == 'Yahoo':
            df = web.DataReader("F", source, start, end)
        elif source == 'FRED':
            df = web.DataReader("GDP", "fred", start, end)
        elif source == 'OECD':
            df = web.DataReader('UN_DEN', 'oecd', end=end)
        elif source == 'World Bank':
            df = wb.download(indicator='NY.GDP.PCAP.KD', country=['US', 'CA', 'MX'], start=2005, end=2008)
        elif source == 'Eurostat':
            df = web.DataReader("tran_sf_railac", 'eurostat')
        elif source == 'TSP':
            import pandas_datareader.tsp as tsp
            tspreader = tsp.TSPReader(start='2015-10-1', end='2015-12-31')
            df = tspreader.read()

        self.parent.load_dataframe(df, source, True)
        return

    def applyOptions(self):
        """Set the options"""

        kwds = {}
        for i in self.opts:
            if self.opts[i]['type'] == 'listbox':
                items = self.widgets[i].curselection()
                kwds[i] = [self.widgets[i].get(j) for j in items]
                print (items, kwds[i])
            else:
                kwds[i] = self.tkvars[i].get()
        self.kwds = kwds

        return

    def _createWidgets(self, parent, callback=None):
        """Auto create tk vars, widgets for corresponding options and
           and return the frame"""

        dialog, self.tkvars, self.widgets = plotting.dialogFromOptions(parent, self.opts, self.groups)
        self.widgets['source'].bind("<<ComboboxSelected>>", self.update)
        return dialog

    def update(self, df):
        """Update data widget(s)"""

        #self.widgets['hue']['values'] = cols

        return

    def quit(self, evt=None):
        """Override this to handle pane closing"""

        self.mainwin.destroy()
        return

    def about(self):
        """About this plugin"""

        txt = "This plugin allows fetching of remote data from\n"+\
              "multiple sources of public data.\n"+\
               "version: %s" %self.version
        return txt
