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
import pylab as plt
from collections import OrderedDict
import operator
from .dialogs import *

try:
    import statsmodels
    import statsmodels.formula.api as smf
    import statsmodels.api as sm
    from patsy import dmatrices
except:
    print('statsmodel not installed')

class StatsViewer(Frame):
    """Provides a frame for model viewing interaction"""

    def __init__(self, table, parent=None):

        self.parent = parent
        self.table = table
        self.table.sv = self
        self.fit = None
        self.model = None
        if self.parent != None:
            Frame.__init__(self, parent)
            self.main = self.master
        else:
            self.main = Toplevel()
            self.master = self.main
            self.main.title('Model Fitting App')
            self.main.protocol("WM_DELETE_WINDOW", self.quit)
        self.setupGUI()
        self.pf = pf = self.table.pf
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

        f = Frame(self.main, padding=2)
        f.pack(side=TOP,fill=BOTH)
        Label(f,text='estimator:').pack(side=LEFT,padx=2)
        self.modelvar = StringVar()
        self.modelvar.set('ols')
        c = Combobox(f, values=['ols','gls','logit'], width=4,
                       textvariable=self.modelvar)
        c.pack(side=LEFT,fill=BOTH,expand=1)

        b = Button(f, text="Fit", command=self.doFit)
        b.pack(side=LEFT,fill=X,expand=1)
        b = Button(f, text="Summary", command=self.summary)
        b.pack(side=LEFT,fill=X,expand=1)
        b = Button(f, text="Close", command=self.quit)
        b.pack(side=LEFT,fill=X,expand=1)

        f = LabelFrame(self.main, text='plots', padding=2)
        f.pack(side=TOP,fill=BOTH)
        Label(f,text='plot type:').pack(side=LEFT)
        self.plotvar = StringVar()
        self.plotvar.set('default')
        c = Combobox(f, values=['default','predicted vs test',
                                'fit line','regression plots','qqplot',
                                'all regressors','leverage','influence'], width=15,
                       textvariable=self.plotvar)
        c.pack(side=LEFT,fill=BOTH)
        Label(f,text='plot indep. variable:').pack(side=LEFT,padx=2)
        self.indvar = StringVar()
        self.indvarwidget = c = Combobox(f, values=list(df.columns), width=8,
                                     textvariable=self.indvar)
        c.pack(side=LEFT,fill=BOTH,expand=1)
        b = Button(f, text="Plot", command=self.showPlot)
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

    def getModel(self, formula, data, est='ols'):
        """Select model to use"""

        s = self.table.multiplerowlist
        if len(s) == 0:
            sub = data.index
        else:
            sub = data.index[s]
        self.sub = sub        
        y,X = dmatrices(formula, data=data, return_type='dataframe')
        self.X = X
        self.y = y
        Xf = X.ix[sub]
        yf = y.ix[sub]

        if est == 'ols':
            #model = smf.ols(formula=formula, data=s)
            model = sm.OLS(yf, Xf)
        elif est == 'gls':
            model = sm.GLS(y, X)
        elif est == 'logit':
            model = sm.Logit(y, X)
        return model

    def doFit(self):
        """Do model fit on selected subset of rows. Will only use
        the currently selected rows for fitting."""

        data = self.table.model.df
        if len(data) == 0 or len(data.columns)<1:
            return
        self.formula = formula = self.formulavar.get()
        est = self.modelvar.get()
        try:
            self.model = mod = self.getModel(formula, data, est)
        except Exception as e:
           self.pf.showWarning(e)
           return

        self.fit = fit = mod.fit()
        self.summary()
        self.updateData()
        return

    def showPlot(self):
        """Do plots"""

        pf = self.pf
        fit = self.fit
        if fit == None:
            pf.showWarning('no fitted model')
            return
        df = self.table.model.df
        s = self.sub

        fig = pf.fig
        fig.clear()
        ax = fig.add_subplot(111)

        #plotframe options
        pf.mplopts.applyOptions()
        kwds = pf.mplopts.kwds
        kind = self.plotvar.get()
        indvar = self.indvar.get()
        if indvar == '':
            indvar = self.model.exog_names[1]

        if kind == 'default':
            if isinstance(self.model, sm.OLS) or isinstance(self.model, sm.GLS):
                self.plotRegression(fit, indvar, ax=ax, **kwds)
            elif isinstance(self.model, sm.Logit):
                self.plotLogit(fit, indvar, ax)
        elif kind == 'predicted vs test':
            self.plotPrediction(fit, ax)
        elif kind == 'fit line':
            try:
                sm.graphics.plot_fit(fit, indvar, ax=ax)
            except ValueError:
                pf.showWarning('%s is not an independent variable' %indvar,ax=ax)
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

    def plotPrediction(self, fit, ax):
        """Plot predicted vs. test"""

        sub = self.sub
        if len(sub) == 0:
            sub = X.index
        Xout = self.X.ix[~self.X.index.isin(sub)]
        yout = self.y.ix[~self.y.index.isin(sub)]
        ypred = fit.predict(Xout)
        ax.scatter(yout, ypred, alpha=0.6, edgecolor='black',
                   color='blue', lw=0.5, label='fit')
        ax.plot(ax.get_xlim(), ax.get_xlim(), ls="--", lw=2, c=".2")
        ax.set_xlabel('test')
        ax.set_ylabel('predicted')
        ax.set_title('predicted vs test data')
        import statsmodels.tools.eval_measures as em
        yt = yout.squeeze().values
        rmse = em.rmse(yt, ypred)
        ax.text(0.9,0.1,'rmse: '+ str(round(rmse,3)),ha='right',
                    va='top', transform=ax.transAxes)
        return

    def plotRegression(self, fit, indvar, ax, **kwds):
        """Plot custom statsmodels fit result for linear regression"""

        depvar = self.model.endog_names
        if indvar == '':
            indvar = self.model.exog_names[1]
        params = list(self.model.exog_names)
        if indvar not in params:
            self.pf.showWarning('chosen col is not a parameter',ax=ax)
            return

        #predict out of sample
        sub = self.sub
        if len(sub) == 0:
            sub = X.index
        Xout = self.X.ix[~self.X.index.isin(sub)]
        yout = self.y.ix[~self.y.index.isin(sub)]
        yfit = fit.predict(Xout)
        x = Xout[indvar]
        #fitted data
        Xin = self.X.ix[sub]
        yin = self.y.ix[sub]

        marker=kwds['marker']
        if marker == '':
            marker='o'
        #s=kwds['s']
        s = 10
        cmap = plt.cm.get_cmap(kwds['colormap'])
        ax.scatter(Xin[indvar], yin, alpha=0.6, color=cmap(.2), label='fitted data',
                    marker=marker,s=s)

        ax.scatter(x, yout, alpha=0.3, color='gray', label='out of sample',
                   marker=marker,s=s)
        ax.scatter(x, yfit, alpha=0.6, edgecolor='black',
                   color='red', s=s, lw=0.5, label='fit (out sample)')

        i=0.05
        for k,p in fit.params.iteritems():
            ax.text(0.9,i, k+': '+ str(round(p,3)), ha='right',
                        va='top', transform=ax.transAxes)
            i+=.05
        ax.text(0.1,0.05, 'R2: '+ str(fit.rsquared), ha='left',
                        va='top', transform=ax.transAxes)
        ax.legend()
        ax.set_title('fitted versus %s' %indvar)
        ax.set_xlabel(indvar)
        ax.set_ylabel(depvar)

        #confidence intervals
        #from statsmodels.sandbox.regression.predstd import wls_prediction_std
        #prstd, iv_l, iv_u = wls_prediction_std(fit)
        #ax.plot(x1, iv_u, 'r--')
        #ax.plot(x1, iv_l, 'r--')
        #plt.tight_layout()
        return

    def plotLogit(self, fit, indvar, ax, **kwds):
        """Plot Logit results"""

        X = self.X
        y = self.y
        #predict out of sample
        ypred = fit.predict(X)
        #ax.plot(X.index, ypred, 'bo', X.index, y, 'mo', alpha=.25)
        ax.plot(ypred, X[indvar], 'o')
        ax.set_xlabel("Predicted")
        ax.set_ylabel(indvar)
        print (fit.pred_table(0.5))
        return

    def summary(self):
        """Fit summary"""

        s = self.fit.summary()
        from .dialogs import SimpleEditor
        if not hasattr(self, 'fitinfo') or self.fitinfo == None:
            self.w = w = Toplevel(self.parent)
            def deletewin():
                self.fitinfo = None
                self.w.destroy()
            w.protocol("WM_DELETE_WINDOW", deletewin)
            self.fitinfo = SimpleEditor(w, height=25, width=85)
            self.fitinfo.pack(in_=w, fill=BOTH, expand=Y)
        self.fitinfo.text.insert(END, s)
        self.fitinfo.text.see(END)
        return

    @classmethod
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
        if self.model is not None:
            self.indvarwidget['values'] = list(self.model.exog_names)
        return

    def quit(self):
        #self.main.withdraw()
        self.table.sv = None
        self.main.destroy()
        return
