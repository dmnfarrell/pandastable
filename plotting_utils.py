import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pandas import plotting as pd_plotting
from matplotlib import patches
from matplotlib import dates as mdates
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 - needed for 3D projection
from scipy import stats, interpolate, signal
from scipy.optimize import curve_fit
import matplotlib.patheffects as patheffects
import re
from pathlib import Path
import math
import io


SPEED_OF_LIGHT = 299_792_458.0  # meters per second


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

def _format_group_label(name):
    if isinstance(name, tuple):
        return ", ".join(map(str, name))
    return str(name)

def plot_correlation_grid(
    data,
    target_col,
    corr_df,
    columns,
    columns_per_row=2,
    show_regression=True,
    show_stats=False,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    if not columns:
        raise ValueError("Select at least one correlated column to plot")

    corr_lookup = corr_df.set_index('Column')['Correlation'].to_dict()
    selected_columns = [col for col in columns if col in corr_lookup]
    if not selected_columns:
        raise ValueError("Selected columns not found in correlation results")

    for col in [group_col, group_col2]:
        if col and col not in data.columns:
            raise ValueError(f"Grouping column '{col}' was not found in the data")

    grouped_data = _build_grouped_data(data, group_col, group_col2)
    multi_group_subplots = subplots and len(grouped_data) > 1

    if multi_group_subplots:
        total_panels = len(grouped_data) * len(selected_columns)
        ncols = max(1, columns_per_row)
        nrows = math.ceil(total_panels / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            figsize=(6 * ncols, 4 * nrows),
            sharex=sharex,
            sharey=sharey,
        )
        axes_flat = np.array(axes).flatten()
        idx = 0
        for label, group_df in grouped_data:
            for corr_col in selected_columns:
                if idx >= len(axes_flat):
                    break
                title = f"{corr_col} ({corr_lookup[corr_col]:.3f}) – {label or 'All Data'}"
                _render_correlation_panel(
                    axes_flat[idx],
                    group_df,
                    target_col,
                    corr_col,
                    corr_lookup[corr_col],
                    show_regression,
                    show_stats,
                    title=title,
                )
                idx += 1
        for ax in axes_flat[idx:]:
            ax.set_visible(False)
    else:
        n_panels = len(selected_columns)
        ncols = min(columns_per_row, n_panels) if n_panels else 1
        ncols = max(1, ncols)
        nrows = math.ceil(n_panels / ncols)
        fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 4 * nrows))
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        for ax, corr_col in zip(axes_flat, selected_columns):
            _render_correlation_overlay_panel(
                ax,
                grouped_data,
                data,
                target_col,
                corr_col,
                corr_lookup[corr_col],
                show_regression,
                show_stats,
            )
        for ax in axes_flat[len(selected_columns):]:
            ax.set_visible(False)

    fig.tight_layout()
    fig.suptitle(f"Correlations vs {target_col}", fontsize=16)
    fig.subplots_adjust(top=0.92)
    return fig


def _build_grouped_data(data, group_col=None, group_col2=None):
    group_cols = [col for col in [group_col, group_col2] if col]
    if not group_cols:
        return [(None, data)]
    subset = data.dropna(subset=group_cols)
    if subset.empty:
        raise ValueError("No data available after grouping for correlation plots")
    grouped = list(subset.groupby(group_cols))
    return [(_format_group_label(name), group_df) for name, group_df in grouped]


def _prepare_correlation_series(df, target_col, corr_col):
    if target_col not in df.columns or corr_col not in df.columns:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    x_data = pd.to_numeric(df[target_col], errors='coerce')
    y_data = pd.to_numeric(df[corr_col], errors='coerce')
    mask = ~(np.isnan(x_data) | np.isnan(y_data))
    return x_data[mask], y_data[mask]


def _compute_regression(x_data, y_data):
    if len(x_data) < 2:
        return None
    z = np.polyfit(x_data, y_data, 1)
    slope, intercept = z
    x_range = np.linspace(x_data.min(), x_data.max(), 100)
    y_fit = np.poly1d(z)(x_range)
    r_matrix = np.corrcoef(x_data, y_data)
    r_value = r_matrix[0, 1]
    return {
        "slope": slope,
        "intercept": intercept,
        "x": x_range,
        "y": y_fit,
        "r": r_value,
        "r2": r_value ** 2 if np.isfinite(r_value) else np.nan,
    }


def _format_regression_stats(data, target_col, corr_col):
    x_data, y_data = _prepare_correlation_series(data, target_col, corr_col)
    regression = _compute_regression(x_data, y_data)
    if not regression:
        return None
    return (
        f"slope={regression['slope']:.3g}\n"
        f"intercept={regression['intercept']:.3g}\n"
        f"R={regression['r']:.3g}, R²={regression['r2']:.3g}"
    )


def _render_correlation_overlay_panel(
    ax,
    grouped_data,
    full_data,
    target_col,
    corr_col,
    corr_val,
    show_regression,
    show_stats,
):
    cmap = plt.cm.get_cmap('tab10', max(len(grouped_data), 1))
    any_points = False
    for idx, (label, group_df) in enumerate(grouped_data):
        x_data, y_data = _prepare_correlation_series(group_df, target_col, corr_col)
        if x_data.empty or y_data.empty:
            continue
        color = cmap(idx)
        ax.scatter(x_data, y_data, alpha=0.5, label=label or 'All Data', color=color)
        any_points = True
        if show_regression:
            regression = _compute_regression(x_data, y_data)
            if regression:
                ax.plot(regression['x'], regression['y'], linestyle='--', linewidth=2, color=color)
    if not any_points:
        ax.set_visible(False)
        return
    if len(grouped_data) > 1:
        ax.legend(loc='best')
    if show_stats:
        stats_text = _format_regression_stats(full_data, target_col, corr_col)
        if stats_text:
            ax.text(
                0.98,
                0.02,
                stats_text,
                transform=ax.transAxes,
                ha='right',
                va='bottom',
                bbox=dict(facecolor='white', alpha=0.8),
            )
    ax.set_xlabel(target_col)
    ax.set_ylabel(corr_col)
    ax.set_title(f"{corr_col} ({corr_val:.3f})")
    ax.grid(True, alpha=0.3, linestyle='--')


