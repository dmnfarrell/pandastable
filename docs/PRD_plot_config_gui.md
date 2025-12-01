# PRD: Plot Configuration GUI Improvements

## Overview
Redesign the pandastable Plot Viewer options panel to improve usability, reduce visual clutter, and provide context-aware controls.

## Current State
The plot configuration GUI displays all options across 6 horizontal tabs (Base Options, Annotation, Grid Layout, Other Options, 3D Options, Animate). Within "Base Options", 12+ LabelFrame groups are packed horizontally, showing all plot-type-specific options (shmoo, bathtub, sparam, gantt, eye, jitter) regardless of the selected plot type.

### Problems
1. **Visual overload** - 50+ controls visible simultaneously
2. **No context filtering** - Irrelevant options shown (e.g., "bathtub" options when plotting a line chart)
3. **Poor layout** - Horizontal packing causes cramped, uneven widget sizing
4. **Difficult discovery** - Users can't find relevant options quickly
5. **Wasted space** - Plot-specific groups empty for most plot types

## Goals
1. Reduce visible options by 60-70% through context-aware filtering
2. Improve visual hierarchy and scannability
3. Maintain full functionality for power users
4. Zero regression in existing workflows

## Non-Goals
- Complete UI framework change (staying with tkinter)
- Changing the underlying options data structures
- Adding new plot types or options

---

## Proposed Changes

### 1. Context-Aware Option Visibility (P0)
**Problem**: All 12 option groups shown regardless of plot type.

**Solution**: Show only relevant groups based on selected `kind`.

```python
PLOT_TYPE_GROUPS = {
    'line':       ['general', 'data', 'axes', 'sizes', 'formats', 'colors'],
    'scatter':    ['general', 'data', 'axes', 'sizes', 'formats', 'colors'],
    'bar':        ['general', 'data', 'axes', 'sizes', 'formats', 'colors'],
    'barh':       ['general', 'data', 'axes', 'sizes', 'formats', 'colors'],
    'histogram':  ['general', 'data', 'axes', 'colors', 'density'],
    'density':    ['general', 'data', 'axes', 'colors', 'density'],
    'boxplot':    ['general', 'data', 'axes', 'formats'],
    'violinplot': ['general', 'data', 'axes', 'formats'],
    'heatmap':    ['general', 'axes', 'colors'],
    'pie':        ['general', 'data', 'colors'],
    'shmoo':      ['general', 'shmoo', 'colors'],
    'bathtub':    ['general', 'bathtub'],
    'sparam':     ['general', 'sparam'],
    'gantt':      ['general', 'gantt'],
    'eye':        ['general', 'eye'],
    'jitter':     ['general', 'jitter'],
    # ... remaining types
}
```

**Implementation**:
- Add `update_visible_groups(kind)` method to `MPLBaseOptions`
- Bind to `kind` combobox `<<ComboboxSelected>>` event
- Use `pack_forget()` / `pack()` to show/hide group frames

**Impact**: Reduces visible controls from ~50 to ~15-20 for common plot types.

---

### 2. Vertical Group Layout (P1)
**Problem**: Horizontal packing creates cramped, uneven layout.

**Solution**: Switch to vertical stacking with consistent widths.

**Before**:
```
[general][data][axes][sizes][formats][colors][density][shmoo][bathtub]...
```

**After**:
```
┌─ general ─────────────┐
│ plot type: [line ▼]   │
│ bins: [20]            │
│ ☐ stacked             │
└───────────────────────┘
┌─ data ────────────────┐
│ group by: [     ▼]    │
│ group by 2: [   ▼]    │
└───────────────────────┘
```

**Implementation**:
- Modify `dialogFromOptions()` to use `layout='vertical'` for Base Options
- Set consistent `width` for all entry/combobox widgets
- Add `pady=4` between groups

---

### 3. Collapsible Sections (P1)
**Problem**: Even with filtering, some groups may be rarely used.

