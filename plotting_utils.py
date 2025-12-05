import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pandas import plotting as pd_plotting
from matplotlib import patches
from matplotlib import dates as mdates
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 - needed for 3D projection
from scipy import stats, interpolate
from scipy.optimize import curve_fit
import matplotlib.patheffects as patheffects
import re
from pathlib import Path


TOUCHSTONE_FREQ_MULTIPLIERS = {
    "hz": 1.0,
    "khz": 1e3,
    "mhz": 1e6,
    "ghz": 1e9,
}

TOUCHSTONE_DISPLAY_MODES = {
    "mag_db": "Magnitude (dB)",
    "mag_linear": "Magnitude (Linear)",
    "phase_deg": "Phase (Degrees)",
}


AGG_MAP = {
    "sum": pd.Series.sum,
    "mean": pd.Series.mean,
    "median": pd.Series.median,
    "count": pd.Series.count,
}


def _aggregate_series(df, category_col, value_col, agg_method):
    if category_col is None or value_col is None:
        raise ValueError("Category and value columns are required")
    if category_col not in df.columns or value_col not in df.columns:
        raise ValueError("Selected columns are missing from the DataFrame")
    grouped = df.groupby(category_col)[value_col]
    func = AGG_MAP.get(agg_method.lower())
    if func is None:
        raise ValueError(f"Unsupported aggregation: {agg_method}")
    result = func(grouped).sort_values(ascending=False)
    return result.dropna()

def get_numeric_varying_columns(data):
    """Get list of numeric columns with variation."""
    numeric_columns = []
    for col in data.columns:
        numeric_series = pd.to_numeric(data[col], errors='coerce')
        if not numeric_series.isna().all() and numeric_series.nunique() > 1:
            numeric_columns.append(col)
    return numeric_columns

def get_top_correlated_columns(data, target_column, top_n=10):
    """Get top N correlated columns."""
    if target_column not in data.columns:
        return None, None

    numeric_data = data.apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all')
    non_constant_data = numeric_data.loc[:, numeric_data.nunique() > 1]

    if target_column not in non_constant_data.columns:
        return None, None

    cor_matrix = non_constant_data.corr()
    cor_target = cor_matrix[target_column]

    cor_target_df = pd.DataFrame({
        'Column': cor_target.index,
        'Correlation': cor_target.values
    })

    top_correlated = cor_target_df[cor_target_df['Column'] != target_column] \
        .sort_values(by='Correlation', key=abs, ascending=False) \
        .head(top_n)

    return top_correlated, data

def plot_correlation(data, target_col, corr_col, corr_val):
    """Create a single correlation plot."""
    fig, ax = plt.subplots(figsize=(10, 6))

    x_data = pd.to_numeric(data[target_col], errors='coerce')
    y_data = pd.to_numeric(data[corr_col], errors='coerce')

    mask = ~(np.isnan(x_data) | np.isnan(y_data))
    x_data = x_data[mask]
    y_data = y_data[mask]

    ax.scatter(x_data, y_data, alpha=0.5)

    if len(x_data) > 1:
        z = np.polyfit(x_data, y_data, 1)
        p = np.poly1d(z)
        x_range = np.linspace(x_data.min(), x_data.max(), 100)
        ax.plot(x_range, p(x_range), "r--", alpha=0.8, linewidth=2)

    ax.set_xlabel(target_col)
    ax.set_ylabel(corr_col)
    ax.set_title(f'Correlation: {corr_val:.3f}')
    ax.grid(True, alpha=0.3, linestyle='--')

    return fig


def plot_jitter(df, column, bins=50, show_gaussian=True, show_stats=True):
    series = pd.to_numeric(df[column], errors='coerce').dropna()
    if series.empty:
        raise ValueError("Selected column has no numeric data for jitter plot")

    fig, ax = plt.subplots()
    counts, edges, _ = ax.hist(series, bins=bins, alpha=0.6, label='Histogram')
    ax.set_xlabel(column)
    ax.set_ylabel('Count')
    ax.set_title('Jitter Histogram')

    if show_gaussian and len(series) > 1:
        mean = series.mean()
        std = series.std()
        x = np.linspace(edges[0], edges[-1], 500)
        gaussian = (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2)
        gaussian *= series.size * (edges[1] - edges[0])
        ax.plot(x, gaussian, 'r--', label='Gaussian Fit')
    if show_stats:
        stats_text = f"Mean: {series.mean():.3g}\nStd Dev: {series.std():.3g}\nMin/Max: {series.min():.3g} / {series.max():.3g}"
        ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, ha='right', va='top',
                bbox=dict(facecolor='white', alpha=0.8))
    ax.legend()
    return fig


