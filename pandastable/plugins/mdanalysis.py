#!/usr/bin/env python
"""
    DataExplore pluin differential expression using R
    Created June 2017
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
import sys,os
import subprocess
import numpy as np
from pandastable.plugin import Plugin
from pandastable import core, plotting, dialogs
try:
    from tkinter import *
    from tkinter.ttk import *
except:
    from Tkinter import *
    from ttk import *
import pandas as pd
import pylab as plt
from mpl_toolkits.mplot3d import Axes3D
from collections import OrderedDict

class MultivariatePlugin(Plugin):
    """Plugin for DataExplore"""

    capabilities = ['gui','uses_sidepane']
    requires = ['']
    menuentry = 'Multivariate Analysis'
    gui_methods = {}
    version = '0.1'

    def __init__(self):
        self.result = None
        return

    def main(self, parent):

        if parent==None:
            return
        self.parent = parent
        self._doFrame()

        grps = {'data':['class_labels','target_col','use_selected'],
                'options':['analysis','transform','3d_plot']  }
        self.groups = grps = OrderedDict(grps)
        kinds = ['']
        methods = ['PCA','LDA','MDS','feature selection']
        transforms = ['','log']
        sheets = self.parent.getSheetList()
        self.opts = {'class_labels': {'type':'combobox','default':'','items':sheets},
                     'target_col': {'type':'combobox','default':'','items':[]},
                     'analysis': {'type':'combobox','default':'PCA','items':methods},
                     'use_selected': {'type':'checkbutton','default':False,'label':'use selected data'},
                     'transform': {'type':'combobox','default':'','items':transforms},
                     '3d_plot': {'type':'checkbutton','default':False,'label':'3d plot'},
                     }
        fr = self._createWidgets(self.mainwin)
        fr.pack(side=LEFT,fill=BOTH)

        bf = Frame(self.mainwin, padding=2)
        bf.pack(side=LEFT,fill=BOTH)

        b = Button(bf, text="Run", command=self.run)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="View Results", command=self.showResults)
        b.pack(side=TOP,fill=X,pady=2)

        bf = Frame(self.mainwin, padding=2)
        bf.pack(side=LEFT,fill=BOTH)
        b = Button(bf, text="Refresh", command=self.update)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="Close", command=self.quit)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="Help", command=self.online_help)
        b.pack(side=TOP,fill=X,pady=2)

        self.update()
        sheet = self.parent.getCurrentSheet()
        #reference to parent frame in sheet
        pw = self.parent.sheetframes[sheet]
        self.pf = self.table.pf

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

        return

    def _createWidgets(self, parent, callback=None):
        """Auto create tk vars, widgets for corresponding options and
           and return the frame"""

        dialog, self.tkvars, self.widgets = plotting.dialogFromOptions(parent,
                                                                       self.opts, self.groups)
        #self.widgets['class_labels'].bind("<<ComboboxSelected>>", self.update)
        return dialog

    def update(self, evt=None):
        """Update data widget(s)"""

        self.table = self.parent.getCurrentTable()
        df = self.table.model.df
        cols = list(df.columns)
        cols += ''
        #self.widgets['sample_labels']['values'] = self.parent.getSheetList()
        self.widgets['class_labels']['values'] = cols
        self.widgets['target_col']['values'] = cols
        return

    def run(self):
        """Run chosen method"""

        method = self.tkvars['analysis'].get()
        sel = self.tkvars['use_selected'].get()
        cats = self.tkvars['class_labels'].get()
        target = self.tkvars['target_col'].get()
        plot3d = self.tkvars['3d_plot'].get()

        if sel == 1:
            data = self.table.getSelectedDataFrame()
        else:
            data = self.table.model.df

        #setup plot
        self.pf._initFigure()
        if plot3d == True:
            fig = self.pf.fig
            ax = self.pf.ax = ax = Axes3D(fig)
        else:
            ax = self.pf.ax
        self.pf.mplopts.applyOptions()
        self.pf.labelopts.applyOptions()
        opts = self.pf.mplopts.kwds
        lopts = self.pf.labelopts.kwds
        #print (opts)

        X = pre_process(data)
        if cats != '':
            X = X.set_index(cats)
            print (X)
        if method == 'PCA':
            pX, result = do_pca(X=X)
            plot_pca(pX, ax=ax, plot3d=plot3d, **opts)
        elif method == 'LDA':
            pX, result = do_lda(X=X)
            plot_pca(pX, ax=ax, plot3d=plot3d, **opts)
        elif method == 'MDS':
            pX, result = do_mds(X=X)
            plot_pca(pX, ax=ax, plot3d=plot3d, **opts)
        elif method == 'feature selection':
            y=X[target]
            X=X.drop(target, 1)
            pX = feature_selection(X.values, y=y)

        self.result = result
        self.pf.ax.set_title(lopts['title'])
        self.pf.canvas.draw()
        return

    def showResults(self):

        import sklearn
        result = self.result
        print (type(result))
        if result is None:
            return
        w = self.resultswin = Toplevel(width=600,height=800)
        w.title('de results')
        fr=Frame(w)
        fr.pack(fill=BOTH,expand=1)

        if type(result) is sklearn.decomposition.pca.PCA:
            print (result.components_)
        elif type(result) is sklearn.discriminant_analysis.LinearDiscriminantAnalysis:
            print (result)

        t = core.Table(fr, dataframe=df, showtoolbar=True)
        t.show()
        return

    def clustermap(self):

        data = self.data
        res = res = self.getFiltered()
        cluster_map(data, res.name)
        plt.show()
        return

    def quit(self, evt=None):
        """Override this to handle pane closing"""

        self.mainwin.destroy()
        return

    def online_help(self,event=None):
        """Open the online documentation"""
        import webbrowser
        link='https://github.com/dmnfarrell/pandastable/wiki'
        webbrowser.open(link,autoraise=1)
        return


def pre_process(data, log=False):

    if log == True:
        X = data.fillna(1)
        X = np.log(X)
    else:
        X = data.fillna(0)
    return X

def do_pca(X, c=3):
    """Do PCA"""

    from sklearn import preprocessing
    from sklearn.decomposition.pca import PCA, RandomizedPCA
    #do PCA
    #S = standardize_data(X)
    #remove non numeric
    X = X._get_numeric_data()
    S = pd.DataFrame(preprocessing.scale(X),columns = X.columns)
    pca = PCA(n_components=c)
    pca.fit(S)
    out = 'explained variance %s' %pca.explained_variance_ratio_
    print (out)
    #print pca.components_
    w = pd.DataFrame(pca.components_,columns=S.columns)
    #print w.T.max(1).sort_values()
    pX = pca.fit_transform(S)
    pX = pd.DataFrame(pX,index=X.index)
    return pX, pca

def plot_pca(pX, plot3d=False, palette='Spectral', labels=False, ax=None,
             colors=None, **kwargs):
    """Plot PCA result, input should be a dataframe"""

    if ax==None:
        fig,ax = plt.subplots(1,1,figsize=(6,6))
    #print (kwargs)
    colormap = kwargs['colormap']
    fs = kwargs['fontsize']
    ms = kwargs['ms']*12
    kwargs = {k:kwargs[k] for k in ('linewidth','alpha','marker')}

    cats = pX.index.unique()
    import seaborn as sns
    colors = sns.mpl_palette(colormap, len(cats))

    for c, i in zip(colors, cats):
        print (i, len(pX.ix[i]))
        if plot3d == True:
            ax.scatter(pX.ix[i, 0], pX.ix[i, 1], pX.ix[i, 2], color=c, s=ms, label=i,
                        edgecolor='black', **kwargs)
        else:
            ax.scatter(pX.ix[i, 0], pX.ix[i, 1], color=c, s=ms, label=i,
                        edgecolor='black', **kwargs)

    ax.set_xlabel('PC1')
    ax.set_ylabel('PC2')
    if labels == True:
        for i, point in pX.iterrows():
            ax.text(point[0]+.3, point[1]+.3, str(i),fontsize=(9))
    if len(cats)<20:
        ax.legend(fontsize=fs*.8)
    return

def do_lda(X, c=3):

    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    idx = X.index
    c = pd.Categorical(idx)
    y = c.codes
    X = X._get_numeric_data()
    lda = LinearDiscriminantAnalysis(n_components=c)
    pX = lda.fit(X, y).transform(X)
    pX = pd.DataFrame(pX,index=idx)
    return pX, lda

def do_mds(X, c=3):
    """Do MDS"""

    X = X._get_numeric_data()
    from sklearn import manifold
    seed = np.random.RandomState(seed=3)
    mds = manifold.MDS(n_components=c, max_iter=500, eps=1e-9, random_state=seed,
                        n_jobs=1)
    pX = mds.fit(X.values).embedding_
    pX = pd.DataFrame(pX,index=X.index)
    return pX, mds

def feature_selection(data, y):
    """feature selection"""

    from sklearn.feature_selection import SelectKBest
    from sklearn.feature_selection import chi2
    X_new = SelectKBest(chi2, k=2).fit_transform(X, y)
    X_new.shape
    return

def cluster_map(data, names):
    import seaborn as sns
    import pylab as plt
    data = data.ix[names]
    X = np.log(data).fillna(0)
    cg = sns.clustermap(X,cmap='RdYlBu',figsize=(8,9),lw=1,linecolor='gray')
    mt = plt.setp(cg.ax_heatmap.yaxis.get_majorticklabels(), rotation=0)
    plt.setp(cg.ax_heatmap.xaxis.get_majorticklabels(), rotation=90)
    cg.fig.subplots_adjust(right=.75)
    return cg
