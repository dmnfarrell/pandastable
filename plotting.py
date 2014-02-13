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
import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
#import matplotlib.animation as animation
import tkinter.font

class PlotFrame(Frame):
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
        self.addFigure(self.main)
        self.nb = Notebook(self.main)
        self.nb.pack(side=TOP,fill=BOTH)
        self.mplopts = MPLoptions()
        w1 = self.mplopts.showDialog(self.nb, callback=self.redraw)
        self.nb.add(w1, text='plot options')      
        #self.anim = animator(self.nb, plotframe=self)
        #self.nb.add(self.anim, text='animation')
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

    def redraw(self):
        """Draw method for current data. There is some messy code here
           to interpret some of the plot types so that the kwds can be
           passed for each plot kind. This could be changed later."""

        if not hasattr(self, 'data'):
            return    
        omitkwds = {'line':['stacked','s'],
                    'scatter':['stacked'],
                    'bar':['marker','linestyle','s'],
                    'barh':['marker','linestyle','s'],
                    'heatmap':[], 'density':['stacked','s'], 'boxplot':[],
                    '3d':[]
                    }
        data = self.data
        kwds = self.mplopts.kwds
        kind = kwds['kind']
        ignore = omitkwds[kind]
        ignore.extend(['font','fontsize'])
        for i in ignore:
            if i in kwds:
                del kwds[i]
        if len(data.columns)==1:
            kwds['subplots']=0
      
        self.fig.clear()
        self.ax = ax = self.fig.add_subplot(111)
        #self.ax.clear()
        ax = self.ax
        if kind == 'bar':
            if len(data) > 50:
                self.ax.get_xaxis().set_visible(False)
        if kind == 'scatter':
            kwds['x'] = data.columns[0]
            kwds['y'] = data.columns[1]
            if kwds['marker'] == '':
                kwds['marker'] = 'o'
            print (data.columns)
        if kind == 'boxplot':
            data.boxplot(ax=ax)           
        elif kind == 'histogram': 
            data.hist(ax=ax) 
        elif kind == 'heatmap':
            hm = ax.pcolor(data, cmap=kwds['colormap'])
            self.fig.colorbar(hm, ax=ax)
            #ax.set_yticks(np.arange(0.5, len(data.index), 1), data.index)
            #ax.set_xticks(np.arange(0.5, len(data.columns), 1), data.columns)
            #ax.set_aspect('equal') 
        else:
            data.plot(ax=ax, **kwds)
        self.canvas.draw()
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
    legend_positions = ['best', 'upper left','upper center','upper right',
                         'center left','center','center right'
                         'lower left','lower center','lower right']
    kinds = ['line', 'scatter', 'bar', 'barh', 'boxplot', 'histogram', 'heatmap', 'density']
    
    def __init__(self):
        """Setup variables"""
  
        fonts = self.getFonts()
        opts = self.opts = {'font':{'type':'combobox','default':'Arial','items':fonts},
                'fontsize':{'type':'scale','default':12,'range':(5,40),'interval':1,'label':'font size'},
                'marker':{'type':'combobox','default':'','items':self.markers},
                'linestyle':{'type':'combobox','default':'-','items':self.linestyles},
                's':{'type':'scale','default':30,'range':(5,500),'interval':10,'label':'marker size'},
                'grid':{'type':'checkbutton','default':0,'label':'show grid'},
                #'logx':{'type':'checkbutton','default':0,'label':'log x-axis'},
                #'logy':{'type':'checkbutton','default':0,'label':'log y-axis'},
                'legend':{'type':'checkbutton','default':1,'label':'legend'},
                'kind':{'type':'combobox','default':'line','items':self.kinds,'label':'kind'},
                'stacked':{'type':'checkbutton','default':0,'label':'stacked bar'},
                'linewidth':{'type':'scale','default':1,'range':(0,5),'interval':0.5,'label':'line width'},
                'alpha':{'type':'scale','default':0.7,'range':(0,1),'interval':0.1,'label':'alpha'},
                'title':{'type':'entry','default':''},
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

        grps = {'styles':['font','colormap','alpha','grid','legend'],
                'sizes':['fontsize','s','linewidth'],
                'format':['kind','marker','linestyle','stacked','subplots'],
                'general':['title']}
        c=0
        for g in ['format','sizes','styles','general']:
            frame = LabelFrame(dialog, text=g)
            frame.grid(row=0,column=c,sticky='news')
            row=0; col=0
            for i in grps[g]:
                w=None
                opt = opts[i]               
                if opt['type'] == 'entry':             
                    Label(frame,text=i).pack() 
                    w = Entry(frame,textvariable=tkvars[i])                               
                elif opt['type'] == 'checkbutton': 
                    w = Checkbutton(frame,text=opt['label'],
                             variable=tkvars[i])       
                elif opt['type'] == 'combobox':
                    Label(frame,text=i).pack()           
                    w = Combobox(frame, values=opt['items'],
                             textvariable=tkvars[i])                    
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

        row=3
        def close():
            dialog.destroy()        
        #frame=Frame(dialog)
        #frame.grid(row=0,column=c,sticky='nwes')
        b = Button(frame, text="Apply", command=self.apply)
        b.pack(side=TOP,fill=X,expand=1)
        c=Button(frame,text='Close', command=close)
        c.pack(side=TOP,fill=X,expand=1)
        return dialog

    def getFonts(self):
        """Get the current list of system fonts"""
        fonts = set(list(tkinter.font.families()))
        fonts = sorted(list(fonts))
        return fonts


