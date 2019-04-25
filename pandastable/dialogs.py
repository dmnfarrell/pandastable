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

from __future__ import absolute_import, division, print_function
import sys,os,types
import platform
try:
    from tkinter import *
    from tkinter.ttk import *
    from tkinter import filedialog, messagebox, simpledialog
    from tkinter.simpledialog import Dialog
    from tkinter import Scale
    from tkinter.scrolledtext import ScrolledText
except:
    from Tkinter import *
    from ttk import *
    from tkSimpleDialog import Dialog
    from Tkinter import Scale
    import tkFileDialog as filedialog
    import tkSimpleDialog as simpledialog
    import tkMessageBox as messagebox
    from ScrolledText import ScrolledText

from collections import OrderedDict
import webbrowser
import numpy as np
import pandas as pd
from .data import TableModel
from . import util, images

def getParentGeometry(parent):
    x = parent.winfo_rootx()
    y = parent.winfo_rooty()
    w = parent.winfo_width()
    h = parent.winfo_height()
    return x,y,w,h

def getDictfromTkVars(opts, tkvars, widgets):
    kwds = {}
    for i in opts:
        if not i in tkvars:
            continue
        if opts[i]['type'] == 'listbox':
            items = widgets[i].curselection()
            kwds[i] = [widgets[i].get(j) for j in items]
            #print (items, kwds[i])
        else:
            try:
                kwds[i] = int(tkvars[i].get())
            except:
                kwds[i] = tkvars[i].get()
    return kwds

def pickColor(parent, oldcolor):

    import tkinter.colorchooser
    ctuple, newcolor = tkinter.colorchooser.askcolor(title='pick a color',
                                                     initialcolor=oldcolor,
                                                     parent=parent)
    if ctuple == None:
        return None
    return str(newcolor)

def dialogFromOptions(parent, opts, groups=None, callback=None,
                        sticky='news',  layout='horizontal'):
    """Auto create tk vars and widgets for corresponding options and
       and return the enclosing frame"""

    tkvars = {}
    widgets = {}
    dialog = Frame(parent)
    if groups == None:
        groups = {'options': opts.keys()}
    c=0
    row=0
    for g in groups:
        if g == 'hidden':
            continue
        if layout=='horizontal':
            row=0; c+=1
            side=LEFT
            fill=Y
        else:
            c=0; row+=1
            side=TOP
            fill=X
        frame = LabelFrame(dialog, text=g)
        #frame.grid(row=row,column=c,sticky=sticky)
        frame.pack(side=side,fill=fill,expand=False)

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
                if type(opts[i]['default']) is int:
                    tkvars[i] = v = IntVar()
                else:
                    tkvars[i] = v = StringVar()
                v.set(opts[i]['default'])
                w = Entry(frame,textvariable=v, width=w, command=callback)
            elif opt['type'] == 'scrolledtext':
                w = ScrolledText(frame, width=20, wrap=WORD)
                tkvars[i] = None
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
                if 'width' in opt:
                    w=opt['width']
                else:
                    w=16
                Label(frame,text=label).pack()
                tkvars[i] = v = StringVar()
                v.set(opts[i]['default'])
                w = Combobox(frame, values=opt['items'],
                         textvariable=v,width=w,
                         validatecommand=callback,validate='key')
                w.set(opt['default'])
                if 'tooltip' in opt:
                    ToolTip.createToolTip(w, opt['tooltip'])
            elif opt['type'] == 'spinbox':
                if 'label' in opt:
                   label=opt['label']
                else:
                    label = i
                Label(frame,text=label).pack()
                tkvars[i] = v = StringVar()
                w = Spinbox(frame, values=opt['items'],
                         textvariable=v,width=w,
                         validatecommand=callback,validate='key')
                w.set(opt['default'])
                #if 'tooltip' in opt:
                #    ToolTip.createToolTip(w, opt['tooltip'])
            elif opt['type'] == 'listbox':
                if 'label' in opt:
                   label=opt['label']
                else:
                    label = i
                Label(frame,text=label).pack()
                w,v = addListBox(frame, values=opt['items'],width=12)
                tkvars[i] = v #add widget instead of var
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
                w = Scale(frame,label=opt['label'],
                         from_=fr,to=to,
                         orient='horizontal',
                         resolution=opt['interval'],
                         variable=v)
            elif opt['type'] == 'colorchooser':
                tkvars[i] = v = StringVar()
                clr = opts[i]['default']
                v.set(clr)
                def func(var):
                    clr=var.get()
                    new=pickColor(parent,clr)
                    if new != None:
                        var.set(new)
                w = Button(frame, text=opt['label'], command=lambda v=v : func(v))

            if w != None:
                w.pack(fill=BOTH,expand=1,pady=1)
                widgets[i] = w
            row+=1

    return dialog, tkvars, widgets

def addButton(frame, name, callback, img=None, tooltip=None,
              side=TOP, compound=None, width=None, padding=None):
    """Add a button with image, toolip to a tkinter frame"""

    #style = ttk.Style()
    #style.configure('TButton', padding=1)
    if img==None:
        b = Button(frame, text=name, command=callback)
    else:
        b = Button(frame, text=name, command=callback, width=width,
                         image=img, compound=compound, padding=padding)
    b.image = img
    b.pack(side=side,fill=X,pady=padding)
    if tooltip != None:
        ToolTip.createToolTip(b, tooltip)
    return

def applyStyle(w):
    """Apply style to individual widget to prevent widget color issues on linux"""

    plf = util.checkOS()
    if plf in ['linux','darwin']:
        bg = Style().lookup('TLabel.label', 'background')
        w.configure(fg='black', bg=bg,
                     activeforeground='white', activebackground='#0174DF')
    return

def setWidgetStyles(widgets):
    """set styles of list of widgets"""

    style = Style()
    bg = style.lookup('TLabel.label', 'background')
    for w in widgets:
        try:
            w.configure(fg='black', bg=bg)
        except:
            pass
    return