**Solution**: Add expand/collapse toggle to each LabelFrame.

**Implementation**:
```python
class CollapsibleLabelFrame(ttk.LabelFrame):
    def __init__(self, parent, text, **kwargs):
        super().__init__(parent, text=f"▼ {text}", **kwargs)
        self.expanded = True
        self.content = ttk.Frame(self)
        self.bind("<Button-1>", self.toggle)
    
    def toggle(self, event=None):
        self.expanded = not self.expanded
        if self.expanded:
            self.content.pack(fill='both', expand=True)
            self.configure(text=f"▼ {self.base_text}")
        else:
            self.content.pack_forget()
            self.configure(text=f"▶ {self.base_text}")
```

---

### 4. Improved Widget Alignment (P2)
**Problem**: Labels and widgets misaligned, inconsistent sizing.

**Solution**: Use grid layout within groups.

```python
# Inside each group frame
label.grid(row=i, column=0, sticky='w', padx=5, pady=2)
widget.grid(row=i, column=1, sticky='ew', padx=5, pady=2)
frame.columnconfigure(1, weight=1)
```

**Consistent widths**:
- Entry fields: `width=10`
- Comboboxes: `width=16`
- Scales: `length=120`

---

### 5. Quick Search Filter (P2)
**Problem**: Hard to find specific options.

**Solution**: Add search box that filters visible options.

```
🔍 [Search options...        ]

┌─ axes ────────────────┐
│ ☑ show grid           │  ← matches "grid"
└───────────────────────┘
```

**Implementation**:
- Add `Entry` at top of options panel
- Filter options by matching label text
- Show only groups containing matches

---

## Implementation Plan

| Phase | Task | Effort | Files |
|-------|------|--------|-------|
| 1 | Context-aware group visibility | 2h | `plotting.py` |
| 2 | Vertical layout for Base Options | 1h | `dialogs.py` |
| 3 | Collapsible sections | 2h | `dialogs.py` |
| 4 | Grid alignment within groups | 1h | `dialogs.py` |
| 5 | Search filter | 2h | `plotting.py` |

**Total estimated effort**: 8 hours

---

## Success Metrics
1. **Visible controls reduced** by 60%+ for common plot types
2. **Time to find option** reduced (qualitative user feedback)
3. **No regressions** in existing plot functionality

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing saved settings | Preserve `kwds` structure unchanged |
| Performance on show/hide | Use `pack_forget()` not widget destruction |
| User confusion from hidden options | Add "Show all options" toggle |

---

## Open Questions
1. Should collapsed state persist across sessions?
2. Should we add presets (e.g., "Simple", "Advanced" mode)?
3. Priority of search filter vs. collapsible sections?

---

## Appendix: Current Group Structure

```python
groups = {
    'general':  ['kind', 'bins', 'hist_min', 'hist_max', 'stacked', 'subplots', 'use_index', 'errorbars'],
    'data':     ['by', 'by2', 'labelcol', 'pointsizes'],
    'axes':     ['grid', 'legend', 'showxlabels', 'showylabels', 'sharex', 'sharey', 'logx', 'logy'],
    'sizes':    ['fontsize', 'ms', 'linewidth'],
    'formats':  ['font', 'marker', 'linestyle', 'alpha'],
    'colors':   ['colormap', 'bw', 'clrcol', 'cscale', 'colorbar'],
    'density':  ['bw_method', 'fill', 'show_rug'],
    'shmoo':    ['show_values', 'log_z_scale', 'x_param', 'y_param', 'z_param', ...],
    'bathtub':  ['ber_target', 'show_margins', 'x_axis_type', ...],
    'sparam':   ['log_freq', 'show_phase', 'spec_limit', ...],
    'gantt':    ['show_progress', 'show_today', 'date_format', ...],
    'eye':      ['persistence', 'ui_width', 'sample_rate', ...],
    'jitter':   ['bins', 'show_stats', 'show_gaussian', ...],
}
```