def plot_phase_noise(df, freq_col, noise_col, carrier_hz=1e9):
    freq = pd.to_numeric(df[freq_col], errors='coerce').dropna()
    noise = pd.to_numeric(df[noise_col], errors='coerce').dropna()
    min_len = min(len(freq), len(noise))
    if min_len < 2:
        raise ValueError("Not enough data for phase noise plot")
    freq = freq.iloc[:min_len]
    noise = noise.iloc[:min_len]

    fig, ax = plt.subplots()
    ax.plot(freq, noise, marker='o', linestyle='-')
    ax.set_xscale('log')
    ax.set_xlabel('Offset Frequency (Hz)')
    ax.set_ylabel('Phase Noise (dBc/Hz)')
    ax.set_title(f'Phase Noise @ {carrier_hz/1e9:.3g} GHz')
    ax.grid(True, which='both', linestyle='--', alpha=0.3)
    return fig


def load_touchstone(source):
    """Load a Touchstone .sNp file into a structured dictionary."""
    if hasattr(source, 'read'):
        raw = source.read()
        try:
            source.seek(0)
        except Exception:
            pass
        filename = getattr(source, 'name', 'uploaded.s2p')
    else:
        path = Path(source)
        filename = path.name
        raw = path.read_bytes()
    if isinstance(raw, str):
        text = raw
    else:
        text = raw.decode('utf-8', errors='ignore')
    return _parse_touchstone_text(text, filename)


def _parse_touchstone_text(text, filename):
    freq_unit = 'hz'
    data_format = 'ma'
    parameter = 's'
    reference = 50.0
    data_tokens = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('!'):
            continue
        if line.startswith('#'):
            tokens = line[1:].strip().split()
            skip_next = False
            for idx, token in enumerate(tokens):
                if skip_next:
                    skip_next = False
                    continue
                lower = token.lower()
                if lower in TOUCHSTONE_FREQ_MULTIPLIERS:
                    freq_unit = lower
                elif lower in {'s', 'y', 'z', 'h', 'g'}:
                    parameter = lower
                elif lower in {'ma', 'db', 'ri'}:
                    data_format = lower
                elif lower == 'r' and idx + 1 < len(tokens):
                    try:
                        reference = float(tokens[idx + 1])
                    except ValueError:
                        pass
                    skip_next = True
            continue

        if '!' in line:
            line = line.split('!')[0].strip()
        if not line:
            continue
        data_tokens.extend(line.split())

    if parameter != 's':
        raise ValueError("Touchstone file must contain S-parameters")
    if not data_tokens:
        raise ValueError("No numeric data found in Touchstone file")

    float_values = []
    for token in data_tokens:
        normalized = token.replace('D', 'E').replace('d', 'e')
        try:
            float_values.append(float(normalized))
        except ValueError:
            raise ValueError(f"Invalid numeric token '{token}' in Touchstone file")

    port_count = _infer_touchstone_ports(filename, len(float_values))
    row_len = 1 + 2 * port_count * port_count
    if len(float_values) % row_len != 0:
        raise ValueError("Touchstone data length does not match expected row size")

    freq_values = []
    matrices = []
    idx = 0
    while idx < len(float_values):
        freq_values.append(float_values[idx])
        idx += 1
        complex_entries = []
        for _ in range(port_count * port_count):
            v1 = float_values[idx]
            v2 = float_values[idx + 1]
            idx += 2
            complex_entries.append(_touchstone_pair_to_complex(v1, v2, data_format))
        matrices.append(np.array(complex_entries).reshape(port_count, port_count))

    return {
        "frequency": np.array(freq_values),
        "freq_unit": freq_unit.upper(),
        "format": data_format.upper(),
        "matrix": np.array(matrices),
        "ports": port_count,
        "reference": reference,
        "filename": filename,
    }


