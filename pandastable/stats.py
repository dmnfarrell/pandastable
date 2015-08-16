#!/usr/bin/env python
"""
    Module for stats and fitting classes.

    Created June 2015
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
from collections import OrderedDict
import operator
from .dialogs import *

try:
    import statsmodels.formula.api as smf
    import statsmodels.api as sm
except:
    print('no statsmodel')

class StatsViewer(Frame):
    """Provides a frame for model viewing interaction"""

    def __init__(self, table, parent=None):

        self.parent = parent
        self.table = table
        self.table.sv = self
        if self.parent != None:
            Frame.__init__(self, parent)
            self.main = self.master
        else:
            self.main = Toplevel()
            self.master = self.main
            self.main.title('Model Fitting App')
            self.main.protocol("WM_DELETE_WINDOW", self.quit)
        self.setupGUI()
        return

    def setupGUI(self):
        """Add GUI elements"""

        ctrls = Frame(self.main)
        ctrls.pack(fill=BOTH,expand=1)
        self.formulavar = StringVar()
        self.formulavar.set('b ~ a')
        Label(ctrls,text='formula:').pack(side=TOP,fill=BOTH)
        e = Entry(ctrls, textvariable=self.formulavar, font="Courier 13 bold")
        e.pack(side=TOP,fill=BOTH,expand=1)
        bf = Frame(ctrls, padding=2)
        bf.pack(side=TOP,fill=BOTH)
        self.plotvar = StringVar()
        self.plotvar.set('fitline')
        c = Combobox(bf, values=['fitline','abline','leverage'],
                       textvariable=self.plotvar)
        c.pack(side=LEFT,fill=Y,expand=1)

        b = Button(bf, text="Fit", command=self.doFit)
        b.pack(side=LEFT,fill=X,expand=1)
        b = Button(bf, text="Summary", command=self.summary)
        b.pack(side=LEFT,fill=X,expand=1)
        b = Button(bf, text="Close", command=self.quit)
        b.pack(side=LEFT,fill=X,expand=1)
        return

    def guessFormula(self):
        """Suggest a start formula"""

        return

    def doFit(self):
        """Do model fit on selected subset of rows. Will only use
        the currently selected rows for the fit and can plot the remainder
        versus a fit line."""

        df = self.table.getSelectedDataFrame()
        df = df.convert_objects(convert_numeric='force')
        formula = self.formulavar.get()
        self.model = mod = smf.ols(formula=formula, data=df)
        self.fit = fit = mod.fit(subset=df[:20])

        pf = self.table.pf
        fig = pf.fig
        fig.clear()
        ax = fig.add_subplot(111)
        kwds = pf.mplopts.kwds

        kind = self.plotvar.get()
        if kind == 'fitline':
            self.plotFit(fit, df, ax, **kwds)
        elif kind == 'leverage':
            from statsmodels.graphics.regressionplots import plot_leverage_resid2
            plot_leverage_resid2(fit, ax=ax)
        elif kind == 'abline':
            sm.graphics.abline_plot(model_results=fit, ax=ax)
        #sm.graphics.plot_fit(fit, "b", ax=ax)
        fig.canvas.draw()
        return

    def plotFit(self, fit, df, ax, **kwds):

        import pylab as plt
        X1 = pd.DataFrame({'a': np.linspace(df.a.min(), df.a.max(), 100)})
        X1 = sm.add_constant(X1)
        #predict out of sample
        y1 = fit.predict(X1)
        #confidence intervals
        from statsmodels.sandbox.regression.predstd import wls_prediction_std
        prstd, iv_l, iv_u = wls_prediction_std(fit)

        cmap = plt.cm.get_cmap(kwds['colormap'])
        ax.scatter(df.a, df.b, alpha=0.7, color=cmap(.2))  # Plot the raw data
        ax.set_xlabel("a")
        ax.set_ylabel("b")
        #print (X1)
        x1 = X1['a']
        ax.plot(x1, y1, 'r', lw=2, alpha=0.9, color=cmap(.8))
        print(fit.params)
        i=0.95
        for p in fit.params:
            ax.text(0.8,i, round(p,3), ha='right', va='top', transform=ax.transAxes)
            i-=.05
        #ax.plot(df.a, iv_u, 'r--')
        #ax.plot(x1, iv_l, 'r--')
        #plt.tight_layout()
        return

    def summary(self):
        """Fit summary"""

        s = self.fit.summary()
        from .dialogs import SimpleEditor
        w = Toplevel(self.parent)
        w.grab_set()
        w.transient(self)
        ed = SimpleEditor(w, height=25, font='monospace 10')
        ed.pack(in_=w, fill=BOTH, expand=Y)
        ed.text.insert(END, s)
        return

    def _import_statsmodels(self):
        """Try to import statsmodels. If not installed return false"""
        try:
            import statsmodels
            return 1
        except:
            print('statsmodels not installed')
            return 0

    def _checkNumeric(self, df):
        x = df.convert_objects()._get_numeric_data()
        if x.empty==True:
            return False

    def updateData(self):
        """Update data widgets"""

        df = self.table.model.df
        return

    def quit(self):
        #self.main.withdraw()
        self.table.sv = None
        self.main.destroy()
        return
