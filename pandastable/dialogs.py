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

import sys,os
import tkinter
from tkinter import *
from tkinter.ttk import *
import types
from collections import OrderedDict
import pandas as pd
from .data import TableModel

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
                self.vrs[i].set(choices[0])
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
                self.entries.append(Entry(master, textvariable=self.vrs[i], width=10, show=s))
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
                    w=6
                Label(frame,text=label).pack()
                if type(opts[i]['default']) == int:
                    tkvars[i] = v = IntVar()
                else:
                    tkvars[i] = v = StringVar()
                v.set(opts[i]['default'])
                w = Entry(frame,textvariable=v, width=w, command=callback)
            elif opt['type'] == 'checkbutton':
                tkvars[i] = v = IntVar()
                v.set(opts[i]['default'])
                w = Checkbutton(frame,text=opt['label'],
                         variable=v)
            elif opt['type'] == 'combobox':
                if 'label' in opt:
                   label=opt['label']
                else:
                    label = i
                Label(frame,text=label).pack()
                tkvars[i] = v = StringVar()
                v.set(opts[i]['default'])
                w = Combobox(frame, values=opt['items'],
                         textvariable=v,width=14,
                         validatecommand=callback,validate='key')
                w.set(opt['default'])
                if 'tooltip' in opt:
                    ToolTip.createToolTip(w, opt['tooltip'])
            elif opt['type'] == 'radio':
                Label(frame,text=label).pack()
                if 'label' in opt:
                   label=opt['label']
                else:
                    label = i
                Label(frame,text=label).pack()
                tkvars[i] = v = StringVar()
                for item in opt['items']:
                    w = Radiobutton(frame, text=item, variable=v, value=item).pack()
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

        from .core import Table
        self.parent = parent
        self.filename = filename
        self.df = None
        self.main = Toplevel()
        self.master = self.main
        self.main.title('Text Import')
        self.main.protocol("WM_DELETE_WINDOW", self.quit)
        self.main.grab_set()
        self.main.transient(parent)

        grps = {'formats':['delimiter','decimal','comment'],
                'data':['header','skiprows','index_col'],
                'other':['skipinitialspace','skip_blank_lines','parse_dates']}
        grps = OrderedDict(sorted(grps.items()))
        opts = self.opts = {'delimiter':{'type':'combobox','default':',',
                        'items':[',',' ',';'], 'tooltip':'seperator'},
                     'header':{'type':'entry','default':0,'label':'header',
                               'tooltip':'position of column header'},
                     'index_col':{'type':'entry','default':'','label':'index col',
                                'tooltip':''},
                     'decimal':{'type':'combobox','default':'.','items':['.',','],
                                'tooltip':'decimal point symbol'},
                     'comment':{'type':'entry','default':'#','label':'comment',
                                'tooltip':'comment symbol'},
                     'skipinitialspace':{'type':'checkbutton','default':0,'label':'skipinitialspace',
                                'tooltip':'skip initial space'},
                     'skiprows':{'type':'entry','default':0,'label':'skiprows',
                                'tooltip':'rows to skip'},
                     'skip_blank_lines':  {'type':'checkbutton','default':0,'label':'skipblanklines',
                                'tooltip':'do not use blank lines'},
                     'parse_dates':{'type':'entry','default':'','label':'parse date',
                                'tooltip':''},
                     #'prefix':{'type':'entry','default':None,'label':'prefix',
                     #           'tooltip':''}
                     #'nrows':{'type':'entry','default':None,'label':'number of rows',
                     #           'tooltip':'rows to read'},
                     }
        optsframe, self.tkvars, w = dialogFromOptions(self.main, opts, grps)

        tf = Frame(self.main)
        tf.pack(side=TOP,fill=BOTH,expand=1)
        self.previewtable = Table(tf,rows=0,columns=0)
        self.previewtable.show()
        self.update()

        optsframe.pack(side=TOP,fill=BOTH)
        bf = Frame(self.main)
        bf.pack(side=TOP,fill=BOTH)
        b = Button(bf, text="Update preview", command=self.update)
        b.pack(side=LEFT,fill=X,expand=1,pady=1)
        b = Button(bf, text="Import", command=self.doImport)
        b.pack(side=LEFT,fill=X,expand=1,pady=1)
        b = Button(bf, text="Cancel", command=self.quit)
        b.pack(side=LEFT,fill=X,expand=1,pady=1)
        self.main.wait_window()
        return

    def update(self):
        kwds = {}
        for i in self.opts:
            val = self.tkvars[i].get()
            if val == '':
                val=None
            kwds[i] = val
        self.kwds = kwds
        f = pd.read_csv(self.filename, chunksize=100, **kwds)
        df = f.get_chunk(100)
        model = TableModel(dataframe=df)
        self.previewtable.updateModel(model)
        self.previewtable.showIndex()
        self.previewtable.redraw()
        return

    def doImport(self):
        self.df = pd.read_csv(self.filename)
        self.quit()
        return

    def quit(self):
        self.main.destroy()
        return