def _infer_touchstone_ports(filename, token_count):
    match = re.search(r's(\d+)p$', filename.lower())
    if match:
        return int(match.group(1))
    for candidate in range(1, 11):
        row_len = 1 + 2 * candidate * candidate
        if token_count % row_len == 0:
            return candidate
    raise ValueError("Unable to infer number of ports from Touchstone file")


def _touchstone_pair_to_complex(value1, value2, data_format):
    fmt = data_format.lower()
    if fmt == 'ri':
        return complex(value1, value2)
    angle_rad = np.deg2rad(value2)
    if fmt == 'ma':
        magnitude = value1
    elif fmt == 'db':
        magnitude = 10 ** (value1 / 20.0)
    else:
        raise ValueError(f"Unsupported Touchstone data format: {data_format}")
    return magnitude * (np.cos(angle_rad) + 1j * np.sin(angle_rad))


def get_sparameter_labels(touchstone_data):
    ports = touchstone_data.get('ports', 0)
    return [f"S{i}{j}" for i in range(1, ports + 1) for j in range(1, ports + 1)]


def plot_s_parameters(touchstone_data, selections, display_mode='mag_db', log_freq=False):
    if not selections:
        raise ValueError("Select at least one S-parameter to plot")
    freq = touchstone_data['frequency']
    freq_label = touchstone_data.get('freq_unit', 'Hz')
    matrix = touchstone_data['matrix']
    ports = touchstone_data['ports']

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, j in selections:
        if not (1 <= i <= ports and 1 <= j <= ports):
            raise ValueError(f"S-parameter S{i}{j} is out of range for a {ports}-port file")
        trace = matrix[:, i - 1, j - 1]
        if display_mode == 'mag_db':
            ylabel = TOUCHSTONE_DISPLAY_MODES['mag_db']
            magnitude = np.maximum(np.abs(trace), 1e-12)
            y_values = 20 * np.log10(magnitude)
        elif display_mode == 'mag_linear':
            ylabel = TOUCHSTONE_DISPLAY_MODES['mag_linear']
            y_values = np.abs(trace)
        elif display_mode == 'phase_deg':
            ylabel = TOUCHSTONE_DISPLAY_MODES['phase_deg']
            y_values = np.angle(trace, deg=True)
        else:
            raise ValueError(f"Unsupported display mode: {display_mode}")
        ax.plot(freq, y_values, label=f"S{i}{j}")

    ax.set_xlabel(f"Frequency ({freq_label})")
    if log_freq:
        ax.set_xscale('log')
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend()
    ax.set_title('S-Parameter Plot')
    return fig

# --- Ported Special Plots from pandastable/plotting.py ---

