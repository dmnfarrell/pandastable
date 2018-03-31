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
#from pandastable.dialogs import *

class DataReaderPlugin(Plugin):
    """Plugin for using pandas datareader for remote data access"""

    #capabilities = ['gui']
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
        self._doFrame(width=480,height=140)
        self.mainwin.title('Remote Data')
        self.mainwin.resizable(width=False,height=False)
        sources = ['Google Finance', 'FRED','World Bank','Eurostat','TSP','FAMA/French']
        dformats = ['%m/%d/%Y','%d/%m/%Y']
        grps = {'sources':['source','dataset','url'], 'time':['start','end','dateformat']}
        self.groups = grps = OrderedDict(grps)

        datacols = []
        self.opts = {
                     'source': {'type':'combobox','default':'FRED','items':sources,'width':20},
                     'dataset': {'type':'combobox','default':'F','items':['F']},
                     'url': {'type':'entry','default':'','label':'download url','width':25},
                     'start': {'type':'entry','default':'01/01/16','label':'start date','width':15},
                     'end': {'type':'entry','default':'31/12/16','label':'end date'},
                     'dateformat': {'type':'combobox','default':'%m/%d/%Y','items':dformats}
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
        #self.progframe = Frame(self.mainwin)
        #self.progframe.pack(side=TOP,fill=X)
        self.update()
        #self.prog_bar = Progress(bf)
        #self.prog_bar.pb_stop()
        return

    def fetch(self):

        import pandas_datareader as pdr
        import pandas_datareader.data as web
        from pandas_datareader import wb

        #self.prog_bar.pb_start()
        self.applyOptions()
        source = self.kwds['source']
        dataset = self.kwds['dataset']
        url = self.kwds['url']
        st = self.kwds['start']
        e = self.kwds['end']
        dateformat = self.kwds['dateformat']
        start = pd.to_datetime(st, format=dateformat, errors='ignore')
        end = pd.to_datetime(e, format=dateformat, errors='ignore')

        if url != '':
            df = self.fetch_url(url)
            if df is None:
                return
            label = os.path.basename(url)
            self.parent.load_dataframe(df, label, True)
            return

        if source == 'Yahoo Finance':
            df = web.DataReader("F", 'yahoo', start, end)
        elif source == 'Google Finance':
            df = web.DataReader("F", 'google', start, end)
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
            tspreader = tsp.TSPReader(start=start, end=end)
            df = tspreader.read()
        elif source == 'FAMA/French':
            ds = web.DataReader(dataset, "famafrench")
            df = ds[0]
        label = source+'_'+dataset
        df=df.reset_index()
        self.parent.load_dataframe(df, label, True)
        #self.prog_bar.pb_stop()
        return

    def fetch_url(self, url):
        """Fetch data from an url"""

        ext = os.path.splitext(url)[1]
        if ext == '.zip':
            import zipfile, io, urllib
            r = urllib.request.urlopen(url)
            z = zipfile.ZipFile(io.BytesIO(r.read()))
            info = z.infolist()
            print (info)
            #for i in info:
            #    name = info.filename

        try:
            df = pd.read_csv(url)
        except Exception as e:
            messagebox.showwarning("Failed to read URL",
                                   "%s" %e,
                                   parent=self.parent)
            df=None
        return df

    def update(self, evt=None):
        """Update data widget(s)"""

        datasets = []
        self.applyOptions()
        source = self.kwds['source']
        x = ['F']
        if source == 'Yahoo Finance':
            x = ['F']
        elif source == 'FAMA/French':
            from pandas_datareader.famafrench import get_available_datasets
            x = get_available_datasets()

        w = self.widgets['dataset']
        w['values'] = x
        w.set(x[0])
        return

    def applyOptions(self):
        """Set the options"""

        kwds = {}
        for i in self.opts:
            if self.opts[i]['type'] == 'listbox':
                items = self.widgets[i].curselection()
                kwds[i] = [self.widgets[i].get(j) for j in items]
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

    def quit(self, evt=None):
        """Override this to handle pane closing"""

        self.mainwin.destroy()
        return

    def about(self):
        """About this plugin"""

        txt = "This plugin allows fetching of remote data from\n"+\
              "multiple sources of public data using the pandas\n"+\
              "datareader. See https://pandas-datareader.readthedocs.io\n"+\
              "version: %s" %self.version
        return txt
