#!/usr/bin/env python
"""
    Module for pandastable plotting classes .

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

from __future__ import absolute_import, division, print_function
try:
    from tkinter import *
    from tkinter.ttk import *
except:
    from Tkinter import *
    from ttk import *
import types
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
        self.mode = 'Base Options'
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
        self.labelopts = AnnotationOptions(parent=self)
        self.layoutopts = PlotLayoutOptions(parent=self)
        self.gridaxes = {}
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
                  'clear plot', side=side)
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
        #plot layout
        self.playoutvar = IntVar()
        self.playoutvar.set(0)
        cb = Checkbutton(bf,text='use grid layout', variable=self.playoutvar)
        cb.pack(side=LEFT)

        if self.layout == 'vertical':
            sf = VerticalScrolledFrame(self.ctrlfr,width=100,height=1050)
            sf.pack(side=TOP,fill=BOTH)
            self.nb = Notebook(sf.interior,width=100,height=1050)
        else:
            self.nb = Notebook(self.ctrlfr,height=195)

        self.nb.bind('<<NotebookTabChanged>>', self.setMode)
        self.nb.pack(side=TOP,fill=BOTH,expand=0)

        #add plotter tool dialogs
        w1 = self.mplopts.showDialog(self.nb, layout=self.layout)
        self.nb.add(w1, text='Base Options', sticky='news')
        #reload tkvars again from stored kwds variable
        self.mplopts.updateFromOptions()
        w2 = self.labelopts.showDialog(self.nb,layout=self.layout)
        self.nb.add(w2, text='Annotation', sticky='news')
        self.labelopts.updateFromOptions()
        w3 = self.layoutopts.showDialog(self.nb,layout=self.layout)
        self.nb.add(w3, text='Grid Layout', sticky='news')
        w4 = self.mplopts3d.showDialog(self.nb,layout=self.layout)
        self.nb.add(w4, text='3D Plot', sticky='news')
        self.mplopts3d.updateFromOptions()

        if self.mode == '3D Plot':
            self.nb.select(w2)

        def onpick(event):
            print(event)
        #self.fig.canvas.mpl_connect('pick_event', onpick)
        #self.fig.canvas.mpl_connect('button_release_event', onpick)
        from . import handlers
        dr = handlers.DragHandler(self)
        dr.connect()
        return

    def setMode(self, evt=None):
        """Set the plot mode based on selected tab"""
        #self.mode = self.nb.index(self.nb.select())
        self.mode = self.nb.tab(self.nb.select(), "text")
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
        self.gridaxes = {}
        return

    def applyPlotoptions(self):
        """Apply the current plotter/options"""

        if self.mode == '3D Plot':
            self.mplopts3d.applyOptions()
        else:
            self.mplopts.applyOptions()
            self.labelopts.applyOptions()

        mpl.rcParams['savefig.dpi'] = self.dpivar.get()
        self.plotCurrent()
        return

    def plotCurrent(self):
        """Plot current data"""

        if self.mode == '3D Plot':
            self.plot3D()
        else:
            self.plot2D()
        return

    def _checkNumeric(self, df):
        """Get only numeric data that can be plotted"""

        x = df.convert_objects()._get_numeric_data()
        #x = df.apply(pd.to_numeric, args=('coerce',))
        #x = df.select_dtypes(include=['int','float','int64'])
        if x.empty==True:
            return False

    def _initFigure(self):
        """Clear figure or add a new axis to existing layout"""

        from matplotlib.gridspec import GridSpec
        layout = self.playoutvar.get()
        #plot layout should be tracked by plotlayoutoptions
        self.layoutopts.applyOptions()
        kwds = self.layoutopts.kwds

        if layout == 0:
            #default layout is just a single axis
            self.fig.clear()
            self.gridaxes={}
            self.ax = self.fig.add_subplot(111)
        else:
            rows = kwds['rows']
            cols = kwds['cols']
            r = kwds['row']-1
            c = kwds['col']-1
            colspan = kwds['colspan']
            rowspan = kwds['rowspan']
            top = float(kwds['top'])
            bottom = float(kwds['bottom'])
            gs = GridSpec(rows,cols,top=top,bottom=bottom,left=0.1,right=0.9)
            name = str(r+1)+','+str(c+1)
            if name in self.gridaxes:
                ax = self.gridaxes[name]
                if ax in self.fig.axes:
                    self.fig.delaxes(ax)
            self.ax = self.fig.add_subplot(gs[r:r+rowspan,c:c+colspan])
            self.gridaxes[name] = self.ax
            #update the axes widget
            self.layoutopts.updateAxesList()
        return

    def removeSubplot(self):
        """Remove a specific axis from the grid layout"""

        axname = self.layoutopts.axeslistvar.get()
        ax = self.gridaxes[axname]
        if ax in self.fig.axes:
            self.fig.delaxes(ax)
        del self.gridaxes[axname]
        self.canvas.show()
        self.layoutopts.updateAxesList()
        self.layoutopts.axeslistvar.set('')
        return

    def setSubplotTitle(self):
        """Set a subplot title if using grid layout"""

        axname = self.layoutopts.axeslistvar.get()
        if not axname in self.gridaxes:
            return
        ax = self.gridaxes[axname]
        label = simpledialog.askstring("Subplot title",
                                      "Title:",initialvalue='',
                                       parent=self.parent)
        if label:
            ax.set_title(label)
            self.canvas.show()
        return

    def plot2D(self):
        """Plot method for current data. Relies on pandas plot functionality
           if possible. There is some temporary code here to make sure only the valid
           plot options are passed for each plot kind."""

        if not hasattr(self, 'data'):
            return
        #needs cleaning up
        valid = {'line': ['alpha', 'colormap', 'grid', 'legend', 'linestyle',
                          'linewidth', 'marker', 'subplots', 'rot', 'logx', 'logy',
                          'sharey', 'kind'],
                    'scatter': ['alpha', 'grid', 'linewidth', 'marker', 'subplots', 's',
                            'legend', 'colormap','sharey', 'logx', 'logy', 'use_index','c',
                            'cscale','colorbar','bw'],
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
                    'contour': ['linewidth','colormap','alpha'],
                    'imshow': ['colormap','alpha']
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
        bw = kwds['bw']

        #valid kwd args for this plot type
        kwargs = dict((k, kwds[k]) for k in valid[kind] if k in kwds)
        #initialise the figure
        self._initFigure()
        ax = self.ax
        #plt.style.use('dark_background')

        if by != '':
            #groupby needs to be handled per group so we can add all the axes to
            #our figure correctly
            if by not in data.columns:
                self.showWarning('the grouping column must be in selected data')
                return
            if by2 != '' and by2 in data.columns:
                by = [by,by2]
            g = data.groupby(by)
            if len(g) > 30:
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
                d = df.drop(by,1) #remove grouping columns
                self._doplot(d, ax, kind, False,  errorbars, useindex,
                              bw=bw, kwargs=kwargs)
                ax.set_title(n)
                handles, labels = ax.get_legend_handles_labels()
                i+=1

            #single plot
            '''cmap = plt.cm.get_cmap(kwargs['colormap'])
            colors = []
            names = []
            for n,df in g:
                ax = self.ax
                kwargs['legend'] = False #remove axis legends
                d = df.drop(by,1) #remove grouping columns
                self._doplot(d, ax, kind, False,  errorbars, useindex,
                              bw=bw, kwargs=kwargs)
                names.append(n)
            handles, labels = ax.get_legend_handles_labels()
            print (labels)
            labels = [l+' '+n for l in labels]
            i+=1'''

            self.fig.legend(handles, labels, loc='center right')
            self.fig.subplots_adjust(left=0.1, right=0.9, top=0.9,
                                     bottom=0.1, hspace=.25)
            axs = self.fig.get_axes()
            #self.ax = axs[0]
        else:
            axs = self._doplot(data, ax, kind, kwds['subplots'], errorbars,
                               useindex, bw=bw, kwargs=kwargs)
        if table == True:
            from pandas.tools.plotting import table
            if self.table.child != None:
                tabledata = self.table.child.model.df
                table(axs, np.round(tabledata, 2),
                      loc='upper right', colWidths=[0.1 for i in tabledata.columns])

        #set options general for all plot types
        #annotation optons are separate
        lkwds = self.labelopts.kwds.copy()
        lkwds.update(kwds)
        self.setFigureOptions(axs, lkwds)
        scf = 12/kwds['fontsize']
        try:
            self.fig.tight_layout()
            self.fig.subplots_adjust(top=0.9)
        except:
            self.fig.subplots_adjust(left=0.1, right=0.9, top=0.89,
                                     bottom=0.1, hspace=.4/scf, wspace=.2/scf)
            print ('tight_layout failed')
        #redraw annotations
        self.labelopts.redraw()
        self.canvas.draw()
        return

    def setFigureOptions(self, axs, kwds):
        """Set axis wide options such as ylabels, title"""

        if type(axs) is np.ndarray:
            self.ax = axs.flat[0]
        elif type(axs) is list:
            self.ax = axs[0]
        self.fig.suptitle(kwds['title'], fontsize=kwds['fontsize']*1.2)
        layout = self.playoutvar.get()
        if layout == 0:
            for ax in self.fig.axes:
                self.setAxisLabels(ax, kwds)
        else:
            self.setAxisLabels(self.ax, kwds)
        return

    def setAxisLabels(self, ax, kwds):
        """Set a plots axis labels"""

        if kwds['xlabel'] != '':
            ax.set_xlabel(kwds['xlabel'])
        if kwds['ylabel'] != '':
            ax.set_ylabel(kwds['ylabel'])
        ax.xaxis.set_visible(kwds['showxlabels'])
        ax.yaxis.set_visible(kwds['showylabels'])
        return

    def _doplot(self, data, ax, kind, subplots, errorbars, useindex, bw, kwargs):
        """Core plotting method"""

        kwargs = kwargs.copy()
        cols = data.columns
        if kind == 'line':
            data = data.sort_index()
        rows = int(round(np.sqrt(len(data.columns)),0))
        if len(data.columns) == 1 and kind not in ['pie']:
            kwargs['subplots'] = 0
        if 'colormap' in kwargs:
            cmap = plt.cm.get_cmap(kwargs['colormap'])
        else:
            cmap = None
        #change some things if we are plotting in b&w
        styles = []
        if bw == True and kind not in ['pie','heatmap']:
            cmap = None
            kwargs['color'] = 'k'
            kwargs['colormap'] = None
            styles = ["-","--","-.",":"]
            if 'linestyle' in kwargs:
                del kwargs['linestyle']

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
            xi,yi,zi = self.contourData(data)
            cs = ax.contour(xi,yi,zi,15,linewidths=.5,colors='k')
            #plt.clabel(cs,fontsize=9)
            cs = ax.contourf(xi,yi,zi,15,cmap=cmap)
            self.fig.colorbar(cs,ax=ax)
            axs = ax
        elif kind == 'imshow':
            xi,yi,zi = self.contourData(data)
            im = ax.imshow(zi, interpolation="nearest",
                           cmap=cmap, alpha=kwargs['alpha'])
            self.fig.colorbar(im,ax=ax)
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
            #line, bar and area plots
            if useindex == False:
                x=data.columns[0]
                data.set_index(x,inplace=True)
                data=data.sort()
            if len(data.columns) == 0:
                msg = "Not enough data.\nIf 'use index' is off select at least 2 columns"
                self.showWarning(msg)
                return
            #adjust colormap to avoid white lines
            if cmap != None:
                cmap = util.adjustColorMap(cmap, 0.15,1.0)
                del kwargs['colormap']
            axs = data.plot(ax=ax, layout=layout, yerr=yerr, style=styles, cmap=cmap,
                             **kwargs)
        return axs

    def scatter(self, df, ax, alpha=0.8, marker='o', **kwds):
        """A custom scatter plot rather than the pandas one. By default this
        plots the first column selected versus the others"""

        #print (kwds)
        if len(df.columns)<2:
            return
        df = df._get_numeric_data()
        cols = list(df.columns)
        x = df[cols[0]]
        s=1
        cmap = plt.cm.get_cmap(kwds['colormap'])
        lw = kwds['linewidth']
        c = kwds['c']
        cscale = kwds['cscale']
        grid = kwds['grid']
        bw = kwds['bw']
        if cscale == 'log':
            norm = mpl.colors.LogNorm()
        else:
            norm = None
        if c != '' and c in cols:
            if len(cols)>2:
                cols.remove(c)
            c = df[c]
        else:
            c = None
        plots = len(cols)
        if marker == '':
            marker = 'o'
        if kwds['subplots'] == 1:
            size = plots-1
            nrows = round(np.sqrt(size),0)
            ncols = np.ceil(size/nrows)
            self.fig.clear()
        if c is not None:
            colormap = kwds['colormap']
        else:
            colormap = None
            c=[]

        for i in range(s,plots):
            y = df[cols[i]]
            ec = 'black'
            if bw == True:
                clr = 'white'
                colormap = None
            else:
                clr = cmap(float(i)/(plots))
            if colormap != None:
                clr=None
            if marker in ['x','+'] and bw == False:
                ec = clr

            if kwds['subplots'] == 1:
                ax = self.fig.add_subplot(nrows,ncols,i)
            scplt = ax.scatter(x, y, marker=marker, alpha=alpha, linewidth=lw, c=c,
                       s=kwds['s'], edgecolors=ec, facecolor=clr, cmap=colormap,
                       norm=norm, label=cols[i], picker=True)
            ax.set_xlabel(cols[0])
            if kwds['logx'] == 1:
                ax.set_xscale('log')
            if kwds['logy'] == 1:
                ax.set_yscale('log')
                ax.set_ylim((y.min()+1e-6,y.max()))
            if grid == 1:
                ax.grid(True)
            if kwds['subplots'] == 1:
                ax.set_title(cols[i])
            if colormap is not None and kwds['colorbar'] == True:
                self.fig.colorbar(scplt, ax=ax)
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

    def contourData(self, data):
        """Get data for contour plot"""

        x = data.values[:,0]
        y = data.values[:,1]
        z = data.values[:,2]
        xi = np.linspace(x.min(), x.max())
        yi = np.linspace(y.min(), y.max())
        zi = griddata(x, y, z, xi, yi, interp='linear')
        return xi,yi,zi

    def meshData(self, x,y,z):
        """Prepare 1D data for plotting in the form (x,y)->Z"""

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
        kind = kwds['kind']
        mode = kwds['mode']
        rstride = kwds['rstride']
        cstride = kwds['cstride']
        lw = kwds['linewidth']
        alpha = kwds['alpha']
        cmap = kwds['colormap']

        if kind == 'scatter':
            self.scatter3D(data, ax, kwds)
        elif kind == 'bar':
            self.bar3D(data, ax, kwds)
        elif kind == 'contour':
            xi = np.linspace(x.min(), x.max())
            yi = np.linspace(y.min(), y.max())
            zi = griddata(x, y, z, xi, yi, interp='linear')
            surf = ax.contour(xi, yi, zi, rstride=rstride, cstride=cstride,
                              cmap=kwds['colormap'], alpha=alpha,
                              linewidth=lw, antialiased=True)
        elif kind == 'wireframe':
            if mode == '(x,y)->z':
                X,Y,zi = self.meshData(x,y,z)
            else:
                X,Y,zi = x,y,z
            w = ax.plot_wireframe(X, Y, zi, rstride=rstride, cstride=cstride,
                                  linewidth=lw)
        elif kind == 'surface':
            X,Y,zi = self.meshData(x,y,z)
            surf = ax.plot_surface(X, Y, zi, rstride=rstride, cstride=cstride,
                                   cmap=cmap, alpha=alpha,
                                   linewidth=lw)
            cb = self.fig.colorbar(surf, shrink=0.5, aspect=5)
            surf.set_clim(vmin=zi.min(), vmax=zi.max())
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
        """3D bar plot"""

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

        lw = kwds['linewidth']
        alpha = kwds['alpha']
        s = kwds['s']
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
            ax.scatter(x, y, z, edgecolor='black', color=c, linewidth=lw,
                       alpha=alpha, s=s)
        return

    def updateData(self):
        """Update data widgets"""

        df = self.table.model.df
        self.mplopts.update(df)
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
        """Show warning message in the plot window"""

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

class TkOptions(object):
    """Class to generate tkinter widget dialog for dict of options"""
    def __init__(self, parent=None):
        """Setup variables"""

        self.parent = parent
        df = self.parent.table.model.df
        return

    def applyOptions(self):
        """Set the plot kwd arguments from the tk variables"""

        kwds = {}
        for i in self.opts:
            if not i in self.tkvars:
                continue
            #print (i, self.opts[i]['type'], self.widgets[i])
            if self.opts[i]['type'] == 'listbox':
                items = self.widgets[i].curselection()
                kwds[i] = [self.widgets[i].get(j) for j in items]
            elif self.opts[i]['type'] == 'scrolledtext':
                kwds[i] = self.widgets[i].get('1.0',END)
            else:
                kwds[i] = self.tkvars[i].get()
        self.kwds = kwds
        return

    def apply(self):
        self.applyOptions()
        if self.callback != None:
            self.callback()
        return

    def showDialog(self, parent, layout='horizontal'):
        """Auto create tk vars, widgets for corresponding options and
           and return the frame"""

        dialog, self.tkvars, self.widgets = dialogFromOptions(parent,
                                                              self.opts, self.groups,
                                                              layout=layout)
        return dialog

    def updateFromOptions(self, kwds=None):
        """Update all widget tk vars using plot kwds dict"""

        if kwds != None:
            self.kwds = kwds
        elif hasattr(self, 'kwds'):
            kwds = self.kwds
        else:
            return
        for i in kwds:
            if i in self.tkvars and self.tkvars[i] != None:
                self.tkvars[i].set(kwds[i])
        return

class MPLBaseOptions(TkOptions):
    """Class to provide a dialog for matplotlib options and returning
        the selected prefs"""

    markers = ['','o','.','^','v','>','<','s','+','x','p','d','h','*']
    linestyles = ['-','--','-.',':','steps']
    kinds = ['line', 'scatter', 'bar', 'barh', 'pie', 'histogram', 'boxplot',
             'heatmap', 'area', 'hexbin', 'contour', 'imshow', 'scatter_matrix', 'density']
    defaultfont = 'monospace'

    def __init__(self, parent=None):
        """Setup variables"""

        self.parent = parent
        df = self.parent.table.model.df
        datacols = list(df.columns)
        datacols.insert(0,'')
        fonts = util.getFonts()
        scales = ['linear','log']
        grps = {'data':['bins','by','by2','use_index','errorbars'],
                'styles':['font','marker','linestyle','alpha'],
                'sizes':['fontsize','s','linewidth'],
                'formats':['kind','stacked','subplots','grid','legend','table'],
                'axes':['showxlabels','showylabels','sharex','sharey','logx','logy','rot'],
                'styles colors':['colormap','bw','c','cscale','colorbar']}
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
                'c':{'type':'combobox','items':datacols,'label':'color by value','default':''},
                'cscale':{'type':'combobox','items':scales,'label':'color scale','default':'linear'},
                'colorbar':{'type':'checkbutton','default':0,'label':'show colorbar'},
                'bw':{'type':'checkbutton','default':0,'label':'black & white'},
                'showxlabels':{'type':'checkbutton','default':1,'label':'x tick labels'},
                'showylabels':{'type':'checkbutton','default':1,'label':'y tick labels'},
                'sharex':{'type':'checkbutton','default':0,'label':'share x'},
                'sharey':{'type':'checkbutton','default':0,'label':'share y'},
                'legend':{'type':'checkbutton','default':1,'label':'legend'},
                'table':{'type':'checkbutton','default':0,'label':'show table'},
                'kind':{'type':'combobox','default':'line','items':self.kinds,'label':'plot type'},
                'stacked':{'type':'checkbutton','default':0,'label':'stacked'},
                'linewidth':{'type':'scale','default':1.5,'range':(0.1,8),'interval':0.1,'label':'line width'},
                'alpha':{'type':'scale','default':0.8,'range':(0,1),'interval':0.1,'label':'alpha'},
                'subplots':{'type':'checkbutton','default':0,'label':'multiple subplots'},
                'colormap':{'type':'combobox','default':'Spectral','items':colormaps},
                'bins':{'type':'entry','default':20,'width':10},
                'by':{'type':'combobox','items':datacols,'label':'group by','default':''},
                'by2':{'type':'combobox','items':datacols,'label':'group by 2','default':''}
                }
        self.kwds = {}
        return

    def applyOptions(self):
        """Set the plot kwd arguments from the tk variables"""

        TkOptions.applyOptions(self)
        size = self.kwds['fontsize']
        plt.rc("font", family=self.kwds['font'], size=size)
        plt.rc('legend', fontsize=size-1)
        return

    def update(self, df):
        """Update data widget(s) when dataframe changes"""

        if util.check_multiindex(df.columns) == 1:
            cols = list(df.columns.get_level_values(0))
        else:
            cols = list(df.columns)
        cols += ''
        self.widgets['by']['values'] = cols
        self.widgets['by2']['values'] = cols
        self.widgets['c']['values'] = cols
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
        fonts = util.getFonts()
        modes = ['parametric','(x,y)->z']
        self.groups = grps = {'formats':['kind','mode','rstride','cstride','points'],
                             'styles':['colormap','alpha','font'],
                             'labels':['title','xlabel','ylabel','zlabel'],
                             'sizes':['fontsize','linewidth','s']}
        self.groups = OrderedDict(sorted(grps.items()))
        opts = self.opts = {'font':{'type':'combobox','default':self.defaultfont,'items':fonts},
                'fontsize':{'type':'scale','default':12,'range':(5,40),'interval':1,'label':'font size'},
                'kind':{'type':'combobox','default':'scatter','items':self.kinds,'label':'kind'},
                'alpha':{'type':'scale','default':0.8,'range':(0,1),'interval':0.1,'label':'alpha'},
                'linewidth':{'type':'scale','default':.5,'range':(0,4),'interval':0.1,'label':'linewidth'},
                's':{'type':'scale','default':30,'range':(1,500),'interval':10,'label':'marker size'},
                'title':{'type':'entry','default':'','width':20},
                'xlabel':{'type':'entry','default':'','width':20},
                'ylabel':{'type':'entry','default':'','width':20},
                'zlabel':{'type':'entry','default':'','width':20},
                'colormap':{'type':'combobox','default':'jet','items': colormaps},
                'rstride':{'type':'entry','default':2,'width':20},
                'cstride':{'type':'entry','default':2,'width':20},
                'points':{'type':'checkbutton','default':0,'label':'show points'},
                'mode':{'type':'combobox','default':'(x,y)->z','items': modes},
                 }
        self.kwds = {}
        return

class PlotLayoutOptions(TkOptions):
    def __init__(self, parent=None):
        """Setup variables"""

        self.parent = parent
        self.groups = grps = {'grid':['rows','cols','top','bottom'],
                             'current axis':['row','col','rowspan','colspan'],
                             #'other':['clear'],
                             }
        self.groups = OrderedDict(sorted(grps.items()))
        opts = self.opts = {
                'rows':{'type':'entry','default':2,'width':10,'label':'size (rows)'},
                'cols':{'type':'entry','default':2,'width':10,'label':'size (cols)'},
                #'clear':{'type':'checkbutton','default':1,'label':'clear on grid update',
                #         'tooltip':'clear figure when the grid is altered'},
                'row':{'type':'entry','default':1,'width':10},
                'col':{'type':'entry','default':1,'width':10},
                'rowspan':{'type':'entry','default':1,'width':10},
                'colspan':{'type':'entry','default':1,'width':10},
                'top':{'type':'entry','default':.9,'width':10},
                'bottom':{'type':'entry','default':.1,'width':10},
                }
        self.kwds = {}
        return

    def showDialog(self, parent, layout='horizontal'):
        """Override because we need to add custom bits"""

        dialog, self.tkvars, self.widgets = dialogFromOptions(parent,
                                                              self.opts, self.groups,
                                                              layout=layout)
        self.main = dialog
        self.subplotsWidget()
        return dialog

    def subplotsWidget(self):
        """Custom dialog to allow selection/removal of individual subplots"""

        frame = LabelFrame(self.main, text='subplots')
        v = self.axeslistvar = StringVar()
        v.set('')
        axes = []
        self.axeslist = Combobox(frame, values=axes,
                        textvariable=v,width=14)
        Label(frame,text='plot list:').pack()
        self.axeslist.pack(fill=BOTH,pady=2)
        b = Button(frame, text='remove axis', command=self.parent.removeSubplot)
        b.pack(fill=X,pady=2)
        b = Button(frame, text='set title', command=self.parent.setSubplotTitle)
        b.pack(fill=X,pady=2)
        frame.pack(side=LEFT,fill=Y)
        return

    def updateAxesList(self):
        """Update axes list"""

        axes = list(self.parent.gridaxes.keys())
        self.axeslist['values'] = axes
        return

class AnnotationOptions(TkOptions):
    """This class also provides custom tools for adding items to the plot"""
    def __init__(self, parent=None):
        """Setup variables"""

        from matplotlib import colors
        import six
        colors = list(six.iteritems(colors.cnames))
        colors = sorted([c[0] for c in colors])
        fillpatterns = ['-', '+', 'x', '\\', '*', 'o', 'O', '.']
        bstyles = ['square','round','round4','circle','rarrow','larrow','sawtooth']
        fonts = util.getFonts()
        defaultfont = 'monospace'
        fontweights = ['normal','bold','heavy','light','ultrabold','ultralight']
        alignments = ['left','center','right']

        self.parent = parent
        self.groups = grps = {'global labels':['title','xlabel','ylabel','zlabel'],
                              'textbox': ['boxstyle','facecolor','linecolor','rotate'],
                              'textbox format': ['fontsize','font','fontweight','align'],
                              'text to add': ['text']
                             }
        self.groups = OrderedDict(sorted(grps.items()))
        opts = self.opts = {
                'title':{'type':'entry','default':'','width':20},
                'xlabel':{'type':'entry','default':'','width':20},
                'ylabel':{'type':'entry','default':'','width':20},
                'zlabel':{'type':'entry','default':'','width':20},
                'facecolor':{'type':'combobox','default':'white','items': colors},
                'linecolor':{'type':'combobox','default':'black','items': colors},
                'fill':{'type':'combobox','default':'-','items': fillpatterns},
                'rotate':{'type':'scale','default':0,'range':(-180,180),'interval':1,'label':'rotate'},
                'boxstyle':{'type':'combobox','default':'square','items': bstyles},
                'text':{'type':'scrolledtext','default':'','width':20},
                'align':{'type':'combobox','default':'center','items': alignments},
                'font':{'type':'combobox','default':defaultfont,'items':fonts},
                'fontsize':{'type':'scale','default':12,'range':(4,50),'interval':1,'label':'font size'},
                'fontweight':{'type':'combobox','default':'normal','items': fontweights}
                }
        self.kwds = {}
        #used to store annotations
        self.textboxes = {}
        return

    def showDialog(self, parent, layout='horizontal'):
        """Override because we need to add custom widgets"""

        dialog, self.tkvars, self.widgets = dialogFromOptions(parent,
                                                              self.opts, self.groups,
                                                              layout=layout)
        self.main = dialog
        self.addWidgets()
        return dialog

    def addWidgets(self):
        """Custom dialogs for manually adding annotation items like text"""

        frame = LabelFrame(self.main, text='add objects')
        v = self.objectvar = StringVar()
        v.set('textbox')
        w = Combobox(frame, values=['textbox'],#'arrow'],
                         textvariable=v,width=14)
        Label(frame,text='add object').pack()
        w.pack(fill=BOTH,pady=2)
        self.coordsvar = StringVar()
        self.coordsvar.set('data')
        w = Combobox(frame, values=['data','axes fraction','figure fraction'],
                         textvariable=self.coordsvar,width=14)
        Label(frame,text='coord system').pack()
        w.pack(fill=BOTH,pady=2)

        b = Button(frame, text='Create', command=self.addObject)
        b.pack(fill=X,pady=2)
        b = Button(frame, text='Clear', command=self.clear)
        b.pack(fill=X,pady=2)
        frame.pack(side=LEFT,fill=Y)
        return

    def clear(self):
        """Clear annotations"""
        self.textboxes = {}
        self.parent.replot()
        return

    def addObject(self):
        """Add an annotation object"""

        o = self.objectvar.get()
        if o == 'textbox':
            self.addTextBox()
        elif o == 'arrow':
            self.addArrow()
        return

    def addTextBox(self, kwds=None, key=None):
        """Add a text annotation and store it using key"""

        import matplotlib.patches as patches
        from matplotlib.text import OffsetFrom

        self.applyOptions()
        if kwds == None:
            kwds = self.kwds
            kwds['xycoords'] = self.coordsvar.get()
        fig = self.parent.fig
        #ax = self.parent.ax
        ax = fig.get_axes()[0]
        canvas = self.parent.canvas
        text = kwds['text'].strip('\n')
        fc = kwds['facecolor']
        ec = kwds['linecolor']
        bstyle = kwds['boxstyle']
        style = "%s,pad=.2" %bstyle
        fontsize = kwds['fontsize']
        font = mpl.font_manager.FontProperties(family=kwds['font'],
                            weight=kwds['fontweight'])
        bbox_args = dict(boxstyle=bstyle, fc=fc, ec=ec, lw=1, alpha=0.9)
        arrowprops = dict(arrowstyle="-|>", connectionstyle="arc3")

        xycoords = kwds['xycoords']
        #if previously drawn will have xy values
        if 'xy' in kwds:
            xy = kwds['xy']
            #print (text, xycoords, xy)
        else:
            xy=(.1, .8)
            xycoords='axes fraction'

        an = ax.annotate(text, xy=xy, xycoords=xycoords,
                   ha=kwds['align'], va="center",
                   size=fontsize,
                   fontproperties=font, rotation=kwds['rotate'],
                   #arrowprops=arrowprops,
                   #xytext=(xy[0]+.2,xy[1]),
                   #textcoords='offset points',
                   zorder=10,
                   bbox=bbox_args)
        an.draggable()
        if key == None:
            import uuid
            key = str(uuid.uuid4().fields[0])
        #need to add the unique id to the annotation
        #so it can be tracked in event handler
        an._id = key
        if key not in self.textboxes:
            self.textboxes[key] = kwds
            print(kwds)
        #canvas.show()
        canvas.draw()
        return

    def addArrow(self, kwds=None, key=None):
        """Add line/arrow"""

        fig = self.parent.fig
        canvas = self.parent.canvas
        ax = fig.get_axes()[0]
        ax.arrow(0.2, 0.2, 0.5, 0.5, fc='k', ec='k',
                 transform=ax.transAxes)
        canvas.draw()
        #self.lines.append(line)
        return

    def redraw(self):
        """Redraw all stored annotations in the right places
           after a plot update"""

        #print (self.textboxes)
        for key in self.textboxes:
            self.addTextBox(self.textboxes[key], key)
        return


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