def plot_shmoo(df, x_param, y_param, z_param, threshold_min=None, threshold_max=None,
               log_z=False, show_stats=True, show_values=False):
    """Shmoo Plot."""
    fig, ax = plt.subplots(figsize=(10, 8))

    data = df[[x_param, y_param, z_param]].apply(pd.to_numeric, errors='coerce').dropna()
    x = data[x_param].values
    y = data[y_param].values
    z = data[z_param].values

    if log_z:
        z_plot = np.log10(np.where(z > 0, z, np.nan))
        label = f'log10({z_param})'
    else:
        z_plot = z
        label = z_param

    # Check for regular grid
    x_unique = np.unique(x)
    y_unique = np.unique(y)

    if len(x) == len(x_unique) * len(y_unique):
        # Regular grid
        X, Y = np.meshgrid(x_unique, y_unique)
        Z = np.full((len(y_unique), len(x_unique)), np.nan)

        x_idx = {val: i for i, val in enumerate(x_unique)}
        y_idx = {val: i for i, val in enumerate(y_unique)}

        for xi, yi, zi in zip(x, y, z_plot):
            Z[y_idx[yi], x_idx[xi]] = zi

        mesh = ax.pcolormesh(X, Y, Z, shading='auto', cmap='RdYlGn')
        fig.colorbar(mesh, ax=ax, label=label)
    else:
        # Scatter
        if threshold_min is not None and threshold_max is not None:
            colors = np.where((z >= threshold_min) & (z <= threshold_max), 'green', 'red')
            sc = ax.scatter(x, y, c=colors, s=50, edgecolors='black', linewidth=0.5)
        else:
            sc = ax.scatter(x, y, c=z_plot, cmap='RdYlGn', s=50, edgecolors='black', linewidth=0.5)
            fig.colorbar(sc, ax=ax, label=label)

    ax.set_xlabel(x_param)
    ax.set_ylabel(y_param)
    ax.set_title(f'Shmoo Plot: {label}')

    if show_stats and threshold_min is not None and threshold_max is not None:
        pass_count = np.sum((z >= threshold_min) & (z <= threshold_max))
        total = len(z)
        rate = 100 * pass_count / total if total > 0 else 0
        stats_text = f"Pass: {pass_count}/{total} ({rate:.1f}%)"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                bbox=dict(facecolor='white', alpha=0.8), va='top')

    if show_values:
        for xi, yi, zi in zip(x, y, z):
            ax.text(xi, yi, f'{zi:.2g}', ha='center', va='center', fontsize=8)

    return fig

def plot_bathtub(df, x_col, y_cols, ber_target=1e-12):
    """Bathtub Plot."""
    fig, ax = plt.subplots(figsize=(10, 6))

    for y_col in y_cols:
        data = df[[x_col, y_col]].apply(pd.to_numeric, errors='coerce').dropna()
        data = data.sort_values(x_col)
        ax.semilogy(data[x_col], data[y_col], 'o-', label=y_col)

    ax.axhline(ber_target, color='gray', linestyle='--', label=f'Target BER: {ber_target}')
    ax.set_xlabel(x_col)
    ax.set_ylabel('BER')
    ax.set_title('Bathtub Curve')
    ax.grid(True, which='both', alpha=0.3)
    ax.legend()

    return fig

def plot_eye(df, time_col, voltage_col, ui_width=1.0, persistence=100):
    """Eye Diagram."""
    fig, ax = plt.subplots(figsize=(10, 6))

    data = df[[time_col, voltage_col]].apply(pd.to_numeric, errors='coerce').dropna()
    t = data[time_col].values
    v = data[voltage_col].values

    # Estimate UI
    time_span = t[-1] - t[0]
    estimated_uis = max(10, int(time_span / (t[1] - t[0]) / 10))
    ui_period = (time_span / estimated_uis) * ui_width

    t_norm = (t - t[0]) % ui_period

    h, xedges, yedges = np.histogram2d(t_norm, v, bins=persistence)
    ax.imshow(h.T, extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
              origin='lower', aspect='auto', cmap='hot', interpolation='bilinear')

    ax.set_xlabel('Time (UI)')
    ax.set_ylabel('Voltage')
    ax.set_title('Eye Diagram')

    return fig

def plot_histogram(df, col, bins=50):
    fig, ax = plt.subplots()
    data = pd.to_numeric(df[col], errors='coerce').dropna()
    ax.hist(data, bins=bins, edgecolor='black', alpha=0.7)
    ax.set_xlabel(col)
    ax.set_ylabel('Frequency')
    ax.set_title(f'Histogram of {col}')
    return fig

def plot_scatter(df, x_col, y_col, color_col=None):
    fig, ax = plt.subplots()
    x = pd.to_numeric(df[x_col], errors='coerce')
    y = pd.to_numeric(df[y_col], errors='coerce')

    c = None
    if color_col:
        c = pd.to_numeric(df[color_col], errors='coerce')

    sc = ax.scatter(x, y, c=c, cmap='viridis' if c is not None else None, alpha=0.6)
    if c is not None:
        fig.colorbar(sc, label=color_col)

    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(f'{y_col} vs {x_col}')
    return fig

