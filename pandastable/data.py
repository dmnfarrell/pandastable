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
        """
        Initialize the table model with a DataFrame or empty dimensions.

        Args:
            dataframe (pd.DataFrame): The DataFrame to be used.
            rows (int): Number of rows for an empty table.
            columns (int): Number of columns for an empty table.
        """

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
        """
        Generate sample data for testing.

        Args:
            rows (int): Number of rows.
            cols (int): Number of columns.
            n (int): Length of random column names.

        Returns:
            pd.DataFrame: A DataFrame with generated sample data.
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
            df['date'] = pd.date_range('1/1/2016', periods=rows, freq='h')
        return df

    @classmethod
    def getIrisData(self):
        """
        Get the Iris dataset.

        Returns:
            pd.DataFrame: The Iris dataset.
        """

        path = os.path.dirname(__file__)
        cols = ['sepal length','sepal width','petal length','petal width','class']
        df = pd.read_csv(os.path.join(path,'datasets','iris.data'),names=cols)
        return df

    @classmethod
    def getStackedData(self):
        """
        Get a stacked DataFrame for testing pivoting.

        Returns:
            pd.DataFrame: A stacked DataFrame.
        """

        import pandas.util.testing as tm; tm.N = 4
        frame = tm.makeTimeDataFrame()
        N, K = frame.shape
        data = {'value' : frame.values.ravel('F'),
                'variable' : np.asarray(frame.columns).repeat(N),
                'date' : np.tile(np.asarray(frame.index), K)}
        return pd.DataFrame(data, columns=['date', 'variable', 'value'])

    def initialiseFields(self):
        """
        Initialize metadata fields.
        """
        self.meta = {}
        #self.columnwidths = {} #used to store col widths
        return

    def save(self, filename):
        """
        Save the DataFrame to a file based on extension.

        Args:
            filename (str): The path to the file.
        """

        ftype = os.path.splitext(filename)[1]
        if ftype == '.pickle':
            self.df.to_pickle(filename)
        elif ftype == '.xls':
            self.df.to_excel(filename)
        elif ftype == '.csv':
            self.df.to_csv(filename)
        #elif ftype == '.html':
        #    self.df.to_html(filename)
        return

    def load(self, filename, filetype=None):
        """
        Load data from a file into the model.

        Args:
            filename (str): The path to the file.
            filetype (str): Optional file type extension.
        """

        if filetype == '.mpk':
            self.df = pd.read_msgpack(filename)
        else:
            self.df = pd.read_pickle(filename)
            #print (len(self.df))
        return

    def getlongestEntry(self, colindex, n=500):
        """
        Get the length of the longest string in a column for auto-sizing.
        Uses a sample of the first n rows for performance.

        Args:
            colindex (int): The column index.
            n (int): The number of rows to sample.

        Returns:
            int: The length of the longest entry.
        """

        df = self.df
        col = df.columns[colindex]
        try:
            if df.dtypes[col] in ['float32','float64']:
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
        """
        Get the entire record (row) at the specified index.

        Args:
            rowindex (int): The row index.

        Returns:
            pd.Series: The row data.
        """

        record = self.df.iloc[rowindex]
        return record

    def moveColumn(self, oldindex, newindex):
        """
        Move a column from one position to another.

        Args:
            oldindex (int): The current index of the column.
            newindex (int): The new index for the column.
        """

        df = self.df
        cols = list(df.columns)
        name = cols[oldindex]
        del cols[oldindex]
        cols.insert(newindex, name)
        self.df = df[cols]
        return

    def autoAddRows(self, num):
        """
        Add rows to the end of the DataFrame.

        Args:
            num (int): Number of rows to add.
        """

        df = self.df
        if len(df) == 0:
            self.df = pd.DataFrame(pd.Series(range(num)))
            #print (df)
            return
        try:
            ind = self.df.index.max()+1
        except:
            ind = len(df)+1
        new = pd.DataFrame(np.nan, index=range(ind,ind+num), columns=df.columns)
        self.df = pd.concat([df, new])
        return

    def insertRow(self, row):
        """
        Insert a single empty row at a specific index.

        Args:
            row (int): The index to insert at.

        Returns:
            int: The new row index.
        """

        df = self.df
        a, b = df[:row], df[row:]
        idx = len(df)+1
        new = pd.DataFrame(np.nan,index=[idx],columns=df.columns)
        a = pd.concat([a,new])
        self.df = pd.concat([a,b])
        return idx

    def deleteRow(self, row, unique=True):
        """
        Delete a single row.

        Args:
            row (int): The row index to delete.
            unique (bool): If true, assumes unique index.
        """

        self.deleteRows([row], unique)
        return

    def deleteRows(self, rowlist=None, unique=True):
        """
        Delete multiple rows.

        Args:
            rowlist (list): List of row indices to delete.
            unique (bool): Whether the index is unique.
        """

        df = self.df
        if unique == True:
            rows = list(set(range(len(df))) - set(rowlist))
            self.df = df.iloc[rows]
        else:
            df.drop(df.index[rowlist],inplace=True)
        return

    def addColumn(self, colname=None, dtype=None, data=None):
        """
        Add a new column to the DataFrame.

        Args:
            colname (str): The name of the new column.
            dtype: The data type for the column.
            data (pd.Series): Data to populate the column (optional).
        """

        if data is None:
            data = pd.Series(dtype=dtype)
        self.df[colname] = data
        return

    def deleteColumn(self, colindex):
        """
        Delete a column by index.

        Args:
            colindex (int): The index of the column to delete.
        """

        df = self.df
        colname = df.columns[colindex]
        df.drop([colname], axis=1, inplace=True)
        return

    def deleteColumns(self, cols=None):
        """
        Delete multiple columns.

        Args:
            cols (list): List of column indices to delete.
        """

        df = self.df
        colnames = df.columns[cols]
        df.drop(colnames, axis=1, inplace=True)
        return

    def deleteCells(self, rows, cols):
        """
        Set the values of specified cells to NaN.

        Args:
            rows (list): List of row indices.
            cols (list): List of column indices.
        """
        self.df.iloc[rows,cols] = np.nan
        return

    def resetIndex(self, drop=False):
        """
        Reset the DataFrame index.

        Args:
            drop (bool): Whether to drop the current index.
        """

        df = self.df
        df.reset_index(drop=drop,inplace=True)
        return

    def setindex(self, colindex):
        """
        Set the index of the DataFrame using a column.

        Args:
            colindex (int): The column index to use as the index.
        """

        df = self.df
        colnames = list(df.columns[colindex])
        indnames = df.index.names
        if indnames[0] != None:
            df.reset_index(inplace=True)
        df.set_index(colnames, inplace=True)
        return

    def copyIndex(self):
        """
        Copy the index to a new column.
        """

        df = self.df
        name = df.index.name
        if name == None: name='index'
        df[name] = df.index#.astype('object')
        return

    def groupby(self, cols):
        """
        Group the DataFrame by specified columns.

        Args:
            cols (list): List of column indices to group by.

        Returns:
            pd.GroupBy: The groupby object.
        """

        df = self.df
        colnames = df.columns[cols]
        grps = df.groupby(colnames)
        return grps

    def getColumnType(self, columnIndex):
        """Get the column type"""

        coltype = self.df.dtypes.iloc[columnIndex]
        return coltype

    def getColumnCount(self):
         """
         Get the total number of columns.

         Returns:
            int: Number of columns.
         """
         return len(self.df.columns)

    def getColumnName(self, columnIndex):
        """
        Get the name of a column by its index.

        Args:
            columnIndex (int): The column index.

        Returns:
            str: The column name.
        """
        try:
            return str(self.df.columns[columnIndex])
        except:
            return self.df.columns[columnIndex].encode('ascii', 'ignore')

    def getRowCount(self):
         """
         Get the total number of rows.

         Returns:
            int: Number of rows.
         """
         return len(self.df)

    def getValueAt(self, row, col):
         """
         Get the value at a specific cell.

         Args:
            row (int): Row index.
            col (int): Column index.

         Returns:
            The value at the cell. Returns empty string if NaN.
         """

         df = self.df
         value = self.df.iloc[row,col]
         if type(value) is float and np.isnan(value):
             return ''
         return value

    def setValueAt(self, value, row, col, df=None):
        """
        Set the value of a specific cell.

        Args:
            value: The new value.
            row (int): Row index.
            col (int): Column index.
            df (pd.DataFrame): Optional DataFrame to operate on (defaults to self.df).

        Returns:
            bool: True if successful, False otherwise.
        """

        if df is None:
            df = self.df
        rowindex = df.iloc[row].name
        colindex = df.columns[col]
        #print (df.loc[rowindex,colindex])
        if value == '':
            value = np.nan

        dtype = self.getColumnType(col)
        #try to cast to column type
        try:
            if dtype in ['float32','float64']:
                value = float(value)
            elif dtype == 'int':
                value = int(value)
            elif dtype == 'datetime64[ns]':
                value = pd.to_datetime(value)
        except Exception as e:
            print (e)
            return False
        if df.index.is_unique is True:
            df.loc[rowindex,colindex] = value
        else:
            #we cannot use index if not unique
            df.iloc[row,col] = value
        return True

    def transpose(self):
        """
        Transpose the DataFrame (swap rows and columns).
        """

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
        """
        Placeholder for query functionality.
        """

        return

    def filterby(self):
        """
        Placeholder for filtering functionality.
        """
        import filtering
        funcs = filtering.operatornames
        floatops = ['=','>','<']
        func = funcs[op]

        return

    def __repr__(self):
        return 'Table Model with %s rows' %len(self.df)