def _render_correlation_panel(ax, data, target_col, corr_col, corr_val, show_regression, show_stats, title):
    x_data, y_data = _prepare_correlation_series(data, target_col, corr_col)
    if x_data.empty or y_data.empty:
        ax.set_visible(False)
        return
    ax.scatter(x_data, y_data, alpha=0.5)
    if show_regression:
        regression = _compute_regression(x_data, y_data)
        if regression:
            ax.plot(regression['x'], regression['y'], "r--", alpha=0.8, linewidth=2)
    if show_stats:
        stats_text = _format_regression_stats(data, target_col, corr_col)
        if stats_text:
            ax.text(
                0.98,
                0.02,
                stats_text,
                transform=ax.transAxes,
                ha='right',
                va='bottom',
                bbox=dict(facecolor='white', alpha=0.8),
            )
    ax.set_xlabel(target_col)
    ax.set_ylabel(corr_col)
    ax.set_title(title)
    ax.grid(True, alpha=0.3, linestyle='--')


def export_correlations_csv(data, target_col, corr_df, selected_columns):
    ordered = data[[target_col] + selected_columns].copy()
    buffer = io.StringIO()
    ordered.to_csv(buffer, index=False)
    buffer.seek(0)
    return buffer.getvalue().encode('utf-8')