class Progress():
    """ threaded progress bar for tkinter gui """
    def __init__(self, parent, side=LEFT):
        import threading
        self.maximum = 100
        self.interval = 10
        self.progressbar = Progressbar(parent, orient=HORIZONTAL,
                                           mode="indeterminate",
                                           maximum=self.maximum)
        #self.progressbar.grid(row=row, column=column,
        #                      columnspan=columnspan, sticky="we")
        self.progressbar.pack(fill=X,side=side)
        self.thread = threading.Thread()
        self.thread.__init__(target=self.progressbar.start(self.interval),
                             args=())
        self.thread.start()

    def pb_stop(self):
        """ stops the progress bar """
        if not self.thread.isAlive():
            VALUE = self.progressbar["value"]
            self.progressbar.stop()
            self.progressbar["value"] = VALUE

    def pb_start(self):
        """ starts the progress bar """
        if not self.thread.isAlive():
            VALUE = self.progressbar["value"]
            self.progressbar.configure(mode="indeterminate",
                                       maximum=self.maximum,
                                       value=VALUE)
            self.progressbar.start(self.interval)

    def pb_clear(self):
        """ stops the progress bar """
        if not self.thread.isAlive():
            self.progressbar.stop()
            self.progressbar.configure(mode="determinate", value=0)

    def pb_complete(self):
        """ stops the progress bar and fills it """
        if not self.thread.isAlive():
            self.progressbar.stop()
            self.progressbar.configure(mode="determinate",
                                       maximum=self.maximum,
                                       value=self.maximum)

class MultipleValDialog(Dialog):
    """Simple dialog to get multiple values"""

    def __init__(self, parent, title=None, initialvalues=None, labels=None,
                    types=None, tooltips=None, width=14, **kwargs):
        if labels != None and types is not None:
            self.initialvalues = initialvalues
            self.labels = labels
            self.types = types
            self.tooltips = tooltips
            self.maxwidth = width

        Dialog.__init__(self, parent, title)
        #super(MultipleValDialog, self).__init__(parent, title)
        return

    def body(self, master):

        r=0
        self.vrs=[];self.entries=[]
        for i in range(len(self.labels)):
            Label(master, text=self.labels[i]).grid(row=r,column=0,sticky='news')
            if self.types[i] in ['int','checkbutton']:
                self.vrs.append(IntVar())
            else:
                self.vrs.append(StringVar())
            default = self.initialvalues[i]
            if self.types[i] == 'password':
                s='*'
            else:
                s=None
            if self.types[i] == 'combobox':
                self.vrs[i].set(default[0])
                w = Combobox(master, values=default,
                         textvariable=self.vrs[i],width=14)
                self.entries.append(w)
            elif self.types[i] == 'listbox':
                f,w = addListBox(master, values=default,width=14)
                self.entries.append(f)
                self.vrs[i] = w #add widget instead of var
            elif self.types[i] == 'checkbutton':
                self.vrs[i].set(default)
                w = Checkbutton(master, text='',
                         variable=self.vrs[i])
                self.entries.append(w)
            else:
                if default == None:
                    default=''
                self.vrs[i].set(default)
                self.entries.append(Entry(master, textvariable=self.vrs[i], width=self.maxwidth, show=s))
            self.entries[i].grid(row=r, column=1,padx=2,pady=2,sticky='ew')
            if self.tooltips != None:
                ToolTip.createToolTip(self.entries[i], self.tooltips[i])
            r+=1
        s=Style()
        bg = s.lookup('TLabel.label', 'background')
        self.configure(background=bg)
        master.configure(background=bg)
        self.option_add("*background", bg)
        self.option_add("*foreground", 'black')
        return self.entries[0] # initial focus

    def apply(self):
        self.result = True
        self.results = []
        for i in range(len(self.labels)):
            if self.types[i] == 'listbox':
                self.results.append(self.vrs[i].getSelectedItem())
            else:
                self.results.append(self.vrs[i].get())
        return

    def getResults(self, null=None):
        """Return a dict of options/values"""

        res = dict(zip(self.labels,self.results))
        #replace null values with None
        if null != None:
            for r in res:
                if res[r] == null: res[r] = None
        for r in res:
            try:
                res[r] = int(res[r])
            except:
                pass
        return res

