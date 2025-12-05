# CSV Browser: Web vs Desktop Comparison

## Overview

| Aspect | Web (Streamlit) | Desktop (Tkinter) |
|--------|-----------------|-------------------|
| **File** | `app.py` (~223 lines) | `csv_browser_v6.x1.2_search_columns.py` (~5952 lines) |
| **Framework** | Streamlit | Tkinter + pandastable |
| **Lines of Code** | ~220 | ~6000 |
| **Deployment** | Browser-based | Native desktop |

---

## Feature Comparison

### File Browser

| Feature | Web | Desktop |
|---------|-----|---------|
| Directory browsing | ✅ Text input | ✅ Dialog + recent directories |
| File filtering | ✅ Basic (include/exclude) | ✅ Advanced (AND, exclude with `!`) |
| File metadata display | ✅ Name, Size, Modified | ✅ Name, Size, Modified + parsed filename fields |
| Subfolder scanning | ❌ | ✅ Load Subfolders button |
| Recent directories | ❌ | ✅ Persisted menu |
| Save/Load file filters | ❌ | ✅ |

### Data Viewing

| Feature | Web | Desktop |
|---------|-----|---------|
| Table display | ✅ Streamlit dataframe | ✅ pandastable (Excel-like) |
| Row filtering | ✅ Query + text + `@` separator | ✅ Query + text + `@` + wildcards |
| Column filtering | ✅ Basic | ✅ Advanced (quotes, `!`, `*` wildcard) |
| Column search | ❌ | ✅ Fuzzy matching + highlight |
| Move column to start | ❌ | ✅ |
| Save filtered data | ❌ | ✅ Save to CSV button |
| Save/Load filters | ❌ | ✅ Persistent filter presets |

### Plotting

| Feature | Web | Desktop |
|---------|-----|---------|
| **General Plots** | | |
| Scatter | ✅ | ✅ |
| Line | ✅ | ✅ |
| Histogram | ✅ | ✅ |
| Bar | ✅ | ✅ |
| **Special Plots** | | |
| Shmoo Plot | ✅ Basic | ✅ Full (thresholds, stats, values) |
| Bathtub Curve | ✅ Basic | ✅ Full |
| Eye Diagram | ✅ Basic | ✅ Full |
| **Correlation Analysis** | | |
| Top N correlations | ✅ | ✅ |
| Correlation plot | ✅ Single | ✅ Multiple + save to file |
| **Plot Settings** | | |
| Save/Load settings | ❌ | ✅ JSON file persistence |
| Interactive options | ❌ | ✅ Full pandastable plot viewer |

### File Operations

| Feature | Web | Desktop |
|---------|-----|---------|
| Move files | ❌ | ✅ |
| Copy files | ❌ | ✅ |
| Delete files | ❌ | ✅ (Recycle Bin) |
| Rename files | ❌ | ✅ Based on field values |
| Merge CSV files | ❌ | ✅ |
| Open in Excel | ❌ | ✅ |
| Open in Spotfire | ❌ | ✅ (with long path handling) |
| Reveal in Explorer | ❌ | ✅ |

### UI/UX

| Feature | Web | Desktop |
|---------|-----|---------|
| Layout options | ❌ Fixed | ✅ Horizontal/Vertical toggle |
| Keyboard shortcuts | ❌ | ✅ Ctrl+F, Ctrl+O, Ctrl+R, Escape, F5 |
| Tooltips | ❌ | ✅ Comprehensive |
| Context menus | ❌ | ✅ Right-click menus |
| Status bar | ❌ | ✅ |
| Settings persistence | ❌ | ✅ JSON file |

### Data Handling

| Feature | Web | Desktop |
|---------|-----|---------|
| Encoding fallbacks | ✅ Multiple | ✅ Multiple |
| Long path support | ❌ | ✅ Windows `\\?\` prefix |
| Index preservation | ❌ | ✅ Complex index handling |
| Table settings save | ❌ | ✅ Column widths, order, sort |

---

## Summary

### Web Version Strengths

- **Simple deployment** — runs in any browser
- **Quick setup** — `streamlit run app.py`
- **Clean UI** — modern Streamlit components
- **Cross-platform** — works anywhere with a browser

### Desktop Version Strengths

- **Feature-rich** — 25x more code, many more features
- **File operations** — move, copy, delete, merge, rename
- **External app integration** — Excel, Spotfire
- **Advanced filtering** — complex query syntax, wildcards
- **Persistence** — settings, filters, plot configurations saved
- **Keyboard shortcuts** — power user workflow
- **Filename parsing** — dynamic columns from filename structure

### Recommended Use Cases

| Use Case | Recommended Version |
|----------|---------------------|
| Quick data exploration | Web |
| Sharing with team | Web |
| Power user workflow | Desktop |
| File management tasks | Desktop |
| Complex filtering needs | Desktop |
| Integration with other tools | Desktop |

## Detailed Plotting Differences

### Streamlit (web) implementation

1. **Fixed plot palette** – Users pick one plot at a time from a small set (Scatter/Line/Histogram/Bar) or run pre-built correlation/special plots without further customization, and pressing each "Generate" button renders a fresh Matplotlib figure with no persistent options or subplot layout controls. (See @app.py#126-219)
2. **Simple data binding** – Inputs directly map to columns chosen via `selectbox`/`multiselect`, and the helper functions simply coerce columns to numeric before calling Matplotlib (e.g., `plot_scatter`, `plot_line`). There is no awareness of PlotViewer state, column persistence, or interactive zoom/pan controls beyond what Matplotlib provides by default. (See @plotting_utils.py#174-216)
3. **No state retention** – After switching files or plots, column selections and plot settings are lost; there is no saving/restoring of PlotViewer configuration because Streamlit recreates figures on demand and discards them immediately.

### Desktop (Tkinter + pandastable) implementation

1. **PlotUtils + mixins** – The desktop app wraps pandastable's `PlotViewer` through `PlotMethodsMixin` and `PlotUtils`, enabling save/restore of global/matplotlib/3D/label options, automatic column persistence, and monkey-patching of `showPlot` so every plot honors the saved configuration.@examples/csv_browser/csv_browser_plot_methods.py#5-40 @examples/csv_browser/csv_browser_combined.py#142-155
2. **Safe replot & column-aware plotting** – `_safe_replot_with_index_preservation` ensures selected columns remain valid after column filtering, preserves DataFrame indices, and retriggers plots with the correct column list rather than re-deriving inputs each time.@examples/csv_browser/plot_utils.py#242-460
3. **Toolbar & viewer controls** – The Tkinter viewer inherits pandastable's interactive toolbar (zoom, pan, hover annotations, scroll zoom, right-click pan), giving much richer interaction than the static Streamlit figures.@pandastable/plotting.py#504-858
4. **Workflow integration** – Toolbar buttons (e.g., "Save Plot Settings", "Load Plot Settings", "Correlation Analysis") sit alongside file operations, so plots can be generated, tweaked, saved, and restored as part of the same desktop workflow.@examples/csv_browser_v6.x1.2_search_columns.py#2042-2119
