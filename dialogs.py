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
            Label(master, text=self.labels[i]).grid(row=r, column=0,sticky='news')
            if self.types[i] == 'int':
                self.vrs.append(IntVar())
            else:
                self.vrs.append(StringVar())
            if self.types[i] == 'password':
                s='*'
            else:
                s=None

            if self.types[i] == 'list':
                button = Menubutton(master, textvariable=self.vrs[i])
                menu = Menu(button,tearoff=0)
                button['menu'] = menu
                choices=self.initialvalues[i]
                for c in choices:
                    menu.add_radiobutton(label=c,
                                        variable=self.vrs[i],
                                        value=c,
                                        indicatoron=1)
                self.entries.append(button)
                self.vrs[i].set(self.initialvalues[i][0])
            else:
                self.vrs[i].set(self.initialvalues[i])
                self.entries.append(Entry(master, textvariable=self.vrs[i], show=s))
            self.entries[i].grid(row=r, column=1)
            r+=1

        return self.entries[0] # initial focus

    def apply(self):
        self.result = True
        self.results = []
        for i in range(len(self.labels)):
            self.results.append(self.vrs[i].get())
        return

def dialogFromOptions(parent, opts, groups=None, callback=None):
    """Auto create tk vars and widgets for corresponding options and
       and return the enclosing frame"""

    tkvars = {}
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
                if 'width' in opt:
                    w=opt['width']
                else:
                    w=8
                Label(frame,text=i).pack()
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
                         textvariable=v,width=15,
                         validatecommand=callback,validate='key')
                w.set(opt['default'])
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
            row+=1
        c+=1
    return dialog, tkvars