class ToolTip(object):
    """Tooltip class for tkinter widgets"""
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text, event=None):
        "Display text in tooltip window"

        self.text = text
        if self.tipwindow or not self.text:
            return

        x, y, cx, cy = self.widget.bbox("insert")
        x = x + event.x
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 10
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

    def hidetip(self, event=None):
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
            toolTip.showtip(text, event)
        def leave(event):
            toolTip.hidetip(event)
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)
        return

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

        delimiters = [',',r'\t',' ',';','/','&','|','^','+','-']
        encodings = ['utf-8','ascii','iso8859_15','cp037','cp1252','big5','euc_jp']
        timeformats = ['infer','%d/%m/%Y','%Y/%m/%d','%Y/%d/%m',
                        '%Y-%m-%d %H:%M:%S','%Y-%m-%d %H:%M',
                        '%d-%m-%Y %H:%M:%S','%d-%m-%Y %H:%M']
        grps = {'formats':['delimiter','decimal','comment'],
                'data':['header','skiprows','index_col','skipinitialspace',
                        'skip_blank_lines','parse_dates','time format','encoding','names'],
                'other':['rowsperfile']}
        grps = OrderedDict(sorted(grps.items()))
        opts = self.opts = {'delimiter':{'type':'combobox','default':',',
                        'items':delimiters, 'tooltip':'seperator'},
                     'header':{'type':'entry','default':0,'label':'header',
                               'tooltip':'position of column header'},
                     'index_col':{'type':'entry','default':'','label':'index col',
                                'tooltip':''},
                     'decimal':{'type':'combobox','default':'.','items':['.',','],
                                'tooltip':'decimal point symbol'},
                     'comment':{'type':'entry','default':'#','label':'comment',
                                'tooltip':'comment symbol'},
                     'skipinitialspace':{'type':'checkbutton','default':0,'label':'skip initial space',
                                'tooltip':'skip initial space'},
                     'skiprows':{'type':'entry','default':0,'label':'skiprows',
                                'tooltip':'rows to skip'},
                     'skip_blank_lines':  {'type':'checkbutton','default':0,'label':'skip blank lines',
                                'tooltip':'do not use blank lines'},
                     'parse_dates':  {'type':'checkbutton','default':1,'label':'parse dates',
                                'tooltip':'try to parse date/time columns'},
                     'time format': {'type':'combobox','default':'','items':timeformats,
                                'tooltip':'date/time format'},
                     'encoding':{'type':'combobox','default':'utf-8','items':encodings,
                                'tooltip':'file encoding'},
                     #'prefix':{'type':'entry','default':None,'label':'prefix',
                     #           'tooltip':''}
                     'rowsperfile':{'type':'entry','default':'','label':'rows per file',
                                'tooltip':'rows to read'},
                     'names':{'type':'entry','default':'','label':'column names',
                                'tooltip':'col labels'},
                     }
        bf = Frame(self.main)
        bf.pack(side=LEFT,fill=BOTH)
        optsframe, self.tkvars, w = dialogFromOptions(bf, opts, grps,
                                    sticky='nwe', layout='vertical')

        self.m = PanedWindow(self.main, orient=VERTICAL)
        self.m.pack(side=LEFT,fill=BOTH,expand=1)
        self.textpreview = ScrolledText(self.main, width=100, height=10, bg='white')
        self.m.add(self.textpreview, weight=3)
        tf = Frame(self.main)
        self.m.add(tf, weight=1)
        self.previewtable = Table(tf,rows=0,columns=0)
        self.previewtable.show()
        self.update()

        optsframe.pack(side=TOP,fill=BOTH)
        b = Button(bf, text="Update preview", command=self.update)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="Import", command=self.doImport)
        b.pack(side=TOP,fill=X,pady=2)
        b = Button(bf, text="Cancel", command=self.quit)
        b.pack(side=TOP,fill=X,pady=2)
        self.main.wait_window()
        return

    def showText(self):
        """show text contents"""

        with open(self.filename, 'r') as stream:
            try:
                text = stream.read()
            except:
                text = 'failed to preview, check encoding and then update preview'
        self.textpreview.delete('1.0', END)
        self.textpreview.insert('1.0', text)
        return

    def update(self):
        """Reload previews"""

        kwds = {}
        other = ['rowsperfile','time format']
        for i in self.opts:
            if i in other:
                continue
            try:
                val = self.tkvars[i].get()
            except:
                val=None
            if val == '':
                val=None
            if self.opts[i]['type'] == 'checkbutton':
                val = bool(val)
            elif type(self.opts[i]['default']) != int:
                try:
                    val=int(val)
                except:
                    pass
            kwds[i] = val
        self.kwds = kwds
        timeformat = self.tkvars['time format'].get()
        dateparse = lambda x: pd.datetime.strptime(x, timeformat)
        self.showText()
        try:
            f = pd.read_csv(self.filename, chunksize=400, error_bad_lines=False,
                        warn_bad_lines=False, date_parser=dateparse, **kwds)
        except Exception as e:
            print ('read csv error')
            print (e)
            return
        try:
            df = f.get_chunk()
        except pandas.errors.ParserError:
            print ('parser error')
            df = pd.DataFrame()

        model = TableModel(dataframe=df)
        self.previewtable.updateModel(model)
        self.previewtable.showIndex()
        self.previewtable.redraw()
        return

    def doImport(self):
        """Do the import"""

        '''pw = Toplevel(self.main)
        pb = Progressbar(pw, orient='horizontal', mode='indeterminate')
        pb.pack(expand=True, fill=BOTH, side=TOP)
        pb.start(500)'''

        self.update()
        self.df = pd.read_csv(self.filename, **self.kwds)
        self.quit()
        return

    def quit(self):
        self.main.destroy()
        return

