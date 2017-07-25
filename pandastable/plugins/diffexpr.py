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
from pandastable import plotting, dialogs
try:
    from tkinter import *
    from tkinter.ttk import *
except:
    from Tkinter import *
    from ttk import *
import pandas as pd
import pylab as plt
from collections import OrderedDict
#import seaborn as sns

class DiffExpressionPlugin(Plugin):
    """Plugin for DataExplore"""

    capabilities = ['gui','uses_sidepane']
    requires = ['']
    menuentry = 'Differential Expression'
    gui_methods = {}
    version = '0.1'

    def __init__(self):

        return

    def main(self, parent):

        if parent==None:
            return
        self.parent = parent
        self._doFrame()

        grps = {'data':['sample_labels','sample_col','factors_col','conditions'],
                'options':['method','cutoff','plot_kind']
                    }
        self.groups = grps = OrderedDict(grps)
        kinds = ['point', 'bar', 'box', 'violin', 'strip']
        methods = ['limma','edger']
        sheets = self.parent.getSheetList()
        self.opts = {'sample_labels': {'type':'combobox','default':sheets[0],'items':sheets},
                     'sample_col': {'type':'combobox','default':'','items':[]},
                     'factors_col': {'type':'combobox','default':'','items':[]},
                     'conditions': {'type':'entry','default':'','label':'conditions'},
                     'method': {'type':'combobox','default':'limma','items':methods},
                     'cutoff': {'type':'entry','default':1.5,'label':'cutoff'},
                     'plot_kind': {'type':'combobox','default':'box','items':kinds},
                     }
        fr = self._createWidgets(self.mainwin)
        fr.pack(side=LEFT,fill=BOTH)

        bf = Frame(self.mainwin, padding=2)
        bf.pack(side=LEFT,fill=BOTH)

        b = Button(bf, text="Run DE", command=self.runDE)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="Plot Result", command=self.plotGenes)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="MD plot", command=self.MDplot)
        b.pack(side=TOP,fill=X,pady=2)

        bf = Frame(self.mainwin, padding=2)
        bf.pack(side=LEFT,fill=BOTH)
        b = Button(bf, text="Refresh", command=self.update)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="Close", command=self.quit)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="About", command=self._aboutWindow)
        b.pack(side=TOP,fill=X,pady=2)

        #self.table = self.parent.getCurrentTable()
        #df = self.table.model.df
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

        dialog, self.tkvars, self.widgets = plotting.dialogFromOptions(parent, self.opts, self.groups)
        self.widgets['sample_labels'].bind("<<ComboboxSelected>>", self.update)
        return dialog

    def update(self, evt=None):
        """Update data widget(s)"""

        self.table = self.parent.getCurrentTable()

        slabels = self.tkvars['sample_labels'].get()
        st = self.parent.sheets[slabels]
        self.labels = df = st.model.df

        cols = list(df.columns)
        cols += ''
        self.widgets['sample_labels']['values'] = self.parent.getSheetList()
        self.widgets['sample_col']['values'] = cols
        self.widgets['factors_col']['values'] = cols

        return

    def runDE(self):

        method = self.tkvars['method'].get()
        labels = self.labels
        counts = self.table.model.df
        cutoff = float(self.tkvars['cutoff'].get())
        sc = self.samplecol = self.tkvars['sample_col'].get()
        fc = self.factorcol = self.tkvars['factors_col'].get()
        self.conditions = conds = self.tkvars['conditions'].get().split(',')

        self.data = get_factor_samples(counts,
                                     labels, [(fc,conds[0]),(fc,conds[1])],
                                     samplecol=sc, index='name')

        if method == 'edger':
            self.result = run_edgeR(data=self.data, cutoff=cutoff)
        elif method == 'limma':
            self.result = run_limma(data=self.data, cutoff=cutoff)
        return

    def showResults(self):

        return

    def plotGenes(self):

        res = self.result
        names = res[(res.logFC>1.5) | (res.logFC<-1.5)].name[:50]
        counts = self.table.model.df
        m = melt_samples(counts, self.labels, names, samplecol=self.samplecol)
        import seaborn as sns
        kind = self.tkvars['plot_kind'].get()
        xorder = self.conditions

        g = sns.factorplot(self.factorcol,'read count', data=m, col='name', kind=kind,
                                col_wrap=4, size=3, aspect=1.1,
                                legend_out=True,sharey=False, order=xorder)
        plt.show()
        return

    def MDplot(self):

        data = self.data
        de = self.result
        md_plot(data, de, title='')
        plt.show()
        return

    def quit(self, evt=None):
        """Override this to handle pane closing"""

        self.mainwin.destroy()
        return

    def about(self):
        """About this plugin"""

        txt = "This plugin implements differential expression\n"+\
              "for gene counts from sequencing data. \n"+\
              "see . \n"+\
               "version: %s" %self.version

        return txt

