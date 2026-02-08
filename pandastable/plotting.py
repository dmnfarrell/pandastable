#!/usr/bin/env python
"""
    Module for pandastable plotting classes .

    Created Jan 2014
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

from __future__ import absolute_import, division, print_function
try:
    from tkinter import *
    from tkinter.ttk import *
except:
    from Tkinter import *
    from ttk import *
import types, time
import numpy as np
import pandas as pd
try:
    from pandas import plotting
except ImportError:
    from pandas.tools import plotting
import matplotlib as mpl
#mpl.use("TkAgg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.lines import Line2D
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
import matplotlib.transforms as mtrans
import matplotlib.patheffects as patheffects
from collections import OrderedDict
import operator
from .dialogs import *
from . import util, images
import logging


def _apply_option_tooltips(opts, overrides=None):
    """Populate tooltip text for every option entry."""

    overrides = overrides or {}
    for key, conf in opts.items():
        if conf.get('tooltip'):
            continue
        text = overrides.get(key)
        if not text:
            label = conf.get('label') or key.replace('_', ' ')
            text = f"Configure {label}."
        conf['tooltip'] = text


BASE_OPTION_TOOLTIPS = {
    'font': 'Font family used for titles, labels, and legends.',
    'fontsize': 'Base font size applied to most plot text.',
    'marker': 'Matplotlib marker symbol for point data.',
    'linestyle': 'Line style used for plotted traces.',
    'ms': 'Marker size in points.',
    'grid': 'Show or hide major grid lines.',
    'logx': 'Plot the X axis on a logarithmic scale.',
    'logy': 'Plot the Y axis on a logarithmic scale.',
    'use_index': 'Use the DataFrame index for the X axis.',
    'errorbars': 'Interpret the selected column as error bar magnitudes.',
    'clrcol': 'Column that provides per-point color values.',
    'cscale': 'Scale applied to mapped colors (linear/log).',
    'colorbar': 'Display a colorbar legend for scalar data.',
    'bw': 'Render the plot using grayscale tones.',
    'showxlabels': 'Toggle visibility of X tick labels.',
    'showylabels': 'Toggle visibility of Y tick labels.',
    'sharex': 'Force subplots to share the same X limits.',
    'sharey': 'Force subplots to share the same Y limits.',
    'legend': 'Show legend entries for plotted series.',
    'kind': 'Primary matplotlib plot type to render.',
    'stacked': 'Stack series on top of each other where applicable.',
    'linewidth': 'Stroke width for lines in points.',
    'alpha': 'Overall transparency applied to plot elements.',
    'subplots': 'Draw each selected series in its own subplot.',
    'colormap': 'Matplotlib colormap used for scalar mappings.',
    'bins': 'Number of bins/steps used for histograms or jitter analysis.',
    'hist_min': 'Minimum value to include in histogram calculations.',
    'hist_max': 'Maximum value to include in histogram calculations.',
    'by': 'First grouping column for split plots.',
    'by2': 'Optional second grouping column.',
    'labelcol': 'Column supplying text labels per data point.',
    'pointsizes': 'Column controlling per-point marker area.',
    'bw_method': 'Kernel density bandwidth selection method.',
    'fill': 'Fill under the density curve.',
    'show_rug': 'Draw individual data ticks along the axis.',
    'x_param': 'Column mapped to the shmoo X axis.',
    'y_param': 'Column mapped to the shmoo Y axis.',
    'z_param': 'Column providing shmoo measurement values.',
    'threshold_min': 'Lower threshold for shmoo pass/fail shading.',
    'threshold_max': 'Upper threshold for shmoo pass/fail shading.',
    'show_contours': 'Overlay contour lines on shmoo heatmaps.',
    'contour_levels': 'Number of contour levels to compute.',
    'interpolation': 'Interpolation method for shmoo grids.',
    'show_stats': 'Display derived statistics for the current plot.',
    'marker_size': 'Size of scatter markers when drawing raw shmoo points.',
    'show_markers': 'Overlay the original shmoo sample positions.',
    'show_values': 'Label each shmoo cell with its numeric value.',
    'log_z_scale': 'Apply log10 scaling to Z data.',
    'ber_target': 'Target BER used for bathtub visualizations.',
    'show_margins': 'Display eye/bathtub margin annotations.',
    'x_axis_type': 'Units used for the eye diagram X axis.',
    'show_target_line': 'Draw the BER target line in bathtub plots.',
    'margin_style': 'Visualization style for BER margins.',
    'dual_curve': 'Show left/right bathtub curves separately.',
    'log_freq': 'Use logarithmic scaling for S-parameter frequency axis.',
    'show_phase': 'Overlay S-parameter phase on a secondary axis.',
    'spec_limit': 'Specification limit value in dB.',
    'limit_type': 'Orient spec limit as horizontal or vertical line.',
    'nyquist_marker': 'Highlight the Nyquist point computed from data rate.',
    'data_rate': 'Data rate (Gbps) used to derive Nyquist frequency.',
    'freq_range': 'Manual frequency range override (GHz).',
    'db_range': 'Manual dB axis range override.',
    'show_progress': 'Display task progress bars on Gantt charts.',
    'show_today': 'Draw a vertical line for today on Gantt charts.',
    'date_format': 'Datetime format string for Gantt labels.',
    'bar_height': 'Relative height of Gantt bars.',
    'show_milestones': 'Display milestone markers on the chart.',
    'group_by': 'Column used to group Gantt tasks.',
    'sort_by': 'Sort order for Gantt tasks.',
    'persistence': 'Heatmap persistence for eye diagrams.',
    'ui_width': 'Unit interval width for eye diagrams.',
    'sample_rate': 'Sample rate in GS/s for the captured waveform.',
    'bit_rate': 'Bit rate in Gbps for the captured waveform.',
    'show_mask': 'Overlay compliance mask on eye diagram.',
    'mask_margin': 'Additional margin applied to the eye mask.',
    'color_mode': 'Color rendering mode for eye diagram accumulation.',
    'overlay_count': 'Number of overlays used when in overlay mode.',
    'show_gaussian': 'Overlay a Gaussian fit when analyzing jitter.',
    'show_dual_dirac': 'Show dual-Dirac components in jitter plots.',
    'tj_separation': 'Total jitter (TJ) separation in picoseconds.',
    'show_components': 'Display RJ/DJ component breakdown.',
    'carrier_freq': 'Carrier frequency in Hz for phase noise to jitter conversion.',
    'freq_min': 'Minimum offset frequency (Hz) for integration range.',
    'freq_max': 'Maximum offset frequency (Hz) for integration range.',
}


MPL3D_OPTION_TOOLTIPS = {
    'kind': 'Type of 3D plot to render.',
    'rstride': 'Row sampling stride for wireframes/surfaces.',
    'cstride': 'Column sampling stride for wireframes/surfaces.',
    'points': 'Overlay original data points on the 3D plot.',
    'mode': 'Interpretation of data (parametric vs grid).',
    'logz': 'Use logarithmic scale for Z axis. Non-positive values are clamped to min(Z)/10.',
}


ANNOTATION_OPTION_TOOLTIPS = {
    'title': 'Global plot title text.',
    'xlabel': 'X axis label text.',
    'ylabel': 'Y axis label text.',
    'facecolor': 'Fill color for annotation boxes.',
    'linecolor': 'Edge color for annotation boxes.',
    'fill': 'Hatch/fill pattern for annotation boxes.',
    'rotate': 'Rotation angle applied to added textbox objects.',
    'boxstyle': 'Box style for annotation backgrounds.',
    'text': 'Body text for added annotation objects.',
    'align': 'Horizontal alignment of annotation text.',
    'font': 'Font used for annotation text.',
    'fontsize': 'Font size used for annotation text.',
    'fontweight': 'Font weight used for annotation text.',
    'rot': 'Rotation angle for tick labels.',
}


EXTRA_OPTION_TOOLTIPS = {
    'xmin': 'Minimum X limit override.',
    'xmax': 'Maximum X limit override.',
    'ymin': 'Minimum Y limit override.',
    'ymax': 'Maximum Y limit override.',
    'major x-ticks': 'Number or spacing for major X ticks.',
    'major y-ticks': 'Number or spacing for major Y ticks.',
    'minor x-ticks': 'Number or spacing for minor X ticks.',
    'minor y-ticks': 'Number or spacing for minor Y ticks.',
    'formatter': 'Tick label formatter preset.',
    'symbol': 'Suffix symbol (e.g., units) appended to tick labels.',
    'precision': 'Decimal precision for formatted tick values.',
    'date format': 'Datetime format string for tick labels.',
}


ANIMATE_OPTION_TOOLTIPS = {
    'increment': 'Row step size between animation frames.',
    'window': 'Number of rows plotted per frame.',
    'startrow': 'Starting row index for playback.',
    'delay': 'Delay between frames in seconds.',
    'tableupdate': 'Refresh the table selection as frames advance.',
    'expand': 'Grow the plotted window instead of sliding it.',
    'usexrange': 'Lock X axis to the full dataset range.',
    'useyrange': 'Lock Y axis to the full dataset range.',
    'smoothing': 'Apply rolling average smoothing before plotting.',
    'columntitle': 'Column used to refresh the plot title each frame.',
    'savevideo': 'Render the animation to a video file.',
    'codec': 'FFMpeg codec used for captured video.',
    'fps': 'Frames per second for saved video.',
    'filename': 'Output filename for the captured video.',
}

colormaps = sorted(m for m in plt.cm.datad if not m.endswith("_r"))
markers = ['','o','.','^','v','>','<','s','+','x','p','d','h','*']
linestyles = ['-','--','-.',':','steps']
#valid kwds for each plot method
valid_kwds = {'line': ['alpha', 'colormap', 'grid', 'legend', 'linestyle','ms',
                  'linewidth', 'marker', 'subplots', 'rot', 'logx', 'logy',
                  'sharex','sharey', 'kind'],
            'scatter': ['alpha', 'grid', 'linewidth', 'marker', 'subplots', 'ms',
                    'legend', 'colormap','sharex','sharey', 'logx', 'logy', 'use_index',
                    'clrcol', 'cscale','colorbar','bw','labelcol','pointsizes'],
            'pie': ['colormap','legend'],
            'hexbin': ['alpha', 'colormap', 'grid', 'linewidth','subplots'],
            'bootstrap': ['grid'],
            'bar': ['alpha', 'colormap', 'grid', 'legend', 'linewidth', 'subplots',
                    'sharex','sharey', 'logy', 'stacked', 'rot', 'kind', 'edgecolor'],
            'barh': ['alpha', 'colormap', 'grid', 'legend', 'linewidth', 'subplots',
                    'sharex','sharey','stacked', 'rot', 'kind', 'logx', 'edgecolor'],
            'histogram': ['alpha', 'linewidth','grid','stacked','subplots','colormap',
                     'sharex','sharey','rot','bins', 'logx', 'logy', 'legend', 'edgecolor'],
            'heatmap': ['colormap','colorbar','rot', 'linewidth','linestyle',
                        'subplots','rot','cscale','bw','alpha','sharex','sharey'],
            'area': ['alpha','colormap','grid','linewidth','legend','stacked',
                     'kind','rot','logx','sharex','sharey','subplots'],
            'density': ['alpha', 'colormap', 'grid', 'legend', 'linestyle',
                         'linewidth', 'marker', 'subplots', 'rot', 'kind',
                         'bw_method', 'fill', 'show_rug'],
            'boxplot': ['rot','grid','logy','colormap','alpha','linewidth','legend',
                        'subplots','edgecolor','sharex','sharey'],
            'violinplot': ['rot','grid','logy','colormap','alpha','linewidth','legend',
                        'subplots','edgecolor','sharex','sharey'],
            'dotplot': ['marker','edgecolor','linewidth','colormap','alpha','legend',
                        'subplots','ms','bw','logy','sharex','sharey'],
            'scatter_matrix':['alpha', 'linewidth', 'grid', 's','alpha'],
            'contour': ['linewidth','colormap','alpha','subplots'],
            'imshow': ['colormap','alpha'],
            'venn': ['colormap','alpha'],
            'radviz': ['linewidth','marker','edgecolor','s','colormap','alpha'],
            'shmoo': ['alpha', 'colormap', 'grid', 'colorbar',
                     'x_param', 'y_param', 'z_param', 'threshold_min', 'threshold_max',
                     'show_contours', 'contour_levels', 'interpolation', 'show_stats',
                     'marker_size', 'show_markers', 'show_values', 'log_z_scale'],
            'bathtub': ['alpha', 'colormap', 'grid', 'legend', 'linewidth',
                       'ber_target', 'show_margins', 'x_axis_type', 'show_target_line',
                       'margin_style', 'dual_curve'],
            'sparam': ['alpha', 'colormap', 'grid', 'legend', 'linewidth',
                      'log_freq', 'show_phase', 'spec_limit', 'limit_type',
                      'nyquist_marker', 'data_rate', 'freq_range', 'db_range'],
            'gantt': ['alpha', 'colormap', 'grid', 'legend',
                     'show_progress', 'show_today', 'date_format', 'bar_height',
                     'show_milestones', 'group_by', 'sort_by'],
            'eye': ['alpha', 'colormap', 'grid', 'persistence', 'ui_width',
                   'sample_rate', 'bit_rate', 'show_mask', 'mask_margin',
                   'color_mode', 'overlay_count'],
            'jitter': ['alpha', 'colormap', 'grid', 'legend', 'bins',
                      'show_stats', 'show_gaussian', 'show_dual_dirac',
                      'tj_separation', 'show_components'],
            'phasenoise': ['alpha', 'colormap', 'grid', 'legend', 'linewidth',
                          'carrier_freq', 'freq_min', 'freq_max', 'show_stats']
            }

def get_defaults(name):
    """
    Get the default options for a given options class name.

    Args:
        name (str): The name of the options class ('mplopts', 'mplopts3d', 'labelopts').

    Returns:
        dict: The default options dictionary.
    """
    if name == 'mplopts':
        return MPLBaseOptions().opts
    elif name == 'mplopts3d':
        return MPL3DOptions().opts
    elif name == 'labelopts':
        return AnnotationOptions().opts

class PlotViewer(Frame):
    """Provides a frame for figure canvas and MPL settings.

    Args:
        table: parent table, required
        parent: parent tkinter frame
        layout: 'horizontal' or 'vertical'
    """

    def __init__(self, table, parent=None, showoptions=True):
        """
        Initialize the PlotViewer.

        Args:
            table: The parent table instance.
            parent: The parent widget (optional). If None, a new Toplevel is created.
            showoptions (bool): Whether to show the options panel. Default is True.
        """

        self.parent = parent
        self.table = table
        if table is not None:
            self.table.pf = self #opaque ref
        #self.mode = '2d'
        self.showoptions = showoptions
        self.multiviews = False
        if self.parent != None:
            Frame.__init__(self, parent)
            self.main = self.master
        else:
            self.main = Toplevel()
            self.master = self.main
            self.main.title('Plot Viewer')
            self.main.protocol("WM_DELETE_WINDOW", self.close)
            g = '800x700+900+200'
            self.main.geometry(g)
        #self.toolslayout = layout
        #if layout == 'horizontal':
        self.orient = VERTICAL
        #else:
        #    self.orient = HORIZONTAL
        self.mplopts = MPLBaseOptions(parent=self)
        self.mplopts3d = MPL3DOptions(parent=self)
        self.labelopts = AnnotationOptions(parent=self)
        self.layoutopts = PlotLayoutOptions(parent=self)

        self.gridaxes = {}
        #reset style if it been set globally
        self.style = None
        # Hover tooltip state
        self._hover_targets = []
        self._hover_annotation = None
        self._hover_annotation_axes = None
        self._hover_cid = None
        self.setupGUI()
        self.updateStyle()
        self.currentdir = os.path.expanduser('~')
        return

    def setupGUI(self):
        """
        Setup the GUI elements including the figure canvas and control panel.
        """

        # Two-pane layout: plot on top, controls underneath, resizable via sash
        self.m = PanedWindow(self.main, orient=VERTICAL)
        self.m.pack(fill=BOTH,expand=1)

        # frame for figure
        self.plotfr = Frame(self.m)
        self.fig, self.canvas = addFigure(self.plotfr)
        self.ax = self.fig.add_subplot(111)
        
        # Add navigation toolbar for zoom/pan (hidden by default, we use custom buttons)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plotfr, pack_toolbar=False)
        self.toolbar.update()
        # Track zoom/pan mode state
        self._zoom_mode = False
        self._pan_mode = False
        self._fullscreen_mode = False
        
        # Connect mouse events for Ctrl+scroll zoom and right-click pan
        self._connect_mouse_events()
        
        # Create active button style for zoom/pan toggle indication
        style = Style()
        style.configure('Active.TButton', background='lightblue', relief='sunken')
        
        self.m.add(self.plotfr, weight=4)

        # frame for controls (options + toolbar)
        self.ctrlfr = Frame(self.m)
        self.m.add(self.ctrlfr, weight=1)

        #button frame
        bf = Frame(self.ctrlfr, padding=2)
        bf.pack(side=TOP,fill=BOTH)

        side = LEFT
        #add button toolbar
        addButton(bf, 'Plot', self.replot, images.plot(),
                  'plot current data', side=side, compound="left", width=16)
        addButton(bf, 'Apply Options', self.updatePlot, images.refresh(),
                  'refresh plot with current options', side=side,
                   width=20)
        addButton(bf, 'Zoom Out', lambda: self.zoom(False), images.zoom_out(),
                  'zoom out element sizes', side=side)
        addButton(bf, 'Zoom In', self.zoom, images.zoom_in(),
                  'zoom in element sizes', side=side)
        # Interactive zoom/pan buttons
        self.zoom_btn = addButton(bf, 'Rect Zoom', self.toggle_zoom_mode, images.zoom_in(),
                  'toggle rectangle zoom mode (click and drag to zoom)', side=side)
        self.pan_btn = addButton(bf, 'Pan', self.toggle_pan_mode, images.zoom_out(),
                  'toggle pan mode (click and drag to pan)', side=side)
        addButton(bf, 'Home', self.reset_view, images.plot_clear(),
                  'reset view to original', side=side)
        self.expand_btn = addButton(bf, 'Expand', self.toggle_fullscreen, images.zoom_in(),
                  'expand/collapse plot to full area', side=side)
        addButton(bf, 'Clear', self.clear, images.plot_clear(),
                  'clear plot', side=side)
        addButton(bf, 'Save', self.savePlot, images.save(),
                  'save plot', side=side)

        #dicts to store global options, can be saved with projects
        self.globalvars = {}
        self.globalopts = OrderedDict({ 'dpi': 80, 'grid layout': False,'3D plot':False })
        from functools import partial
        for n in self.globalopts:
            val = self.globalopts[n]
            if type(val) is bool:
                v = self.globalvars[n] = BooleanVar()
                v.set(val)
                b = Checkbutton(bf,text=n, variable=v, command=partial(self.setGlobalOption, n))
            else:
                v = self.globalvars[n] = IntVar()
                v.set(val)
                Label(bf, text=n).pack(side=LEFT,fill=X,padx=2)
                b = Entry(bf,textvariable=v, width=5)
                v.trace("w", partial(self.setGlobalOption, n))
            b.pack(side=LEFT,padx=2)
        addButton(bf, 'Hide', self.toggle_options, images.prefs(),
                  'show/hide plot options', side=RIGHT)
        self.addWidgets()

        #def onpick(event):
        #    print(event)
        #self.fig.canvas.mpl_connect('pick_event', onpick)
        #self.fig.canvas.mpl_connect('button_release_event', onpick)
        from . import handlers
        dr = handlers.DragHandler(self)
        dr.connect()
        return

    def addWidgets(self):
        """
        Add option widgets (Notebook tabs) to the control panel.
        """

        self.nb = Notebook(self.ctrlfr)
        if self.showoptions == 1:
            self.nb.pack(side=TOP,fill=BOTH,expand=1)

        #add plotter tool dialogs
        w1 = self.mplopts.showDialog(self.nb)
        self.nb.add(w1, text='Base Options', sticky='news')
        #reload tkvars again from stored kwds variable
        self.mplopts.updateFromDict()
        self.styleopts = ExtraOptions(parent=self)
        self.animateopts = AnimateOptions(parent=self)

        w3 = self.labelopts.showDialog(self.nb)
        self.nb.add(w3, text='Annotation', sticky='news')
        self.labelopts.updateFromDict()
        w4 = self.layoutopts.showDialog(self.nb)
        self.nb.add(w4, text='Grid Layout', sticky='news')
        w2 = self.styleopts.showDialog(self.nb)
        self.nb.add(w2, text='Other Options', sticky='news')
        w5 = self.mplopts3d.showDialog(self.nb)
        self.nb.add(w5, text='3D Options', sticky='news')
        self.mplopts3d.updateFromDict()
        w6 = self.animateopts.showDialog(self.nb)
        self.nb.add(w6, text='Animate', sticky='news')
        return

    def setGlobalOption(self, name='', *args):
        """
        Update a global option value from the associated widget variable.

        Args:
            name (str): The name of the option.
            *args: Additional arguments (unused).
        """

        try:
            self.globalopts[name] = self.globalvars[name].get()
            #print (self.globalopts)
        except:
            logging.error("Exception occurred", exc_info=True)
        return

    def _reset_hover_targets(self):
        """Clear hover tooltip targets and annotations."""

        self._hover_targets = []
        if self._hover_annotation is not None:
            try:
                self._hover_annotation.remove()
            except Exception:
                pass
            self._hover_annotation = None
        self._hover_annotation_axes = None

    def _ensure_hover_support(self, ax):
        """Ensure annotation widget and motion handler exist for the axis."""

        if ax is None:
            return
        if self._hover_annotation is None or self._hover_annotation_axes is not ax:
            if self._hover_annotation is not None:
                try:
                    self._hover_annotation.remove()
                except Exception:
                    pass
            self._hover_annotation = ax.annotate(
                "",
                xy=(0, 0),
                xytext=(12, 12),
                textcoords="offset points",
                bbox=dict(boxstyle='round', fc='white', ec='black', lw=0.5, alpha=1.0),
                fontsize=9,
                ha='left',
                va='bottom'
            )
            # Keep tooltip above shmoo value overlays
            self._hover_annotation.set_zorder(2000)
            bbox_patch = self._hover_annotation.get_bbox_patch()
            if bbox_patch is not None:
                bbox_patch.set_zorder(1999)
            self._hover_annotation.set_visible(False)
            self._hover_annotation_axes = ax
        if self._hover_cid is None:
            self._hover_cid = self.canvas.mpl_connect("motion_notify_event", self._on_hover_motion)

    def _register_hover_target(self, artist, payload):
        """Register an artist for hover handling."""

        if artist is None:
            return
        payload = payload.copy()
        payload['artist'] = artist
        self._hover_targets.append(payload)
        self._ensure_hover_support(artist.axes)

    def _resolve_hover_point(self, target, info):
        indices = info.get('ind') if isinstance(info, dict) else None
        if not indices:
            return None
        idx = indices[0]
        x_vals = target.get('x_values')
        y_vals = target.get('y_values')
        if x_vals is None or y_vals is None:
            return None
        if idx >= len(x_vals) or idx >= len(y_vals):
            return None
        x_val = x_vals[idx]
        y_val = y_vals[idx]
        if np.isnan(x_val) or np.isnan(y_val):
            return None
        z_linear = target.get('z_linear')
        z_display = target.get('z_display')
        z_lin_val = None
        z_disp_val = None
        if z_linear is not None and idx < len(z_linear):
            z_lin_val = z_linear[idx]
        if z_display is not None and idx < len(z_display):
            z_disp_val = z_display[idx]
        labels = target.get('labels', {})
        scale = target.get('scale', 'linear')
        return {
            'x': x_val,
            'y': y_val,
            'z': z_lin_val,
            'z_display': z_disp_val,
            'labels': labels,
            'scale': scale
        }

    def _format_hover_value(self, value):
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return 'n/a'
        if isinstance(value, (int, np.integer)):
            return str(value)
        return f"{value:.6g}"

    def _format_hover_text(self, point):
        labels = point.get('labels', {})
        x_label = labels.get('x', 'X')
        y_label = labels.get('y', 'Y')
        z_label = labels.get('z', 'Z')
        lines = [
            f"{x_label}: {self._format_hover_value(point.get('x'))}",
            f"{y_label}: {self._format_hover_value(point.get('y'))}"
        ]
        z_val = point.get('z')
        z_disp = point.get('z_display')
        if z_val is not None:
            lines.append(f"{z_label}: {self._format_hover_value(z_val)}")
        elif z_disp is not None:
            lines.append(f"{z_label}: {self._format_hover_value(z_disp)}")
        if point.get('scale') == 'log' and z_val is not None and z_disp is not None:
            lines.append(f"log10({z_label}): {self._format_hover_value(z_disp)}")
        return "\n".join(lines)

    def _show_hover_annotation(self, point, ax):
        self._ensure_hover_support(ax)
        if self._hover_annotation is None:
            return
        self._hover_annotation.xy = (point.get('x'), point.get('y'))
        self._hover_annotation.set_text(self._format_hover_text(point))
        if not self._hover_annotation.get_visible():
            self._hover_annotation.set_visible(True)
        self.canvas.draw_idle()

    def _hide_hover_annotation(self):
        if self._hover_annotation is not None and self._hover_annotation.get_visible():
            self._hover_annotation.set_visible(False)
            self.canvas.draw_idle()

    def _on_hover_motion(self, event):
        if not self._hover_targets:
            return
        if event.inaxes is None:
            self._hide_hover_annotation()
            return
        for target in self._hover_targets:
            artist = target.get('artist')
            if artist is None or artist.axes is not event.inaxes:
                continue
            try:
                contains, info = artist.contains(event)
            except Exception:
                continue
            if not contains:
                continue
            point = self._resolve_hover_point(target, info)
            if point is None:
                continue
            self._show_hover_annotation(point, event.inaxes)
            return
        self._hide_hover_annotation()

    def _render_shmoo_stats_box(self, ax, stats_text):
        """Render statistics text just outside the left edge of the shmoo axes."""

        props = dict(boxstyle='round', facecolor='wheat', edgecolor='black', linewidth=0.5, alpha=1.0)
        stats_box = ax.text(
            -0.08,
            1.0,
            stats_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            horizontalalignment='right',
            bbox=props,
            clip_on=False,
        )
        stats_box.set_zorder(1000)
        bbox_patch = stats_box.get_bbox_patch()
        if bbox_patch is not None:
            bbox_patch.set_zorder(999)
        return stats_box

    def updateWidgets(self):
        """
        Update the global option widgets with current values.
        """
        for n in self.globalopts:
            self.globalvars[n].set(self.globalopts[n])

    def setOption(self, option, value):
        """
        Set a specific option value in the appropriate options class.

        Args:
            option (str): The option name.
            value: The value to set.
        """
        basewidgets = self.mplopts.tkvars
        labelwidgets = self.labelopts.tkvars
        try:
            basewidgets[option].set(value)
        except:
            labelwidgets[option].set(value)
        finally:
            pass
        return

    def replot(self, data=None):
        """
        Re-plot the data using current settings and selection.

        Args:
            data (pd.DataFrame): Optional DataFrame to plot.
                                 If None, uses the current table selection.
        """

        #print (self.table.getSelectedRows())
        if data is None:
            self.data = self.table.getSelectedDataFrame()
            # For shmoo plots, use full dataframe if selection is too small
            kind = self.mplopts.kwds.get('kind', 'line')
            if kind == 'shmoo' and len(self.data.columns) < 3:
                print("DEBUG: Shmoo plot needs 3+ columns, using full dataframe")
                self.data = self.table.model.df
        else:
            self.data = data
        self.updateStyle()
        self.applyPlotoptions()
        self.plotCurrent()
        return

    def applyPlotoptions(self):
        """
        Apply the current options from all option tabs.
        """

        self.mplopts.applyOptions()
        self.mplopts3d.applyOptions()
        self.labelopts.applyOptions()
        self.styleopts.applyOptions()
        mpl.rcParams['savefig.dpi'] = self.globalopts['dpi'] #self.dpivar.get()
        return

    def updatePlot(self):
        """
        Update the current plot with the latest applied options.
        """

        self.applyPlotoptions()
        self.plotCurrent()
        return

    def plotCurrent(self, redraw=True):
        """
        Execute the plotting based on current data and configuration.

        Args:
            redraw (bool): Whether to redraw the canvas immediately. Default is True.
        """

        layout = self.globalopts['grid layout']
        gridmode = self.layoutopts.modevar.get()
        plot3d = self.globalopts['3D plot']
        self._initFigure()
        if layout == 1 and gridmode == 'multiviews':
            self.plotMultiViews()
        elif layout == 1 and gridmode == 'splitdata':
            self.plotSplitData()
        elif plot3d == 1:
            self.plot3D(redraw=redraw)
        else:
            self.plot2D(redraw=redraw)
        return

    def zoom(self, zoomin=True):
        """
        Zoom in/out by adjusting element sizes (linewidth, markersize, fontsize).

        Args:
            zoomin (bool): True to zoom in (increase sizes), False to zoom out.
        """

        if zoomin == False:
            val=-1.0
        else:
            val=1.0

        if len(self.mplopts.kwds) == 0:
            return

        self.mplopts.increment('linewidth',val/10)
        self.mplopts.increment('ms',val)
        self.mplopts.increment('fontsize',val)
        self.replot()
        return

    def toggle_zoom_mode(self):
        """
        Toggle interactive rectangle zoom mode.
        When active, click and drag on the plot to zoom into a rectangular region.
        """
        if self._pan_mode:
            # Deactivate pan mode first
            self.toolbar.pan()
            self._pan_mode = False
            self._update_mode_button_style(self.pan_btn, False)
        
        # Toggle zoom mode
        self.toolbar.zoom()
        self._zoom_mode = not self._zoom_mode
        self._update_mode_button_style(self.zoom_btn, self._zoom_mode)
        return

    def toggle_pan_mode(self):
        """
        Toggle interactive pan mode.
        When active, click and drag on the plot to pan the view.
        """
        if self._zoom_mode:
            # Deactivate zoom mode first
            self.toolbar.zoom()
            self._zoom_mode = False
            self._update_mode_button_style(self.zoom_btn, False)
        
        # Toggle pan mode
        self.toolbar.pan()
        self._pan_mode = not self._pan_mode
        self._update_mode_button_style(self.pan_btn, self._pan_mode)
        return

    def reset_view(self):
        """
        Reset the plot view to the original/home position.
        """
        self.toolbar.home()
        self._zoom_mode = False
        self._pan_mode = False
        self._update_mode_button_style(self.zoom_btn, False)
        self._update_mode_button_style(self.pan_btn, False)
        return

    def _update_mode_button_style(self, button, active):
        """
        Update button appearance to indicate active/inactive state.
        
        Args:
            button: The button widget to update.
            active (bool): Whether the mode is active.
        """
        try:
            if active:
                button.configure(style='Active.TButton')
            else:
                button.configure(style='TButton')
        except:
            # Fallback if style doesn't work
            pass
        return

    def _connect_mouse_events(self):
        """
        Connect mouse events for Ctrl+scroll zoom and right-click pan.
        """
        # Ctrl+scroll to zoom
        self._scroll_cid = self.canvas.mpl_connect('scroll_event', self._on_scroll)
        
        # Right-click drag to pan
        self._right_press_cid = self.canvas.mpl_connect('button_press_event', self._on_right_press)
        self._right_release_cid = self.canvas.mpl_connect('button_release_event', self._on_right_release)
        self._right_motion_cid = self.canvas.mpl_connect('motion_notify_event', self._on_right_motion)
        
        # Track right-click pan state
        self._right_pan_active = False
        self._right_pan_start = None
        self._right_pan_xlim = None
        self._right_pan_ylim = None
        return

    def _on_scroll(self, event):
        """
        Handle Ctrl+scroll wheel for zooming.
        
        Args:
            event: Matplotlib scroll event.
        """
        if event.inaxes is None:
            return
        
        # Check if Ctrl key is pressed (key modifier)
        # In matplotlib, we need to check the guiEvent for modifiers
        ctrl_pressed = False
        if hasattr(event, 'guiEvent') and event.guiEvent is not None:
            try:
                # For Tkinter, check state for Control key (bit 2 = 4)
                ctrl_pressed = bool(event.guiEvent.state & 0x4)
            except:
                pass
        
        if not ctrl_pressed:
            return
        
        ax = event.inaxes
        
        # Get current axis limits
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        # Calculate zoom factor
        base_scale = 1.2
        if event.button == 'up':
            scale_factor = 1 / base_scale  # Zoom in
        elif event.button == 'down':
            scale_factor = base_scale  # Zoom out
        else:
            return
        
        # Get mouse position in data coordinates
        xdata = event.xdata
        ydata = event.ydata
        
        # Calculate new limits centered on mouse position
        new_width = (xlim[1] - xlim[0]) * scale_factor
        new_height = (ylim[1] - ylim[0]) * scale_factor
        
        # Calculate relative position of mouse in current view
        relx = (xdata - xlim[0]) / (xlim[1] - xlim[0])
        rely = (ydata - ylim[0]) / (ylim[1] - ylim[0])
        
        # Set new limits
        ax.set_xlim([xdata - new_width * relx, xdata + new_width * (1 - relx)])
        ax.set_ylim([ydata - new_height * rely, ydata + new_height * (1 - rely)])
        
        self.canvas.draw_idle()
        return

    def _on_right_press(self, event):
        """
        Handle right mouse button press for pan start.
        
        Args:
            event: Matplotlib button press event.
        """
        if event.button != 3 or event.inaxes is None:
            return
        
        self._right_pan_active = True
        self._right_pan_start = (event.xdata, event.ydata)
        self._right_pan_xlim = event.inaxes.get_xlim()
        self._right_pan_ylim = event.inaxes.get_ylim()
        self._right_pan_ax = event.inaxes
        return

    def _on_right_release(self, event):
        """
        Handle right mouse button release for pan end.
        
        Args:
            event: Matplotlib button release event.
        """
        if event.button != 3:
            return
        
        self._right_pan_active = False
        self._right_pan_start = None
        return

    def _on_right_motion(self, event):
        """
        Handle mouse motion during right-click pan.
        
        Args:
            event: Matplotlib motion event.
        """
        if not self._right_pan_active or self._right_pan_start is None:
            return
        
        if event.xdata is None or event.ydata is None:
            return
        
        ax = self._right_pan_ax
        
        # Calculate pan offset
        dx = self._right_pan_start[0] - event.xdata
        dy = self._right_pan_start[1] - event.ydata
        
        # Apply pan
        ax.set_xlim([self._right_pan_xlim[0] + dx, self._right_pan_xlim[1] + dx])
        ax.set_ylim([self._right_pan_ylim[0] + dy, self._right_pan_ylim[1] + dy])
        
        self.canvas.draw_idle()
        return

    def toggle_fullscreen(self):
        """
        Toggle between expanded (full area) and normal plot view.
        Hides/shows the control panel to maximize plot area.
        """
        if self._fullscreen_mode:
            # Restore normal view - show control frame
            self.m.add(self.ctrlfr, weight=1)
            self._fullscreen_mode = False
            try:
                self.expand_btn.configure(text='Expand')
            except:
                pass
        else:
            # Expand plot - hide control frame
            self.m.forget(self.ctrlfr)
            self._fullscreen_mode = True
            try:
                self.expand_btn.configure(text='Collapse')
            except:
                pass
        return

    def clear(self):
        """
        Clear the current figure.
        """

        self.fig.clear()
        self.ax = None
        self.canvas.draw()
        self.table.plotted=None
        self.gridaxes = {}
        return

    def _checkNumeric(self, df):
        """
        Check if the DataFrame contains plottable numeric data.

        Args:
            df (pd.DataFrame): The DataFrame to check.

        Returns:
            bool: True if numeric columns exist, False otherwise.
        """

        #x = df.convert_objects()._get_numeric_data()
        x = df.apply( lambda x: pd.to_numeric(x,errors='coerce',downcast='float') )
        if x.empty==True:
            return False

    def _initFigure(self):
        """
        Initialize the figure, clearing it or managing subplots based on layout options.
        """

        from matplotlib.gridspec import GridSpec
        layout = self.globalopts['grid layout']
        plot3d = self.globalopts['3D plot']

        #plot layout should be tracked by plotlayoutoptions
        gl = self.layoutopts

        if plot3d == 1:
            proj = '3d'
        else:
            proj = None
        if layout == 0:
            #default layout is just a single axis
            self.fig.clear()
            self.gridaxes={}
            self.ax = self.fig.add_subplot(111, projection=proj)
        else:
            #get grid layout from layout opt
            rows = gl.rows
            cols = gl.cols
            x = gl.selectedrows
            y = gl.selectedcols
            r=min(x); c=min(y)
            rowspan = gl.rowspan
            colspan = gl.colspan
            top = .92
            bottom = .1
            #print (rows,cols,r,c)
            #print (rowspan,colspan)

            ws = cols/10-.05
            hs = rows/10-.05
            gs = self.gridspec = GridSpec(rows,cols,top=top,bottom=bottom,
                                          left=0.1,right=0.9,wspace=ws,hspace=hs)
            name = str(r+1)+','+str(c+1)
            if name in self.gridaxes:
                ax = self.gridaxes[name]
                if ax in self.fig.axes:
                    self.fig.delaxes(ax)
            self.ax = self.fig.add_subplot(gs[r:r+rowspan,c:c+colspan], projection=proj)
            self.gridaxes[name] = self.ax
            #update the axes widget
            self.layoutopts.updateAxesList()
        return

    def removeSubplot(self):
        """
        Remove a specific subplot axis from the grid layout.
        """

        axname = self.layoutopts.axeslistvar.get()
        ax = self.gridaxes[axname]
        if ax in self.fig.axes:
            self.fig.delaxes(ax)
        del self.gridaxes[axname]
        self.canvas.show()
        self.layoutopts.updateAxesList()
        self.layoutopts.axeslistvar.set('')
        return

    def setSubplotTitle(self):
        """
        Prompt the user to set a title for a specific subplot.
        """

        axname = self.layoutopts.axeslistvar.get()
        if not axname in self.gridaxes:
            return
        ax = self.gridaxes[axname]
        label = simpledialog.askstring("Subplot title",
                                      "Title:",initialvalue='',
                                       parent=self.parent)
        if label:
            ax.set_title(label)
            self.canvas.show()
        return

    def plotMultiViews(self, plot_types=['bar','scatter']):
        """
        Plot multiple views (different plot types) of the same data in a grid layout.

        Args:
            plot_types (list): List of plot types to include (default is overridden by listbox selection).
        """

        #plot_types=['bar','scatter','histogram','boxplot']
        #self._initFigure()
        self.fig.clear()
        gs = self.gridspec
        gl = self.layoutopts
        plot_types = getListBoxSelection(gl.plottypeslistbox)
        kwds = self.mplopts.kwds
        rows = gl.rows
        cols = gl.cols
        c=0; i=0
        for r in range(0,rows):
            for c in range(0,cols):
                if i>=len(plot_types):
                    break
                self.ax = self.fig.add_subplot(gs[r:r+1,c:c+1])
                #print (self.ax)
                kwds['kind'] = plot_types[i]
                kwds['legend'] = False
                self.plot2D(redraw=False)
                i+=1

        #legend - put this as a normal option..
        handles, labels = self.ax.get_legend_handles_labels()
        self.fig.legend(handles, labels)
        self.canvas.draw()
        return

    def plotSplitData(self):
        """
        Split the selected data into chunks and plot each chunk in a separate grid cell.
        """

        self.fig.clear()
        gs = self.gridspec
        gl = self.layoutopts
        kwds = self.mplopts.kwds
        kwds['legend'] = False
        rows = gl.rows
        cols = gl.cols
        c=0; i=0
        data = self.data
        n = rows * cols
        chunks = np.array_split(data, n)
        proj=None
        plot3d = self.globalopts['3D plot']
        if plot3d == True:
            proj='3d'
        for r in range(0,rows):
            for c in range(0,cols):
                self.data = chunks[i]
                self.ax = self.fig.add_subplot(gs[r:r+1,c:c+1], projection=proj)
                if plot3d == True:
                    self.plot3D()
                else:
                    self.plot2D(redraw=False)
                i+=1
        handles, labels = self.ax.get_legend_handles_labels()
        self.fig.legend(handles, labels)
        self.canvas.draw()
        return

    def checkColumnNames(self, cols):
        """
        Format column names by wrapping text if too long.

        Args:
            cols (list): List of column names.

        Returns:
            list: Formatted column names.
        """

        from textwrap import fill
        try:
            cols = [fill(l, 25) for l in cols]
        except:
            logging.error("Exception occurred", exc_info=True)
        return cols

    def plot2D(self, redraw=True):
        """
        Main method for 2D plotting. Handles various plot types using pandas or custom implementations.

        Args:
            redraw (bool): Whether to redraw the canvas. Default is True.

        Returns:
            The plot axes.
        """

        if not hasattr(self, 'data'):
            return

        data = self.data
        #print (data)
        #get all options from the mpl options object
        kwds = self.mplopts.kwds
        lkwds = self.labelopts.kwds.copy()
        kind = kwds['kind']
        by = kwds['by']
        by2 = kwds['by2']
        errorbars = kwds['errorbars']
        useindex = kwds['use_index']
        bw = kwds['bw']
        self._reset_hover_targets()
        #print (kwds)
        if self._checkNumeric(data) == False and kind != 'venn':
            self.showWarning('no numeric data to plot')
            return

        kwds['edgecolor'] = 'black'
        #valid kwd args for this plot type
        kwargs = dict((k, kwds[k]) for k in valid_kwds[kind] if k in kwds)
        #initialise the figure
        #self._initFigure()
        ax = self.ax

        if by != '':
            # groupby needs to be handled per group so we can create the axes
            # for our figure and add them outside the pandas logic
            if by not in data.columns:
                # attempt to join the missing grouping column from the full table by index
                try:
                    full = self.table.model.df
                    if by in full.columns:
                        data = data.join(full[[by]], how='left')
                        self.data = data
                except Exception:
                    pass
            if by not in data.columns:
                self.showWarning('the grouping column must be in selected data')
                return
            # ensure optional second grouping column is present; if missing, try to join it
            if by2 != '':
                if by2 not in data.columns:
                    try:
                        full = self.table.model.df
                        if by2 in full.columns:
                            data = data.join(full[[by2]], how='left')
                            self.data = data
                    except Exception:
                        pass
                if by2 in data.columns:
                    by = [by, by2]
            g = data.groupby(by)

            use_subplots = kwargs.get('subplots', False)
            if use_subplots:
                i=1
                if len(g) > 30:
                    self.showWarning('%s is too many subplots' %len(g))
                    return
                size = len(g)
                nrows = int(round(np.sqrt(size),0))
                ncols = int(np.ceil(size/nrows))
                self.ax.set_visible(False)
                del kwargs['subplots']
                any_plotted = False
                last_handles, last_labels = [], []
                for n,df in g:
                    if ncols==1 and nrows==1:
                        ax = self.fig.add_subplot(111)
                        self.ax.set_visible(True)
                    else:
                        ax = self.fig.add_subplot(nrows,ncols,i)
                    kwargs['legend'] = False #remove axis legends
                    # remove grouping columns (handle single string or list)
                    try:
                        d = df.drop(by, axis=1)
                    except Exception:
                        d = df.drop(columns=by)
                    # restrict to numeric columns for plotting; skip if none
                    d_num = d._get_numeric_data()
                    if d_num.shape[1] == 0:
                        i+=1
                        continue
                    d_num = self._sanitize_dataframe_for_logy(d_num, kind)
                    axs = self._doplot(d_num, ax, kind, False,  errorbars, useindex,
                                  bw=bw, yerr=None, kwargs=kwargs)
                    # set subplot title; handle tuple group keys
                    if isinstance(n, tuple):
                        try:
                            n = (n[0], str(n[1]))
                        except Exception:
                            n = ", ".join(map(str, n))
                    ax.set_title(n)
                    handles, labels = ax.get_legend_handles_labels()
                    last_handles, last_labels = handles, labels
                    any_plotted = True
                    i+=1

                if kwargs.get('sharey') == True:
                    self.autoscale()
                if kwargs.get('sharex') == True:
                    self.autoscale('x')
                if any_plotted and last_handles:
                    self.fig.legend(last_handles, last_labels, loc='center right', #bbox_to_anchor=(0.9, 0),
                                    bbox_transform=self.fig.transFigure )
                axs = self.fig.get_axes()

            else:
                #single plot grouped only apply to some plot kinds
                #the remainder are not supported
                axs = self.ax
                labels = []; handles=[]
                cmap = plt.cm.get_cmap(kwargs['colormap'])
                # plot each group separately for line/bar/barh to avoid pivot issues
                if kind in ['line','bar','barh']:
                    groups = data.groupby(by)
                    num_groups = len(groups)
                    for i, (name, group) in enumerate(groups):
                        color = cmap(float(i)/num_groups)
                        group = group.drop(by, axis=1)
                        group_num = group._get_numeric_data()
                        if group_num.shape[1] == 0:
                            continue
                        group_num = self._sanitize_dataframe_for_logy(group_num, kind)
                        if errorbars:
                            errs = group_num.std()
                            kwargs['color'] = color
                            self._doplot(group_num, axs, kind, False, errorbars, useindex=None,
                                         bw=bw, yerr=errs, kwargs=kwargs)
                        else:
                            kwargs['color'] = color
                            self._doplot(group_num, axs, kind, False, errorbars, useindex=None,
                                         bw=bw, yerr=None, kwargs=kwargs)
                elif kind == 'scatter':
                    #we plot multiple groups and series in different colors
                    #this logic could be placed in the scatter method?
                    d = data.drop(columns=by, errors='ignore')
                    d = d._get_numeric_data()
                    d = self._sanitize_dataframe_for_logy(d, kind)
                    xcol = d.columns[0]
                    ycols = d.columns[1:]
                    c=0
                    legnames = []
                    handles = []
                    slen = len(g)*len(ycols)
                    clrs = [cmap(float(i)/slen) for i in range(slen)]
                    for n, df in g:
                        for y in ycols:
                            kwargs['color'] = clrs[c]
                            group_df = d.loc[df.index, [xcol, y]].copy()
                            currax, sc = self.scatter(group_df, ax=axs, **kwargs)
                            if type(n) is tuple:
                                n = ','.join(n)
                            legnames.append(','.join([n,y]))
                            handles.append(sc[0])
                            c+=1
                    if kwargs['legend'] == True:
                        if slen>6:
                            lc = int(np.round(slen/10))
                        else:
                            lc = 1
                        axs.legend([])
                        axs.legend(handles, legnames, ncol=lc)
                else:
                    self.showWarning('single grouped plots not supported for %s\n'
                                     'try using multiple subplots' %kind)
        else:
            #non-grouped plot
            try:
                # restrict to numeric data to avoid pandas raising on non-numeric frames
                numeric_data = data._get_numeric_data()
                if numeric_data.shape[1] == 0:
                    self.showWarning('no numeric data to plot')
                    return
                sanitized_numeric = self._sanitize_dataframe_for_logy(numeric_data, kind)
                axs = self._doplot(sanitized_numeric, ax, kind, kwds['subplots'], errorbars,
                                 useindex, bw=bw, yerr=None, kwargs=kwargs)
            except Exception as e:
                self.showWarning(e)
                logging.error("Exception occurred", exc_info=True)
                return

        #set options general for all plot types
        #annotation optons are separate
        lkwds.update(kwds)

        #table = lkwds['table']
        '''if table == True:
            #from pandas.tools.plotting import table
            from pandas.plotting import table
            if self.table.child != None:
                tabledata = self.table.child.model.df
                table(axs, np.round(tabledata, 2),
                      loc='upper left', colWidths=[0.1 for i in tabledata.columns])'''

        self.setFigureOptions(axs, lkwds)
        scf = 12/kwds['fontsize']
        try:
            self.fig.tight_layout()
            self.fig.subplots_adjust(top=0.9)
            if by != '':
                self.fig.subplots_adjust(right=0.9)
        except:
            self.fig.subplots_adjust(left=0.1, right=0.9, top=0.89,
                                     bottom=0.1, hspace=.4/scf, wspace=.2/scf)
            print ('tight_layout failed')
        #redraw annotations
        self.labelopts.redraw()
        if self.style == 'dark_background':
            self.fig.set_facecolor('black')
        else:
            self.fig.set_facecolor('white')
        if redraw == True:
            self.canvas.draw()
        return

    def setFigureOptions(self, axs, kwds):
        """
        Apply figure-wide options like title and labels to axes.

        Args:
            axs: The axes object(s).
            kwds (dict): Plot options dictionary.
        """

        if type(axs) is np.ndarray:
            self.ax = axs.flat[0]
        elif type(axs) is list:
            self.ax = axs[0]
        self.fig.suptitle(kwds['title'], fontsize=kwds['fontsize']*1.2)
        layout = self.globalopts['grid layout']
        if layout == 0:
            for ax in self.fig.axes:
                self.setAxisLabels(ax, kwds)
        else:
            self.setAxisLabels(self.ax, kwds)
        return

    def setAxisLabels(self, ax, kwds):
        """
        Set axis labels and visibility based on options.

        Args:
            ax: The axis object.
            kwds (dict): Plot options dictionary.
        """

        if kwds['xlabel'] != '':
            ax.set_xlabel(kwds['xlabel'])
        if kwds['ylabel'] != '':
            ax.set_ylabel(kwds['ylabel'])
        ax.xaxis.set_visible(kwds['showxlabels'])
        ax.yaxis.set_visible(kwds['showylabels'])
        try:
            ax.tick_params(labelrotation=kwds['rot'])
        except:
            logging.error("Exception occurred", exc_info=True)
        return

    def autoscale(self, axis='y'):
        """
        Autoscale all subplots to the same range for a given axis.

        Args:
            axis (str): 'x' or 'y'. Default is 'y'.
        """

        l=None
        u=None
        for ax in self.fig.axes:
            if axis=='y':
                a, b  = ax.get_ylim()
            else:
                a, b  = ax.get_xlim()
            if l == None or a<l:
                l=a
            if u == None or b>u:
                u=b
        lims = (l, u)
        print (lims)
        for a in self.fig.axes:
            if axis=='y':
                a.set_ylim(lims)
            else:
                a.set_xlim(lims)
        return

    def _clearArgs(self, kwargs):
        """
        Remove formatting arguments (colormap, grid) from kwargs to allow style usage.

        Args:
            kwargs (dict): The arguments dictionary.

        Returns:
            dict: The cleaned dictionary.
        """

        keys = ['colormap','grid']
        for k in keys:
            if k in kwargs:
                kwargs[k] = None
        return kwargs

    def _log_safe_floor(self, values):
        """Compute a safe replacement floor for log scaling."""

        arr = np.asarray(values, dtype=float)
        positive = arr[arr > 0]
        if positive.size > 0:
            min_positive = positive.min()
        else:
            non_zero = np.abs(arr[arr != 0])
            min_positive = non_zero.min() if non_zero.size > 0 else 1.0
        min_positive = max(min_positive, np.finfo(float).tiny)
        return min_positive / 10.0

    def _clamp_for_log_scale(self, values):
        """Clamp non-positive values so log plots remain valid."""

        arr = np.asarray(values, dtype=float)
        if np.all(arr > 0):
            return arr
        safe_floor = self._log_safe_floor(arr)
        return np.where(arr <= 0, safe_floor, arr)

    def _sanitize_dataframe_for_logy(self, data, kind):
        """Return a copy with non-positive Y data replaced for log plots."""

        logy_kinds = {'line', 'area', 'bar', 'barh', 'boxplot', 'violinplot', 'dotplot', 'scatter'}
        if kind not in logy_kinds:
            return data

        sanitized = data.copy()
        numeric_cols = sanitized.select_dtypes(include=[np.number]).columns
        if not len(numeric_cols):
            return sanitized

        if kind == 'scatter':
            cols_to_adjust = [col for col in numeric_cols if col != sanitized.columns[0]]
        else:
            cols_to_adjust = numeric_cols

        for col in cols_to_adjust:
            sanitized[col] = self._clamp_for_log_scale(sanitized[col].to_numpy())
        return sanitized

    def _doplot(self, data, ax, kind, subplots, errorbars, useindex, bw, yerr, kwargs):
        """
        Dispatch the plotting task to specific methods based on 'kind'.

        Args:
            data (pd.DataFrame): The data to plot.
            ax: The axis to plot on.
            kind (str): The type of plot.
            subplots (bool): Whether to use subplots.
            errorbars (bool): Whether to show error bars.
            useindex (bool): Whether to use the index as x-axis.
            bw (bool): Black and white mode.
            yerr: Error values.
            kwargs (dict): Additional arguments.

        Returns:
            The plot axes.
        """

        kwargs = kwargs.copy()
        if self.style != None:
            keargs = self._clearArgs(kwargs)

        cols = data.columns
        if kind == 'line':
            data = data.sort_index()

        rows = int(round(np.sqrt(len(data.columns)),0))
        if len(data.columns) == 1 and kind not in ['pie']:
            kwargs['subplots'] = False
        if 'colormap' in kwargs:
            cmap = plt.cm.get_cmap(kwargs['colormap'])
        else:
            cmap = None
        styles = []
        if bw == True and kind not in ['pie','heatmap']:
            cmap = None
            kwargs['color'] = 'k'
            kwargs['colormap'] = None
            styles = ["-","--","-.",":"]
            if 'linestyle' in kwargs:
                del kwargs['linestyle']

        if subplots == 0:
            layout = None
        else:
            layout=(rows,-1)

        if errorbars == True and yerr == None:
            yerr = data[data.columns[1::2]]
            data = data[data.columns[0::2]]
            yerr.columns = data.columns
            plt.rcParams['errorbar.capsize']=4

        if kind == 'bar' or kind == 'barh':
            if len(data) > 50:
                ax.get_xaxis().set_visible(False)
            if len(data) > 300:
                self.showWarning('too many bars to plot')
                return
        plot_data = self._sanitize_dataframe_for_logy(data, kind)

        if kind == 'scatter':
            axs, sc = self.scatter(plot_data, ax, **kwargs)
            if kwargs['sharey'] == 1:
                lims = self.fig.axes[0].get_ylim()
                for a in self.fig.axes:
                    a.set_ylim(lims)
        elif kind == 'boxplot':
            box_data = self._sanitize_dataframe_for_logy(data, 'boxplot')
            axs = box_data.boxplot(ax=ax, grid=kwargs['grid'],
                               patch_artist=True, return_type='dict')
            lw = kwargs['linewidth']
            plt.setp(axs['boxes'], color='black', lw=lw)
            plt.setp(axs['whiskers'], color='black', lw=lw)
            plt.setp(axs['fliers'], color='black', marker='+', lw=lw)
            clr = cmap(0.5)
            for patch in axs['boxes']:
                patch.set_facecolor(clr)
            if kwargs['logy'] == 1:
                ax.set_yscale('log')
        elif kind == 'violinplot':
            sanitized = self._sanitize_dataframe_for_logy(data, 'violinplot')
            axs = self.violinplot(sanitized, ax, kwargs)
        elif kind == 'dotplot':
            sanitized = self._sanitize_dataframe_for_logy(data, 'dotplot')
            axs = self.dotplot(sanitized, ax, kwargs)
        elif kind == 'histogram':
            min_str = self.mplopts.kwds.get('hist_min', '')
            max_str = self.mplopts.kwds.get('hist_max', '')
            try:
                min_v = float(min_str) if str(min_str).strip() != '' else None
            except Exception:
                min_v = None
            try:
                max_v = float(max_str) if str(max_str).strip() != '' else None
            except Exception:
                max_v = None
            fdata = data.copy()
            for col in fdata.columns:
                s = pd.to_numeric(fdata[col], errors='coerce')
                m = ~s.isna()
                if min_v is not None:
                    m &= s >= min_v
                if max_v is not None:
                    m &= s <= max_v
                fdata[col] = s.where(m, np.nan)
            b = kwargs.get('bins', None)
            if isinstance(b, str):
                try:
                    kwargs['bins'] = int(b)
                except Exception:
                    try:
                        w = float(b)
                        arr = np.asarray(fdata.to_numpy().flatten(), dtype=float)
                        if arr.size:
                            mn = np.nanmin(arr)
                            mx = np.nanmax(arr)
                            if not np.isfinite(mn) or not np.isfinite(mx) or mx == mn:
                                kwargs['bins'] = 20
                            else:
                                count = max(int(np.ceil((mx - mn) / max(w, 1e-12))), 1)
                                edges = np.linspace(mn, mx, count + 1)
                                kwargs['bins'] = edges
                        else:
                            kwargs['bins'] = 20
                    except Exception:
                        kwargs['bins'] = 20
            elif isinstance(b, float):
                if b.is_integer() or b >= 2.0:
                    kwargs['bins'] = int(round(b))
                else:
                    w = b
                    arr = np.asarray(fdata.to_numpy().flatten(), dtype=float)
                    if arr.size:
                        mn = np.nanmin(arr)
                        mx = np.nanmax(arr)
                        if not np.isfinite(mn) or not np.isfinite(mx) or mx == mn:
                            kwargs['bins'] = 20
                        else:
                            count = max(int(np.ceil((mx - mn) / max(w, 1e-12))), 1)
                            edges = np.linspace(mn, mx, count + 1)
                            kwargs['bins'] = edges
                    else:
                        kwargs['bins'] = 20
            axs = fdata.plot(kind='hist',layout=layout, ax=ax, **kwargs)
            if min_v is not None:
                ax.axvline(min_v, color='red', linestyle='--', linewidth=1)
            if max_v is not None:
                ax.axvline(max_v, color='red', linestyle='--', linewidth=1)
            try:
                lines = []
                for col in fdata.columns:
                    s = pd.to_numeric(fdata[col], errors='coerce')
                    s = s.dropna()
                    if s.empty:
                        continue
                    lines.append(
                        f"{col}: min={s.min():.6g}, max={s.max():.6g}, mean={s.mean():.6g}, median={s.median():.6g}, std={s.std(ddof=1):.6g}"
                    )
                if lines:
                    txt = "\n".join(lines)
                    ann_ax = axs
                    if isinstance(ann_ax, np.ndarray):
                        ann_ax = ann_ax.flat[0]
                    fs = max(int(self.mplopts.kwds.get('fontsize', 12) * 0.9), 8)
                    ann_ax.text(
                        0.98,
                        0.98,
                        txt,
                        transform=ann_ax.transAxes,
                        ha='right',
                        va='top',
                        bbox=dict(boxstyle='round', fc='white', ec='black', lw=0.5, alpha=0.7),
                        fontsize=fs,
                    )
            except Exception:
                pass
        elif kind == 'heatmap':
            if len(data) > 1000:
                self.showWarning('too many rows to plot')
                return
            axs = self.heatmap(data, ax, kwargs)
        elif kind == 'bootstrap':
            axs = plotting.bootstrap_plot(data)
        elif kind == 'scatter_matrix':
            axs = pd.plotting.scatter_matrix(data, ax=ax, **kwargs)
        elif kind == 'hexbin':
            x = cols[0]
            y = cols[1]
            axs = data.plot(x,y,ax=ax,kind='hexbin',gridsize=20,**kwargs)
        elif kind == 'contour':
            xi,yi,zi = self.contourData(data)
            cs = ax.contour(xi,yi,zi,15,linewidths=.5,colors='k')
            cs = ax.contourf(xi,yi,zi,15,cmap=cmap)
            self.fig.colorbar(cs,ax=ax)
            axs = ax
        elif kind == 'imshow':
            xi,yi,zi = self.contourData(data)
            im = ax.imshow(zi, interpolation="nearest",
                           cmap=cmap, alpha=kwargs['alpha'])
            self.fig.colorbar(im,ax=ax)
            axs = ax
        elif kind == 'pie':
            if useindex == False:
                x=data.columns[0]
                data.set_index(x,inplace=True)
            if kwargs['legend'] == True:
                lbls=None
            else:
                lbls = list(data.index)
            axs = data.plot(ax=ax,kind='pie', labels=lbls, layout=layout,
                            autopct='%1.1f%%', subplots=True, **kwargs)
            if lbls == None:
                axs[0].legend(labels=data.index, loc='best')
        elif kind == 'venn':
            axs = self.venn(data, ax, **kwargs)
        elif kind == 'radviz':
            if kwargs['marker'] == '':
                kwargs['marker'] = 'o'
            col = data.columns[-1]
            axs = pd.plotting.radviz(data, col, ax=ax, **kwargs)
        elif kind == 'density':
            axs = self.density(data, ax, kwargs)
        elif kind == 'shmoo':
            axs = self.shmoo(data, ax, kwargs)
        elif kind == 'bathtub':
            axs = self.bathtub(data, ax, kwargs)
        elif kind == 'sparam':
            axs = self.sparam(data, ax, kwargs)
        elif kind == 'gantt':
            axs = self.gantt(data, ax, kwargs)
        elif kind == 'eye':
            axs = self.eye(data, ax, kwargs)
        elif kind == 'jitter':
            axs = self.jitter(data, ax, kwargs)
        elif kind == 'phasenoise':
            axs = self.phasenoise(data, ax, kwargs)
        else:
            if useindex == False:
                x=data.columns[0]
                data.set_index(x,inplace=True)
            if len(data.columns) == 0:
                msg = "Not enough data.\nIf 'use index' is off select at least 2 columns"
                self.showWarning(msg)
                return
            if cmap != None:
                cmap = util.adjustColorMap(cmap, 0.15,1.0)
                del kwargs['colormap']
            if kind == 'barh':
                kwargs['xerr']=yerr
                yerr=None
            axs = data.plot(ax=ax, layout=layout, yerr=yerr, style=styles, cmap=cmap,
                             **kwargs)
        self._setAxisRanges()
        self._setAxisTickFormat()
        return axs

    def _setAxisRanges(self):
        """
        Set explicit axis limits if specified in style options.
        """
        kwds = self.styleopts.kwds
        ax = self.ax
        try:
            xmin=float(kwds['xmin'])
            xmax=float(kwds['xmax'])
            ax.set_xlim((xmin,xmax))
        except:
            pass
        try:
            ymin=float(kwds['ymin'])
            ymax=float(kwds['ymax'])
            ax.set_ylim((ymin,ymax))
        except:
            pass
        return

    def _setAxisTickFormat(self):
        """
        Set axis tick locators and formatters based on style options.
        """

        import matplotlib.ticker as mticker
        kwds = self.styleopts.kwds
        ax = self.ax
        data = self.data
        cols = list(data.columns)
        x = data[cols[0]]
        xt = kwds['major x-ticks']
        yt = kwds['major y-ticks']
        xmt = kwds['minor x-ticks']
        ymt = kwds['minor y-ticks']
        symbol = kwds['symbol']
        places = kwds['precision']
        dateformat = kwds['date format']
        if xt != 0:
            ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=xt))
        if yt != 0:
            ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=yt))
        if xmt != 0:
            ax.xaxis.set_minor_locator(mticker.AutoMinorLocator(n=xmt))
            ax.grid(b=True, which='minor', linestyle='--', linewidth=.5)
        if ymt != 0:
            ax.yaxis.set_minor_locator(mticker.AutoMinorLocator(n=ymt))
            ax.grid(b=True, which='minor', linestyle='--', linewidth=.5)
        formatter = kwds['formatter']
        if formatter == 'percent':
            ax.xaxis.set_major_formatter(mticker.PercentFormatter())
        elif formatter == 'eng':
            ax.xaxis.set_major_formatter(mticker.EngFormatter(unit=symbol,places=places))
        elif formatter == 'sci notation':
            ax.xaxis.set_major_formatter(mticker.LogFormatterSciNotation())
        if dateformat != '':
            print (x.dtype)
            import matplotlib.dates as mdates
            ax.xaxis.set_major_formatter(mdates.DateFormatter(dateformat))
        return

    def scatter(self, df, ax, alpha=0.8, marker='o', color=None, **kwds):
        """
        Custom scatter plot implementation.
        Plots the first column against subsequent columns.

        Args:
            df (pd.DataFrame): Data to plot.
            ax: Axis to plot on.
            alpha (float): Transparency.
            marker (str): Marker style.
            color: Color override.
            **kwds: Additional keyword arguments.

        Returns:
            tuple: (ax, handles)
        """

        if len(df.columns)<2:
            self.showWarning('scatter plot requires at least 2 columns')
            return ax, []
        data = df
        df = df.copy()._get_numeric_data()
        cols = list(df.columns)
        x = df[cols[0]]
        s=1
        cmap = plt.cm.get_cmap(kwds['colormap'])
        lw = kwds['linewidth']
        clrcol = kwds['clrcol']  #color by values in a column
        cscale = kwds['cscale']
        grid = kwds['grid']
        bw = kwds['bw']

        if cscale == 'log':
            norm = mpl.colors.LogNorm()
        else:
            norm = None
        if color != None:
            c = color
        elif clrcol != '':
            if clrcol in df.columns:
                if len(cols)>2:
                    cols.remove(clrcol)
            c = data[clrcol]
            if c.dtype.kind not in 'bifc':
                c = pd.factorize(c)[0]
        else:
            c = None
        plots = len(cols)
        if marker == '':
            marker = 'o'
        if kwds['subplots'] == True:
            size = plots-1
            nrows = int(round(np.sqrt(size),0))
            ncols = int(np.ceil(size/nrows))
            self.fig.clear()
        if c is not None:
            colormap = kwds['colormap']
        else:
            colormap = None
            c=None

        #print (kwds)
        labelcol = kwds['labelcol']
        pointsizes = kwds['pointsizes']
        handles = []
        for i in range(s,plots):
            y = df[cols[i]]
            ec = 'black'
            if bw == True:
                clr = 'white'
                colormap = None
            else:
                clr = cmap(float(i)/(plots))
            if colormap != None:
                clr=None
            if marker in ['x','+'] and bw == False:
                ec = clr

            if kwds['subplots'] == True:
                ax = self.fig.add_subplot(nrows,ncols,i)
            if pointsizes != '' and pointsizes in df.columns:
                ms = df[pointsizes]
                s=kwds['ms']
                getsizes = lambda x : (((x-x.min())/float(x.max()-x.min())+1)*s)**2.3
                ms = getsizes(ms)
                #print (ms)
            else:
                ms = kwds['ms'] * 12
            sc = ax.scatter(x, y, marker=marker, alpha=alpha, linewidth=lw, c=c,
                       s=ms, edgecolors=ec, facecolor=clr, cmap=colormap,
                       norm=norm, label=cols[i], picker=True)

            #create proxy artist for markers so we can return these handles if needed
            mkr = Line2D([0], [0], marker=marker, alpha=alpha, ms=10, markerfacecolor=c,
                        markeredgewidth=lw, markeredgecolor=ec, linewidth=0)
            handles.append(mkr)
            ax.set_xlabel(cols[0])
            if kwds['logx'] == 1:
                ax.set_xscale('log')
            if kwds['logy'] == 1:
                ax.set_yscale('log')
                ax.set_ylim((x.min()+.1,x.max()))
            if grid == 1:
                ax.grid(True)
            if kwds['subplots'] == True:
                ax.set_title(cols[i])
            if colormap is not None and kwds['colorbar'] == True:
                self.fig.colorbar(sc, ax=ax)

            if labelcol != '':
                if not labelcol in data.columns:
                    self.showWarning('label column %s not in selected data' %labelcol)
                elif len(data)<1500:
                    for i, r in data.iterrows():
                        txt = r[labelcol]
                        if pd.isnull(txt) is True:
                            continue
                        ax.annotate(txt, (x[i],y[i]), xycoords='data',
                                    xytext=(5, 5), textcoords='offset points',)

        if kwds['legend'] == 1 and kwds['subplots'] == False:
            ax.legend(cols[1:])

        return ax, handles

    def violinplot(self, df, ax, kwds):
        """
        Create a violin plot.

        Args:
            df (pd.DataFrame): Data.
            ax: Axis.
            kwds (dict): Options.

        Returns:
            The axis.
        """

        data=[]
        clrs=[]
        cols = len(df.columns)
        cmap = plt.cm.get_cmap(kwds['colormap'])
        for i,d in enumerate(df):
            clrs.append(cmap(float(i)/cols))
            data.append(df[d].values)
        lw = kwds['linewidth']
        alpha = kwds['alpha']
        parts = ax.violinplot(data, showextrema=False, showmeans=True)
        i=0
        for pc in parts['bodies']:
            pc.set_facecolor(clrs[i])
            pc.set_edgecolor('black')
            pc.set_alpha(alpha)
            pc.set_linewidth(lw)
            i+=1
        labels = df.columns
        ax.set_xticks(np.arange(1, len(labels) + 1))
        ax.set_xticklabels(labels)
        return

    def dotplot(self, df, ax, kwds):
        """
        Create a dot plot (strip plot).

        Args:
            df (pd.DataFrame): Data.
            ax: Axis.
            kwds (dict): Options.

        Returns:
            The axis.
        """

        marker = kwds['marker']
        if marker == '':
            marker = 'o'
        cmap = plt.cm.get_cmap(kwds['colormap'])
        ms = kwds['ms']
        lw = kwds['linewidth']
        alpha = kwds['alpha']
        cols = len(df.columns)
        axs = df.boxplot(ax=ax, grid=False, return_type='dict')
        plt.setp(axs['boxes'], color='white')
        plt.setp(axs['whiskers'], color='white')
        plt.setp(axs['caps'], color='black', lw=lw)
        plt.setp(axs['medians'], color='black', lw=lw)
        np.random.seed(42)
        for i,d in enumerate(df):
            clr = cmap(float(i)/cols)
            y = df[d]
            x = np.random.normal(i+1, 0.04, len(y))
            ax.plot(x, y, c=clr, mec='k', ms=ms, marker=marker, alpha=alpha, mew=lw, linestyle="None")
        if kwds['logy'] == 1:
            ax.set_yscale('log')
        return ax

    def heatmap(self, df, ax, kwds):
        """
        Create a heatmap plot.

        Args:
            df (pd.DataFrame): Data.
            ax: Axis.
            kwds (dict): Options.
        """

        X = df._get_numeric_data()
        clr='black'
        lw = kwds['linewidth']
        if lw==0:
            clr=None
            lw=None
        if kwds['cscale']=='log':
            norm=mpl.colors.LogNorm()
        else:
            norm=None
        hm = ax.pcolor(X, cmap=kwds['colormap'], edgecolor=clr,
                       linewidth=lw,alpha=kwds['alpha'],norm=norm)
        if kwds['colorbar'] == True:
            self.fig.colorbar(hm, ax=ax)
        ax.set_xticks(np.arange(0.5, len(X.columns)))
        ax.set_yticks(np.arange(0.5, len(X.index)))
        ax.set_xticklabels(X.columns, minor=False)
        ax.set_yticklabels(X.index, minor=False)
        ax.set_ylim(0, len(X.index))
        ##if kwds['rot'] != 0:
        #    for tick in ax.get_xticklabels():
        #        tick.set_rotation(kwds['rot'])
        #from mpl_toolkits.axes_grid1 import make_axes_locatable
        #divider = make_axes_locatable(ax)
        return

    def venn(self, data, ax, colormap=None, alpha=0.8):
        """
        Create a Venn diagram (2 or 3 sets).
        Requires matplotlib-venn.

        Args:
            data (pd.DataFrame): Data (columns used as sets).
            ax: Axis.
            colormap: Colormap name (unused in current impl?).
            alpha (float): Transparency (unused?).

        Returns:
            The axis.
        """

        try:
            from matplotlib_venn import venn2,venn3
        except:
            self.showWarning('requires matplotlib_venn')
            return
        l = len(data.columns)
        if l<2: return
        x=data.values[:,0]
        y=data.values[:,1]
        if l==2:
            labels = list(data.columns[:2])
            v = venn2([set(x), set(y)], set_labels=labels, ax=ax)
        else:
            labels = list(data.columns[:3])
            z = data.values[:,2]
            v = venn3([set(x), set(y), set(z)], set_labels=labels, ax=ax)
        ax.axis('off')
        ax.set_axis_off()
        return ax

    def bathtub(self, df, ax, kwds):
        """Create bathtub curve plot for SerDes BER analysis.
        
        A bathtub curve shows Bit Error Rate (BER) vs sampling point position,
        used to measure timing margins in high-speed serial links.
        
        Parameters:
        -----------
        df : pandas.DataFrame
            Data with sample points and BER values
        ax : matplotlib.axes.Axes
            Axes object to plot on
        kwds : dict
            Plotting keywords
            
        Returns:
        --------
        ax : matplotlib.axes.Axes
        """
        from scipy import interpolate
        
        print(f"DEBUG: bathtub() called with {len(df)} rows, {len(df.columns)} columns")
        print(f"DEBUG: Columns: {list(df.columns)}")
        
        # Get options
        ber_target_str = kwds.get('ber_target', '1e-12')
        show_margins = kwds.get('show_margins', True)
        x_axis_type = kwds.get('x_axis_type', 'UI')
        show_target_line = kwds.get('show_target_line', True)
        margin_style = kwds.get('margin_style', 'arrows')
        dual_curve = kwds.get('dual_curve', False)
        grid = kwds.get('grid', True)
        legend = kwds.get('legend', True)
        
        # Parse BER target
        try:
            ber_target = float(ber_target_str)
        except (ValueError, TypeError):
            ber_target = 1e-12
        
        # Get numeric data
        data = df._get_numeric_data()
        
        if len(data.columns) < 2:
            self.showWarning('Bathtub plot requires at least 2 columns (Sample Point, BER)')
            return ax
        
        # Auto-detect columns
        x_col = data.columns[0]  # Sample point (UI, ps, or mV)
        
        # Check if dual curve (3 columns: x, ber_left, ber_right)
        if len(data.columns) >= 3 and dual_curve:
            y_cols = [data.columns[1], data.columns[2]]
            labels = [data.columns[1], data.columns[2]]
        else:
            y_cols = [data.columns[1]]
            labels = [data.columns[1]]
        
        x_data = data[x_col].values
        
        # Plot each BER curve
        for i, y_col in enumerate(y_cols):
            y_data = data[y_col].values
            
            # Remove NaN values
            mask = ~(np.isnan(x_data) | np.isnan(y_data))
            x_clean = x_data[mask]
            y_clean = y_data[mask]
            
            if len(x_clean) < 2:
                continue
            
            # Sort by x for proper plotting
            sort_idx = np.argsort(x_clean)
            x_clean = x_clean[sort_idx]
            y_clean = y_clean[sort_idx]
            
            # Plot BER curve
            ax.semilogy(x_clean, y_clean, marker='o', linewidth=2, label=labels[i])
            
            # Calculate margin at target BER
            if show_margins and len(x_clean) > 2:
                try:
                    # Interpolate in log space
                    log_y = np.log10(y_clean)
                    log_target = np.log10(ber_target)
                    
                    # Find crossings
                    f = interpolate.interp1d(x_clean, log_y, kind='linear', fill_value='extrapolate')
                    
                    # Find left and right crossings
                    x_fine = np.linspace(x_clean.min(), x_clean.max(), 1000)
                    y_fine = f(x_fine)
                    
                    # Find where curve crosses target
                    crossings = []
                    for j in range(len(y_fine)-1):
                        if (y_fine[j] >= log_target and y_fine[j+1] < log_target) or \
                           (y_fine[j] <= log_target and y_fine[j+1] > log_target):
                            # Linear interpolation to find exact crossing
                            x_cross = x_fine[j] + (log_target - y_fine[j]) * (x_fine[j+1] - x_fine[j]) / (y_fine[j+1] - y_fine[j])
                            crossings.append(x_cross)
                    
                    if len(crossings) >= 2:
                        left_margin = crossings[0]
                        right_margin = crossings[-1]
                        margin = right_margin - left_margin
                        
                        # Draw margin annotation
                        if margin_style == 'arrows':
                            ax.annotate('', xy=(right_margin, ber_target), xytext=(left_margin, ber_target),
                                      arrowprops=dict(arrowstyle='<->', color='red', lw=2))
                            ax.text((left_margin + right_margin)/2, ber_target*2, 
                                  f'Margin: {margin:.3f} {x_axis_type}',
                                  ha='center', va='bottom', color='red', fontweight='bold')
                        elif margin_style == 'lines':
                            ax.axvline(left_margin, color='red', linestyle='--', alpha=0.7)
                            ax.axvline(right_margin, color='red', linestyle='--', alpha=0.7)
                        elif margin_style == 'shaded':
                            ax.axvspan(left_margin, right_margin, alpha=0.2, color='green')
                
                except Exception as e:
                    print(f"Warning: Could not calculate margin: {e}")
        
        # Show target BER line
        if show_target_line:
            ax.axhline(ber_target, color='gray', linestyle='--', linewidth=1, 
                      label=f'Target BER: {ber_target:.0e}')
        
        # Labels and formatting
        ax.set_xlabel(f'Sample Point ({x_axis_type})', fontsize=12)
        ax.set_ylabel('Bit Error Rate (BER)', fontsize=12)
        ax.set_title('Bathtub Curve', fontsize=14, fontweight='bold')
        
        if grid:
            ax.grid(True, alpha=0.3, which='both')
        
        if legend:
            ax.legend(loc='best')
        
        # Set y-axis limits for better visibility
        if len(y_cols) > 0:
            all_y = np.concatenate([data[col].dropna().values for col in y_cols])
            if len(all_y) > 0:
                y_min = max(all_y.min(), 1e-18)
                y_max = min(all_y.max(), 1e-1)
                ax.set_ylim(y_min/10, y_max*10)
        
        return ax

    def sparam(self, df, ax, kwds):
        """Create S-parameter plot for channel characterization.
        
        S-parameters show frequency response of channels, typically
        insertion loss (S21) and return loss (S11/S22).
        
        Parameters:
        -----------
        df : pandas.DataFrame
            Data with frequency and S-parameter values
        ax : matplotlib.axes.Axes
            Axes object to plot on
        kwds : dict
            Plotting keywords
            
        Returns:
        --------
        ax : matplotlib.axes.Axes
        """
        from scipy import interpolate
        
        print(f"DEBUG: sparam() called with {len(df)} rows, {len(df.columns)} columns")
        print(f"DEBUG: Columns: {list(df.columns)}")
        
        # Get options
        log_freq = kwds.get('log_freq', True)
        show_phase = kwds.get('show_phase', False)
        spec_limit_str = kwds.get('spec_limit', '')
        limit_type = kwds.get('limit_type', 'None')
        nyquist_marker = kwds.get('nyquist_marker', False)
        data_rate_str = kwds.get('data_rate', '')
        freq_range_str = kwds.get('freq_range', '')
        db_range_str = kwds.get('db_range', '')
        grid = kwds.get('grid', True)
        legend = kwds.get('legend', True)
        
        # Parse spec limit
        spec_limit = None
        if spec_limit_str:
            try:
                spec_limit = float(spec_limit_str)
            except (ValueError, TypeError):
                pass
        
        # Parse data rate for Nyquist
        data_rate = None
        if data_rate_str:
            try:
                data_rate = float(data_rate_str)
            except (ValueError, TypeError):
                pass
        
        # Get numeric data
        data = df._get_numeric_data()
        
        if len(data.columns) < 2:
            self.showWarning('S-parameter plot requires at least 2 columns (Frequency, S-parameter)')
            return ax
        
        # Auto-detect frequency column (first column)
        freq_col = data.columns[0]
        freq_data = data[freq_col].values
        
        # Auto-detect and convert frequency units
        if freq_data.max() > 1000:  # Likely MHz or Hz
            if freq_data.max() > 1e6:
                freq_ghz = freq_data / 1e9  # Hz to GHz
                print(f"DEBUG: Converted frequency from Hz to GHz")
            else:
                freq_ghz = freq_data / 1000  # MHz to GHz
                print(f"DEBUG: Converted frequency from MHz to GHz")
        else:
            freq_ghz = freq_data  # Already in GHz
        
        # Get S-parameter columns (all except first)
        sparam_cols = data.columns[1:]
        
        # Plot each S-parameter
        for col in sparam_cols:
            sparam_data = data[col].values
            
            # Remove NaN values
            mask = ~(np.isnan(freq_ghz) | np.isnan(sparam_data))
            freq_clean = freq_ghz[mask]
            sparam_clean = sparam_data[mask]
            
            if len(freq_clean) < 2:
                continue
            
            # Sort by frequency
            sort_idx = np.argsort(freq_clean)
            freq_clean = freq_clean[sort_idx]
            sparam_clean = sparam_clean[sort_idx]
            
            # Plot S-parameter
            if log_freq:
                ax.semilogx(freq_clean, sparam_clean, linewidth=2, label=col, marker='o', markersize=3)
            else:
                ax.plot(freq_clean, sparam_clean, linewidth=2, label=col, marker='o', markersize=3)
        
        # Add spec limit line
        if spec_limit is not None and limit_type != 'None':
            if limit_type == 'Horizontal':
                ax.axhline(spec_limit, color='red', linestyle='--', linewidth=2, 
                          label=f'Spec Limit: {spec_limit} dB')
            elif limit_type == 'Vertical' and data_rate is not None:
                nyquist_ghz = data_rate / 2
                ax.axvline(nyquist_ghz, color='red', linestyle='--', linewidth=2,
                          label=f'Nyquist: {nyquist_ghz} GHz')
        
        # Add Nyquist marker
        if nyquist_marker and data_rate is not None:
            nyquist_ghz = data_rate / 2
            ax.axvline(nyquist_ghz, color='orange', linestyle=':', linewidth=2,
                      label=f'Nyquist: {nyquist_ghz} GHz')
        
        # Labels and formatting
        ax.set_xlabel('Frequency (GHz)', fontsize=12)
        ax.set_ylabel('Magnitude (dB)', fontsize=12)
        ax.set_title('S-Parameter Plot', fontsize=14, fontweight='bold')
        
        if grid:
            ax.grid(True, alpha=0.3, which='both')
        
        if legend:
            ax.legend(loc='best')
        
        # Set axis ranges if specified
        if freq_range_str:
            try:
                freq_min, freq_max = map(float, freq_range_str.split('-'))
                ax.set_xlim(freq_min, freq_max)
            except:
                pass
        
        if db_range_str:
            try:
                db_min, db_max = map(float, db_range_str.split('-'))
                ax.set_ylim(db_min, db_max)
            except:
                pass
        
        return ax

    def gantt(self, df, ax, kwds):
        """Create Gantt chart for project timeline visualization.
        
        A Gantt chart displays project tasks as horizontal bars along a timeline,
        showing task durations, dependencies, and progress.
        
        Parameters:
        -----------
        df : pandas.DataFrame
            Data with task information
        ax : matplotlib.axes.Axes
            Axes object to plot on
        kwds : dict
            Plotting keywords
            
        Returns:
        --------
        ax : matplotlib.axes.Axes
        """
        import matplotlib.dates as mdates
        from datetime import datetime, timedelta
        
        print(f"DEBUG: gantt() called with {len(df)} rows, {len(df.columns)} columns")
        print(f"DEBUG: Columns: {list(df.columns)}")
        
        # Get options
        show_progress = kwds.get('show_progress', True)
        show_today = kwds.get('show_today', True)
        date_format = kwds.get('date_format', '%Y-%m-%d')
        bar_height = kwds.get('bar_height', 0.8)
        show_milestones = kwds.get('show_milestones', True)
        group_by = kwds.get('group_by', '')
        sort_by = kwds.get('sort_by', 'start_date')
        colormap = kwds.get('colormap', 'tab10')
        grid = kwds.get('grid', True)
        legend = kwds.get('legend', True)
        
        # Identify required columns
        # Expected columns: Task, Start, End (or Duration), Progress (optional), Status (optional)
        data = df.copy()

        def _identify_columns(current_data):
            """Return tuple with detected gantt columns from the provided dataframe."""

            def _match(candidates):
                for candidate in candidates:
                    if candidate in current_data.columns:
                        return candidate
                return None

            task = _match(['Task', 'task', 'Task_Name', 'task_name', 'Name', 'name'])
            if task is None and len(current_data.columns) > 0:
                task = current_data.columns[0]

            start = _match(['Start', 'start', 'Start_Date', 'start_date', 'Begin', 'begin'])
            end = _match(['End', 'end', 'End_Date', 'end_date', 'Finish', 'finish'])
            duration = _match(['Duration', 'duration', 'Days', 'days'])
            progress = _match(['Progress', 'progress', 'Complete', 'complete', 'Completion', 'completion'])
            status = _match(['Status', 'status', 'State', 'state'])
            return task, start, end, duration, progress, status

        task_col, start_col, end_col, duration_col, progress_col, status_col = _identify_columns(data)

        # If the current selection is missing required columns, try falling back to full table data
        if (task_col is None or start_col is None) and hasattr(self, 'table'):
            base_df = getattr(getattr(getattr(self, 'table', None), 'model', None), 'df', None)
            if base_df is not None:
                try:
                    if len(df.index) > 0:
                        fallback = base_df.loc[df.index].copy()
                    else:
                        fallback = base_df.copy()
                except Exception:
                    # Fall back to full dataframe order if index alignment fails
                    fallback = base_df.copy()

                if fallback is not None and len(fallback.columns) > 0:
                    data = fallback
                    task_col, start_col, end_col, duration_col, progress_col, status_col = _identify_columns(data)
                    print('DEBUG: Gantt fallback to full dataframe for column detection')

        # Validate required columns
        if task_col is None or start_col is None:
            self.showWarning('Gantt chart requires at least Task and Start columns')
            return ax
        
        # Convert dates
        try:
            data[start_col] = pd.to_datetime(data[start_col])
        except Exception as e:
            self.showWarning(f'Could not parse start dates: {str(e)}')
            return ax
        
        # Calculate end dates if not provided
        if end_col is None and duration_col is not None:
            # Calculate end from start + duration
            try:
                data['_end_date'] = data[start_col] + pd.to_timedelta(data[duration_col], unit='D')
                end_col = '_end_date'
            except Exception as e:
                self.showWarning(f'Could not calculate end dates from duration: {str(e)}')
                return ax
        elif end_col is not None:
            try:
                data[end_col] = pd.to_datetime(data[end_col])
            except Exception as e:
                self.showWarning(f'Could not parse end dates: {str(e)}')
                return ax
        else:
            # Default to 1 day duration
            data['_end_date'] = data[start_col] + timedelta(days=1)
            end_col = '_end_date'
        
        # Calculate duration in days
        data['_duration'] = (data[end_col] - data[start_col]).dt.days
        
        # Handle progress
        if progress_col and show_progress:
            try:
                data['_progress'] = pd.to_numeric(data[progress_col], errors='coerce').fillna(0)
                # Ensure progress is between 0 and 100
                data['_progress'] = data['_progress'].clip(0, 100) / 100.0
            except:
                data['_progress'] = 0
        
        # Sort data
        if sort_by and sort_by != 'none':
            if sort_by == 'start_date':
                data = data.sort_values(start_col)
            elif sort_by == 'end_date':
                data = data.sort_values(end_col)
            elif sort_by == 'task_name':
                data = data.sort_values(task_col)
            elif sort_by == 'duration':
                data = data.sort_values('_duration')
        
        # Group by if specified
        if group_by and group_by in data.columns:
            data = data.sort_values([group_by, start_col])
        
        # Create color map
        if status_col:
            unique_statuses = data[status_col].unique()
            cmap = plt.get_cmap(colormap)
            colors = {status: cmap(i / len(unique_statuses)) for i, status in enumerate(unique_statuses)}
        else:
            colors = None
        
        # Plot bars
        y_pos = np.arange(len(data))
        
        for idx, (i, row) in enumerate(data.iterrows()):
            start = row[start_col]
            end = row[end_col]
            duration = row['_duration']
            progress = row['_progress']
            
            # Determine color
            if colors and status_col:
                color = colors[row[status_col]]
            else:
                color = '#4A90E2'  # Default blue
            
            # Plot full bar (background)
            ax.barh(y_pos[idx], duration, left=mdates.date2num(start), 
                   height=bar_height, color=color, alpha=0.3, edgecolor='black', linewidth=0.5)
            
            # Plot progress bar if enabled
            if show_progress and progress > 0:
                progress_duration = duration * progress
                ax.barh(y_pos[idx], progress_duration, left=mdates.date2num(start),
                       height=bar_height, color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # Add today line
        if show_today:
            today = datetime.now()
            ax.axvline(mdates.date2num(today), color='red', linestyle='--', linewidth=2, 
                      label='Today', alpha=0.7)
        
        # Format x-axis as dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        
        # Rotate date labels
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Set y-axis labels
        ax.set_yticks(y_pos)
        ax.set_yticklabels(data[task_col].values)
        
        # Invert y-axis so first task is at top
        ax.invert_yaxis()
        
        # Labels and title
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Tasks', fontsize=12)
        ax.set_title('Gantt Chart', fontsize=14, fontweight='bold')
        
        # Grid
        if grid:
            ax.grid(True, alpha=0.3, axis='x')
        
        # Legend
        if legend and colors and status_col:
            from matplotlib.patches import Patch
            legend_elements = [Patch(facecolor=colors[status], label=status) 
                             for status in unique_statuses]
            if show_today:
                from matplotlib.lines import Line2D
                legend_elements.append(Line2D([0], [0], color='red', linestyle='--', label='Today'))
            ax.legend(handles=legend_elements, loc='best')
        elif legend and show_today:
            ax.legend()
        
        # Tight layout
        plt.tight_layout()
        
        return ax

    def eye(self, df, ax, kwds):
        """Create eye diagram for SerDes signal quality visualization.
        
        An eye diagram shows signal transitions overlaid at the bit period,
        revealing signal integrity issues like jitter, noise, and ISI.
        
        Parameters:
        -----------
        df : pandas.DataFrame
            Data with time and voltage samples
        ax : matplotlib.axes.Axes
            Axes object to plot on
        kwds : dict
            Plotting keywords
            
        Returns:
        --------
        ax : matplotlib.axes.Axes
        """
        print(f"DEBUG: eye() called with {len(df)} rows, {len(df.columns)} columns")
        print(f"DEBUG: Columns: {list(df.columns)}")
        
        # Get options
        persistence = int(kwds.get('persistence', 100))  # Convert to int for histogram
        ui_width = kwds.get('ui_width', 1.0)
        sample_rate = kwds.get('sample_rate', '')
        bit_rate = kwds.get('bit_rate', '')
        show_mask = kwds.get('show_mask', False)
        mask_margin = kwds.get('mask_margin', 0.3)
        color_mode = kwds.get('color_mode', 'density')
        overlay_count = int(kwds.get('overlay_count', 100))  # Convert to int
        colormap = kwds.get('colormap', 'hot')
        grid = kwds.get('grid', True)
        
        # Identify time and voltage columns
        data = df.copy()
        
        # Try to identify time column
        time_col = None
        for col in ['Time', 'time', 'Time_s', 'time_s', 't']:
            if col in data.columns:
                time_col = col
                break
        
        if time_col is None and len(data.columns) > 0:
            time_col = data.columns[0]
        
        # Try to identify voltage column
        voltage_col = None
        for col in ['Voltage', 'voltage', 'V', 'v', 'Signal', 'signal', 'Amplitude', 'amplitude']:
            if col in data.columns:
                voltage_col = col
                break
        
        if voltage_col is None and len(data.columns) > 1:
            voltage_col = data.columns[1]
        
        # Validate columns
        if time_col is None or voltage_col is None:
            self.showWarning('Eye diagram requires Time and Voltage columns')
            return ax
        
        # Get time and voltage data
        try:
            time = pd.to_numeric(data[time_col], errors='coerce').dropna().values
            voltage = pd.to_numeric(data[voltage_col], errors='coerce').dropna().values
            
            # Ensure same length
            min_len = min(len(time), len(voltage))
            time = time[:min_len]
            voltage = voltage[:min_len]
            
        except Exception as e:
            self.showWarning(f'Could not parse time/voltage data: {str(e)}')
            return ax
        
        # Calculate UI (Unit Interval) period
        if bit_rate:
            try:
                bit_rate_val = float(bit_rate)
                ui_period = 1.0 / bit_rate_val  # in nanoseconds if bit_rate in Gbps
            except:
                self.showWarning('Invalid bit rate value')
                return ax
        elif sample_rate:
            try:
                sample_rate_val = float(sample_rate)
                # Estimate UI from data
                time_span = time[-1] - time[0]
                num_samples = len(time)
                sample_period = time_span / num_samples
                # Assume at least 10 samples per UI
                ui_period = sample_period * 10
            except:
                self.showWarning('Invalid sample rate value')
                return ax
        else:
            # Auto-detect UI from data
            time_span = time[-1] - time[0]
            # Assume data spans multiple UIs, estimate from total span
            estimated_uis = max(10, int(time_span / (time[1] - time[0]) / 10))
            ui_period = time_span / estimated_uis
        
        # Apply UI width scaling
        ui_period *= ui_width
        
        # Normalize time to UI periods
        time_normalized = (time - time[0]) % ui_period
        
        # Create eye diagram based on color mode
        if color_mode == 'density':
            # 2D histogram for density plot
            try:
                h, xedges, yedges = np.histogram2d(time_normalized, voltage, bins=persistence)
                h = h.T  # Transpose for correct orientation
                
                # Plot as image
                extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
                im = ax.imshow(h, extent=extent, origin='lower', aspect='auto',
                              cmap=colormap, interpolation='bilinear')
                
                # Add colorbar
                plt.colorbar(im, ax=ax, label='Sample Density')
                
            except Exception as e:
                self.showWarning(f'Error creating density plot: {str(e)}')
                return ax
                
        elif color_mode == 'overlay':
            # Overlay multiple traces
            # Split data into segments of one UI each
            num_uis = int((time[-1] - time[0]) / ui_period)
            samples_per_ui = len(time) // num_uis
            
            # Limit number of overlays
            step = max(1, num_uis // overlay_count)
            
            for i in range(0, num_uis, step):
                start_idx = i * samples_per_ui
                end_idx = min((i + 1) * samples_per_ui, len(time))
                
                if end_idx > start_idx:
                    t_segment = time_normalized[start_idx:end_idx]
                    v_segment = voltage[start_idx:end_idx]
                    ax.plot(t_segment, v_segment, color='blue', alpha=0.1, linewidth=0.5)
        
        else:  # single
            # Plot all points as scatter
            ax.scatter(time_normalized, voltage, s=1, alpha=0.5, c='blue')
        
        # Add eye mask if requested
        if show_mask:
            v_min, v_max = voltage.min(), voltage.max()
            v_range = v_max - v_min
            v_mid = (v_max + v_min) / 2
            
            # Standard eye mask (hexagonal shape)
            mask_x = [0, ui_period * 0.2, ui_period * 0.5, ui_period * 0.8, ui_period, ui_period]
            mask_y_top = [v_mid + v_range * mask_margin] * 6
            mask_y_bot = [v_mid - v_range * mask_margin] * 6
            
            ax.fill_between(mask_x, mask_y_bot, mask_y_top, color='red', alpha=0.3, label='Mask')
        
        # Labels and formatting
        ax.set_xlabel('Time (UI)', fontsize=12)
        ax.set_ylabel('Voltage', fontsize=12)
        ax.set_title('Eye Diagram', fontsize=14, fontweight='bold')
        
        # Set x-axis limits to one UI
        ax.set_xlim(0, ui_period)
        
        # Grid
        if grid:
            ax.grid(True, alpha=0.3)
        
        # Add UI markers
        ax.axvline(ui_period / 2, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='UI Center')
        
        # Legend
        if show_mask:
            ax.legend(loc='upper right')
        
        plt.tight_layout()
        
        return ax

    def jitter(self, df, ax, kwds):
        """Create jitter histogram for timing analysis.
        
        A jitter histogram shows the distribution of timing errors,
        separating random jitter (RJ) and deterministic jitter (DJ).
        
        Parameters:
        -----------
        df : pandas.DataFrame
            Data with jitter measurements
        ax : matplotlib.axes.Axes
            Axes object to plot on
        kwds : dict
            Plotting keywords
            
        Returns:
        --------
        ax : matplotlib.axes.Axes
        """
        from scipy import stats
        from scipy.optimize import curve_fit
        
        print(f"DEBUG: jitter() called with {len(df)} rows, {len(df.columns)} columns")
        print(f"DEBUG: Columns: {list(df.columns)}")
        
        # Get options
        bins = int(kwds.get('bins', 100))  # Convert to int for histogram
        show_stats = kwds.get('show_stats', True)
        show_gaussian = kwds.get('show_gaussian', True)
        show_dual_dirac = kwds.get('show_dual_dirac', False)
        tj_separation = kwds.get('tj_separation', '')
        show_components = kwds.get('show_components', False)
        colormap = kwds.get('colormap', 'viridis')
        grid = kwds.get('grid', True)
        legend = kwds.get('legend', True)
        
        # Identify jitter column
        data = df.copy()
        
        # Try to identify jitter column
        jitter_col = None
        for col in ['Jitter', 'jitter', 'TJ', 'tj', 'Timing_Error', 'timing_error', 'Error', 'error']:
            if col in data.columns:
                jitter_col = col
                break
        
        if jitter_col is None and len(data.columns) > 0:
            jitter_col = data.columns[0]
        
        # Get jitter data
        try:
            jitter_data = pd.to_numeric(data[jitter_col], errors='coerce').dropna().values
        except Exception as e:
            self.showWarning(f'Could not parse jitter data: {str(e)}')
            return ax
        
        if len(jitter_data) == 0:
            self.showWarning('No valid jitter data found')
            return ax
        
        # Create histogram
        counts, bin_edges, patches = ax.hist(jitter_data, bins=bins, density=True, 
                                             alpha=0.7, color='steelblue', edgecolor='black', 
                                             linewidth=0.5, label='Jitter Data')
        
        # Calculate statistics
        mean_jitter = np.mean(jitter_data)
        std_jitter = np.std(jitter_data)
        rms_jitter = np.sqrt(np.mean(jitter_data**2))
        
        # Fit Gaussian if requested
        if show_gaussian:
            # Gaussian function
            def gaussian(x, amp, mean, std):
                return amp * np.exp(-((x - mean)**2) / (2 * std**2))
            
            # Fit
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            try:
                popt, _ = curve_fit(gaussian, bin_centers, counts, 
                                   p0=[counts.max(), mean_jitter, std_jitter])
                
                # Plot fitted Gaussian
                x_fit = np.linspace(jitter_data.min(), jitter_data.max(), 200)
                y_fit = gaussian(x_fit, *popt)
                ax.plot(x_fit, y_fit, 'r-', linewidth=2, label=f'Gaussian Fit (σ={popt[2]:.3f})')
                
            except Exception as e:
                print(f"Gaussian fit failed: {e}")
        
        # Dual-Dirac model for DJ separation
        dual_dirac_params = None
        if show_dual_dirac and tj_separation:
            try:
                tj_sep = float(tj_separation)

                # Dual-Dirac function: two Gaussians separated by DJ
                def dual_dirac(x, amp1, amp2, mean, rj_std, dj):
                    g1 = amp1 * np.exp(-((x - (mean - dj / 2))**2) / (2 * rj_std**2))
                    g2 = amp2 * np.exp(-((x - (mean + dj / 2))**2) / (2 * rj_std**2))
                    return g1 + g2

                # Fit
                bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                popt, _ = curve_fit(
                    dual_dirac,
                    bin_centers,
                    counts,
                    p0=[counts.max() / 2, counts.max() / 2, mean_jitter, std_jitter / 2, tj_sep],
                )

                # Plot fitted dual-Dirac
                x_fit = np.linspace(jitter_data.min(), jitter_data.max(), 200)
                y_fit = dual_dirac(x_fit, *popt)
                ax.plot(
                    x_fit,
                    y_fit,
                    'g--',
                    linewidth=2,
                    label=f'Dual-Dirac (RJ={popt[3]:.3f}, DJ={popt[4]:.3f})',
                )

                # Show components if requested
                if show_components:
                    rj_component = popt[0] * np.exp(-((x_fit - popt[2])**2) / (2 * popt[3]**2))
                    ax.plot(
                        x_fit,
                        rj_component,
                        'b:',
                        linewidth=1.5,
                        label='RJ Component',
                        alpha=0.7,
                    )

                dual_dirac_params = popt

            except Exception as e:
                print(f"Dual-Dirac fit failed: {e}")

        # Add statistics text box
        if show_stats:
            stats_lines = [
                f'Mean: {mean_jitter:.3f}',
                f'Std Dev: {std_jitter:.3f}',
                f'RMS: {rms_jitter:.3f}',
            ]
            if dual_dirac_params is not None:
                stats_lines.append(f'RJ σ: {dual_dirac_params[3]:.3f}')
                stats_lines.append(f'DJ: {dual_dirac_params[4]:.3f}')

            stats_text = "\n".join(stats_lines)
            ax.text(
                0.02,
                0.98,
                stats_text,
                transform=ax.transAxes,
                fontsize=10,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.6),
            )
        # Grid
        if grid:
            ax.grid(True, alpha=0.3, axis='y')
        
        # Legend
        if legend:
            ax.legend(loc='upper right')
        
        plt.tight_layout()
        
        return ax

    def phasenoise(self, df, ax, kwds):
        """Convert phase noise to RMS jitter and plot results.
        
        This method takes phase noise data (offset frequency vs phase noise in dBc/Hz)
        and calculates the RMS jitter by integrating the phase noise over a specified
        frequency range. It displays both the phase noise curve and cumulative jitter.
        
        Parameters:
        -----------
        df : pandas.DataFrame
            Data with two columns:
            - First column: Offset frequency (Hz)
            - Second column: Phase noise (dBc/Hz)
        ax : matplotlib.axes.Axes
            Axes object to plot on
        kwds : dict
            Plotting keywords including:
            - carrier_freq: Carrier frequency in Hz (default: 156e6)
            - freq_min: Minimum frequency for integration (Hz)
            - freq_max: Maximum frequency for integration (Hz)
            - show_stats: Show statistics text box
            - grid: Show grid
            - legend: Show legend
            - linewidth: Line width
            - alpha: Transparency
            
        Returns:
        --------
        ax : matplotlib.axes.Axes
        
        CSV file format:
            Column 1: Offset frequency (Hz)
            Column 2: Phase noise (dBc/Hz)
        """
        # Compatibility for numpy < 2.0 (trapz) and >= 2.0 (trapezoid)
        trapz = getattr(np, 'trapezoid', np.trapz)
        
        print(f"DEBUG: phasenoise() called with {len(df)} rows, {len(df.columns)} columns")
        print(f"DEBUG: Columns: {list(df.columns)}")
        
        # Get options
        carrier_freq_str = kwds.get('carrier_freq', '156e6')
        freq_min_str = kwds.get('freq_min', '')
        freq_max_str = kwds.get('freq_max', '')
        show_stats = kwds.get('show_stats', True)
        grid = kwds.get('grid', True)
        legend = kwds.get('legend', True)
        linewidth = kwds.get('linewidth', 2)
        alpha = kwds.get('alpha', 0.9)
        
        # Parse carrier frequency
        try:
            f_carrier = float(carrier_freq_str) if carrier_freq_str else 156e6
        except ValueError:
            f_carrier = 156e6
            print(f"Warning: Invalid carrier frequency '{carrier_freq_str}', using default 156 MHz")
        
        # Parse frequency limits
        freq_min = None
        freq_max = None
        try:
            if freq_min_str:
                freq_min = float(freq_min_str)
        except ValueError:
            print(f"Warning: Invalid freq_min '{freq_min_str}', ignoring")
        try:
            if freq_max_str:
                freq_max = float(freq_max_str)
        except ValueError:
            print(f"Warning: Invalid freq_max '{freq_max_str}', ignoring")
        
        # Get data from dataframe
        data = df.copy()
        
        if len(data.columns) < 2:
            self.showWarning('Phase noise plot requires at least 2 columns:\n'
                           'Column 1: Offset frequency (Hz)\n'
                           'Column 2: Phase noise (dBc/Hz)')
            return ax
        
        # Get the first two columns regardless of header names
        try:
            offset_freq = pd.to_numeric(data.iloc[:, 0], errors='coerce').values.astype(float)
            phase_noise_dbc = pd.to_numeric(data.iloc[:, 1], errors='coerce').values.astype(float)
        except Exception as e:
            self.showWarning(f'Could not parse phase noise data: {str(e)}')
            return ax
        
        # Remove NaN values
        valid_mask = ~(np.isnan(offset_freq) | np.isnan(phase_noise_dbc))
        offset_freq = offset_freq[valid_mask]
        phase_noise_dbc = phase_noise_dbc[valid_mask]
        
        if len(offset_freq) == 0:
            self.showWarning('No valid phase noise data found')
            return ax
        
        # Sort by frequency
        sort_idx = np.argsort(offset_freq)
        offset_freq = offset_freq[sort_idx]
        phase_noise_dbc = phase_noise_dbc[sort_idx]
        
        # Filter to user-defined frequency range
        mask = np.ones(len(offset_freq), dtype=bool)
        if freq_min is not None:
            mask &= offset_freq >= freq_min
        if freq_max is not None:
            mask &= offset_freq <= freq_max
        
        offset_freq_filtered = offset_freq[mask]
        phase_noise_dbc_filtered = phase_noise_dbc[mask]
        
        if len(offset_freq_filtered) < 2:
            self.showWarning('Not enough data points in frequency range for integration')
            return ax
        
        # Convert phase noise to linear scale
        phase_noise_linear = 10 ** (phase_noise_dbc_filtered / 10)
        
        # Calculate cumulative jitter at each frequency point
        cumulative_jitter = np.zeros(len(offset_freq_filtered))
        for i in range(1, len(offset_freq_filtered)):
            # Integrate phase noise up to this frequency point
            sigma_phi_sq = 2 * trapz(phase_noise_linear[:i+1], offset_freq_filtered[:i+1])
            sigma_phi = np.sqrt(sigma_phi_sq)
            cumulative_jitter[i] = sigma_phi / (2 * np.pi * f_carrier)
        
        # Total RMS phase and jitter
        sigma_phi_sq_total = 2 * trapz(phase_noise_linear, offset_freq_filtered)
        sigma_phi = np.sqrt(sigma_phi_sq_total)
        sigma_t = sigma_phi / (2 * np.pi * f_carrier)
        
        # Create two subplots
        fig = ax.get_figure()
        fig.clear()
        ax1, ax2 = fig.subplots(2, 1, sharex=True)
        
        # Plot phase noise
        ax1.semilogx(offset_freq_filtered, phase_noise_dbc_filtered, 'b-o', 
                    linewidth=linewidth, markersize=4, alpha=alpha)
        ax1.set_ylabel('Phase Noise (dBc/Hz)', fontsize=12)
        ax1.set_title('Phase Noise vs Offset Frequency', fontsize=14)
        if grid:
            ax1.grid(True, which='both', linestyle='--', alpha=0.7)
        ax1.set_xlim(offset_freq_filtered[0] * 0.5, offset_freq_filtered[-1] * 2)
        
        # Shade integration range if specified
        if freq_min is not None or freq_max is not None:
            x_min = freq_min if freq_min is not None else offset_freq_filtered[0]
            x_max = freq_max if freq_max is not None else offset_freq_filtered[-1]
            ax1.axvspan(x_min, x_max, alpha=0.2, color='green', 
                       label=f'Integration: {x_min:.0e} - {x_max:.0e} Hz')
            if legend:
                ax1.legend(loc='upper right')
        
        # Plot cumulative jitter
        cumulative_jitter_ps = cumulative_jitter * 1e12  # Convert to picoseconds
        ax2.semilogx(offset_freq_filtered, cumulative_jitter_ps, 'r-o', 
                    linewidth=linewidth, markersize=4, alpha=alpha)
        ax2.set_xlabel('Offset Frequency (Hz)', fontsize=12)
        ax2.set_ylabel('Cumulative RMS Jitter (ps)', fontsize=12)
        ax2.set_title(f'Cumulative RMS Jitter (Total: {sigma_t*1e12:.3f} ps)', fontsize=14)
        if grid:
            ax2.grid(True, which='both', linestyle='--', alpha=0.7)
        
        # Add statistics text box
        if show_stats:
            stats_lines = [
                f'Carrier: {f_carrier/1e6:.3f} MHz',
                f'Freq Range: {offset_freq_filtered[0]:.2e} - {offset_freq_filtered[-1]:.2e} Hz',
                f'RMS Phase: {sigma_phi:.6e} rad',
                f'RMS Phase: {np.degrees(sigma_phi):.4f} deg',
                f'RMS Jitter: {sigma_t*1e12:.3f} ps',
            ]
            stats_text = '\n'.join(stats_lines)
            ax1.text(0.02, 0.02, stats_text,
                    transform=ax1.transAxes,
                    fontsize=9,
                    verticalalignment='bottom',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        fig.tight_layout()
        
        # Print results to console
        print(f"\n{'='*50}")
        print("PHASE NOISE TO JITTER RESULTS")
        print(f"{'='*50}")
        print(f"Carrier frequency: {f_carrier/1e6:.3f} MHz")
        print(f"Frequency range: {offset_freq_filtered[0]:.2e} Hz to {offset_freq_filtered[-1]:.2e} Hz")
        print(f"Data points: {len(offset_freq_filtered)}")
        print(f"RMS Phase:  {sigma_phi:.6e} rad ({np.degrees(sigma_phi):.4f} deg)")
        print(f"RMS Jitter: {sigma_t:.6e} s ({sigma_t*1e12:.3f} ps)")
        print(f"{'='*50}")
        
        return ax2

    def density(self, df, ax, kwds):
        """Create kernel density estimation plot.
        
        This method creates smooth density curves for numeric data using
        kernel density estimation (KDE). Supports multiple columns with
        overlaid densities.
        
        Parameters:
        -----------
        df : pandas.DataFrame
            Data to plot. All numeric columns will be used.
        ax : matplotlib.axes.Axes
            Axes object to plot on
        kwds : dict
            Plotting keywords including:
            - bw_method: str or float, bandwidth method ('scott', 'silverman', or numeric)
            - fill: bool, whether to fill under the curve
            - show_rug: bool, whether to show rug plot
            - alpha: float, transparency (0-1)
            - colormap: str, colormap name
            - linewidth: float, line width
            - grid: bool, show grid
            - legend: bool, show legend
            - subplots: bool, create separate subplots
            
        Returns:
        --------
        ax or list of axes
        """
        
        # Get parameters
        bw_method = kwds.get('bw_method', 'scott')
        fill = kwds.get('fill', False)
        show_rug = kwds.get('show_rug', False)
        alpha = kwds.get('alpha', 0.7)
        cmap = plt.cm.get_cmap(kwds.get('colormap', 'tab10'))
        lw = kwds.get('linewidth', 1.5)
        grid = kwds.get('grid', True)
        legend = kwds.get('legend', True)
        subplots = kwds.get('subplots', False)
        
        # Get numeric data only
        data = df._get_numeric_data()
        
        if len(data.columns) == 0:
            self.showWarning('No numeric data to plot')
            return ax
        
        # Check if scipy is available for KDE
        try:
            from scipy import stats
            use_scipy = True
        except ImportError:
            use_scipy = False
            # Fall back to pandas built-in density plot
            if not subplots:
                for i, col in enumerate(data.columns):
                    color = cmap(float(i) / len(data.columns))
                    data[col].plot.density(ax=ax, color=color, linewidth=lw, 
                                          alpha=alpha, label=col)
                if legend:
                    ax.legend()
                if grid:
                    ax.grid(True, alpha=0.3)
                ax.set_ylabel('Density')
                return ax
        
        # Create subplots if requested
        if subplots:
            n_cols = len(data.columns)
            n_rows = int(np.ceil(np.sqrt(n_cols)))
            n_cols_grid = int(np.ceil(n_cols / n_rows))
            
            fig = ax.get_figure()
            fig.clear()
            axes = []
            
            for i, col in enumerate(data.columns):
                ax_sub = fig.add_subplot(n_rows, n_cols_grid, i + 1)
                axes.append(ax_sub)
                
                # Get data for this column, remove NaN
                col_data = data[col].dropna()
                
                if len(col_data) < 2:
                    ax_sub.text(0.5, 0.5, 'Insufficient data', 
                               ha='center', va='center', transform=ax_sub.transAxes)
                    ax_sub.set_title(col)
                    continue
                
                # Compute KDE
                if use_scipy:
                    try:
                        kde = stats.gaussian_kde(col_data, bw_method=bw_method)
                        x_range = np.linspace(col_data.min(), col_data.max(), 200)
                        density_vals = kde(x_range)
                        
                        # Plot
                        color = cmap(float(i) / n_cols)
                        ax_sub.plot(x_range, density_vals, color=color, linewidth=lw, alpha=alpha)
                        
                        if fill:
                            ax_sub.fill_between(x_range, density_vals, alpha=alpha*0.5, color=color)
                        
                        if show_rug:
                            # Add rug plot at bottom
                            y_min = ax_sub.get_ylim()[0]
                            ax_sub.plot(col_data, [y_min] * len(col_data), '|', 
                                       color=color, alpha=0.5, markersize=10)
                        
                    except Exception as e:
                        ax_sub.text(0.5, 0.5, f'Error: {str(e)}', 
                                   ha='center', va='center', transform=ax_sub.transAxes)
                
                ax_sub.set_title(col)
                ax_sub.set_ylabel('Density')
                if grid:
                    ax_sub.grid(True, alpha=0.3)
            
            # Remove empty subplots
            for i in range(len(data.columns), len(axes)):
                fig.delaxes(axes[i])
            
            plt.tight_layout()
            return axes
        
        else:
            # Single plot with multiple densities
            for i, col in enumerate(data.columns):
                # Get data for this column, remove NaN
                col_data = data[col].dropna()
                
                if len(col_data) < 2:
                    continue
                
                color = cmap(float(i) / len(data.columns))
                
                if use_scipy:
                    try:
                        # Compute KDE
                        kde = stats.gaussian_kde(col_data, bw_method=bw_method)
                        x_range = np.linspace(col_data.min(), col_data.max(), 200)
                        density_vals = kde(x_range)
                        
                        # Plot
                        ax.plot(x_range, density_vals, color=color, linewidth=lw, 
                               alpha=alpha, label=col)
                        
                        if fill:
                            ax.fill_between(x_range, density_vals, alpha=alpha*0.3, color=color)
                        
                        if show_rug:
                            # Add rug plot at bottom
                            y_min = ax.get_ylim()[0]
                            ax.plot(col_data, [y_min] * len(col_data), '|', 
                                   color=color, alpha=0.3, markersize=8)
                    
                    except Exception as e:
                        print(f"Error plotting density for {col}: {e}")
                        continue
            
            if legend and len(data.columns) > 1:
                ax.legend()
            
            ax.set_ylabel('Density')
            ax.set_xlabel('Value')
            
            if grid:
                ax.grid(True, alpha=0.3)
            
            return ax

    def shmoo(self, df, ax, kwds):
        """Create 2D shmoo plot for parameter sweep visualization.
        
        A shmoo plot visualizes the results of a 2D parameter sweep, typically
        showing pass/fail regions or measurement values across a grid of test conditions.
        Common in semiconductor testing, hardware validation, and system characterization.
        
        Parameters:
        -----------
        df : pandas.DataFrame
            Data to plot. Must contain at least 3 columns for X, Y, and Z values.
        ax : matplotlib.axes.Axes
            Axes object to plot on
        kwds : dict
            Plotting keywords
            
        Returns:
        --------
        ax : matplotlib.axes.Axes
        """
        
        print(f"DEBUG: shmoo() called with {len(df)} rows, {len(df.columns)} columns")
        print(f"DEBUG: Columns: {list(df.columns)}")
        print(f"DEBUG: kwds keys: {list(kwds.keys())}")
        
        # Get parameters
        x_param = kwds.get('x_param', None)
        y_param = kwds.get('y_param', None)
        z_param = kwds.get('z_param', None)
        
        print(f"DEBUG: x_param={x_param}, y_param={y_param}, z_param={z_param}")
        threshold_min = kwds.get('threshold_min', None)
        threshold_max = kwds.get('threshold_max', None)
        cmap_name = kwds.get('colormap', 'RdYlGn')
        show_contours = kwds.get('show_contours', False)
        contour_levels = kwds.get('contour_levels', 10)
        interpolation = kwds.get('interpolation', 'nearest')
        show_stats = kwds.get('show_stats', False)
        grid = kwds.get('grid', True)
        show_colorbar = kwds.get('colorbar', True)
        marker_size = kwds.get('marker_size', 50)
        show_markers = kwds.get('show_markers', False)
        show_values = kwds.get('show_values', False)
        log_z_scale = kwds.get('log_z_scale', False)
        
        # Convert threshold strings to floats if needed
        if threshold_min is not None and threshold_min != '':
            try:
                threshold_min = float(threshold_min)
            except (ValueError, TypeError):
                threshold_min = None
        else:
            threshold_min = None
            
        if threshold_max is not None and threshold_max != '':
            try:
                threshold_max = float(threshold_max)
            except (ValueError, TypeError):
                threshold_max = None
        else:
            threshold_max = None
        
        # Get numeric data only
        data = df._get_numeric_data()
        
        if len(data.columns) < 3:
            self.showWarning('Shmoo plot requires at least 3 numeric columns (X, Y, Z)')
            return ax
        
        # Auto-select columns if not specified
        if x_param is None or x_param == '' or x_param not in data.columns:
            x_param = data.columns[0]
        if y_param is None or y_param == '' or y_param not in data.columns:
            y_param = data.columns[1]
        if z_param is None or z_param == '' or z_param not in data.columns:
            z_param = data.columns[2]
        
        # Extract data
        x_data = data[x_param].values
        y_data = data[y_param].values
        z_data = data[z_param].values
        
        # Remove NaN values
        mask = ~(np.isnan(x_data) | np.isnan(y_data) | np.isnan(z_data))
        x_data = x_data[mask]
        y_data = y_data[mask]
        z_data = z_data[mask]
        raw_z_values = z_data.copy()

        if len(x_data) == 0:
            self.showWarning('No valid data points after removing NaN values')
            return ax

        colorbar_label = z_param

        if log_z_scale:
            positive_values = z_data[z_data > 0]
            if positive_values.size > 0:
                min_positive = positive_values.min()
            else:
                non_zero = np.abs(z_data[z_data != 0])
                if non_zero.size > 0:
                    min_positive = non_zero.min()
                else:
                    min_positive = 1.0
            min_positive = max(min_positive, np.finfo(float).tiny)
            safe_floor = min_positive / 10.0

            adjusted_z = np.where(z_data <= 0, safe_floor, z_data)
            z_data = np.log10(adjusted_z)

            def _log_threshold(val):
                if val is None:
                    return None
                safe_val = max(val, safe_floor)
                return np.log10(safe_val)

            threshold_min = _log_threshold(threshold_min)
            threshold_max = _log_threshold(threshold_max)
            colorbar_label = f'log10({z_param})'
        
        hover_labels = {'x': x_param, 'y': y_param, 'z': z_param}
        hover_scale = 'log' if log_z_scale else 'linear'
        tooltip_values_enabled = bool(show_values)

        def _tooltip_payload(payload):
            if tooltip_values_enabled:
                return payload
            stripped = payload.copy()
            stripped['z_linear'] = None
            stripped['z_display'] = None
            return stripped

        def _build_boundary_norm(z_arr, tmin, tmax, cmap_name):
            import numpy as np
            from matplotlib import colors as mcolors
            zmin = np.nanmin(z_arr)
            zmax = np.nanmax(z_arr)
            if not np.isfinite(zmin) or not np.isfinite(zmax) or zmin == zmax:
                return None, plt.cm.get_cmap(cmap_name)
            if tmin is None or tmax is None:
                return None, plt.cm.get_cmap(cmap_name)
            tmin = np.clip(tmin, zmin, zmax)
            tmax = np.clip(tmax, zmin, zmax)
            if tmin > tmax:
                tmin, tmax = tmax, tmin
            boundaries = np.array([zmin, tmin, tmax, zmax], dtype=float)
            eps = np.finfo(float).eps
            for i in range(1, len(boundaries)):
                if boundaries[i] <= boundaries[i-1]:
                    boundaries[i] = boundaries[i-1] + eps
            norm = mcolors.BoundaryNorm(boundaries, ncolors=256)
            return norm, plt.cm.get_cmap(cmap_name)

        # Check if data is on a regular grid
        x_unique = np.unique(x_data)
        y_unique = np.unique(y_data)
        
        is_regular_grid = (len(x_data) == len(x_unique) * len(y_unique))
        
        if is_regular_grid:
            # Data is on a regular grid - reshape for pcolormesh
            try:
                # Create meshgrid
                X, Y = np.meshgrid(x_unique, y_unique)
                
                # Reshape Z data to match grid
                Z = np.full((len(y_unique), len(x_unique)), np.nan, dtype=float)
                Z_linear = np.full_like(Z, np.nan, dtype=float)
                x_index = {value: idx for idx, value in enumerate(x_unique)}
                y_index = {value: idx for idx, value in enumerate(y_unique)}
                for x, y, z_val, z_raw in zip(x_data, y_data, z_data, raw_z_values):
                    xi = x_index.get(x)
                    yi = y_index.get(y)
                    if xi is None or yi is None:
                        continue
                    Z[yi, xi] = z_val
                    Z_linear[yi, xi] = z_raw

                # Create the plot using pcolormesh for regular grids
                if threshold_min is not None and threshold_max is not None:
                    norm, cmap = _build_boundary_norm(z_data, threshold_min, threshold_max, cmap_name)
                else:
                    norm = None
                    cmap = plt.cm.get_cmap(cmap_name)
                
                mesh = ax.pcolormesh(X, Y, Z, cmap=cmap, norm=norm, shading='auto')

                if show_colorbar:
                    self.fig.colorbar(mesh, ax=ax, label=colorbar_label)

                self._register_hover_target(
                    mesh,
                    _tooltip_payload(
                        {
                            'type': 'mesh',
                            'x_values': X.flatten(),
                            'y_values': Y.flatten(),
                            'z_linear': Z_linear.flatten(),
                            'z_display': Z.flatten(),
                            'labels': hover_labels,
                            'scale': hover_scale
                        }
                    )
                )

                # Add contour lines if requested
                if show_contours:
                    try:
                        contour_levels_int = int(contour_levels)
                        contours = ax.contour(X, Y, Z, levels=contour_levels_int, colors='black', 
                                             linewidths=0.5, alpha=0.5)
                        ax.clabel(contours, inline=True, fontsize=8)
                    except:
                        pass
                
            except Exception as e:
                self.showWarning(f'Error creating regular grid plot: {str(e)}')
                return ax
        
        else:
            # Irregular grid - use scatter plot or interpolation
            try:
                if interpolation != 'none':
                    from scipy.interpolate import griddata
                    
                    # Create regular grid for interpolation
                    xi = np.linspace(x_data.min(), x_data.max(), 100)
                    yi = np.linspace(y_data.min(), y_data.max(), 100)
                    Xi, Yi = np.meshgrid(xi, yi)
                    
                    # Interpolate Z values
                    method = 'cubic' if interpolation == 'cubic' else 'linear'
                    Zi = griddata((x_data, y_data), z_data, (Xi, Yi), method=method)
                    if log_z_scale:
                        Zi_linear = griddata((x_data, y_data), raw_z_values, (Xi, Yi), method=method)
                    else:
                        Zi_linear = Zi.copy() if Zi is not None else None

                    if threshold_min is not None and threshold_max is not None:
                        norm, cmap = _build_boundary_norm(z_data, threshold_min, threshold_max, cmap_name)
                    else:
                        norm = None
                        cmap = plt.cm.get_cmap(cmap_name)
                    
                    mesh = ax.pcolormesh(Xi, Yi, Zi, cmap=cmap, norm=norm, shading='auto')

                    if show_colorbar:
                        self.fig.colorbar(mesh, ax=ax, label=z_param)

                    self._register_hover_target(
                        mesh,
                        _tooltip_payload(
                            {
                                'type': 'mesh',
                                'x_values': Xi.flatten(),
                                'y_values': Yi.flatten(),
                                'z_linear': Zi_linear.flatten() if Zi_linear is not None else None,
                                'z_display': Zi.flatten(),
                                'labels': hover_labels,
                                'scale': hover_scale
                            }
                        )
                    )

                    if show_contours:
                        try:
                            contour_levels_int = int(contour_levels)
                            contours = ax.contour(Xi, Yi, Zi, levels=contour_levels_int, colors='black',
                                                 linewidths=0.5, alpha=0.5)
                            ax.clabel(contours, inline=True, fontsize=8)
                        except:
                            pass
                    
                    # Optionally show original data points
                    if show_markers:
                        markers = ax.scatter(x_data, y_data, c='black', s=10, marker='o', alpha=0.5)
                        self._register_hover_target(
                            markers,
                            _tooltip_payload(
                                {
                                    'type': 'scatter',
                                    'x_values': x_data,
                                    'y_values': y_data,
                                    'z_linear': raw_z_values,
                                    'z_display': z_data,
                                    'labels': hover_labels,
                                    'scale': hover_scale
                                }
                            )
                        )
                else:
                    # Just use scatter plot
                    if threshold_min is not None and threshold_max is not None:
                        colors_array = np.where((z_data >= threshold_min) & (z_data <= threshold_max),
                                              'green', 'red')
                        scatter = ax.scatter(x_data, y_data, c=colors_array, s=marker_size,
                                           edgecolors='black', linewidth=0.5)
                    else:
                        scatter = ax.scatter(x_data, y_data, c=z_data, cmap=cmap_name,
                                           s=marker_size, edgecolors='black', linewidth=0.5)
                        if show_colorbar:
                            self.fig.colorbar(scatter, ax=ax, label=colorbar_label)

                    self._register_hover_target(
                        scatter,
                        _tooltip_payload(
                            {
                                'type': 'scatter',
                                'x_values': x_data,
                                'y_values': y_data,
                                'z_linear': raw_z_values,
                                'z_display': z_data,
                                'labels': hover_labels,
                                'scale': hover_scale
                            }
                        )
                    )

            except ImportError:
                # Scipy not available, fall back to scatter plot
                if threshold_min is not None and threshold_max is not None:
                    colors_array = np.where((z_data >= threshold_min) & (z_data <= threshold_max),
                                          'green', 'red')
                    scatter = ax.scatter(x_data, y_data, c=colors_array, s=marker_size,
                                       edgecolors='black', linewidth=0.5)
                else:
                    scatter = ax.scatter(x_data, y_data, c=z_data, cmap=cmap_name,
                                       s=marker_size, edgecolors='black', linewidth=0.5)
                    if show_colorbar:
                        self.fig.colorbar(scatter, ax=ax, label=colorbar_label)

                self._register_hover_target(
                    scatter,
                    _tooltip_payload(
                        {
                            'type': 'scatter',
                            'x_values': x_data,
                            'y_values': y_data,
                            'z_linear': raw_z_values,
                            'z_display': z_data,
                            'labels': hover_labels,
                            'scale': hover_scale
                        }
                    )
                )

            except Exception as e:
                self.showWarning(f'Error creating irregular grid plot: {str(e)}')
                return ax
        
        # Set labels
        ax.set_xlabel(x_param, fontsize=12, fontweight='bold')
        ax.set_ylabel(y_param, fontsize=12, fontweight='bold')
        ax.set_title(f'Shmoo Plot: {colorbar_label}', fontsize=14, pad=15)
        
        # Add grid
        if grid:
            ax.grid(True, alpha=0.3, linestyle='--')
        
        # Add statistics if requested
        if show_stats:
            if threshold_min is not None and threshold_max is not None:
                pass_mask = (z_data >= threshold_min) & (z_data <= threshold_max)
                pass_count = np.sum(pass_mask)
                total_count = len(z_data)
                pass_rate = 100.0 * pass_count / total_count if total_count > 0 else 0
                
                # Calculate margins
                if pass_count > 0:
                    margin_min = np.min(z_data[pass_mask] - threshold_min)
                    margin_max = np.min(threshold_max - z_data[pass_mask])
                else:
                    margin_min = margin_max = 0
                
                stats_text = f'Pass: {pass_count}/{total_count} ({pass_rate:.1f}%)\n'
                stats_text += f'Min Margin: {margin_min:.3f}\n'
                stats_text += f'Max Margin: {margin_max:.3f}'
                
                # Add text box with statistics
                self._render_shmoo_stats_box(ax, stats_text)
            else:
                stats_text = f'Points: {len(z_data)}\n'
                stats_text += f'Min: {z_data.min():.3f}\n'
                stats_text += f'Max: {z_data.max():.3f}\n'
                stats_text += f'Mean: {z_data.mean():.3f}'
                
                self._render_shmoo_stats_box(ax, stats_text)
        
        # Add values if requested
        if show_values:
            value_map = OrderedDict()
            for x, y, raw_val in zip(x_data, y_data, raw_z_values):
                value_map[(x, y)] = raw_val
            for (x, y), raw_val in value_map.items():
                label = f'{raw_val:.3g}'
                text = ax.text(
                    x,
                    y,
                    label,
                    ha='center',
                    va='center',
                    fontsize=9,
                    color='black',
                    path_effects=[patheffects.withStroke(linewidth=2, foreground='white')]
                )
                text.set_zorder(1000)

        return ax

    def contourData(self, data):
        """
        Prepare data for contour plotting (interpolates to a grid).

        Args:
            data (pd.DataFrame): DataFrame with 3 columns (x, y, z).

        Returns:
            tuple: (xi, yi, zi) arrays.
        """

        #from matplotlib.mlab import griddata
        from scipy.interpolate import griddata
        x = data.values[:,0]
        y = data.values[:,1]
        z = data.values[:,2]
        xi = np.linspace(x.min(), x.max())
        yi = np.linspace(y.min(), y.max())
        zi = griddata((x, y), z, (xi[None,:], yi[:,None]), method='cubic')
        return xi,yi,zi

    def meshData(self, x,y,z):
        """
        Prepare 1D data arrays for 3D surface/wireframe plotting.

        Args:
            x, y, z: 1D arrays of coordinates.

        Returns:
            tuple: (X, Y, zi) mesh grids.
        """

        from scipy.interpolate import griddata
        xi = np.linspace(x.min(), x.max())
        yi = np.linspace(y.min(), y.max())
        #zi = griddata(x, y, z, xi, yi, interp='linear')
        zi = griddata((x, y), z, (xi[None,:], yi[:,None]), method='cubic')
        X, Y = np.meshgrid(xi, yi)
        return X,Y,zi

    def getView(self):
        """
        Get current 3D view angles.

        Returns:
            tuple: (azim, elev, dist) or (None, None, None).
        """
        ax = self.ax
        if hasattr(ax, 'azim'):
            azm = ax.azim
            ele = ax.elev
            # ax.dist was removed in matplotlib 3.6+, use default distance
            dst = getattr(ax, 'dist', 10)
        else:
            return None, None, None
        return azm, ele, dst

    def getcmap(self, name):
        """
        Safely get a colormap by name.

        Args:
            name (str): Colormap name.

        Returns:
            Colormap object.
        """
        try:
            return plt.cm.get_cmap(name)
        except:
            return plt.cm.get_cmap('Spectral')

    def _apply_logz(self, z):
        """
        Apply log10 transformation to Z values for 3D plots.
        
        Non-positive values are clamped to min(positive_z)/10 before log transform.
        
        Args:
            z: Array of Z values (can be 1D or 2D).
            
        Returns:
            Array of log10-transformed Z values.
        """
        z = np.asarray(z, dtype=float)
        # Find minimum positive value
        positive_mask = z > 0
        if np.any(positive_mask):
            min_positive = np.min(z[positive_mask])
            clamp_value = min_positive / 10.0
        else:
            # All values are non-positive, use a small default
            clamp_value = 1e-10
        
        # Clamp non-positive values
        z_clamped = np.where(z > 0, z, clamp_value)
        
        # Apply log10
        return np.log10(z_clamped)

    def plot3D(self, redraw=True):
        """
        Generate a 3D plot.

        Args:
            redraw (bool): Whether to draw the canvas.
        """

        if not hasattr(self, 'data') or len(self.data.columns)<3:
            return
        kwds = self.mplopts.kwds.copy()
        #use base options by joining the dicts
        kwds.update(self.mplopts3d.kwds)
        kwds.update(self.labelopts.kwds)
        #print (kwds)
        data = self.data
        x = data.values[:,0]
        y = data.values[:,1]
        z = data.values[:,2].copy()
        
        # Handle log Z option
        logz = kwds.get('logz', False)
        if logz:
            z = self._apply_logz(z)
        
        azm,ele,dst = self.getView()

        #self.fig.clear()
        ax = self.ax# = Axes3D(self.fig)
        kind = kwds['kind']
        mode = kwds['mode']
        rstride = kwds['rstride']
        cstride = kwds['cstride']
        lw = kwds['linewidth']
        alpha = kwds['alpha']
        cmap = kwds['colormap']

        if kind == 'scatter':
            self.scatter3D(data, ax, kwds, logz=logz)
        elif kind == 'bar':
            self.bar3D(data, ax, kwds, logz=logz)
        elif kind == 'contour':
            from scipy.interpolate import griddata
            xi = np.linspace(x.min(), x.max())
            yi = np.linspace(y.min(), y.max())
            # z already has logz applied if enabled, griddata interpolates it
            zi = griddata((x, y), z, (xi[None,:], yi[:,None]), method='cubic')
            #zi = np.meshgrid(x, y, z, xi, yi)
            surf = ax.contour(xi, yi, zi, rstride=rstride, cstride=cstride,
                              cmap=kwds['colormap'], alpha=alpha,
                              linewidth=lw, antialiased=True)
        elif kind == 'wireframe':
            if mode == '(x,y)->z':
                # z already has logz applied if enabled, meshData interpolates it
                X,Y,zi = self.meshData(x,y,z)
            else:
                X,Y,zi = x,y,z
            w = ax.plot_wireframe(X, Y, zi, rstride=rstride, cstride=cstride,
                                  linewidth=lw)
        elif kind == 'surface':
            # z already has logz applied if enabled, meshData interpolates it
            X,Y,zi = self.meshData(x,y,z)
            surf = ax.plot_surface(X, Y, zi, rstride=rstride, cstride=cstride,
                                   cmap=cmap, alpha=alpha,
                                   linewidth=lw)
            cb = self.fig.colorbar(surf, shrink=0.5, aspect=5)
            surf.set_clim(vmin=zi.min(), vmax=zi.max())
        if kwds['points'] == True:
            self.scatter3D(data, ax, kwds, logz=logz)

        self.setFigureOptions(ax, kwds)
        if azm != None:
            self.ax.azim = azm
            self.ax.elev = ele
            # ax.dist was removed in matplotlib 3.6+, only set if attribute exists
            if hasattr(self.ax, 'dist'):
                self.ax.dist = dst
        #handles, labels = self.ax.get_legend_handles_labels()
        #self.fig.legend(handles, labels)
        self.canvas.draw()
        return

    def bar3D(self, data, ax, kwds, logz=False):
        """
        Create a 3D bar plot.

        Args:
            data (pd.DataFrame): Data.
            ax: 3D Axis.
            kwds (dict): Options.
            logz (bool): Apply log10 to Z values.
        """

        i=0
        plots=len(data.columns)
        cmap = plt.cm.get_cmap(kwds['colormap'])
        for c in data.columns:
            h = data[c].values
            if logz:
                h = self._apply_logz(h)
            c = cmap(float(i)/(plots))
            ax.bar(data.index, h, zs=i, zdir='y', color=c)
            i+=1

    def scatter3D(self, data, ax, kwds, logz=False):
        """
        Create a 3D scatter plot.

        Args:
            data (pd.DataFrame): Data.
            ax: 3D Axis.
            kwds (dict): Options.
            logz (bool): Apply log10 to Z values.
        """
        
        parent_self = self  # Reference to parent for _apply_logz

        def doscatter(data, ax, color=None, pointlabels=None):
            data = data._get_numeric_data()
            l = len(data.columns)
            if l<3: return

            X = data.values
            x = X[:,0]
            y = X[:,1]
            handles=[]
            labels=data.columns[2:]
            for i in range(2,l):
                z = X[:,i]
                if logz:
                    z = parent_self._apply_logz(z)
                if color==None:
                    c = cmap(float(i)/(l))
                else:
                    c = color
                h=ax.scatter(x, y, z, edgecolor='black', c=c, linewidth=lw,
                           alpha=alpha, marker=marker, s=ms)
                handles.append(h)
            if pointlabels is not None:
                trans_offset = mtrans.offset_copy(ax.transData, fig=self.fig,
                                  x=0.05, y=0.10, units='inches')
                for i in zip(x,y,z,pointlabels):
                    txt=i[3]
                    ax.text(i[0],i[1],i[2], txt, None,
                    transform=trans_offset)

            return handles,labels

        lw = kwds['linewidth']
        alpha = kwds['alpha']
        ms = kwds['ms']*6
        marker = kwds['marker']
        if marker=='':
            marker='o'
        by = kwds['by']
        legend = kwds['legend']
        cmap = self.getcmap(kwds['colormap'])
        labelcol = kwds['labelcol']
        handles=[]
        pl=None
        if by != '':
            if by not in data.columns:
                self.showWarning('grouping column not in selection')
                return
            g = data.groupby(by)
            i=0
            pl=None
            for n,df in g:
                c = cmap(float(i)/(len(g)))
                if labelcol != '':
                    pl = df[labelcol]
                h,l = doscatter(df, ax, color=c, pointlabels=pl)
                handles.append(h[0])
                i+=1
            self.fig.legend(handles, g.groups)

        else:
            if labelcol != '':
                pl = data[labelcol]
            handles,lbls=doscatter(data, ax, pointlabels=pl)
            self.fig.legend(handles, lbls)
        return

    def updateData(self):
        """
        Update data-related widgets (e.g., column selectors) in options panels.
        """

        if self.table is None:
            return
        df = self.table.model.df
        self.mplopts.update(df)
        return

    def updateStyle(self):
        """
        Apply the selected matplotlib style.
        """
        if self.style == None:
            mpl.rcParams.update(mpl.rcParamsDefault)
        else:
            plt.style.use(self.style)
        return

    def savePlot(self, filename=None):
        """
        Save the current plot to a file.

        Args:
            filename (str): Path to save. If None, prompts user.
        """

        ftypes = [('png','*.png'),('jpg','*.jpg'),('tif','*.tif'),('pdf','*.pdf'),
                    ('eps','*.eps'),('svg','*.svg')]
        if filename == None:
            filename = filedialog.asksaveasfilename(parent=self.master,
                                                     initialdir = self.currentdir,
                                                     filetypes=ftypes)
        if filename:
            self.currentdir = os.path.dirname(os.path.abspath(filename))
            dpi = self.globalopts['dpi']
            self.fig.savefig(filename, dpi=dpi)
        return

    def showWarning(self, text='plot error', ax=None):
        """
        Display a warning message on the plot canvas.

        Args:
            text (str): The warning message.
            ax: The axis to display text on.
        """

        if ax==None:
            ax = self.fig.add_subplot(111)
        ax.clear()
        ax.text(.5, .5, text, transform=self.ax.transAxes,
                       horizontalalignment='center', color='blue', fontsize=16)
        self.canvas.draw()
        return

    def toggle_options(self):
        """
        Toggle the visibility of the options panel.
        """

        if self.nb.winfo_ismapped() == 1:
            self.nb.pack_forget()
        else:
            self.nb.pack(fill=BOTH,expand=1)
        return

    def close(self):
        """
        Close the PlotViewer window and clean up.
        """

        self.table.pf = None
        self.animateopts.stop()
        self.main.destroy()
        return

class TkOptions(object):
    """
    Base class to generate a tkinter widget dialog for a dictionary of options.

    Args:
        parent: The parent object (usually PlotViewer).
    """
    def __init__(self, parent=None):
        """Setup variables"""

        self.parent = parent
        df = self.parent.table.model.df
        return

    def applyOptions(self):
        """
        Collect values from tkinter variables and update the kwds dictionary.
        """

        kwds = {}
        for i in self.opts:
            if not i in self.tkvars:
                continue
            #print (i, self.opts[i]['type'], self.widgets[i])
            if self.opts[i]['type'] == 'listbox':
                items = self.widgets[i].curselection()
                kwds[i] = [self.widgets[i].get(j) for j in items]
            elif self.opts[i]['type'] == 'scrolledtext':
                kwds[i] = self.widgets[i].get('1.0',END)
            elif self.opts[i]['type'] == 'checkbutton':
                kwds[i] = bool(self.tkvars[i].get())
            else:
                kwds[i] = self.tkvars[i].get()
        self.kwds = kwds
        return

    def setWidgetStyles(self):
        """
        Set background colors for widgets to match theme.
        """

        style = Style()
        bg = style.lookup('TLabel.label', 'background')
        for i in self.widgets:
            try:
                self.widgets[i].configure(fg='black', bg=bg)
            except:
                pass
        return

    def apply(self):
        """
        Apply options and trigger callback if present.
        """
        self.applyOptions()
        if self.callback != None:
            self.callback()
        return

    def showDialog(self, parent, layout='horizontal'):
        """
        Create and return the dialog frame with auto-generated widgets.

        Args:
            parent: Parent widget.
            layout (str): Layout direction.

        Returns:
            Frame: The dialog frame.
        """

        dialog, self.tkvars, self.widgets, self.group_frames = dialogFromOptions(parent,
                                                              self.opts, self.groups,
                                                              layout=layout)
        self.setWidgetStyles()
        return dialog

    def updateFromDict(self, kwds=None):
        """
        Update the tkinter variables from a dictionary of values.

        Args:
            kwds (dict): Dictionary of values to set.
        """

        if kwds != None:
            self.kwds = kwds
        elif hasattr(self, 'kwds'):
            kwds = self.kwds
        else:
            return
        if self.tkvars == None:
            return
        for i in kwds:
            if i in self.tkvars and self.tkvars[i]:
                self.tkvars[i].set(kwds[i])
        return

    def increment(self, key, inc):
        """
        Increment the value of a numeric option.

        Args:
            key (str): Option key.
            inc (float/int): Amount to increment.
        """

        new = self.kwds[key]+inc
        self.tkvars[key].set(new)
        return

class MPLBaseOptions(TkOptions):
    """
    Class to provide a dialog for basic matplotlib options (2D plots).
    """

    kinds = ['line', 'scatter', 'bar', 'barh', 'pie', 'histogram', 'boxplot', 'violinplot', 'dotplot',
             'heatmap', 'area', 'hexbin', 'contour', 'imshow', 'scatter_matrix', 'density', 'radviz', 'venn', 'shmoo', 'bathtub', 'sparam', 'gantt', 'eye', 'jitter', 'phasenoise']
    legendlocs = ['best','upper right','upper left','lower left','lower right','right','center left',
                'center right','lower center','upper center','center']
    defaultfont = 'monospace'

    # Map plot types to relevant option groups (context-aware filtering)
    PLOT_TYPE_GROUPS = {
        'line':           ['general', 'data', 'axes', 'sizes', 'formats', 'colors'],
        'scatter':        ['general', 'data', 'axes', 'sizes', 'formats', 'colors'],
        'bar':            ['general', 'data', 'axes', 'sizes', 'formats', 'colors'],
        'barh':           ['general', 'data', 'axes', 'sizes', 'formats', 'colors'],
        'area':           ['general', 'data', 'axes', 'sizes', 'formats', 'colors'],
        'pie':            ['general', 'data', 'colors'],
        'histogram':      ['general', 'data', 'axes', 'colors', 'density'],
        'density':        ['general', 'data', 'axes', 'colors', 'density'],
        'boxplot':        ['general', 'data', 'axes', 'formats', 'colors'],
        'violinplot':     ['general', 'data', 'axes', 'formats', 'colors'],
        'dotplot':        ['general', 'data', 'axes', 'sizes', 'formats', 'colors'],
        'heatmap':        ['general', 'axes', 'colors'],
        'hexbin':         ['general', 'axes', 'colors'],
        'contour':        ['general', 'axes', 'colors'],
        'imshow':         ['general', 'axes', 'colors'],
        'scatter_matrix': ['general', 'data', 'axes', 'sizes', 'formats', 'colors'],
        'radviz':         ['general', 'data', 'colors'],
        'venn':           ['general', 'colors'],
        'shmoo':          ['general', 'shmoo', 'colors'],
        'bathtub':        ['general', 'bathtub', 'colors'],
        'sparam':         ['general', 'sparam', 'axes', 'colors'],
        'gantt':          ['general', 'gantt', 'colors'],
        'eye':            ['general', 'eye', 'colors'],
        'jitter':         ['general', 'jitter', 'colors'],
        'phasenoise':     ['general', 'phasenoise', 'axes', 'colors'],
    }

    def __init__(self, parent=None):
        """
        Initialize options structure.

        Args:
            parent: Parent object.
        """

        self.parent = parent
        if self.parent is not None:
            df = self.parent.table.model.df
            datacols = list(df.columns)
            datacols.insert(0,'')
        else:
            datacols=[]
        fonts = util.getFonts()
        scales = ['linear','log']
        grps = {'data':['by','by2','labelcol','pointsizes'],
                'formats':['font','marker','linestyle','alpha'],
                'sizes':['fontsize','ms','linewidth'],
                'general':['kind','bins','hist_min','hist_max','stacked','subplots','use_index','errorbars'],
                'axes':['grid','legend','showxlabels','showylabels','sharex','sharey','logx','logy'],
                'colors':['colormap','bw','clrcol','cscale','colorbar'],
                'density':['bw_method','fill','show_rug'],
                'shmoo':['show_values','log_z_scale','x_param','y_param','z_param','threshold_min','threshold_max',
                        'show_contours','contour_levels','interpolation','show_stats',
                        'marker_size','show_markers'],
                'bathtub':['ber_target','show_margins','x_axis_type','show_target_line',
                          'margin_style','dual_curve'],
                'sparam':['log_freq','show_phase','spec_limit','limit_type',
                         'nyquist_marker','data_rate','freq_range','db_range'],
                'gantt':['show_progress','show_today','date_format','bar_height',
                        'show_milestones','group_by','sort_by'],
                'eye':['persistence','ui_width','sample_rate','bit_rate','show_mask',
                      'mask_margin','color_mode','overlay_count'],
                'jitter':['bins','show_stats','show_gaussian','show_dual_dirac',
                         'tj_separation','show_components'],
                'phasenoise':['carrier_freq','freq_min','freq_max','show_stats']}
        order = ['general','data','axes','sizes','formats','colors','density','shmoo','bathtub','sparam','gantt','eye','jitter','phasenoise']
        self.groups = OrderedDict((key, grps[key]) for key in order)
        opts = self.opts = {'font':{'type':'combobox','default':self.defaultfont,'items':fonts},
                'fontsize':{'type':'scale','default':12,'range':(5,40),'interval':1,'label':'font size'},
                'marker':{'type':'combobox','default':'','items': markers},
                'linestyle':{'type':'combobox','default':'-','items': linestyles},
                'ms':{'type':'scale','default':5,'range':(1,80),'interval':1,'label':'marker size'},
                'grid':{'type':'checkbutton','default':0,'label':'show grid'},
                'logx':{'type':'checkbutton','default':0,'label':'log x'},
                'logy':{'type':'checkbutton','default':0,'label':'log y'},
                #'rot':{'type':'entry','default':0, 'label':'xlabel angle'},
                'use_index':{'type':'checkbutton','default':1,'label':'use index'},
                'errorbars':{'type':'checkbutton','default':0,'label':'errorbar column'},
                'clrcol':{'type':'combobox','items':datacols,'label':'color by value','default':''},
                'cscale':{'type':'combobox','items':scales,'label':'color scale','default':'linear'},
                'colorbar':{'type':'checkbutton','default':0,'label':'show colorbar'},
                'bw':{'type':'checkbutton','default':0,'label':'black & white'},
                'showxlabels':{'type':'checkbutton','default':1,'label':'x tick labels'},
                'showylabels':{'type':'checkbutton','default':1,'label':'y tick labels'},
                'sharex':{'type':'checkbutton','default':0,'label':'share x'},
                'sharey':{'type':'checkbutton','default':0,'label':'share y'},
                'legend':{'type':'checkbutton','default':1,'label':'legend'},
                #'loc':{'type':'combobox','default':'best','items':self.legendlocs,'label':'legend loc'},
                'kind':{'type':'combobox','default':'line','items':self.kinds,'label':'plot type'},
                'stacked':{'type':'checkbutton','default':0,'label':'stacked'},
                'linewidth':{'type':'scale','default':1.5,'range':(0,10),'interval':0.1,'label':'line width'},
                'alpha':{'type':'scale','default':0.9,'range':(0,1),'interval':0.1,'label':'alpha'},
                'subplots':{'type':'checkbutton','default':0,'label':'multiple subplots'},
                'colormap':{'type':'combobox','default':'Spectral','items':colormaps},
                'bins':{'type':'entry','default':20,'width':10},
                'hist_min':{'type':'entry','default':'','width':10,'label':'min threshold'},
                'hist_max':{'type':'entry','default':'','width':10,'label':'max threshold'},
                'by':{'type':'combobox','items':datacols,'label':'group by','default':''},
                'by2':{'type':'combobox','items':datacols,'label':'group by 2','default':''},
                'labelcol':{'type':'combobox','items':datacols,'label':'point labels','default':''},
                'pointsizes':{'type':'combobox','items':datacols,'label':'point sizes','default':''},
                'bw_method':{'type':'combobox','default':'scott',
                            'items':['scott','silverman','0.1','0.2','0.5','1.0'],
                            'label':'bandwidth method'},
                'fill':{'type':'checkbutton','default':0,'label':'fill under curve'},
                'show_rug':{'type':'checkbutton','default':0,'label':'show rug plot'},
                'x_param':{'type':'combobox','items':datacols,'label':'X parameter','default':''},
                'y_param':{'type':'combobox','items':datacols,'label':'Y parameter','default':''},
                'z_param':{'type':'combobox','items':datacols,'label':'Z value','default':''},
                'threshold_min':{'type':'entry','default':'','width':10,'label':'min threshold'},
                'threshold_max':{'type':'entry','default':'','width':10,'label':'max threshold'},
                'show_contours':{'type':'checkbutton','default':0,'label':'show contours'},
                'contour_levels':{'type':'entry','default':10,'width':10,'label':'contour levels'},
                'interpolation':{'type':'combobox','default':'nearest',
                               'items':['none','nearest','bilinear','cubic'],
                               'label':'interpolation'},
                'show_stats':{'type':'checkbutton','default':0,'label':'show statistics'},
                'marker_size':{'type':'scale','default':50,'range':(10,200),'interval':10,'label':'marker size'},
                'show_markers':{'type':'checkbutton','default':0,'label':'show markers'},
                'show_values':{'type':'checkbutton','default':1,'label':'show values'},
                'log_z_scale':{'type':'checkbutton','default':1,'label':'log10 scale (Z)'},
                'ber_target':{'type':'entry','default':'1e-12','width':10,'label':'BER target'},
                'show_margins':{'type':'checkbutton','default':1,'label':'show margins'},
                'x_axis_type':{'type':'combobox','default':'UI',
                              'items':['UI','Time (ps)','Voltage (mV)'],
                              'label':'X-axis type'},
                'show_target_line':{'type':'checkbutton','default':1,'label':'show target line'},
                'margin_style':{'type':'combobox','default':'arrows',
                               'items':['arrows','lines','shaded'],
                               'label':'margin style'},
                'dual_curve':{'type':'checkbutton','default':0,'label':'dual curve (L/R)'},
                'log_freq':{'type':'checkbutton','default':1,'label':'log frequency'},
                'show_phase':{'type':'checkbutton','default':0,'label':'show phase'},
                'spec_limit':{'type':'entry','default':'','width':10,'label':'spec limit (dB)'},
                'limit_type':{'type':'combobox','default':'None',
                             'items':['None','Horizontal','Vertical'],
                             'label':'limit type'},
                'nyquist_marker':{'type':'checkbutton','default':0,'label':'Nyquist marker'},
                'data_rate':{'type':'entry','default':'','width':10,'label':'data rate (Gbps)'},
                'freq_range':{'type':'entry','default':'','width':15,'label':'freq range (GHz)'},
                'db_range':{'type':'entry','default':'','width':15,'label':'dB range'},
                'show_progress':{'type':'checkbutton','default':1,'label':'show progress'},
                'show_today':{'type':'checkbutton','default':1,'label':'show today line'},
                'date_format':{'type':'combobox','default':'%Y-%m-%d',
                              'items':['%Y-%m-%d','%m/%d/%Y','%d/%m/%Y','%b %d','%Y-%m'],
                              'label':'date format'},
                'bar_height':{'type':'scale','default':0.8,'range':(0.3,1.0),'interval':0.1,'label':'bar height'},
                'show_milestones':{'type':'checkbutton','default':1,'label':'show milestones'},
                'group_by':{'type':'entry','default':'','width':15,'label':'group by column'},
                'sort_by':{'type':'combobox','default':'start_date',
                          'items':['start_date','end_date','task_name','duration','none'],
                          'label':'sort by'},
                'persistence':{'type':'scale','default':100,'range':(10,1000),'interval':10,'label':'persistence'},
                'ui_width':{'type':'scale','default':1.0,'range':(0.5,2.0),'interval':0.1,'label':'UI width'},
                'sample_rate':{'type':'entry','default':'','width':15,'label':'sample rate (GS/s)'},
                'bit_rate':{'type':'entry','default':'','width':15,'label':'bit rate (Gbps)'},
                'show_mask':{'type':'checkbutton','default':0,'label':'show mask'},
                'mask_margin':{'type':'scale','default':0.3,'range':(0.1,0.5),'interval':0.05,'label':'mask margin'},
                'color_mode':{'type':'combobox','default':'density',
                             'items':['density','overlay','single'],
                             'label':'color mode'},
                'overlay_count':{'type':'scale','default':100,'range':(10,1000),'interval':10,'label':'overlay count'},
                'bins':{'type':'scale','default':100,'range':(20,500),'interval':10,'label':'bins'},
                'show_stats':{'type':'checkbutton','default':1,'label':'show statistics'},
                'show_gaussian':{'type':'checkbutton','default':1,'label':'show Gaussian fit'},
                'show_dual_dirac':{'type':'checkbutton','default':0,'label':'show dual-Dirac'},
                'tj_separation':{'type':'entry','default':'','width':15,'label':'TJ separation (ps)'},
                'show_components':{'type':'checkbutton','default':0,'label':'show RJ/DJ components'},
                'carrier_freq':{'type':'entry','default':'156e6','width':15,'label':'carrier freq (Hz)'},
                'freq_min':{'type':'entry','default':'','width':15,'label':'freq min (Hz)'},
                'freq_max':{'type':'entry','default':'','width':15,'label':'freq max (Hz)'},
                }
        _apply_option_tooltips(self.opts, BASE_OPTION_TOOLTIPS)
        self.kwds = {}
        return

    def applyOptions(self):
        """
        Apply options and set global font settings.
        """

        TkOptions.applyOptions(self)
        size = self.kwds['fontsize']
        plt.rc("font", family=self.kwds['font'], size=size)
        plt.rc('legend', fontsize=size-1)
        return

    def showDialog(self, parent, layout='horizontal', collapsible=True, use_grid=True):
        """
        Create and return the dialog frame with auto-generated widgets.
        Overrides parent to bind kind combobox for context-aware visibility.

        Args:
            parent: Parent widget.
            layout (str): Layout direction.
            collapsible (bool): If True, use collapsible frames for option groups.
            use_grid (bool): If True, use grid layout within groups for better alignment.

        Returns:
            Frame: The dialog frame.
        """
        dialog, self.tkvars, self.widgets, self.group_frames = dialogFromOptions(parent,
                                                              self.opts, self.groups,
                                                              layout=layout,
                                                              collapsible=collapsible,
                                                              use_grid=use_grid)
        self.setWidgetStyles()

        # Add "Show All Options" checkbox to the general group
        self._show_all_var = IntVar(value=0)
        if 'general' in self.group_frames:
            general_frame = self.group_frames['general']
            # For collapsible frames, add to content; otherwise add directly
            target_frame = general_frame.content if hasattr(general_frame, 'content') else general_frame
            show_all_cb = Checkbutton(target_frame, text='show all options',
                                      variable=self._show_all_var,
                                      command=self._on_show_all_changed)
            # Use grid if use_grid is enabled, otherwise pack
            if use_grid:
                # Find the next available row in the grid
                grid_info = target_frame.grid_size()
                next_row = grid_info[1]  # Number of rows
                show_all_cb.grid(row=next_row, column=0, columnspan=2, sticky='w', padx=4, pady=2)
            else:
                show_all_cb.pack(fill=X)

        # Bind kind combobox to update visible groups
        if 'kind' in self.widgets:
            self.widgets['kind'].bind('<<ComboboxSelected>>', self._on_kind_changed)
            # Set initial visibility based on default kind
            self.update_visible_groups(self.opts['kind']['default'])

        return dialog

    def _on_kind_changed(self, event=None):
        """Handle plot type selection change."""
        if hasattr(self, '_show_all_var') and self._show_all_var.get():
            return  # Don't filter if "show all" is enabled
        kind = self.tkvars['kind'].get()
        self.update_visible_groups(kind)

    def _on_show_all_changed(self):
        """Handle 'Show All Options' checkbox toggle."""
        if self._show_all_var.get():
            self._show_all_groups()
        else:
            kind = self.tkvars['kind'].get()
            self.update_visible_groups(kind)

    def _show_all_groups(self):
        """Show all option groups."""
        if not hasattr(self, 'group_frames') or not self.group_frames:
            return
        for group_name, frame in self.group_frames.items():
            if not frame.winfo_ismapped():
                frame.pack(side=LEFT, fill=Y, expand=False)

    def update_visible_groups(self, kind):
        """
        Show/hide option groups based on selected plot type.

        Args:
            kind (str): The selected plot type.
        """
        if not hasattr(self, 'group_frames') or not self.group_frames:
            return

        # If "show all" is enabled, don't filter
        if hasattr(self, '_show_all_var') and self._show_all_var.get():
            return

        # Get relevant groups for this plot type, default to showing common groups
        visible_groups = self.PLOT_TYPE_GROUPS.get(kind, ['general', 'data', 'axes', 'sizes', 'formats', 'colors'])

        for group_name, frame in self.group_frames.items():
            if group_name in visible_groups:
                # Show the group
                if not frame.winfo_ismapped():
                    frame.pack(side=LEFT, fill=Y, expand=False)
            else:
                # Hide the group
                frame.pack_forget()

    def update(self, df):
        """
        Update dropdown menus with column names from the DataFrame.

        Args:
            df (pd.DataFrame): The current DataFrame.
        """

        if util.check_multiindex(df.columns) == 1:
            cols = list(df.columns.get_level_values(0))
        else:
            cols = list(df.columns)
        #add empty value
        cols = ['']+cols
        self.widgets['by']['values'] = cols
        self.widgets['by2']['values'] = cols
        self.widgets['labelcol']['values'] = cols
        self.widgets['clrcol']['values'] = cols
        # Update shmoo plot parameter dropdowns
        if 'x_param' in self.widgets:
            self.widgets['x_param']['values'] = cols
        if 'y_param' in self.widgets:
            self.widgets['y_param']['values'] = cols
        if 'z_param' in self.widgets:
            self.widgets['z_param']['values'] = cols
        return

class MPL3DOptions(MPLBaseOptions):
    """
    Class to provide options for 3D plots.
    """

    kinds = ['scatter', 'bar', 'contour', 'wireframe', 'surface']
    defaultfont = 'monospace'

    def __init__(self, parent=None):
        """
        Initialize 3D options.

        Args:
            parent: Parent object.
        """

        self.parent = parent
        if self.parent is not None:
            df = self.parent.table.model.df
            datacols = list(df.columns)
            datacols.insert(0,'')
        else:
            datacols=[]
        fonts = util.getFonts()
        modes = ['parametric','(x,y)->z']
        self.groups = grps = {'formats':['kind','mode','rstride','cstride','points','logz'],
                             }
        self.groups = OrderedDict(sorted(grps.items()))
        opts = self.opts = {
                'kind':{'type':'combobox','default':'scatter','items':self.kinds,'label':'kind'},
                'rstride':{'type':'entry','default':2,'width':20},
                'cstride':{'type':'entry','default':2,'width':20},
                'points':{'type':'checkbutton','default':0,'label':'show points'},
                'mode':{'type':'combobox','default':'(x,y)->z','items': modes},
                'logz':{'type':'checkbutton','default':0,'label':'log Z'},
                 }
        _apply_option_tooltips(self.opts, MPL3D_OPTION_TOOLTIPS)
        self.kwds = {}
        return

    def showDialog(self, parent, layout='horizontal'):
        """
        Create and return the dialog frame.
        Uses base TkOptions behavior without context-aware filtering.

        Args:
            parent: Parent widget.
            layout (str): Layout direction.

        Returns:
            Frame: The dialog frame.
        """
        dialog, self.tkvars, self.widgets, self.group_frames = dialogFromOptions(parent,
                                                              self.opts, self.groups,
                                                              layout=layout,
                                                              collapsible=True,
                                                              use_grid=True)
        return dialog

    def applyOptions(self):
        """
        Apply options.
        """

        TkOptions.applyOptions(self)
        return

class PlotLayoutOptions(TkOptions):
    """
    Class to manage grid layout options for subplots.
    """
    def __init__(self, parent=None):
        """
        Initialize layout variables.

        Args:
            parent: Parent object.
        """

        self.parent = parent
        self.rows = 2
        self.cols = 2
        self.top = .1
        self.bottom =.9
        return

    def showDialog(self, parent, layout='horizontal'):
        """
        Create the layout configuration dialog (grid selector, sliders, etc.).

        Args:
            parent: Parent widget.
            layout: Layout direction.

        Returns:
            Frame: The dialog frame.
        """

        self.tkvars = {}
        self.main = Frame(parent)
        self.plotgrid = c = PlotLayoutGrid(self.main)
        self.plotgrid.update_callback = self.updateFromGrid
        c.pack(side=LEFT,fill=Y,pady=2,padx=2)

        frame = Frame(self.main)
        frame.pack(side=LEFT,fill=Y)
        v = self.rowsvar = IntVar()
        v.set(self.rows)
        w = Scale(frame,label='rows',
                 from_=1,to=6,
                 orient='vertical',
                 resolution=1,
                 variable=v,
                 command=self.resetGrid)
        maybe_add_tooltip('Number of subplot rows to allocate.', w)
        w.pack(fill=X,pady=2)
        v = self.colsvar = IntVar()
        v.set(self.cols)
        w = Scale(frame,label='cols',
                 from_=1,to=6,
                 orient='horizontal',
                 resolution=1,
                 variable=v,
                 command=self.resetGrid)
        maybe_add_tooltip('Number of subplot columns to allocate.', w)
        w.pack(side=TOP,fill=X,pady=2)

        self.modevar = StringVar()
        self.modevar.set('normal')
        frame = LabelFrame(self.main, text='modes')
        rb = Radiobutton(frame, text='normal', variable=self.modevar, value='normal')
        rb.pack(fill=X)
        maybe_add_tooltip('Single subplot layout using all selected data.', rb)
        rb = Radiobutton(frame, text='split data', variable=self.modevar, value='splitdata')
        rb.pack(fill=X)
        maybe_add_tooltip('Split selected data into multiple subplots.', rb)
        rb = Radiobutton(frame, text='multi views', variable=self.modevar, value='multiviews')
        rb.pack(fill=X)
        maybe_add_tooltip('Enable collection of predefined multi-view plots.', rb)
        frame.pack(side=LEFT,fill=Y)

        frame = LabelFrame(self.main, text='multi views')
        #v = self.multiviewsvar = BooleanVar()
        plot_types = ['histogram','line','scatter','boxplot','dotplot','area','density','bar','barh',
                      'heatmap','contour','hexbin','imshow']
        lbl = Label(frame,text='plot types:')
        lbl.pack(fill=X)
        w,v = addListBox(frame, values=plot_types,width=12,height=8)
        w.pack(fill=X)
        maybe_add_tooltip('Choose plot types to include in multi-view layouts.', lbl, v)
        self.plottypeslistbox = v
        frame.pack(side=LEFT,fill=Y)

        frame = LabelFrame(self.main, text='split data')
        frame.pack(side=LEFT,fill=Y)

        frame = LabelFrame(self.main, text='subplots')
        v = self.axeslistvar = StringVar()
        v.set('')
        axes = []
        self.axeslist = Combobox(frame, values=axes,
                        textvariable=v,width=14)
        lbl = Label(frame,text='plot list:')
        lbl.pack()
        self.axeslist.pack(fill=BOTH,pady=2)
        maybe_add_tooltip('Select an axis from the current layout.', lbl, self.axeslist)
        b = Button(frame, text='remove axis', command=self.parent.removeSubplot)
        maybe_add_tooltip('Remove the selected subplot from the layout.', b)
        b.pack(fill=X,pady=2)
        b = Button(frame, text='set title', command=self.parent.setSubplotTitle)
        maybe_add_tooltip('Assign a custom title to the selected subplot.', b)
        b.pack(fill=X,pady=2)
        frame.pack(side=LEFT,fill=Y)
        self.updateFromGrid()
        return self.main

    def setmultiviews(self, event=None):
        """
        Handle toggle of multi-views mode.
        """
        val=self.multiviewsvar.get()
        if val == 1:
            self.parent.multiviews = True
            self.parent.gridlayoutvar.set(1)
        if val == 0:
            self.parent.multiviews = False
        return

    def resetGrid(self, event=None):
        """
        Reset the grid selection widget based on slider values.
        """

        pg = self.plotgrid
        self.rows = pg.rows = self.rowsvar.get()
        self.cols = pg.cols = self.colsvar.get()
        pg.selectedrows = [0]
        pg.selectedcols = [0]
        pg.redraw()
        self.updateFromGrid()
        return

    def updateFromGrid(self):
        """
        Update internal state from grid selection.
        """
        pg = self.plotgrid
        r = self.selectedrows = pg.selectedrows
        c = self.selectedcols = pg.selectedcols
        self.rowspan = len(r)
        self.colspan = len(c)
        return

    def updateAxesList(self):
        """
        Update the list of available axes in the dropdown.
        """

        axes = list(self.parent.gridaxes.keys())
        self.axeslist['values'] = axes
        return

class PlotLayoutGrid(BaseTable):
    """
    A simple table widget for selecting grid cells.
    """
    def __init__(self, parent=None, width=280, height=205, rows=2, cols=2, **kwargs):
        BaseTable.__init__(self, parent, bg='white',
                         width=width, height=height )
        return

    def handle_left_click(self, event):
        """
        Handle click to select cells.
        """
        BaseTable.handle_left_click(self, event)

class AnnotationOptions(TkOptions):
    """
    Class to provide options for plot annotations (titles, labels, text boxes).
    """
    def __init__(self, parent=None):
        """
        Initialize annotation options.

        Args:
            parent: Parent object.
        """

        from matplotlib import colors
        import six
        colors = list(six.iteritems(colors.cnames))
        colors = sorted([c[0] for c in colors])
        fillpatterns = ['-', '+', 'x', '\\', '*', 'o', 'O', '.']
        bstyles = ['square','round','round4','circle','rarrow','larrow','sawtooth']
        fonts = util.getFonts()
        defaultfont = 'monospace'
        fontweights = ['normal','bold','heavy','light','ultrabold','ultralight']
        alignments = ['left','center','right']

        self.parent = parent
        self.groups = grps = {'global labels':['title','xlabel','ylabel','rot'],
                              'textbox': ['boxstyle','facecolor','linecolor','rotate'],
                              'textbox format': ['fontsize','font','fontweight','align'],
                              'text to add': ['text']
                             }
        self.groups = OrderedDict(sorted(grps.items()))
        opts = self.opts = {
                'title':{'type':'entry','default':'','width':20},
                'xlabel':{'type':'entry','default':'','width':20},
                'ylabel':{'type':'entry','default':'','width':20},
                'facecolor':{'type':'combobox','default':'white','items': colors},
                'linecolor':{'type':'combobox','default':'black','items': colors},
                'fill':{'type':'combobox','default':'-','items': fillpatterns},
                'rotate':{'type':'scale','default':0,'range':(-180,180),'interval':1,'label':'rotate'},
                'boxstyle':{'type':'combobox','default':'square','items': bstyles},
                'text':{'type':'scrolledtext','default':'','width':20},
                'align':{'type':'combobox','default':'center','items': alignments},
                'font':{'type':'combobox','default':defaultfont,'items':fonts},
                'fontsize':{'type':'scale','default':12,'range':(4,50),'interval':1,'label':'font size'},
                'fontweight':{'type':'combobox','default':'normal','items': fontweights},
                'rot':{'type':'entry','default':0, 'label':'ticklabel angle'}
                }
        _apply_option_tooltips(self.opts, ANNOTATION_OPTION_TOOLTIPS)
        self.kwds = {}
        #used to store annotations
        self.textboxes = {}
        return

    def showDialog(self, parent, layout='horizontal'):
        """
        Create the annotation options dialog.

        Args:
            parent: Parent widget.
            layout: Layout direction.

        Returns:
            Frame: The dialog frame.
        """

        dialog, self.tkvars, self.widgets, self.group_frames = dialogFromOptions(parent,
                                                              self.opts, self.groups,
                                                              layout=layout)
        self.main = dialog
        self.addWidgets()
        self.setWidgetStyles()
        return dialog

    def addWidgets(self):
        """
        Add controls for adding manual annotations (textboxes, arrows).
        """

        frame = LabelFrame(self.main, text='add objects')
        v = self.objectvar = StringVar()
        v.set('textbox')
        w = Combobox(frame, values=['textbox'],#'arrow'],
                         textvariable=v,width=14)
        Label(frame,text='add object').pack()
        w.pack(fill=BOTH,pady=2)
        self.coordsvar = StringVar()
        self.coordsvar.set('data')
        w = Combobox(frame, values=['data','axes fraction','figure fraction'],
                         textvariable=self.coordsvar,width=14)
        Label(frame,text='coord system').pack()
        w.pack(fill=BOTH,pady=2)

        b = Button(frame, text='Create', command=self.addObject)
        b.pack(fill=X,pady=2)
        b = Button(frame, text='Clear', command=self.clear)
        b.pack(fill=X,pady=2)
        frame.pack(side=LEFT,fill=Y)
        return

    def clear(self):
        """
        Clear all manually added annotations.
        """
        self.textboxes = {}
        self.parent.replot()
        return

    def addObject(self):
        """
        Add an annotation object based on the selected type.
        """

        o = self.objectvar.get()
        if o == 'textbox':
            self.addTextBox()
        elif o == 'arrow':
            self.addArrow()
        return

    def addTextBox(self, kwds=None, key=None):
        """
        Add a text box annotation to the plot.

        Args:
            kwds (dict): Dictionary of text properties (text, xy, etc.).
            key (str): Unique ID for the annotation.
        """

        import matplotlib.patches as patches
        from matplotlib.text import OffsetFrom

        self.applyOptions()
        if kwds == None:
            kwds = self.kwds
            kwds['xycoords'] = self.coordsvar.get()
        fig = self.parent.fig
        #ax = self.parent.ax
        ax = fig.get_axes()[0]
        canvas = self.parent.canvas
        text = kwds['text'].strip('\n')
        fc = kwds['facecolor']
        ec = kwds['linecolor']
        bstyle = kwds['boxstyle']
        style = "%s,pad=.2" %bstyle
        fontsize = kwds['fontsize']
        font = mpl.font_manager.FontProperties(family=kwds['font'],
                            weight=kwds['fontweight'])
        bbox_args = dict(boxstyle=bstyle, fc=fc, ec=ec, lw=1, alpha=0.9)
        arrowprops = dict(arrowstyle="-|>", connectionstyle="arc3")

        xycoords = kwds['xycoords']
        #if previously drawn will have xy values
        if 'xy' in kwds:
            xy = kwds['xy']
            #print (text, xycoords, xy)
        else:
            xy=(.1, .8)
            xycoords='axes fraction'

        an = ax.annotate(text, xy=xy, xycoords=xycoords,
                   ha=kwds['align'], va="center",
                   size=fontsize,
                   fontproperties=font, rotation=kwds['rotate'],
                   #arrowprops=arrowprops,
                   #xytext=(xy[0]+.2,xy[1]),
                   #textcoords='offset points',
                   zorder=10,
                   bbox=bbox_args)
        an.draggable()
        if key == None:
            import uuid
            key = str(uuid.uuid4().fields[0])
        #need to add the unique id to the annotation
        #so it can be tracked in event handler
        an._id = key
        if key not in self.textboxes:
            self.textboxes[key] = kwds
            print(kwds)
        #canvas.show()
        canvas.draw()
        return

    def addArrow(self, kwds=None, key=None):
        """
        Add an arrow annotation (not fully implemented).
        """

        fig = self.parent.fig
        canvas = self.parent.canvas
        ax = fig.get_axes()[0]
        ax.arrow(0.2, 0.2, 0.5, 0.5, fc='k', ec='k',
                 transform=ax.transAxes)
        canvas.draw()
        #self.lines.append(line)
        return

    def redraw(self):
        """
        Redraw all stored annotations after a plot update.
        """

        #print (self.textboxes)
        for key in self.textboxes:
            self.addTextBox(self.textboxes[key], key)
        return

class ExtraOptions(TkOptions):
    """
    Class for additional options like axis ranges and ticks.
    """
    def __init__(self, parent=None):
        """
        Initialize extra options.

        Args:
            parent: Parent object.
        """

        self.parent = parent
        self.styles = sorted(plt.style.available)
        formats = ['auto','percent','eng','sci notation']
        datefmts = ['','%d','%b %d,''%Y-%m-%d','%d-%m-%Y',"%d-%m-%Y %H:%M"]
        self.groups = grps = {'axis ranges':['xmin','xmax','ymin','ymax'],
                              'axis tick positions':['major x-ticks','major y-ticks',
                                                   'minor x-ticks','minor y-ticks'],
                              'tick label format':['formatter','symbol','precision','date format'],
                              #'tables':['table']
                             }
        self.groups = OrderedDict(sorted(grps.items()))
        opts = self.opts = {'xmin':{'type':'entry','default':'','label':'x min'},
                            'xmax':{'type':'entry','default':'','label':'x max'},
                            'ymin':{'type':'entry','default':'','label':'y min'},
                            'ymax':{'type':'entry','default':'','label':'y max'},
                            'major x-ticks':{'type':'entry','default':0},
                            'major y-ticks':{'type':'entry','default':0},
                            'minor x-ticks':{'type':'entry','default':0},
                            'minor y-ticks':{'type':'entry','default':0},
                            'formatter':{'type':'combobox','items':formats,'default':'auto'},
                            'symbol':{'type':'entry','default':''},
                            'precision':{'type':'entry','default':0},
                            'date format':{'type':'combobox','items':datefmts,'default':''},
                            #'table':{'type':'checkbutton','default':0,'label':'show table'},
                            }
        _apply_option_tooltips(self.opts, EXTRA_OPTION_TOOLTIPS)
        self.kwds = {}
        return

    def showDialog(self, parent, layout='horizontal'):
        """
        Create the dialog.

        Args:
            parent: Parent widget.
            layout: Layout direction.

        Returns:
            Frame: The dialog frame.
        """

        dialog, self.tkvars, self.widgets, self.group_frames = dialogFromOptions(parent,
                                                              self.opts, self.groups,
                                                              layout=layout)
        self.main = dialog
        self.addWidgets()
        self.setWidgetStyles()
        return dialog

    def addWidgets(self):
        """
        Add style selection widgets.
        """

        main = self.main
        frame = LabelFrame(main, text='styles')
        v = self.stylevar = StringVar()
        v.set('ggplot')
        w = Combobox(frame, values=self.styles,
                         textvariable=v,width=14)
        w.pack(side=TOP,pady=2)
        addButton(frame, 'Apply', self.apply, None,
                  'apply', side=TOP, compound="left", width=20, padding=2)
        addButton(frame, 'Reset', self.reset, None,
                  'reset', side=TOP, compound="left", width=20, padding=2)
        frame.pack(side=LEFT,fill='y')
        return main

    def apply(self):
        """
        Apply the selected matplotlib style.
        """
        mpl.rcParams.update(mpl.rcParamsDefault)
        self.parent.style = self.stylevar.get()
        self.parent.replot()
        return

    def reset(self):
        """
        Reset to default matplotlib style.
        """
        mpl.rcParams.update(mpl.rcParamsDefault)
        self.parent.style = None
        self.parent.replot()
        return

class AnimateOptions(TkOptions):
    """
    Class for handling live updates or animation of plots.
    """
    def __init__(self, parent=None):
        """
        Initialize animation options.

        Args:
            parent: Parent object.
        """

        self.parent = parent
        df = self.parent.table.model.df
        datacols = list(df.columns)
        self.groups = grps = {'data window':['increment','window','startrow','delay'],
                              'display':['expand','usexrange','useyrange','tableupdate','smoothing','columntitle'],
                              #'3d mode':['rotate axis','degrees'],
                              'record video':['savevideo','codec','fps','filename']
                             }
        self.groups = OrderedDict(sorted(grps.items()))
        codecs = ['default','h264']
        opts = self.opts = {'increment':{'type':'entry','default':2},
                            'window':{'type':'entry','default':10},
                            'startrow':{'type':'entry','default':0,'label':'start row'},
                            'delay':{'type':'entry','default':.05},
                            'tableupdate':{'type':'checkbutton','default':0,'label':'update table'},
                            'expand':{'type':'checkbutton','default':0,'label':'expanding view'},
                            'usexrange':{'type':'checkbutton','default':0,'label':'use full x range'},
                            'useyrange':{'type':'checkbutton','default':0,'label':'use full y range'},
                            'smoothing':{'type':'checkbutton','default':0,'label':'smoothing'},
                            'columntitle':{'type':'combobox','default':'','items':datacols,'label':'column data as title'},
                            #'source':{'type':'entry','default':'','width':30},
                            #'rotate axis':{'type':'combobox','default':'x','items':['x','y','z'],'label':'rotate axis'},
                            #'degrees':{'type':'entry','default':5},
                            'savevideo':{'type':'checkbutton','default':0,'label':'save as video'},
                            'codec':{'type':'combobox','default':'default','items': codecs},
                            'fps':{'type':'entry','default':15},
                            'filename':{'type':'entry','default':'myplot.mp4','width':20},
                            }
        _apply_option_tooltips(self.opts, ANIMATE_OPTION_TOOLTIPS)
        self.kwds = {}
        self.running = False
        return

    def showDialog(self, parent, layout='horizontal'):
        """
        Create the animation options dialog.

        Args:
            parent: Parent widget.
            layout: Layout direction.

        Returns:
            Frame: The dialog frame.
        """

        dialog, self.tkvars, self.widgets, self.group_frames = dialogFromOptions(parent,
                                                              self.opts, self.groups,
                                                              layout=layout)
        self.main = dialog
        self.addWidgets()
        return dialog

    def addWidgets(self):
        """
        Add Start/Stop buttons for animation.
        """

        main = self.main
        frame = LabelFrame(main, text='Run')
        addButton(frame, 'START', self.start, None,
                  'apply', side=TOP, compound="left", width=20, padding=2)
        addButton(frame, 'STOP', self.stop, None,
                  'reset', side=TOP, compound="left", width=20, padding=2)
        frame.pack(side=LEFT,fill='y')
        return main

    def getWriter(self):
        """
        Get a FFMpegWriter instance for saving video.

        Returns:
            matplotlib.animation.FFMpegWriter
        """
        fps = self.kwds['fps']
        import matplotlib.animation as manimation
        FFMpegWriter = manimation.writers['ffmpeg']
        metadata = dict(title='My Plot', artist='Matplotlib',
                        comment='Made using DataExplore')
        writer = FFMpegWriter(fps=fps, metadata=metadata)
        return writer

    def update(self):
        """
        Main loop for live updating/recording.
        """

        self.applyOptions()
        savevid = self.kwds['savevideo']
        videofile  = self.kwds['filename']
        #if self.kwds['source'] != '':
        #    self.stream()
        #else:
        if savevid == 1:
            writer = self.getWriter()
            with writer.saving(self.parent.fig, videofile, 100):
                self.updateCurrent(writer)
        else:
            self.updateCurrent()
        return

    def updateCurrent(self, writer=None):
        """
        Iterate through rows of the table and update the plot (frame by frame).

        Args:
            writer: Optional FFMpegWriter to save frames.
        """

        kwds = self.kwds
        table = self.parent.table
        df = table.model.df
        titledata = None
        inc = kwds['increment']
        w = kwds['window']
        st = kwds['startrow']
        delay = float(kwds['delay'])
        refresh = kwds['tableupdate']
        expand = kwds['expand']
        fullxrange = kwds['usexrange']
        fullyrange = kwds['useyrange']
        smooth = kwds['smoothing']
        coltitle = kwds['columntitle']
        if coltitle != '':
            titledata = df[coltitle]
        self.parent.clear()
        for i in range(st,len(df)-w,inc):
            cols = table.multiplecollist
            if expand == 1:
                rows = range(st,i+w)
            else:
                rows = range(i,i+w)
            data = df.iloc[list(rows),cols]

            if smooth == 1:
                w=int(len(data)/10.0)
                data = data.rolling(w).mean()

            self.parent.data = data
            #plot but don't redraw figure until the end
            self.parent.applyPlotoptions()
            self.parent.plotCurrent(redraw=False)

            if titledata is not None:
                l = titledata.iloc[i]
                self.parent.setOption('title',l)
            if fullxrange == 1:
                self.parent.ax.set_xlim(df.index.min(),df.index.max())
            if fullyrange == 1:
                ymin = df.min(numeric_only=True).min()
                ymax = df.max(numeric_only=True).max()
                self.parent.ax.set_ylim(ymin,ymax)
            #finally draw the plot
            self.parent.canvas.draw()

            table.multiplerowlist = rows
            if refresh == 1:
                table.drawMultipleRows(rows)
            time.sleep(delay)
            if self.stopthread == True:
                return
            if writer is not None:
                writer.grab_frame()
        self.running = False
        return

    def stream(self):
        """
        Stream data from a URL (placeholder/not fully implemented).
        """

        import requests, io
        kwds = self.kwds
        table = self.parent.table
        #endpoint = kwds['source']
        base = ""
        endpoint = ""
        raw = requests.get(base + endpoint)#, params=payload)
        raw = io.BytesIO(raw.content)
        print ('got data source')
        print(raw)
        df = pd.read_csv(raw, sep=",")
        print (df)

        table.model.df = df
        for i in range(0,100):
            table.selectAll()
            self.parent.replot()
        return

    def start(self):
        """
        Start the animation loop in a separate thread.
        """

        if self.running == True:
            return
        from threading import Thread
        self.stopthread = False
        self.running = True
        t = Thread(target=self.update)
        t.start()
        self.thread = t
        return

    def stop(self):
        """
        Stop the animation loop.
        """

        self.stopthread = True
        self.running = False
        time.sleep(.2)
        try:
            self.parent.update_idletasks()
        except:
            pass
        return

def addFigure(parent, figure=None, resize_callback=None):
    """
    Create a matplotlib Figure and a FigureCanvasTkAgg in the parent frame.

    Args:
        parent: The parent tkinter widget.
        figure (Figure): Optional existing figure.
        resize_callback: Unused.

    Returns:
        tuple: (figure, canvas)
    """

    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg#, NavigationToolbar2TkAgg
    from matplotlib.figure import Figure

    if figure == None:
        figure = Figure(figsize=(6,4), dpi=100, facecolor='white')

    canvas = FigureCanvasTkAgg(figure, master=parent)
    canvas.draw()
    canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)
    canvas.get_tk_widget().configure(highlightcolor='gray75',
                                   highlightbackground='gray75')
    #canvas._tkcanvas.pack(side=TOP, fill=BOTH, expand=1)
    figure.subplots_adjust(bottom=0.15)
    return figure, canvas