class CombineDialog(Frame):
    """Provides a frame for setting up merge/combine operations"""

    def __init__(self, parent=None, df1=None, df2=None):

        self.parent = parent
        self.main = Toplevel()
        self.master = self.main
        self.main.title('Merge/Join/Concat')
        self.main.protocol("WM_DELETE_WINDOW", self.quit)
        self.main.grab_set()
        self.main.transient(parent)
        self.main.resizable(width=False, height=False)
        self.df1 = df1
        self.df2 = df2
        self.merged = None

        wf = Frame(self.main)
        wf.pack(side=LEFT,fill=BOTH)
        f=Frame(wf)
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
                'concat': ['join','ignore_index','verify_integrity']}
        self.grps = grps = OrderedDict(sorted(grps.items()))
        cols1 = list(df1.columns)
        cols2 = list(df2.columns)
        opts = self.opts = {'left_on':{'type':'listbox','default':'',
                            'items':cols1, 'tooltip':'left column'},
                            'right_on':{'type':'listbox','default':'',
                            'items':cols2, 'tooltip':'right column'},
                            #'left_index':{'type':'checkbutton','default':0,'label':'use left index'},
                            #'right_index':{'type':'checkbutton','default':0,'label':'use right index'},
                            'suffix1':{'type':'entry','default':'_1','label':'left suffix'},
                            'suffix2':{'type':'entry','default':'_2','label':'right suffix'},
                            'how':{'type':'combobox','default':'inner',
                            'items':how, 'tooltip':'how to merge'},
                            'join':{'type':'combobox','default':'inner',
                            'items':['inner','outer'], 'tooltip':'how to join'},
                            'ignore_index':{'type':'checkbutton','default':0,'label':'ignore index',
                                'tooltip':'do not use the index values on the concatenation axis'},
                            'verify_integrity':{'type':'checkbutton','default':0,'label':'check duplicates'},
                             }
        optsframe, self.tkvars, w = dialogFromOptions(wf, opts, grps, sticky='new')
        optsframe.pack(side=TOP,fill=BOTH)

        bf = Frame(wf)
        bf.pack(side=TOP,fill=BOTH)
        b = Button(bf, text="Apply", command=self.apply)
        b.pack(side=LEFT,fill=X,expand=1,pady=1)
        b = Button(bf, text="Close", command=self.quit)
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
            if self.opts[i]['type'] == 'listbox':
                val = self.tkvars[i].getSelectedItem()
            else:
                val = self.tkvars[i].get()
            if val == '':
                val=None
            kwds[i] = val
        #print (kwds)
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
            self.getResult(m)
        else:
            f = self.tbf = Frame(self.main)
            f.pack(side=LEFT,fill=BOTH)
            st = ScrolledText(f, bg='white', fg='black')
            st.pack(in_=f, fill=BOTH, expand=1)
            msg = 'result is empty, check your columns. column types might differ'
            st.insert(END, msg)
        return

    def getResult(self, df):
        """Show result of merge and let user choose to replace current table"""

        self.result = df
        from . import core
        if hasattr(self, 'tbf'):
            self.tbf.destroy()
        f = self.tbf = Frame(self.main)
        f.pack(side=LEFT,fill=BOTH)
        newtable = core.Table(f, dataframe=df, showstatusbar=1)
        newtable.adjustColumnWidths()
        newtable.show()
        bf = Frame(f)
        bf.grid(row=4,column=0,columnspan=2,sticky='news',padx=2,pady=2)
        b = Button(bf, text="Copy Table", command=lambda : self.result.to_clipboard(sep=','))
        b.pack(side=RIGHT)
        b = Button(bf, text="Replace Current Table", command=self.replaceTable)
        b.pack(side=RIGHT)
        return

    def replaceTable(self):
        """replace parent table"""

        n = messagebox.askyesno("Replace with merged",
                                 "Are you sure?",
                                  parent=self.main)
        if not n:
            return
        df = self.result
        model = TableModel(dataframe=df)
        self.parent.updateModel(model)
        self.parent.redraw()
        return

    def help(self):
        link='http://pandas.pydata.org/pandas-docs/stable/merging.html'
        webbrowser.open(link,autoraise=1)
        return

    def quit(self):
        self.main.destroy()
        return

class BaseDialog(Frame):
    """Generic dialog - inherit from this and customise the
       createWidgets and apply methods."""

    def __init__(self, parent=None, df=None, title=''):

        self.parent = parent
        self.main = Toplevel()
        self.master = self.main
        x,y,w,h = getParentGeometry(self.parent)
        self.main.geometry('+%d+%d' %(x+w/2-200,y+h/2-200))
        self.main.title(title)
        self.main.protocol("WM_DELETE_WINDOW", self.quit)
        self.main.grab_set()
        self.main.transient(parent)
        self.main.resizable(width=False, height=False)
        self.df = df
        self.result = None
        return

    def createWidgets(self, m):
        """Override this"""

        cols = list(self.df.columns)
        f = LabelFrame(m, text='frame')
        f.pack(side=LEFT,fill=BOTH,padx=2)
        self.buttonsFrame()
        return

    def buttonsFrame(self):
        bf = Frame(self.main)
        bf.pack(side=TOP,fill=BOTH)
        b = Button(bf, text="Apply", command=self.apply)
        b.pack(side=LEFT,fill=X,expand=1,pady=2)
        b = Button(bf, text="Close", command=self.quit)
        b.pack(side=LEFT,fill=X,expand=1,pady=2)
        b = Button(bf, text="Help", command=self.help)
        b.pack(side=LEFT,fill=X,expand=1,pady=2)
        return

    def apply(self):
        """Code to run when Apply is pressed"""
        return

    def help(self):
        """Help button code"""
        return

    def quit(self):
        self.main.destroy()
        return

class CrosstabDialog(BaseDialog):
    def __init__(self, parent=None, df=None, title=''):

        BaseDialog.__init__(self, parent, df, title)
        m = Frame(self.main)
        m.pack(side=TOP)
        self.createWidgets(m)
        return

    def createWidgets(self, m):
        """Create a set of grp-agg-func options together"""

        cols = list(self.df.columns)
        funcs = ['mean','median','sum','size','count','std','first','last',
                 'min','max','var']
        f = LabelFrame(m, text='crosstab')
        f.pack(side=LEFT,fill=BOTH,padx=2)
        w,self.colsvar = addListBox(f, values=cols,width=14, label='columns')
        w.pack(side=LEFT,padx=2)
        self.vars = OrderedDict()
        w,self.rowsvar = addListBox(f, values=cols,width=14,label='rows')
        w.pack(side=LEFT,padx=2)
        valcols = list(self.df.select_dtypes(include=[np.float64,np.int32,np.int64]))
        w,self.valsvar = addListBox(f, values=valcols,width=14,label='values')
        w.pack(side=LEFT,padx=2)
        w,self.funcvar = addListBox(f, values=funcs,width=14,label='functions')
        w.pack(side=LEFT,padx=2)
        self.marginsvar = BooleanVar()
        w = Checkbutton(self.main,text='add row/column subtotals',
                         variable=self.marginsvar)
        w.pack(padx=2,pady=2)
        self.buttonsFrame()
        return

    def apply(self):
        """Apply crosstab"""

        cols = self.colsvar.getSelectedItem()
        rows = self.rowsvar.getSelectedItem()
        vals = self.valsvar.getSelectedItem()
        funcs = self.funcvar.getSelectedItem()
        margins = self.marginsvar.get()
        df = self.df
        rowdata = [df[r] for r in rows]
        coldata = [df[c] for c in cols]
        if vals == '':
            vals=None
        else:
            vals=df[vals]
        if funcs == '':
            funcs=None
        elif len(funcs) != len(cols):
            funcs = [funcs[0] for i in cols]

        self.result = pd.crosstab(rowdata, coldata, values=vals, aggfunc=funcs, margins=margins)
        self.parent.createChildTable(self.result, '', index=True)
        return

    def help(self):
        link='https://pandas.pydata.org/pandas-docs/stable/generated/pandas.crosstab.html'
        webbrowser.open(link,autoraise=1)
        return

