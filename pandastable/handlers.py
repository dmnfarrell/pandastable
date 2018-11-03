#!/usr/bin/env python
"""
    Module for plot viewer event classes.

    Created Jan 2016
    Copyright (C) Damien Farrell

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import types
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
#import matplotlib.animation as animation
from collections import OrderedDict
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.text import Text, Annotation
from matplotlib.collections import PathCollection
from matplotlib.backend_bases import key_press_handler

class DragHandler(object):
    """ A simple class to handle picking and dragging"""

    def __init__(self, parent, figure=None):
        """ Create a handler and connect it to the plotviewer figure.
        """

        self.parent = parent
        #store the dragged text object
        self.dragged = None
        self.selected = None
        self.selectedrect = None
        return

    def connect(self):
        """Connect events"""

        fig = self.parent.fig
        fig.canvas.mpl_connect("pick_event", self.on_pick_event)
        fig.canvas.mpl_connect('button_press_event', self.button_press_event)
        fig.canvas.mpl_connect("button_release_event", self.on_release_event)
        fig.canvas.mpl_connect("key_press_event", self.key_press_event)
        return

    def button_press_event(self, event):

        #print (event)
        fig = self.parent.fig
        fig.canvas._tkcanvas.focus_set()
        if self.selectedrect != None:
            self.selectedrect.set_visible(False)
        return

    def on_pick_event(self, event):
        " Store which text object was picked and were the pick event occurs."

        df = self.parent.data
        self.dragged = event.artist
        #print(self.dragged)
        if isinstance(event.artist, PathCollection):
            ind = event.ind
            print('onpick scatter:', ind, df.ix[ind])
        elif isinstance(event.artist, Line2D):
            thisline = event.artist
            xdata = thisline.get_xdata()
            ydata = thisline.get_ydata()
            ind = event.ind
            print('onpick line:', zip(np.take(xdata, ind), np.take(ydata, ind)))
        elif isinstance(event.artist, Rectangle):
            patch = event.artist
            print('onpick patch:', patch.get_path())
        elif isinstance(self.dragged, Annotation):
            text = event.artist
            print('onpick text:', text.get_text())
            self.selected = text
            #self.drawSelectionRect()
        return True

    def on_release_event(self, event):
        " Update and store text/annotation position "

        fig = self.parent.fig
        #ax = fig.axes[0]
        ax = self.parent.ax
        xy = (event.xdata, event.ydata)
        #xy = (event.x, event.y)
        print (xy)
        #if annotation object moved we record new coords
        if isinstance(self.dragged, Annotation):
            key = self.dragged._id
            #print (self.dragged.get_text(), key)
            d = self.parent.labelopts.textboxes[key]
            #print (d)
            fig.canvas.draw()
            bbox = self.dragged.get_window_extent()

            if d['xycoords'] == 'axes fraction':
                inv = ax.transAxes.inverted()
            elif d['xycoords'] == 'figure fraction':
                inv = fig.transFigure.inverted()
            else:
                inv = ax.transData.inverted()
            bbdata = inv.transform(bbox)
            xy = bbdata[0][0],bbdata[0][1]
            d['xy'] = xy
            print (xy)
        self.dragged = None
        return True

    def key_press_event(self, event):
        """Handle key press"""

        if event.key == 'delete':
            if self.selected == None:
                return
            self.selected.set_visible(False)
            fig = self.parent.fig
            key = self.selected._id
            del self.parent.labelopts.textboxes[key]
            self.selected = None
            if self.selectedrect != None:
                self.selectedrect.set_visible(False)
        fig.canvas.draw()
        return

    def drawSelectionRect(self):
        """Draw a selection box"""

        from matplotlib.patches import FancyBboxPatch
        if self.selectedrect != None:
            self.selectedrect.set_visible(False)
        fig = self.parent.fig
        ax = fig.axes[0]
        bb = self.selected.get_window_extent()
        bb = ax.transAxes.inverted().transform(bb)
        x,y = bb[0]
        x1,y1 = bb[1]
        print (x,y,x1,y1)
        pad = (x1-x)/10
        self.selectedrect = FancyBboxPatch((x, y),
                                 abs(x1-x), abs(y1-y),
                                 boxstyle="round,pad=%s" %pad, lw=2, alpha=0.5,
                                 ec="red", fc="red", zorder=10.,
                                 transform=ax.transAxes)
        ax.add_patch(self.selectedrect)
        fig.canvas.draw()
        return

    def disconnect(self):
        """disconnect all the stored connection ids"""

        return