def plot_line(df, x_col, y_cols):
    fig, ax = plt.subplots()
    x = pd.to_numeric(df[x_col], errors='coerce')

    for y_col in y_cols:
        y = pd.to_numeric(df[y_col], errors='coerce')
        # Sort by x for line plot
        mask = ~(np.isnan(x) | np.isnan(y))
        sorted_indices = np.argsort(x[mask])
        ax.plot(x[mask].iloc[sorted_indices], y[mask].iloc[sorted_indices], label=y_col)

    ax.set_xlabel(x_col)
    ax.legend()
    ax.set_title('Line Plot')
    return fig


def plot_barh(df, category_col, value_col, agg_method):
    data = _aggregate_series(df, category_col, value_col, agg_method)
    fig, ax = plt.subplots()
    data.sort_values().plot.barh(ax=ax)
    ax.set_xlabel(f"{value_col} ({agg_method})")
    ax.set_ylabel(category_col)
    ax.set_title('Horizontal Bar Plot')
    return fig


def plot_pie(df, category_col, value_col, agg_method):
    data = _aggregate_series(df, category_col, value_col, agg_method)
    if data.empty:
        raise ValueError("No data available for pie chart")
    fig, ax = plt.subplots()
    ax.pie(data.values, labels=data.index, autopct='%1.1f%%', startangle=90)
    ax.set_title('Pie Chart')
    ax.axis('equal')
    return fig


def plot_box(df, columns):
    numeric = df[columns].apply(pd.to_numeric, errors='coerce').dropna(how='all')
    if numeric.empty:
        raise ValueError("Selected columns have no numeric data")
    fig, ax = plt.subplots()
    numeric.plot.box(ax=ax)
    ax.set_title('Box Plot')
    return fig


def plot_violin(df, columns):
    numeric = df[columns].apply(pd.to_numeric, errors='coerce').dropna()
    if numeric.empty:
        raise ValueError("Selected columns have no numeric data")
    fig, ax = plt.subplots()
    ax.violinplot([numeric[col].dropna().values for col in numeric.columns], showmeans=True)
    ax.set_xticks(range(1, len(numeric.columns) + 1))
    ax.set_xticklabels(numeric.columns, rotation=45, ha='right')
    ax.set_title('Violin Plot')
    return fig


def plot_density(df, columns, bw_method='scott', fill=False, show_rug=False):
    numeric = df[columns].apply(pd.to_numeric, errors='coerce')
    fig, ax = plt.subplots()
    for col in numeric.columns:
        series = numeric[col].dropna()
        if series.empty:
            continue
        try:
            bw = float(bw_method)
        except (ValueError, TypeError):
            bw = bw_method
        kde = stats.gaussian_kde(series, bw_method=bw)
        x_grid = np.linspace(series.min(), series.max(), 500)
        y = kde(x_grid)
        ax.plot(x_grid, y, label=col)
        if fill:
            ax.fill_between(x_grid, y, alpha=0.2)
        if show_rug:
            ax.plot(series, np.full_like(series, -0.005), '|', color=ax.lines[-1].get_color())
    ax.set_title('Density Plot')
    ax.legend()
    return fig


def _prepare_3d_numeric(df, x_col, y_col, z_col, log_z=False):
    cols = [x_col, y_col, z_col]
    numeric = df[cols].apply(pd.to_numeric, errors='coerce').dropna()
    if numeric.empty:
        raise ValueError("Selected columns do not contain enough numeric data")
    x = numeric[x_col].values
    y = numeric[y_col].values
    z = numeric[z_col].values
    if log_z:
        positive_mask = z > 0
        if not np.any(positive_mask):
            raise ValueError("Log-scale requested but Z column has no positive values")
        z = np.where(positive_mask, np.log10(z), np.nan)
        z = np.nan_to_num(z, nan=np.nanmin(z[np.isfinite(z)]) if np.isfinite(z).any() else 0)
        label = f"log10({z_col})"
    else:
        label = z_col
    return x, y, z, label