class AggregateDialog(BaseDialog):
    """Provides a frame for split-apply-combine operations"""

    def __init__(self, parent=None, df=None):

        BaseDialog.__init__(self, parent, df)
        m = Frame(self.main)
        m.pack(side=TOP)
        self.createWidgets(m)
        f = Frame(self.main)
        f.pack(side=TOP)
        self.mapcolfuncs = BooleanVar()
        w = Checkbutton(f,text='map columns to functions',
                         variable=self.mapcolfuncs)
        w.pack(padx=2,pady=2)
        ToolTip.createToolTip(w, 'do 1-1 mapping of cols to functions')
        self.keepcols = BooleanVar()
        self.keepcols.set(False)
        w = Checkbutton(f,text='set grouping column as index',
                         variable=self.keepcols)
        w.pack(padx=2,pady=2)

        #self.main.wait_window()
        return

    def createWidgets(self, m):
        """Create a set of grp-agg-func options together"""

        cols = list(self.df.columns)
        funcs = ['mean','median','sum','size','count','std','first','last',
                 'min','max','var']

        f = LabelFrame(m, text='group by')
        f.pack(side=LEFT,fill=BOTH,padx=2)
        w,self.grpvar = addListBox(f, values=cols,width=14, label='columns')
        w.pack()
        self.vars = OrderedDict()
        f = LabelFrame(m, text='aggregate on')
        f.pack(side=LEFT,fill=BOTH,padx=2)
        w,self.aggvar = addListBox(f, values=cols,width=14,label='columns')
        w.pack(side=LEFT,padx=2)
        w,self.funcvar = addListBox(f, values=funcs,width=14,label='functions')
        w.pack(side=LEFT,padx=2)
        self.buttonsFrame()
        return

    def apply(self):
        """Apply operation"""

        funcs = self.funcvar.getSelectedItem()
        grpcols = self.grpvar.getSelectedItem()
        agg = self.aggvar.getSelectedItem()
        mapfuncs = self.mapcolfuncs.get()
        keepcols = self.keepcols.get()
        #print (grpcols, agg, funcs)

        if mapfuncs == True:
            aggdict = (dict(zip(agg,funcs)))
        else:
            aggdict = {}
            if len(funcs)==1: funcs=funcs[0]
            for a in agg:
                aggdict[a] = funcs
        #print (aggdict)
        self.result = self.df.groupby(grpcols,as_index=keepcols).agg(aggdict)
        self.parent.createChildTable(self.result, 'aggregated', index=True)
        #self.quit()
        return

    def copyResult(self, ):
        if self.result is not None:
            self.parent.createChildTable(self.result, 'aggregated', index=True)

    def help(self):
        link='http://pandas.pydata.org/pandas-docs/stable/groupby.html'
        webbrowser.open(link,autoraise=1)
        return

    def quit(self):
        self.main.destroy()
        return

def addListBox(parent, values=[], width=10, height=6, label=''):
    """Add an EasyListBox"""

    frame=Frame(parent)
    Label(frame, text=label).grid(row=0)
    yScroll = Scrollbar(frame, orient = VERTICAL)
    yScroll.grid(row = 1, column = 1, sticky = N+S)
    listItemSelected = lambda index: index
    lbx = EasyListbox(frame, width, height, yScroll.set, listItemSelected)
    lbx.grid(row = 1, column = 0, sticky = N+S+E+W)
    frame.columnconfigure(0, weight = 1)
    frame.rowconfigure(0, weight = 1)
    yScroll["command"] = lbx.yview
    for i in values:
        lbx.insert(END, i)
    return frame, lbx

def getListBoxSelection(w):
    items = w.curselection()
    return [w.get(j) for j in items]

class AutoScrollbar(Scrollbar):
    """A scrollbar that hides itself if it's not needed. only \
       works if you use the grid geometry manager."""

    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.tk.call("grid", "remove", self)
        else:
            self.grid()
        Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        """pack"""
        raise TclError("cannot use pack with this widget")
        return

    def place(self, **kw):
        """place"""
        raise TclError("cannot use place with this widget")
        return

