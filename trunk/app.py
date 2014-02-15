#!/usr/bin/env python
"""
    Sample App to illustrate table functionality.
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
from core import Table
from data import TableModel
from prefs import Preferences
import images

class ViewerApp(Frame):
    """pandastable viewer app"""
    def __init__(self,parent=None, data=None, projfile=None):
        "Initialize the application."

        self.parent=parent
        if not self.parent:
            Frame.__init__(self)
            self.main=self.master
        else:
            self.main=Toplevel()
            self.master=self.main

        # Get platform into a variable
        self.currplatform=platform.system()
        if not hasattr(self,'defaultsavedir'):
            self.defaultsavedir = os.getcwd()

        self.style = Style()
        available_themes = self.style.theme_names()        
        self.style.theme_use('clam') 
        self.style.configure("TButton", padding=2, relief="raised")
        self.main.title('Pandas DataFrame Viewer')
        self.createMenuBar()
        self.setupGUI()

        if data != None:
            self.data = data
            self.new_project(data)
        elif projfile != None:
            self.openProject(projfile)
        else:
            self.newProject()
        
        self.main.protocol('WM_DELETE_WINDOW',self.quit)
        return

    def setupGUI(self):
        
        self.m = PanedWindow(self.main, orient=HORIZONTAL)
        self.m.pack(fill=BOTH,expand=1)
        self.nb = Notebook(self.main)       
        self.m.add(self.nb)       
        self.setGeometry()
        return

    def createSidePane(self, width=200):
        """Side panel for various dialogs is tabbed notebook"""
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
        self.proj_menu={'01New':{'cmd':self.newProject},
                        '02Open':{'cmd':self.openProject},
                        '03Close':{'cmd':self.closeProject},
                        '04Save':{'cmd':self.saveProject},
                        '05Save As':{'cmd':self.saveasProject},          
                        '08Quit':{'cmd':self.quit}}
        if self.parent:
            self.proj_menu['08Return to Database']={'cmd':self.return_data}
        self.proj_menu=self.createPulldown(self.menu,self.proj_menu)
        self.menu.add_cascade(label='Project',menu=self.proj_menu['var'])

        self.sheet_menu={'01Add Sheet':{'cmd':self.addSheet},
                         '02Remove Sheet':{'cmd':self.deleteSheet},
                         '03Copy Sheet':{'cmd':self.copySheet},
                         '04Rename Sheet':{'cmd':self.renameSheet},
                         }
        self.sheet_menu=self.createPulldown(self.menu,self.sheet_menu)
        self.menu.add_cascade(label='Sheet',menu=self.sheet_menu['var'])

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
                    var.add_command(label='%-25s %9s' %(item[2:],dict[item]['sc']),command=command)
                else:
                    var.add_command(label='%-25s' %(item[2:]),command=command)
        dict['var']=var
        return dict

    def newProject(self, data=None):
        """Create a new project"""

        self.sheets={}
        for n in self.nb.tabs():
            self.nb.forget(n)
        if data != None:
            for s in sorted(data.keys()):
                self.addSheet(s ,data[s])
        else:
            self.addSheet('sheet1')     
        return

    def openProject(self, filename=None):
        if filename == None:
            filename = filedialog.askopenfilename(defaultextension='.tbleprj"',
                                                    initialdir=os.getcwd(),
                                                    filetypes=[("msgpack","*.dfv"),
                                                               ("All files","*.*")],
                                                    parent=self.main)
        if os.path.isfile(filename):
            data = pd.read_msgpack(filename)        
        self.newProject(data)
        self.filename = filename
        return

    def saveProject(self):
        if not hasattr(self, 'filename') or self.filename == None:
            self.saveasProject()
        else:
            self.doSaveProject(self.filename)
        return

    def saveasProject(self):
        """Save as a new filename"""
        filename = filedialog.asksaveasfilename(parent=self.main,
                                                defaultextension='.dfv',
                                                initialdir=self.defaultsavedir,
                                                filetypes=[("msgpack","*.dfv"),
                                                           ("All files","*.*")])
        if not filename:
            return
        self.filename=filename
        self.doSaveProject(self.filename)
        return

    def doSaveProject(self, filename):
        """Save sheets as dict in msgpack"""
        data={}
        for i in self.sheets:           
            data[i] = self.sheets[i].model.df
           
        pd.to_msgpack(filename, data)
        return

    def closeProject(self):
        for n in self.nb.tabs():
            self.nb.forget(n)
        self.filename = None
        return

    def addSheet(self, sheetname=None, df=None):
        """Add a new sheet"""

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
        checkName(sheetname)        
        #Create the table
        main = PanedWindow(orient=HORIZONTAL)
        self.nb.add(main, text=sheetname)
        f1 = Frame(main)
        main.add(f1)
        table = Table(f1, dataframe=df)    
        table.createTableFrame()    
        f2 = Frame(main)
        main.add(f2, weight=3)            
        pf = table.showPlotFrame(f2)
        self.saved = 0
        self.currenttable = table
        self.sheets[sheetname] = table
   
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
        newdata = self.currenttable.model.df
        if newname == None:
            self.addSheet(None, newdata)
        else:
            self.addSheet(newname, newdata)
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

    def about(self):
        """About dialog"""
        abwin = Toplevel()
        abwin.geometry('+200+350')
        abwin.title('About')      
        abwin.transient()
        logo = images.tableapp_logo()
        label = Label(abwin,image=logo,anchor=CENTER)
        label.image = logo
        label.grid(row=0,column=0,sticky='ew',padx=4,pady=4)
        style = Style()
        style.configure("BW.TLabel", font='arial 11 bold')

        text='DataFrame Viewer for pandastable library\n'\
                +'Copyright (C) Damien Farrell 2014-\n'\
                +'This program is free software; you can redistribute it and/or\n'\
                +'modify it under the terms of the GNU General Public License\n'\
                +'as published by the Free Software Foundation; either version 3\n'\
                +'of the License, or (at your option) any later version.'
        row=1
        #for line in text:
        tmp = Label(abwin, text=text, style="BW.TLabel")
        tmp.grid(row=row,column=0,sticky='news',padx=4)
        
        return

    def online_documentation(self,event=None):
        """Open the online documentation"""
        import webbrowser
        link='http://sourceforge.net/projects/pandastable/'
        webbrowser.open(link,autoraise=1)
        return

    def quit(self):
        self.main.destroy()
        return

def main():
    "Run the application"
    import sys, os
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="projfile",
                        help="Open a dataframe viewer project file", metavar="FILE")
    opts, remainder = parser.parse_args()
    if opts.projfile != None:
        app = ViewerApp(projfile=opts.projfile)
    else:
        app = ViewerApp()
    app.mainloop()
    return

if __name__ == '__main__':
    main()