def _build_3d_grid(x, y, z, grid_resolution=40):
    points = np.column_stack((x, y))
    grid_x = np.linspace(np.nanmin(x), np.nanmax(x), grid_resolution)
    grid_y = np.linspace(np.nanmin(y), np.nanmax(y), grid_resolution)
    grid_xx, grid_yy = np.meshgrid(grid_x, grid_y)
    grid_z = interpolate.griddata(points, z, (grid_xx, grid_yy), method='cubic')
    if np.isnan(grid_z).all():
        grid_z = interpolate.griddata(points, z, (grid_xx, grid_yy), method='linear')
    if np.isnan(grid_z).all():
        grid_z = interpolate.griddata(points, z, (grid_xx, grid_yy), method='nearest')
    if np.isnan(grid_z).all():
        raise ValueError("Unable to interpolate surface for given data")
    return grid_xx, grid_yy, grid_z


def plot_scatter3d(df, x_col, y_col, z_col, colormap='viridis', log_z=False):
    x, y, z, label = _prepare_3d_numeric(df, x_col, y_col, z_col, log_z=log_z)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    sc = ax.scatter(x, y, z, c=z, cmap=colormap, depthshade=True, alpha=0.8)
    fig.colorbar(sc, ax=ax, label=label)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_zlabel(label)
    ax.set_title('3D Scatter Plot')
    return fig


def plot_surface3d(df, x_col, y_col, z_col, colormap='viridis', log_z=False,
                   stride=2, show_points=False, grid_resolution=50, alpha=0.9):
    x, y, z, label = _prepare_3d_numeric(df, x_col, y_col, z_col, log_z=log_z)
    X, Y, Z = _build_3d_grid(x, y, z, grid_resolution=grid_resolution)
    stride = max(1, int(stride))
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    surf = ax.plot_surface(X[::stride, ::stride], Y[::stride, ::stride], Z[::stride, ::stride],
                           cmap=colormap, linewidth=0, antialiased=True, alpha=alpha)
    fig.colorbar(surf, ax=ax, shrink=0.5, aspect=12, label=label)
    if show_points:
        ax.scatter(x, y, z, c=z, cmap=colormap, s=15, alpha=0.6, depthshade=True)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_zlabel(label)
    ax.set_title('3D Surface Plot')
    return fig


def plot_wireframe3d(df, x_col, y_col, z_col, colormap='viridis', log_z=False,
                     stride=2, show_points=False, grid_resolution=50):
    x, y, z, label = _prepare_3d_numeric(df, x_col, y_col, z_col, log_z=log_z)
    X, Y, Z = _build_3d_grid(x, y, z, grid_resolution=grid_resolution)
    stride = max(1, int(stride))
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_wireframe(X, Y, Z, rstride=stride, cstride=stride, color='black')
    if show_points:
        ax.scatter(x, y, z, c=z, cmap=colormap, s=15, alpha=0.8, depthshade=True)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_zlabel(label)
    ax.set_title('3D Wireframe Plot')
    return fig


def plot_gantt(df, task_col, start_col, end_col, group_col=None, progress_col=None):
    required = [task_col, start_col, end_col]
    if any(col not in df.columns for col in required):
        raise ValueError("Selected columns are missing from the dataset")

    subset_cols = required + ([group_col] if group_col else []) + ([progress_col] if progress_col else [])
    gantt_df = df[subset_cols].dropna(subset=[task_col, start_col, end_col])
    if gantt_df.empty:
        raise ValueError("No rows contain task, start, and end values")

    gantt_df[start_col] = pd.to_datetime(gantt_df[start_col], errors='coerce')
    gantt_df[end_col] = pd.to_datetime(gantt_df[end_col], errors='coerce')
    gantt_df = gantt_df.dropna(subset=[start_col, end_col])
    if gantt_df.empty:
        raise ValueError("Unable to parse start/end dates")

    gantt_df = gantt_df.sort_values(start_col)
    tasks = gantt_df[task_col].astype(str).tolist()
    y_positions = np.arange(len(tasks))
    start_nums = mdates.date2num(gantt_df[start_col].dt.to_pydatetime())
    durations = (gantt_df[end_col] - gantt_df[start_col]).dt.total_seconds() / 86400.0
    if np.any(durations <= 0):
        raise ValueError("End date must be after start date for all tasks")

    fig, ax = plt.subplots(figsize=(10, max(4, len(tasks) * 0.4)))
    if group_col and group_col in gantt_df.columns:
        groups = gantt_df[group_col].astype(str)
        unique_groups = groups.unique()
        cmap = plt.cm.get_cmap('tab20', len(unique_groups))
        color_map = {grp: cmap(idx) for idx, grp in enumerate(unique_groups)}
        bar_colors = [color_map[g] for g in groups]
    else:
        color_map = None
        bar_colors = 'skyblue'

    ax.barh(y_positions, durations, left=start_nums, color=bar_colors, align='center', edgecolor='black')

    if progress_col and progress_col in gantt_df.columns:
        progress_values = pd.to_numeric(gantt_df[progress_col], errors='coerce').fillna(0).clip(0, 1)
        ax.barh(
            y_positions,
            durations * progress_values,
            left=start_nums,
            color='green',
            alpha=0.5,
            align='center',
            height=0.4,
            label='Progress'
        )

    ax.set_yticks(y_positions)
    ax.set_yticklabels(tasks)
    ax.invert_yaxis()
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    ax.set_xlabel('Date')
    ax.set_title('Gantt Chart')

    if color_map:
        handles = [patches.Patch(color=color_map[g], label=str(g)) for g in color_map]
        ax.legend(handles=handles, title=group_col)
    elif progress_col and progress_col in gantt_df.columns:
        ax.legend()

    return fig


