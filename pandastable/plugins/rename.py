#!/usr/bin/env python
"""
    File rename utility.
    Created January 2012
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
try:
    from tkinter import *
    from tkinter.ttk import *
    from tkinter.scrolledtext import ScrolledText
except:
    from Tkinter import *
    from ttk import *

if (sys.version_info > (3, 0)):
    from tkinter import filedialog, messagebox, simpledialog
else:
    import tkFileDialog as filedialog
    import tkSimpleDialog as simpledialog
    import tkMessageBox as messagebox
    from ScrolledText import ScrolledText
import os, string
import re, glob
from pandastable.plugin import Plugin

class BatchRenamePlugin(Plugin):
    """Batch renaming plugin for DataExplore"""

    capabilities = ['gui']
    requires = ['']
    menuentry = 'Batch File Rename'
    gui_methods = {}
    version = '0.1'

    def __init__(self):
        return

    def main(self, parent):
        self.parent=parent
        if not self.parent:
            Frame.__init__(self)
            self.main=self.master
        else:
            self.main=Toplevel()
            self.master=self.main
        self.main.title('Batch Rename')
        ws = self.main.winfo_screenwidth()
        hs = self.main.winfo_screenheight()
        w = 800; h=500
        x = (ws/2)-(w/2); y = (hs/2)-(h/2)
        self.main.geometry('%dx%d+%d+%d' % (w,h,x,y))
        self.doGUI()
        self.currentdir = os.path.expanduser('~')
        return

    def doGUI(self):
        """Create GUI"""

        self.m = PanedWindow(self.main,
                           orient=HORIZONTAL)
        self.m.pack(side=LEFT,fill=BOTH,expand=1)

        self.fileslist = ScrolledText(self.m, width=50, height=20)
        self.m.add(self.fileslist)
        self.preview = ScrolledText(self.m, width=20, height=20)
        self.m.add(self.preview)
        fr=Frame(self.main, padding=(4,4), width=90)
        b=Button(fr,text='Add Folder',command=self.addFolder)
        b.pack(side=TOP,fill=BOTH,pady=2)
        b=Button(fr,text='Clear',command=self.clear)
        b.pack(side=TOP,fill=BOTH,pady=2)

        self.patternvar = StringVar()
        self.patternvar.set('*.*')
        self.filepattern = Entry(fr, textvariable=self.patternvar)
        Label(fr,text='Wildcard:').pack(side=TOP)
        self.filepattern.pack(side=TOP,fill=BOTH,pady=2)
        self.findvar = StringVar()
        self.findvar.set(' ')
        self.findtext = Entry(fr, textvariable=self.findvar)
        Label(fr,text='Find:').pack(side=TOP)
        self.findtext.pack(side=TOP,fill=BOTH,pady=2)
        self.replacevar = StringVar()
        self.replacevar.set('.')
        self.replacetext = Entry(fr, textvariable=self.replacevar)
        Label(fr,text='Replace With:').pack(side=TOP)
        self.replacetext.pack(side=TOP,fill=BOTH,pady=2)

        b=Button(fr,text='Preview',command=self.dopreview)
        b.pack(side=TOP,fill=BOTH,pady=2)
        b=Button(fr,text='Execute',command=self.execute)
        b.pack(side=TOP,fill=BOTH,pady=2)
        fr.pack(side=LEFT,fill=BOTH)
        return

    def addFolder(self,path=None):
        """Get a folder"""

        if path==None:
            path = filedialog.askdirectory(parent=self.main,
                                            initialdir=self.currentdir,
                                            title='Select folder')
        if path:
            self.path = path
            #self.refresh()
            self.dopreview()
            self.currentdir = path
        return

    def refresh(self):
        """Load files list"""

        self.fileslist.delete('1.0',END)
        fp = self.patternvar.get()
        flist = glob.glob(os.path.join(self.path,fp))
        filestr = '\n'.join(flist)
        self.fileslist.insert(END, filestr)
        return

    def dopreview(self):
        """Preview update"""

        self.refresh()
        self.preview.delete('1.0',END)
        flist = self.fileslist.get('1.0',END)
        flist = flist.split('\n')
        find = self.findvar.get()
        repl = self.replacevar.get()
        new = doFindReplace(files=flist, find=find, replace=repl)
        new = '\n'.join(new)
        self.preview.insert(END,new)
        return

    def clear(self):

        self.fileslist.delete('1.0',END)
        self.preview.delete('1.0',END)
        self.path = None
        return

    def execute(self):
        """Do rename"""

        n = messagebox.askyesno("Rename",
                                  "Rename the files?",
                                  parent=self.master)
        if not n:
            return
        flist = self.fileslist.get('1.0',END).split('\n')
        find = self.findvar.get()
        repl = self.replacevar.get()
        doFindReplace(files=flist, find=find, replace=repl, rename=True)
        self.refresh()
        return

def doRename(files=None, wildcard=None, pattern='', replacement='', rename=False):
    """Rename all files in a directory using replacement"""

    newfiles = []
    if files==None:
        files = glob.glob(wildcard)
    for pathname in files:
        basename= os.path.basename(pathname)
        new_filename= re.sub(pattern, replacement, basename)
        if new_filename != basename:
            newfiles.append(new_filename)
            if rename == True:
                os.rename(pathname,
                          os.path.join(os.path.dirname(pathname),
                          new_filename))
    return newfiles

def doFindReplace(files=None, wildcard=None, find='', replace='', rename=False):
    """Find replace method"""

    newfiles = []
    if files==None:
        files = glob.glob(wildcard)
    for pathname in files:
        basename= os.path.basename(pathname)
        new_filename = basename.replace(find,replace)
        newfiles.append(new_filename)
        if new_filename != basename:

            if rename == True:
                os.rename(pathname,
                          os.path.join(os.path.dirname(pathname),
                          new_filename))
    return newfiles

def constructRegex(inputstr):
    return

def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-d", "--dir", dest="directory",
                        help="Folder of raw files")

    opts, remainder = parser.parse_args()
    app = BatchRenameApp()
    if opts.directory != None:
        app.addFolder(opts.directory)
    app.mainloop()

if __name__ == '__main__':
    main()
