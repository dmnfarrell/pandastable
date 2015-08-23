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
import pylab as plt
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

        df = self.table.getSelectedDataFrame()
        formula = self.guessFormula()
        self.formulavar = StringVar()
        self.formulavar.set(formula)
        ef = Frame(self.main, padding=2)
        ef.pack(side=TOP,fill=BOTH,expand=1)
        Label(ef,text='formula:').pack(side=LEFT)
        e = Entry(ef, textvariable=self.formulavar, font="Courier 13 bold")
        e.pack(side=LEFT,fill=BOTH,expand=1)
        bf = Frame(self.main, padding=2)
        bf.pack(side=TOP,fill=BOTH)
        Label(bf,text='plot:').pack(side=LEFT)
        self.plotvar = StringVar()
        self.plotvar.set('fit line')
        c = Combobox(bf, values=['fit line','fit line2','regression plots','qqplot',
                                 'all regressors','leverage','influence'], width=15,
                       textvariable=self.plotvar)
        c.pack(side=LEFT,fill=BOTH)
        Label(bf,text='indep. variable:').pack(side=LEFT)
        self.indvar = StringVar()
        self.indvarwidget = c = Combobox(bf, values=list(df.columns), width=8,
                                     textvariable=self.indvar)
        c.pack(side=LEFT,fill=BOTH,expand=1)
        Label(bf,text='model type:').pack(side=LEFT)
        self.modelvar = StringVar()
        self.modelvar.set('OLS')
        c = Combobox(bf, values=['OLS','GLS','WLS'], width=4,
                       textvariable=self.modelvar)
        c.pack(side=LEFT,fill=BOTH,expand=1)

        bf = Frame(self.main, padding=2)
        bf.pack(side=TOP,fill=BOTH)
        b = Button(bf, text="Fit", command=self.doFit)
        b.pack(side=LEFT,fill=X,expand=1)
        b = Button(bf, text="Summary", command=self.summary)
        b.pack(side=LEFT,fill=X,expand=1)
        b = Button(bf, text="Close", command=self.quit)
        b.pack(side=LEFT,fill=X,expand=1)
        self.updateData()
        return

    def guessFormula(self):
        """Suggest a start formula"""

        df = self.table.model.df
        df = df.convert_objects(convert_numeric='force')
        cols = list(df.columns)
        if len(cols)>1:
            formula = '%s ~ %s' %(cols[1], cols[0])
        else:
            formula = None
        return formula

    def doFit(self):
        """Do model fit on selected subset of rows. Will only use
        the currently selected rows for the fit and can plot the remainder
        versus a fit line."""

        #out of sample data
        df = self.table.model.df
        #sub sample to fit
        s = self.table.getSelectedDataFrame()
        s = s.convert_objects(convert_numeric='force')
        if len(s) == 0 or len(s.columns)<1:
            return

        formula = self.formulavar.get()
        self.model = mod = smf.ols(formula=formula, data=s)
        self.fit = fit = mod.fit()

        pf = self.table.pf
        fig = pf.fig
        fig.clear()
        ax = fig.add_subplot(111)
        #plotframe options
        kwds = pf.mplopts.kwds

        kind = self.plotvar.get()
        indvar = self.indvar.get()
        if indvar == '':
            indvar = self.model.exog_names[1]
        if kind == 'fit line':
            self.plotFit(fit, df, s, indvar, ax=ax, **kwds)
        elif kind == 'fit line2':
            sm.graphics.plot_fit(fit, indvar, ax=ax)
        elif kind == 'regression plots':
            fig.clear()
            sm.graphics.plot_regress_exog(fit, indvar, fig=fig)
        elif kind == 'influence':
            sm.graphics.influence_plot(fit, ax=ax, criterion="cooks")
        elif kind == 'leverage':
            from statsmodels.graphics.regressionplots import plot_leverage_resid2
            plot_leverage_resid2(fit, ax=ax)
        elif kind =='qqplot':
            sm.graphics.qqplot(fit.resid, line='r', ax=ax)
        elif kind == 'all regressors':
            fig.clear()
            sm.graphics.plot_partregress_grid(fit, fig=fig)

        fig.tight_layout()
        fig.canvas.draw()
        return

    def plotFit(self, fit, data, sub, indvar, ax, **kwds):
        """Plot custom statsmodels fit result"""

        depvar = self.model.endog_names
        if indvar == '':
            indvar = self.model.exog_names[1]
        #df = df.sort(indvar)
        #out of sample points
        out = data.ix[-data.index.isin(sub.index)]
        print (out)
        x = sub[indvar]
        y = sub[depvar]
        xout = out[indvar]
        yout = out[depvar]
        X1 = pd.DataFrame({indvar : np.linspace(xout.min(), xout.max(), 100)})

        for i, r in data.iterrows():
            vals = np.linspace(r.min(), r.max(), 100)

        X1 = sm.add_constant(X1)
        #predict out of sample
        y1 = fit.predict(X1)

        marker=kwds['marker']
        if marker == '':
            marker='o'
        s=kwds['s']
        cmap = plt.cm.get_cmap(kwds['colormap'])
        ax.scatter(x, y, alpha=0.7, color=cmap(.2), label='fitted data',
                    marker=marker,s=s)
        ax.scatter(xout, yout, alpha=0.3, color='gray', label='out of sample',
                   marker=marker,s=s)
        ax.set_xlabel(indvar)
        ax.set_ylabel(depvar)
        #print (X1)
        x1 = X1[indvar]
        ax.plot(x1, y1, 'r', lw=2, alpha=0.9, color=cmap(.8), label='fit')
        #print(fit.params)
        i=0.05
        for k,p in fit.params.iteritems():
            ax.text(0.9,i, k+': '+ str(round(p,3)), ha='right',
                        va='top', transform=ax.transAxes)
            i+=.05
        ax.text(0.1,0.05, 'R2: '+ str(fit.rsquared), ha='left',
                        va='top', transform=ax.transAxes)
        ax.legend()
        ax.set_title('fitted versus %s' %indvar)

        #confidence intervals
        from statsmodels.sandbox.regression.predstd import wls_prediction_std
        prstd, iv_l, iv_u = wls_prediction_std(fit)
        #ax.plot(x1, iv_u, 'r--')
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

    def _doimport(self):
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
        self.indvarwidget['values'] = list(df.columns)
        return

    def quit(self):
        #self.main.withdraw()
        self.table.sv = None
        self.main.destroy()
        return
