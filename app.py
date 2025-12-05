import json
import streamlit as st
import pandas as pd
import os
import re
from copy import deepcopy
from pathlib import Path
from datetime import datetime
import utils
import plotting_utils
import numpy as np
import file_ops
from plot_state import DEFAULT_PLOT_STATE, PlotStateManager
from settings_store import SettingsManager

SAVED_FILTER_PLACEHOLDER = "-- Select Saved --"
RECENT_DIR_PLACEHOLDER = "-- Select Recent Directory --"
TOUCHSTONE_FILE_PLACEHOLDER = "-- Select Touchstone --"
TOUCHSTONE_EXTENSIONS = {'.s1p', '.s2p', '.s3p', '.s4p'}

st.set_page_config(layout="wide", page_title="CSV Browser")

# --- Session State Initialization ---
if 'current_dir' not in st.session_state:
    st.session_state.current_dir = os.getcwd()
if 'file_filter' not in st.session_state:
    st.session_state.file_filter = ""
if 'selected_file' not in st.session_state:
    st.session_state.selected_file = None
if 'df' not in st.session_state:
    st.session_state.df = None
if 'plot_state_manager' not in st.session_state:
    st.session_state.plot_state_manager = PlotStateManager()
if 'plot_state' not in st.session_state:
    st.session_state.plot_state = None
if 'plot_state_file_key' not in st.session_state:
    st.session_state.plot_state_file_key = None
if 'settings_manager' not in st.session_state:
    st.session_state.settings_manager = SettingsManager()
if 'row_filter_text' not in st.session_state:
    st.session_state.row_filter_text = ""
if 'column_filter_text' not in st.session_state:
    st.session_state.column_filter_text = ""
if 'saved_file_filter_select' not in st.session_state:
    st.session_state.saved_file_filter_select = SAVED_FILTER_PLACEHOLDER
if 'saved_row_filter_select' not in st.session_state:
    st.session_state.saved_row_filter_select = SAVED_FILTER_PLACEHOLDER
if 'saved_column_filter_select' not in st.session_state:
    st.session_state.saved_column_filter_select = SAVED_FILTER_PLACEHOLDER
if 'saved_file_op_dest_select' not in st.session_state:
    st.session_state.saved_file_op_dest_select = SAVED_FILTER_PLACEHOLDER
if 'saved_file_op_template_select' not in st.session_state:
    st.session_state.saved_file_op_template_select = SAVED_FILTER_PLACEHOLDER
if 'recent_dir_select' not in st.session_state:
    st.session_state.recent_dir_select = RECENT_DIR_PLACEHOLDER
if 'include_subdirs' not in st.session_state:
    st.session_state.include_subdirs = False
if 'file_min_size_kb' not in st.session_state:
    st.session_state.file_min_size_kb = 0
if 'file_max_size_kb' not in st.session_state:
    st.session_state.file_max_size_kb = 0
if 'file_modified_after' not in st.session_state:
    st.session_state.file_modified_after = ""
if 'file_modified_before' not in st.session_state:
    st.session_state.file_modified_before = ""
if 'filename_parse_mode' not in st.session_state:
    st.session_state.filename_parse_mode = 'split'
if 'filename_delimiter' not in st.session_state:
    st.session_state.filename_delimiter = '_'
if 'filename_max_parts' not in st.session_state:
    st.session_state.filename_max_parts = 4
if 'selected_file_option' not in st.session_state:
    st.session_state.selected_file_option = ""
if 'column_search_text' not in st.session_state:
    st.session_state.column_search_text = ""
if 'move_column_select' not in st.session_state:
    st.session_state.move_column_select = "-- Select Column --"
if 'file_browser_df' not in st.session_state:
    st.session_state.file_browser_df = pd.DataFrame()
if 'file_browser_selection' not in st.session_state:
    st.session_state.file_browser_selection = []
if 'selected_files' not in st.session_state:
    st.session_state.selected_files = []
if 'file_op_dest' not in st.session_state:
    st.session_state.file_op_dest = ""
if 'file_op_overwrite' not in st.session_state:
    st.session_state.file_op_overwrite = False
if 'file_op_rename_template' not in st.session_state:
    st.session_state.file_op_rename_template = "{stem}"
if 'file_op_delete_confirm' not in st.session_state:
    st.session_state.file_op_delete_confirm = ""
if 'file_op_feedback' not in st.session_state:
    st.session_state.file_op_feedback = None
if 'sparam_data' not in st.session_state:
    st.session_state.sparam_data = None
if 'sparam_source' not in st.session_state:
    st.session_state.sparam_source = None
if 'sparam_selection' not in st.session_state:
    st.session_state.sparam_selection = []
if 'sparam_display_mode' not in st.session_state:
    st.session_state.sparam_display_mode = 'mag_db'
if 'sparam_file_option' not in st.session_state:
    st.session_state.sparam_file_option = TOUCHSTONE_FILE_PLACEHOLDER


def _settings_manager():
    manager = st.session_state.get('settings_manager')
    if manager is None:
        manager = SettingsManager()
        st.session_state.settings_manager = manager
    return manager


