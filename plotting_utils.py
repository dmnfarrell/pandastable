import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats, interpolate
from scipy.optimize import curve_fit
import matplotlib.patheffects as patheffects

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
