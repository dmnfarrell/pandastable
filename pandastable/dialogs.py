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

import sys,os,types
import platform
import tkinter
from tkinter import *
from tkinter.ttk import *
from tkinter.scrolledtext import ScrolledText
from collections import OrderedDict
import webbrowser
import pandas as pd
from .data import TableModel

def getParentGeometry(parent):
    x = parent.winfo_rootx()
    y = parent.winfo_rooty()
    w = parent.winfo_width()
    h = parent.winfo_height()
    return x,y,w,h

def getDictfromTkVars(opts, tkvars, widgets):
    kwds = {}
    for i in opts:
        if opts[i]['type'] == 'listbox':
            items = widgets[i].curselection()
            kwds[i] = [widgets[i].get(j) for j in items]
            #print (items, kwds[i])
        else:
            kwds[i] = tkvars[i].get()
    return kwds

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
        else:
            c=0; row+=1
        frame = LabelFrame(dialog, text=g)
        frame.grid(row=row,column=c,sticky=sticky)

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
                w = tkinter.Scale(frame,label=opt['label'],
                         from_=fr,to=to,
                         orient='horizontal',
                         resolution=opt['interval'],
                         variable=v)
            if w != None:
                w.pack(fill=BOTH,expand=1)
                widgets[i] = w
            row+=1

    return dialog, tkvars, widgets

def addButton(frame, name, callback, img=None, tooltip=None,
              side=TOP, compound=None, width=None):
    """Add a button with image, toolip to a tkinter frame"""

    if img==None:
        b = Button(frame, text=name, command=callback)
    else:
        b = Button(frame, text=name, command=callback, width=width,
                         image=img, compound=compound)
    b.image = img
    b.pack(side=side,fill=X)
    if tooltip != None:
        ToolTip.createToolTip(b, tooltip)
    return