class VerticalScrolledFrame(Frame):
    """A pure Tkinter scrollable frame \
    see http://tkinter.unpythonic.net/wiki/VerticalScrolledFrame. \
    Use the 'interior' attribute to place widgets inside the scrollable frame.
    """

    def __init__(self, parent, height=None, width=None, *args, **kw):
        Frame.__init__(self, parent, *args, **kw)

        # create a canvas object and a vertical scrollbar for scrolling it
        #vscrollbar = AutoScrollbar(self, orient=VERTICAL)
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        #vscrollbar.grid(row=0,column=2,rowspan=1,sticky='news',pady=0)
        canvas = Canvas(self, bd=0, highlightthickness=0, height=height, width=width,
                            yscrollcommand=vscrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        #canvas.grid(row=0,column=0,rowspan=1,sticky='ns',pady=0)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)

        return

class EasyListbox(Listbox):
    """Customised list box to replace useless default one"""

    def __init__(self, parent, width, height, yscrollcommand, listItemSelected):
        self._listItemSelected = listItemSelected
        Listbox.__init__(self, parent,
                                 width = width, height = height,
                                 yscrollcommand = yscrollcommand,
                                 selectmode = MULTIPLE, exportselection=0)
        self.bind("<<ListboxSelect>>", self.triggerListItemSelected)
        self.configure(background='white', foreground='black',
                       selectbackground='#0174DF', selectforeground='white')
        return

    def triggerListItemSelected(self, event):
        """Strategy method to respond to an item selection in the list box. \
        Runs the client's listItemSelected method with the selected index.
        """

        if self.size() == 0: return
        widget = event.widget
        indexes = widget.curselection()
        #self._listItemSelected(index)

    def getSelectedIndex(self):
        """Returns the index of the selected item or -1 if no item is selected."""

        tup = self.curselection()
        if len(tup) == 0:
            return -1
        else:
            return tup

    def getSelectedItem(self):
        """Returns the selected item or the empty string if no item is selected."""

        index = self.getSelectedIndex()
        if index == -1:
            return ""
        else:
            return [self.get(i) for i in index]

    def setSelectedIndex(self, index):
        """Selects the item at the index if it's in the range."""

        if index < 0 or index >= self.size(): return
        self.selection_set(index, index)

    def clear(self):
        """Deletes all items from the list box."""

        while self.size() > 0:
            self.delete(0)

    def getIndex(self, item):
        """Returns the index of item if it's in the list box."""

        tup = self.get(0, self.size() - 1)
        if item in tup:
            return tup.index(item)
        else:
            return -1

class SimpleEditor(Frame):
    """Simple text editor"""

    def __init__(self, parent=None, width=100, height=40, font=None):

        Frame.__init__(self, parent)
        st = self.text = ScrolledText(self, width=width, height=height, bg='white', fg='black')
        st.pack(in_=self, fill=BOTH, expand=1)
        if font == None:
            if 'Windows' in platform.system():
                font = ('Courier New',10)
            else:
                font = 'monospace 10'
        st.config(font=font)
        btnform = Frame(self)
        btnform.pack(fill=BOTH)
        Button(btnform, text='Save',  command=self.onSave).pack(side=LEFT)
        #Button(frm, text='Cut',   command=self.onCut).pack(side=LEFT)
        #Button(frm, text='Paste', command=self.onPaste).pack(side=LEFT)
        Button(btnform, text='Find',  command=self.onFind).pack(side=LEFT)
        Button(btnform, text='Clear',  command=self.onClear).pack(side=LEFT)
        self.target=''
        return

    def onSave(self):
        """Save text"""

        filename = filedialog.asksaveasfilename(defaultextension='.txt',
                                    initialdir=os.path.expanduser('~'),
                                     filetypes=(('Text files', '*.txt'),
                                                ('All files', '*.*')))
        if filename:
            with open(filename, 'w') as stream:
                stream.write(self.text.get('1.0',END))
        return

    def onClear(self):
        """Clear text"""
        self.text.delete('1.0',END)
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

class FindReplaceDialog(Frame):
    """Find/replace dialog."""

    def __init__(self, table):
        parent = table.parentframe
        Frame.__init__(self, parent)
        self.parent = parent
        self.table = table
        self.coords = []
        self.current = 0 #coords of found cells
        self.setup()
        return

    def setup(self):

        sf = self
        sfont = "Helvetica 10 bold"
        Label(sf, text='Enter Search String:', font=sfont).pack(side=TOP,fill=X)
        self.searchvar = StringVar()
        e = Entry(sf, textvariable=self.searchvar)
        self.searchvar.trace("w", self.updated)
        e.bind('<Return>', self.find)
        e.pack(fill=BOTH,side=TOP,expand=1,padx=2,pady=2)
        Label(sf, text='Replace With:', font=sfont).pack(side=TOP,fill=X)
        self.replacevar = StringVar()
        e = Entry(sf, textvariable=self.replacevar)
        e.pack(fill=BOTH,side=TOP,expand=1,padx=2,pady=2)
        f = Frame(sf)
        f.pack(side=TOP, fill=BOTH, padx=2, pady=2)
        addButton(f, 'Find Next', self.findNext, None, None, side=LEFT)
        addButton(f, 'Find All', self.findAll, None, None, side=LEFT)
        addButton(f, 'Replace All', self.replace, None, None, side=LEFT)
        addButton(f, 'Clear', self.clear, None, None, side=LEFT)
        addButton(f, 'Close', self.close, None, None, side=LEFT)
        f = Frame(sf)
        f.pack(side=TOP, fill=BOTH, padx=2, pady=2)
        self.casevar = BooleanVar()
        cb=Checkbutton(f, text= 'case sensitive', variable=self.casevar, command=self.updated)
        cb.pack(side=LEFT)
        return

    def updated(self, name='', index='', mode=''):
        """Widgets changed so run search again"""
        self.search_changed=True
        return

    def find(self):
        """Do string search. Creates a masked dataframe for results and then stores each cell
        coordinate in a list."""

        table = self.table
        df = table.model.df
        df = df.astype('object').astype('str')
        s = self.searchvar.get()
        case = self.casevar.get()
        self.search_changed = False
        self.clear()
        if s == '':
            return
        found = pd.DataFrame()
        for col in df:
            found[col] = df[col].str.contains(s, na=False, case=case)
        #set the masked dataframe so that highlighted cells are shown on redraw
        table.highlighted = found
        i=0
        self.coords = []
        for r,row in found.iterrows():
            j=0
            for col,val in row.iteritems():
                if val is True:
                    #print (r,col,val, i, j)
                    self.coords.append((i,j))
                j+=1
            i+=1
        self.current = 0
        return

    def findAll(self):
        """Highlight all found cells"""

        table = self.table
        table.delete('temprect')
        df = table.model.df
        self.find()
        table.redraw()
        return

    def findNext(self):
        """Show next cell of search results"""

        table = self.table
        s = self.searchvar.get()
        if len(self.coords)==0  or self.search_changed == True:
            self.find()
        if len(self.coords)==0:
            return
        idx = self.current
        i,j = self.coords[idx]
        table.movetoSelection(row=i,col=j,offset=3)
        table.redraw()
        table.drawSelectedRect(i, j, color='red')
        self.current+=1
        if self.current>=len(self.coords):
            self.current=0
        return

    def replace(self):
        """Replace all instances of search text"""

        table = self.table
        table.storeCurrent()
        df = table.model.df
        s=self.searchvar.get()
        r=self.replacevar.get()
        case = self.casevar.get()
        #import re
        #r = re.compile(re.escape(r), re.IGNORECASE)
        table.model.df = df.replace(s,r,regex=True)
        table.redraw()
        self.search_changed = True
        return

    def clear(self):
        self.coords = []
        self.table.delete('temprect')
        self.table.highlighted = None
        self.table.redraw()
        return

    def close(self):
        self.clear()
        self.table.searchframe=None
        self.destroy()
        return

class QueryDialog(Frame):
    """Use string query to filter. Will not work with spaces in column
        names, so these would need to be converted first."""

    def __init__(self, table):
        parent = table.parentframe
        Frame.__init__(self, parent)
        self.parent = parent
        self.table = table
        self.setup()
        self.filters = []
        return

    def setup(self):

        qf = self
        sfont = "Helvetica 10 bold"
        Label(qf, text='Enter String Query:', font=sfont).pack(side=TOP,fill=X)
        self.queryvar = StringVar()
        e = Entry(qf, textvariable=self.queryvar, font="Courier 12 bold")
        e.bind('<Return>', self.query)
        e.pack(fill=BOTH,side=TOP,expand=1,padx=2,pady=2)
        self.fbar = Frame(qf)
        self.fbar.pack(side=TOP,fill=BOTH,expand=1,padx=2,pady=2)
        f = Frame(qf)
        f.pack(side=TOP, fill=BOTH, padx=2, pady=2)
        addButton(f, 'find', self.query, images.filtering(), 'apply filters', side=LEFT)
        addButton(f, 'add manual filter', self.addFilter, images.add(),
                  'add manual filter', side=LEFT)
        addButton(f, 'close', self.close, images.cross(), 'close', side=LEFT)
        self.applyqueryvar = BooleanVar()
        self.applyqueryvar.set(True)
        c = Checkbutton(f, text='show filtered only', variable=self.applyqueryvar,
                      command=self.query)
        c.pack(side=LEFT,padx=2)
        addButton(f, 'color rows', self.colorResult, images.color_swatch(), 'color filtered rows', side=LEFT)

        self.queryresultvar = StringVar()
        l = Label(f,textvariable=self.queryresultvar, font=sfont)
        l.pack(side=RIGHT)
        return

    def close(self):
        self.destroy()
        self.table.qframe = None
        self.table.showAll()

    def query(self, evt=None):
        """Do query"""

        table = self.table
        s = self.queryvar.get()
        if table.filtered == True:
            table.model.df = table.dataframe
        df = table.model.df
        mask = None

        #string query first
        if s!='':
            try:
                mask = df.eval(s)
            except:
                mask = df.eval(s, engine='python')
        #add any filters from widgets
        if len(self.filters)>0:
            mask = self.applyFilter(df, mask)
        if mask is None:
            table.showAll()
            self.queryresultvar.set('')
            return
        #apply the final mask
        self.filtdf = filtdf = df[mask]
        self.queryresultvar.set('%s rows found' %len(filtdf))

        if self.applyqueryvar.get() == 1:
            #replace current dataframe but keep a copy!
            table.dataframe = table.model.df.copy()
            table.delete('rowrect')
            table.multiplerowlist = []
            table.model.df = filtdf
            table.filtered = True
        else:
            idx = filtdf.index
            rows = table.multiplerowlist = table.getRowsFromIndex(idx)
            if len(rows)>0:
                table.currentrow = rows[0]

        table.redraw()
        return

    def addFilter(self):
        """Add a filter using widgets"""

        df = self.table.model.df
        fb = FilterBar(self, self.fbar, list(df.columns))
        fb.pack(side=TOP, fill=BOTH, expand=1, padx=2, pady=2)
        self.filters.append(fb)
        return

    def applyFilter(self, df, mask=None):
        """Apply the widget based filters, returns a boolean mask"""

        if mask is None:
            mask = df.index==df.index

        for f in self.filters:
            col, val, op, b = f.getFilter()
            try:
                val = float(val)
            except:
                pass
            #print (col, val, op, b)
            if op == 'contains':
                m = df[col].str.contains(str(val))
            elif op == 'equals':
                m = df[col]==val
            elif op == 'not equals':
                m = df[col]!=val
            elif op == '>':
                m = df[col]>val
            elif op == '<':
                m = df[col]<val
            elif op == 'is empty':
                m = df[col].isnull()
            elif op == 'not empty':
                m = ~df[col].isnull()
            elif op == 'excludes':
                m = -df[col].str.contains(val)
            elif op == 'starts with':
                m = df[col].str.startswith(val)
            elif op == 'has length':
                m = df[col].str.len()>val
            elif op == 'is number':
                m = df[col].astype('object').str.isnumeric()
            elif op == 'is lowercase':
                m = df[col].astype('object').str.islower()
            elif op == 'is uppercase':
                m = df[col].astype('object').str.isupper()
            else:
                continue
            if b == 'AND':
                mask = mask & m
            elif b == 'OR':
                mask = mask | m
            elif b == 'NOT':
                mask = mask ^ m
        return mask

    def colorResult(self):
        """Color filtered rows in main table"""

        table=self.table
        if not hasattr(self.table,'dataframe') or not hasattr(self, 'filtdf'):
            return
        clr = self.table.getaColor('#dcf1fc')
        if clr is None: return
        df = table.model.df = table.dataframe
        idx = self.filtdf.index
        rows = table.multiplerowlist = table.getRowsFromIndex(idx)
        table.setRowColors(rows, clr, cols='all')
        return

    def update(self):
        df = self.table.model.df
        cols = list(df.columns)
        for f in self.filters:
            f.update(cols)
        return

class FilterBar(Frame):
    """Class providing filter widgets"""

    operators = ['contains','excludes','equals','not equals','>','<','is empty','not empty',
                 'starts with','ends with','has length','is number','is lowercase','is uppercase']
    booleanops = ['AND','OR','NOT']

    def __init__(self, parent, parentframe, cols):

        Frame.__init__(self, parentframe)
        self.parent = parent
        self.filtercol = StringVar()
        initial = cols[0]
        self.filtercolmenu = Combobox(self,
                textvariable = self.filtercol,
                values = cols,
                #initialitem = initial,
                width = 14)
        self.filtercolmenu.grid(row=0,column=1,sticky='news',padx=2,pady=2)
        self.operator = StringVar()
        #self.operator.set('equals')
        operatormenu = Combobox(self,
                textvariable = self.operator,
                values = self.operators,
                width = 10)
        operatormenu.grid(row=0,column=2,sticky='news',padx=2,pady=2)
        self.filtercolvalue=StringVar()
        valsbox = Entry(self,textvariable=self.filtercolvalue,width=26)
        valsbox.grid(row=0,column=3,sticky='news',padx=2,pady=2)
        #valsbox.bind("<Return>", self.parent.callback)
        self.booleanop = StringVar()
        self.booleanop.set('AND')
        booleanopmenu = Combobox(self,
                textvariable = self.booleanop,
                values = self.booleanops,
                width = 6)
        booleanopmenu.grid(row=0,column=0,sticky='news',padx=2,pady=2)
        #disable the boolean operator if it's the first filter
        #if self.index == 0:
        #    booleanopmenu.component('menubutton').configure(state=DISABLED)
        img = images.cross()
        cb = Button(self,text='-', image=img, command=self.close)
        cb.image = img
        cb.grid(row=0,column=5,sticky='news',padx=2,pady=2)
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

    def update(self, cols):
        self.filtercolmenu['values'] = cols
        return

class BaseTable(Canvas):
    """Basic table class based on tk canvas. inherit from this to add your own functionality"""
    def __init__(self, parent=None, width=280, height=190, rows=2, cols=2, **kwargs):

        Canvas.__init__(self, parent, bg='white',
                         width=width, height=height )
        self.parent = parent
        self.rows = rows
        self.cols = cols
        self.selectedrows = [0]
        self.selectedcols = [0]
        self.top = .1
        self.bottom =.9
        self.height = height
        self.width = width
        self.doBindings()
        self.redraw()
        self.update_callback = None
        return

    def update(self):
        if self.update_callback != None:
            self.update_callback()

    def doBindings(self):
        self.bind("<Button-1>",self.handle_left_click)
        self.bind('<B1-Motion>', self.handle_mouse_drag)
        return

    def redraw(self):
        self.drawGrid()
        self.drawMultipleCells(self.selectedrows, self.selectedcols)
        return

    def drawGrid(self):
        self.delete('gridline')
        self.delete('currentrect')
        self.delete('multiplesel')
        rows = self.rows
        h = self.height
        w = self.width
        for row in range(rows+1):
            y = row*h/rows
            self.create_line(1,y,w,y, tag='gridline',
                                fill='gray', width=2)
        for col in range(self.cols+1):
            x = col*w/self.cols
            self.create_line(x,1,x,rows*h, tag='gridline',
                                fill='gray', width=2)
        return

    def handle_left_click(self, event):
        """Respond to a single press"""

        #self.clearSelected()
        #which row and column is the click inside?
        row = self.get_row_clicked(event)
        col = self.get_col_clicked(event)
        self.focus_set()
        #print (row, col)
        self.delete('multiplesel')
        self.delete('currentrect')
        self.drawSelectedRect(row, col, tags='currentrect')
        self.startrow = row
        self.startcol = col
        self.selectedrows = [row]
        self.selectedcols = [col]
        self.update()
        return

    def handle_mouse_drag(self, event):
        """Handle mouse moved with button held down, multiple selections"""

        rowover = self.get_row_clicked(event)
        colover = self.get_col_clicked(event)
        self.endrow = rowover
        self.endcol = colover
        rows = [rowover]
        cols = [colover]
        if colover == None or rowover == None:
            return
        #draw the selected rows
        if self.endrow != self.startrow:
            if self.endrow < self.startrow:
                rows = list(range(self.endrow, self.startrow+1))
            else:
                rows = list(range(self.startrow, self.endrow+1))
        if self.endcol != self.startcol:
            if self.endcol < self.startcol:
                cols = list(range(self.endcol, self.startcol+1))
            else:
                cols = list(range(self.startcol, self.endcol+1))
        self.drawMultipleCells(rows,cols)
        self.selectedrows = rows
        self.selectedcols = cols
        self.update()
        return

    def get_row_clicked(self, event):
        """Get row where event on canvas occurs"""

        h = self.height/self.rows
        #get coord on canvas, not window, need this if scrolling
        y = int(self.canvasy(event.y))
        row = int(int(y)/h)
        return row

    def get_col_clicked(self, event):
        """Get column where event on the canvas occurs"""

        w = self.width/self.cols
        x = int(self.canvasx(event.x))
        col =int(int(x)/w)
        return col

    def getCellCoords(self, row, col):
        """Get x-y coordinates to drawing a cell in a given row/col"""

        h = self.height/self.rows
        x_start=0
        y_start=0
        #get nearest rect co-ords for that row/col
        w = self.width/self.cols
        x1 = w*col
        y1=y_start+h*row
        x2=x1+w
        y2=y1+h
        return x1,y1,x2,y2

    def drawSelectedRect(self, row, col, color='#c2c2d6',pad=4, tags=''):
        """User has clicked to select area"""

        if col >= self.cols:
            return
        w=1
        pad=pad
        x1,y1,x2,y2 = self.getCellCoords(row,col)
        #print (x1,y1,x2,y2)
        rect = self.create_rectangle(x1+pad+w,y1+pad+w,x2-pad-w,y2-pad-w,
                                  outline='gray50', fill=color,
                                  width=w,
                                  tag=tags)
        return

    def drawMultipleCells(self, rows, cols):
        """Draw more than one row selection"""

        self.delete('multiplesel')
        self.delete('currentrect')
        for col in cols:
            for row in rows:
                #print (row, col)
                self.drawSelectedRect(row, col, tags='multiplesel')
        return