def get_column_names(df):
    """Get count data sample column names"""

    ignore = ['total_reads','mean_norm']
    ncols = [i for i in df.columns if (i.endswith('norm')) and i not in ignore]
    cols = [i.split(' ')[0] for i in ncols if i not in ignore]
    return cols, ncols

def get_columns_by_label(labels, samplecol, filters=[], querystr=None):
    """Get sample columns according to a condition from a set of labels
    Args:
        labels: dataframe matching sample labels to conditions/factors
        samplecol: name of column holding sample/file names
        filters: tuples containing column/.value pairs to filter on
        querystr: optional string instead of tuple filters
        (see pandas.DataFrame.query documentation)
    """

    if querystr == None:
        q=[]
        for f in filters:
            print (f)
            if type(f[1]) in ['int','float']:
                s = "%s==%s" %(f[0],f[1])
            else:
                s = "%s=='%s'" %(f[0],f[1])
            q.append(s)
        querystr = ' & '.join(q)
    print (querystr)
    x = labels.query(querystr)
    cols = x[samplecol]
    return list(cols)

def get_factor_samples(df, labels, factors, filters=[],
                       samplecol='filename', index=None):
    """Get subsets of samples according to factor/levels specified in another mapping file
       Used for doing differential expr with edgeR.
       Args:
            labels: dataframe matching sample labels to conditions/factors
            factors: conditions to compare
            filters: additional filters for samples e.g. a time point
            samplecol: name of column holding sample/file names
       Returns:
            dataframe of data columns with header labels for edgeR script
    """

    if index != None:
        df=df.set_index(index)
    l=0
    res = None

    for f in factors:
        f = filters + [f]
        cols = get_columns_by_label(labels, samplecol, f)
        print (cols)
        cols = list(set(cols) & set(df.columns))
        x = df[cols]
        print ('%s samples, %s genes' %(len(cols),len(x)))
        if len(x.columns)==0:
            #no data found warning
            print ('WARNING: no data for %s' %f)
            continue
        print()
        x.columns = ['s'+str(cols.index(i))+'_'+str(l) for i in x.columns]
        l+=1
        if res is None:
            res = x
        else:
            res = res.join(x)
    res=res.dropna()
    return res

def melt_samples(df, labels, names, samplecol='filename', index='name'):
    """Melt sample data by factor labels so we can plot with seaborn"""

    df=df.set_index(index)
    scols,ncols = get_column_names(df)
    df = df.ix[names][ncols]
    t=df.T
    t.index = scols
    t = t.merge(labels,left_index=True,right_on=samplecol)
    m = pd.melt(t,id_vars=list(labels.columns),
                 var_name='name',value_name='read count')
    return m

def run_edgeR(countsfile=None, data=None, cutoff=1.5):
    """Run edgeR from R script"""

    if data is not None:
        countsfile = 'de_counts.csv'
        data.to_csv(countsfile)
    path = os.path.dirname(os.path.abspath(__file__)) #path to module
    descript = os.path.join(path, 'DEanalysis.R')
    cmd = 'Rscript %s %s' %(descript, countsfile)
    print (cmd)
    result = subprocess.check_output(cmd, shell=True, executable='/bin/bash')
    print (result)
    #read result back in
    de = pd.read_csv('edger_output.csv')
    de.rename(columns={'Unnamed: 0':'name'}, inplace=True)
    de = de[(de.FDR<0.05) & ((de.logFC>cutoff) | (de.logFC<-cutoff))]
    return de

def run_limma(countsfile=None, data=None, cutoff=1.5):
    """Run limma de from R script"""

    if data is not None:
        countsfile = 'de_counts.csv'
        data.to_csv(countsfile)
    path = os.path.dirname(os.path.abspath(__file__)) #path to module
    descript = os.path.join(path, 'Limma.R')
    cmd = 'Rscript %s %s' %(descript, countsfile)
    result = subprocess.check_output(cmd, shell=True, executable='/bin/bash')
    #read result back in
    de = pd.read_csv('limma_output.csv')
    de.rename(columns={'Unnamed: 0':'name'}, inplace=True)
    #md_plot(data, de)
    de = de[(de['adj.P.Val']<0.05) & ((de.logFC>cutoff) | (de.logFC<-cutoff))]
    de = de.sort_values('logFC',ascending=False)
    return de

def md_plot(data, de, title=''):
    """MD plot"""

    data = data.reset_index()
    data['mean log expr'] = data.mean(1).apply(np.log)
    df = data.merge(de,on='name')
    df['s'] = pd.cut(df.logFC, [-100,-1.5,1.5], labels=[1,0])
    #print (df[:10])
    a = df[df['adj.P.Val']<0.05]
    b = df[-df.name.isin(a.name)]
    c = a[a.logFC<0]
    ax=a.plot('mean log expr','logFC',kind='scatter',figsize=(10,10),color='red',s=60)
    c.plot('mean log expr','logFC',kind='scatter',ax=ax,color='g',s=60)
    b.plot('mean log expr','logFC',kind='scatter',ax=ax,color='black')
    ax.set_title(title, fontsize=20)
    return ax