class MultipleValDialog(simpledialog.Dialog):
    """Simple dialog to get multiple values"""

    def __init__(self, parent, title=None, initialvalues=None, labels=None,
                    types=None, tooltips=None):
        if labels != None and types is not None:
            self.initialvalues = initialvalues
            self.labels = labels
            self.types = types
            self.tooltips = tooltips
        simpledialog.Dialog.__init__(self, parent, title)
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
                self.entries.append(Entry(master, textvariable=self.vrs[i], width=10, show=s))
            self.entries[i].grid(row=r, column=1,padx=2,pady=2,sticky='ew')
            if self.tooltips != None:
                ToolTip.createToolTip(self.entries[i], self.tooltips[i])
            r+=1

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

        delimiters = [',','\t',' ',';','/','&','|','^','+','-']
        encodings = ['utf-8','ascii','iso8859_15','cp037','cp1252','big5','euc_jp']
        grps = {'formats':['delimiter','decimal','comment'],
                'data':['header','skiprows','index_col','skipinitialspace',
                        'skip_blank_lines','encoding','names'],
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
        self.textpreview = ScrolledText(self.main, width=80, height=10)
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
            text = stream.read()
        self.textpreview.delete('1.0', END)
        self.textpreview.insert('1.0', text)
        return

    def update(self):
        """Reload previews"""

        kwds = {}
        other = ['rowsperfile']
        for i in self.opts:
            if i in other:
                continue
            try:
                val = self.tkvars[i].get()
            except:
                val=None
            if val == '':
                val=None
            elif type(self.opts[i]['default']) != int:
                try:
                    val=int(val)
                except:
                    pass
            kwds[i] = val
        self.kwds = kwds

        self.showText()
        f = pd.read_csv(self.filename, chunksize=400, error_bad_lines=False,
                        warn_bad_lines=False, **kwds)
        try:
            df = f.get_chunk()
        except pd.parser.CParserError:
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
        self.df = pd.read_csv(self.filename, **self.kwds)
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
                'concat': ['join','ignore_index','verify_integrity']}
        self.grps = grps = OrderedDict(sorted(grps.items()))
        cols1 = list(df1.columns)
        cols2 = list(df2.columns)
        opts = self.opts = {'left_on':{'type':'listbox','default':'',
                            'items':cols1, 'tooltip':'left column'},
                            'right_on':{'type':'listbox','default':'',
                            'items':cols2, 'tooltip':'right column'},
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
        optsframe, self.tkvars, w = dialogFromOptions(self.main, opts, grps, sticky='new')
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
            if self.opts[i]['type'] == 'listbox':
                val = self.tkvars[i].getSelectedItem()
            else:
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
        link='http://pandas.pydata.org/pandas-docs/stable/merging.html'
        webbrowser.open(link,autoraise=1)
        return

    def quit(self):
        self.main.destroy()
        return

class AggregateDialog(Frame):
    """Provides a frame for split-apply-combine operations"""

    def __init__(self, parent=None, df=None):

        self.parent = parent
        self.main = Toplevel()
        self.master = self.main
        self.main.title('Aggregate')
        self.main.protocol("WM_DELETE_WINDOW", self.quit)
        self.main.grab_set()
        self.main.transient(parent)
        self.df = df
        self.result = None
        cols = list(self.df.columns)

        m = Frame(self.main)
        m.pack(side=TOP)
        w,self.grpvar = addListBox(m, values=cols,width=14)
        ToolTip.createToolTip(w, 'columns to group on')
        Label(m, text='group by:').pack()
        w.pack()
        self.vars = OrderedDict()
        for i in range(1,3):
            f = LabelFrame(m, text='aggregate-%s' %i)
            f.pack(side=LEFT,fill=BOTH,padx=2)
            self.vars[i] = self.createWidgets(f)

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

    def createWidgets(self, f):
        """Create a set of grp-agg-func options together"""

        funcs = ['mean','sum','size','count','std','first','last',
                 'min','max','var']
        cols = list(self.df.columns)
        colvar = StringVar()
        w = Combobox(f, values=cols,
                 textvariable=colvar,width=14)
        Label(f, text='column:').pack()
        w.pack()
        w,funcvar = addListBox(f, values=funcs,width=14)
        Label(f, text='functions:').pack()
        w.pack()
        return colvar, funcvar

    def apply(self):
        """Apply operation"""

        grp = self.grpvar.getSelectedItem()
        aggdict = {}
        for i in self.vars:
            agg = self.vars[i][0].get()
            funcs = self.vars[i][1].getSelectedItem()
            if agg != '' and agg not in grp:
                aggdict[agg] = funcs
        #print (aggdict)
        self.result = self.df.groupby(grp).agg(aggdict)
        self.quit()
        return

    def help(self):
        link='http://pandas.pydata.org/pandas-docs/stable/groupby.html'
        webbrowser.open(link,autoraise=1)
        return

    def quit(self):
        self.main.destroy()
        return

def addListBox(parent, values=[], width=10):
    """Add an EasyListBox"""

    frame=Frame(parent)
    yScroll = Scrollbar(frame, orient = VERTICAL)
    yScroll.grid(row = 0, column = 1, sticky = N+S)
    listItemSelected = lambda index: index
    lbx = EasyListbox(frame, width, 6, yScroll.set, listItemSelected)
    lbx.grid(row = 0, column = 0, sticky = N+S+E+W)
    frame.columnconfigure(0, weight = 1)
    frame.rowconfigure(0, weight = 1)
    yScroll["command"] = lbx.yview
    for i in values:
        lbx.insert(END, i)
    return frame, lbx

class AutoScrollbar(Scrollbar):
    """a scrollbar that hides itself if it's not needed.  only
       works if you use the grid geometry manager."""

    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            # grid_remove is currently missing from Tkinter!
            self.tk.call("grid", "remove", self)
        else:
            self.grid()
        Scrollbar.set(self, lo, hi)
    def pack(self, **kw):
        raise TclError("cannot use pack with this widget")
    def place(self, **kw):
        raise TclError("cannot use place with this widget")

class VerticalScrolledFrame(Frame):
    """A pure Tkinter scrollable frame
    see http://tkinter.unpythonic.net/wiki/VerticalScrolledFrame.
    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
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

    def triggerListItemSelected(self, event):
        """Strategy method to respond to an item selection in the list box.
        Runs the client's listItemSelected method with the selected index if
        there is one."""
        if self.size() == 0: return
        widget = event.widget
        indexes = widget.curselection()
        #self._listItemSelected(index)

    def getSelectedIndex(self):
        """Returns the index of the selected item or -1 if no item
        is selected."""
        tup = self.curselection()
        if len(tup) == 0:
            return -1
        else:
            return tup

    def getSelectedItem(self):
        """Returns the selected item or the empty string if no item
        is selected."""
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
        """Returns the index of item if it's in the list box,
        or -1 otherwise."""
        tup = self.get(0, self.size() - 1)
        if item in tup:
            return tup.index(item)
        else:
            return -1

class SimpleEditor(Frame):
    """Simple text editor"""

    def __init__(self, parent=None, width=100, height=40, font=None):

        Frame.__init__(self, parent)
        st = self.text = ScrolledText(self, width=width, height=height)
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