def plot_area(df, columns, stacked=True):
    numeric = df[columns].apply(pd.to_numeric, errors='coerce').dropna(how='all')
    if numeric.empty:
        raise ValueError("Selected columns have no numeric data")
    fig, ax = plt.subplots()
    numeric.plot.area(ax=ax, stacked=stacked, alpha=0.8)
    ax.set_title('Area Plot')
    return fig


def plot_dot(df, category_col, value_col, agg_method):
    data = _aggregate_series(df, category_col, value_col, agg_method)
    if data.empty:
        raise ValueError("No data for dot plot")
    fig, ax = plt.subplots()
    y_positions = np.arange(len(data))
    ax.scatter(data.values, y_positions)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(data.index)
    ax.set_xlabel(f"{value_col} ({agg_method})")
    ax.set_title('Dot Plot')
    return fig


def plot_heatmap(df, columns):
    numeric = df[columns].apply(pd.to_numeric, errors='coerce')
    numeric = numeric.dropna(axis=1, how='all')
    if numeric.empty:
        raise ValueError("Selected columns have no numeric data")
    fig, ax = plt.subplots()
    cax = ax.imshow(numeric.T, aspect='auto', cmap='viridis')
    ax.set_yticks(range(len(numeric.columns)))
    ax.set_yticklabels(numeric.columns)
    ax.set_xlabel('Row Index')
    ax.set_title('Heatmap')
    fig.colorbar(cax, ax=ax)
    return fig


def plot_hexbin(df, x_col, y_col, gridsize=30):
    x = pd.to_numeric(df[x_col], errors='coerce')
    y = pd.to_numeric(df[y_col], errors='coerce')
    mask = ~(x.isna() | y.isna())
    fig, ax = plt.subplots()
    hb = ax.hexbin(x[mask], y[mask], gridsize=gridsize, cmap='viridis')
    fig.colorbar(hb, ax=ax, label='Counts')
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title('Hexbin Plot')
    return fig


def plot_contour(df, x_col, y_col, z_col, levels=10):
    x = pd.to_numeric(df[x_col], errors='coerce')
    y = pd.to_numeric(df[y_col], errors='coerce')
    z = pd.to_numeric(df[z_col], errors='coerce')
    mask = ~(x.isna() | y.isna() | z.isna())
    if mask.sum() < 3:
        raise ValueError("Not enough data for contour plot")
    fig, ax = plt.subplots()
    contour = ax.tricontourf(x[mask], y[mask], z[mask], levels=levels, cmap='viridis')
    fig.colorbar(contour, ax=ax)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title('Contour Plot')
    return fig


