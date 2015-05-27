#!/usr/bin/env python
"""
    Module implements Table filtering and searching functionality.
    Created Oct 2008
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

import tkinter
from tkinter import *
from tkinter.ttk import *
from types import *
import re

def contains(v1,v2):
    if v1 in v2:
        return True

def excludes(v1, v2):
    if not v1 in v2:
        return True

def equals(v1,v2):
    if v1==v2:
        return True

def notequals(v1,v2):
    if v1!=v2:
        return True

def greaterthan(v1,v2):
    if v2>v1:
        return True
    return False

def lessthan(v1,v2):
    if v2<v1:
        return True
    return False

def startswith(v1,v2):
    if v2.startswith(v1):
        return True

def endswith(v1,v2):
    if v2.endswith(v1):
        return True

def haslength(v1,v2):
    if len(v2)>v1:
        return True

def isnumber(v1,v2):
    try:
        float(v2)
        return True
    except:
        return False

def regex(v1,v2):
    """Apply a regular expression"""
    print (re.findall(v1,v2))
    return

operatornames = {'=':equals,'!=':notequals,
                   'contains':contains,'excludes':excludes,
                   '>':greaterthan,'<':lessthan,
                   'starts with':startswith,
                   'ends with':endswith,
                   'has length':haslength,
                   'is number':isnumber}

def doFiltering(searchfunc, filters=None):
    """Module level method. Filter recs by several filters using a user provided
       search function.
       filters is a list of tuples of the form (key,value,operator,bool)
       returns: found record keys"""

    if filters == None:
        return
    F = filters
    sets = []
    for f in F:
        col, val, op, boolean = f
        names = searchfunc(col, val, op)
        sets.append((set(names), boolean))
    names = sets[0][0]
    for s in sets[1:]:
        b=s[1]
        if b == 'AND':
            names = names & s[0]
        elif b == 'OR':
            names = names | s[0]
        elif b == 'NOT':
            names = names - s[0]
        #print len(names)
    names = list(names)
    return names

class Filterer(Frame):

    def __init__(self, parent, fields, callback=None, closecallback=None):
        """Create a filtering gui frame.
        Callback must be some method that can accept tuples of filter
        parameters connected by boolean operators """
        Frame.__init__(self, parent)
        self.parent = parent
        self.callback = callback
        self.closecallback = closecallback
        self.fields = fields
        self.filters = []
        self.addFilterBar()
        addbutton=Button(self,text='Go', command=self.callback)
        addbutton.grid(row=0,column=0,sticky='news',padx=2,pady=2)
        addbutton=Button(self,text='+Add Filter', command=self.addFilterBar)
        addbutton.grid(row=0,column=1,sticky='news',padx=2,pady=2)
        cbutton=Button(self,text='Close', command=self.close)
        cbutton.grid(row=0,column=2,sticky='news',padx=2,pady=2)
        self.resultsvar=IntVar()
        Label(self,text='found:').grid(row=0,column=3,sticky='nes')
        Label(self,textvariable=self.resultsvar).grid(row=0,column=4,sticky='nws',padx=2,pady=2)
        return

    def addFilterBar(self):
        """Add filter"""
        index = len(self.filters)
        f = FilterBar(self, index, self.fields)
        self.filters.append(f)
        f.grid(row=index+1,column=0,columnspan=5,sticky='news',padx=2,pady=2)
        return

    def close(self):
        """Close frame and do stuff in parent app if needed"""
        self.closecallback()
        self.destroy()
        return

    def doFiltering(self, searchfunc):
        """Apply the filters"""
        F=[]
        for f in self.filters:
            F.append(f.getFilter())
        names = doFiltering(searchfunc, F)
        self.updateResults(len(names))
        return names

    def updateResults(self, i):
        self.resultsvar.set(i)
        return

class FilterBar(Frame):
    """Class providing filter widgets"""

    operators = ['contains','excludes','=','!=','>','<','starts with',
                 'ends with','has length','is number']
    booleanops = ['AND','OR','NOT']
    def __init__(self, parent, index, fields):
        Frame.__init__(self, parent)
        self.parent=parent
        self.index = index
        self.filtercol=StringVar()
        initial = fields[0]
        filtercolmenu = Combobox(self,
                #labelpos = 'w',
                #label_text = 'Column:',
                textvariable = self.filtercol,
                values = fields,
                #initialitem = initial,
                width = 10)
        filtercolmenu.grid(row=0,column=1,sticky='news',padx=2,pady=2)
        self.operator=StringVar()
        operatormenu = Combobox(self,
                textvariable = self.operator,
                values = self.operators,
                #initialitem = 'contains',
                width = 8)
        operatormenu.grid(row=0,column=2,sticky='news',padx=2,pady=2)
        self.filtercolvalue=StringVar()
        valsbox=Entry(self,textvariable=self.filtercolvalue,width=20)
        valsbox.grid(row=0,column=3,sticky='news',padx=2,pady=2)
        valsbox.bind("<Return>", self.parent.callback)
        self.booleanop=StringVar()
        booleanopmenu = Combobox(self,
                textvariable = self.booleanop,
                values = self.booleanops,
                #initialitem = 'AND',
                width = 6)
        booleanopmenu.grid(row=0,column=0,sticky='news',padx=2,pady=2)
        #disable the boolean operator if it's the first filter
        #if self.index == 0:
            #booleanopmenu.component('menubutton').configure(state=DISABLED)
        cbutton=Button(self,text='-', command=self.close, width=5)
        cbutton.grid(row=0,column=5,sticky='news',padx=2,pady=2)
        return

    def close(self):
        """Destroy and remove from parent"""
        self.parent.filters.remove(self)
        self.destroy()
        return

    def getFilter(self):
        """Get filter values for this instance"""
        col = self.filtercol.get()
        val = self.filtercolvalue.get()
        op = self.operator.get()
        booleanop = self.booleanop.get()
        return col, val, op, booleanop