class CombineDialog(Frame):
    """Provides a frame for setting up combine operations"""

    def __init__(self, parent=None, df1=None, df2=None):

        self.parent = parent
        self.main = Toplevel()
        self.master = self.main
        self.main.title('Merge/Join/Concat')
        self.main.protocol("WM_DELETE_WINDOW", self.quit)
        self.main.grab_set()
        self.main.transient(parent)
        self.df1 = df1
        self.df2 = df2
        self.merged = None

        f = Frame(self.main)
        f.pack(side=TOP,fill=BOTH)
        ops = ['merge','concat']
        self.opvar = StringVar()
        w = Combobox(f, values=ops,
                 textvariable=self.opvar,width=14 )
        w.set('merge')
        Label(f,text='operation:').pack()
        w.pack()

        #buttons to add for each op.
        #merge: left, right, how, suff1, suff2
        #concat assumes homogeneous dfs
        how = ['inner','outer','left','right']
        grps = {'merge': ['left_on','right_on','suffix1','suffix2','how'],
                'concat': ['join','ignore_index']}
        self.grps = grps = OrderedDict(sorted(grps.items()))
        cols1 = list(df1.columns)
        cols2 = list(df2.columns)
        opts = self.opts = {'left_on':{'type':'combobox','default':'',
                            'items':cols1, 'tooltip':'left column'},
                            'right_on':{'type':'combobox','default':'',
                            'items':cols2, 'tooltip':'right column'},
                            'suffix1':{'type':'entry','default':'_1','label':'left suffix'},
                            'suffix2':{'type':'entry','default':'_2','label':'right suffix'},
                            'how':{'type':'combobox','default':'inner',
                            'items':how, 'tooltip':'how to merge'},
                            'join':{'type':'combobox','default':'inner',
                            'items':['inner','outer'], 'tooltip':'how to join'},
                            'ignore_index':{'type':'checkbutton','default':0,'label':'ignore index',
                             'tooltip':'do not use the index values on the concatenation axis'},
                             }
        optsframe, self.tkvars, w = dialogFromOptions(self.main, opts, grps)
        optsframe.pack(side=TOP,fill=BOTH)

        bf = Frame(self.main)
        bf.pack(side=TOP,fill=BOTH)
        b = Button(bf, text="Apply", command=self.apply)
        b.pack(side=LEFT,fill=X,expand=1,pady=1)
        b = Button(bf, text="Cancel", command=self.quit)
        b.pack(side=LEFT,fill=X,expand=1,pady=1)
        b = Button(bf, text="Help", command=self.help)
        b.pack(side=LEFT,fill=X,expand=1,pady=1)
        self.main.wait_window()
        return

    def apply(self):
        """Apply operation"""
        kwds = {}
        method = self.opvar.get()
        for i in self.opts:
            if i not in self.grps[method]:
                continue
            val = self.tkvars[i].get()
            if val == '':
                val=None
            kwds[i] = val
        print (kwds)
        if method == 'merge':
            s=(kwds['suffix1'],kwds['suffix2'])
            del kwds['suffix1']
            del kwds['suffix2']
            m = pd.merge(self.df1,self.df2,on=None,suffixes=s, **kwds)
        elif method == 'concat':
            m = pd.concat([self.df1,self.df2], **kwds)
        print (m)
        #if successful ask user to replace table and close
        if len(m) > 0:
            n = messagebox.askyesno("Join done",
                                     "Merge/concat success.\nReplace table with new data?",
                                     parent=self.parent)
            if n == True:
                self.merged = m
                self.quit()
            else:
                self.merged = None
        return

    def help(self):
        import webbrowser
        link='http://pandas.pydata.org/pandas-docs/stable/merging.html'
        webbrowser.open(link,autoraise=1)
        return

    def quit(self):
        self.main.destroy()
        return

class SimpleEditor(Frame):

    def __init__(self, parent=None, width=100, height=40):

        from tkinter.scrolledtext import ScrolledText
        Frame.__init__(self, parent)
        st = self.text = ScrolledText(self, width=width, height=height)
        st.pack(in_=self, fill=BOTH, expand=Y)
        st.config(font='monospace 12')
        btnform = Frame(self)
        btnform.pack()
        Button(btnform, text='Save',  command=self.onSave).pack(side=LEFT)
        #Button(frm, text='Cut',   command=self.onCut).pack(side=LEFT)
        #Button(frm, text='Paste', command=self.onPaste).pack(side=LEFT)
        Button(btnform, text='Find',  command=self.onFind).pack(side=LEFT)
        self.target=''
        return

    def onSave(self):
        filename = filedialog.asksaveasfilename(defaultextension='.txt',
                                    initialdir=os.path.expanduser('~'),
                                     filetypes=(('Text files', '*.txt'),
                                                ('All files', '*.*')))
        if filename:
            with open(filename, 'w') as stream:
                stream.write(self.text.get('1.0',END))
        return

    def onFind(self):
        self.target = simpledialog.askstring('SimpleEditor', 'Search String?',
                                initialvalue=self.target)
        if self.target:
            where = self.text.search(self.target, INSERT, END, nocase=True)
            if where:
                pastit = '{}+{}c'.format(where, len(self.target))
                self.text.tag_add(SEL, where, pastit)
                self.text.mark_set(INSERT, pastit)
                self.text.see(INSERT)
                self.text.focus()
