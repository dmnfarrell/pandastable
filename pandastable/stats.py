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
        self.formulavar.set('a ~ b')
        e = Entry(ctrls, textvariable=self.formulavar, font="Courier 13 bold")
        e.pack(side=TOP,fill=BOTH,expand=1)
        bf = Frame(ctrls, padding=2)
        bf.pack(side=TOP,fill=BOTH)
        self.fitvar = StringVar()
        c = Combobox(bf, values=['ols'],
                       textvariable=self.fitvar)
        c.pack(side=LEFT,fill=Y,expand=1)
        b = Button(bf, text="Fit", command=self.doFit)
        b.pack(side=LEFT,fill=X,expand=1)
        b = Button(bf, text="Close", command=self.quit)
        b.pack(side=LEFT,fill=X,expand=1)

        return

    def doFit(self):
        """Do model fit"""

        import statsmodels.formula.api as smf
        df = self.table.getSelectedDataFrame()
        df = df.convert_objects(convert_numeric='force')

        formula = self.formulavar.get()
        mod = smf.ols(formula=formula, data=df)
        fit = mod.fit(subset=df[:20])
        #print (fit.summary())
        df['fit'] = fit.fittedvalues

        #df['fit'] = fit.predict(df)
        data = df[['a','b','fit']]
        pf = self.table.pf
        #print (pf.mplopts.kwds)
        #pf.plotFit(data, fit)

        import statsmodels.api as sm
        pf.fig.clear()
        ax = pf.fig.add_subplot(111)
        sm.graphics.plot_fit(fit, "b", ax=ax)
        pf.canvas.draw()
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
