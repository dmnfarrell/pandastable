# Getting Started with Streamlit CSV Browser

Your workspace contains a Streamlit-based CSV browser application. Here's how to get started:

## Quick Start

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app:**

   ```bash
   streamlit run app.py
   ```

## Application Structure

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit application |
| `utils.py` | CSV loading and filtering utilities |
| `plotting_utils.py` | Plotting functions (scatter, line, shmoo, bathtub, etc.) |
| `requirements.txt` | Dependencies (streamlit, pandas, matplotlib, scipy, numpy, plotly) |

## Features

- **File Browser** — Browse and select CSV/TSV files from sidebar
- **Row Filtering** — Query syntax (`col > 10`), text search, or combined (`col > 10 @ error`)
- **Column Filtering** — Space-separated terms, `!exclude`, `*wildcard`
- **General Plots** — Scatter, Line, Histogram, Bar
- **Correlation Analysis** — Find top correlated columns with a target
- **Special Plots** — Shmoo, Bathtub curves, Eye diagrams

## Usage Tips

- Enter a directory path in the sidebar to browse CSV files
- Use the filter input to narrow down files (supports `!exclude` syntax)
- Click a file to load it
- Apply row/column filters in the expander
- Use the plotting tabs to visualize data
