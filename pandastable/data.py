#!/usr/bin/env python
"""
    Module implementing the Data class that manages data for
    it's associated PandasTable.

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

from types import *
import operator
import os, string, types, copy
import pickle
import numpy as np
import pandas as pd
from . import util

class TableModel(object):
    """A data model for the Table class that uses pandas

    Args:
        dataframe: pandas dataframe
        rows: number of rows if empty table
        columns: number of columns if empty table
    """

    keywords = {'colors':'colors'}

    def __init__(self, dataframe=None, rows=20, columns=5):
        """Constructor for table model. """
        self.initialiseFields()
        self.setup(dataframe, rows, columns)
        return

    def setup(self, dataframe, rows=20, columns=5):
        """Create table model"""

        if not dataframe is None:
            self.df = dataframe
        else:
            colnames = list(string.ascii_lowercase[:columns])
            self.df = pd.DataFrame(index=range(rows),columns=colnames)
            #self.df = self.getSampleData()
        #self.reclist = self.df.index # not needed now?
        return

    @classmethod
    def getSampleData(self, rows=400, cols=5, n=2):
        """Generate sample data
        Args:
            rows: no. of rows
            cols: columns
            n: length of column names
        """

        import random
        s = string.ascii_lowercase
        def genstr(n=2):
            return ''.join(random.choice(s) for i in range(n))
        maxrows = 5e6
        if rows>maxrows:
            rows=maxrows
        if cols>1e5:
            cols=int(1e5)
        n=2
        if cols>100: n=3
        colnames = [genstr(n) for i in range(cols)]
        coldata = [np.random.normal(x,1,rows) for x in np.random.normal(5,3,cols)]
        n = np.array(coldata).T
        df = pd.DataFrame(n, columns=colnames)
        col1 = colnames[0]
        col2 = colnames[1]
        df[col2] = df[col1]*np.random.normal(.8, .2, len(df))
        df = np.round(df, 3)
        cats = ['low','medium','high','very high']
        df['label'] = pd.cut(df[col1], bins=4, labels=cats).astype(str)
        #df['label'] = df.label.cat.as_ordered()
        #don't add date if rows too large
        if rows<2e6:
            df['date'] = pd.date_range('1/1/2016', periods=rows, freq='H')
        return df

    @classmethod
    def getIrisData(self):
        """Get iris dataset"""

        path = os.path.dirname(__file__)
        cols = ['sepal length','sepal width','petal length','petal width','class']
        df = pd.read_csv(os.path.join(path,'datasets','iris.data'),names=cols)
        return df

    @classmethod
    def getStackedData(self):
        """Get a dataframe to pivot test"""

        import pandas.util.testing as tm; tm.N = 4
        frame = tm.makeTimeDataFrame()
        N, K = frame.shape
        data = {'value' : frame.values.ravel('F'),
                'variable' : np.asarray(frame.columns).repeat(N),
                'date' : np.tile(np.asarray(frame.index), K)}
        return pd.DataFrame(data, columns=['date', 'variable', 'value'])

    def initialiseFields(self):
        """Create meta data fields"""
        self.meta = {}
        #self.columnwidths = {} #used to store col widths
        return

    def save(self, filename):
        """Save dataframe"""

        ftype = os.path.splitext(filename)[1]
        if ftype == '.mpk':
            self.df.to_msgpack(filename)
        elif ftype == '.pickle':
            self.df.to_pickle(filename)
        elif ftype == '.xls':
            self.df.to_excel(filename)
        elif ftype == '.csv':
            self.df.to_csv(filename)
        #elif ftype == '.html':
        #    self.df.to_html(filename)
        return

    def load(self, filename, filetype=None):
        """Load file, if no filetype given assume it's msgpack format"""

        if filetype == '.pickle':
            self.df = pd.read_pickle(filename)
        else:
            self.df = pd.read_msgpack(filename)
            #print (len(self.df))
        return

    def getlongestEntry(self, colindex, n=500):
        """Get the longest string in the column for determining width. Just uses the first
         n rows for speed"""

        df = self.df
        col = df.columns[colindex]
        try:
            if df.dtypes[col] == 'float64':
                c = df[col][:n].round(3)
            else:
                c = df[col][:n]
        except:
            return 1
        longest = c.astype('object').astype('str').str.len().max()
        if np.isnan(longest):
            return 1
        return longest

    def getRecordAtRow(self, rowindex):
        """Get the entire record at the specifed row"""

        record = self.df.iloc[rowindex]
        return record

    def moveColumn(self, oldindex, newindex):
        """Changes the order of columns"""

        df = self.df
        cols = list(df.columns)
        name = cols[oldindex]
        del cols[oldindex]
        cols.insert(newindex, name)
        self.df = df[cols]
        return

    def autoAddRows(self, num):
        """Add n rows to end of dataframe. Will create rows with index starting
           from highest previous row count"""

        df = self.df
        if len(df) == 0:
            self.df = pd.DataFrame(pd.Series(range(num)))
            print (df)
            return
        try:
            ind = self.df.index.max()+1
        except:
            ind = len(df)+1
        new = pd.DataFrame(np.nan, index=range(ind,ind+num), columns=df.columns)
        self.df = pd.concat([df, new])
        return

    def addRow(self, rowindex):
        """Inserts a row at the required index by append/concat"""

        df = self.df
        a, b = df[:rowindex], df[rowindex:]
        a = a.append(pd.Series(), ignore_index=1)
        self.df = pd.concat([a,b])
        return

    def deleteRow(self, row, unique=True):
        """Delete a row"""

        self.deleteRows([row], unique)
        return

    def deleteRows(self, rowlist=None, unique=True):
        """Delete multiple or all rows"""

        df = self.df
        if unique == True:
            rows = list(set(range(len(df))) - set(rowlist))
            self.df = df.iloc[rows]
        else:
            df.drop(df.index[rowlist],inplace=True)
        return

    def addColumn(self, colname=None, dtype=None, data=None):
        """Add a column"""

        if data is None:
            data = pd.Series(dtype=dtype)
        self.df[colname] = data
        return

    def deleteColumn(self, colindex):
        """delete a column"""

        df = self.df
        colname = df.columns[colindex]
        df.drop([colname], axis=1, inplace=True)
        return

    def deleteColumns(self, cols=None):
        """Remove all cols or list provided"""

        df = self.df
        colnames = df.columns[cols]
        df.drop(colnames, axis=1, inplace=True)
        return

    def deleteCells(self, rows, cols):
        self.df.iloc[rows,cols] = np.nan
        return

    def resetIndex(self, drop=False):
        """Reset index behaviour"""

        df = self.df
        df.reset_index(drop=drop,inplace=True)
        return

    def setindex(self, colindex):
        """Index setting behaviour"""

        df = self.df
        colnames = list(df.columns[colindex])
        indnames = df.index.names
        if indnames[0] != None:
            df.reset_index(inplace=True)
        df.set_index(colnames, inplace=True)
        return

    def copyIndex(self):
        """Copy index to a column"""

        df = self.df
        name = df.index.name
        if name == None: name='index'
        df[name] = df.index#.astype('object')
        return

    def groupby(self, cols):
        """Group by cols"""

        df = self.df
        colnames = df.columns[cols]
        grps = df.groupby(colnames)
        return grps

    def getColumnType(self, columnIndex):
        """Get the column type"""
        coltype = self.df.dtypes[columnIndex]
        return coltype

    def getColumnCount(self):
         """Returns the number of columns in the data model"""
         return len(self.df.columns)

    def getColumnName(self, columnIndex):
        """Returns the name of the given column by columnIndex"""
        try:
            return str(self.df.columns[columnIndex])
        except:
            return self.df.columns[columnIndex].encode('ascii', 'ignore')

    def getColumnData(self, columnIndex=None, columnName=None,
                        filters=None):
        """Return the data in a list for this col,
            filters is a tuple of the form (key,value,operator,bool)"""
        if columnIndex != None and columnIndex < len(self.columnNames):
            columnName = self.getColumnName(columnIndex)
        names = Filtering.doFiltering(searchfunc=self.filterBy,
                                         filters=filters)
        coldata = [self.data[n][columnName] for n in names]
        return coldata

    def getColumns(self, colnames, filters=None, allowempty=True):
        """Get column data for multiple cols, with given filter options,
            filterby: list of tuples of the form (key,value,operator,bool)
            allowempty: boolean if false means rows with empty vals for any
            required fields are not returned
            returns: lists of column data"""

        def evaluate(l):
            for i in l:
                if i == '' or i == None:
                    return False
            return True
        coldata=[]
        for c in colnames:
            vals = self.getColumnData(columnName=c, filters=filters)
            coldata.append(vals)
        if allowempty == False:
            result = [i for i in zip(*coldata) if evaluate(i) == True]
            coldata = list(zip(*result))
        return coldata

    def getRowCount(self):
         """Returns the number of rows in the table model."""
         return len(self.df)

    def getValueAt(self, row, col):
         """Returns the cell value at location specified
             by columnIndex and rowIndex."""

         df = self.df
         value = self.df.iloc[row,col]
         if type(value) is float and np.isnan(value):
             return ''
         return value

    def setValueAt(self, value, row, col, df=None):
        """Change dataframe according to row/col numbers. You can
        also pass an arbitrary dataframe here."""

        if df is None:
            df = self.df
        rowindex = df.iloc[row].name
        colindex = df.columns[col]
        #print (df.loc[rowindex,colindex])
        if value == '':
            value = np.nan
        dtype = self.df.dtypes[col]
        #try to cast to column type
        try:
            if dtype == 'float64':
                value = float(value)
            elif dtype == 'int':
                value = int(value)
            elif dtype == 'datetime64[ns]':
                value = pd.to_datetime(value)
        except Exception as e:
            print (e)
        if df.index.is_unique is True:
            df.loc[rowindex,colindex] = value
        else:
            #we cannot use index if not unique
            df.iloc[row,col] = value
        return

    def transpose(self):
        """Transpose dataframe"""

        df = self.df
        rows = df.index
        df = df.transpose()
        df.reset_index()
        if util.check_multiindex(df.columns) != 1:
            try:
                df.columns = df.columns.astype(str)
            except:
                pass
        try:
            self.df = df.infer_objects()
        except:
            self.df = df.convert_objects()
        #self.columnwidths = {}
        return

    def query(self):

        return

    def filterby(self):
        import filtering
        funcs = filtering.operatornames
        floatops = ['=','>','<']
        func = funcs[op]

        return

    def __repr__(self):
        return 'Table Model with %s rows' %len(self.df)
