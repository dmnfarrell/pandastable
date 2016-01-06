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
from pandas.tools import plotting
import matplotlib as mpl
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.mlab import griddata
#import matplotlib.animation as animation
from collections import OrderedDict
import operator
from .dialogs import *
from . import util, images

colormaps = sorted(m for m in plt.cm.datad if not m.endswith("_r"))

class PlotViewer(Frame):
    """Provides a frame for figure canvas and MPL settings"""

    def __init__(self, table, parent=None, layout='horizontal'):

        self.parent = parent
        self.table = table
        self.table.pf = self #opaque ref
        self.mode = 0
        if self.parent != None:
            Frame.__init__(self, parent)
            self.main = self.master
        else:
            self.main = Toplevel()
            self.master = self.main
            self.main.title('Plot Viewer')
            self.main.protocol("WM_DELETE_WINDOW", self.quit)
        self.layout = layout
        if layout == 'horizontal':
            self.orient = VERTICAL
        else:
            self.orient = HORIZONTAL
        self.mplopts = MPLBaseOptions(parent=self)
        self.mplopts3d = MPL3DOptions(parent=self)
        self.setupGUI()
        return

    def refreshLayout(self):
        """Redraw plot tools dialogs"""

        self.m.destroy()
        if self.layout == 'horizontal':
            self.layout = 'vertical'
            self.orient = HORIZONTAL
        else:
            self.layout = 'horizontal'
            self.orient = VERTICAL

        self.setupGUI()
        self.replot()
        return

    def setupGUI(self):
        """Add GUI elements"""

        self.m = PanedWindow(self.main, orient=self.orient)
        self.m.pack(fill=BOTH,expand=1)
        #frame for figure
        self.plotfr = Frame(self.m)
        #add it to the panedwindow
        self.fig, self.canvas = addFigure(self.plotfr)
        self.ax = self.fig.add_subplot(111)

        self.m.add(self.plotfr, weight=2)
        #frame for others
        self.ctrlfr = Frame(self.main)
        self.m.add(self.ctrlfr)
        bf = Frame(self.ctrlfr, padding=2)
        bf.pack(side=TOP,fill=BOTH)
        if self.layout == 'vertical':
            side = TOP
        else:
            side = LEFT

        addButton(bf, 'Plot', self.replot, images.plot(),
                  'plot current data', side=side, compound="left", width=20)
        addButton(bf, 'Apply Options', self.applyPlotoptions, images.refresh(),
                  'refresh plot with current options', side=side, compound="left", width=20)
        addButton(bf, 'Clear', self.clear, images.plot_clear(),
                  'clear plot', side=side, compound="left")
        addButton(bf, 'Hide', self.hide, images.cross(),
                  'hide plot frame', side=side)
        addButton(bf, 'Vertical', self.refreshLayout, images.tilehorizontal(),
                  'change plot tools orientation', side=side)

        #add button toolbar
        self.dpivar = IntVar()
        self.dpivar.set(80)
        Label(bf, text='save dpi:').pack(side=LEFT,fill=X,padx=2)
        e = Entry(bf, textvariable=self.dpivar, width=5)
        e.pack(side=LEFT,padx=2)

        if self.layout == 'vertical':
            sf = VerticalScrolledFrame(self.ctrlfr,width=100,height=1050)
            sf.pack(side=TOP,fill=BOTH)
            self.nb = Notebook(sf.interior,width=100,height=1050)
        else:
            self.nb = Notebook(self.ctrlfr,height=190)

        self.nb.bind('<<NotebookTabChanged>>', self.setMode)
        self.nb.pack(side=TOP,fill=BOTH,expand=1)

        #add plotter tool dialogs
        w1 = self.mplopts.showDialog(self.nb, layout=self.layout)
        self.nb.add(w1, text='base plot options', sticky='news')
        #reload tkvars again from stored kwds variable
        self.mplopts.updateFromOptions()
        #self.mplopts.applyOptions()
        w2 = self.mplopts3d.showDialog(self.nb,layout=self.layout)
        self.nb.add(w2, text='3D plot', sticky='news')
        self.mplopts3d.updateFromOptions()
        #self.mplopts3d.applyOptions()
        if self.mode == 1:
            self.nb.select(w2)
        return

    def setMode(self, evt=None):
        """Set the plot mode based on selected tab"""
        self.mode = self.nb.index(self.nb.select())
        return

    def replot(self):
        """Re-plot from parent table when selected data changed"""

        self.data = self.table.getPlotData()
        self.applyPlotoptions()
        return

    def clear(self):
        """Clear plot"""

        self.fig.clear()
        self.ax = None
        self.canvas.draw()
        self.table.plotted=None
        return

    def applyPlotoptions(self):
        """Apply the current plotter/options"""

        if self.mode == 0:
            self.mplopts.applyOptions()
        elif self.mode == 1:
            self.mplopts3d.applyOptions()

        mpl.rcParams['savefig.dpi'] = self.dpivar.get()
        self.plotCurrent()
        return

    def plotCurrent(self):
        """Plot current data"""

        if self.mode == 0:
            #self.setFigure()
            self.plot2D()
        elif self.mode == 1:
            self.plot3D()
        return

    def _checkNumeric(self, df):
        """Get only numeric data that can be plotted"""

        x = df._convert()._get_numeric_data()
        #x = df.apply(pd.to_numeric, args=('coerce',))
        #x = df.select_dtypes(include=['int','float','int64'])
        if x.empty==True:
            return False

    def plot2D(self):
        """Draw method for current data. Relies on pandas plot functionality
           if possible. There is some temporary code here to make sure only the valid
           plot options are passed for each plot kind."""

        if not hasattr(self, 'data'):
            return
        #needs cleaning up
        valid = {'line': ['alpha', 'colormap', 'grid', 'legend', 'linestyle',
                          'linewidth', 'marker', 'subplots', 'rot', 'logx', 'logy',
                          'sharey', 'kind'],
                    'scatter': ['alpha', 'grid', 'linewidth', 'marker', 'subplots', 's',
                            'legend', 'colormap','sharey', 'logx', 'logy', 'use_index'],
                    'pie': ['colormap','legend'],
                    'hexbin': ['alpha', 'colormap', 'grid', 'linewidth'],
                    'bootstrap': ['grid'],
                    'bar': ['alpha', 'colormap', 'grid', 'legend', 'linewidth', 'subplots',
                            'sharey',  'logy', 'stacked', 'rot', 'kind'],
                    'barh': ['alpha', 'colormap', 'grid', 'legend', 'linewidth', 'subplots',
                            'stacked', 'rot', 'kind', 'logx'],
                    'histogram': ['alpha', 'linewidth','grid','stacked','subplots','colormap',
                             'sharey','rot','bins', 'logx', 'logy'],
                    'heatmap': ['colormap','rot'],
                    'area': ['alpha','colormap','grid','linewidth','legend','stacked',
                             'kind','rot','logx'],
                    'density': ['alpha', 'colormap', 'grid', 'legend', 'linestyle',
                                 'linewidth', 'marker', 'subplots', 'rot', 'kind'],
                    'boxplot': ['rot', 'grid', 'logy','colormap','alpha','linewidth'],
                    'scatter_matrix':['alpha', 'linewidth', 'marker', 'grid', 's'],
                    'contour': ['colormap','alpha']
                    }

        data = self.data
        if self._checkNumeric(data) == False:
            self.showWarning('no numeric data to plot')
            return
        #get all options from the mpl options object
        kwds = self.mplopts.kwds
        kind = kwds['kind']
        table = kwds['table']
        by = kwds['by']
        by2 = kwds['by2']
        errorbars = kwds['errorbars']
        useindex = kwds['use_index']

        #valid kwd args for this plot type
        kwargs = dict((k, kwds[k]) for k in valid[kind] if k in kwds)
        self.fig.clear()
        self.ax = ax = self.fig.add_subplot(111)

        if by != '':
            #groupby needs to be handled per group so we can add all the axes to
            #our figure correctly
            if by not in data.columns:
                self.showWarning('the grouping column must be in selected data')
                return
            if by2 != '' and by2 in data.columns:
                by = [by,by2]
            g = data.groupby(by)
            if len(g) >25:
                self.showWarning('too many groups to plot')
                return
            self.ax.set_visible(False)
            kwargs['subplots'] = False
            size = len(g)
            nrows = round(np.sqrt(size),0)
            ncols = np.ceil(size/nrows)
            i=1
            for n,df in g:
                ax = self.fig.add_subplot(nrows,ncols,i)
                kwargs['legend'] = False #remove axis legends
                d=df.drop(by,1) #remove grouping columns
                self._doplot(d, ax, kind, False,  errorbars, useindex, kwargs)
                ax.set_title(n)
                handles, labels = ax.get_legend_handles_labels()
                i+=1
            self.fig.legend(handles, labels, loc='center right')#, bbox_to_anchor=(1, 0.5))
            self.fig.subplots_adjust(left=0.1, right=0.9, top=0.9,
                                     bottom=0.1, hspace=.25)
            axs = self.fig.get_axes()
            #self.canvas.draw()
        else:
            axs = self._doplot(data, ax, kind, kwds['subplots'], errorbars,
                               useindex, kwargs)
        if table == True:
            from pandas.tools.plotting import table
            if self.table.child != None:
                tabledata = self.table.child.model.df
                table(axs, np.round(tabledata, 2),
                      loc='upper right', colWidths=[0.1 for i in tabledata.columns])

        #set options general for all plot types
        self.setFigureOptions(axs, kwds)
        scf = 12/kwds['fontsize']
        try:
            self.fig.tight_layout()
            self.fig.subplots_adjust(top=0.9)
        except:
            self.fig.subplots_adjust(left=0.1, right=0.9, top=0.89,
                                     bottom=0.1, hspace=.4/scf, wspace=.2/scf)
            print ('tight_layout failed')
        #plt.xkcd()
        self.canvas.draw()
        return

    def setFigureOptions(self, axs, kwds):
        """Set axis wide options such as ylabels, title"""

        if type(axs) is np.ndarray:
            self.ax = axs.flat[0]
        elif type(axs) is list:
            self.ax = axs[0]
        self.fig.suptitle(kwds['title'], fontsize=kwds['fontsize']*1.2)
        for ax in self.fig.axes:
            if kwds['xlabel'] != '':
                ax.set_xlabel(kwds['xlabel'])
            if kwds['ylabel'] != '':
                ax.set_ylabel(kwds['ylabel'])
            ax.xaxis.set_visible(kwds['showxlabels'])
            ax.yaxis.set_visible(kwds['showylabels'])
        return

    def _doplot(self, data, ax, kind, subplots, errorbars, useindex, kwargs):
        """Do core plotting"""

        cols = data.columns
        if kind == 'line':
            data = data.sort_index()
        rows = int(round(np.sqrt(len(data.columns)),0))
        if len(data.columns) == 1 and kind not in ['pie']:
            kwargs['subplots'] = 0
        if 'colormap' in kwargs:
            cmap = plt.cm.get_cmap(kwargs['colormap'])
        if subplots == 0:
            layout = None
        else:
            layout=(rows,-1)
        if errorbars == True:
            yerr = data[data.columns[1::2]]
            data = data[data.columns[0::2]]
            yerr.columns = data.columns
        else:
            yerr = None
        if kind == 'bar':
            if len(data) > 50:
                ax.get_xaxis().set_visible(False)
            if len(data) > 300:
                self.showWarning('too many bars to plot')
                return
        if kind == 'scatter':
            axs = self.scatter(data, ax, **kwargs)
            if kwargs['sharey'] == 1:
                lims = self.fig.axes[0].get_ylim()
                for a in self.fig.axes:
                    a.set_ylim(lims)
        elif kind == 'boxplot':
            axs = data.boxplot(ax=ax, rot=kwargs['rot'], grid=kwargs['grid'],
                               patch_artist=True)
            lw = kwargs['linewidth']
            plt.setp(axs['boxes'], color='black', lw=lw)
            plt.setp(axs['whiskers'], color='black', lw=lw)
            plt.setp(axs['fliers'], color='black', marker='+', lw=lw)
            clr = cmap(0.5)
            for patch in axs['boxes']:
                patch.set_facecolor(clr)
            #boxplot won't accept required kwargs?
            if kwargs['logy'] == 1:
                ax.set_yscale('log')
        elif kind == 'histogram':
            bins = int(kwargs['bins'])
            axs = data.plot(kind='hist',layout=layout, ax=ax, **kwargs)
        elif kind == 'heatmap':
            axs = self.heatmap(data, ax, kwargs)
        elif kind == 'bootstrap':
            axs = plotting.bootstrap_plot(data)
        elif kind == 'scatter_matrix':
            axs = pd.scatter_matrix(data, ax=ax, **kwargs)
        elif kind == 'hexbin':
            x = cols[0]
            y = cols[1]
            axs = data.plot(x,y,ax=ax,kind='hexbin',gridsize=20,**kwargs)
        elif kind == 'contour':
            x = data.values[:,0]
            y = data.values[:,1]
            z = data.values[:,2]
            xi = np.linspace(x.min(), x.max())
            yi = np.linspace(y.min(), y.max())
            zi = griddata(x, y, z, xi, yi, interp='linear')
            cs = ax.contour(xi,yi,zi,15,linewidths=0.5,colors='k')
            cs = ax.contourf(xi,yi,zi,15,cmap=cmap)
            self.fig.colorbar(cs,ax=ax)
            axs = ax
        elif kind == 'pie':
            if kwargs['legend'] == True:
                lbls=None
            else:
                lbls = list(data.index)
            axs = data.plot(ax=ax,kind='pie', labels=lbls, layout=layout,
                            autopct='%1.1f%%', subplots=True, **kwargs)
            if lbls == None:
                axs[0].legend(labels=data.index)
        elif kind == 'barh':
            lw = kwargs['linewidth']
            axs = data.plot(ax=ax, layout=layout, xerr=yerr, **kwargs)
        else:
            if useindex == False:
                x=data.columns[0]
                data.set_index(x,inplace=True)
                data=data.sort()
            if len(data.columns) == 0:
                msg = "Not enough data.\nIf 'use index' is off select at least 2 columns"
                self.showWarning(msg)
                return
            axs = data.plot(ax=ax, layout=layout, yerr=yerr, **kwargs)
        return axs

    def scatter(self, df, ax, alpha=0.8, marker='o', **kwds):
        """A custom scatter plot rather than the pandas one. By default this
        plots the first column selected versus the others"""

        #print (kwds)
        if len(df.columns)<2:
            return
        df = df._get_numeric_data()
        cols = df.columns
        x = df[cols[0]]
        s=1
        plots = len(cols)
        cmap = plt.cm.get_cmap(kwds['colormap'])
        lw = kwds['linewidth']
        if marker == '':
            marker = 'o'
        if kwds['subplots'] == 1:
            size=plots-1
            nrows = round(np.sqrt(size),0)
            ncols = np.ceil(size/nrows)
            print (plots,nrows,ncols)
            self.fig.clear()
        for i in range(s,plots):
            y = df[cols[i]]
            c = cmap(float(i)/(plots))
            if marker in ['x','+']:
                ec=c
            else:
                ec='black'
            if kwds['subplots'] == 1:
                ax = self.fig.add_subplot(nrows,ncols,i)
            ax.scatter(x, y, marker=marker, alpha=alpha, linewidth=lw,
                       s=kwds['s'], edgecolors=ec, facecolor=c)
            ax.set_xlabel(cols[0])
            if kwds['logx'] == 1:
                ax.set_xscale('log')
            if kwds['logy'] == 1:
                ax.set_yscale('log')
            if kwds['grid'] == 1:
                ax.grid()
            if kwds['subplots'] == 1:
                ax.set_title(cols[i])
        if kwds['legend'] == 1 and kwds['subplots'] == 0:
            ax.legend(cols[1:])
        return ax

    def heatmap(self, df, ax, kwds):
        """Plot heatmap"""

        X = df._get_numeric_data()
        hm = ax.pcolor(X, cmap=kwds['colormap'])
        self.fig.colorbar(hm, ax=ax)
        ax.set_xticks(np.arange(0.5, len(X.columns)))
        ax.set_yticks(np.arange(0.5, len(X.index)))
        ax.set_xticklabels(X.columns, minor=False)
        ax.set_yticklabels(X.index, minor=False)
        ax.set_ylim(0, len(X.index))
        return

    def prepareData(self, x,y,z):
        """Prepare 3 1D data for plotting in 3D"""

        '''x = np.random.uniform(-2,2,50)
        y = np.random.uniform(-2,2,50)
        z = x*np.exp(-x**2-y**2)
        # define grid.
        xi = np.linspace(-2.1,2.1,100)
        yi = np.linspace(-2.1,2.1,100)'''

        xi = np.linspace(x.min(), x.max())
        yi = np.linspace(y.min(), y.max())
        zi = griddata(x, y, z, xi, yi, interp='linear')
        X, Y = np.meshgrid(xi, yi)
        return X,Y,zi

    def getView(self):
        ax = self.ax
        if hasattr(ax,'azim'):
            azm=ax.azim
            ele=ax.elev
            dst=ax.dist
        else:
            return None,None,None
        return azm,ele,dst

    def plot3D(self):
        """3D plots"""

        if not hasattr(self, 'data'):
            return
        kwds = self.mplopts3d.kwds
        data = self.data
        x = data.values[:,0]
        y = data.values[:,1]
        z = data.values[:,2]
        azm,ele,dst = self.getView()

        self.fig.clear()
        ax = self.ax = Axes3D(self.fig)
        rstride=kwds['rstride']
        cstride=kwds['cstride']
        lw = kwds['linewidth']
        alpha = kwds['alpha']

        if kwds['kind'] == 'scatter':
            self.scatter3D(data, ax, kwds)
        elif kwds['kind'] == 'bar':
            self.bar3D(data, ax, kwds)
        elif kwds['kind'] == 'contour':
            xi = np.linspace(x.min(), x.max())
            yi = np.linspace(y.min(), y.max())
            zi = griddata(x, y, z, xi, yi, interp='linear')
            surf = ax.contour(xi, yi, zi, rstride=rstride, cstride=cstride,
                              cmap=kwds['colormap'], alpha=alpha,
                              linewidth=lw, antialiased=True)
        elif kwds['kind'] == 'wireframe':
            X,Y,zi = self.prepareData(x,y,z)
            w = ax.plot_wireframe(X, Y, zi, rstride=rstride, cstride=cstride,
                                  linewidth=lw)
        elif kwds['kind'] == 'surface':
            X,Y,zi = self.prepareData(x,y,z)
            surf = ax.plot_surface(X, Y, zi, rstride=rstride, cstride=cstride,
                                   cmap=kwds['colormap'], alpha=alpha,
                                   linewidth=lw)

            self.fig.colorbar(surf, shrink=0.5, aspect=5)
        if kwds['points'] == True:
            self.scatter3D(data, ax, kwds)
        self.fig.suptitle(kwds['title'])
        self.ax.set_xlabel(kwds['xlabel'])
        self.ax.set_ylabel(kwds['ylabel'])
        self.ax.set_zlabel(kwds['zlabel'])
        if azm!=None:
            self.ax.azim = azm
            self.ax.elev = ele
            self.ax.dist = dst
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
        """3D scatter plot"""

        #print (kwds['by'])
        data = data._get_numeric_data()
        l = len(data.columns)
        if l<3: return
        X = data.values
        cmap = plt.cm.get_cmap(kwds['colormap'])
        x = X[:,0]
        for i in range(1,l-1):
            y = X[:,i]
            z = X[:,i+1]
            c = cmap(float(i)/(l))
            ax.scatter(x, y, z, edgecolor='black', color=c, linewidth=.5)
        return

    def updateData(self):
        """Update data widgets"""

        df = self.table.model.df
        self.mplopts.update(df)
        if hasattr(self, 'factorplotter'):
            self.factorplotter.update(df)
        return

    def savePlot(self):
        """Save the current plot"""

        ftypes = ['png','jpg','tif','pdf','eps','ps','svg']
        d = MultipleValDialog(title='Save plot',
                                initialvalues=('',[80,120,150,300,600],ftypes),
                                labels=('File name:','dpi:','type:'),
                                types=('filename','combobox','combobox'),
                                parent = self)
        if d.result == None:
            return
        fname = d.results[0]
        dpi = int(d.results[1])
        ftype = d.results[2]
        filename = fname + '.'+ ftype
        self.fig.savefig(filename, dpi=dpi)
        self.currfilename = filename
        return

    def showWarning(self, s='plot error', ax=None):
        if ax==None:
            ax=self.fig.gca()
        ax.clear()
        ax.text(.5, .5, s,transform=self.ax.transAxes,
                       horizontalalignment='center', color='blue', fontsize=16)
        self.canvas.draw()
        return

    def hide(self):
        self.m.pack_forget()
        return

    def show(self):
        self.m.pack(fill=BOTH,expand=1)
        return

    def quit(self):
        #self.main.withdraw()
        self.table.pf = None
        self.main.destroy()
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
    kinds = ['line', 'scatter', 'bar', 'barh', 'pie', 'histogram', 'boxplot',
             'heatmap', 'area', 'hexbin', 'contour', 'scatter_matrix', 'density']
    defaultfont = 'monospace'

    def __init__(self, parent=None):
        """Setup variables"""

        self.parent = parent
        df = self.parent.table.model.df
        datacols = list(df.columns)
        datacols.insert(0,'')
        fonts = getFonts()
        grps = {'data':['bins','by','by2','use_index','errorbars'],
                'styles':['font','colormap','alpha','grid'],
                'sizes':['fontsize','s','linewidth'],
                'formats':['kind','marker','linestyle','stacked','subplots'],
                'axes':['showxlabels','showylabels','sharex','sharey','logx','logy','rot'],
                'labels':['title','xlabel','ylabel','legend','table']}
        order = ['data','formats','sizes','axes','styles','labels']
        self.groups = OrderedDict(sorted(grps.items()))
        opts = self.opts = {'font':{'type':'combobox','default':self.defaultfont,'items':fonts},
                'fontsize':{'type':'scale','default':12,'range':(5,40),'interval':1,'label':'font size'},
                'marker':{'type':'combobox','default':'','items':self.markers},
                'linestyle':{'type':'combobox','default':'-','items':self.linestyles},
                's':{'type':'scale','default':30,'range':(1,500),'interval':10,'label':'marker size'},
                'grid':{'type':'checkbutton','default':0,'label':'show grid'},
                'logx':{'type':'checkbutton','default':0,'label':'log x'},
                'logy':{'type':'checkbutton','default':0,'label':'log y'},
                'rot':{'type':'entry','default':0, 'label':'xlabel angle'},
                'use_index':{'type':'checkbutton','default':1,'label':'use index'},
                'errorbars':{'type':'checkbutton','default':0,'label':'use errorbars'},
                'showxlabels':{'type':'checkbutton','default':1,'label':'x tick labels'},
                'showylabels':{'type':'checkbutton','default':1,'label':'y tick labels'},
                'sharex':{'type':'checkbutton','default':0,'label':'share x'},
                'sharey':{'type':'checkbutton','default':0,'label':'share y'},
                'legend':{'type':'checkbutton','default':1,'label':'legend'},
                'table':{'type':'checkbutton','default':0,'label':'show table'},
                'kind':{'type':'combobox','default':'line','items':self.kinds,'label':'kind'},
                'stacked':{'type':'checkbutton','default':0,'label':'stacked'},
                'linewidth':{'type':'scale','default':1.5,'range':(0,5),'interval':0.5,'label':'line width'},
                'alpha':{'type':'scale','default':0.7,'range':(0,1),'interval':0.1,'label':'alpha'},
                'title':{'type':'entry','default':'','width':20},
                'xlabel':{'type':'entry','default':'','width':20},
                'ylabel':{'type':'entry','default':'','width':20},
                'subplots':{'type':'checkbutton','default':0,'label':'multiple subplots'},
                'colormap':{'type':'combobox','default':'Spectral','items':colormaps},
                'bins':{'type':'entry','default':20,'width':10},
                'by':{'type':'combobox','items':datacols,'label':'group by','default':''},
                'by2':{'type':'combobox','items':datacols,'label':'group by 2','default':''}
                }
        return

    def applyOptions(self):
        """Set the plot kwd arguments from the tk variables"""

        kwds = {}
        for i in self.opts:
            if self.opts[i]['type'] == 'listbox':
                items = self.widgets[i].curselection()
                kwds[i] = [self.widgets[i].get(j) for j in items]
                #print (items, kwds[i])
            else:
                kwds[i] = self.tkvars[i].get()
        self.kwds = kwds
        size = kwds['fontsize']
        plt.rc("font", family=kwds['font'], size=size)
        plt.rc('legend', fontsize=size-1)
        return

    def apply(self):
        self.applyOptions()
        if self.callback != None:
            self.callback()
        return

    def showDialog(self, parent, callback=None, layout='horizontal'):
        """Auto create tk vars, widgets for corresponding options and
           and return the frame"""

        dialog, self.tkvars, self.widgets = dialogFromOptions(parent,
                                                              self.opts, self.groups,
                                                              layout=layout)
        return dialog

    def update(self, df):
        """Update data widget(s) when dataframe changes"""

        if util.check_multiindex(df.columns) == 1:
            cols = list(df.columns.get_level_values(0))
        else:
            cols = list(df.columns)
        cols += ''
        self.widgets['by']['values'] = cols
        self.widgets['by2']['values'] = cols
        return

    def updateFromOptions(self, kwds=None):
        """Update all widget tk vars using plot kwds dict"""

        if kwds != None:
            self.kwds = kwds
        elif hasattr(self, 'kwds'):
            kwds = self.kwds
        else:
            return
        for i in kwds:
            self.tkvars[i].set(kwds[i])
        return

