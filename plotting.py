#!/usr/bin/env python
"""
    Module for pylab plotting helper classes.

    Created Jan 2014
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
import matplotlib as mpl
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
#import matplotlib.animation as animation
from collections import OrderedDict
import operator
from pandastable.dialogs import *

colormaps = sorted(m for m in plt.cm.datad if not m.endswith("_r"))

class PlotViewer(Frame):
    """Provides a frame for figure canvas and MPL settings"""

    def __init__(self,parent=None):

        self.parent=parent
        self.mode = 0
        if self.parent != None:
            Frame.__init__(self, parent)
            self.main = self.master
        else:
            self.main = Toplevel()
            self.master = self.main
            self.main.title('Plot Viewer')
            self.main.protocol("WM_DELETE_WINDOW", self.quit)
        self.addFigure(self.main)
        def hide():
            if hidevar.get():
                self.nb.pack_forget()
            else:
                self.nb.pack(side=TOP,fill=BOTH)
        bf = Frame(self.main)
        bf.pack(side=TOP,fill=BOTH)
        b = Button(bf, text="Apply", command=self.applyPlotoptions)
        b.pack(side=LEFT,fill=X,expand=1)
        hidevar = IntVar()
        c = Checkbutton(bf,text='Hide Options', command=hide, variable=hidevar)
        c.pack(side=LEFT,fill=X,expand=1)
        self.nb = Notebook(self.main)
        self.nb.bind('<<NotebookTabChanged>>', self.setMode)
        self.nb.pack(side=TOP,fill=BOTH)

        self.mplopts = MPLBaseOptions()
        w1 = self.mplopts.showDialog(self.nb)
        self.nb.add(w1, text='base plot options', sticky='news')
        #self.factorplotter = FactorPlotter()
        #w3 = self.factorplotter.showDialog(self.nb)
        #self.nb.add(w3, text='factor plots', sticky='news')
        self.mplopts3d = MPL3DOptions()
        w2 = self.mplopts3d.showDialog(self.nb)
        self.nb.add(w2, text='3D plot', sticky='news')

        return

    def setMode(self, evt=None):
        """Set the plot mode based on selected tab"""
        self.mode = self.nb.index(self.nb.select())
        return

    def applyPlotoptions(self):
        """Apply the current plotter/options"""
        if self.mode == 0:
            self.mplopts.applyOptions()
        #elif self.mode == 1:
        #    self.factorplotter.applyOptions()
        elif self.mode == 1:
            self.mplopts3d.applyOptions()
        self.plotCurrent()
        return

    def addFigure(self, parent):
        """Add the tk figure canvas"""
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
        from matplotlib.figure import Figure
        #if hasattr(self,'canvas'):
        #    self.canvas._tkcanvas.destroy()
        self.fig = f = Figure(figsize=(5,4), dpi=100)
        a = f.add_subplot(111)
        canvas = FigureCanvasTkAgg(f, master=parent)
        canvas.show()
        canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)
        toolbar = NavigationToolbar2TkAgg(canvas, parent)
        toolbar.update()
        canvas._tkcanvas.pack(side=TOP, fill=BOTH, expand=1)
        self.ax = a
        self.canvas = canvas
        return

    def setFigure(self):
        from matplotlib.figure import Figure
        self.fig = f = Figure(figsize=(5,4), dpi=100)
        self.ax = f.add_subplot(111)
        self.canvas.figure = f
        f.canvas = self.canvas
        return

    def plotCurrent(self):
        """Plot current data"""
        if self.mode == 0:
            #self.setFigure()
            self.plot2D()
        #elif self.mode == 1:
        #    self.factorplotter.data = self.data
        #    self.factorPlot()
        elif self.mode == 1:
            self.plot3D()
        return

    def plot2D(self):
        """Draw method for current data. Relies on pandas plot functionality
           if possible. There is some messy code here to make sure only the valid
           plot options are passed for each plot kind."""

        if not hasattr(self, 'data'):
            return
        valid = {'line': ['alpha', 'colormap', 'grid', 'legend', 'linestyle',
                          'linewidth', 'marker', 'subplots', 'rot', 'logx', 'logy',
                           'sharey', 'use_index', 'kind'],
                    'scatter': ['alpha', 'grid', 'linewidth', 'marker', 's', 'legend', 'colormap'],
                    'hexbin': ['alpha', 'colormap', 'grid', 'linewidth'],
                    'bar': ['alpha', 'colormap', 'grid', 'legend', 'linewidth', 'subplots',
                            'sharey', 'stacked', 'rot', 'kind'],
                    'barh': ['alpha', 'colormap', 'grid', 'legend', 'linewidth', 'subplots',
                            'stacked', 'rot', 'kind'],
                    'histogram': ['alpha', 'linewidth', 'grid'],
                    'heatmap': ['colormap','rot'],
                    'density': ['alpha', 'colormap', 'grid', 'legend', 'linestyle',
                                 'linewidth', 'marker', 'subplots', 'rot', 'kind'],
                    'boxplot': ['alpha', 'linewidth', 'rot', 'grid'],
                    'scatter_matrix':['alpha', 'linewidth', 'marker', 'grid', 's'],
                    }

        data = self.data
        kwds = self.mplopts.kwds
        kind = kwds['kind']
        #valid kwd args for this plot type
        kwdargs = dict((k, kwds[k]) for k in valid[kind])

        if len(data.columns)==1:
            kwdargs['subplots'] = 0
        if kwds['subplots'] == 0:
            layout=None
        else:
            r=int(np.sqrt(len(data.columns)))
            layout=(r,-1)
        self.fig.clear()
        self.ax = ax = self.fig.add_subplot(111)
        if kind == 'bar':
            if len(data) > 50:
                self.ax.get_xaxis().set_visible(False)
        if kind == 'scatter':
            axs = self.scatter(data, ax, kwdargs)
        elif kind == 'boxplot':
            axs = data.boxplot(ax=ax)
        elif kind == 'histogram':
            axs = data.hist(ax=ax, **kwdargs)
        elif kind == 'heatmap':
            axs = self.heatmap(data, ax, kwdargs)
        elif kind == 'pie':
            ax.pie(data)
        elif kind == 'scatter_matrix':
            axs = pd.scatter_matrix(data, ax=ax, **kwdargs)
        elif kind == 'hexbin':
            cols = data.columns
            x = cols[0]
            y = cols[1]
            axs = data.plot(x,y,ax=ax,kind='hexbin',gridsize=20,**kwdargs)
        else:
            axs = data.plot(ax=ax, layout=layout, **kwdargs)
        if type(axs) is np.ndarray:
            self.ax = axs[0,0]
        self.fig.suptitle(kwds['title'])
        self.ax.set_xlabel(kwds['xlabel'])
        self.ax.set_ylabel(kwds['ylabel'])
        self.ax.xaxis.set_visible(kwds['showxlabels'])
        self.ax.yaxis.set_visible(kwds['showylabels'])
        self.canvas.draw()
        return

    def scatter(self, df, ax, kwds):
        """A more custom scatter plot"""
        if len(df.columns)<2:
            return
        cols = df.columns
        plots = len(cols)
        cmap = plt.cm.get_cmap(kwds['colormap'])
        if kwds['marker'] == '':
            kwds['marker'] = 'o'
        for i in range(1,plots):
            x = df[cols[0]]
            y = df[cols[i]]
            c = cmap(float(i)/(plots))
            if kwds['marker'] in ['x','+']:
                ec=c
            else:
                ec='black'
            ax.scatter(x, y, marker=kwds['marker'], alpha=kwds['alpha'],
                       s=kwds['s'], color=c, edgecolor=ec)
        if kwds['grid'] == 1:
            ax.grid()
        if kwds['legend'] == 1:
            ax.legend(cols[1:])
        return

    def heatmap(self, df, ax, kwds):
        """Plot heatmap"""
        hm = ax.pcolor(df, cmap=kwds['colormap'])
        self.fig.colorbar(hm, ax=ax)
        ax.set_xticks(np.arange(0.5, len(df.columns)))
        ax.set_yticks(np.arange(0.5, len(df.index)))
        ax.set_xticklabels(df.columns, minor=False)
        ax.set_yticklabels(df.index, minor=False)
        return

    def plot3D(self):
        """3D plots"""
        if not hasattr(self, 'data'):
            return
        kwds = self.mplopts3d.kwds
        print (kwds)
        data = self.data
        self.fig.clear()
        ax = self.ax = Axes3D(self.fig)
        if kwds['kind'] == 'scatter':
            self.scatter3D(data, ax, kwds)
        elif kwds['kind'] == 'bar':
            self.bar3D(data, ax, kwds)
        elif kwds['kind'] == 'contour':
            X = data.values
            ax.contour(X[:,0], X[:,1], X[:,2])
        self.fig.suptitle(kwds['title'])
        self.ax.set_xlabel(kwds['xlabel'])
        self.ax.set_ylabel(kwds['ylabel'])
        self.canvas.draw()
        return

    def bar3D(self, data, ax, kwds):
        i=0
        plots=len(data.columns)
        cmap = plt.cm.get_cmap(kwds['colormap'])
        for c in data.columns:
            h = data[c]
            c = cmap(float(i)/(plots))
            ax.bar(data.index, h, zs=i, zdir='y', color=c)
            i+=1

    def scatter3D(self, data, ax, kwds):
        X = data.values
        plots=len(data.columns)
        cmap = plt.cm.get_cmap(kwds['colormap'])
        x = X[:,0]
        for i in range(1,plots-1,2):
            y = X[:,i]
            z = X[:,i+1]
            c = cmap(float(i)/(plots))
            ax.scatter(x, y, z, color=c)
        return

    def factorPlot(self):
        """Seaborn facet grid plots"""
        import seaborn as sns
        if not hasattr(self, 'data'):
            return
        df = self.data
        labels = list(df.columns)
        dtypes = list(df.dtypes)
        x='id'
        print (labels)
        hue='label'
        col='var'
        row=None
        wrap=2
        kind='auto'
        aspect = 1.0

        print (df[:10])
        tm = pd.melt(df,id_vars=['label'],
                     var_name='var',value_name='x')
        print (tm[:10])

        '''plots = len(df[col].unique())
        wrap=int(wrap)
        if plots == 1 or wrap==1:
            row=col
            col=None
            wrap=None
        if hue == '':
            hue=None'''
        plt.clf()
        g = sns.factorplot('label','x',data=tm, hue=hue, row=row, col=col,
                                col_wrap=wrap, kind=kind,size=3, aspect=float(aspect),
                                legend_out=True,sharey=False,palette='Spectral')
        print (g.fig)
        #rotateLabels(g)
        self.fig.clear()
        self.figure.canvas = self.canvas
        self.canvas.figure = g.fig
        self.canvas._tkcanvas.config('state')
        self.canvas.draw()

        return

    def quit(self):
        self.main.withdraw()
        return

class animator(Frame):

    def __init__(self, parent, plotframe):
        Frame.__init__(self, parent)
        self.main = Frame(self)
        self.main.pack(side=TOP, fill=BOTH, expand=1)
        self.plotframe = plotframe
        self.doGUI()
        return

    def doGUI(self):
        b = Button(self.main, text='animate', command=self.animate)
        b.pack(side=TOP)
        l = Label(self.main, text='arse')
        l.pack(side=TOP)
        return

    def animate(self):

        def run(i):
            line.set_ydata(np.sin(x+i/10.0))
            return line,
        fig = self.plotframe.fig
        data = self.plotframe.data
        ax = self.plotframe.ax
        ax.clear()
        x = np.arange(0, 2*np.pi, 0.01)
        line, = ax.plot(x, np.sin(x))
        ani = animation.FuncAnimation(fig, run, np.arange(1, 200),
                            blit=True, interval=10,
                            repeat=False)
        return

    def run(data, ax):
        """update the data"""
        t,y = data
        xdata.append(t)
        ydata.append(y)
        xmin, xmax = ax.get_xlim()
        if t >= xmax:
            ax.set_xlim(xmin, 2*xmax)
            ax.figure.canvas.draw()
        line.set_data(xdata, ydata)
        return line,

class MPLBaseOptions(object):
    """Class to provide a dialog for matplotlib options and returning
        the selected prefs"""

    markers = ['','o','.','^','v','>','<','s','+','x','p','d','h','*']
    linestyles = ['-','--','-.',':','steps']
    kinds = ['line', 'scatter', 'bar', 'barh', 'boxplot', 'histogram',
             'heatmap', 'hexbin', 'scatter_matrix', 'density']

    def __init__(self):
        """Setup variables"""

        fonts = self.getFonts()
        grps = {'styles':['font','colormap','alpha','grid'],
                'sizes':['fontsize','s','linewidth'],
                'formats':['kind','marker','linestyle','stacked','subplots'],
                'axes':['showxlabels','showylabels','use_index','sharey','logx','logy','rot'],
                'labels':['title','xlabel','ylabel','legend']}
        order = ['data','formats','sizes','axes','styles','labels']
        self.groups = OrderedDict(sorted(grps.items()))
        opts = self.opts = {'font':{'type':'combobox','default':'Arial','items':fonts},
                'fontsize':{'type':'scale','default':12,'range':(5,40),'interval':1,'label':'font size'},
                'marker':{'type':'combobox','default':'','items':self.markers},
                'linestyle':{'type':'combobox','default':'-','items':self.linestyles},
                's':{'type':'scale','default':30,'range':(5,500),'interval':10,'label':'marker size'},
                'grid':{'type':'checkbutton','default':0,'label':'show grid'},
                'logx':{'type':'checkbutton','default':0,'label':'log x'},
                'logy':{'type':'checkbutton','default':0,'label':'log y'},
                'rot':{'type':'entry','default':0, 'label':'ylabel rot'},
                'use_index':{'type':'checkbutton','default':1,'label':'use index'},
                'showxlabels':{'type':'checkbutton','default':1,'label':'x tick labels'},
                'showylabels':{'type':'checkbutton','default':1,'label':'y tick labels'},
                'sharey':{'type':'checkbutton','default':0,'label':'share y'},
                'legend':{'type':'checkbutton','default':1,'label':'legend'},
                'kind':{'type':'combobox','default':'line','items':self.kinds,'label':'kind'},
                'stacked':{'type':'checkbutton','default':0,'label':'stacked bar'},
                'linewidth':{'type':'scale','default':1,'range':(0,5),'interval':0.5,'label':'line width'},
                'alpha':{'type':'scale','default':0.7,'range':(0,1),'interval':0.1,'label':'alpha'},
                'title':{'type':'entry','default':'','width':25},
                'xlabel':{'type':'entry','default':'','width':25},
                'ylabel':{'type':'entry','default':'','width':25},
                'subplots':{'type':'checkbutton','default':0,'label':'multiple subplots'},
                'colormap':{'type':'combobox','default':'jet','items':colormaps}
                }
        return

    def applyOptions(self):
        """Set the options"""

        kwds = {}
        for i in self.opts:
            kwds[i] = self.tkvars[i].get()
        self.kwds = kwds
        plt.rc("font", family=kwds['font'], size=kwds['fontsize'])
        return

    def apply(self):
        self.applyOptions()
        if self.callback != None:
            self.callback()
        return

    def showDialog(self, parent, callback=None):
        """Auto create tk vars, widgets for corresponding options and
           and return the frame"""

        dialog, self.tkvars = dialogFromOptions(parent, self.opts, self.groups)
        self.applyOptions()
        return dialog

    def getFonts(self):
        """Get the current list of system fonts"""

        import tkinter.font
        fonts = set(list(tkinter.font.families()))
        fonts = sorted(list(fonts))
        return fonts

class MPL3DOptions(object):
    """Class to provide 3D matplotlib options"""

    kinds = ['scatter', 'bar', 'bar3d', 'surface', 'contour']

    def __init__(self):
        """Setup variables"""

        fonts = self.getFonts()
        self.groups = grps = {'styles':['font','fontsize','colormap','alpha'],
                            'formats':['kind','subplots','title','xlabel','ylabel']}

        opts = self.opts = {'font':{'type':'combobox','default':'Arial','items':fonts},
                'fontsize':{'type':'scale','default':12,'range':(5,40),'interval':1,'label':'font size'},
                'kind':{'type':'combobox','default':'scatter','items':self.kinds,'label':'kind'},
                'alpha':{'type':'scale','default':0.7,'range':(0,1),'interval':0.1,'label':'alpha'},
                'title':{'type':'entry','default':'','width':25},
                'xlabel':{'type':'entry','default':'','width':25},
                'ylabel':{'type':'entry','default':'','width':25},
                'subplots':{'type':'checkbutton','default':0,'label':'multiple subplots'},
                'colormap':{'type':'combobox','default':'jet','items': colormaps}
                 }

    def applyOptions(self):
        """Set the options"""

        kwds = {}
        for i in self.opts:
            kwds[i] = self.tkvars[i].get()
        self.kwds = kwds
        plt.rc("font", family=kwds['font'], size=kwds['fontsize'])
        return

    def showDialog(self, parent, callback=None):
        """Auto create tk vars, widgets for corresponding options and
           and return the frame"""

        dialog, self.tkvars = dialogFromOptions(parent, self.opts, self.groups)
        self.applyOptions()
        return dialog

    def getFonts(self):
        """Get the current list of system fonts"""

        import tkinter.font
        fonts = set(list(tkinter.font.families()))
        fonts = sorted(list(fonts))
        return fonts

class FactorPlotter(object):
    """Provides seaborn factor plots"""
    def __init__(self, data=None):
        """Setup variables"""
        self.data=data
        #self.setDefaultStyle()
        self.groups = grps = {'formats':['style','despine','palette'],
                'factors':['kind','hue','x']}
        styles = ['darkgrid', 'whitegrid', 'dark', 'white', 'ticks']
        kinds = ['auto','bar']
        palettes = ['Spectral','cubehelix','hls','hot','coolwarm','copper',
                    'winter','spring','summer','autumn','Greys','Blues','Reds',
                    'Set1','Accent']
        if self.data is not None:
            cols = self.data.columns

        self.opts = {'style': {'type':'combobox','default':'whitegrid','items':styles},
                     'despine': {'type':'checkbutton','default':0,'label':'despine'},
                     'palette': {'type':'combobox','default':'Spectral','items':palettes},
                     'kind': {'type':'combobox','default':'auto','items':kinds},
                     'x': {'type':'combobox','default':'auto','items':kinds},
                     'hue': {'type':'combobox','default':'auto','items':kinds},
                        }
        return

    def showDialog(self, parent, callback=None):
        """Auto create tk vars, widgets for corresponding options and
           and return the frame"""

        dialog, self.tkvars = dialogFromOptions(parent, self.opts, self.groups)
        #self.applyOptions()
        return dialog

    def applyOptions(self):
        """Set the options"""
        import seaborn as sns
        kwds = {}
        for i in self.opts:
            kwds[i] = self.tkvars[i].get()
        self.kwds = kwds
        sns.set_style(self.kwds['style'])
        if self.kwds['despine'] == 1:
            sns.despine()
        return

    def setDefaultStyle(self):
        import seaborn as sns
        sns.set_style("ticks", {'axes.facecolor': '#F7F7F7','legend.frameon': True})
        sns.set_context("paper", rc={'legend.fontsize':18,'xtick.labelsize':14,
                        'ytick.labelsize':16,'axes.labelsize':20,'axes.titlesize':20})
        return
