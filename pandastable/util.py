#!/usr/bin/env python
"""
    Implements the utility methods for pandastable classes.
    Created August 2015
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
except:
    from Tkinter import *
    from ttk import *
import math, time
import os, types
import string, copy
import numpy as np
import pandas as pd

def getTextLength(text, w, scratch=None, font=None):
    """Get correct canvas text size (chars) that will fit in
    a given canvas width"""

    if scratch == None:
        scratch = Canvas()
    length = len(str(text))
    t = scratch.create_text((0,0), text=text, font=font)
    b = scratch.bbox(t)
    twidth = b[2]-b[0]
    ratio = length/twidth
    length = math.floor(w*ratio)
    return twidth,length

def check_multiindex(index):
    """Check if index is a multiindex"""

    if isinstance(index, pd.core.index.MultiIndex):
        return 1
    else:
        return 0

def getAttributes(obj):
    """Get non hidden and built-in type object attributes that can be persisted"""

    d={}
    allowed = [str,int,float,list,tuple,bool]
    for key in obj.__dict__:
        if key.startswith('_'):
            continue
        item = obj.__dict__[key]
        if type(item) in allowed:
            d[key] = item
        elif type(item) is dict:
            if checkDict(item) == 1:
                d[key] = item
    return d

def setAttributes(obj, data):
    """Set attributes from a dict. Used for restoring settings in tables"""

    for key in data:
        #if key.startswith('_'): continue
        obj.__dict__[key] = data[key]
    return

def checkDict(d):
    """Check a dict recursively for non serializable types"""

    allowed = [str,int,float,list,tuple,bool]
    for k, v in d.items():
        if isinstance(v, dict):
            checkDict(v)
        else:
            if type(v) not in allowed:
                return 0
    return 1

def getFonts():
     """Get the current list of system fonts"""

     import matplotlib.font_manager
     #l = matplotlib.font_manager.get_fontconfig_fonts()
     l = matplotlib.font_manager.findSystemFonts()
     fonts = []
     for fname in l:
        try: fonts.append(matplotlib.font_manager.FontProperties(fname=fname).get_name())
        except RuntimeError: pass
     fonts = list(set(fonts))
     fonts.sort()
     #f = matplotlib.font_manager.FontProperties(family='monospace')
     #print (matplotlib.font_manager.findfont(f))
     return fonts

def adjustColorMap(cmap, minval=0.0, maxval=1.0, n=100):
    """Adjust colormap to avoid using white in plots"""

    from matplotlib import colors
    new_cmap = colors.LinearSegmentedColormap.from_list(
        'trunc({n},{a:.2f},{b:.2f})'.format(n=cmap.name, a=minval, b=maxval),
        cmap(np.linspace(minval, maxval, n)))
    return new_cmap