class MPL3DOptions(MPLBaseOptions):
    """Class to provide 3D matplotlib options"""

    kinds = ['scatter', 'bar', 'contour', 'wireframe', 'surface']
    defaultfont = 'monospace'

    def __init__(self, parent=None):
        """Setup variables"""

        self.parent = parent
        df = self.parent.table.model.df
        datacols = list(df.columns)
        datacols.insert(0,'')
        fonts = getFonts()
        modes = ['parametric','(x,y)->z']
        self.groups = grps = {'formats':['kind','mode','rstride','cstride','points'],
                             'styles':['colormap','alpha','font'],
                             'labels':['title','xlabel','ylabel','zlabel'],
                             'sizes':['fontsize','linewidth']}
        self.groups = OrderedDict(sorted(grps.items()))
        opts = self.opts = {'font':{'type':'combobox','default':self.defaultfont,'items':fonts},
                'fontsize':{'type':'scale','default':12,'range':(5,40),'interval':1,'label':'font size'},
                'kind':{'type':'combobox','default':'scatter','items':self.kinds,'label':'kind'},
                'alpha':{'type':'scale','default':0.8,'range':(0,1),'interval':0.1,'label':'alpha'},
                'linewidth':{'type':'scale','default':.5,'range':(0,4),'interval':0.1,'label':'linewidth'},
                'title':{'type':'entry','default':'','width':25},
                'xlabel':{'type':'entry','default':'','width':25},
                'ylabel':{'type':'entry','default':'','width':25},
                'zlabel':{'type':'entry','default':'','width':25},
                'colormap':{'type':'combobox','default':'jet','items': colormaps},
                'rstride':{'type':'entry','default':2,'width':25},
                'cstride':{'type':'entry','default':2,'width':25},
                'points':{'type':'checkbutton','default':0,'label':'show points'},
                'mode':{'type':'combobox','default':'(x,y)->z','items': modes},
                 }


def addFigure(parent, figure=None, resize_callback=None):
    """Create a tk figure and canvas in the parent frame"""

    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
    from matplotlib.figure import Figure

    if figure == None:
        figure = Figure(figsize=(5,4), dpi=80, facecolor='white')

    canvas = FigureCanvasTkAgg(figure, master=parent, resize_callback=resize_callback)
    canvas.show()
    canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)
    canvas.get_tk_widget().configure(highlightcolor='gray75',
                                   highlightbackground='gray75')
    toolbar = NavigationToolbar2TkAgg(canvas, parent)
    toolbar.update()
    canvas._tkcanvas.pack(side=TOP, fill=BOTH, expand=1)
    return figure, canvas

def getFonts():
     """Get the current list of system fonts"""

     import matplotlib.font_manager
     l = matplotlib.font_manager.get_fontconfig_fonts()
     fonts = [matplotlib.font_manager.FontProperties(fname=fname).get_name() for fname in l]
     fonts = list(set(fonts))
     fonts.sort()
     #f = matplotlib.font_manager.FontProperties(family='monospace')
     #print (matplotlib.font_manager.findfont(f))
     return fonts