def plot_imshow(df, columns):
    numeric = df[columns].apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all')
    if numeric.empty:
        raise ValueError("Selected columns have no numeric data")
    fig, ax = plt.subplots()
    cax = ax.imshow(numeric.values, aspect='auto', cmap='viridis')
    ax.set_xticks(range(len(numeric.columns)))
    ax.set_xticklabels(numeric.columns, rotation=45, ha='right')
    ax.set_ylabel('Row Index')
    ax.set_title('Imshow Plot')
    fig.colorbar(cax, ax=ax)
    return fig


def plot_scatter_matrix(df, columns):
    numeric = df[columns].apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all')
    if numeric.shape[1] < 2:
        raise ValueError("Select at least two numeric columns for scatter matrix")
    axes = pd_plotting.scatter_matrix(numeric, figsize=(8, 8), diagonal='hist')
    fig = axes[0, 0].get_figure()
    fig.suptitle('Scatter Matrix')
    return fig


def plot_radviz(df, columns, class_column):
    if class_column not in df.columns:
        raise ValueError("Class column is missing")
    subset_cols = columns + [class_column]
    numeric = df[subset_cols].copy()
    numeric = numeric.dropna()
    if numeric.empty:
        raise ValueError("No data available for radviz")
    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(111)
    pd_plotting.radviz(numeric, class_column, ax=ax)
    ax.set_title('Radviz Plot')
    return fig


def plot_venn(df, columns):
    if not 2 <= len(columns) <= 3:
        raise ValueError("Venn diagram supports 2 or 3 columns")
    sets = []
    for col in columns:
        mask = df[col].astype(bool) if df[col].dtype == bool else df[col].notna()
        sets.append(set(df.index[mask]))

    fig, ax = plt.subplots()
    ax.axis('off')
    if len(sets) == 2:
        _draw_venn2(ax, sets, columns)
    else:
        _draw_venn3(ax, sets, columns)
    return fig


def _draw_venn2(ax, sets, labels):
    A, B = sets
    only_a = len(A - B)
    only_b = len(B - A)
    both = len(A & B)
    circle1 = patches.Circle((0.4, 0.5), 0.3, alpha=0.3, color='tab:blue')
    circle2 = patches.Circle((0.6, 0.5), 0.3, alpha=0.3, color='tab:orange')
    ax.add_patch(circle1)
    ax.add_patch(circle2)
    ax.text(0.3, 0.5, str(only_a), ha='center', va='center')
    ax.text(0.7, 0.5, str(only_b), ha='center', va='center')
    ax.text(0.5, 0.5, str(both), ha='center', va='center')
    ax.text(0.25, 0.85, labels[0], ha='center')
    ax.text(0.75, 0.85, labels[1], ha='center')
    ax.set_title('Venn Diagram (2 Sets)')


def _draw_venn3(ax, sets, labels):
    A, B, C = sets
    only_a = len(A - B - C)
    only_b = len(B - A - C)
    only_c = len(C - A - B)
    ab = len((A & B) - C)
    ac = len((A & C) - B)
    bc = len((B & C) - A)
    abc = len(A & B & C)
    circle1 = patches.Circle((0.45, 0.6), 0.3, alpha=0.3, color='tab:blue')
    circle2 = patches.Circle((0.55, 0.6), 0.3, alpha=0.3, color='tab:orange')
    circle3 = patches.Circle((0.5, 0.35), 0.3, alpha=0.3, color='tab:green')
    for circle in (circle1, circle2, circle3):
        ax.add_patch(circle)
    ax.text(0.32, 0.65, str(only_a), ha='center')
    ax.text(0.68, 0.65, str(only_b), ha='center')
    ax.text(0.5, 0.2, str(only_c), ha='center')
    ax.text(0.5, 0.65, str(ab), ha='center')
    ax.text(0.4, 0.45, str(ac), ha='center')
    ax.text(0.6, 0.45, str(bc), ha='center')
    ax.text(0.5, 0.45, str(abc), ha='center', fontweight='bold')
    ax.text(0.2, 0.9, labels[0], ha='center')
    ax.text(0.8, 0.9, labels[1], ha='center')
    ax.text(0.5, 0.05, labels[2], ha='center')
    ax.set_title('Venn Diagram (3 Sets)')