def _list_csv_files(directory, include_subdirs=False):
    if not directory or not os.path.isdir(directory):
        return pd.DataFrame()
    base_path = Path(directory)
    records = []
    try:
        iterator = base_path.rglob('*') if include_subdirs else base_path.iterdir()
        for candidate in iterator:
            try:
                if not candidate.is_file():
                    continue
                suffix = candidate.suffix.lower()
                if suffix not in {'.csv', '.tsv'} and suffix not in TOUCHSTONE_EXTENSIONS:
                    continue
                stat = candidate.stat()
                modified_dt = datetime.fromtimestamp(stat.st_mtime)
                records.append({
                    "Name": candidate.name,
                    "Directory": str(candidate.parent),
                    "Path": str(candidate),
                    "Extension": suffix,
                    "SizeBytes": stat.st_size,
                    "SizeDisplay": _format_size(stat.st_size),
                    "ModifiedDt": modified_dt,
                    "Modified": modified_dt.strftime("%Y-%m-%d %H:%M:%S"),
                })
            except PermissionError:
                continue
    except PermissionError:
        return pd.DataFrame()

    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df.sort_values('ModifiedDt', ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def _apply_file_filters(file_df):
    df = file_df.copy()
    filter_text = st.session_state.get('file_filter', '').strip()
    if filter_text:
        terms = [term.strip() for term in filter_text.replace(',', ' ').split() if term.strip()]
        for term in terms:
            invert = term.startswith('!')
            needle = term[1:] if invert else term
            if not needle:
                continue
            mask = df['Name'].str.contains(needle, case=False, na=False) | df['Directory'].str.contains(needle, case=False, na=False)
            df = df[~mask] if invert else df[mask]

    min_kb = st.session_state.get('file_min_size_kb', 0) or 0
    max_kb = st.session_state.get('file_max_size_kb', 0) or 0
    if min_kb:
        df = df[df['SizeBytes'] >= min_kb * 1024]
    if max_kb:
        df = df[df['SizeBytes'] <= max_kb * 1024]

    modified_after = _parse_date_input(st.session_state.get('file_modified_after', ''))
    modified_before = _parse_date_input(st.session_state.get('file_modified_before', ''))
    if modified_after:
        df = df[df['ModifiedDt'] >= modified_after]
    if modified_before:
        df = df[df['ModifiedDt'] <= modified_before]

    return df.reset_index(drop=True)


def _parse_filename_parts(name, mode, delimiter, max_parts):
    if mode == 'none':
        return {}
    stem = Path(name).stem
    if mode == 'dash':
        parts = stem.split('-')
    else:
        token = delimiter or '_'
        parts = stem.split(token)
    parts = parts[:max_parts]
    return {f"Part {idx + 1}": part.strip() for idx, part in enumerate(parts)}


def _selected_file_records():
    return st.session_state.get('selected_files') or []


def _invalidate_loaded_file(paths):
    current = st.session_state.get('selected_file')
    if current and current in paths:
        st.session_state.selected_file = None
        st.session_state.df = None


def _set_file_op_feedback(kind, message):
    st.session_state.file_op_feedback = {"kind": kind, "message": message}


def _render_file_operations():
    with st.expander("File Operations", expanded=False):
        selected_records = _selected_file_records()
        if not selected_records:
            st.info("Select one or more files from the sidebar list to enable actions.")
            return

        sample_names = ", ".join(Path(rec['Path']).name for rec in selected_records[:3])
        if sample_names:
            suffix = " …" if len(selected_records) > 3 else ""
            st.caption(f"Selected ({len(selected_records)}): {sample_names}{suffix}")

        st.session_state.file_op_dest = st.text_input(
            "Destination Directory",
            st.session_state.file_op_dest,
            placeholder="C:/data/exports"
        )
        dest_cols = st.columns([3, 1])
        _render_saved_filter_selector(
            "Saved Destinations",
            "file_op_dest",
            "saved_file_op_dest_select",
            "file_op_dest",
            dest_cols[0]
        )
        if dest_cols[1].button("Save", key="save_file_op_dest"):
            if _save_filter_preset("file_op_dest", st.session_state.file_op_dest):
                st.success("Destination saved")
            else:
                st.warning("Nothing to save")
        st.session_state.file_op_overwrite = st.checkbox(
            "Allow overwrite",
            value=st.session_state.file_op_overwrite
        )

        copy_col, move_col = st.columns(2)
        if copy_col.button("Copy Selected"):
            kind, message, _, mutated = file_ops.copy_or_move_files(
                selected_records,
                st.session_state.file_op_dest,
                st.session_state.file_op_overwrite,
                operation='copy'
            )
            if mutated:
                _invalidate_loaded_file(mutated)
            _set_file_op_feedback(kind, message)
        if move_col.button("Move Selected"):
            kind, message, _, mutated = file_ops.copy_or_move_files(
                selected_records,
                st.session_state.file_op_dest,
                st.session_state.file_op_overwrite,
                operation='move'
            )
            if mutated:
                _invalidate_loaded_file(mutated)
            _set_file_op_feedback(kind, message)

        st.divider()
        st.session_state.file_op_rename_template = st.text_input(
            "Rename Template",
            st.session_state.file_op_rename_template,
            help="Use placeholders like {stem}, {suffix}, {Part_1}."
        )
        template_cols = st.columns([3, 1])
        _render_saved_filter_selector(
            "Saved Templates",
            "file_op_template",
            "saved_file_op_template_select",
            "file_op_rename_template",
            template_cols[0]
        )
        if template_cols[1].button("Save", key="save_file_op_template"):
            if _save_filter_preset("file_op_template", st.session_state.file_op_rename_template):
                st.success("Template saved")
            else:
                st.warning("Nothing to save")
        previews = file_ops.preview_rename(selected_records, st.session_state.file_op_rename_template)
        if previews:
            st.table(pd.DataFrame(previews))
        if st.button("Rename Selected"):
            kind, message, _, mutated = file_ops.rename_files(
                selected_records,
                st.session_state.file_op_rename_template,
                st.session_state.file_op_overwrite
            )
            if mutated:
                _invalidate_loaded_file(mutated)
            _set_file_op_feedback(kind, message)

        st.divider()
        st.session_state.file_op_delete_confirm = st.text_input(
            "Type DELETE to confirm",
            st.session_state.file_op_delete_confirm
        )
        delete_disabled = st.session_state.file_op_delete_confirm.strip().upper() != "DELETE"
        if st.button("Delete Selected", disabled=delete_disabled):
            kind, message, _, mutated = file_ops.delete_files(selected_records)
            if kind == 'success':
                st.session_state.file_op_delete_confirm = ""
            if mutated:
                _invalidate_loaded_file(mutated)
            _set_file_op_feedback(kind, message)

        feedback = st.session_state.get('file_op_feedback')
        if feedback:
            feedback_kind = feedback.get('kind', 'info')
            feedback_message = feedback.get('message', '')
            getattr(st, feedback_kind, st.info)(feedback_message)


def _option_index(options, value, default=0):
    if not options:
        return 0
    try:
        return options.index(value)
    except ValueError:
        return default


def _ensure_plot_state(file_key):
    manager = st.session_state.get('plot_state_manager')
    if not manager:
        st.session_state.plot_state = deepcopy(DEFAULT_PLOT_STATE)
    else:
        st.session_state.plot_state = manager.get(file_key)
    st.session_state.plot_state_file_key = file_key


def _current_plot_file_key():
    return st.session_state.get('plot_state_file_key') or st.session_state.get('selected_file')


def _save_current_plot_state():
    file_key = _current_plot_file_key()
    state = st.session_state.get('plot_state')
    manager = st.session_state.get('plot_state_manager')
    if file_key and state and manager:
        manager.update(file_key, state)


def _parse_date_input(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _format_size(size_bytes):
    return f"{size_bytes / 1024:.1f} KB"


def _touchstone_files_in_df(file_df):
    if file_df is None or file_df.empty:
        return []
    mask = file_df['Extension'].str.lower().isin(TOUCHSTONE_EXTENSIONS)
    return file_df[mask]['Path'].tolist()


def _load_touchstone_file(path):
    try:
        data = plotting_utils.load_touchstone(path)
        st.session_state.sparam_data = data
        st.session_state.sparam_source = path
        st.session_state.sparam_selection = []
        return True, None
    except Exception as exc:
        st.session_state.sparam_data = None
        st.session_state.sparam_source = None
        return False, str(exc)


def _touchstone_selection_options(data):
    if not data:
        return []
    labels = plotting_utils.get_sparameter_labels(data)
    return labels


def _saved_filter_options(category):
    options = [SAVED_FILTER_PLACEHOLDER]
    manager = _settings_manager()
    if manager:
        options.extend(manager.get_saved_filters(category))
    return options


def _render_saved_filter_selector(label, category, selection_key, target_state_key, container):
    options = _saved_filter_options(category)
    current_selection = st.session_state.get(selection_key, SAVED_FILTER_PLACEHOLDER)
    selected_value = container.selectbox(
        label,
        options,
        index=_option_index(options, current_selection, 0)
    )
    if selected_value != current_selection:
        st.session_state[selection_key] = selected_value
        if selected_value != SAVED_FILTER_PLACEHOLDER:
            st.session_state[target_state_key] = selected_value
    return selected_value


def _save_filter_preset(category, value):
    manager = _settings_manager()
    if manager and value:
        manager.add_saved_filter(category, value)
        state_key = f"saved_{category}_filter_select"
        if state_key in st.session_state:
            st.session_state[state_key] = value
        return True
    return False


def _recent_directory_options():
    options = [RECENT_DIR_PLACEHOLDER]
    manager = _settings_manager()
    if manager:
        options.extend(manager.get_recent_directories())
    return options


def _remember_directory(directory):
    manager = _settings_manager()
    if manager and directory:
        manager.add_recent_directory(directory)


def _get_plot_state(path, default=None):
    state = st.session_state.get('plot_state')
    if not state:
        return default
    current = state
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _set_plot_state(path, value, persist=True):
    if 'plot_state' not in st.session_state or st.session_state.plot_state is None:
        st.session_state.plot_state = deepcopy(DEFAULT_PLOT_STATE)
    current = st.session_state.plot_state
    for key in path[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[path[-1]] = value
    if persist:
        _save_current_plot_state()


def _render_general_plots(filtered_df, numeric_cols, all_cols):
    general_state = _get_plot_state(['general'], {}) or {}
    plot_options = [
        "Scatter",
        "Line",
        "Histogram",
        "Bar",
        "BarH",
        "Pie",
        "Area",
        "Density",
        "Box",
        "Violin",
        "Dot",
        "Heatmap",
        "Hexbin",
        "Contour",
        "Imshow",
        "Scatter Matrix",
        "Radviz",
        "Venn",
        "Gantt"
    ]
    selected_type = general_state.get('plot_type', 'Scatter')
    plot_type = st.selectbox(
        "Plot Type",
        plot_options,
        index=_option_index(plot_options, selected_type, 0)
    )
    if plot_type != selected_type:
        _set_plot_state(['general', 'plot_type'], plot_type)

    if not numeric_cols:
        st.info("No numeric columns available for plotting.")
        return

    # Continuous numeric-only plots
    if plot_type == "Scatter":
        if len(numeric_cols) < 2:
            st.info("Select at least two numeric columns for scatter plots.")
            return
        scatter_state = general_state.get('scatter', {})
        col1, col2, col3 = st.columns(3)
        x_default = scatter_state.get('x') or numeric_cols[0]
        y_default = scatter_state.get('y') or (numeric_cols[1] if len(numeric_cols) > 1 else numeric_cols[0])
        c_options = [None] + numeric_cols
        c_default = scatter_state.get('color')
        x_col = col1.selectbox("X Axis", numeric_cols, index=_option_index(numeric_cols, x_default, 0))
        y_col = col2.selectbox("Y Axis", numeric_cols, index=_option_index(numeric_cols, y_default, 0))
        c_idx = _option_index(c_options, c_default, 0)
        color_col = col3.selectbox("Color", c_options, index=c_idx)

        if x_col != scatter_state.get('x'):
            _set_plot_state(['general', 'scatter', 'x'], x_col)
        if y_col != scatter_state.get('y'):
            _set_plot_state(['general', 'scatter', 'y'], y_col)
        if color_col != scatter_state.get('color'):
            _set_plot_state(['general', 'scatter', 'color'], color_col)

        if st.button("Generate Scatter Plot"):
            fig = plotting_utils.plot_scatter(filtered_df, x_col, y_col, color_col)
            st.pyplot(fig)

    elif plot_type == "Line":
        line_state = general_state.get('line', {})
        default_x = line_state.get('x') or numeric_cols[0]
        stored_ys = line_state.get('ys', []) or ([numeric_cols[1]] if len(numeric_cols) > 1 else [])
        col1, col2 = st.columns(2)
        x_col = col1.selectbox("X Axis", numeric_cols, index=_option_index(numeric_cols, default_x, 0))
        default_selected = [col for col in stored_ys if col in numeric_cols]
        if not default_selected and len(numeric_cols) > 1:
            default_selected = [numeric_cols[1]]
        y_cols = col2.multiselect("Y Axis", numeric_cols, default=default_selected)

        if x_col != line_state.get('x'):
            _set_plot_state(['general', 'line', 'x'], x_col)
        if y_cols != line_state.get('ys'):
            _set_plot_state(['general', 'line', 'ys'], y_cols)

        if y_cols and st.button("Generate Line Plot"):
            fig = plotting_utils.plot_line(filtered_df, x_col, y_cols)
            st.pyplot(fig)
        elif not y_cols:
            st.info("Select at least one Y column for line plots.")

    elif plot_type == "Histogram":
        hist_state = general_state.get('histogram', {})
        default_col = hist_state.get('column') or numeric_cols[0]
        bins_state = hist_state.get('bins', 20)
        col = st.selectbox("Column", numeric_cols, index=_option_index(numeric_cols, default_col, 0))
        bins = st.slider("Bins", 5, 100, int(bins_state))
        if col != hist_state.get('column'):
            _set_plot_state(['general', 'histogram', 'column'], col)
        if bins != bins_state:
            _set_plot_state(['general', 'histogram', 'bins'], bins)
        if st.button("Generate Histogram"):
            fig = plotting_utils.plot_histogram(filtered_df, col, bins)
            st.pyplot(fig)

    elif plot_type == "Bar":
        bar_state = general_state.get('bar', {})
        category_cols = all_cols
        if not category_cols:
            st.info("No columns available for bar charts.")
            return
        numeric_for_value = numeric_cols
        if not numeric_for_value:
            st.info("Need at least one numeric column for bar values.")
            return
        default_category = bar_state.get('category') or category_cols[0]
        default_value = bar_state.get('value') or numeric_for_value[0]
        agg_options = ["Sum", "Mean", "Median", "Count"]
        default_agg = bar_state.get('agg', 'Sum')

        col1, col2, col3 = st.columns(3)
        category = col1.selectbox("Category", category_cols, index=_option_index(category_cols, default_category, 0))
        value = col2.selectbox("Value", numeric_for_value, index=_option_index(numeric_for_value, default_value, 0))
        agg_choice = col3.selectbox("Aggregation", agg_options, index=_option_index(agg_options, default_agg, 0))

        if category != bar_state.get('category'):
            _set_plot_state(['general', 'bar', 'category'], category)
        if value != bar_state.get('value'):
            _set_plot_state(['general', 'bar', 'value'], value)
        if agg_choice != bar_state.get('agg'):
            _set_plot_state(['general', 'bar', 'agg'], agg_choice)

        if st.button("Generate Bar Plot"):
            fig = plotting_utils.plot_bar(filtered_df, category, value, agg_choice)
            st.pyplot(fig)

    elif plot_type == "BarH":
        barh_state = general_state.get('barh', {})
        category_cols = all_cols
        numeric_for_value = numeric_cols
        if not category_cols or not numeric_for_value:
            st.info("Need categorical and numeric columns for barh plots.")
            return
        category = st.selectbox(
            "Category",
            category_cols,
            index=_option_index(category_cols, barh_state.get('category') or category_cols[0], 0)
        )
        value = st.selectbox(
            "Value",
            numeric_for_value,
            index=_option_index(numeric_for_value, barh_state.get('value') or numeric_for_value[0], 0)
        )
        agg_options = ["Sum", "Mean", "Median", "Count"]
        agg_choice = st.selectbox(
            "Aggregation",
            agg_options,
            index=_option_index(agg_options, barh_state.get('agg', 'Sum'), 0)
        )
        _set_plot_state(['general', 'barh'], {"category": category, "value": value, "agg": agg_choice}, persist=False)
        if st.button("Generate Horizontal Bar Plot"):
            fig = plotting_utils.plot_barh(filtered_df, category, value, agg_choice)
            st.pyplot(fig)

    elif plot_type == "Pie":
        pie_state = general_state.get('pie', {})
        category_cols = all_cols
        numeric_for_value = numeric_cols
        if not category_cols or not numeric_for_value:
            st.info("Need categorical and numeric columns for pie charts.")
            return
        category = st.selectbox(
            "Category",
            category_cols,
            index=_option_index(category_cols, pie_state.get('category') or category_cols[0], 0)
        )
        value = st.selectbox(
            "Value",
            numeric_for_value,
            index=_option_index(numeric_for_value, pie_state.get('value') or numeric_for_value[0], 0)
        )
        agg_options = ["Sum", "Mean", "Median", "Count"]
        agg_choice = st.selectbox(
            "Aggregation",
            agg_options,
            index=_option_index(agg_options, pie_state.get('agg', 'Sum'), 0)
        )
        _set_plot_state(['general', 'pie'], {"category": category, "value": value, "agg": agg_choice}, persist=False)
        if st.button("Generate Pie Chart"):
            fig = plotting_utils.plot_pie(filtered_df, category, value, agg_choice)
            st.pyplot(fig)

    elif plot_type == "Area":
        area_state = general_state.get('area', {})
        columns = st.multiselect("Columns", numeric_cols, default=area_state.get('columns') or numeric_cols[:2])
        stacked = st.checkbox("Stacked", value=area_state.get('stacked', True))
        _set_plot_state(['general', 'area'], {"columns": columns, "stacked": stacked}, persist=False)
        if columns and st.button("Generate Area Plot"):
            fig = plotting_utils.plot_area(filtered_df, columns, stacked)
            st.pyplot(fig)
        elif not columns:
            st.info("Select at least one column.")

    elif plot_type == "Density":
        density_state = general_state.get('density', {})
        columns = st.multiselect("Columns", numeric_cols, default=density_state.get('columns') or numeric_cols[:1])
        bw_method = st.selectbox("Bandwidth", ["scott", "silverman", "0.2", "0.5", "1.0"], index=_option_index(["scott", "silverman", "0.2", "0.5", "1.0"], density_state.get('bw_method', 'scott'), 0))
        fill = st.checkbox("Fill", value=density_state.get('fill', False))
        show_rug = st.checkbox("Rug", value=density_state.get('show_rug', False))
        _set_plot_state(['general', 'density'], {"columns": columns, "bw_method": bw_method, "fill": fill, "show_rug": show_rug}, persist=False)
        if columns and st.button("Generate Density Plot"):
            fig = plotting_utils.plot_density(filtered_df, columns, bw_method=bw_method, fill=fill, show_rug=show_rug)
            st.pyplot(fig)
        elif not columns:
            st.info("Select at least one column.")

    elif plot_type == "Box":
        box_state = general_state.get('box', {})
        columns = st.multiselect("Columns", numeric_cols, default=box_state.get('columns') or numeric_cols[:2])
        _set_plot_state(['general', 'box'], {"columns": columns}, persist=False)
        if columns and st.button("Generate Box Plot"):
            fig = plotting_utils.plot_box(filtered_df, columns)
            st.pyplot(fig)
        elif not columns:
            st.info("Select at least one column.")

    elif plot_type == "Violin":
        violin_state = general_state.get('violin', {})
        columns = st.multiselect("Columns", numeric_cols, default=violin_state.get('columns') or numeric_cols[:2])
        _set_plot_state(['general', 'violin'], {"columns": columns}, persist=False)
        if columns and st.button("Generate Violin Plot"):
            fig = plotting_utils.plot_violin(filtered_df, columns)
            st.pyplot(fig)
        elif not columns:
            st.info("Select at least one column.")

    elif plot_type == "Dot":
        dot_state = general_state.get('dot', {})
        category_cols = all_cols
        value_cols = numeric_cols
        if not category_cols or not value_cols:
            st.info("Need categorical and numeric columns for dot plots.")
            return
        category = st.selectbox(
            "Category",
            category_cols,
            index=_option_index(category_cols, dot_state.get('category') or category_cols[0], 0)
        )
        value = st.selectbox(
            "Value",
            value_cols,
            index=_option_index(value_cols, dot_state.get('value') or value_cols[0], 0)
        )
        agg_options = ["Sum", "Mean", "Median", "Count"]
        agg_choice = st.selectbox(
            "Aggregation",
            agg_options,
            index=_option_index(agg_options, dot_state.get('agg', 'Sum'), 0)
        )
        _set_plot_state(['general', 'dot'], {"category": category, "value": value, "agg": agg_choice}, persist=False)
        if st.button("Generate Dot Plot"):
            fig = plotting_utils.plot_dot(filtered_df, category, value, agg_choice)
            st.pyplot(fig)

    elif plot_type == "Heatmap":
        heatmap_state = general_state.get('heatmap', {})
        columns = st.multiselect("Columns", numeric_cols, default=heatmap_state.get('columns') or numeric_cols[:3])
        _set_plot_state(['general', 'heatmap'], {"columns": columns}, persist=False)
        if columns and st.button("Generate Heatmap"):
            fig = plotting_utils.plot_heatmap(filtered_df, columns)
            st.pyplot(fig)
        elif not columns:
            st.info("Select at least one column.")

    elif plot_type == "Hexbin":
        hex_state = general_state.get('hexbin', {})
        if len(numeric_cols) < 2:
            st.info("Select at least two numeric columns for hexbin.")
            return
        col1, col2 = st.columns(2)
        x_col = col1.selectbox("X", numeric_cols, index=_option_index(numeric_cols, hex_state.get('x') or numeric_cols[0], 0))
        y_col = col2.selectbox("Y", numeric_cols, index=_option_index(numeric_cols, hex_state.get('y') or numeric_cols[1], 0))
        gridsize = st.slider("Grid Size", 10, 100, int(hex_state.get('gridsize', 30)))
        _set_plot_state(['general', 'hexbin'], {"x": x_col, "y": y_col, "gridsize": gridsize}, persist=False)
        if st.button("Generate Hexbin Plot"):
            fig = plotting_utils.plot_hexbin(filtered_df, x_col, y_col, gridsize)
            st.pyplot(fig)

    elif plot_type == "Contour":
        contour_state = general_state.get('contour', {})
        if len(numeric_cols) < 3:
            st.info("Select at least three numeric columns for contour plots.")
            return
        col1, col2, col3 = st.columns(3)
        x_col = col1.selectbox("X", numeric_cols, index=_option_index(numeric_cols, contour_state.get('x') or numeric_cols[0], 0))
        y_col = col2.selectbox("Y", numeric_cols, index=_option_index(numeric_cols, contour_state.get('y') or numeric_cols[1], 0))
        z_col = col3.selectbox("Z", numeric_cols, index=_option_index(numeric_cols, contour_state.get('z') or numeric_cols[2], 0))
        levels = st.slider("Levels", 5, 30, int(contour_state.get('levels', 10)))
        _set_plot_state(['general', 'contour'], {"x": x_col, "y": y_col, "z": z_col, "levels": levels}, persist=False)
        if st.button("Generate Contour Plot"):
            fig = plotting_utils.plot_contour(filtered_df, x_col, y_col, z_col, levels)
            st.pyplot(fig)

    elif plot_type == "Imshow":
        im_state = general_state.get('imshow', {})
        columns = st.multiselect("Columns", numeric_cols, default=im_state.get('columns') or numeric_cols[:3])
        _set_plot_state(['general', 'imshow'], {"columns": columns}, persist=False)
        if columns and st.button("Generate Imshow Plot"):
            fig = plotting_utils.plot_imshow(filtered_df, columns)
            st.pyplot(fig)
        elif not columns:
            st.info("Select at least one column.")

    elif plot_type == "Scatter Matrix":
        sm_state = general_state.get('scatter_matrix', {})
        columns = st.multiselect("Columns", numeric_cols, default=sm_state.get('columns') or numeric_cols[:3])
        _set_plot_state(['general', 'scatter_matrix'], {"columns": columns}, persist=False)
        if len(columns) >= 2 and st.button("Generate Scatter Matrix"):
            fig = plotting_utils.plot_scatter_matrix(filtered_df, columns)
            st.pyplot(fig)
        elif len(columns) < 2:
            st.info("Select at least two columns.")

    elif plot_type == "Radviz":
        radviz_state = general_state.get('radviz', {})
        columns = st.multiselect("Columns", numeric_cols, default=radviz_state.get('columns') or numeric_cols[:3])
        class_column = st.selectbox("Class Column", all_cols, index=_option_index(all_cols, radviz_state.get('class_column') or all_cols[0], 0))
        _set_plot_state(['general', 'radviz'], {"columns": columns, "class_column": class_column}, persist=False)
        if columns and class_column and st.button("Generate Radviz Plot"):
            try:
                fig = plotting_utils.plot_radviz(filtered_df, columns, class_column)
                st.pyplot(fig)
            except ValueError as err:
                st.error(str(err))
        elif not columns:
            st.info("Select at least one column plus a class column.")

    elif plot_type == "Venn":
        venn_state = general_state.get('venn', {})
        columns = st.multiselect("Columns (2 or 3)", all_cols, default=venn_state.get('sets') or all_cols[:2])
        _set_plot_state(['general', 'venn'], {"sets": columns}, persist=False)
        if 2 <= len(columns) <= 3 and st.button("Generate Venn Diagram"):
            try:
                fig = plotting_utils.plot_venn(filtered_df, columns)
                st.pyplot(fig)
            except ValueError as err:
                st.error(str(err))
        elif len(columns) not in (2, 3):
            st.info("Select 2 or 3 columns.")

    elif plot_type == "Gantt":
        gantt_state = general_state.get('gantt', {})
        if not all_cols:
            st.info("No columns available for Gantt charts.")
            return
        task_col = st.selectbox(
            "Task Column",
            all_cols,
            index=_option_index(all_cols, gantt_state.get('task') or all_cols[0], 0)
        )
        start_col = st.selectbox(
            "Start Date Column",
            all_cols,
            index=_option_index(all_cols, gantt_state.get('start') or all_cols[0], 0)
        )
        end_col = st.selectbox(
            "End Date Column",
            all_cols,
            index=_option_index(all_cols, gantt_state.get('end') or all_cols[0], 0)
        )
        optional_cols = ["-- None --"] + all_cols
        group_selection = st.selectbox(
            "Group Column (optional)",
            optional_cols,
            index=_option_index(optional_cols, gantt_state.get('group') or "-- None --", 0)
        )
        progress_selection = st.selectbox(
            "Progress Column (0-1, optional)",
            optional_cols,
            index=_option_index(optional_cols, gantt_state.get('progress') or "-- None --", 0)
        )

        _set_plot_state(['general', 'gantt'], {
            "task": task_col,
            "start": start_col,
            "end": end_col,
            "group": None if group_selection == "-- None --" else group_selection,
            "progress": None if progress_selection == "-- None --" else progress_selection,
        }, persist=False)

        if st.button("Generate Gantt Chart"):
            try:
                fig = plotting_utils.plot_gantt(
                    filtered_df,
                    task_col,
                    start_col,
                    end_col,
                    group_col=None if group_selection == "-- None --" else group_selection,
                    progress_col=None if progress_selection == "-- None --" else progress_selection,
                )
                st.pyplot(fig)
            except ValueError as exc:
                st.error(str(exc))

    elif plot_type == "S-Parameters":
        file_df = st.session_state.get('file_browser_df')
        touchstone_paths = _touchstone_files_in_df(file_df)
        uploaded_file = st.file_uploader("Upload Touchstone (.sNp) file", type=[ext[1:] for ext in TOUCHSTONE_EXTENSIONS])
        ts_options = [TOUCHSTONE_FILE_PLACEHOLDER] + touchstone_paths
        selected_path = st.selectbox(
            "Select Touchstone from browser",
            ts_options,
            index=_option_index(ts_options, st.session_state.get('sparam_file_option', TOUCHSTONE_FILE_PLACEHOLDER), 0),
            key="special_sparam_file_select",
        )
        if selected_path != st.session_state.get('sparam_file_option'):
            st.session_state.sparam_file_option = selected_path
            if selected_path != TOUCHSTONE_FILE_PLACEHOLDER:
                success, error = _load_touchstone_file(selected_path)
                if not success and error:
                    st.error(f"Failed to load Touchstone: {error}")
        if uploaded_file is not None:
            success, error = _load_touchstone_file(uploaded_file)
            if not success and error:
                st.error(f"Failed to load uploaded Touchstone: {error}")

        sparam_data = st.session_state.get('sparam_data')
        if not sparam_data:
            st.info("Upload or select a Touchstone file to enable S-parameter plotting.")
            return

        labels = _touchstone_selection_options(sparam_data)
        default_selection = st.session_state.get('sparam_selection') or labels[:1]
        selection = st.multiselect("S-Parameters", labels, default=default_selection, key="special_sparam_selection")
        parsed_selection = []
        for label in selection:
            match = re.match(r"S(\d)(\d)", label)
            if match:
                parsed_selection.append((int(match.group(1)), int(match.group(2))))
        st.session_state.sparam_selection = selection

        mode_display = plotting_utils.TOUCHSTONE_DISPLAY_MODES
        display_options = [(value, key) for key, value in mode_display.items()]
        display_labels = [label for label, _ in display_options]
        current_mode = st.session_state.get('sparam_display_mode', 'mag_db')
        mode_index = next((idx for idx, (_, key) in enumerate(display_options) if key == current_mode), 0)
        selected_label = st.selectbox("Display Mode", display_labels, index=mode_index, key="special_sparam_display_mode")
        selected_mode = display_options[display_labels.index(selected_label)][1]
        if selected_mode != current_mode:
            st.session_state.sparam_display_mode = selected_mode

        log_freq = st.checkbox("Log Frequency Axis", value=bool(special_state.get('sparam_log_freq', True)))
        _set_plot_state(['special', 'sparam_log_freq'], log_freq, persist=False)

        if selection and st.button("Plot S-Parameters"):
            try:
                fig = plotting_utils.plot_s_parameters(
                    sparam_data,
                    parsed_selection,
                    display_mode=selected_mode,
                    log_freq=log_freq,
                )
                st.pyplot(fig)
            except ValueError as exc:
                st.error(str(exc))
        elif not selection:
            st.info("Select at least one S-parameter trace.")

    elif plot_type == "Jitter":
        if not numeric_cols:
            st.info("No numeric columns available for jitter plots.")
            return
        jitter_state = special_state.get('jitter', {})
        column = st.selectbox(
            "Jitter Column",
            numeric_cols,
            index=_option_index(numeric_cols, jitter_state.get('column') or numeric_cols[0], 0),
            key="special_jitter_column",
        )
        bins = st.slider("Bins", 10, 200, int(jitter_state.get('bins', 50)))
        show_gaussian = st.checkbox("Show Gaussian Fit", value=jitter_state.get('show_gaussian', True))
        show_stats = st.checkbox("Show Stats", value=jitter_state.get('show_stats', True))

        _set_plot_state(['special', 'jitter'], {
            "column": column,
            "bins": bins,
            "show_gaussian": show_gaussian,
            "show_stats": show_stats,
        }, persist=False)

        if st.button("Generate Jitter Plot"):
            try:
                fig = plotting_utils.plot_jitter(
                    filtered_df,
                    column,
                    bins=bins,
                    show_gaussian=show_gaussian,
                    show_stats=show_stats,
                )
                st.pyplot(fig)
            except ValueError as exc:
                st.error(str(exc))

    elif plot_type == "Phase Noise":
        if len(numeric_cols) < 2:
            st.info("Select at least two numeric columns for phase noise plots.")
            return
        phase_state = special_state.get('phase_noise', {})
        freq_col = st.selectbox(
            "Offset Frequency Column",
            numeric_cols,
            index=_option_index(numeric_cols, phase_state.get('freq_col') or numeric_cols[0], 0),
            key="special_phase_noise_freq",
        )
        noise_col = st.selectbox(
            "Phase Noise Column (dBc/Hz)",
            numeric_cols,
            index=_option_index(numeric_cols, phase_state.get('noise_col') or numeric_cols[1], 0),
            key="special_phase_noise_value",
        )
        carrier_hz = st.number_input(
            "Carrier Frequency (Hz)",
            min_value=1e3,
            max_value=1e13,
            value=float(phase_state.get('carrier_hz', 1e9)),
            step=1e6,
            format="%.0f"
        )

        _set_plot_state(['special', 'phase_noise'], {
            "freq_col": freq_col,
            "noise_col": noise_col,
            "carrier_hz": carrier_hz,
        }, persist=False)

        if st.button("Generate Phase Noise Plot"):
            try:
                fig = plotting_utils.plot_phase_noise(
                    filtered_df,
                    freq_col,
                    noise_col,
                    carrier_hz=carrier_hz,
                )
                st.pyplot(fig)
            except ValueError as exc:
                st.error(str(exc))


def _render_correlation_tab(filtered_df, numeric_cols):
    if not numeric_cols:
        st.info("No numeric columns available for correlation analysis.")
        return
    corr_state = _get_plot_state(['correlation'], {}) or {}
    default_target = corr_state.get('target') or numeric_cols[0]
    target_col = st.selectbox(
        "Target Column",
        numeric_cols,
        index=_option_index(numeric_cols, default_target, 0)
    )
    if target_col != corr_state.get('target'):
        _set_plot_state(['correlation', 'target'], target_col)

    top_n_default = int(corr_state.get('top_n', 5))
    top_n = st.number_input("Top N", 1, 20, top_n_default)
    if top_n != corr_state.get('top_n'):
        _set_plot_state(['correlation', 'top_n'], int(top_n))

    if st.button("Analyze Correlations"):
        corr_df, _ = plotting_utils.get_top_correlated_columns(filtered_df, target_col, int(top_n))
        if corr_df is not None:
            st.dataframe(corr_df)
            if not corr_df.empty:
                top_corr_col = corr_df.iloc[0]['Column']
                top_corr_val = corr_df.iloc[0]['Correlation']
                st.write(f"Top correlation: {top_corr_col} ({top_corr_val:.3f})")
                fig = plotting_utils.plot_correlation(filtered_df, target_col, top_corr_col, top_corr_val)
                st.pyplot(fig)


def _render_special_plots(filtered_df, numeric_cols):
    special_state = _get_plot_state(['special'], {}) or {}
    plot_type_options = [
        "Shmoo",
        "Bathtub",
        "Eye Diagram",
        "3D Plot",
        "S-Parameters",
        "Jitter",
        "Phase Noise",
    ]
    selected_type = special_state.get('plot_type', 'Shmoo')
    plot_type = st.selectbox(
        "Special Plot Type",
        plot_type_options,
        index=_option_index(plot_type_options, selected_type, 0),
        key="special_plot_type_select",
    )
    if plot_type != selected_type:
        _set_plot_state(['special', 'plot_type'], plot_type)

    if plot_type == "Shmoo":
        if len(numeric_cols) < 3:
            st.info("Select at least three numeric columns for shmoo plots.")
            return
        shmoo_state = special_state.get('shmoo', {})
        col1, col2, col3 = st.columns(3)
        x_col = col1.selectbox("X Param", numeric_cols, index=_option_index(numeric_cols, shmoo_state.get('x') or numeric_cols[0], 0), key="special_shmoo_x")
        y_col = col2.selectbox("Y Param", numeric_cols, index=_option_index(numeric_cols, shmoo_state.get('y') or numeric_cols[1], 0), key="special_shmoo_y")
        z_col = col3.selectbox("Z Param", numeric_cols, index=_option_index(numeric_cols, shmoo_state.get('z') or numeric_cols[2], 0), key="special_shmoo_z")
        if x_col != shmoo_state.get('x'):
            _set_plot_state(['special', 'shmoo', 'x'], x_col)
        if y_col != shmoo_state.get('y'):
            _set_plot_state(['special', 'shmoo', 'y'], y_col)
        if z_col != shmoo_state.get('z'):
            _set_plot_state(['special', 'shmoo', 'z'], z_col)

        col4, col5 = st.columns(2)
        t_min = col4.text_input("Threshold Min", shmoo_state.get('threshold_min', ""))
        t_max = col5.text_input("Threshold Max", shmoo_state.get('threshold_max', ""))
        if t_min != shmoo_state.get('threshold_min'):
            _set_plot_state(['special', 'shmoo', 'threshold_min'], t_min)
        if t_max != shmoo_state.get('threshold_max'):
            _set_plot_state(['special', 'shmoo', 'threshold_max'], t_max)

        if st.button("Generate Shmoo Plot"):
            t_min_val = float(t_min) if t_min else None
            t_max_val = float(t_max) if t_max else None
            fig = plotting_utils.plot_shmoo(filtered_df, x_col, y_col, z_col, t_min_val, t_max_val)
            st.pyplot(fig)

    elif plot_type == "Bathtub":
        if len(numeric_cols) < 2:
            st.info("Select at least two numeric columns for bathtub plots.")
            return
        bath_state = special_state.get('bathtub', {})
        col1, col2 = st.columns(2)
        x_col = col1.selectbox("X Axis (Sample Point)", numeric_cols, index=_option_index(numeric_cols, bath_state.get('x') or numeric_cols[0], 0), key="special_bathtub_x")
        default_ys = bath_state.get('ys', [])
        default_selected = [col for col in default_ys if col in numeric_cols]
        if not default_selected:
            default_selected = numeric_cols[1:2]
        y_cols = col2.multiselect("Y Axis (BER)", numeric_cols, default=default_selected, key="special_bathtub_y")
        target_text = st.text_input("BER Target", bath_state.get('target', "1e-12"))

        if x_col != bath_state.get('x'):
            _set_plot_state(['special', 'bathtub', 'x'], x_col)
        if y_cols != bath_state.get('ys'):
            _set_plot_state(['special', 'bathtub', 'ys'], y_cols)
        if target_text != bath_state.get('target'):
            _set_plot_state(['special', 'bathtub', 'target'], target_text)

        if y_cols and st.button("Generate Bathtub Plot"):
            try:
                target_val = float(target_text)
            except ValueError:
                st.error("Enter a valid numeric BER target.")
                return
            fig = plotting_utils.plot_bathtub(filtered_df, x_col, y_cols, target_val)
            st.pyplot(fig)
        elif not y_cols:
            st.info("Select at least one BER column.")

    elif plot_type == "Eye Diagram":
        if len(numeric_cols) < 2:
            st.info("Select at least two numeric columns for eye diagrams.")
            return
        eye_state = special_state.get('eye', {})
        col1, col2 = st.columns(2)
        time_col = col1.selectbox("Time Column", numeric_cols, index=_option_index(numeric_cols, eye_state.get('time') or numeric_cols[0], 0), key="special_eye_time")
        voltage_col = col2.selectbox("Voltage Column", numeric_cols, index=_option_index(numeric_cols, eye_state.get('voltage') or numeric_cols[1], 0), key="special_eye_voltage")
        ui_default = float(eye_state.get('ui', 1.0))
        ui_value = st.slider("UI Width", 0.1, 2.0, float(ui_default), 0.1)

        if time_col != eye_state.get('time'):
            _set_plot_state(['special', 'eye', 'time'], time_col)
        if voltage_col != eye_state.get('voltage'):
            _set_plot_state(['special', 'eye', 'voltage'], voltage_col)
        if ui_value != eye_state.get('ui'):
            _set_plot_state(['special', 'eye', 'ui'], ui_value)

        if st.button("Generate Eye Diagram"):
            fig = plotting_utils.plot_eye(filtered_df, time_col, voltage_col, ui_value)
            st.pyplot(fig)

    elif plot_type == "3D Plot":
        if len(numeric_cols) < 3:
            st.info("Select at least three numeric columns for 3D plots.")
            return
        three_state = special_state.get('three_d', {})
        mode_options = ["Scatter", "Surface", "Wireframe"]
        colormap_options = ["viridis", "plasma", "inferno", "magma", "cividis"]

        mode = st.selectbox(
            "3D Mode",
            mode_options,
            index=_option_index(mode_options, three_state.get('mode', 'Scatter'), 0),
            key="special_three_d_mode",
        )
        if mode != three_state.get('mode'):
            _set_plot_state(['special', 'three_d', 'mode'], mode)

        col1, col2, col3 = st.columns(3)
        x_col = col1.selectbox("X Axis", numeric_cols, index=_option_index(numeric_cols, three_state.get('x') or numeric_cols[0], 0), key="special_three_d_x")
        y_col = col2.selectbox("Y Axis", numeric_cols, index=_option_index(numeric_cols, three_state.get('y') or numeric_cols[1], 0), key="special_three_d_y")
        z_col = col3.selectbox("Z Axis", numeric_cols, index=_option_index(numeric_cols, three_state.get('z') or numeric_cols[2], 0), key="special_three_d_z")
        if x_col != three_state.get('x'):
            _set_plot_state(['special', 'three_d', 'x'], x_col)
        if y_col != three_state.get('y'):
            _set_plot_state(['special', 'three_d', 'y'], y_col)
        if z_col != three_state.get('z'):
            _set_plot_state(['special', 'three_d', 'z'], z_col)

        colormap = st.selectbox(
            "Colormap",
            colormap_options,
            index=_option_index(colormap_options, three_state.get('colormap', 'viridis'), 0),
            key="special_three_d_colormap",
        )
        if colormap != three_state.get('colormap'):
            _set_plot_state(['special', 'three_d', 'colormap'], colormap)

        log_z = st.checkbox("Log-scale Z axis", value=three_state.get('log_z', False))
        if log_z != three_state.get('log_z'):
            _set_plot_state(['special', 'three_d', 'log_z'], log_z)

        stride = st.slider("Stride", 1, 10, int(three_state.get('stride', 2))) if mode != "Scatter" else three_state.get('stride', 2)
        resolution = st.slider("Grid Resolution", 20, 100, int(three_state.get('resolution', 50))) if mode != "Scatter" else three_state.get('resolution', 50)
        show_points = st.checkbox("Overlay original points", value=three_state.get('show_points', False)) if mode != "Scatter" else three_state.get('show_points', False)

        if mode != "Scatter":
            if stride != three_state.get('stride'):
                _set_plot_state(['special', 'three_d', 'stride'], stride)
            if resolution != three_state.get('resolution'):
                _set_plot_state(['special', 'three_d', 'resolution'], resolution)
            if show_points != three_state.get('show_points'):
                _set_plot_state(['special', 'three_d', 'show_points'], show_points)

        button_label = f"Generate {mode} 3D Plot"
        if st.button(button_label):
            try:
                if mode == "Scatter":
                    fig = plotting_utils.plot_scatter3d(
                        filtered_df,
                        x_col,
                        y_col,
                        z_col,
                        colormap=colormap,
                        log_z=log_z,
                    )
                elif mode == "Surface":
                    fig = plotting_utils.plot_surface3d(
                        filtered_df,
                        x_col,
                        y_col,
                        z_col,
                        colormap=colormap,
                        log_z=log_z,
                        stride=stride,
                        show_points=show_points,
                        grid_resolution=resolution,
                    )
                else:
                    fig = plotting_utils.plot_wireframe3d(
                        filtered_df,
                        x_col,
                        y_col,
                        z_col,
                        colormap=colormap,
                        log_z=log_z,
                        stride=stride,
                        show_points=show_points,
                        grid_resolution=resolution,
                    )
                st.pyplot(fig)
            except ValueError as exc:
                st.error(str(exc))


def _render_plot_state_controls():
    st.markdown("### Plot State Management")
    file_key = _current_plot_file_key()
    manager: PlotStateManager | None = st.session_state.get('plot_state_manager')
    if not file_key or not manager:
        st.info("Select a file to manage plot settings.")
        return

    col1, col2, col3 = st.columns(3)
    reset_clicked = col1.button("Reset to Defaults")
    export_placeholder = col2.empty()
    import_placeholder = col3.empty()

    if reset_clicked:
        new_state = manager.reset(file_key)
        st.session_state.plot_state = new_state
        st.success("Plot settings reset to defaults for this file.")

    export_state = _get_plot_state([], {}) or {}
    if export_state:
        export_placeholder.download_button(
            label="Export Settings",
            data=json.dumps(export_state, indent=2),
            file_name=f"plot_settings_{Path(file_key).stem}.json",
            mime="application/json"
        )

    uploaded_file = import_placeholder.file_uploader("Import Settings", type="json")
    if uploaded_file is not None:
        try:
            payload = json.load(uploaded_file)
            new_state = manager.import_state(file_key, payload)
            st.session_state.plot_state = new_state
            st.success("Plot settings imported.")
        except Exception as exc:
            st.error(f"Failed to import settings: {exc}")

# --- Sidebar: File Browser ---
st.sidebar.title("File Browser")

# Directory Selection
recent_options = _recent_directory_options()
selected_recent = st.sidebar.selectbox(
    "Recent Directories",
    recent_options,
    index=_option_index(recent_options, st.session_state.recent_dir_select, 0)
)
if selected_recent != st.session_state.recent_dir_select and selected_recent != RECENT_DIR_PLACEHOLDER:
    st.session_state.current_dir = selected_recent
    st.session_state.recent_dir_select = selected_recent

new_dir = st.sidebar.text_input("Current Directory", st.session_state.current_dir)
if os.path.isdir(new_dir):
    st.session_state.current_dir = new_dir
    _remember_directory(new_dir)
else:
    st.sidebar.error("Invalid directory")

with st.sidebar.expander("File Filter", expanded=True):
    st.session_state.file_filter = st.text_input("Filter Files", st.session_state.file_filter)
    filter_col1, filter_col2 = st.columns([3, 1])
    with filter_col1:
        _render_saved_filter_selector("Saved File Filters", "file", "saved_file_filter_select", "file_filter", st)
    with filter_col2:
        if st.button("Save", key="save_file_filter"):
            if _save_filter_preset("file", st.session_state.file_filter):
                st.success("File filter saved")
            else:
                st.warning("Nothing to save")

with st.sidebar.expander("Advanced File Filters", expanded=False):
    st.checkbox("Include subdirectories", key="include_subdirs")
    size_col1, size_col2 = st.columns(2)
    size_col1.number_input("Min size (KB)", min_value=0, step=1, key="file_min_size_kb")
    size_col2.number_input("Max size (KB)", min_value=0, step=1, key="file_max_size_kb")
    date_col1, date_col2 = st.columns(2)
    date_col1.text_input("Modified After (YYYY-MM-DD)", key="file_modified_after")
    date_col2.text_input("Modified Before (YYYY-MM-DD)", key="file_modified_before")

with st.sidebar.expander("Filename Parsing", expanded=False):
    parse_mode = st.selectbox("Mode", ["split", "dash", "none"], key="filename_parse_mode")
    if parse_mode == "split":
        st.text_input("Delimiter", key="filename_delimiter")
    st.number_input("Max parts", min_value=1, max_value=10, step=1, key="filename_max_parts")

# List Files
file_df = _list_csv_files(st.session_state.current_dir, st.session_state.include_subdirs)

st.session_state.file_browser_df = file_df.copy()
st.session_state.file_browser_selection = []
st.session_state.selected_files = []

if not file_df.empty:
    file_df = _apply_file_filters(file_df)

    if not file_df.empty:
        parse_mode = st.session_state.filename_parse_mode
        delimiter = st.session_state.filename_delimiter if parse_mode == 'split' else None
        max_parts = st.session_state.filename_max_parts
        parsed_parts = file_df['Name'].apply(lambda name: _parse_filename_parts(name, parse_mode, delimiter, max_parts))
        parts_df = pd.DataFrame(parsed_parts.tolist()).fillna("") if not parsed_parts.empty else pd.DataFrame()
        if not parts_df.empty:
            file_df = pd.concat([file_df, parts_df], axis=1)
        display_columns = ["Name", "SizeDisplay", "Modified", "Directory", "Extension"]
        part_columns = [col for col in file_df.columns if col.startswith('Part ')]
        display_columns.extend(part_columns)
        display_df = file_df[display_columns]
        file_widget = st.sidebar.dataframe(
            display_df,
            selection_mode="multi-row",
            on_select="rerun",
            hide_index=True
        )

        selected_indices = []
        if file_widget and hasattr(file_widget, "selection"):
            selected_indices = list(getattr(file_widget.selection, "rows", []))

        if selected_indices:
            st.session_state.file_browser_selection = selected_indices
            selected_subset = file_df.iloc[selected_indices]
            st.session_state.selected_files = selected_subset.to_dict('records')

            idx = selected_indices[0]
            record = file_df.iloc[idx]
            filepath = record["Path"]

            if st.session_state.selected_file != filepath:
                st.session_state.selected_file = filepath
                try:
                    st.session_state.df = utils.load_csv_file(filepath)
                    if st.session_state.df is not None:
                        _ensure_plot_state(filepath)
                except Exception as e:
                    st.error(f"Error loading file: {e}")
                    st.session_state.df = None
        else:
            st.session_state.selected_files = []
    else:
        st.sidebar.info("No files match the current filters.")
else:
    st.sidebar.info("No CSV/TSV files found in this directory.")

_render_file_operations()

# --- Main Content ---
if st.session_state.selected_file and st.session_state.df is not None:
    st.title(f"Viewing: {os.path.basename(st.session_state.selected_file)}")

    # --- Filters ---
    with st.expander("Filters", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.session_state.row_filter_text = st.text_input(
                "Row Filter (query, text, @)",
                st.session_state.row_filter_text,
                help="e.g., 'col > 10', 'error', 'col > 10 @ error'"
            )
            saved_row_col = st.columns([3, 1])
            _render_saved_filter_selector(
                "Saved Row Filters",
                "row",
                "saved_row_filter_select",
                "row_filter_text",
                saved_row_col[0]
            )
            if saved_row_col[1].button("Save", key="save_row_filter"):
                if _save_filter_preset("row", st.session_state.row_filter_text):
                    st.success("Row filter saved")
                else:
                    st.warning("Nothing to save")

        with col2:
            st.session_state.column_filter_text = st.text_input(
                "Column Filter",
                st.session_state.column_filter_text,
                help="Space/comma separated. !exclude, *wildcard"
            )
            saved_col_cols = st.columns([3, 1])
            _render_saved_filter_selector(
                "Saved Column Filters",
                "column",
                "saved_column_filter_select",
                "column_filter_text",
                saved_col_cols[0]
            )
            if saved_col_cols[1].button("Save", key="save_column_filter"):
                if _save_filter_preset("column", st.session_state.column_filter_text):
                    st.success("Column filter saved")
                else:
                    st.warning("Nothing to save")

            st.session_state.column_search_text = st.text_input(
                "Column Search",
                st.session_state.column_search_text,
                help="Case-insensitive substring matches"
            )
            if st.session_state.column_search_text:
                matches = [
                    col for col in st.session_state.df.columns
                    if st.session_state.column_search_text.lower() in col.lower()
                ]
                if matches:
                    st.caption("Matches: " + ", ".join(matches[:20]))
                else:
                    st.caption("No columns match")

            columns_for_move = st.session_state.df.columns.tolist()
            if columns_for_move:
                move_options = ["-- Select Column --"] + columns_for_move
                st.session_state.move_column_select = st.selectbox(
                    "Move column to start",
                    move_options,
                    index=_option_index(move_options, st.session_state.move_column_select, 0)
                )
                if st.session_state.move_column_select != "-- Select Column --" and st.button("Move", key="move_column_button"):
                    target_col = st.session_state.move_column_select
                    if target_col in columns_for_move:
                        ordered = [target_col] + [c for c in columns_for_move if c != target_col]
                        st.session_state.df = st.session_state.df[ordered]
                        st.success(f"Moved {target_col} to start")

        filtered_df = st.session_state.df.copy()
        if st.session_state.column_filter_text:
            try:
                filtered_df = utils.apply_column_filter(filtered_df, st.session_state.column_filter_text)
            except Exception as e:
                st.error(f"Column filter error: {e}")

    # --- Data Viewer ---
    st.dataframe(filtered_df, use_container_width=True)
    st.caption(f"Showing {len(filtered_df)} rows, {len(filtered_df.columns)} columns")
    csv_data = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Export Filtered CSV",
        data=csv_data,
        file_name=f"filtered_{Path(st.session_state.selected_file).stem}.csv",
        mime="text/csv"
    )

    # --- Plotting ---
    st.divider()
    st.subheader("Plotting")

    tabs = st.tabs(["General Plots", "Correlation Analysis", "Special Plots"])

    numeric_cols = plotting_utils.get_numeric_varying_columns(filtered_df)
    all_cols = filtered_df.columns.tolist()

    with tabs[0]:
        _render_general_plots(filtered_df, numeric_cols, all_cols)

    with tabs[1]:
        _render_correlation_tab(filtered_df, numeric_cols)

    with tabs[2]:
        _render_special_plots(filtered_df, numeric_cols)

else:
    st.info("Select a CSV file from the sidebar to view.")
