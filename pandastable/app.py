#!/usr/bin/env python
"""
    DataExplore Application based on pandastable.
    Created January 2014
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

import tkinter
from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog, messagebox, simpledialog
import matplotlib
matplotlib.use('TkAgg')
import pandas as pd
import re, os, platform
import time
from .core import Table
from .data import TableModel
from .prefs import Preferences
from . import images, util, dialogs
from .dialogs import MultipleValDialog

class ViewerApp(Frame):
    """Pandastable viewer application"""

    def __init__(self,parent=None, data=None, projfile=None, msgpack=None):
        "Initialize the application."

        self.parent=parent
        if not self.parent:
            Frame.__init__(self)
            self.main=self.master
        else:
            self.main=Toplevel()
            self.master=self.main

        if getattr(sys, 'frozen', False):
            #the application is frozen
            self.modulepath = os.path.dirname(sys.executable)
        else:
            self.modulepath = os.path.dirname(__file__)

        icon = os.path.join(self.modulepath,'dataexplore.gif')
        img = PhotoImage(file=icon)
        self.main.tk.call('wm', 'iconphoto', self.main._w, img)

        # Get platform into a variable
        self.currplatform=platform.system()
        if not hasattr(self,'defaultsavedir'):
            self.defaultsavedir = os.getcwd()

        self.style = Style()
        available_themes = self.style.theme_names()
        pf = Table.checkOS()
        if pf == 'linux':
            self.style.theme_use('default')

        self.style.configure("TButton", padding=(3, 3, 3, 3), relief="raised")
        self.style.configure("TEntry", padding=(3, 3, 3, 3))
        self.main.title('DataExplore')
        self.createMenuBar()
        self.setupGUI()
        self.clipboarddf = None
        self.projopen = False

        if data != None:
            self.data = data
            self.new_project(data)
        elif projfile != None:
            self.openProject(projfile)
        elif msgpack != None:
            self.loadmsgpack(msgpack)
        else:
            self.newProject()

        self.main.protocol('WM_DELETE_WINDOW',self.quit)
        return

    def setupGUI(self):
        """Add all GUI elements"""

        self.m = PanedWindow(self.main, orient=HORIZONTAL)
        self.m.pack(fill=BOTH,expand=1)
        self.nb = Notebook(self.main)
        self.m.add(self.nb)
        self.setGeometry()
        return

    def createSidePane(self, width=200):
        """Side panel for plot viewer"""

        self.closeSidePane()
        self.sidepane = Frame(self.m)
        self.m.add(self.sidepane, weight=3)
        return self.sidepane

    def closeSidePane(self):
        """Destroy sidepine"""

        if hasattr(self, 'sidepane'):
            self.m.forget(self.sidepane)
            self.sidepane.destroy()
        return

    def createMenuBar(self):
        """Create the menu bar for the application. """

        self.menu=Menu(self.main)
        self.proj_menu={'01New':{'cmd': self.newProject},
                        '02Open':{'cmd': lambda: self.openProject(asksave=True)},
                        '03Close':{'cmd':self.closeProject},
                        '04Save':{'cmd':self.saveProject},
                        '05Save As':{'cmd':self.saveasProject},
                        '08Quit':{'cmd':self.quit}}
        if self.parent:
            self.proj_menu['08Return to Database']={'cmd':self.return_data}
        self.proj_menu=self.createPulldown(self.menu,self.proj_menu)
        self.menu.add_cascade(label='Project',menu=self.proj_menu['var'])

        self.sheet_menu={'01Add Sheet':{'cmd': lambda: self.addSheet(select=True)},
                         '02Remove Sheet':{'cmd':self.deleteSheet},
                         '03Copy Sheet':{'cmd':self.copySheet},
                         '04Rename Sheet':{'cmd':self.renameSheet},
                         }
        self.sheet_menu=self.createPulldown(self.menu,self.sheet_menu)
        self.menu.add_cascade(label='Sheet',menu=self.sheet_menu['var'])

        self.edit_menu={'01Copy Table':{'cmd': self.copyTable},
                        '02Paste Table':{'cmd':self.pasteTable},
                        '03Paste as Subtable':{'cmd': lambda: self.pasteTable(subtable=True)}
                         }
        self.edit_menu = self.createPulldown(self.menu,self.edit_menu)
        self.menu.add_cascade(label='Edit',menu=self.edit_menu['var'])

        self.table_menu={'01Describe Table':{'cmd':self.describe},
                         '02Convert Column Names':{'cmd':lambda: self._call('convertColumnNames')},
                         '03Convert Numeric':{'cmd': lambda: self._call('convertNumeric')},
                         '04Clean Data': {'cmd': lambda: self._call('cleanData')},
                         '05Correlation Matrix':{'cmd': lambda: self._call('corrMatrix')},
                         '06Concatenate Tables':{'cmd':self.concat},
                         '07Table to Text':{'cmd': lambda: self._call('showasText')},
                         '08Table Info':{'cmd': lambda: self._call('showInfo')} }
        self.table_menu=self.createPulldown(self.menu,self.table_menu)
        self.menu.add_cascade(label='Table',menu=self.table_menu['var'])

        self.tools_menu={'01Batch File Rename':{'cmd':self.fileRename},
                         }
        self.tools_menu=self.createPulldown(self.menu,self.tools_menu)
        self.menu.add_cascade(label='Tools',menu=self.tools_menu['var'])

        self.dataset_menu={'01Sample Data':{'cmd':self.sampleData},
                         '03Iris Data':{'cmd': lambda: self.getData('iris.mpk')},
                         '03Tips Data':{'cmd': lambda: self.getData('tips.mpk')},
                         '04Stacked Data':{'cmd':self.getStackedData},
                         '05Pima Diabetes':
                             {'cmd': lambda: self.getData('pima.mpk')},
                         '06Titanic':
                             {'cmd': lambda: self.getData('titanic3.mpk')},
                         }
        self.dataset_menu=self.createPulldown(self.menu,self.dataset_menu)
        self.menu.add_cascade(label='Datasets',menu=self.dataset_menu['var'])

        self.help_menu={'01Online Help':{'cmd':self.online_documentation},
                        '02About':{'cmd':self.about}}
        self.help_menu=self.createPulldown(self.menu,self.help_menu)
        self.menu.add_cascade(label='Help',menu=self.help_menu['var'])

        self.main.config(menu=self.menu)
        return

    def getBestGeometry(self):
        """Calculate optimal geometry from screen size"""

        ws = self.main.winfo_screenwidth()
        hs = self.main.winfo_screenheight()
        self.w=w=ws/1.4; h=hs*0.7
        x = (ws/2)-(w/2); y = (hs/2)-(h/2)
        g = '%dx%d+%d+%d' % (w,h,x,y)
        return g

    def setGeometry(self):
        self.winsize = self.getBestGeometry()
        self.main.geometry(self.winsize)
        return

    def createPulldown(self,menu,dict):
        var=Menu(menu,tearoff=0)
        items=list(dict.keys())
        items.sort()
        for item in items:
            if item[-3:]=='sep':
                var.add_separator()
            else:
                command=None
                if 'cmd' in dict[item]:
                    command=dict[item]['cmd']
                if 'sc' in dict[item]:
                    var.add_command(label='%-25s %9s' %(item[2:],dict[item]['sc']),
                                    command=command)
                else:
                    var.add_command(label='%-25s' %(item[2:]),command=command)
        dict['var']=var
        return dict

    def loadMeta(self, table, meta):
        """Load meta data for a table"""

        plotopts = meta['plotoptions']
        tablesettings = meta['table']
        rowheadersettings = meta['rowheader']

        if 'childtable' in meta:
            childtable = meta['childtable']
            childsettings = meta['childselected']
        else:
            childtable = None
        table.pf.mplopts.updateFromOptions(plotopts)
        table.pf.mplopts.applyOptions()

        util.setAttributes(table, tablesettings)
        util.setAttributes(table.rowheader, rowheadersettings)
        if childtable is not None:
            table.createChildTable(df=childtable)
            util.setAttributes(table.child, childsettings)

        if table.plotted == 'main':
            table.plotSelected()
        elif table.plotted == 'child' and table.child != None:
            table.child.plotSelected()
        #redraw col selections
        table.drawMultipleCols()
        return

    def saveMeta(self, table):
        """Save meta data such as current plot options"""

        meta = {}
        #save plot options
        meta['plotoptions'] = table.pf.mplopts.kwds
        #save table selections
        meta['table'] = util.getAttributes(table)
        meta['rowheader'] = util.getAttributes(table.rowheader)
        #save child table if present
        if table.child != None:
            meta['childtable'] = table.child.model.df
            meta['childselected'] = util.getAttributes(table.child)
        #for i in meta['table']:
        #    print (i,meta['table'][i])
        return meta

    def newProject(self, data=None, df=None):
        """Create a new project from data or empty"""

        w = self.closeProject()
        if w == None:
            return
        self.sheets={}
        for n in self.nb.tabs():
            self.nb.forget(n)
        if data != None:
            for s in sorted(data.keys()):
                if s == 'meta':
                    continue
                df = data[s]['table']
                if 'meta' in data[s]:
                    meta = data[s]['meta']
                else:
                    meta=None
                self.addSheet(s, df, meta)
        else:
            self.addSheet('sheet1')
        self.filename = None
        self.projopen = True
        self.main.title('DataExplore')
        return

    def openProject(self, filename=None, asksave=False):
        """Open project file"""

        w=True
        if asksave == True:
            w = self.closeProject()
        if w == None:
            return
        if filename == None:
            filename = filedialog.askopenfilename(defaultextension='.dexpl"',
                                                    initialdir=os.getcwd(),
                                                    filetypes=[("project","*.dexpl"),
                                                               ("All files","*.*")],
                                                    parent=self.main)
        if not filename:
            return
        if os.path.isfile(filename):
            data = pd.read_msgpack(filename)
        self.newProject(data)
        self.filename = filename
        self.main.title('%s - DataExplore' %filename)
        self.projopen = True
        return

    def saveProject(self):
        """Save project"""

        if not hasattr(self, 'filename') or self.filename == None:
            self.saveasProject()
        else:
            self.doSaveProject(self.filename)
        return

    def saveasProject(self):
        """Save as a new filename"""

        filename = filedialog.asksaveasfilename(parent=self.main,
                                                defaultextension='.dexpl',
                                                initialdir=self.defaultsavedir,
                                                filetypes=[("project","*.dexpl")])
        if not filename:
            return
        self.filename=filename
        self.doSaveProject(self.filename)
        return

    def doSaveProject(self, filename):
        """Save sheets as dict in msgpack"""

        data={}
        for i in self.sheets:
            table = self.sheets[i]
            data[i] = {}
            data[i]['table'] = table.model.df
            data[i]['meta'] = self.saveMeta(table)
        try:
            pd.to_msgpack(filename, data, encoding='utf-8')
        except:
            print('SAVE FAILED!!!')
        return

    def closeProject(self):
        """Close"""

        if self.projopen == False:
            w=False
        else:
            w = messagebox.askyesnocancel("Close Project",
                                        "Save this project?",
                                        parent=self.master)
        if w==None:
            return
        elif w==True:
            self.saveProject()
        else:
            pass
        for n in self.nb.tabs():
            self.nb.forget(n)
        self.filename = None
        self.projopen = False
        self.main.title('DataExplore')
        return w

    def loadmsgpack(self, filename):
        """Load a msgpack file"""

        df = pd.read_msgpack(filename)
        name = os.path.splitext(os.path.basename(filename))[0]
        if hasattr(self,'sheets'):
            self.addSheet(sheetname=name, df=df)
        else:
            data = {name:{'table':df}}
            self.newProject(data)
        return

    def getData(self, name):
        """Get predefined data from dataset folder"""

        filename = os.path.join(self.modulepath, 'datasets', name)
        self.loadmsgpack(filename)
        return

    def addSheet(self, sheetname=None, df=None, meta=None, select=False):
        """Add a sheet with new or existing data"""

        names = [self.nb.tab(i, "text") for i in self.nb.tabs()]
        def checkName(name):
            if name == '':
                messagebox.showwarning("Whoops", "Name should not be blank.")
                return 0
            if name in names:
                messagebox.showwarning("Name exists", "Sheet name already exists!")
                return 0

        noshts = len(self.nb.tabs())
        if sheetname == None:
            sheetname = simpledialog.askstring("New sheet name?", "Enter sheet name:",
                                                initialvalue='sheet'+str(noshts+1))
        if sheetname == None:
            return
        if checkName(sheetname) == 0:
            return
        #Create the table
        main = PanedWindow(orient=HORIZONTAL)
        self.nb.add(main, text=sheetname)
        f1 = Frame(main)
        main.add(f1)
        table = Table(f1, dataframe=df, showtoolbar=1, showstatusbar=1)
        table.show()
        f2 = Frame(main)
        main.add(f2, weight=3)
        pf = table.showPlotViewer(f2)
        self.saved = 0
        self.currenttable = table
        self.sheets[sheetname] = table
        #load meta data
        if meta != None:
        #if data != None and 'meta' in data:
            self.loadMeta(table, meta)
        if select == True:
            ind = self.nb.index('end')-1
            s = self.nb.tabs()[ind]
            self.nb.select(s)
        return sheetname

    def deleteSheet(self):
        """Delete a sheet"""

        s = self.nb.index(self.nb.select())
        name = self.nb.tab(s, 'text')
        self.nb.forget(s)
        del self.sheets[name]
        return

    def copySheet(self, newname=None):
        """Copy a sheet"""

        currenttable = self.getCurrentTable()
        newdata = currenttable.model.df
        if newname == None:
            self.addSheet(None, df=newdata)
        else:
            self.addSheet(newname, df=newdata)
        return

    def renameSheet(self):
        """Rename a sheet"""

        s = self.nb.tab(self.nb.select(), 'text')
        newname = simpledialog.askstring("New sheet name?",
                                          "Enter new sheet name:",
                                          initialvalue=s)
        if newname == None:
            return
        self.copySheet(newname)
        self.deleteSheet()
        return

    def getCurrentTable(self):

        s = self.nb.index(self.nb.select())
        name = self.nb.tab(s, 'text')
        table = self.sheets[name]
        return table

    def describe(self):
        """Describe dataframe"""

        table = self.getCurrentTable()
        df = table.model.df
        d = df.describe()
        table.createChildTable(d,index=True)
        return

    def concat(self):
        """Concat 2 tables"""

        vals = list(self.sheets.keys())
        if len(vals)<=1:
            return
        d = MultipleValDialog(title='Concat',
                                initialvalues=(vals,vals),
                                labels=('Table 1','Table 2'),
                                types=('combobox','combobox'),
                                parent = self.master)
        if d.result == None:
            return
        else:
            s1 = d.results[0]
            s2 = d.results[1]
        if s1 == s2:
            return
        df1 = self.sheets[s1].model.df
        df2 = self.sheets[s2].model.df
        m = pd.concat([df1,df2])
        self.addSheet('concat-%s-%s' %(s1,s2),m)
        return

    def sampleData(self):
        """Load sample table"""

        df = TableModel.getSampleData()

        name='sample'
        i=1
        while name in self.sheets:
            name='sample'+str(i)
            i+=1
        self.addSheet(sheetname=name, df=df)
        return

    def getStackedData(self):

        df = TableModel.getStackedData()
        self.addSheet(sheetname='stacked-data', df=df)
        return

    def fileRename(self):
        """Start file renaming util"""

        from .rename import BatchRenameApp
        br = BatchRenameApp(self.master)
        return

    def copyTable(self):
        """Copy current table dataframe"""

        table = self.getCurrentTable()
        self.clipboarddf = table.model.df.copy()
        return

    def pasteTable(self, subtable=False):
        """Paste copied dataframe into current table"""

        #add warning?
        if self.clipboarddf is None:
            return
        df = self.clipboarddf
        table = self.getCurrentTable()
        if subtable == True:
            table.createChildTable(df)
        else:
            model = TableModel(df)
            table.updateModel(model)
        return

    def _call(self, func):
        """Call a table function from it's string name"""
        table = self.getCurrentTable()
        getattr(table, func)()
        return

    def about(self):
        """About dialog"""

        abwin = Toplevel()
        x,y,w,h = dialogs.getParentGeometry(self.main)
        abwin.geometry('+%d+%d' %(x+w/2-200,y+h/2-200))
        abwin.title('About')
        abwin.transient(self)
        abwin.grab_set()
        logo = images.tableapp_logo()
        label = Label(abwin,image=logo,anchor=CENTER)
        label.image = logo
        label.grid(row=0,column=0,sticky='ew',padx=4,pady=4)
        style = Style()
        style.configure("BW.TLabel", font='arial 11')
        from . import __version__

        text='DataExplore Application\n'\
                +'pandastable version '+__version__+'\n'\
                +'Copyright (C) Damien Farrell 2014-\n'\
                +'This program is free software; you can redistribute it and/or\n'\
                +'modify it under the terms of the GNU General Public License\n'\
                +'as published by the Free Software Foundation; either version 3\n'\
                +'of the License, or (at your option) any later version.'
        row=1
        #for line in text:
        tmp = Label(abwin, text=text, style="BW.TLabel")
        tmp.grid(row=row,column=0,sticky='news',pady=2,padx=4)

        return

    def online_documentation(self,event=None):
        """Open the online documentation"""
        import webbrowser
        link='https://github.com/dmnfarrell/pandastable/wiki'
        webbrowser.open(link,autoraise=1)
        return

    def quit(self):
        #import pylab as plt
        #plt.close()
        self.main.destroy()
        return

def main():
    "Run the application"
    import sys, os
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="msgpack",
                        help="Open a dataframe as msgpack", metavar="FILE")
    parser.add_option("-p", "--project", dest="projfile",
                        help="Open a dataexplore project file", metavar="FILE")
    opts, remainder = parser.parse_args()
    if opts.projfile != None:
        app = ViewerApp(projfile=opts.projfile)
    elif opts.msgpack != None:
        app = ViewerApp(msgpack=opts.msgpack)
    else:
        app = ViewerApp()
    app.mainloop()
    return

if __name__ == '__main__':
    main()
