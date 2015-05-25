#!/usr/bin/env python
"""
    Dialog classes.
    Created Oct 2014
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
import types
import pandas as pd
from data import TableModel

class MultipleValDialog(simpledialog.Dialog):
    """Simple dialog to get multiple values"""

    def __init__(self, parent, title=None, initialvalues=None, labels=None, types=None):
        if labels != None and types is not None:
            self.initialvalues = initialvalues
            self.labels = labels
            self.types = types
        simpledialog.Dialog.__init__(self, parent, title)

    def body(self, master):

        r=0
        self.vrs=[];self.entries=[]
        for i in range(len(self.labels)):
            Label(master, text=self.labels[i]).grid(row=r,column=0,sticky='news')
            if self.types[i] in ['int','boolean']:
                self.vrs.append(IntVar())
            else:
                self.vrs.append(StringVar())
            if self.types[i] == 'password':
                s='*'
            else:
                s=None

            if self.types[i] == 'list':
                choices = self.initialvalues[i]
                self.vrs[i].set(self.initialvalues[i][0])
                w = Combobox(master, values=choices,
                         textvariable=self.vrs[i],width=14)
                self.entries.append(w)
            elif self.types[i] == 'boolean':
                self.vrs[i].set(self.initialvalues[i][0])
                w = Checkbutton(master, text='',
                         variable=self.vrs[i])
                self.entries.append(w)
            else:
                self.vrs[i].set(self.initialvalues[i])
                self.entries.append(Entry(master, textvariable=self.vrs[i], show=s))
            self.entries[i].grid(row=r, column=1,padx=2,pady=2)
            r+=1

        return self.entries[0] # initial focus

    def apply(self):
        self.result = True
        self.results = []
        for i in range(len(self.labels)):
            self.results.append(self.vrs[i].get())
        return

class ToolTip(object):
    """Tooltip class for tkinter widgets"""
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() +25
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        try:
            # For Mac OS
            tw.tk.call("::tk::unsupported::MacWindowStyle",
                       "style", tw._w,
                       "help", "noActivates")
        except TclError:
            pass
        label = Label(tw, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        """Hide tooltip"""
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

    @classmethod
    def createToolTip(self, widget, text):
        """Create a tooltip for a widget"""
        toolTip = ToolTip(widget)
        def enter(event):
            toolTip.showtip(text)
        def leave(event):
            toolTip.hidetip()
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)
        return

def dialogFromOptions(parent, opts, groups=None, callback=None):
    """Auto create tk vars and widgets for corresponding options and
       and return the enclosing frame"""

    tkvars = {}
    widgets = {}
    dialog = Frame(parent)
    if groups == None:
        groups = {'options': opts.keys()}
    c=0
    for g in groups:
        frame = LabelFrame(dialog, text=g)
        frame.grid(row=0,column=c,sticky='news')
        row=0; col=0
        for i in groups[g]:
            w=None
            opt = opts[i]
            if opt['type'] == 'entry':
                if 'label' in opt:
                    label=opt['label']
                else:
                    label=i
                if 'width' in opt:
                    w=opt['width']
                else:
                    w=8
                Label(frame,text=label).pack()
                tkvars[i] = v = StringVar()
                v.set(opts[i]['default'])
                w = Entry(frame,textvariable=v, width=w, command=callback)
            elif opt['type'] == 'checkbutton':
                tkvars[i] = v = IntVar()
                v.set(opts[i]['default'])
                w = Checkbutton(frame,text=opt['label'],
                         variable=v)
            elif opt['type'] == 'combobox':
                Label(frame,text=i).pack()
                tkvars[i] = v = StringVar()
                v.set(opts[i]['default'])
                w = Combobox(frame, values=opt['items'],
                         textvariable=v,width=14,
                         validatecommand=callback,validate='key')
                w.set(opt['default'])
                if 'tooltip' in opt:
                    ToolTip.createToolTip(w, opt['tooltip'])
            elif opt['type'] == 'scale':
                fr,to=opt['range']
                tkvars[i] = v = DoubleVar()
                v.set(opts[i]['default'])
                w = tkinter.Scale(frame,label=opt['label'],
                         from_=fr,to=to,
                         orient='horizontal',
                         resolution=opt['interval'],
                         variable=v)
            if w != None:
                w.pack(fill=BOTH,expand=1)
                widgets[i] = w
            row+=1
        c+=1
    return dialog, tkvars, widgets

class ProgressDialog(Toplevel):
    def __init__(self):
        Toplevel.__init__()
        prog = Progressbar(self, orient='horizontal',
                            length=200, mode='indeterminate')


class ImportDialog(Frame):
    """Provides a frame for figure canvas and MPL settings"""

    def __init__(self, parent=None, filename=None):

        from core import Table
        self.parent = parent
        self.filename = filename
        self.df = None
        self.main = Toplevel()
        self.master = self.main
        self.main.title('Text Import')
        self.main.protocol("WM_DELETE_WINDOW", self.quit)
        self.main.grab_set()
        self.main.transient(parent)

        opts = self.opts = {'delimiter':{'type':'combobox','default':',',
                        'items':[',',' ',';'], 'tooltip':'seperator'},
                     'header':{'type':'combobox','default':'infer','items':['infer'],
                                'tooltip':'position of column header'},
                     'decimal':{'type':'combobox','default':'.','items':['.',','],
                                'tooltip':'decimal point symbol'},
                     'comment':{'type':'entry','default':'#','label':'comment',
                                'tooltip':'comment symbol'},
                     'skipinitialspace':{'type':'checkbutton','default':0,'label':'skipinitialspace',
                                'tooltip':'skip initial space'},
                     }
        optsframe, self.tkvars, w = dialogFromOptions(self.main, opts)

        ''' escapechar=None, quotechar='"',
            skipinitialspace=False,
            lineterminator=None, index_col=None,
            names=None, prefix=None,
            skiprows=None, delimiter=None,
            delim_whitespace=False,
            '''
        tf = Frame(self.main)
        tf.pack(side=TOP,fill=BOTH,expand=1)
        self.previewtable = Table(tf,rows=0,columns=0)
        self.previewtable.show()
        self.update()

        optsframe.pack(side=TOP,fill=BOTH)
        bf = Frame(self.main)
        bf.pack(side=TOP,fill=BOTH)
        b = Button(bf, text="Update preview", command=self.update)
        b.pack(side=LEFT,fill=X,expand=1)
        b = Button(bf, text="Import", command=self.doImport)
        b.pack(side=LEFT,fill=X,expand=1)
        b = Button(bf, text="Cancel", command=self.quit)
        b.pack(side=LEFT,fill=X,expand=1)
        self.main.wait_window()
        return

    def update(self):
        kwds = {}
        for i in self.opts:
            kwds[i] = self.tkvars[i].get()
        self.kwds = kwds
        f = pd.read_csv(self.filename, chunksize=100, **kwds)
        df = f.get_chunk(100)
        model = TableModel(dataframe=df)
        self.previewtable.updateModel(model)
        self.previewtable.redraw()
        return

    def doImport(self):
        self.df = pd.read_csv(self.filename)
        self.quit()
        return

    def quit(self):
        self.main.destroy()
        return