def export_correlation_figure(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    return buffer.getvalue()


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


def _mixed_mode_transform(port_pairs):
    size = port_pairs * 2
    total_ports = size
    rows = []
    for pair in range(port_pairs):
        row = np.zeros(total_ports)
        idx = pair * 2
        row[idx] = 1
        row[idx + 1] = -1
        rows.append(row)
    for pair in range(port_pairs):
        row = np.zeros(total_ports)
        idx = pair * 2
        row[idx] = 1
        row[idx + 1] = 1
        rows.append(row)
    return (1 / np.sqrt(2)) * np.array(rows)


def _get_diff_matrix(touchstone_data):
    diff_matrix = touchstone_data.get('_diff_matrix')
    if diff_matrix is not None:
        return diff_matrix, touchstone_data.get('_diff_ports', diff_matrix.shape[1])
    ports = touchstone_data.get('ports', 0)
    if ports < 4 or ports % 2 != 0:
        raise ValueError("Differential mode requires an even number of ports >= 4")
    port_pairs = ports // 2
    matrix = touchstone_data['matrix']
    transform = _mixed_mode_transform(port_pairs)
    inv_transform = np.linalg.inv(transform)
    diff_slices = []
    for freq_matrix in matrix:
        mixed = transform @ freq_matrix @ inv_transform
        diff_slices.append(mixed[:port_pairs, :port_pairs])
    diff_matrix = np.array(diff_slices)
    touchstone_data['_diff_matrix'] = diff_matrix
    touchstone_data['_diff_ports'] = port_pairs
    return diff_matrix, port_pairs


def get_sparameter_matrix(touchstone_data, mode='single_ended'):
    if mode == 'single_ended':
        return touchstone_data['matrix'], touchstone_data.get('ports', 0)
    if mode == 'differential':
        return _get_diff_matrix(touchstone_data)
    raise ValueError(f"Unsupported S-parameter mode: {mode}")


def get_sparameter_labels(touchstone_data, mode='single_ended'):
    matrix, ports = get_sparameter_matrix(touchstone_data, mode)
    prefix = 'S' if mode == 'single_ended' else 'SDD'
    return [f"{prefix}{i}{j}" for i in range(1, ports + 1) for j in range(1, ports + 1)]


def plot_s_parameters(touchstone_data, selections, display_mode='mag_db', log_freq=False, mode='single_ended'):
    if not selections:
        raise ValueError("Select at least one S-parameter to plot")
    freq = touchstone_data['frequency']
    freq_label = touchstone_data.get('freq_unit', 'Hz')
    matrix, ports = get_sparameter_matrix(touchstone_data, mode)

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


def _draw_smith_background(ax):
    outer = patches.Circle((0, 0), 1, fill=False, color='black', linewidth=1.0)
    ax.add_patch(outer)
    ax.axhline(0, color='gray', linewidth=0.5)
    ax.axvline(0, color='gray', linewidth=0.5)
    for r in [0.2, 0.5, 1.0, 2.0]:
        center = r / (1 + r)
        radius = 1 / (1 + r)
        ax.add_patch(patches.Circle((center, 0), radius, fill=False, color='lightgray', linewidth=0.5))
    for x in np.linspace(-0.5, 0.5, 5):
        ax.add_patch(patches.Circle((1, x), 0.5, fill=False, color='lightgray', linewidth=0.5))
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect('equal')
    ax.set_xlabel('Real(Γ)')
    ax.set_ylabel('Imag(Γ)')
    ax.set_title('Smith Chart')


def plot_smith_chart(touchstone_data, selections, mode='single_ended'):
    if not selections:
        raise ValueError("Select at least one reflection parameter for Smith chart")
    diag_selections = [(i, j) for i, j in selections if i == j]
    if not diag_selections:
        raise ValueError("Smith chart supports reflection terms (i==j) only")
    matrix, ports = get_sparameter_matrix(touchstone_data, mode)
    fig, ax = plt.subplots(figsize=(6, 6))
    _draw_smith_background(ax)
    prefix = 'S' if mode == 'single_ended' else 'SDD'
    for i, _ in diag_selections:
        trace = matrix[:, i - 1, i - 1]
        ax.plot(trace.real, trace.imag, label=f"{prefix}{i}{i}")
    ax.legend(loc='upper right')
    return fig


def calculate_tdr_iczt(freq, s_params, t_start, t_stop, num_points=2048, window='hann'):
    freq = np.asarray(freq)
    s_params = np.asarray(s_params)
    if freq.ndim != 1:
        raise ValueError("Frequency array must be 1-D")
    if len(freq) != len(s_params):
        raise ValueError("Frequency and S-parameter arrays must have the same length")
    order = np.argsort(freq)
    freq = freq[order]
    s_params = s_params[order]

    if len(freq) > 1:
        delta_f = np.mean(np.diff(freq))
        if delta_f <= 0:
            delta_f = abs(delta_f)
        t_stop = t_stop or (1.0 / delta_f)
    else:
        t_stop = t_stop or 1e-6

    if window and window.lower() not in {'none', 'rect'}:
        try:
            weights = signal.windows.get_window(window, len(freq))
        except Exception:
            weights = np.ones(len(freq))
    else:
        weights = np.ones(len(freq))
    s_weighted = s_params * weights

    time = np.linspace(t_start, t_stop, int(num_points))
    exponent = np.exp(1j * 2 * np.pi * np.outer(freq, time))
    tdr = (s_weighted[:, None] * exponent).sum(axis=0) / len(freq)
    return time, tdr


def compute_tdr_trace(touchstone_data, parameter=(1, 1), mode='single_ended', velocity=0.5,
                      points=2048, window='hann'):
    matrix, ports = get_sparameter_matrix(touchstone_data, mode)
    i, j = parameter
    if not (1 <= i <= ports and 1 <= j <= ports):
        raise ValueError("Selected parameter is out of range")
    if i != j:
        raise ValueError("TDR requires a reflection parameter (i == j)")

    freq = np.asarray(touchstone_data['frequency'])
    trace = matrix[:, i - 1, j - 1]
    t_start = 0.0
    t_stop = None
    time, response = calculate_tdr_iczt(freq, trace, t_start, t_stop, num_points=points, window=window)

    velocity = np.clip(float(velocity), 0.01, 1.0)
    reference = float(touchstone_data.get('reference', 50.0))
    distance = 0.5 * velocity * SPEED_OF_LIGHT * time
    rho = response.real
    epsilon = 1e-6
    impedance = reference * (1 + rho) / (np.maximum(epsilon, 1 - rho))

    return {
        'time': time,
        'distance': distance,
        'rho': rho,
        'impedance': impedance,
        'reference': reference,
    }


def plot_tdr(tdr_data, show_impedance=True):
    time = tdr_data['time']
    distance = tdr_data['distance']
    rho = tdr_data['rho']
    impedance = tdr_data['impedance']
    reference = tdr_data['reference']

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(distance * 100, rho, label='Reflection (ρ)', color='tab:blue')
    ax1.set_xlabel('Distance (cm)')
    ax1.set_ylabel('Reflection Coefficient (ρ)', color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax1.grid(True, alpha=0.3, linestyle='--')

    if show_impedance:
        ax2 = ax1.twinx()
        ax2.plot(distance * 100, impedance, label='Impedance (Ω)', color='tab:red')
        ax2.axhline(reference, color='tab:red', linestyle='--', alpha=0.5)
        ax2.set_ylabel('Impedance (Ω)', color='tab:red')
        ax2.tick_params(axis='y', labelcolor='tab:red')

    fig.tight_layout()
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

def plot_histogram(
    df,
    col,
    bins=50,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    if col not in df.columns:
        raise ValueError(f"Column {col} missing from DataFrame")

    bins = int(bins)
    base_series = pd.to_numeric(df[col], errors='coerce')

    group_columns = [c for c in [group_col, group_col2] if c]
    if not group_columns:
        data = base_series.dropna()
        if data.empty:
            raise ValueError("No numeric data available for histogram")
        fig, ax = plt.subplots()
        ax.hist(data, bins=bins, edgecolor='black', alpha=0.7)
        ax.set_xlabel(col)
        ax.set_ylabel('Frequency')
        ax.set_title(f'Histogram of {col}')
        return fig

    subset_cols = [col] + group_columns
    subset = df[subset_cols].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for histogram")

    def _label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    if subplots:
        n_groups = len(grouped)
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            sharex=sharex,
            sharey=sharey,
            figsize=(5 * ncols, 4 * nrows)
        )
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        for ax, (name, group) in zip(axes_flat, grouped):
            data = pd.to_numeric(group[col], errors='coerce').dropna()
            if data.empty:
                ax.set_visible(False)
                continue
            ax.hist(data, bins=bins, edgecolor='black', alpha=0.7)
            ax.set_title(_label(name))
            ax.set_xlabel(col)
            ax.set_ylabel('Frequency')
        for ax in axes_flat[len(grouped):]:
            ax.set_visible(False)
        fig.tight_layout()
        fig.suptitle(f'Histogram of {col} by Group', fontsize=14)
        fig.subplots_adjust(top=0.9)
        return fig

    fig, ax = plt.subplots()
    cmap = plt.cm.get_cmap('tab10', len(grouped))
    for idx, (name, group) in enumerate(grouped):
        data = pd.to_numeric(group[col], errors='coerce').dropna()
        if data.empty:
            continue
        ax.hist(data, bins=bins, alpha=0.6, label=_label(name), color=cmap(idx))
    ax.set_xlabel(col)
    ax.set_ylabel('Frequency')
    ax.set_title(f'Histogram of {col} by Group')
    ax.legend()
    return fig

def plot_scatter(
    df,
    x_col,
    y_col,
    color_col=None,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    group_columns = [col for col in [group_col, group_col2] if col]
    required_cols = [x_col, y_col] + group_columns
    if color_col and not group_columns:
        required_cols.append(color_col)

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for scatter plot: {', '.join(missing)}")

    numeric_df = df[required_cols].copy()
    numeric_df[x_col] = pd.to_numeric(numeric_df[x_col], errors='coerce')
    numeric_df[y_col] = pd.to_numeric(numeric_df[y_col], errors='coerce')
    if color_col and not group_columns:
        numeric_df[color_col] = pd.to_numeric(df[color_col], errors='coerce')

    numeric_df = numeric_df.dropna(subset=[x_col, y_col])
    if numeric_df.empty:
        raise ValueError("No numeric data available for scatter plot")

    if not group_columns:
        fig, ax = plt.subplots()
        x = numeric_df[x_col]
        y = numeric_df[y_col]
        mask = ~(x.isna() | y.isna())
        x_vals = x[mask]
        y_vals = y[mask]
        color_data = None
        if color_col:
            color_series = numeric_df[color_col]
            color_data = color_series[mask]
        sc = ax.scatter(
            x_vals,
            y_vals,
            c=color_data,
            cmap='viridis' if color_data is not None else None,
            alpha=0.7
        )
        if color_data is not None:
            fig.colorbar(sc, label=color_col)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title(f'{y_col} vs {x_col}')
        return fig

    numeric_df = numeric_df.dropna(subset=group_columns)
    grouped = list(numeric_df.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for scatter plot")

    def _group_label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    if subplots:
        n_groups = len(grouped)
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            sharex=sharex,
            sharey=sharey,
            figsize=(5 * ncols, 4 * nrows)
        )
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        cmap = plt.cm.get_cmap('tab10', n_groups)
        for ax, (name, group), idx in zip(axes_flat, grouped, range(len(grouped))):
            x = group[x_col]
            y = group[y_col]
            mask = ~(x.isna() | y.isna())
            if not mask.any():
                continue
            ax.scatter(
                x[mask],
                y[mask],
                color=cmap(idx),
                alpha=0.75,
                label=_group_label(name)
            )
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.set_title(_group_label(name))
            ax.legend()
        for ax in axes_flat[len(grouped):]:
            ax.set_visible(False)
        fig.tight_layout()
        fig.suptitle('Scatter Plot by Group', fontsize=14)
        fig.subplots_adjust(top=0.92)
        return fig

    fig, ax = plt.subplots()
    cmap = plt.cm.get_cmap('tab10', len(grouped))
    for idx, (name, group) in enumerate(grouped):
        x = group[x_col]
        y = group[y_col]
        mask = ~(x.isna() | y.isna())
        if not mask.any():
            continue
        ax.scatter(
            x[mask],
            y[mask],
            color=cmap(idx),
            alpha=0.75,
            label=_group_label(name)
        )
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title('Scatter Plot by Group')
    ax.legend()
    return fig

def plot_line(df, x_col, y_cols, group_col=None, group_col2=None, subplots=False, sharex=False, sharey=False):
    if not y_cols:
        raise ValueError("Select at least one Y column for line plots")

    group_columns = [col for col in [group_col, group_col2] if col]
    requested_cols = [x_col] + y_cols + group_columns
    # If the same column is reused across axes/grouping (common for single-series plots),
    # keep only the first occurrence so DataFrame slicing stays 1-D per label.
    required_cols = list(dict.fromkeys(requested_cols))
    missing = [col for col in requested_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for line plot: {', '.join(missing)}")

    numeric_df = df[required_cols].copy()
    numeric_df[x_col] = pd.to_numeric(numeric_df[x_col], errors='coerce')
    for col in y_cols:
        numeric_df[col] = pd.to_numeric(numeric_df[col], errors='coerce')

    numeric_df = numeric_df.dropna(subset=[x_col])

    if not group_columns:
        fig, ax = plt.subplots()
        x = numeric_df[x_col]
        for y_col in y_cols:
            y = numeric_df[y_col]
            mask = ~(x.isna() | y.isna())
            if not mask.any():
                continue
            x_values = x[mask]
            y_values = y[mask]
            order = np.argsort(x_values)
            ax.plot(x_values.iloc[order], y_values.iloc[order], label=y_col)
        ax.set_xlabel(x_col)
        ax.legend()
        ax.set_title('Line Plot')
        return fig

    numeric_df = numeric_df.dropna(subset=group_columns)
    grouped = list(numeric_df.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for line plot")

    if subplots:
        n_groups = len(grouped)
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
        fig, axes = plt.subplots(nrows, ncols, sharex=sharex, sharey=sharey, figsize=(5 * ncols, 4 * nrows))
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        for ax, (name, group) in zip(axes_flat, grouped):
            x = group[x_col]
            for y_col in y_cols:
                y = group[y_col]
                mask = ~(x.isna() | y.isna())
                if not mask.any():
                    continue
                x_values = x[mask]
                y_values = y[mask]
                order = np.argsort(x_values)
                ax.plot(x_values.iloc[order], y_values.iloc[order], label=y_col)
            title = name if not isinstance(name, tuple) else ", ".join(map(str, name))
            ax.set_title(title)
            if y_cols:
                ax.legend()
            ax.set_xlabel(x_col)
        for ax in axes_flat[len(grouped):]:
            ax.set_visible(False)
        fig.tight_layout()
        fig.suptitle('Line Plot by Group', fontsize=14)
        fig.subplots_adjust(top=0.92)
        return fig

    fig, ax = plt.subplots()
    cmap = plt.cm.get_cmap('tab10', len(grouped))
    for idx, (name, group) in enumerate(grouped):
        x = group[x_col]
        for y_col in y_cols:
            y = group[y_col]
            mask = ~(x.isna() | y.isna())
            if not mask.any():
                continue
            x_values = x[mask]
            y_values = y[mask]
            order = np.argsort(x_values)
            label_name = name if not isinstance(name, tuple) else ", ".join(map(str, name))
            label = f"{label_name} – {y_col}" if len(y_cols) > 1 else str(label_name)
            ax.plot(
                x_values.iloc[order],
                y_values.iloc[order],
                label=label,
                color=cmap(idx)
            )
    ax.set_xlabel(x_col)
    ax.legend()
    ax.set_title('Line Plot by Group')
    return fig


def plot_bar(
    df,
    category_col,
    value_col,
    agg_method,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    group_columns = [col for col in [group_col, group_col2] if col]
    if not group_columns:
        data = _aggregate_series(df, category_col, value_col, agg_method)
        fig, ax = plt.subplots()
        data.plot.bar(ax=ax)
        ax.set_xlabel(category_col)
        ax.set_ylabel(f"{value_col} ({agg_method})")
        ax.set_title('Bar Plot')
        return fig

    subset_cols = [category_col, value_col] + group_columns
    subset = df[subset_cols].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for bar plot")

    def _label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    if subplots:
        n_groups = len(grouped)
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            sharex=sharex,
            sharey=sharey,
            figsize=(6 * ncols, 4 * nrows)
        )
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        for ax, (name, group) in zip(axes_flat, grouped):
            series = _aggregate_series(group, category_col, value_col, agg_method)
            if series.empty:
                ax.set_visible(False)
                continue
            series.plot.bar(ax=ax)
            ax.set_title(_label(name))
            ax.set_xlabel(category_col)
            ax.set_ylabel(f"{value_col} ({agg_method})")
        for ax in axes_flat[len(grouped):]:
            ax.set_visible(False)
        fig.tight_layout()
        fig.suptitle('Bar Plot by Group', fontsize=14)
        fig.subplots_adjust(top=0.92)
        return fig

    series_list = []
    for name, group in grouped:
        series = _aggregate_series(group, category_col, value_col, agg_method)
        if series.empty:
            continue
        series_list.append(series.rename(_label(name)))
    if not series_list:
        raise ValueError("No aggregated data available for grouped bar plot")
    combined = pd.concat(series_list, axis=1).fillna(0)
    fig, ax = plt.subplots()
    combined.plot(kind='bar', ax=ax)
    ax.set_xlabel(category_col)
    ax.set_ylabel(f"{value_col} ({agg_method})")
    ax.set_title('Bar Plot by Group')
    ax.legend(title='Group')
    return fig


def plot_barh(
    df,
    category_col,
    value_col,
    agg_method,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    group_columns = [col for col in [group_col, group_col2] if col]
    if not group_columns:
        data = _aggregate_series(df, category_col, value_col, agg_method)
        fig, ax = plt.subplots()
        data.sort_values().plot.barh(ax=ax)
        ax.set_xlabel(f"{value_col} ({agg_method})")
        ax.set_ylabel(category_col)
        ax.set_title('Horizontal Bar Plot')
        return fig

    subset_cols = [category_col, value_col] + group_columns
    subset = df[subset_cols].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for horizontal bar plot")

    def _label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    if subplots:
        n_groups = len(grouped)
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            sharex=sharex,
            sharey=sharey,
            figsize=(6 * ncols, 4 * nrows)
        )
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        for ax, (name, group) in zip(axes_flat, grouped):
            series = _aggregate_series(group, category_col, value_col, agg_method)
            if series.empty:
                ax.set_visible(False)
                continue
            series.sort_values().plot.barh(ax=ax)
            ax.set_ylabel(category_col)
            ax.set_xlabel(f"{value_col} ({agg_method})")
            ax.set_title(_label(name))
        for ax in axes_flat[len(grouped):]:
            ax.set_visible(False)
        fig.tight_layout()
        fig.suptitle('Horizontal Bar Plot by Group', fontsize=14)
        fig.subplots_adjust(top=0.92)
        return fig

    series_list = []
    for name, group in grouped:
        series = _aggregate_series(group, category_col, value_col, agg_method)
        if series.empty:
            continue
        series_list.append(series.rename(_label(name)))
    if not series_list:
        raise ValueError("No aggregated data available for grouped horizontal bar plot")
    combined = pd.concat(series_list, axis=1).fillna(0)
    fig, ax = plt.subplots()
    combined.plot(kind='barh', ax=ax)
    ax.set_ylabel(category_col)
    ax.set_xlabel(f"{value_col} ({agg_method})")
    ax.set_title('Horizontal Bar Plot by Group')
    ax.legend(title='Group')
    return fig


def plot_pie(
    df,
    category_col,
    value_col,
    agg_method,
    group_col=None,
    group_col2=None,
    subplots=False,
):
    group_columns = [col for col in [group_col, group_col2] if col]
    if not group_columns:
        data = _aggregate_series(df, category_col, value_col, agg_method)
        if data.empty:
            raise ValueError("No data available for pie chart")
        fig, ax = plt.subplots()
        ax.pie(data.values, labels=data.index, autopct='%1.1f%%', startangle=90)
        ax.set_title('Pie Chart')
        ax.axis('equal')
        return fig

    subset_cols = [category_col, value_col] + group_columns
    subset = df[subset_cols].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for pie chart")

    def _label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    n_groups = len(grouped)
    if subplots:
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
    else:
        nrows = 1
        ncols = n_groups
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 5 * nrows))
    axes_array = np.array(axes)
    axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
    for ax, (name, group) in zip(axes_flat, grouped):
        series = _aggregate_series(group, category_col, value_col, agg_method)
        if series.empty:
            ax.set_visible(False)
            continue
        ax.pie(series.values, labels=series.index, autopct='%1.1f%%', startangle=90)
        ax.set_title(_label(name))
        ax.axis('equal')
    for ax in axes_flat[len(grouped):]:
        ax.set_visible(False)
    fig.tight_layout()
    fig.suptitle('Pie Chart by Group', fontsize=14)
    fig.subplots_adjust(top=0.9)
    return fig


def plot_box(
    df,
    columns,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    if not columns:
        raise ValueError("Select at least one column for box plot")

    group_columns = [c for c in [group_col, group_col2] if c]

    def _label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    if not group_columns:
        numeric = df[columns].apply(pd.to_numeric, errors='coerce').dropna(how='all')
        if numeric.empty:
            raise ValueError("Selected columns have no numeric data")
        fig, ax = plt.subplots()
        numeric.plot.box(ax=ax)
        ax.set_title('Box Plot')
        return fig

    subset_cols = columns + group_columns
    subset = df[subset_cols].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for box plot")

    if subplots:
        n_groups = len(grouped)
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            sharex=sharex,
            sharey=sharey,
            figsize=(6 * ncols, 4 * nrows)
        )
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        for ax, (name, group) in zip(axes_flat, grouped):
            numeric = group[columns].apply(pd.to_numeric, errors='coerce').dropna(how='all')
            if numeric.empty:
                ax.set_visible(False)
                continue
            numeric.plot.box(ax=ax)
            ax.set_title(_label(name))
        for ax in axes_flat[len(grouped):]:
            ax.set_visible(False)
        fig.tight_layout()
        fig.suptitle('Box Plot by Group', fontsize=14)
        fig.subplots_adjust(top=0.92)
        return fig

    data_series = []
    labels = []
    for name, group in grouped:
        numeric = group[columns].apply(pd.to_numeric, errors='coerce')
        for col in columns:
            series = numeric[col].dropna()
            if series.empty:
                continue
            data_series.append(series.values)
            labels.append(f"{col} – {_label(name)}")
    if not data_series:
        raise ValueError("No numeric data available for grouped box plot")
    fig, ax = plt.subplots()
    ax.boxplot(data_series, labels=labels, vert=True)
    ax.set_title('Box Plot by Group')
    ax.tick_params(axis='x', rotation=45)
    return fig


def plot_violin(
    df,
    columns,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    if not columns:
        raise ValueError("Select at least one column for violin plot")

    group_columns = [c for c in [group_col, group_col2] if c]

    def _label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    if not group_columns:
        numeric = df[columns].apply(pd.to_numeric, errors='coerce').dropna()
        if numeric.empty:
            raise ValueError("Selected columns have no numeric data")
        fig, ax = plt.subplots()
        ax.violinplot([numeric[col].dropna().values for col in numeric.columns], showmeans=True)
        ax.set_xticks(range(1, len(numeric.columns) + 1))
        ax.set_xticklabels(numeric.columns, rotation=45, ha='right')
        ax.set_title('Violin Plot')
        return fig

    subset_cols = columns + group_columns
    subset = df[subset_cols].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for violin plot")

    if subplots:
        n_groups = len(grouped)
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            sharex=sharex,
            sharey=sharey,
            figsize=(6 * ncols, 4 * nrows)
        )
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        for ax, (name, group) in zip(axes_flat, grouped):
            numeric = group[columns].apply(pd.to_numeric, errors='coerce').dropna()
            if numeric.empty:
                ax.set_visible(False)
                continue
            ax.violinplot([numeric[col].dropna().values for col in numeric.columns], showmeans=True)
            ax.set_xticks(range(1, len(numeric.columns) + 1))
            ax.set_xticklabels(numeric.columns, rotation=45, ha='right')
            ax.set_title(_label(name))
        for ax in axes_flat[len(grouped):]:
            ax.set_visible(False)
        fig.tight_layout()
        fig.suptitle('Violin Plot by Group', fontsize=14)
        fig.subplots_adjust(top=0.92)
        return fig

    data_series = []
    labels = []
    for name, group in grouped:
        numeric = group[columns].apply(pd.to_numeric, errors='coerce')
        for col in columns:
            series = numeric[col].dropna()
            if series.empty:
                continue
            data_series.append(series.values)
            labels.append(f"{col} – {_label(name)}")
    if not data_series:
        raise ValueError("No numeric data available for grouped violin plot")
    fig, ax = plt.subplots()
    parts = ax.violinplot(data_series, showmeans=True)
    ax.set_xticks(range(1, len(data_series) + 1))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_title('Violin Plot by Group')
    return fig


def plot_density(
    df,
    columns,
    bw_method='scott',
    fill=False,
    show_rug=False,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    if not columns:
        raise ValueError("Select at least one column for density plot")

    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for density plot: {', '.join(missing)}")

    group_columns = [col for col in [group_col, group_col2] if col]

    def _format_label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    def _plot_series(ax, series, label):
        clean = pd.to_numeric(series, errors='coerce').dropna()
        if clean.empty:
            return False
        try:
            bw = float(bw_method)
        except (ValueError, TypeError):
            bw = bw_method
        kde = stats.gaussian_kde(clean, bw_method=bw)
        x_grid = np.linspace(clean.min(), clean.max(), 500)
        y = kde(x_grid)
        ax.plot(x_grid, y, label=label)
        if fill:
            ax.fill_between(x_grid, y, alpha=0.2)
        if show_rug:
            ax.plot(clean, np.full_like(clean, -0.005), '|', color=ax.lines[-1].get_color())
        return True

    if not group_columns:
        fig, ax = plt.subplots()
        any_plotted = False
        for col in columns:
            plotted = _plot_series(ax, df[col], col)
            any_plotted = any_plotted or plotted
        if not any_plotted:
            raise ValueError("No numeric data available for density plot")
        ax.set_title('Density Plot')
        ax.legend()
        return fig

    required = columns + group_columns
    subset = df[required].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for density plot")

    if subplots:
        n_groups = len(grouped)
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            sharex=sharex,
            sharey=sharey,
            figsize=(5 * ncols, 4 * nrows)
        )
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        for ax, (name, group) in zip(axes_flat, grouped):
            any_plotted = False
            for col in columns:
                plotted = _plot_series(ax, group[col], f"{_format_label(name)} – {col}")
                any_plotted = any_plotted or plotted
            if any_plotted:
                ax.legend()
            ax.set_title(_format_label(name))
        for ax in axes_flat[len(grouped):]:
            ax.set_visible(False)
        fig.tight_layout()
        fig.suptitle('Density Plot by Group', fontsize=14)
        fig.subplots_adjust(top=0.92)
        return fig

    fig, ax = plt.subplots()
    for name, group in grouped:
        for col in columns:
            _plot_series(ax, group[col], f"{_format_label(name)} – {col}")
    ax.set_title('Density Plot by Group')
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


def plot_area(
    df,
    columns,
    stacked=True,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    if not columns:
        raise ValueError("Select at least one column for area plot")

    group_columns = [col for col in [group_col, group_col2] if col]
    if not group_columns:
        numeric = df[columns].apply(pd.to_numeric, errors='coerce').dropna()
        if numeric.empty:
            raise ValueError("Selected columns have no numeric data")
        fig, ax = plt.subplots()
        numeric.plot.area(ax=ax, stacked=stacked)
        ax.set_title('Area Plot')
        return fig

    subset_cols = columns + group_columns
    subset = df[subset_cols].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for area plot")

    def _label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    if subplots:
        n_groups = len(grouped)
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            sharex=sharex,
            sharey=sharey,
            figsize=(6 * ncols, 4 * nrows)
        )
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        for ax, (name, group) in zip(axes_flat, grouped):
            numeric = group[columns].apply(pd.to_numeric, errors='coerce').dropna()
            if numeric.empty:
                ax.set_visible(False)
                continue
            numeric.plot.area(ax=ax, stacked=stacked)
            ax.set_title(_label(name))
        for ax in axes_flat[len(grouped):]:
            ax.set_visible(False)
        fig.tight_layout()
        fig.suptitle('Area Plot by Group', fontsize=14)
        fig.subplots_adjust(top=0.92)
        return fig

    fig, ax = plt.subplots()
    cmap = plt.cm.get_cmap('tab10', len(grouped))
    for idx, (name, group) in enumerate(grouped):
        numeric = group[columns].apply(pd.to_numeric, errors='coerce').dropna()
        if numeric.empty:
            continue
        numeric.plot.area(ax=ax, stacked=stacked, alpha=0.4 + 0.4 * (idx % 2), color=cmap(idx))
    ax.set_title('Area Plot by Group')
    return fig


def plot_dot(
    df,
    category_col,
    value_col,
    agg_method,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    group_columns = [c for c in [group_col, group_col2] if c]
    if not group_columns:
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

    subset_cols = [category_col, value_col] + group_columns
    subset = df[subset_cols].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for dot plot")

    def _label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    if subplots:
        n_groups = len(grouped)
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            sharex=sharex,
            sharey=sharey,
            figsize=(5 * ncols, 4 * nrows)
        )
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        for ax, (name, group) in zip(axes_flat, grouped):
            data = _aggregate_series(group, category_col, value_col, agg_method)
            if data.empty:
                ax.set_visible(False)
                continue
            y_positions = np.arange(len(data))
            ax.scatter(data.values, y_positions)
            ax.set_yticks(y_positions)
            ax.set_yticklabels(data.index)
            ax.set_xlabel(f"{value_col} ({agg_method})")
            ax.set_title(_label(name))
        for ax in axes_flat[len(grouped):]:
            ax.set_visible(False)
        fig.tight_layout()
        fig.suptitle('Dot Plot by Group', fontsize=14)
        fig.subplots_adjust(top=0.92)
        return fig

    fig, ax = plt.subplots()
    cmap = plt.cm.get_cmap('tab10', len(grouped))
    max_len = 0
    y_ticks = []
    y_labels = []
    for idx, (name, group) in enumerate(grouped):
        data = _aggregate_series(group, category_col, value_col, agg_method)
        if data.empty:
            continue
        y_positions = np.arange(len(data)) + max_len
        max_len += len(data)
        ax.scatter(data.values, y_positions, label=_label(name), color=cmap(idx))
        y_ticks.extend(y_positions)
        y_labels.extend(data.index)
    if not y_ticks:
        raise ValueError("No aggregated data available for grouped dot plot")
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels, rotation=0)
    ax.set_xlabel(f"{value_col} ({agg_method})")
    ax.set_title('Dot Plot by Group')
    ax.legend()
    return fig


def plot_heatmap(
    df,
    columns,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    if not columns:
        raise ValueError("Select at least one column for heatmap")

    group_columns = [c for c in [group_col, group_col2] if c]

    def _label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    if not group_columns:
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

    subset_cols = columns + group_columns
    subset = df[subset_cols].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for heatmap")

    n_groups = len(grouped)
    if subplots:
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
    else:
        nrows = 1
        ncols = n_groups
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(5 * ncols, 4 * nrows),
        sharex=sharex,
        sharey=sharey
    )
    axes_array = np.array(axes)
    axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
    for ax, (name, group) in zip(axes_flat, grouped):
        numeric = group[columns].apply(pd.to_numeric, errors='coerce')
        numeric = numeric.dropna(axis=1, how='all')
        if numeric.empty:
            ax.set_visible(False)
            continue
        cax = ax.imshow(numeric.T, aspect='auto', cmap='viridis')
        ax.set_yticks(range(len(numeric.columns)))
        ax.set_yticklabels(numeric.columns)
        ax.set_title(_label(name))
    for ax in axes_flat[len(grouped):]:
        ax.set_visible(False)
    fig.tight_layout()
    fig.suptitle('Heatmap by Group', fontsize=14)
    fig.subplots_adjust(top=0.9)
    fig.colorbar(cax, ax=axes_flat.tolist(), shrink=0.6)
    return fig


def plot_hexbin(
    df,
    x_col,
    y_col,
    gridsize=30,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    group_columns = [c for c in [group_col, group_col2] if c]
    base_x = pd.to_numeric(df[x_col], errors='coerce')
    base_y = pd.to_numeric(df[y_col], errors='coerce')

    if not group_columns:
        mask = ~(base_x.isna() | base_y.isna())
        fig, ax = plt.subplots()
        hb = ax.hexbin(base_x[mask], base_y[mask], gridsize=gridsize, cmap='viridis')
        fig.colorbar(hb, ax=ax, label='Counts')
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title('Hexbin Plot')
        return fig

    subset_cols = [x_col, y_col] + group_columns
    subset = df[subset_cols].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for hexbin plot")

    def _label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    if subplots:
        n_groups = len(grouped)
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            sharex=sharex,
            sharey=sharey,
            figsize=(5 * ncols, 4 * nrows)
        )
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        for ax, (name, group) in zip(axes_flat, grouped):
            x = pd.to_numeric(group[x_col], errors='coerce')
            y = pd.to_numeric(group[y_col], errors='coerce')
            mask = ~(x.isna() | y.isna())
            if not mask.any():
                ax.set_visible(False)
                continue
            hb = ax.hexbin(x[mask], y[mask], gridsize=gridsize, cmap='viridis')
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.set_title(_label(name))
        for ax in axes_flat[len(grouped):]:
            ax.set_visible(False)
        fig.tight_layout()
        fig.suptitle('Hexbin Plot by Group', fontsize=14)
        fig.subplots_adjust(top=0.92)
        return fig

    fig, ax = plt.subplots()
    cmap = plt.cm.get_cmap('tab10', len(grouped))
    for idx, (name, group) in enumerate(grouped):
        x = pd.to_numeric(group[x_col], errors='coerce')
        y = pd.to_numeric(group[y_col], errors='coerce')
        mask = ~(x.isna() | y.isna())
        if not mask.any():
            continue
        hb = ax.hexbin(x[mask], y[mask], gridsize=gridsize, cmap='viridis', alpha=0.4 + 0.4 * (idx % 2))
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title('Hexbin Plot by Group')
    return fig


def plot_contour(
    df,
    x_col,
    y_col,
    z_col,
    levels=10,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    group_columns = [c for c in [group_col, group_col2] if c]
    base_x = pd.to_numeric(df[x_col], errors='coerce')
    base_y = pd.to_numeric(df[y_col], errors='coerce')
    base_z = pd.to_numeric(df[z_col], errors='coerce')

    if not group_columns:
        mask = ~(base_x.isna() | base_y.isna() | base_z.isna())
        if mask.sum() < 3:
            raise ValueError("Not enough data for contour plot")
        fig, ax = plt.subplots()
        contour = ax.tricontourf(base_x[mask], base_y[mask], base_z[mask], levels=levels, cmap='viridis')
        fig.colorbar(contour, ax=ax)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title('Contour Plot')
        return fig

    subset_cols = [x_col, y_col, z_col] + group_columns
    subset = df[subset_cols].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for contour plot")

    def _label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    if subplots:
        n_groups = len(grouped)
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
        fig, axes = plt.subplots(
            nrows,
            ncols,
            sharex=sharex,
            sharey=sharey,
            figsize=(5 * ncols, 4 * nrows)
        )
        axes_array = np.array(axes)
        axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
        for ax, (name, group) in zip(axes_flat, grouped):
            x = pd.to_numeric(group[x_col], errors='coerce')
            y = pd.to_numeric(group[y_col], errors='coerce')
            z = pd.to_numeric(group[z_col], errors='coerce')
            mask = ~(x.isna() | y.isna() | z.isna())
            if mask.sum() < 3:
                ax.set_visible(False)
                continue
            contour = ax.tricontourf(x[mask], y[mask], z[mask], levels=levels, cmap='viridis')
            ax.set_title(_label(name))
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
        for ax in axes_flat[len(grouped):]:
            ax.set_visible(False)
        fig.tight_layout()
        fig.suptitle('Contour Plot by Group', fontsize=14)
        fig.subplots_adjust(top=0.92)
        return fig

    fig, ax = plt.subplots()
    cmap = plt.cm.get_cmap('tab10', len(grouped))
    for idx, (name, group) in enumerate(grouped):
        x = pd.to_numeric(group[x_col], errors='coerce')
        y = pd.to_numeric(group[y_col], errors='coerce')
        z = pd.to_numeric(group[z_col], errors='coerce')
        mask = ~(x.isna() | y.isna() | z.isna())
        if mask.sum() < 3:
            continue
        contour = ax.tricontourf(x[mask], y[mask], z[mask], levels=levels, cmap='viridis', alpha=0.3)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title('Contour Plot by Group')
    return fig


def plot_imshow(
    df,
    columns,
    group_col=None,
    group_col2=None,
    subplots=False,
    sharex=False,
    sharey=False,
):
    if not columns:
        raise ValueError("Select at least one column for imshow plot")

    group_columns = [c for c in [group_col, group_col2] if c]

    def _label(name):
        if isinstance(name, tuple):
            return ", ".join(map(str, name))
        return str(name)

    if not group_columns:
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

    subset_cols = columns + group_columns
    subset = df[subset_cols].dropna(subset=group_columns)
    grouped = list(subset.groupby(group_columns))
    if not grouped:
        raise ValueError("No data available after grouping for imshow plot")

    n_groups = len(grouped)
    if subplots:
        ncols = math.ceil(math.sqrt(n_groups))
        nrows = math.ceil(n_groups / ncols)
    else:
        nrows = 1
        ncols = n_groups
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(5 * ncols, 4 * nrows),
        sharex=sharex,
        sharey=sharey
    )
    axes_array = np.array(axes)
    axes_flat = axes_array.flatten() if axes_array.ndim > 1 else axes_array.reshape(-1)
    for ax, (name, group) in zip(axes_flat, grouped):
        numeric = group[columns].apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all')
        if numeric.empty:
            ax.set_visible(False)
            continue
        cax = ax.imshow(numeric.values, aspect='auto', cmap='viridis')
        ax.set_xticks(range(len(numeric.columns)))
        ax.set_xticklabels(numeric.columns, rotation=45, ha='right')
        ax.set_title(_label(name))
    for ax in axes_flat[len(grouped):]:
        ax.set_visible(False)
    fig.tight_layout()
    fig.suptitle('Imshow Plot by Group', fontsize=14)
    fig.subplots_adjust(top=0.9)
    fig.colorbar(cax, ax=axes_flat.tolist(), shrink=0.6)
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
