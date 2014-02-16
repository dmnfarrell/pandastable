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
import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
#import matplotlib.animation as animation
import tkinter.font

class PlotViewer(Frame):
    """Provides a frame for figure canvas and MPL settings"""

    def __init__(self,parent=None):

        self.parent=parent
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
        self.nb.pack(side=TOP,fill=BOTH)
        self.mplopts = MPLoptions()
        w1 = self.mplopts.showDialog(self.nb)
        self.nb.add(w1, text='plot options', sticky='news')        
        return

    def applyPlotoptions(self):
        self.mplopts.applyOptions()
        self.plot2D()
        return

    def addFigure(self, parent):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
        from matplotlib.figure import Figure
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
        self.fig.clear()
        self.ax = ax = self.fig.add_subplot(111)
        if kind == 'bar':
            if len(data) > 50:
                self.ax.get_xaxis().set_visible(False)
        if kind == 'scatter':
            self.scatter(data, ax, kwdargs)
        elif kind == 'boxplot':
            data.boxplot(ax=ax)
        elif kind == 'histogram':
            data.hist(ax=ax, **kwdargs)
        elif kind == 'heatmap':
            self.heatmap(data, ax, kwdargs)
        elif kind == 'pie':
            ax.pie(data)
        elif kind == 'scatter_matrix':
            pd.scatter_matrix(data, ax=ax, **kwdargs)
        else:
            data.plot(ax=ax, **kwdargs)
        self.fig.suptitle(kwds['title'])
        self.ax.set_xlabel(kwds['xlabel'])
        self.ax.set_ylabel(kwds['ylabel'])
        self.ax.xaxis.set_visible(kwds['showxlabels'])
        self.ax.yaxis.set_visible(kwds['showylabels'])
        #self.fig.tight_layout()
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
        if not hasattr(self, 'data'):
            return
        kwds = self.mplopts.kwds
        data = self.data
        self.fig.clear()
        ax = self.ax = Axes3D(self.fig)
        X = data.values
        if len(X[0])<3:
            zs=0
        else:
            zs=X[:,2]
        ax.scatter(X[:,0], X[:,1], zs, cmap=kwds['colormap'])
        '''i=0
        for c in data.columns:
            h = data[c]
            ax.bar(data.index, h, zs=i, zdir='y')
            i+=1'''
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

class MPLoptions(object):
    """Class to provide a dialog for matplotlib options and returning
        the selected prefs"""

    colormaps = sorted(m for m in plt.cm.datad if not m.endswith("_r"))
    markers = ['','o','.','^','v','>','<','s','+','x','p','d','h','*']
    linestyles = ['-','--','-.',':','steps']
    kinds = ['line', 'scatter', 'bar', 'barh', 'boxplot', 'histogram',
             'heatmap', 'scatter_matrix', 'density']

    def __init__(self):
        """Setup variables"""

        fonts = self.getFonts()
        self.groups = {'styles':['font','colormap','alpha','grid','legend'],
                'sizes':['fontsize','s','linewidth'],
                'formats':['kind','marker','linestyle','stacked','subplots'],
                'axes':['showxlabels','showylabels','use_index','sharey','logx','logy','rot'],
                'labels':['title','xlabel','ylabel']}
        opts = self.opts = {'font':{'type':'combobox','default':'Arial','items':fonts},
                'fontsize':{'type':'scale','default':12,'range':(5,40),'interval':1,'label':'font size'},
                'marker':{'type':'combobox','default':'','items':self.markers},
                'linestyle':{'type':'combobox','default':'-','items':self.linestyles},
                's':{'type':'scale','default':30,'range':(5,500),'interval':10,'label':'marker size'},
                'grid':{'type':'checkbutton','default':0,'label':'show grid'},
                'logx':{'type':'checkbutton','default':0,'label':'log x'},
                'logy':{'type':'checkbutton','default':0,'label':'log y'},
                'rot':{'type':'entry','default':0},
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
                'colormap':{'type':'combobox','default':'jet','items':self.colormaps}
                }
        self.tkvars = {}
        for i in opts:
            t = opts[i]['type']
            if t in ['entry','combobox']:
                var = StringVar()
            elif t in ['checkbutton']:
                var = IntVar()
            elif t in ['scale']:
                var = DoubleVar()
            var.set(opts[i]['default'])
            self.tkvars[i] = var

        self.applyOptions()
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

        opts = self.opts
        tkvars = self.tkvars
        dialog = Frame(parent)
        self.callback = callback

        c=0
        for g in ['formats','axes','sizes','styles','labels']:
            frame = LabelFrame(dialog, text=g)
            frame.grid(row=0,column=c,sticky='news')
            row=0; col=0
            for i in self.groups[g]:
                w=None
                opt = opts[i]
                if opt['type'] == 'entry':
                    if 'width' in opt:
                        w=opt['width']
                    else:
                        w=8
                    Label(frame,text=i).pack()
                    w = Entry(frame,textvariable=tkvars[i], width=w)
                elif opt['type'] == 'checkbutton':
                    w = Checkbutton(frame,text=opt['label'],
                             variable=tkvars[i])
                elif opt['type'] == 'combobox':
                    Label(frame,text=i).pack()
                    w = Combobox(frame, values=opt['items'],
                             textvariable=tkvars[i],width=15)
                    w.set(opt['default'])
                elif opt['type'] == 'scale':
                    fr,to=opt['range']
                    w = tkinter.Scale(frame,label=opt['label'],
                             from_=fr,to=to,
                             orient='horizontal',
                             resolution=opt['interval'],
                             variable=tkvars[i])
                if w != None:
                    w.pack(fill=BOTH,expand=1)
                row+=1
            c+=1

        return dialog

    def getFonts(self):
        """Get the current list of system fonts"""
        fonts = set(list(tkinter.font.families()))
        fonts = sorted(list(fonts))
        return fonts


