# dataPlot Studio

[![PyPI version shields.io](https://img.shields.io/pypi/v/pandastable.svg)](https://pypi.python.org/pypi/pandastable/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

## Why dataPlot Studio?

- **Desktop parity in the browser** – Move/copy/rename/delete/merge files, apply saved filters, and launch external apps directly from the UI.
- **Column-aware CSV viewer** – Per-file column layouts, move-to-front controls, saved presets, row/column filters, frozen headers, and zoom controls.
- **Plotting power** – Scatter/line/density/bar/box/violin/dot/heatmap and specialty plots (3D, Gantt, jitter, phase-noise, S-parameters, TDR) with grouping, subplots, and Plotly interactivity (zoom/pan/hover).
- **RF & Touchstone workflows** – Upload `.s2p/.s4p` files, compute derived metrics, run ICZT-based TDR, view Smith charts, and export traces.
- **Persistent state** – Plot settings, filters, column layouts, and saved presets are stored per file/session via `plot_state.py` and `settings_store.py`.

## Quick Start

```bash
git clone <repo-url> dataplot-studio
cd dataplot-studio
python -m venv .venv && .venv\Scripts\activate  # PowerShell on Windows
pip install -r requirements.txt
streamlit run app.py
```

1. Use the sidebar to pick a working directory (recent + saved filters are restored).
2. Select files from the file browser table and open them in the CSV viewer.
3. Configure filters, column layouts, and plotting state; settings persist automatically.
4. Use “General Plots” or “Special Plots” tabs to generate interactive Plotly views, grouped subplots, and RF-focused charts.

## Repository Layout

| Path | Description |
|------|-------------|
| `app.py` | Main Streamlit app: layout, file browser, CSV viewer, plotting UI, and file operations. |
| `plotting_utils.py` | Matplotlib-based plotting helpers reused by the web app (converted to Plotly at render time). |
| `plot_state.py` | Default plot state schema + persistence helper. |
| `settings_store.py` | Saved filters, recent directories, column presets, and other user settings. |
| `file_ops.py` | Copy/move/rename/delete/merge/open-in helpers with Windows/macOS support. |
| `test_app_logic.py` | Regression tests for filters, correlation plots, file ops, and Plotly conversion fallbacks. |
| `examples/` | Legacy desktop CSV Browser code and reference scripts for migration parity. |

## Feature Highlights

### File Browser & Operations

- Multi-select copy/move/delete/rename with templates, merge CSVs, and “Open in” Excel/Spotfire.
- Include/exclude filters, size/date ranges, saved presets, and per-user recent directories.

### Column-Aware CSV Viewer

- Preserve column order per file, move columns to front, reset to original, and save named presets.
- Apply column filters with wildcards/exclusions and desktop-style row filter syntax (`query`, free text, wildcards, `@`).
- Frozen header toggle, adjustable font scale/height, and export filtered data.

### Plotting & Analysis

see the [docs](https://pandastable.readthedocs.io/en/latest/description.html#installation) for more details on installing.

## Current features

* add, remove rows and columns
* spreadsheet-like drag, shift-click, ctrl-click selection
* edit individual cells
* sort by column, rename columns
* reorder columns dynamically by mouse drags
* set some basic formatting such as font, text size and column width
* save the DataFrame to supported pandas formats
* import/export of supported text files
* rendering of very large tables is only memory limited
* interactive plots with matplotlib, mostly using the pandas plot functions
* basic table manipulations like aggregate and pivot
* filter table using built in dataframe functionality
* graphical way to perform split-apply-combine operations

- [CSV Browser → dataPlot Studio Migration PRD](CSV_BROWSER_WEB_MIGRATION_PRD.md)
- [Touchstone & S-Parameter Guide](TOUCHSTONE_SUPPORT.md)
- [Plotting Guides (3D, Shmoo, Density, Gantt, etc.)](./)

## Contributing

1. Fork + clone the repository.
2. Install dev dependencies: `pip install -r requirements-dev.txt` (if available).
3. Run tests: `python -m pytest test_app_logic.py -v`.
4. Use the configured formatters/linters before submitting PRs.

## Legacy Notes

This repository previously hosted the `pandastable` Tkinter widget and the desktop CSV Browser app. The legacy sources remain under `examples/` for reference while the active development target is the **dataPlot Studio** Streamlit experience.
