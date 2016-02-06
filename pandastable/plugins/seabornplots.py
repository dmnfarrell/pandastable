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

class SeabornPlugin(Plugin):
    """Plugin for DataExplore"""

    capabilities = ['gui','uses_sidepane']
    requires = ['']
    menuentry = 'Factor Plots'
    gui_methods = {}
    version = '0.1'

    def __init__(self):

        return

    def main(self, parent):

        if parent==None:
            return
        self.parent = parent
        self._doFrame()
        self.setDefaultStyle()
        grps = {'formats':['kind','wrap','palette','logy','aspect'],
                    'factors':['hue','col','x','ci','melt'],
                    'labels':['title','ylabel','rot','fontscale']}
        self.groups = grps = OrderedDict(grps)
        styles = ['darkgrid', 'whitegrid', 'dark', 'white', 'ticks']
        kinds = ['point', 'bar', 'count', 'box', 'violin', 'strip']
        palettes = ['Spectral','cubehelix','hls','hot','coolwarm','copper',
                    'winter','spring','summer','autumn','Greys','Blues','Reds',
                    'Set1','Set2','Accent']
        datacols = []
        self.opts = {'wrap': {'type':'entry','default':2,'label':'column wrap'},
                     'palette': {'type':'combobox','default':'Spectral','items':palettes},
                     'kind': {'type':'combobox','default':'bar','items':kinds},
                     'col': {'type':'combobox','default':'','items':datacols},
                     'hue': {'type':'combobox','default':'','items':datacols},
                     'x': {'type':'combobox','default':'','items':datacols},
                     'ci':{'type':'entry','default':95,'width':16},
                     'melt':{'type':'checkbutton','default':1,'label':'convert to long form'},
                     'fontscale':{'type':'scale','default':1.2,'range':(.5,3),'interval':.1,'label':'font scale'},
                     'title':{'type':'entry','default':'','width':16},
                     'ylabel':{'type':'entry','default':'','width':16},
                     'rot':{'type':'entry','default':0, 'label':'xlabel angle'},
                     'logy':{'type':'checkbutton','default':0,'label':'log y'},
                     'aspect':{'type':'entry','default':1.0, 'label':'aspect'},
                     }
        fr = self._plotWidgets(self.mainwin)
        fr.pack(side=LEFT,fill=BOTH)
        bf = Frame(self.mainwin, padding=2)
        bf.pack(side=LEFT,fill=BOTH)
        b = Button(bf, text="Replot", command=self._plot)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="Clear", command=self.clear)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="Close", command=self.quit)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="About", command=self._aboutWindow)
        b.pack(side=TOP,fill=X,pady=2)

        self.table = self.parent.getCurrentTable()
        df = self.table.model.df
        self.update(df)

        sheet = self.parent.getCurrentSheet()
        #reference to parent frame in sheet
        pw = self.parent.sheetframes[sheet]
        #hide the plot viewer from the sheet?
        #self.parent.hidePlot()
        self.pf = Frame(pw)
        pw.add(self.pf, weight=3)
        self.fig, self.canvas = plotting.addFigure(self.pf)
        return

    def _plot(self):
        """Do plot"""

        import seaborn as sns
        self.applyOptions()
        kwds = self.kwds
        fontscale = kwds['fontscale']
        font = kwds['font']
        self.setDefaultStyle(fontscale=fontscale, font=font)

        df = self.table.getPlotData()
        #dtypes = list(df.dtypes)
        col = kwds['col']
        wrap=int(kwds['wrap'])
        ci = kwds['ci']
        logy = kwds['logy']
        melt = kwds['melt']
        if col == '':
            col = None
            wrap = 1
        if wrap == 1:
            row=col
            col=None
            wrap=None
        else:
            row=None
        hue = kwds['hue']
        kind = kwds['kind']
        x = kwds['x']
        order = None
        if x == '':
            x = 'var'
        aspect = float(kwds['aspect'])
        palette=kwds['palette']
        xlabelrot = kwds['rot']
        if hue == '':
            hue=None
        if col == '':
            col=None

        labels = list(df.select_dtypes(include=['object','category']).columns)
        if melt == True:
            t = pd.melt(df,id_vars=labels, var_name='var',value_name='value')
        else:
            t = df
        try:
            g = sns.factorplot(x=x,y='value',data=t, hue=hue, col=col, row=row,
                            col_wrap=wrap, kind=kind,size=3, aspect=float(aspect),
                            legend_out=False, sharey='all', palette=palette, order=order,
                            ci=ci)
            self.g = g
        except Exception as e:
            self.showWarning(e)
            return

        #need to always make a new canvas to get size right
        for child in self.pf.winfo_children():
            child.destroy()
        self.fig, self.canvas = plotting.addFigure(self.pf, g.fig)
        plt.suptitle(kwds['title'], fontsize=14*fontscale)
        plt.legend(loc='best')

        ylabel = kwds['ylabel']
        for ax in g.axes.flatten():
            for t in ax.get_xticklabels():
                t.set(rotation=xlabelrot)
            if ylabel != '':
                ax.set_ylabel(ylabel)
            if logy == True:
                ax.set_yscale('log')

        plt.tight_layout()
        bottom = 0.1
        if xlabelrot>30:
            bottom=0.2
        self.fig.subplots_adjust(top=0.9, bottom=bottom)
        self.canvas.draw()
        return

    def clear(self):
        """Clear figure canvas"""
        self.fig.clear()
        self.canvas.draw()
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
        #take font from plotter?
        kwds['font'] = self.table.pf.mplopts.kwds['font']
        return

    def setDefaultStyle(self, fontscale=1.2, font='monospace'):

        import seaborn as sns
        sns.set(font_scale=fontscale,
                rc={'figure.facecolor':'white','axes.facecolor': '#F7F7F7'})
        sns.set_style("ticks", {'font.family':font, 'axes.facecolor': '#F7F7F7',
                                'legend.frameon': True})
        sns.plotting_context('notebook',
                           rc={'legend.fontsize':16,'xtick.labelsize':12,
                          'ytick.labelsize':12,'axes.labelsize':14,'axes.titlesize':16})
        return

    def _plotWidgets(self, parent, callback=None):
        """Auto create tk vars, widgets for corresponding options and
           and return the frame"""

        dialog, self.tkvars, self.widgets = plotting.dialogFromOptions(parent, self.opts, self.groups)
        #self.applyOptions()
        return dialog

    def update(self, df):
        """Update data widget(s)"""

        cols = list(df.columns)
        cols += ''
        self.widgets['hue']['values'] = cols
        self.widgets['col']['values'] = cols
        self.widgets['x']['values'] = cols
        return

    def showWarning(self, s='plot error'):

        self.fig.clear()
        ax=self.fig.add_subplot(111)
        ax.text(.5, .5, s,transform=ax.transAxes,
                       horizontalalignment='center', color='blue', fontsize=16)
        self.canvas.draw()
        return

    def quit(self, evt=None):
        """Override this to handle pane closing"""

        self.fig.clear()
        plt.close('all')
        self.pf.destroy()
        self.mainwin.destroy()
        import seaborn as sns
        sns.reset_orig()
        return

    def about(self):
        """About this plugin"""

        txt = "This plugin implements factor plotting using\n"+\
              "the seaborn library which provides an interface\n"+\
              "for drawing attractive statistical graphics.\n\n"+\
              "http://stanford.edu/~mwaskom/software/seaborn/\n\n"\
               "version: %s" %self.version

        return txt

    def _importSeaborn(self):
        """Try to import seaborn. If not installed return false"""
        try:
            import seaborn as sns
            return 1
        except:
            print('seaborn not installed')
            return 0
