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

SCRATCH = None


def getTextLength(text, w, font=None):
    """Get correct canvas text size (chars) that will fit in \
    a given canvas width"""

    global SCRATCH
    if SCRATCH is None:
        SCRATCH = Canvas()
    scratch = SCRATCH
    length = len(text)
    t = scratch.create_text((0,0), text=text, font=font)
    b = scratch.bbox(t)
    scratch.delete(t)
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
        try:
            obj.__dict__[key] = data[key]
        except Exception as e:
            print (e)
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

def colorScale(hex_color, brightness_offset=1):
    """Takes a hex color and produces a lighter or darker variant.
    Returns:
        new color in hex format
    """

    #if not hex_color.startswith('#'):
        #import matplotlib
        #hex_color = matplotlib.colors.cnames[hex_color].lower()
    if len(hex_color) != 7:
        raise Exception("Passed %s into color_variant(), needs to be in #87c95f format." % hex_color)
    rgb_hex = [hex_color[x:x+2] for x in [1, 3, 5]]
    new_rgb_int = [max(0, int(hex_value, 16) + brightness_offset) for hex_value in rgb_hex]
    r,g,b = [min([255, max([1, i])]) for i in new_rgb_int]
    # hex() produces "0x88", we want just "88"
    return "#{0:02x}{1:02x}{2:02x}".format(r, g, b)

def checkOS():
    """Check the OS we are in"""

    from sys import platform as _platform
    if _platform == "linux" or _platform == "linux2":
        return 'linux'
    elif _platform == "darwin":
        return 'darwin'
    if "win" in _platform:
        return 'windows'
