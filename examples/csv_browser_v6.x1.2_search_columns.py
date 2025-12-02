"""
CSV Browser Application with Excel-like File List

A tkinter-based CSV browser that displays CSV files in a dual-pane layout with Excel-like tables.
### Fixed
- Fixed issue with filtered table where row selection would load incorrect CSV files

Changelog:
### [2025-01-19]- add button to rename all files based on the field values
### [2025-01-17]Changed
- Added auto column width adjustment for file list table
- Set default sort order to sort by date modified (newest first)

## [2025-01-14] - CSV Browser Update
### Added
- Converted from Image Browser to CSV Browser
- Added CSV file viewing functionality in second panel
- Added Move Files functionality for CSV files
- Added Delete Files functionality for CSV files

### Changed
- Modified file filtering to only show CSV files
- Replaced image grid with pandastable for CSV viewing
- Updated UI layout for CSV file viewing
- Removed image-specific functionality
- Simplified toolbar to remove image-specific controls

Features:
- File browser with:
  - Sorting by name, date, size, and filename fields
  - Dynamic columns based on filename structure
  - Filter functionality across all fields
  - Horizontal scrolling for many fields
- CSV file preview in second panel
- Vertical and horizontal layout options
- Directory selection
- File operations (move, delete)
"""
# Import os and sys first
import os
import sys
import logging

# ============== Logging Configuration ==============
# Set up logging with configurable level via environment variable
# Use CSV_BROWSER_LOG_LEVEL=DEBUG for verbose output
LOG_LEVEL = os.environ.get('CSV_BROWSER_LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('CSVBrowser')

# Add custom pandastable path to sys.path BEFORE importing pandastable
custom_pandastable_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pandastable")
if os.path.exists(custom_pandastable_path):
    sys.path.insert(0, os.path.dirname(custom_pandastable_path))
    logger.info(f"Using custom pandastable from: {custom_pandastable_path}")

import pandastable.plotting as p
logger.debug(f"Using plotting.py from: {p.__file__}")

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import pandas as pd
import numpy as np
import traceback
import difflib
import warnings
import shutil
import subprocess
import json
from datetime import datetime
from pandastable import Table, TableModel
import time
import pyperclip
import copy
import types
import re  # For regex operations
from typing import Optional, List, Dict, Any, Tuple, Union

warnings.filterwarnings('ignore', category=FutureWarning)


class ToolTip:
    """Create a tooltip for a given widget.
    
    Usage:
        ToolTip(widget, "Tooltip text here")
    """
    
    def __init__(self, widget: tk.Widget, text: str, delay: int = 500):
        """Initialize tooltip.
        
        Args:
            widget: The widget to attach the tooltip to
            text: The tooltip text to display
            delay: Delay in milliseconds before showing tooltip (default 500ms)
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window: Optional[tk.Toplevel] = None
        self.scheduled_id: Optional[str] = None
        
        # Bind events
        self.widget.bind('<Enter>', self._schedule_tooltip)
        self.widget.bind('<Leave>', self._hide_tooltip)
        self.widget.bind('<ButtonPress>', self._hide_tooltip)
    
    def _schedule_tooltip(self, event: tk.Event = None) -> None:
        """Schedule tooltip to appear after delay."""
        self._cancel_scheduled()
        self.scheduled_id = self.widget.after(self.delay, self._show_tooltip)
    
    def _cancel_scheduled(self) -> None:
        """Cancel any scheduled tooltip."""
        if self.scheduled_id:
            self.widget.after_cancel(self.scheduled_id)
            self.scheduled_id = None
    
    def _show_tooltip(self, event: tk.Event = None) -> None:
        """Display the tooltip."""
        if self.tooltip_window:
            return
        
        # Get widget position
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        # Create tooltip window
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Create tooltip label with styling
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            background="#FFFFD0",  # Light yellow
            foreground="#000000",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9),
            padx=6,
            pady=3,
            wraplength=300,
            justify="left"
        )
        label.pack()
        
        # Ensure tooltip stays on screen
        self.tooltip_window.update_idletasks()
        screen_width = self.widget.winfo_screenwidth()
        screen_height = self.widget.winfo_screenheight()
        tooltip_width = self.tooltip_window.winfo_width()
        tooltip_height = self.tooltip_window.winfo_height()
        
        if x + tooltip_width > screen_width:
            x = screen_width - tooltip_width - 10
        if y + tooltip_height > screen_height:
            y = self.widget.winfo_rooty() - tooltip_height - 5
        
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
    
    def _hide_tooltip(self, event: tk.Event = None) -> None:
        """Hide the tooltip."""
        self._cancel_scheduled()
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
    
    def update_text(self, new_text: str) -> None:
        """Update the tooltip text."""
        self.text = new_text


class CSVBrowser(tk.Tk):
    """CSV Browser Application with Excel-like File List.
    
    A tkinter-based CSV browser that displays CSV files in a dual-pane layout
    with Excel-like tables, filtering, and plotting capabilities.
    """
    
    # ============== Configuration Constants ==============
    # UI Layout
    DEFAULT_HORIZONTAL_SASH_POS = 400  # pixels from left for horizontal layout
    DEFAULT_MIN_PANEL_HEIGHT = 150  # minimum height for any panel in pixels
    MIN_CSV_PANEL_RATIO = 0.55  # minimum ratio of height for CSV panel (55%)
    
    # File Browser
    MAX_RECENT_DIRECTORIES = 5  # maximum number of recent directories to remember
    DEFAULT_FIELD_COUNT = 25  # default number of Field_N columns for filename parsing
    
    # Column Display
    MIN_COLUMN_WIDTH = 50  # minimum column width in pixels
    MAX_COLUMN_WIDTH = 300  # maximum column width in pixels
    COLUMN_WIDTH_CHAR_MULTIPLIER = 8  # approximate pixels per character
    
    # File Path Handling
    LONG_PATH_THRESHOLD = 250  # characters before adding Windows long path prefix
    SPOTFIRE_PATH_LIMIT = 200  # max path length for Spotfire compatibility
    
    # Encoding Fallbacks
    ENCODING_FALLBACKS = ['utf-8', 'latin1', 'ISO-8859-1', 'cp1252', 'utf-16']
    
    def __init__(self):
        super().__init__()
        
        self.title("CSV Browser")
        self.state('zoomed')
        
        # Suppress specific warnings globally
        import warnings
        warnings.filterwarnings('ignore', message='.*color.*and.*colormap.*cannot be used simultaneously.*')
        warnings.filterwarnings('ignore', message='.*Tight layout not applied.*')
        
        # Initialize variables
        self.current_file = None
        self.is_horizontal = False  # Start with vertical layout
        self.filter_text = tk.StringVar()
        self.filter_text.trace_add("write", self.filter_files)
        self.last_clicked_row = None
        self.csv_frame = None
        self.include_subfolders = tk.BooleanVar(value=False)
        
        # Initialize CSV filter variables
        self.current_csv_filter = ""
        self.csv_filter_text = tk.StringVar(value="")
        self.csv_filter_text.trace_add("write", self.row_filter)
        
        # Initialize column search variable
        self.column_search_var = tk.StringVar(value="")
        self.column_search_var.trace_add("write", self.search_columns)
        
        # Initialize column filter variable
        self.column_filter_var = tk.StringVar(value="")
        self.column_filter_var.trace_add("write", self.filter_columns)
        self.visible_columns = None  # Store currently visible columns
        
        # Store saved filters (row and column)
        self.saved_filters = []  # List to store saved filter configurations
        
        # Store saved file filters
        self.saved_file_filters = []  # List to store saved file filter configurations
        
        # Set maximum number of recent directories to store
        self.max_recent_directories = self.MAX_RECENT_DIRECTORIES
        
        # Initialize recent directories list
        self.recent_directories = []
        
        # File to store settings (recent directories and filters)
        self.settings_file = os.path.join(os.path.expanduser("~"), "csv_browser_settings.json")
        logger.info(f"Settings file path: {self.settings_file}")
        
        # Load settings from file
        self.load_settings()
        
        # Track highlighted columns
        self.highlighted_columns = {}
        
        # Initialize last_searched_column
        self.last_searched_column = None
        
        # Initialize plot settings storage
        self.saved_plot_settings = None
        
        # Initialize table settings storage
        self.saved_table_settings = None
        
        # Initialize minimum CSV panel ratio
        self.min_csv_panel_ratio = self.MIN_CSV_PANEL_RATIO  # use class constant
        
        # # Initialize frame attributes
        self.pt_frame = ttk.Frame(self)
        self.csv_frame = ttk.Frame(self)
        
        # Set default directory - use last recent directory or fallback to user's home/Documents
        self.current_directory = self._get_default_directory()
        
        # Add current directory to recent directories
        self.add_to_recent_directories(self.current_directory)
        
        # Get initial list of CSV files
        self.update_file_list()
        
        # Calculate max fields for the current directory
        self.max_fields = self.get_max_fields()
        
        # Create main container
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)
        
        # Create and pack the toolbar
        self.toolbar = ttk.Frame(self.main_container)
        self.toolbar.pack(fill="x", padx=5, pady=5)
        self.setup_toolbar()
        
        # Create status bar
        self.status_bar = ttk.Frame(self.main_container, height=20)
        self.status_bar.pack(fill="x", side="bottom", padx=5, pady=2)
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self.status_bar, textvariable=self.status_var, relief="sunken", anchor="w")
        status_label.pack(fill="x")
        ToolTip(status_label, "Status bar: Shows current operation status, row/column counts, and filter feedback")
        
        # Create and pack the panels
        self.setup_panels()
        
        # Create the file browser and CSV viewer
        self.setup_file_browser()
        self.setup_csv_viewer()
        
        # Setup column search menu
        self.setup_column_search_menu()
        
        # Set up keyboard shortcuts
        self.bind("<Control-f>", self.focus_column_search)
        self.bind("<Control-o>", self._shortcut_open_directory)
        self.bind("<Control-r>", self._shortcut_refresh)
        self.bind("<Escape>", self._shortcut_clear_filters)
        self.bind("<F5>", self._shortcut_refresh)
        
        # Create the application menu
        self.create_menu()

    def _shortcut_open_directory(self, event: Optional[tk.Event] = None) -> str:
        """Keyboard shortcut handler for opening a directory (Ctrl+O)"""
        self.browse_directory()
        return "break"
    
    def _shortcut_refresh(self, event: Optional[tk.Event] = None) -> str:
        """Keyboard shortcut handler for refreshing file list (Ctrl+R or F5)"""
        self.refresh_file_list()
        return "break"
    
    def _shortcut_clear_filters(self, event: Optional[tk.Event] = None) -> str:
        """Keyboard shortcut handler for clearing all filters (Escape)"""
        # Clear file filter
        if hasattr(self, 'filter_text'):
            self.filter_text.set("")
        # Clear row filter
        if hasattr(self, 'csv_filter_text'):
            self.csv_filter_text.set("")
        # Clear column filter
        if hasattr(self, 'column_filter_var'):
            self.column_filter_var.set("")
        # Clear column search
        if hasattr(self, 'column_search_var'):
            self.column_search_var.set("")
        # Update status
        self._update_status("Filters cleared")
        return "break"
    
    def _update_status(self, message: str) -> None:
        """Update the status bar with a message"""
        if hasattr(self, 'status_var'):
            self.status_var.set(message)
            # Auto-clear status after 3 seconds
            self.after(3000, lambda: self.status_var.set("Ready") if self.status_var.get() == message else None)

    def _get_default_directory(self) -> str:
        """Get the default directory for the file browser.
        
        Priority:
        1. Most recent directory from settings (if it exists)
        2. User's Documents folder
        3. User's home directory
        4. Current working directory
        
        Returns:
            str: Path to the default directory
        """
        # Try to use the most recent directory from settings
        if hasattr(self, 'recent_directories') and self.recent_directories:
            for recent_dir in self.recent_directories:
                if recent_dir and os.path.isdir(recent_dir):
                    logger.info(f"Using recent directory: {recent_dir}")
                    return recent_dir
        
        # Try user's Documents folder
        documents_path = os.path.join(os.path.expanduser("~"), "Documents")
        if os.path.isdir(documents_path):
            logger.info(f"Using Documents folder: {documents_path}")
            return documents_path
        
        # Try user's home directory
        home_path = os.path.expanduser("~")
        if os.path.isdir(home_path):
            logger.info(f"Using home directory: {home_path}")
            return home_path
        
        # Fallback to current working directory
        cwd = os.getcwd()
        logger.info(f"Using current working directory: {cwd}")
        return cwd

    def normalize_long_path(self, path: str) -> str:
        """Normalize path and add long path prefix if needed."""
        # Normalize the path
        normalized_path = os.path.normpath(os.path.abspath(path))
        
        # If path is longer than threshold, add the long path prefix
        if len(normalized_path) > self.LONG_PATH_THRESHOLD and not normalized_path.startswith('\\\\?\\'):
            # Add Windows long path prefix
            normalized_path = '\\\\?\\' + normalized_path
            logger.debug(f"Using long path format: {normalized_path}")
        
        return normalized_path
        
    def format_size(self, size: Union[int, float]) -> str:
        """Convert size in bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def format_date(self, timestamp: float) -> str:
        """Convert timestamp to readable date format."""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")

    def setup_panels(self):
        """Setup the main panels with proper orientation"""
        # Create main paned window with proper orientation
        orient = tk.HORIZONTAL if self.is_horizontal else tk.VERTICAL
        self.paned = ttk.PanedWindow(self.main_container, orient=orient)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Create file browser frame
        self.file_frame = ttk.Frame(self.paned)
        self.paned.add(self.file_frame, weight=1)

        # Create CSV viewer container frame
        self.csv_container = ttk.Frame(self.paned)
        self.paned.add(self.csv_container, weight=2)

        # Set minimum sizes to prevent collapse
        if self.is_horizontal:
            self.file_frame.configure(width=400)
            self.csv_container.configure(width=800)
        else:
            self.file_frame.configure(height=300)
            self.csv_container.configure(height=500)

        # Force geometry update
        self.update_idletasks()
        
        # Set initial sash position
        if self.is_horizontal:
            self.paned.sashpos(0, 400)  # 400 pixels from left
        else:
            self._schedule_vertical_sash_adjustment()

    def _schedule_vertical_sash_adjustment(self, delay=50):
        if self.is_horizontal:
            return
        self.after(delay, self._ensure_bottom_table_min_height)

    def _ensure_bottom_table_min_height(self):
        if self.is_horizontal or not hasattr(self, 'paned'):
            return
        total_height = self.paned.winfo_height()
        if total_height <= 1:
            self._schedule_vertical_sash_adjustment(50)
            return
        top_height = int(total_height * (1 - self.min_csv_panel_ratio))
        top_height = max(top_height, 150)
        if total_height - top_height < 150:
            top_height = max(total_height - 150, 0)
        try:
            self.paned.sashpos(0, top_height)
        except tk.TclError:
            pass

    def setup_file_browser(self):
        """Setup the file browser panel with pandastable"""
        print("\n=== Setting up file browser ===")  # Debug print
        
        # Create frame for pandastable
        if hasattr(self, 'pt_frame'):
            self.pt_frame.destroy()
        self.pt_frame = ttk.Frame(self.file_frame)
        self.pt_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add filter frame
        filter_frame = ttk.Frame(self.pt_frame)
        filter_frame.pack(fill="x", padx=5, pady=5)
        
        # Add filter label and entry
        filter_files_label = ttk.Label(filter_frame, text="Filter Files:")
        filter_files_label.pack(side="left", padx=(0,5))
        ToolTip(filter_files_label, "Filter the file list by filename\nUse space for AND, '!' to exclude")
        filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_text)
        filter_entry.pack(side="left", fill="x", expand=True)
        ToolTip(filter_entry, "Filter files by name. Use space to combine terms, '!' to exclude.\nRight-click for more options.")
        
        # Add save file filter button
        save_file_filter_btn = ttk.Button(filter_frame, text="Save Filter", command=self.save_file_filter)
        save_file_filter_btn.pack(side="left", padx=5)
        ToolTip(save_file_filter_btn, "Save the current file filter for later use")
        
        # Add load file filter button
        load_file_filter_btn = ttk.Button(filter_frame, text="Load Filter", command=self.show_saved_file_filters)
        load_file_filter_btn.pack(side="left", padx=5)
        ToolTip(load_file_filter_btn, "Load a previously saved file filter")
        
        # Create right-click context menu for filtering instructions
        filter_menu = tk.Menu(filter_entry, tearoff=0)
        filter_menu.add_command(label="Filtering Instructions", state='disabled', font=('Arial', 10, 'bold'))
        filter_menu.add_separator()
        filter_menu.add_command(label="Basic Search: Enter any text to match", state='disabled')
        filter_menu.add_command(label="Multiple Terms: Use space ' 'to combine", state='disabled')
        filter_menu.add_command(label="Exclude Terms: Use '!' prefix", state='disabled')
        filter_menu.add_separator()
        filter_menu.add_command(label="Examples:", state='disabled', font=('Arial', 10, 'bold'))
        filter_menu.add_command(label="'csv': Show files with 'csv'", state='disabled')
        filter_menu.add_command(label="'2024 report': Files with both terms", state='disabled')
        filter_menu.add_command(label="'!temp': Exclude files with 'temp'", state='disabled')
        filter_menu.add_command(label="'csv !old': CSV files, not old", state='disabled')
        
        def show_filter_menu(event):
            filter_menu.tk_popup(event.x_root, event.y_root)
        
        filter_entry.bind('<Button-3>', show_filter_menu)  # Right-click
        
        # Create table frame
        table_frame = ttk.Frame(self.pt_frame)
        table_frame.pack(fill="both", expand=True)
        
        # Create DataFrame for files
        self.update_file_dataframe()
        
        # Create pandastable with editable cells
        self.table = Table(table_frame, dataframe=self.df,
                        showtoolbar=True, showstatusbar=True)
        
        # Enable editing and bind to key events
        self.table.editable = True
        self.table.bind('<Key>', self.on_key_press)
        self.table.bind('<Return>', self.on_return_press)
        self.table.bind('<FocusOut>', self.on_focus_out)
        
        self.table.show()
        ToolTip(self.table, "File list table\nClick to select, double-click to load CSV\nCtrl+Click for multi-select, right-click for options")
        
        # Configure table options
        self.table.autoResizeColumns()
        self.table.columnwidths['Name'] = 50
        self.table.columnwidths['File_Path'] = 90

        for col in self.df.columns:
            if col not in ['Name', 'File_Path']:
                # Check if DataFrame is not empty before calculating max width
                if not self.df.empty and len(self.df[col]) > 0:
                    max_width = max(len(str(x)) for x in self.df[col].head(20))
                    self.table.columnwidths[col] = max(min(max_width * 10, 200), 50)
                else:
                    # Set a default width if DataFrame is empty
                    self.table.columnwidths[col] = 100

        self.table.redraw()
        
        # Bind selection event
        self.table.bind('<ButtonRelease-1>', self.on_table_select)
        self.table.bind('<Up>', self.on_key_press)
        self.table.bind('<Down>', self.on_key_press)

    def merge_selected_csv_files(self):
        """Merge selected CSV files with comprehensive error handling and column preservation"""
        try:
            # Check if table exists
            if not hasattr(self, 'table'):
                messagebox.showwarning("Merge CSV", "File table not initialized.")
                return
    
            # Get selected rows indices
            selected_rows = self.table.multiplerowlist
            if not selected_rows or len(selected_rows) < 2:
                messagebox.showwarning("Merge CSV", "Please select at least two CSV files to merge.")
                return
            
            # Get full paths of selected files from the filtered/displayed DataFrame
            displayed_df = self.table.model.df
            selected_files = [displayed_df.iloc[idx]['File_Path'] for idx in selected_rows]
            
            # Read the first CSV as the base file with error handling
            try:
                base_df = pd.read_csv(selected_files[0], index_col=False)
                base_filename = os.path.basename(selected_files[0])
            except UnicodeDecodeError:
                # Try different encodings
                encodings = ['utf-8', 'latin1', 'cp1252']
                for encoding in encodings:
                    try:
                        base_df = pd.read_csv(selected_files[0], encoding=encoding, index_col=False)
                        base_filename = os.path.basename(selected_files[0])
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise Exception(f"Failed to read {selected_files[0]} with any encoding")
            
            # Merge subsequent CSVs
            for file_path in selected_files[1:]:
                try:
                    # Try reading with default encoding
                    next_df = pd.read_csv(file_path, index_col=False)
                except UnicodeDecodeError:
                    # Try different encodings
                    encodings = ['utf-8', 'latin1', 'cp1252']
                    for encoding in encodings:
                        try:
                            next_df = pd.read_csv(file_path, encoding=encoding, index_col=False)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        raise Exception(f"Failed to read {file_path} with any encoding")
                
                # Concatenate with outer join to preserve all columns
                base_df = pd.concat([base_df, next_df], ignore_index=True, join='outer')
            
            # Create merged filename
            merged_filename = os.path.splitext(base_filename)[0] + "_merged.csv"
            merged_filepath = os.path.join(os.path.dirname(selected_files[0]), merged_filename)
            
            # Save merged CSV
            base_df.to_csv(merged_filepath, index=False)
            
            messagebox.showinfo("Merge CSV", f"Files merged successfully!\nMerged file: {merged_filename}")
            
            # Refresh file list to show the new merged file
            self.update_file_list()
        
        except Exception as e:
            messagebox.showerror("Merge CSV Error", f"An error occurred while merging files:\n{str(e)}")

    def filter_files(self, *args):
        """Filter files based on the filter text"""
        if hasattr(self, 'table'):
            try:
                # Get filter text and remove any quotes
                filter_text = self.filter_text.get().lower().strip('"\'')
                print(f"\n=== Filtering files with: '{filter_text}' ===")  # Debug print
                
                if filter_text:
                    # Split filter text by AND (both & and +)
                    filter_terms = [term.strip() for term in filter_text.split()]
                    print(f"Searching for terms: {filter_terms}")  # Debug print
                    
                    # Start with all rows
                    mask = pd.Series([True] * len(self.df), index=self.df.index)
                    
                    # Apply each filter term with AND logic
                    for term in filter_terms:
                        term = term.strip()
                        if term:  # Skip empty terms
                            if term.startswith('!'):  # Exclusion term
                                exclude_term = term[1:].strip()  # Remove ! and whitespace
                                if exclude_term:  # Only if there's something to exclude
                                    term_mask = ~self.df['Name'].str.contains(exclude_term, case=False, na=False)
                                    print(f"Excluding rows with name containing: '{exclude_term}'")  # Debug print
                            else:  # Inclusion term
                                term_mask = self.df['Name'].str.contains(term, case=False, na=False)
                                print(f"Including rows with name containing: '{term}'")  # Debug print
                            mask = mask & term_mask
                    
                    # Debug print matches
                    print("\nMatching results:")
                    for idx, row in self.df[mask].iterrows():
                        print(f"Match found in row {idx}: {row['Name']}")
                    
                    filtered_df = self.df[mask].copy()
                    print(f"\nFound {len(filtered_df)} matching files")  # Debug print
                else:
                    filtered_df = self.df.copy()
                    print("No filter applied, showing all files")  # Debug print
                
                # Update table
                self.table.model.df = filtered_df
                
                # Only update column widths if we have data
                if not filtered_df.empty:
                    # Preserve column widths
                    for col in filtered_df.columns:
                        if col in self.table.columnwidths:
                            width = max(
                                len(str(filtered_df[col].max())),
                                len(str(filtered_df[col].min())),
                                len(col),
                                self.table.columnwidths[col]
                            )
                            self.table.columnwidths[col] = width
                
                # Redraw the table
                self.table.redraw()
                
            except Exception as e:
                print(f"Error in filter_files: {str(e)}")
                traceback.print_exc()  # Print the full traceback for debugging
                self.update_file_dataframe()

    def on_key_press(self, event):
        """Handle key press events"""
        try:
            if event.keysym in ('Up', 'Down'):
                # Handle arrow key navigation
                current_row = self.table.getSelectedRow()
                num_rows = len(self.table.model.df)
                
                if event.keysym == 'Up' and current_row > 0:
                    new_row = current_row - 1
                elif event.keysym == 'Down' and current_row < num_rows - 1:
                    new_row = current_row + 1
                else:
                    return
                
                # Select the new row and ensure it's visible
                self.table.setSelectedRow(new_row)
                self.table.redraw()  # Ensure table updates
                
                # Get filename and path directly from the displayed DataFrame
                displayed_df = self.table.model.df
                if new_row < 0 or new_row >= len(displayed_df):  # Fixed variable name from 'row' to 'new_row'
                    print(f"Row index {new_row} out of bounds for displayed_df of length {len(displayed_df)}")
                    return
                file_path = str(displayed_df.iloc[new_row]['File_Path'])
    
                # Load the CSV file
                self.load_csv_file(file_path)   
            elif event.char and event.char.isprintable():
                row = self.table.getSelectedRow()
                col = self.table.getSelectedColumn()
                if row is not None and col is not None:
                    # Then check for changes
                    self.check_for_changes(row, col)
        except Exception as e:
            print(f"Error handling key press: {e}")
            traceback.print_exc()

    def on_return_press(self, event):
        """Handle return key press"""
        try:
            row = self.table.getSelectedRow()
            col = self.table.getSelectedColumn()
            if row is not None and col is not None:
                self.check_for_changes(row, col)
        except Exception as e:
            print(f"Error handling return press: {e}")
            traceback.print_exc()

    def on_focus_out(self, event):
        """Handle focus out events"""
        try:
            row = self.table.getSelectedRow()
            col = self.table.getSelectedColumn()
            if row is not None and col is not None:
                self.check_for_changes(row, col)
        except Exception as e:
            print(f"Error handling focus out: {e}")
            traceback.print_exc()
    
    def check_for_changes(self, row, col):
        """Check for changes in the cell and handle file renaming"""
        # try:
        #     # Get the displayed DataFrame before any filter operations
        #     displayed_df = self.table.model.df
        #     if row < len(displayed_df):
        #         # Get current filename and path from displayed DataFrame
        #         file_path = os.path.normpath(str(displayed_df.iloc[row]['File_Path']))
        #         current_name = displayed_df.iloc[row]['Name']
                
        #         # Reconstruct filename from Field_ columns
        #         new_filename = self.reconstruct_filename(displayed_df.iloc[row])
                
        #         # If filename is different, rename the file
        #         if new_filename != current_name:
        #             print(f"Renaming file from {current_name} to {new_filename}")  # Debug print
        #             new_filepath = self.rename_csv_file(file_path, new_filename)
                    
        #             if new_filepath != file_path:  # Only update if rename was successful
        #                 # Update the displayed DataFrame
        #                 displayed_df.loc[row, 'Name'] = new_filename
        #                 displayed_df.loc[row, 'File_Path'] = new_filepath
                        
        #                 # Find and update the corresponding row in the original DataFrame
        #                 orig_idx = self.df[self.df['File_Path'] == file_path].index
        #                 if len(orig_idx) > 0:
        #                     # Update all Field_ columns in the original DataFrame
        #                     for col in self.df.columns:
        #                         if col.startswith('Field_'):
        #                             self.df.loc[orig_idx[0], col] = displayed_df.iloc[row][col]
        #                     # Update Name and File_Path
        #                     self.df.loc[orig_idx[0], 'Name'] = new_filename
        #                     self.df.loc[orig_idx[0], 'File_Path'] = new_filepath
                        
        #                 # Store current filter text
        #                 filter_text = self.filter_text.get()
                        
        #                 # Temporarily disable filter to update the model
        #                 if filter_text:
        #                     self.filter_text.set('')
        #                     self.table.model.df = displayed_df
        #                     self.table.redraw()
                        
        #                 # Reapply the filter if it was active
        #                 if filter_text:
        #                     self.filter_text.set(filter_text)
                        
        #                 # Show confirmation
        #                 messagebox.showinfo("File Renamed", 
        #                                 f"File has been renamed from:\n{current_name}\nto:\n{new_filename}")
                        
        #         else:
        #             print("No changes detected")  # Debug print
            
        # except Exception as e:
        #     print(f"Error checking for changes: {e}")
        #     traceback.print_exc()
        pass
    
    def setup_csv_viewer(self):
        """Setup the CSV viewer panel"""
        try:
            # Create frame for CSV viewer
            if hasattr(self, 'csv_frame') and self.csv_frame is not None:
                self.csv_frame.destroy()
            self.csv_frame = ttk.Frame(self.csv_container)
            self.csv_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Create a container frame that will use grid
            self.csv_view_container = ttk.Frame(self.csv_frame)
            self.csv_view_container.pack(fill="both", expand=True)
            
            # Add filter entry for CSV viewer using grid
            self.csv_filter_frame = ttk.Frame(self.csv_view_container)
            self.csv_filter_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
            self.csv_filter_frame.columnconfigure(1, weight=1)  # Make the entry expand
            self.csv_filter_frame.columnconfigure(3, weight=1)  # Make the column search entry expand
            
            row_filter_label = ttk.Label(self.csv_filter_frame, text="Row Filter:")
            row_filter_label.grid(row=0, column=0, padx=(0,5))
            ToolTip(row_filter_label, "Filter rows in the CSV data\nSupports pandas query syntax and text search\nUse '@' to combine query and text search")
            
            # Use the existing StringVar - don't add another trace
            print(f"Current filter value: '{self.csv_filter_text.get()}'")  # Debug print
            
            # Create and set up the entry widget
            self.csv_filter_entry = ttk.Entry(self.csv_filter_frame, textvariable=self.csv_filter_text)
            self.csv_filter_entry.grid(row=0, column=1, sticky='ew')
            ToolTip(self.csv_filter_entry, "Filter rows by text search. Supports pandas query syntax.\nRight-click for filter examples and options.")
            
            # Create the context menu first
            self.setup_csv_filter_context_menu()
            
            # Bind right-click to show context menu
            self.csv_filter_entry.bind("<Button-3>", self.show_csv_filter_context_menu)
            
            # Also bind to the right-click release to ensure menu stays open
            self.csv_filter_entry.bind("<ButtonRelease-3>", lambda e: "break")
            
            # Make sure the entry can get focus
            self.csv_filter_entry.bind("<FocusIn>", lambda e: print("CSV filter entry got focus"))
            self.csv_filter_entry.bind("<FocusOut>", lambda e: print("CSV filter entry lost focus"))
            
            # Add column search box
            search_col_label = ttk.Label(self.csv_filter_frame, text="Search Column:")
            search_col_label.grid(row=0, column=2, padx=(10,5))
            ToolTip(search_col_label, "Search for columns by name\nRight-click or press Enter to see matches")
            self.column_search_entry = ttk.Entry(self.csv_filter_frame, textvariable=self.column_search_var)
            self.column_search_entry.grid(row=0, column=3, sticky='ew')
            self.column_search_entry.bind("<Button-3>", self.show_column_search_menu)
            self.column_search_entry.bind("<Return>", self.show_column_search_menu)
            ToolTip(self.column_search_entry, "Search for columns by name (Ctrl+F).\nType to filter, press Enter or right-click to see matches.")
            
            # Ensure the context menu is set up for column search
            self.setup_column_search_menu()
            
            # Add Move to Start button
            self.move_to_start_btn = ttk.Button(
                self.csv_filter_frame, 
                text="Move to Start", 
                command=self.move_searched_column_to_start,
                width=12
            )
            self.move_to_start_btn.grid(row=0, column=4, padx=(5,0))
            ToolTip(self.move_to_start_btn, "Move the searched column to the first position in the table")
            
            # Add Save to CSV button
            self.save_to_csv_button = ttk.Button(
                self.csv_filter_frame, 
                text="Save to CSV",
                command=self.save_to_filtered_csv,
                width=12
            )
            self.save_to_csv_button.grid(row=0, column=5, padx=(5,0))
            ToolTip(self.save_to_csv_button, "Save the currently filtered data to a new CSV file")
            
            # Add column filter row
            self.column_filter_frame = ttk.Frame(self.csv_view_container)
            self.column_filter_frame.grid(row=1, column=0, sticky='ew', padx=5, pady=(0,5))
            self.column_filter_frame.columnconfigure(1, weight=1)  # Make the entry expand
            
            col_filter_label = ttk.Label(self.column_filter_frame, text="Column Filter:")
            col_filter_label.grid(row=0, column=0, padx=(0,5))
            ToolTip(col_filter_label, "Filter which columns are visible\nUse quotes for exact match, '!' to exclude, '*' for remaining")
            self.column_filter_entry = ttk.Entry(self.column_filter_frame, textvariable=self.column_filter_var)
            self.column_filter_entry.grid(row=0, column=1, sticky='ew')
            ToolTip(self.column_filter_entry, "Filter which columns are visible\nSeparate terms with spaces, commas, or semicolons\nUse quotes for exact match, '!' to exclude, '*' for remaining\nRight-click for examples")
            
            # Add reset button for column filter
            self.reset_column_filter_btn = ttk.Button(
                self.column_filter_frame,
                text="Reset Columns",
                command=self.reset_column_filter,
                width=12
            )
            self.reset_column_filter_btn.grid(row=0, column=2, padx=(5,0))
            ToolTip(self.reset_column_filter_btn, "Show all columns (reset column visibility)")
            
            # Add save filter button
            self.save_filter_button = ttk.Button(
                self.column_filter_frame,
                text="Save Filter",
                command=self.save_current_filter,
                width=12
            )
            self.save_filter_button.grid(row=0, column=3, padx=(5,0))
            ToolTip(self.save_filter_button, "Save current row and column filter settings")
            
            # Add load filter button
            self.load_filter_button = ttk.Button(
                self.column_filter_frame,
                text="Load Filter",
                command=self.show_saved_filters,
                width=12
            )
            self.load_filter_button.grid(row=0, column=4, padx=(5,0))
            ToolTip(self.load_filter_button, "Load previously saved filter settings")
            
            # Add reset all filters button
            self.reset_all_filters_button = ttk.Button(
                self.column_filter_frame,
                text="Reset All Filters",
                command=self.reset_all_filters,
                width=12
            )
            self.reset_all_filters_button.grid(row=0, column=5, padx=(5,0))
            ToolTip(self.reset_all_filters_button, "Clear all filters and show all data (Escape)")
            
            # Create frame for pandastable using grid
            self.csv_table_frame = ttk.Frame(self.csv_view_container)
            self.csv_table_frame.grid(row=2, column=0, sticky='nsew', padx=5, pady=5)
            
            # Configure grid weights
            self.csv_view_container.rowconfigure(2, weight=1)
            self.csv_view_container.columnconfigure(0, weight=1)
            
            # Create empty pandastable for CSV viewing
            empty_df = pd.DataFrame()
            self.csv_table = Table(self.csv_table_frame, dataframe=empty_df,
                                showtoolbar=True, showstatusbar=True)
            self.csv_table.show()
            ToolTip(self.csv_table, "CSV data viewer\nClick column headers to sort\nCtrl+Click columns to select for plotting\nRight-click for more options")
            
            # Store original data
            self.original_csv_df = None
            
            # Reset highlighted columns
            self.highlighted_columns = {}
            
            # Setup filter context menu
            self.setup_csv_filter_context_menu()
            
            # Set up the column search menu in row 1
            self.setup_column_search_menu()
            
            # Set up the column filter context menu
            self.setup_column_filter_context_menu()
            
        except Exception as e:
            print(f"Error in setup_csv_viewer: {e}")
            traceback.print_exc()

    def _apply_filter(self, df, search_text):
        """
        Apply a filter to the DataFrame based on search text.
        
        Args:
            df: The input DataFrame to filter
            search_text: The text to search for in the DataFrame
            
        Returns:
            DataFrame containing rows that match the search text, with wildcard matches appended
        """
        if not search_text or not isinstance(df, pd.DataFrame) or df.empty:
            return df
            
        try:
            # Check for wildcard pattern 'term *' or 'term*'
            if ' *' in search_text or search_text.endswith('*'):
                # Get everything before the wildcard as the base search
                base_search = search_text.split('*')[0].strip()
                
                # Make a copy of the original DataFrame to avoid modifying it
                df = df.copy()
                
                # Apply the base search
                base_matches = self._apply_single_filter(df, base_search)
                
                # Get all row indices from the original DataFrame
                all_indices = set(df.index)
                matched_indices = set(base_matches.index)
                
                # Find all non-matching indices
                non_matched_indices = list(all_indices - matched_indices)
                
                # Get non-matching rows
                non_matches = df.loc[non_matched_indices]
                
                # Combine results (base matches first, then non-matches)
                if len(non_matches) > 0:
                    return pd.concat([base_matches, non_matches])
                return base_matches
            
            # No wildcard, apply normal filter
            return self._apply_single_filter(df, search_text)
            
        except Exception as e:
            print(f"Error in _apply_filter: {e}")
            traceback.print_exc()
            return df
            
    def _apply_single_filter(self, df, search_text):
        """Helper method to apply a single filter without wildcard handling"""
        if not search_text or not isinstance(df, pd.DataFrame) or df.empty:
            return df
            
        try:
            # Handle list pattern matching [term1,term2]
            if search_text.startswith('[') and search_text.endswith(']'):
                list_terms = [t.strip() for t in search_text[1:-1].split(',') if t.strip()]
                if list_terms:
                    str_df = df.astype(str)
                    mask = str_df.apply(lambda x: any(
                        x.str.contains(re.escape(term), case=False, na=False, regex=False).any()
                        for term in list_terms
                    ), axis=1)
                    return df[mask].copy()
                return df
                
            # Handle exclusion patterns
            if search_text.startswith('!'):
                exclude_text = search_text[1:]
                if (exclude_text.startswith('"') and exclude_text.endswith('"')) or \
                   (exclude_text.startswith("'") and exclude_text.endswith("'") and len(exclude_text) > 1):
                    # Exact match exclusion
                    exclude_text = exclude_text[1:-1]
                    str_df = df.astype(str)
                    mask = ~str_df.apply(lambda x: x == exclude_text).any(axis=1)
                else:
                    # Multiple terms exclusion (all must be present)
                    terms = [t.strip() for t in exclude_text.split() if t.strip()]
                    if len(terms) > 1:
                        str_df = df.astype(str)
                        mask = ~str_df.apply(lambda x: all(
                            x.str.contains(re.escape(term), case=False, na=False, regex=False).any() 
                            for term in terms
                        ), axis=1)
                    else:
                        # Single term exclusion
                        str_df = df.astype(str)
                        mask = ~str_df.apply(lambda x: x.str.contains(re.escape(exclude_text), case=False, na=False, regex=False)).any(axis=1)
            # Handle exact match in quotes
            elif (search_text.startswith('"') and search_text.endswith('"')) or \
                 (search_text.startswith("'") and search_text.endswith("'")):
                exact_text = search_text[1:-1]
                str_df = df.astype(str)
                mask = str_df.apply(lambda x: x == exact_text).any(axis=1)
            # Handle prefix/suffix patterns
            elif search_text.startswith('^') or search_text.endswith('$'):
                str_df = df.astype(str)
                if search_text.startswith('^'):
                    # Prefix match
                    pattern = f'^{re.escape(search_text[1:])}'
                    mask = str_df.apply(lambda x: x.str.contains(pattern, case=False, na=False, regex=True)).any(axis=1)
                elif search_text.endswith('$'):
                    # Suffix match
                    pattern = f'{re.escape(search_text[:-1])}$'
                    mask = str_df.apply(lambda x: x.str.contains(pattern, case=False, na=False, regex=True)).any(axis=1)
            # Handle multiple terms (all must be present)
            else:
                terms = [t.strip() for t in search_text.split() if t.strip()]
                if len(terms) > 1:
                    str_df = df.astype(str)
                    mask = str_df.apply(lambda x: all(
                        x.str.contains(re.escape(term), case=False, na=False, regex=False).any() 
                        for term in terms
                    ), axis=1)
                else:
                    # Single term search - use regex=False to handle special characters literally
                    str_df = df.astype(str)
                    mask = str_df.apply(lambda x: x.str.contains(re.escape(search_text), case=False, na=False, regex=False)).any(axis=1)
            
            # Return only matching rows, ensuring it's a DataFrame
            result = df[mask]
            if isinstance(result, pd.Series):
                return result.to_frame()
            return result.copy()
            
        except Exception as e:
            print(f"Error in _apply_single_filter: {e}")
            traceback.print_exc()
            return df
            
    def row_filter(self, *args):
        """
        Advanced row filtering with support for:
        1. Pandas query filtering
        2. Text-based contains search
        3. Mixing query and contains search using '@' separator
        4. Wildcard '*' to show non-matching rows
        
        This works in conjunction with the column filter to maintain both row and column filtering states.
        """
        global re  # Ensure we're using the global re module
        print("\n=== Row filter applied ===")
        
        if not hasattr(self, 'csv_table') or not hasattr(self, 'original_csv_df') or self.original_csv_df is None:
            return
            
        try:
            filter_text = self.csv_filter_text.get().strip()
            print(f"Row filter text: '{filter_text}'")
            
            # Store the current row filter
            self.current_csv_filter = filter_text
            
            # Get current column filter state
            column_filter_text = self.column_filter_var.get().strip()
            has_column_filter = bool(column_filter_text)
            
            # Start with a fresh copy of the original data
            filtered_df = self.original_csv_df.copy()
            
            # Check for wildcard pattern first
            if ' *' in filter_text or filter_text.endswith('*'):
                # Get everything before the wildcard as the base search
                base_search = filter_text.split('*')[0].strip()
                
                # Apply the base search (which can include query and contains parts)
                base_matches = self.row_filter_impl(filtered_df, base_search)
                
                # Get all rows that didn't match the base search
                non_matches = filtered_df[~filtered_df.index.isin(base_matches.index)]
                
                # Combine results (base matches first, then non-matches)
                if len(non_matches) > 0:
                    filtered_df = pd.concat([base_matches, non_matches])
                else:
                    filtered_df = base_matches
                    
                print(f"Rows after wildcard append: {len(filtered_df)}")
            else:
                # No wildcard, apply normal filtering
                filtered_df = self.row_filter_impl(filtered_df, filter_text)
            
            # Store the filtered DataFrame for column filtering (only if valid)
            if filtered_df is not None and not filtered_df.empty:
                self.filtered_csv_df = filtered_df
            elif not filter_text:  # No filter, use original
                self.filtered_csv_df = self.original_csv_df.copy()
            # else: keep previous filtered_csv_df to avoid stale state issues
            
            # Apply column filter if it exists
            if has_column_filter:
                print(f"Applying column filter: '{column_filter_text}' to filtered data")
                self._apply_column_filter_to_filtered_data()
            else:
                # Update the table with filtered data
                self.csv_table.model.df = filtered_df
                self.csv_table.redraw()
            
            # Update status bar if it exists
            if hasattr(self, 'status_var'):
                try:
                    row_count = len(filtered_df)
                    col_count = len(filtered_df.columns)
                    self.status_var.set(f"Showing {row_count:,} rows × {col_count} columns")
                except Exception as e:
                    print(f"Error updating status bar: {e}")
                    if hasattr(self, 'status_var'):
                        self.status_var.set("Ready")
                        
        except Exception as e:
            import traceback
            error_msg = f"Error in row filter: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            if hasattr(self, 'status_var'):
                self.status_var.set(f"Error: {str(e)}")
            # Restore original data on error
            if hasattr(self, 'original_csv_df'):
                self.csv_table.model.df = self.original_csv_df
                self.csv_table.redraw()
                        
    def row_filter_impl(self, df, filter_text):
        """Helper method that implements the actual filtering logic without wildcard handling"""
        if not filter_text or not isinstance(df, pd.DataFrame) or df.empty:
            return df
            
        # Split filter into query and contains parts
        query_part = ''
        contains_part = ''
        
        # Check for '@' separator
        if '@' in filter_text:
            query_part, contains_part = [part.strip() for part in filter_text.split('@', 1)]
        else:
            # If no '@', try to use as query first
            query_part = filter_text
        
        filtered_df = df.copy()
        
        # Apply query filtering if query part exists
        query_successful = False
        if query_part:
            try:
                # Try pandas query
                print(f"Attempting pandas query: '{query_part}'")
                filtered_df = filtered_df.query(query_part)
                print(f"Query successful, rows after query: {len(filtered_df)}")
                query_successful = True
            except Exception as query_error:
                print(f"Query failed: {query_error}")
                query_successful = False
        
        # If there's a contains part after @, apply it to the filtered results
        if contains_part and query_successful:
            print(f"Applying contains filter: '{contains_part}' to query results")
            filtered_df = self._apply_single_filter(filtered_df, contains_part)
            print(f"Rows after contains filter: {len(filtered_df) if filtered_df is not None else 0}")
        # If query was not successful and we have a contains part, try that instead
        elif not query_successful and contains_part:
            print(f"Query failed, falling back to contains search for: '{contains_part}'")
            filtered_df = self._apply_single_filter(df, contains_part)  # Use original df since query failed
            print(f"Rows after contains filter: {len(filtered_df) if filtered_df is not None else 0}")
        # If query was not successful and no contains part, try contains on the original query
        elif not query_successful and not contains_part:
            print(f"Query failed, falling back to contains search for: '{query_part}'")
            if hasattr(self, 'status_var'):
                self.status_var.set(f"Query syntax invalid, searching as text: '{query_part}'")
            filtered_df = self._apply_single_filter(df, query_part)  # Use original df since query failed
            print(f"Rows after contains filter: {len(filtered_df) if filtered_df is not None else 0}")
        
        # Ensure filtered_df is a DataFrame and not empty
        if filtered_df is not None:
            if isinstance(filtered_df, pd.Series):
                filtered_df = filtered_df.to_frame()
            if not isinstance(filtered_df, pd.DataFrame) or filtered_df.empty:
                filtered_df = pd.DataFrame(columns=df.columns)
        
        return filtered_df

    def search_columns(self, *args):
        """Search for column names matching the search text"""
        try:
            # First check if we have a valid dataframe to search in
            if not hasattr(self, 'original_csv_df') or self.original_csv_df is None:
                print("No CSV file loaded or dataframe is None")
                return
                
            # Check if we have a valid table
            if not hasattr(self, 'csv_table') or not hasattr(self.csv_table, 'model'):
                print("CSV table not initialized")
                return
                
            search_text = self.column_search_var.get().lower().strip()
            
            if search_text:
                print(f"\n=== Searching columns with: '{search_text}' ===")
            else:
                # If search text is empty, remove any column highlighting
                if hasattr(self.csv_table, 'columncolors'):
                    self.csv_table.columncolors = {}
                    self.csv_table.redraw()
                return
                
            # Check if the entered text matches a column exactly
            all_columns = self.original_csv_df.columns.tolist()
            
            # Find matching columns
            matching_column = None
            partial_matches = []
            
            for col in all_columns:
                if col.lower() == search_text:
                    matching_column = col
                    break
                elif search_text in col.lower():
                    partial_matches.append(col)
            
            if matching_column:
                # Highlight the matching column
                # self.highlight_column(matching_column)
                pass
            elif partial_matches:
                # If no exact match but we have partial matches, show a tooltip or status message
                partial_match_str = ", ".join(partial_matches[:5])
                if len(partial_matches) > 5:
                    partial_match_str += f"... ({len(partial_matches) - 5} more)"
                
                print(f"Partial matches found: {partial_match_str}")
                
                # If there's only one partial match, highlight it
                if len(partial_matches) == 1:
                    # self.highlight_column(partial_matches[0])
                    pass
                else:
                    # Show a tooltip or message about right-clicking
                    self.column_search_entry.config(background='#FFFFCC')  # Light yellow background
                    self.after(1500, lambda: self.column_search_entry.config(background='white'))  # Reset after 1.5 seconds
                    
                    # Create a tooltip-like message
                    tooltip = tk.Toplevel(self)
                    tooltip.wm_overrideredirect(True)
                    tooltip.wm_geometry(f"+{self.winfo_pointerx()+10}+{self.winfo_pointery()+10}")
                    label = tk.Label(tooltip, text=f"Found {len(partial_matches)} matches.\n\nRight-click to select.", 
                                  justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1)
                    label.pack()
                    
                    # Auto-destroy after 3 seconds
                    self.after(3000, tooltip.destroy)
            else:
                # No matches found
                print(f"No columns matching '{search_text}' found")
                self.column_search_entry.config(background='#FFCCCC')  # Light red background
                self.after(1500, lambda: self.column_search_entry.config(background='white'))  # Reset after 1.5 seconds
                
        except Exception as e:
            print(f"Error in search_columns: {e}")
            traceback.print_exc()
    
    def on_table_select(self, event):
        """Handle table row selection"""
        try:
            # Get the row that was clicked
            row = self.table.get_row_clicked(event)
            print(f"Clicked row: {row}")  # Debug print
            if self.last_clicked_row == row:
                # Get the current column as well
                col = self.table.get_col_clicked(event)
                if col is not None:
                    self.table.drawCellEntry(row, col)  # Changed from createCellEntry to drawCellEntry
            elif row is not None:            
                # Get the actual data from the filtered/sorted view                
                displayed_df = self.table.model.df
                if row < len(displayed_df):
                    # Get filename and path directly from the displayed DataFrame
                    if row < 0 or row >= len(displayed_df): # Add this check
                        print(f"Row index {row} out of bounds for displayed_df of length {len(displayed_df)}")
                        return
                    file_path = str(displayed_df.iloc[row]['File_Path'])

                    # Load the CSV file
                    self.load_csv_file(file_path)   
                self.last_clicked_row = row
        except Exception as e:
            print(f"Error in table selection: {e}")
            traceback.print_exc()

    def load_csv_file(self, file_path):
        """Load and display the selected CSV file with comprehensive error handling and diagnostics"""
        print(f"\n=== Loading CSV file: {file_path} ===")
        
        try:
            # Save plot settings before loading a new file
            if hasattr(self, 'csv_table') and hasattr(self.csv_table, 'pf'):
                self.save_plot_settings()
            
            # Save table settings before loading a new file
            if hasattr(self, 'csv_table'):
                self.save_table_settings()
            
            # Store the current file path
            self.current_csv_file = file_path
            
            # Try to read the file with advanced error handling
            df = self._advanced_file_read(file_path)
            
            # Check if file was successfully loaded before accessing attributes
            if df is None or df.empty:
                messagebox.showerror("Error", f"Failed to load or empty file: {file_path}")
                return
            
            print(f"DEBUG: Original DataFrame index type: {type(df.index)}")
            print(f"DEBUG: Original DataFrame index name: {df.index.name}")
            print(f"DEBUG: Original DataFrame index sample: {df.index[:5]}")
            
            # Store the original data
            self.original_csv_df = df.copy()

            if hasattr(self, 'saved_table_settings') and self.saved_table_settings is not None:
                if 'index_column' in self.saved_table_settings and self.saved_table_settings['index_column'] is not None:
                    saved_index_column = self.saved_table_settings['index_column']
                    print(f"Found saved index column: {saved_index_column}")
                    
                    # Check if this column exists in the new DataFrame
                    if saved_index_column in df.columns:
                        print(f"Setting {saved_index_column} as index column")
                        # Set this column as the index before applying any filters
                        df = df.set_index(saved_index_column)
                        # Update the original DataFrame as well
                        self.original_csv_df = df.copy()
                                    
            # Restore table settings if available
            self.restore_table_settings()
            
            # Clear any existing filtered data
            self.filtered_csv_df = None
            
            # Always set the initial dataframe
            self.original_csv_df = df.copy()  # Make sure we have a fresh copy
            self.csv_table.model.df = df
            self.csv_table.redraw()
            
            # Get current filter text
            filter_text = self.column_filter_var.get().strip()
            
            # Check if we have active filters
            has_row_filter = self.csv_filter_text.get().strip() != ""
            has_column_filter = (hasattr(self, 'visible_columns') and self.visible_columns is not None) or filter_text != ""
            
            # If we have a column filter, make sure visible_columns only contains columns that exist in the new DataFrame
            if has_column_filter and hasattr(self, 'visible_columns') and self.visible_columns is not None:
                # Filter visible_columns to only include columns that exist in the new DataFrame
                self.visible_columns = [col for col in self.visible_columns if col in df.columns]
                print(f"Adjusted visible_columns to match new DataFrame columns: {self.visible_columns}")
            
            # Reapply filters in the correct order
            if has_row_filter and has_column_filter:
                # Apply both row and column filtering
                print("Applying both row and column filters to new file")
                # First apply row filter (this will store filtered_csv_df)
                self.row_filter()
                # Then apply column filter to the row-filtered data
                if hasattr(self, 'filtered_csv_df') and self.filtered_csv_df is not None:
                    self._apply_column_filter_to_filtered_data()
            elif has_row_filter:
                # Apply only row filter
                print("Applying only row filter to new file")
                self.row_filter()
            elif has_column_filter:
                # Apply only column filter
                print("Applying only column filter to new file")
                if filter_text:
                    # If there's filter text, apply it to get the visible columns
                    self.filter_columns()
                elif hasattr(self, 'visible_columns') and self.visible_columns:
                    # Otherwise use the stored visible_columns if they exist
                    self._apply_column_filter()
                else:
                    # No valid visible_columns, show all columns
                    print("No valid visible_columns, showing all columns")
                    self.filtered_csv_df = None
                    self.csv_table.model.df = self.original_csv_df
                    self.csv_table.redraw()
                    self.visible_columns = list(df.columns)
                    self._apply_column_filter()
                
                # Ensure the index is properly preserved after column filtering
                self._safe_preserve_index()
            else:
                # No filters, just show the data
                print("No filters active, showing all data")
                self.csv_table.model.df = df
                self.csv_table.redraw()

            print(f"DEBUG: After filters - DataFrame index type: {type(self.csv_table.model.df.index)}")
            print(f"DEBUG: After filters - DataFrame index name: {self.csv_table.model.df.index.name}")
            print(f"DEBUG: After filters - DataFrame index sample: {self.csv_table.model.df.index[:5]}")

            # Ensure the index is properly preserved regardless of which filter was applied
            self._safe_preserve_index()     

            # Adjust column widths to fit content
            self.adjust_column_widths()
            
            # Update window title with filename
            filename = os.path.basename(file_path)
            self.title(f"CSV Browser - {filename}")
            
            # Restore plot settings if available
            self.restore_plot_settings()

            print(f"DEBUG: After restore_table_settings - DataFrame index type: {type(self.csv_table.model.df.index)}")
            print(f"DEBUG: After restore_table_settings - DataFrame index name: {self.csv_table.model.df.index.name}")
            print(f"DEBUG: After restore_table_settings - DataFrame index sample: {self.csv_table.model.df.index[:5]}")

            print(f"Successfully loaded CSV file with {len(df)} rows and {len(df.columns)} columns")
            
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load CSV file:\n{str(e)}")

    def apply_saved_filter(self, filter_config):
        """Apply a saved filter configuration"""
        try:
            # Get the filter settings
            row_filter = filter_config.get("row_filter", "")
            column_filter = filter_config.get("column_filter", "")
            
            # Apply the row filter
            if row_filter:
                self.csv_filter_text.set(row_filter)
                # Note: filter_csv_content will be called automatically due to the trace
            else:
                # Clear the row filter if empty
                self.csv_filter_text.set("")
            
            # Apply the column filter
            if column_filter:
                self.column_filter_var.set(column_filter)
                # Note: filter_columns will be called automatically due to the trace
            else:
                # Clear the column filter if empty
                self.column_filter_var.set("")
                
            # Show a confirmation message
            filter_name = filter_config.get("name", "Selected")
            messagebox.showinfo("Filter Applied", f"Filter '{filter_name}' has been applied")
            
        except Exception as e:
            print(f"Error applying filter: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to apply filter:\n{str(e)}")
            
    def restore_filter(self, filter_text):
        """Restore the filter text and apply it"""
        try:
            print("\n=== Restoring filter ===")  # Debug print
            print(f"Filter text to restore: '{filter_text}'")  # Debug print
            
            # Only proceed if we have data to filter
            if hasattr(self, 'csv_table') and self.original_csv_df is not None:
                print("CSV table and original data available")  # Debug print
                
                # Update the stored filter
                self.current_csv_filter = filter_text
                
                # Set the filter text - this will trigger filter_csv_content via the trace
                print("Setting filter text...")  # Debug print
                self.csv_filter_text.set(filter_text)
                
                print(f"Current filter text value: '{self.csv_filter_text.get()}'")  # Debug print
                
                # Force a filter operation if the trace didn't trigger
                print("Forcing filter operation...")  # Debug print
                self.row_filter()
                
                # Force a redraw
                print("Forcing table redraw...")  # Debug print
                self.csv_table.redraw()
                
                print("Filter restoration complete")  # Debug print
            else:
                print("No CSV table or original data available")  # Debug print
                
        except Exception as e:
            print(f"Error restoring filter: {e}")
            traceback.print_exc()
    
    def _highlight_column_after_filter(self, column_name):
        """Highlight a column after the filter has been cleared"""
        try:
            print(f"Checking if column '{column_name}' is now visible after clearing filter")
            
            # Clean the column name
            clean_column_name = self._clean_column_name(column_name)
            
            # Debug: Print all available columns for troubleshooting
            current_columns = list(self.csv_table.model.df.columns)
            clean_current_columns = [self._clean_column_name(col) for col in current_columns]
            print(f"Available columns after clearing filter ({len(current_columns)}): {current_columns[:10]}...")
            
            # Check if the column is now visible
            if clean_column_name in clean_current_columns:
                print(f"Column '{clean_column_name}' is now visible after clearing filter")
                # Find the actual column name
                idx = clean_current_columns.index(clean_column_name)
                actual_column = current_columns[idx]
                # self.highlight_column(actual_column)
            else:
                print(f"Column '{clean_column_name}' still not visible after clearing filter")
                
                # Try to find a close match
                closest_matches = difflib.get_close_matches(clean_column_name, clean_current_columns, n=3, cutoff=0.6)
                if closest_matches:
                    print(f"Closest matches after clearing filter: {closest_matches}")
                    
                    # Map back to actual column names
                    actual_matches = []
                    for match in closest_matches:
                        for col, clean_col in zip(current_columns, clean_current_columns):
                            if clean_col == match:
                                actual_matches.append(col)
                                break
                    
                    # Ask user if they want to use a close match
                    msg = f"Column '{clean_column_name}' still not found after clearing filters. Did you mean one of these?\n\n"
                    for i, match in enumerate(actual_matches):
                        msg += f"{i+1}. {self._clean_column_name(match)}\n"
                    
                    response = messagebox.askyesno("Column Not Found", 
                                                 msg + "\nWould you like to use the first match?")
                    if response:
                        column_name = actual_matches[0]
                        print(f"Using closest match after clearing filter: '{column_name}'")
                        # self.highlight_column(column_name)
                    else:
                        messagebox.showinfo("Column Not Found", 
                                           f"Column '{clean_column_name}' could not be found even after clearing filters.")
        except Exception as e:
            print(f"Error in _highlight_column_after_filter: {e}")
            traceback.print_exc()
    
    def _clean_column_name(self, column_name):
        """Remove any decorative elements from column names.
        
        Args:
            column_name: The column name to clean
            
        Returns:
            str: The cleaned column name without decorative elements
        """
        if column_name is None:
            return None
        
        # Convert to string if not already
        name = str(column_name).strip()
        
        # Remove arrow indicators (▲, ▼, ↑, ↓) used for sort indicators
        arrow_chars = ['▲', '▼', '↑', '↓', '△', '▽', '⬆', '⬇', '↗', '↘']
        for arrow in arrow_chars:
            name = name.replace(arrow, '')
        
        # Remove leading/trailing whitespace that may remain
        name = name.strip()
        
        # Remove any leading/trailing special characters
        name = name.strip('*#@!~`')
        
        return name

    def setup_csv_filter_context_menu(self):
        """Create a context menu for row filter with instructions and examples"""
        print("setup_csv_filter_context_menu called")
        
        # Create context menu if it doesn't exist
        if not hasattr(self, 'csv_filter_context_menu'):
            try:
                self.csv_filter_context_menu = tk.Menu(self, tearoff=0)
                
                # Add title
                self.csv_filter_context_menu.add_command(
                    label="Row Filter Help", 
                    state='disabled', 
                    font=('Arial', 10, 'bold')
                )
                
                # Add separator
                self.csv_filter_context_menu.add_separator()
                
                # Categorized examples
                categories = [
                    ("Search Operators", [
                        ("AND (space)", "Find rows containing ALL terms (implicit AND)", "term1 term2"),
                        ("OR (list)", "Find rows containing ANY term in list", "[term1,term2]"),
                        ("Exclude Text", "Exclude rows with text", "!error"),
                        ("Exact Phrase", "Find exact phrase match", "\"exact phrase\""),
                    ]),
                    ("Basic Search", [
                        ("Text Search", "Search for text in any column", "example"),
                        ("Multiple Terms", "Find rows with all terms (space = AND)", "term1 term2"),
                        ("List Pattern", "Find rows with any term in list (OR)", "[term1,term2,term3]"),
                    ]),
                    ("Pandas Query", [
                        ("Numeric Comparison", "Find values greater than", "column > 100"),
                        ("Text Matching", "Find exact text match", "column == 'value'"),
                        ("Date Range", "Find dates in range", "'2023-01-01' <= date <= '2023-12-31'"),
                        ("Multiple Conditions", "Combine conditions", "(age > 30) & (salary < 50000)"),
                    ]),
                    ("Advanced Patterns", [
                        ("Starts With", "Text starts with", "^prefix"),
                        ("Ends With", "Text ends with", "suffix$"),
                        ("Regex Pattern", "Match pattern", "col.str.match('^[A-Z]\\w*')"),
                        ("In List", "Value in list (OR)", "col in [value1,value2,value3]"),
                        ("List Pattern", "Shortcut for OR conditions", "[value1,value2,value3]"),
                    ]),
                    ("Combined Queries", [
                        ("Query + Text", "Pandas query with text search", "column > 100 @ important"),
                        ("Multiple Queries", "Chain multiple conditions", "col1 > 10 @ col2 < 5 @ !exclude"),
                    ]),
                ]
                
                # Add categories and examples
                for category, examples in categories:
                    # Add category header
                    self.csv_filter_context_menu.add_command(
                        label=f"--- {category} ---",
                        state='disabled',
                        font=('Arial', 9, 'bold')
                    )
                    
                    # Add examples for this category
                    for name, desc, example in examples:
                        # Create a submenu for each example
                        submenu = tk.Menu(self.csv_filter_context_menu, tearoff=0)
                        
                        # Add example with description
                        submenu.add_command(
                            label=f"{name}: {desc}",
                            command=lambda e=example, n=name, d=desc: self.show_row_filter_example(n, d, e)
                        )
                        
                        # Add a "Use This" button for quick application
                        submenu.add_command(
                            label=f"Use: {example}",
                            command=lambda e=example: self.apply_filter_example(e)
                        )
                        
                        # Add the submenu to the main menu
                        self.csv_filter_context_menu.add_cascade(
                            label=f"{name}: {example}",
                            menu=submenu
                        )
                
                # Add separator before actions
                self.csv_filter_context_menu.add_separator()
                
                # Add action buttons
                self.csv_filter_context_menu.add_command(
                    label="Clear Current Filter",
                    command=lambda: self.csv_filter_entry.delete(0, tk.END)
                )
                
                self.csv_filter_context_menu.add_command(
                    label="View All Examples...",
                    command=lambda: self.show_row_filter_example(
                        "Complete Filtering Guide", 
                        "Detailed explanation of all filtering options",
                        """
                        === FILTERING GUIDE ===
                        
                        1. BASIC SEARCH:
                           - text: Find text in any column
                           - !text: Exclude text
                           - text1 & text2: Both must match (AND)
                           - text1 | text2: Either can match (OR)
                        
                        2. PANDAS QUERY:
                           - column > 10: Numeric comparison
                           - col == 'value': Exact match
                           - col.str.contains('text'): Text contains
                           - col.isin([1,2,3]): Value in list
                        
                        3. COMBINED:
                           - query @ text: Apply query then text search
                           - col > 10 @ !exclude: Multiple conditions
                        
                        Use @ to chain multiple conditions together!
                        """
                    )
                )
                
                self.update_idletasks()
                print("Enhanced context menu created")
                
            except Exception as e:
                print(f"Error creating context menu: {e}")
                traceback.print_exc()
                raise
    
    def show_csv_filter_context_menu(self, event):
        """Display the context menu for CSV filter"""
        print("\n=== show_csv_filter_context_menu called ===")  # Debug print
        
        try:
            # Make sure the context menu is set up
            if not hasattr(self, 'csv_filter_context_menu'):
                self.setup_csv_filter_context_menu()
            
            if hasattr(self, 'csv_filter_context_menu'):
                print(f"Menu exists, children: {self.csv_filter_context_menu.winfo_children()}")
                
                # Unpost any existing menu first
                if self.csv_filter_context_menu.winfo_ismapped():
                    self.csv_filter_context_menu.unpost()
                
                # Post the menu at the current mouse position
                print(f"Posting menu at {event.x_root}, {event.y_root}")
                self.csv_filter_context_menu.post(event.x_root, event.y_root)
                
                # Force focus to the menu
                self.csv_filter_context_menu.focus_force()
                
                # Add binding to close menu when clicking outside
                def on_focus_out(e):
                    if (not self.csv_filter_context_menu.focus_get() and 
                        not self.csv_filter_entry.focus_get()):
                        self.csv_filter_context_menu.unpost()
                
                # Bind to focus out event
                self.csv_filter_context_menu.bind("<FocusOut>", on_focus_out, add='+')
                
                print("Menu should now be visible")
                
                # Return 'break' to prevent the default context menu
                return "break"
                
        except Exception as e:
            print(f"Error in show_csv_filter_context_menu: {e}")
            traceback.print_exc()
    
    def apply_filter_example(self, example_text):
        """Apply the filter example to the filter entry"""
        if hasattr(self, 'csv_filter_entry') and self.csv_filter_entry.winfo_exists():
            self.csv_filter_entry.delete(0, tk.END)
            self.csv_filter_entry.insert(0, example_text)
            # Trigger the filter update
            self.row_filter()
            # Move focus to the entry for immediate typing
            self.csv_filter_entry.focus_set()
            self.csv_filter_entry.icursor(tk.END)
    
    def show_row_filter_example(self, example, description, example_text=None):
        """Show a detailed tooltip with filter example and usage instructions"""
        print(f"\n=== show_row_filter_example called ===")
        print(f"Example: {example}")
        print(f"Description: {description}")
        print(f"Example text: {example_text}")
        
        # Create a custom tooltip window
        tooltip = tk.Toplevel(self)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{self.winfo_pointerx()+10}+{self.winfo_pointery()+10}")
        tooltip.attributes('-topmost', 1)  # Make sure tooltip stays on top
        
        # Create frame for better styling
        frame = tk.Frame(tooltip, borderwidth=1, relief=tk.SOLID, bg='#f0f0f0')
        frame.pack(expand=True, fill=tk.BOTH, padx=1, pady=1)
        
        # Make window draggable
        def start_move(event):
            tooltip._drag_data = {
                'x': event.x_root,
                'y': event.y_root
            }
            title_bar.config(cursor='fleur')

        def stop_move(event):
            if hasattr(tooltip, '_drag_data'):
                delattr(tooltip, '_drag_data')
            title_bar.config(cursor='')

        def do_move(event):
            if not hasattr(tooltip, '_drag_data'):
                return
                
            # Calculate new window position
            x = tooltip.winfo_x() + (event.x_root - tooltip._drag_data['x'])
            y = tooltip.winfo_y() + (event.y_root - tooltip._drag_data['y'])
            
            # Update drag data
            tooltip._drag_data['x'] = event.x_root
            tooltip._drag_data['y'] = event.y_root
            
            # Update window position
            tooltip.geometry(f"+{x}+{y}")
        
        # Title bar with proper event binding
        title_bar = tk.Frame(frame, bg='#e0e0e0', bd=1, relief=tk.RAISED)
        title_bar.pack(fill=tk.X)
        
        # Title with drag handle
        title_container = tk.Frame(title_bar, bg='#e0e0e0')
        title_container.pack(fill=tk.X, expand=True)
        
        # Title label with drag handle
        title_label = tk.Label(
            title_container, 
            text=example, 
            font=('Arial', 10, 'bold'), 
            bg='#e0e0e0', 
            fg='#333',
            padx=5,
            pady=3
        )
        title_label.pack(side=tk.LEFT)
        
        # Add a transparent label to fill the space for dragging
        drag_handle = tk.Label(
            title_container,
            text='',
            bg='#e0e0e0',
            cursor='fleur'
        )
        drag_handle.pack(fill=tk.X, expand=True, side=tk.LEFT)
        
        # Close button in title bar
        close_btn = tk.Label(
            title_bar, 
            text='×', 
            font=('Arial', 12, 'bold'),
            bg='#e0e0e0',
            fg='#666',
            padx=8,
            pady=0,
            cursor='hand2'
        )
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind('<Button-1>', lambda e: tooltip.destroy())
        
        # Bind events to the title bar and drag handle
        for widget in [title_bar, title_container, drag_handle, title_label]:
            widget.bind('<ButtonPress-1>', start_move)
            widget.bind('<B1-Motion>', do_move)
            widget.bind('<ButtonRelease-1>', stop_move)
        
        # Content frame
        content_frame = tk.Frame(frame, bg='white', padx=10, pady=10)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Description
        desc_frame = tk.Frame(content_frame, bg='white')
        desc_frame.pack(fill=tk.X, pady=(0, 10))
        
        desc_label = tk.Label(
            desc_frame, 
            text=description, 
            font=('Arial', 9), 
            bg='white', 
            justify=tk.LEFT, 
            anchor='w',
            wraplength=380
        )
        desc_label.pack(fill=tk.X)
        
        # Example code block if provided
        if example_text and example_text.strip():
            example_frame = tk.Frame(content_frame, bg='#f8f8f8', bd=1, relief=tk.SOLID)
            example_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Format the example text with line numbers and syntax highlighting
            lines = example_text.strip().split('\n')
            for i, line in enumerate(lines, 1):
                line_frame = tk.Frame(example_frame, bg='#f8f8f8')
                line_frame.pack(fill=tk.X)
                
                # Line number
                line_no = tk.Label(
                    line_frame, 
                    text=str(i).rjust(2), 
                    bg='#e8e8e8', 
                    fg='#666',
                    font=('Courier New', 9),
                    width=3,
                    anchor='e',
                    padx=2
                )
                line_no.pack(side=tk.LEFT, fill=tk.Y)
                
                # Code content
                code_label = tk.Label(
                    line_frame, 
                    text=line, 
                    bg='#f8f8f8',
                    fg='#0066cc',
                    font=('Courier New', 9),
                    justify=tk.LEFT,
                    anchor='w',
                    padx=5
                )
                code_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Action buttons
        btn_frame = tk.Frame(content_frame, bg='white')
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        if example_text and example_text.strip():
            use_btn = tk.Button(
                btn_frame,
                text="Use This Filter",
                command=lambda: [self.apply_filter_example(example_text), tooltip.destroy()],
                bg='#4CAF50',
                fg='white',
                bd=0,
                padx=15,
                pady=3,
                font=('Arial', 9)
            )
            use_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        close_btn = tk.Button(
            btn_frame,
            text="Close",
            command=tooltip.destroy,
            bg='#f0f0f0',
            bd=1,
            padx=15,
            pady=3,
            font=('Arial', 9)
        )
        close_btn.pack(side=tk.LEFT)
        
        # Dragging functions are now defined above
        
        # Bind escape key to close the tooltip
        tooltip.bind('<Escape>', lambda e: tooltip.destroy())
        
        # Focus the tooltip to receive keyboard events
        tooltip.focus_set()
        
        # Make tooltip close when clicking outside
        def on_click_outside(event):
            if event.widget == tooltip:
                tooltip.destroy()
        
        tooltip.bind('<Button-1>', on_click_outside, add='+')
        
        # Prevent closing when clicking on content
        for child in [frame, title_bar, content_frame, btn_frame]:
            child.bind('<Button-1>', lambda e: 'break')
        
        # Return the tooltip window in case we need to modify it later
        return tooltip
    
    def setup_toolbar(self):
        """Setup the toolbar with necessary controls and tooltips"""
        # Add browse folder button
        btn_browse = ttk.Button(self.toolbar, text="Browse Folder", command=self.browse_folder)
        btn_browse.pack(side="left", padx=5)
        ToolTip(btn_browse, "Open a folder to browse CSV files (Ctrl+O)")
            
        # Add load subfolders button
        btn_subfolders = ttk.Button(self.toolbar, text="Load Subfolders", command=self.load_subfolders)
        btn_subfolders.pack(side="left", padx=5)
        ToolTip(btn_subfolders, "Include CSV files from all subfolders in the current directory")

        # Add move files button
        btn_move = ttk.Button(self.toolbar, text="Move Files", command=self.move_selected_files)
        btn_move.pack(side="left", padx=5)
        ToolTip(btn_move, "Move selected files to a different folder")

        # Add copy files button
        btn_copy = ttk.Button(self.toolbar, text="Copy Files", command=self.copy_selected_files)
        btn_copy.pack(side="left", padx=5)
        ToolTip(btn_copy, "Copy selected files to a different folder")
                
        # Add delete files button
        btn_delete = ttk.Button(self.toolbar, text="Delete Files", command=self.delete_selected_files)
        btn_delete.pack(side="left", padx=5)
        ToolTip(btn_delete, "Delete selected files (moves to Recycle Bin)")

        # Add rename all files button
        btn_rename = ttk.Button(self.toolbar, text="Rename All Files", command=self.rename_all_files)
        btn_rename.pack(side="left", padx=5)
        ToolTip(btn_rename, "Rename all files based on field values from the filename structure")

        # Add reveal in explorer button
        btn_reveal = ttk.Button(self.toolbar, text="Reveal in Explorer", command=self.reveal_in_explorer)
        btn_reveal.pack(side="left", padx=5)
        ToolTip(btn_reveal, "Open the folder containing the selected file in Windows Explorer")

        # Add Merge CSV button
        self.merge_csv_button = ttk.Button(self.toolbar, text="Merge CSV", command=self.merge_selected_csv_files)
        self.merge_csv_button.pack(side="left", padx=2)
        ToolTip(self.merge_csv_button, "Merge multiple selected CSV files into one file")

        # Add open in Excel button
        btn_excel = ttk.Button(self.toolbar, text="Open in Excel", command=self.open_in_excel)
        btn_excel.pack(side="left", padx=5)
        ToolTip(btn_excel, "Open the selected CSV file in Microsoft Excel")

        # Add open in Spotfire button
        btn_spotfire = ttk.Button(self.toolbar, text="Open in Spotfire", command=self.open_in_spotfire)
        btn_spotfire.pack(side="left", padx=5)
        ToolTip(btn_spotfire, "Open the selected CSV file in TIBCO Spotfire")

        # Add correlation analysis button
        btn_corr = ttk.Button(self.toolbar, text="Correlation Analysis", command=self.save_correlation_analysis)
        btn_corr.pack(side="left", padx=5)
        ToolTip(btn_corr, "Perform correlation analysis on numeric columns and save results")

        # Add refresh button  
        btn_refresh = ttk.Button(self.toolbar, text="Refresh", command=self.refresh_file_list)
        btn_refresh.pack(side="left", padx=5)
        ToolTip(btn_refresh, "Refresh the file list (Ctrl+R or F5)")

        # Add save plot settings button
        btn_save_plot = ttk.Button(self.toolbar, text="Save Plot Settings", command=self.save_plot_settings_to_file)
        btn_save_plot.pack(side="right", padx=5)
        ToolTip(btn_save_plot, "Save current plot configuration to a JSON file")
                
        # Add load plot settings button
        btn_load_plot = ttk.Button(self.toolbar, text="Load Plot Settings", command=self.load_plot_settings_from_file)
        btn_load_plot.pack(side="right", padx=5)
        ToolTip(btn_load_plot, "Load plot configuration from a JSON file")
        
        # Add save table settings button
        btn_save_table = ttk.Button(self.toolbar, text="Save Table Settings", command=self.save_table_settings)
        btn_save_table.pack(side="right", padx=5)
        ToolTip(btn_save_table, "Save current table display settings (column widths, visibility)")

    def browse_folder(self):
        """Open a directory chooser dialog and update the file list"""
        print("\n=== Browse folder called ===")  # Debug print
        directory = filedialog.askdirectory(
            initialdir=self.current_directory
        )
        if directory:
            print(f"Selected directory: {directory}")  # Debug print
            self.current_directory = directory
            # Add to recent directories list
            self.add_to_recent_directories(directory)
            # Force explicit menu update
            self.update_recent_directories_menu()
            print(f"Recent directories menu updated with {len(self.recent_directories)} items")
            # Save settings explicitly
            print("Explicitly saving settings after directory change")
            self.save_settings()
            
            self.include_subfolders.set(False)  # Reset to not include subfolders
            
            # Update file list
            self.update_file_list()
            
            # Update max fields
            old_max = self.max_fields
            self.max_fields = self.get_max_fields()
            print(f"Max fields changed from {old_max} to {self.max_fields}")  # Debug print
            
            # Update file browser
            self.setup_file_browser()
            self.setup_csv_viewer()

    def update_file_list(self):
        """Update the list of CSV and TSV files"""
        print("\n=== Updating file list ===")  # Debug print
        print(f"Current directory: {self.current_directory}")
        print(f"Include subfolders: {self.include_subfolders.get()}")
        
        # Normalize the current directory path
        try:
            normalized_directory = self.normalize_long_path(self.current_directory)
            print(f"Normalized directory: {normalized_directory}")
        except Exception as e:
            print(f"Error normalizing directory path: {e}")
            normalized_directory = self.current_directory
        
        if self.include_subfolders.get():
            # Walk through all subdirectories with error handling
            self.csv_files = []
            try:
                for root, _, files in os.walk(normalized_directory):
                    try:
                        # Normalize the root path for each iteration
                        normalized_root = self.normalize_long_path(root)
                        print(f"Searching in subdirectory: {normalized_root}")
                        
                        for file in files:
                            if file.lower().endswith(('.csv', '.tsv')):
                                # Use normpath to ensure consistent path separators
                                full_path = os.path.normpath(os.path.join(normalized_root, file))
                                
                                # Additional path validation
                                if os.path.exists(full_path):
                                    self.csv_files.append(full_path)
                                    print(f"Found file: {full_path}")
                                else:
                                    print(f"File not accessible: {full_path}")
                    except PermissionError:
                        print(f"Permission denied accessing directory: {normalized_root}")
                    except Exception as dir_error:
                        print(f"Error searching directory {normalized_root}: {dir_error}")
                
                print(f"Found {len(self.csv_files)} CSV/TSV files in all subfolders")
            except Exception as walk_error:
                print(f"Critical error during file walk: {walk_error}")
                self.csv_files = []
        else:
            # Only get files in current directory
            try:
                files = os.listdir(normalized_directory)
                # Use normpath for consistent path separators
                self.csv_files = [
                    os.path.normpath(os.path.join(normalized_directory, f)) 
                    for f in files 
                    if f.lower().endswith(('.csv', '.tsv')) and os.path.isfile(os.path.join(normalized_directory, f))
                ]
                print(f"Found {len(self.csv_files)} CSV/TSV files in current directory")
            except PermissionError:
                print(f"Permission denied accessing directory: {normalized_directory}")
                self.csv_files = []
            except Exception as list_error:
                print(f"Error listing directory: {list_error}")
                self.csv_files = []
        
        # Print out all found files for verification
        for file in self.csv_files:
            print(f"Discovered file: {file}")
        
        if not self.csv_files:
            print("WARNING: No CSV or TSV files found. Check directory path and permissions.")
        
    def get_max_fields(self):
        """Get the maximum number of underscore-separated fields in filenames"""
        max_fields = 0
        for file_path in self.csv_files:
            # Get just the filename without path
            file_name = os.path.basename(file_path)
            # Remove extension and split by underscore
            name_without_ext = os.path.splitext(file_name)[0]
            fields = name_without_ext.split('_')
            
            # Add all field columns at once
            for i in range(len(fields)):
                field_name = f'Field_{i+1}'
                max_fields = max(max_fields, i+1)
        
        # Ensure at least 25 fields even if directory is empty
        max_fields = max(max_fields, 25)
        print(f"Max fields found: {max_fields}")  # Debug print
        return max_fields

    def open_in_excel(self):
        """Open the selected CSV file in Excel"""
        selected_rows = self.table.multiplerowlist
        if not selected_rows:
            messagebox.showinfo("Info", "Please select a file to open in Excel")
            return
    
        try:
            # Get the filtered/displayed DataFrame
            displayed_df = self.table.model.df
            
            for row in selected_rows:
                if row < len(displayed_df):
                    file_path = displayed_df.iloc[row]['File_Path']
                    os.startfile(file_path)  # This will open the file with its default application (Excel for CSV)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file in Excel:\n{str(e)}")

    def open_in_spotfire(self):
        """Open the first selected CSV file in Spotfire and copy remaining paths to clipboard"""
        selected_rows = self.table.multiplerowlist
        if not selected_rows:
            messagebox.showinfo("Info", "Please select file(s) to open in Spotfire")
            return
    
        # Create a temporary directory for files
        temp_dir = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'CSVBrowser_temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Clear any existing files in the temp directory
        for f in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, f))
            except:
                pass
        
        try:
            # Find Spotfire executable - check common installation locations
            spotfire_path = self._find_spotfire_executable()
            if not spotfire_path:
                messagebox.showerror("Spotfire Not Found", 
                    "Could not find Spotfire installation.\n\n"
                    "Please ensure Spotfire is installed or set the SPOTFIRE_PATH environment variable.")
                return
            
            # Get all selected file paths and process them
            file_paths = []
            temp_paths = []  # To store any temporary copies
            
            # Get the filtered/displayed DataFrame
            displayed_df = self.table.model.df
            
            for row in selected_rows:
                if row < len(displayed_df):
                    original_path = displayed_df.iloc[row]['File_Path']
                    file_path = self.normalize_long_path(original_path)
                    
                    # If path is too long, create a temporary copy with a shorter name
                    if len(file_path) > 200:  # Conservative limit
                        file_name = os.path.basename(file_path)
                        # Create a shorter name by using index and hash
                        short_name = f"{row}_{hash(file_path) % 1000000}_{file_name[-50:]}" if len(file_name) > 50 else file_name
                        temp_path = os.path.join(temp_dir, short_name)
                        
                        # Copy the file to temp location
                        try:
                            shutil.copy2(file_path, temp_path)
                            print(f"Created temporary copy at: {temp_path}")
                            file_paths.append(temp_path)
                            temp_paths.append(temp_path)  # Remember to track this for cleanup
                        except Exception as copy_error:
                            print(f"Error creating temporary copy: {str(copy_error)}")
                            # If copying fails, try with original path
                            file_paths.append(file_path)
                    else:
                        file_paths.append(file_path)
            
            if file_paths:
                num_files = len(file_paths)
                
                # Show info about temporary files if any were created
                if temp_paths:
                    messagebox.showinfo("Long Paths Found", 
                        f"Created {len(temp_paths)} temporary copies with shorter paths in {temp_dir}.\n"
                        "These files will remain until the application is closed.")
                
                # If there's only one file, just open it
                if num_files == 1:
                    subprocess.Popen([spotfire_path, file_paths[0]])
                    print(f"Opened single file in Spotfire: {file_paths[0]}")
                else:
                    # Open first file in Spotfire
                    first_file = file_paths[0]
                    subprocess.Popen([spotfire_path, first_file])
                    
                    # Copy remaining file paths to clipboard with double quotes
                    remaining_files = file_paths[1:]
                    quoted_paths = [f'"{path}"' for path in remaining_files]
                    clipboard_text = " ".join(quoted_paths)
                    
                    # Copy to clipboard
                    pyperclip.copy(clipboard_text)
                    
                    # Show simple notification
                    messagebox.showinfo("Multiple Files", 
                        f"Opened first file in Spotfire.\n\n"
                        f"Remaining {len(remaining_files)} file paths have been copied to clipboard with quotes.\n\n"
                        f"Use File > Add Data Table... in Spotfire to add the additional files.")
                    
                    print(f"Opened first file in Spotfire and copied {len(remaining_files)} paths to clipboard")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file(s) in Spotfire:\n{str(e)}")


    def _find_spotfire_executable(self):
        """Find the Spotfire executable on the system.
        
        Checks in order:
        1. SPOTFIRE_PATH environment variable
        2. Common installation locations
        
        Returns:
            str: Path to Spotfire executable, or None if not found
        """
        # Check environment variable first
        env_path = os.environ.get('SPOTFIRE_PATH')
        if env_path and os.path.isfile(env_path):
            print(f"Found Spotfire from environment variable: {env_path}")
            return env_path
        
        # Common Spotfire installation locations
        local_app_data = os.environ.get('LOCALAPPDATA', os.path.join(os.path.expanduser('~'), 'AppData', 'Local'))
        program_files = os.environ.get('PROGRAMFILES', 'C:\\Program Files')
        program_files_x86 = os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')
        
        # Search patterns for Spotfire installations
        search_paths = [
            # Spotfire Cloud installations (versioned)
            os.path.join(local_app_data, 'Spotfire Cloud'),
            # TIBCO Spotfire installations
            os.path.join(program_files, 'TIBCO', 'Spotfire'),
            os.path.join(program_files_x86, 'TIBCO', 'Spotfire'),
            # Spotfire Analyst installations
            os.path.join(program_files, 'Spotfire'),
            os.path.join(program_files_x86, 'Spotfire'),
        ]
        
        # Look for Spotfire.Dxp.exe in each location
        for base_path in search_paths:
            if os.path.isdir(base_path):
                # Walk through subdirectories to find the executable
                for root, dirs, files in os.walk(base_path):
                    for file in files:
                        if file.lower() == 'spotfire.dxp.exe':
                            full_path = os.path.join(root, file)
                            print(f"Found Spotfire at: {full_path}")
                            return full_path
        
        print("Spotfire executable not found in common locations")
        return None

    def get_top_correlated_columns(self, data, target_column, top_n=10):
        """
        Get the top N most correlated columns to a specified target column in a DataFrame.
        Excludes constant columns (columns with zero variance).

        Parameters:
        - data (pd.DataFrame): The input DataFrame.
        - target_column (str): The name of the target column.
        - top_n (int): The number of top correlated columns to return.

        Returns:
        - tuple: (correlation_df, data_df) where:
            - correlation_df: DataFrame with correlation information
            - data_df: DataFrame with all columns, but correlated columns moved to the front
        """
        # Store original column order for non-correlated columns
        original_columns = list(data.columns)
        
        # Ensure the target column exists in the dataset
        if target_column not in data.columns:
            raise ValueError(f"The specified target column '{target_column}' does not exist in the dataset.")
        
        # Convert all possible columns to numeric
        numeric_data = data.apply(pd.to_numeric, errors='coerce')
        
        # Remove columns with all NaN values (non-numeric columns)
        numeric_data = numeric_data.dropna(axis=1, how='all')
        
        # Ensure the target column is still in the dataset
        if target_column not in numeric_data.columns:
            raise ValueError(f"The target column '{target_column}' could not be converted to numeric type.")
        
        # Remove constant columns (columns with zero variance)
        non_constant_data = numeric_data.loc[:, numeric_data.nunique() > 1]
        
        # Check if the target column still exists after filtering
        if target_column not in non_constant_data.columns:
            raise ValueError(f"The target column '{target_column}' is constant (has zero variance).")
        
        # Calculate the correlation matrix
        cor_matrix = non_constant_data.corr()
        
        # Extract correlations for the target column
        cor_target = cor_matrix[target_column]
        
        # Create a DataFrame for sorting
        cor_target_df = pd.DataFrame({
            'Column': cor_target.index,
            'Correlation': cor_target.values
        })
        
        # Sort by absolute correlation and get the top N (excluding the target column itself)
        top_correlated = cor_target_df[cor_target_df['Column'] != target_column] \
            .sort_values(by='Correlation', key=abs, ascending=False) \
            .head(top_n)
        
        # Get the column names for the top correlated columns
        selected_columns = list(top_correlated['Column'])
        
        # Create the final column order:
        # 1. Target column
        # 2. Top correlated columns
        # 3. Remaining columns (in original order)
        final_columns = [target_column] + selected_columns
        remaining_columns = [col for col in original_columns if col not in final_columns]
        final_columns.extend(remaining_columns)
        
        # Create a DataFrame with all data in the new column order
        data_df = data[final_columns].copy()
        
        return top_correlated, data_df

    def save_correlation_analysis(self):
        """Save correlation analysis for the selected CSV file"""
        if self.current_csv_file is None or not hasattr(self, 'csv_table'):
            messagebox.showinfo("Info", "Please load a CSV file first")
            return

        # Get the current DataFrame
        df = self.csv_table.model.df
        
        # Get numeric columns that have variation
        numeric_columns = self.get_numeric_varying_columns(df)
        
        if not numeric_columns:
            messagebox.showerror("Error", "No numeric columns with variation found in the dataset")
            return
        
        # Create a dialog to get user input
        dialog = tk.Toplevel(self)
        dialog.title("Correlation Analysis Settings")
        dialog.geometry("400x200")
        
        # Make dialog modal
        dialog.transient(self)
        dialog.grab_set()
        
        # Create and pack widgets
        ttk.Label(dialog, text="Target Column:").pack(pady=5)
        target_var = tk.StringVar(value="")
        target_combo = ttk.Combobox(dialog, textvariable=target_var)
        # Set only numeric columns with variation in the dropdown
        target_combo['values'] = numeric_columns
        # Set the first numeric column as default if available
        if numeric_columns:
            target_combo.set(numeric_columns[0])
        target_combo.pack(pady=5)
        
        ttk.Label(dialog, text="Number of top correlated columns:").pack(pady=5)
        # Default to number of numeric columns - 1 (excluding target column)
        default_n = len(numeric_columns) - 1
        num_cols_var = tk.StringVar(value=str(default_n))
        num_cols_entry = ttk.Entry(dialog, textvariable=num_cols_var)
        # Add a note about the maximum available columns
        ttk.Label(dialog, text=f"(Maximum available: {default_n} columns)").pack(pady=2)
        num_cols_entry.pack(pady=5)
        
        def on_ok():
            target_col = target_var.get()
            if not target_col:
                messagebox.showerror("Error", "Please select a target column")
                return
                
            try:
                num_cols = int(num_cols_var.get())
                if num_cols <= 0:
                    raise ValueError("Number of columns must be positive")
                
                # Limit number of columns to available numeric columns - 1
                max_cols = len(numeric_columns) - 1
                if num_cols > max_cols:
                    if not messagebox.askyesno("Warning", 
                        f"Requested {num_cols} columns but only {max_cols} numeric columns available (excluding target).\n"
                        f"Continue with {max_cols} columns?"):
                        return
                    num_cols = max_cols
                
                # Get correlation analysis
                try:
                    corr_df, data_df = self.get_top_correlated_columns(df, target_col, num_cols)
                    
                    # Ask user where to save the results
                    base_path = filedialog.asksaveasfilename(
                        defaultextension=".csv",
                        filetypes=[("CSV files", "*.csv")],
                        initialdir=os.path.dirname(self.current_csv_file),
                        # Use a shorter filename by taking first 30 chars of the original name
                        initialfile=f"corr-{os.path.basename(self.current_csv_file)[:30]}"
                    )
                    
                    if base_path:
                        # Remove .csv extension if present
                        base_path = base_path.rsplit('.csv', 1)[0]
                        base_path = os.path.normpath(os.path.abspath(base_path))
                        base_path = self.normalize_long_path(base_path)

                        # Save correlation results
                        # Use shorter suffixes for output files
                        corr_path = f"{base_path}_corr.csv"
                        corr_df.to_csv(corr_path, index=False)
                        
                        # Save data with all columns
                        data_path = f"{base_path}_data.csv"
                        data_df.to_csv(data_path, index=False)
                        
                        # Create and save correlation plots
                        plots_dir = self.create_correlation_plots(data_df, target_col, corr_df, base_path)
                        
                        
                        success_message = (
                            f"Analysis saved to:\n"
                            f"Correlations: {os.path.basename(corr_path)}\n"
                            f"Data: {os.path.basename(data_path)}\n"
                        )
                        
                        if plots_dir:
                            success_message += (
                                f"\nCorrelation plots saved to:\n"
                                f"{os.path.basename(plots_dir)}/\n"
                                f"- Individual correlation plots\n"
                                f"- Combined correlation plot\n"
                            )
                        
                        success_message += "\nNote: In the data file, columns are ordered by correlation strength"
                        
                        messagebox.showinfo("Success", success_message)
                        dialog.destroy()
                        
                except Exception as e:
                    messagebox.showerror("Error", f"Error in correlation analysis:\n{str(e)}")
                
            except ValueError as e:
                messagebox.showerror("Error", "Please enter a valid positive number for top columns")
        
        def on_cancel():
            dialog.destroy()
        
        # Add OK and Cancel buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Center the dialog on the screen
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')

    def create_correlation_plots(self, data_df, target_column, corr_df, base_path):
        """
        Create scatter plots for each correlated column vs target column.
        
        Parameters:
        - data_df: DataFrame containing the data
        - target_column: Name of the target column
        - corr_df: DataFrame containing correlation information
        - base_path: Base path for saving plots
        """
        try:
            # Check for required packages
            try:
                import matplotlib.pyplot as plt
                from math import ceil
                import numpy as np
                import pandas as pd
            except ImportError as e:
                messagebox.showerror("Error", 
                    "Required plotting package not found. Please install matplotlib:\n"
                    "pip install matplotlib")
                return None
            
            # Ensure data types are numeric
            try:
                # Convert target column to numeric
                data_df[target_column] = pd.to_numeric(data_df[target_column], errors='coerce')
                
                # Convert correlated columns to numeric
                for _, row in corr_df.iterrows():
                    corr_col = row['Column']
                    data_df[corr_col] = pd.to_numeric(data_df[corr_col], errors='coerce')
                
                # Remove any rows with NaN values
                data_df = data_df.dropna(subset=[target_column] + corr_df['Column'].tolist())
                
                if len(data_df) == 0:
                    messagebox.showerror("Error", "No valid numeric data found after conversion")
                    return None
                    
            except Exception as e:
                messagebox.showerror("Error", f"Error converting data to numeric format:\n{str(e)}")
                return None
            
            # Create a directory for plots if it doesn't exist
            # plots_dir = os.path.normpath(f"{base_path}_plots")
            plots_dir = self.normalize_long_path(f"{base_path}_plots")
            os.makedirs(plots_dir, exist_ok=True)
            
            # Set style for better visibility
            plt.style.use('default')
            
            # Create individual scatter plots
            for _, row in corr_df.iterrows():
                corr_col = row['Column']
                corr_val = row['Correlation']
                
                # Create figure with white background
                plt.figure(figsize=(10, 6), facecolor='white')
                
                # Get numeric data for plotting
                x_data = data_df[target_column].values  # Target column on x-axis
                y_data = data_df[corr_col].values      # Correlated column on y-axis
                
                # Create scatter plot with improved styling
                plt.scatter(x_data, y_data, alpha=0.5, c='#1f77b4', edgecolors='none')
                
                # Add trend line
                z = np.polyfit(x_data, y_data, 1)
                p = np.poly1d(z)
                x_range = np.linspace(x_data.min(), x_data.max(), 100)
                plt.plot(x_range, p(x_range), "r--", alpha=0.8, linewidth=2)
                
                # Add labels and title with improved styling
                plt.xlabel(target_column, fontsize=12, fontweight='bold')  # Target column on x-axis
                plt.ylabel(corr_col, fontsize=12, fontweight='bold')      # Correlated column on y-axis
                plt.title(f'Correlation: {corr_val:.3f}', fontsize=14, pad=15)
                
                # Add grid with lighter style
                plt.grid(True, alpha=0.3, linestyle='--')
                
                # Improve tick label visibility
                plt.xticks(fontsize=10)
                plt.yticks(fontsize=10)
                
                # Add a light box around the plot
                plt.box(True)
                
                # Adjust layout
                plt.tight_layout()
                
                # Save plot with white background
                plt.savefig(os.path.normpath(os.path.join(plots_dir, f"{corr_col}_vs_{target_column}.png")), 
                           dpi=300, bbox_inches='tight', facecolor='white')
                plt.close()
            
            # Create combined plot
            n_cols = min(len(corr_df), 3)
            n_rows = ceil(len(corr_df) / n_cols)
            
            # Create figure with white background
            fig, axes = plt.subplots(n_rows, n_cols, 
                                   figsize=(5*n_cols, 4*n_rows), 
                                   facecolor='white')
            fig.suptitle(f'Correlation Plots for {target_column}', 
                        fontsize=16, y=1.02, fontweight='bold')
            
            # Flatten axes for easier iteration
            if n_rows * n_cols > 1:
                axes_flat = axes.flatten()
            else:
                axes_flat = [axes]
            
            # Create subplots
            for idx, (_, row) in enumerate(corr_df.iterrows()):
                corr_col = row['Column']
                corr_val = row['Correlation']
                
                ax = axes_flat[idx]
                
                # Get numeric data for plotting
                x_data = data_df[target_column].values  # Target column on x-axis
                y_data = data_df[corr_col].values      # Correlated column on y-axis
                
                # Create scatter plot with improved styling
                ax.scatter(x_data, y_data, alpha=0.5, c='#1f77b4', edgecolors='none')
                
                # Add trend line
                z = np.polyfit(x_data, y_data, 1)
                p = np.poly1d(z)
                x_range = np.linspace(x_data.min(), x_data.max(), 100)
                ax.plot(x_range, p(x_range), "r--", alpha=0.8, linewidth=2)
                
                # Add labels and title with improved styling
                ax.set_xlabel(target_column, fontsize=10, fontweight='bold')  # Target column on x-axis
                ax.set_ylabel(corr_col, fontsize=10, fontweight='bold')      # Correlated column on y-axis
                ax.set_title(f'Correlation: {corr_val:.3f}', fontsize=12)
                
                # Add grid with lighter style
                ax.grid(True, alpha=0.3, linestyle='--')
                
                # Improve tick label visibility
                ax.tick_params(labelsize=8)
                
                # Add a light box around the plot
                ax.set_frame_on(True)
            
            # Remove empty subplots
            for idx in range(len(corr_df), len(axes_flat)):
                fig.delaxes(axes_flat[idx])
            
            # Adjust layout
            plt.tight_layout()
            
            # Save combined plot with white background
            plt.savefig(os.path.normpath(os.path.join(plots_dir, "combined_correlation_plots.png")), 
                        dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            return plots_dir
            
        except Exception as e:
            error_msg = str(e)
            messagebox.showerror("Error", f"Error creating correlation plots:\n{error_msg}")
            return None

    def get_numeric_varying_columns(self, data):
        """
        Get list of columns that are numeric and have more than one unique value.
        
        Parameters:
        - data (pd.DataFrame): Input DataFrame
        
        Returns:
        - list: List of column names that are numeric and non-constant
        """
        numeric_columns = []
        for col in data.columns:
            # Try to convert to numeric
            numeric_series = pd.to_numeric(data[col], errors='coerce')
            # Check if conversion was successful (not all NaN) and has more than one unique value
            if not numeric_series.isna().all() and data[col].nunique() > 1:
                numeric_columns.append(col)
        return numeric_columns

    def reconstruct_filename(self, row):
        """Reconstruct filename from columns starting with 'Field_'"""
        # Find columns starting with 'Field_'
        f_columns = [col for col in row.index if col.startswith('Field_')]
        
        # Extract values from these columns, skipping None/empty values
        filename_parts = [str(row[col]) for col in f_columns if pd.notna(row[col]) and str(row[col]).strip()]
        
        # Join with underscore, add .csv extension
        new_filename = '_'.join(filename_parts).replace('\n', '') + '.csv'
        
        return new_filename
    
    def rename_csv_file(self, old_filepath, new_filename):
        """Rename CSV file on disk"""
        try:
            # Convert to raw string and normalize path separators
            old_filepath = os.path.normpath(str(old_filepath).replace('/', os.sep))
            directory = os.path.dirname(old_filepath)
            new_filepath = os.path.normpath(os.path.join(directory, new_filename))
            
            print("\nRenaming file details:")  # Debug prints
            print(f"Original path: {old_filepath}")
            print(f"Directory: {directory}")
            print(f"New filename: {new_filename}")
            print(f"New full path: {new_filepath}")
            
            # Check if source file exists
            if not os.path.exists(old_filepath):
                print(f"Source file not found: {old_filepath}")  # Debug print
                raise FileNotFoundError(f"Source file not found: {old_filepath}")
            
            # Check if target directory exists
            if not os.path.exists(directory):
                raise FileNotFoundError(f"Target directory not found: {directory}")
            
            # Check if target file already exists
            if os.path.exists(new_filepath):
                raise FileExistsError(f"Target file already exists: {new_filepath}")
            
            # Rename the file
            print(f"Performing rename operation...")  # Debug print
            os.rename(old_filepath, new_filepath)
            print(f"Rename successful")  # Debug print
            return new_filepath
            
        except Exception as e:
            print(f"\nError renaming file:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print(f"Old path: {old_filepath}")
            print(f"New filename: {new_filename}")
            print(f"Directory: {directory}")
            print("\nFull traceback:")
            traceback.print_exc()
            return old_filepath

    def rename_all_files(self):
        """Rename all files where constructed name differs from current name"""
        try:
            renamed_count = 0
            for idx, row in self.df.iterrows():
                current_name = row['Name']
                new_name = self.reconstruct_filename(row)
                
                if new_name != current_name:
                    old_path = row['File_Path']
                    new_path = self.rename_csv_file(old_path, new_name)
                    
                    # Update the DataFrame
                    self.df.at[idx, 'Name'] = new_name
                    self.df.at[idx, 'File_Path'] = new_path
                    renamed_count += 1
            
            if renamed_count > 0:
                # Update the table display
                self.table.model.df = self.df
                self.table.redraw()
                messagebox.showinfo("Files Renamed", 
                                 f"Renamed {renamed_count} files based on field values")
            else:
                messagebox.showinfo("No Changes", 
                                 "All filenames already match their field values")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename files: {str(e)}")

    def refresh_file_list(self):
        """Refresh the file list and reload the currently selected file if any"""
        print("\n=== Refreshing file list ===")  # Debug print
        
        # Store the currently selected file path
        current_selected_file = None
        current_selected_row = None
        
        # Check if a file is currently selected
        if hasattr(self, 'table') and hasattr(self, 'df'):
            selected_rows = self.table.multiplerowlist
            if selected_rows and selected_rows[0] < len(self.df):
                current_selected_row = selected_rows[0]
                current_selected_file = self.df.iloc[current_selected_row]['File_Path']
        
        # Update the file list
        self.update_file_list()
        
        # Update max fields
        old_max = self.max_fields
        self.max_fields = self.get_max_fields()
        print(f"Max fields changed from {old_max} to {self.max_fields}")  # Debug print
        
        # Update file browser
        self.setup_file_browser()
        self.setup_csv_viewer()
        
        # Attempt to reload the previously selected file
        if current_selected_file and os.path.exists(current_selected_file):
            try:
                # Find the row of the previously selected file in the new dataframe
                selected_row = self.df[self.df['File_Path'] == current_selected_file].index
                
                if not selected_row.empty:
                    # Select the row in the table
                    self.table.setSelectedRow(selected_row[0])
                    
                    # Load the CSV file using the method that populates the CSV viewer
                    self.load_csv_file(current_selected_file)   
                self.last_clicked_row = selected_row[0]
            except Exception as e:
                print(f"Error reloading selected file: {e}")

    def toggle_layout(self):
        """Toggle between horizontal and vertical layouts"""
        # Toggle orientation
        self.is_horizontal = not self.is_horizontal
        
        # Update button text
        self.toggle_btn.configure(
            text="Switch to Vertical Layout" if self.is_horizontal else "Switch to Horizontal Layout"
        )

        # Remove old panes
        if hasattr(self, 'paned'):
            self.paned.pack_forget()
            
        # Create new layout
        self.setup_panels()
        
        # Restore file browser and CSV viewer
        self.setup_file_browser()
        self.setup_csv_viewer()
        
        # Force geometry update
        self.update_idletasks()
        
        # Set final sash position
        if self.is_horizontal:
            self.paned.sashpos(0, 400)
        else:
            self._schedule_vertical_sash_adjustment()
            
    def copy_selected_files(self):
        """Copy selected files to another folder"""
        # Get selected rows from the table's multiplerowlist
        selected_rows = self.table.multiplerowlist
        if not selected_rows:
            messagebox.showinfo("Info", "Please select files to copy")
            return

        # Ask for destination directory once
        dest_dir = filedialog.askdirectory(
            title="Select Destination Folder",
            initialdir=os.path.dirname(self.current_directory)
        )
        if not dest_dir:
            return
            
        # Normalize the destination directory
        dest_dir = os.path.normpath(os.path.abspath(dest_dir))
        
        try:
            copied_files = []
            failed_files = []
            
            # Get the filtered/displayed DataFrame
            displayed_df = self.table.model.df
            
            for row in selected_rows:
                if row < len(displayed_df):
                    filename = displayed_df.iloc[row]['Name']
                    
                    # Use the stored file path from the displayed DataFrame
                    if 'File_Path' in displayed_df.columns and not pd.isna(displayed_df.iloc[row]['File_Path']):
                        src_path = displayed_df.iloc[row]['File_Path']
                    else:
                        # Fall back to constructing the path
                        src_path = os.path.join(self.current_directory, filename)
                    
                    # Normalize the source path
                    src_path = os.path.normpath(os.path.abspath(src_path))
                    
                    # Destination path
                    dst_path = os.path.join(dest_dir, filename)
                    
                    print(f"Copying file: {src_path} to {dst_path}")
                    
                    try:
                        # Check if source file exists
                        if not os.path.exists(src_path):
                            print(f"Source file not found: {src_path}")  # Debug print
                            # Try with forward slashes
                            alt_path = src_path.replace(os.sep, '/')
                            if os.path.exists(alt_path):
                                src_path = alt_path
                                print(f"Found file using alternative path: {alt_path}")  # Debug print
                            else:
                                failed_files.append((filename, "Source file not found"))
                                continue
                        
                        # Check if file already exists in destination
                        if os.path.exists(dst_path):
                            if not messagebox.askyesno("File Exists", 
                                f"File {filename} already exists in destination.\nDo you want to overwrite it?"):
                                continue
                        
                        # Copy the file
                        shutil.copy2(src_path, dst_path)  # copy2 preserves metadata
                        copied_files.append(filename)
                        
                        # If we're copying a CSV file that's currently loaded, update the path
                        if hasattr(self, 'current_csv_file') and self.current_csv_file == src_path:
                            self.current_csv_file = dst_path
                            
                    except PermissionError as pe:
                        failed_files.append((filename, f"Permission denied: {str(pe)}"))
                    except Exception as e:
                        print(f"Error copying file {filename}: {e}")
                        failed_files.append((filename, str(e)))
            
            # Show success message
            if copied_files:
                messagebox.showinfo("Success", f"Copied {len(copied_files)} files to:\n{dest_dir}")
            
            # Show errors if any files failed to copy
            if failed_files:
                error_message = "Failed to copy the following files:\n\n"
                for filename, reason in failed_files:
                    error_message += f"• {filename}: {reason}\n"
                
                messagebox.showerror("Copy Errors", error_message)
                
        except Exception as e:
            print(f"Error in copy_selected_files: {e}")
            messagebox.showerror("Error", f"Failed to copy files:\n{str(e)}")

    def move_selected_files(self):
        """Move selected files to a new directory"""
        try:
            # Get selected rows from the table
            selected_rows = self.table.multiplerowlist
            
            # Check if any files are selected
            if not selected_rows:
                messagebox.showinfo("Info", "Please select files to move")
                return
            
            # Open directory selection dialog
            destination_dir = filedialog.askdirectory(
                title="Select Destination Folder for Moving Files",
                initialdir=os.path.dirname(self.current_directory)
            )
            
            # Check if a destination was selected
            if not destination_dir:
                return
            
            # Track successful and failed moves
            moved_files = []
            failed_files = []
            
            # Move each selected file
            for row in selected_rows:
                try:
                    # Get the actual file path from the filtered DataFrame
                    file_path = self.table.model.df.iloc[row]['File_Path']
                    
                    # Generate destination file path
                    file_name = os.path.basename(file_path)
                    dest_path = os.path.join(destination_dir, file_name)
                    
                    # Ensure unique filename if file already exists
                    counter = 1
                    while os.path.exists(dest_path):
                        name, ext = os.path.splitext(file_name)
                        dest_path = os.path.join(destination_dir, f"{name}_{counter}{ext}")
                        counter += 1
                    
                    # Move the file
                    shutil.move(file_path, dest_path)
                    moved_files.append(file_path)
                    
                except Exception as e:
                    failed_files.append((file_path, str(e)))

            # Provide summary of move operation
            if moved_files:
                # Refresh file list after moving
                self.update_file_list()
                
                # Create summary message
                summary_msg = f"Moved {len(moved_files)} file(s) to {destination_dir}"
                if failed_files:
                    summary_msg += f"\n\nFailed to move {len(failed_files)} file(s):"
                    for file, error in failed_files:
                        summary_msg += f"\n- {os.path.basename(file)}: {error}"
                
                messagebox.showinfo("Move Files", summary_msg)
            else:
                messagebox.showwarning("Move Files", "No files were moved")
        
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while moving files:\n{str(e)}")

    def delete_selected_files(self):
        """Delete selected files"""
        # Get selected rows from the table's multiplerowlist
        selected_rows = self.table.multiplerowlist
        if not selected_rows:
            messagebox.showinfo("Info", "Please select a file to delete")
            return

        # Show confirmation dialog with count of files
        if not messagebox.askyesno("Confirm Delete", 
                                f"Are you sure you want to delete {len(selected_rows)} selected files?",
                                icon='warning'):
            return

        deleted_files = []
        failed_files = []
        try:
            # Get the filtered/displayed DataFrame
            displayed_df = self.table.model.df
            
            for row in selected_rows:
                if row < len(displayed_df):
                    file_path = displayed_df.iloc[row]['File_Path']
                    
                    # Normalize the path to handle potential issues
                    file_path = os.path.normpath(file_path)
                    
                    # Ensure the file path exists
                    if not os.path.exists(file_path):
                        messagebox.showerror("Error", f"File not found: {file_path}")
                        continue
                    
                    # Use Windows-specific command to open and select file
                    try:
                        # Check if file is in use or locked
                        try:
                            # Try to open the file in exclusive write mode to check if it's locked
                            with open(file_path, 'a+b') as test_file:
                                pass
                        except PermissionError:
                            # File is locked or in use
                            failed_files.append((file_path, "File is in use by another program"))
                            continue
                        
                        # Delete the file
                        print(f"Performing delete operation...")  # Debug print
                        os.remove(file_path)
                        deleted_files.append(file_path)
                        
                        # Clear CSV viewer if it was the deleted file
                        if hasattr(self, 'current_file') and self.current_file == file_path:
                            self.current_file = None
                            self.current_csv_file = None
                            if hasattr(self, 'csv_table') and hasattr(self.csv_table, 'model'):
                                self.csv_table.model.df = pd.DataFrame()
                                self.csv_table.redraw()
                                
                    except PermissionError as pe:
                        failed_files.append((file_path, f"Permission denied: {str(pe)}"))
                    except FileNotFoundError as fnf:
                        failed_files.append((file_path, f"File not found: {str(fnf)}"))
                    except Exception as e:
                        print(f"Exception during delete: {e}")
                        failed_files.append((file_path, str(e)))

            # Update the file list after deletion
            if deleted_files:
                # Refresh the file list instead of manually updating the DataFrame
                self.update_file_list()
                
                if len(deleted_files) == 1:
                    messagebox.showinfo("Success", f"Deleted file: {os.path.basename(deleted_files[0])}")
                else:
                    messagebox.showinfo("Success", f"Deleted {len(deleted_files)} files")
            
            # Show errors if any files failed to delete
            if failed_files:
                error_message = "Failed to delete the following files:\n\n"
                for filename, reason in failed_files:
                    error_message += f"• {os.path.basename(filename)}: {reason}\n"
                
                messagebox.showerror("Delete Errors", error_message)
                
        except Exception as e:
            print(f"Error in delete_selected_files: {e}")
            messagebox.showerror("Error", f"An error occurred during file deletion:\n{str(e)}")
            traceback.print_exc()

    def load_subfolders(self):
        """Load all CSV and TSV files from current directory and all subdirectories"""
        try:
            print("\n=== Loading files from subfolders ===")  # Debug print
            
            # Set include_subfolders to True
            self.include_subfolders.set(True)
            
            # Use standard directory selection
            directory = filedialog.askdirectory(
                initialdir=self.current_directory
            )
            
            # Validate the selected directory
            if directory:
                # Update current directory
                self.current_directory = directory
                
                # Add to recent directories list
                self.add_to_recent_directories(directory)
                # Force explicit menu update
                self.update_recent_directories_menu()
                print(f"Recent directories menu updated with {len(self.recent_directories)} items")
                # Save settings explicitly
                print("Explicitly saving settings after directory change")
                self.save_settings()
                
                # Update file list
                self.update_file_list()
                
                # Update file browser dataframe
                self.update_file_dataframe()
                
                # Refresh the file browser table
                if hasattr(self, 'table'):
                    self.table.model.df = self.df
                    self.table.redraw()
                
                # Show summary of files found
                messagebox.showinfo("Subfolder Search", 
                    f"Found {len(self.csv_files)} CSV/TSV files in {directory}")
            
        except Exception as e:
            print(f"Error in load_subfolders: {e}")
            messagebox.showerror("Error", "Failed to load subfolders")

    def update_file_dataframe(self):
        """Update the pandas DataFrame with file information"""
        print("\n=== Updating File DataFrame ===")
        
        # Ensure csv_files is a list
        if not hasattr(self, 'csv_files'):
            self.csv_files = []
        
        # If no files found, create an empty DataFrame with expected columns
        if not self.csv_files:
            print("WARNING: No CSV/TSV files found in the directory.")
            self.df = pd.DataFrame(columns=[
                'Name', 'File_Path', 'Size', 'Modified', 
                'Type'
            ] + [f'Field_{i+1}' for i in range(25)])
            return
        
        # Prepare lists to store file information
        names = []
        file_paths = []
        sizes = []
        modified_times = []
        types = []
        
        # Collect file information
        for file_path in self.csv_files:
            try:
                # Get file stats
                file_stat = os.stat(file_path)
                
                # Extract filename and path
                file_name = os.path.basename(file_path)
                
                # Collect basic file information
                names.append(file_name)
                file_paths.append(file_path)
                sizes.append(self.format_size(file_stat.st_size))
                modified_times.append(self.format_date(file_stat.st_mtime))
                types.append(os.path.splitext(file_name)[1][1:].upper())
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
        
        # Create initial DataFrame
        self.df = pd.DataFrame({
            'Name': names,
            'File_Path': file_paths,
            'Size': sizes,
            'Modified': modified_times,
            'Type': types
        })
        
        # Add dynamic Field columns based on filename
        for i in range(25):  # Ensure at least 25 fields
            field_name = f'Field_{i+1}'
            self.df[field_name] = self.df['Name'].apply(
                lambda x: self._extract_field(x, i) if '_' in x else ''
            )
        
        # Print DataFrame info for debugging
        print(f"Created DataFrame with {len(self.df)} rows")
        print("DataFrame Columns:", list(self.df.columns))
        
        # Optional: Sort by modified time (newest first)
        try:
            self.df['Modified_Datetime'] = pd.to_datetime(self.df['Modified'], errors='coerce')
            self.df = self.df.sort_values('Modified_Datetime', ascending=False)
            self.df = self.df.drop(columns=['Modified_Datetime'])
        except Exception as sort_error:
            print(f"Error sorting DataFrame: {sort_error}")
        
        # Reset index to ensure clean indexing
        self.df = self.df.reset_index(drop=True)
    
    def _extract_field(self, filename, field_index):
        """Extract a specific field from filename split by underscore"""
        try:
            # Remove extension
            name_without_ext = os.path.splitext(filename)[0]
            
            # Split by underscore
            fields = name_without_ext.split('_')
            
            # Return field if exists, otherwise empty string
            return fields[field_index] if field_index < len(fields) else ''
        except Exception as e:
            print(f"Error extracting field from {filename}: {e}")
            return ''

    def setup_column_search_menu(self):
        """Set up the right-click menu for column search"""
        self.column_search_menu = tk.Menu(self, tearoff=0)
        
        # The menu will be populated dynamically when shown

    def show_column_search_menu(self, event=None):
        """Show the column search menu with matching columns"""
        try:
            # First check if we have a valid dataframe to search in
            if not hasattr(self, 'original_csv_df') or self.original_csv_df is None:
                print("No CSV file loaded or dataframe is None")
                # Show a message to the user
                self.column_search_entry.config(background='#FFCCCC')  # Light red background
                self.after(1500, lambda: self.column_search_entry.config(background='white'))  # Reset after 1.5 seconds
                return
                
            # Check if we have a valid table
            if not hasattr(self, 'csv_table') or not hasattr(self.csv_table, 'model'):
                print("CSV table not initialized")
                return
                
            search_text = self.column_search_var.get().lower().strip()
            
            if not search_text:
                # When empty, show all available columns
                self.column_search_menu.delete(0, tk.END)
                all_columns = self.original_csv_df.columns.tolist()
                all_columns_sorted = sorted(all_columns, key=lambda x: str(x).lower())

                # Local callback creator
                def make_callback_all(column):
                    def callback():
                        self.column_search_var.set(column)
                        self.last_searched_column = column
                    return callback

                # Group into submenus if many columns
                if len(all_columns_sorted) > 20:
                    group_size = 15
                    for i in range(0, len(all_columns_sorted), group_size):
                        group = all_columns_sorted[i:i+group_size]
                        start_letter = str(group[0])[0].upper()
                        end_letter = str(group[-1])[0].upper()

                        submenu = tk.Menu(self.column_search_menu, tearoff=0)
                        for col in group:
                            submenu.add_command(label=col, command=make_callback_all(col))
                        self.column_search_menu.add_cascade(
                            label=f"{start_letter}-{end_letter} ({len(group)} columns)",
                            menu=submenu
                        )
                else:
                    for col in all_columns_sorted:
                        self.column_search_menu.add_command(label=col, command=make_callback_all(col))

                self.column_search_menu.add_separator()
                self.column_search_menu.add_command(
                    label="Clear Search",
                    command=lambda: self.column_search_var.set("")
                )

                # Show the menu at the event position
                if event:
                    self.column_search_menu.post(event.x_root, event.y_root)
                else:
                    x = self.column_search_entry.winfo_rootx()
                    y = self.column_search_entry.winfo_rooty() + self.column_search_entry.winfo_height()
                    self.column_search_menu.post(x, y)
                return "break"
                
            print(f"\n=== Searching columns with: '{search_text}' ===")
            
            # Clear existing menu items
            self.column_search_menu.delete(0, tk.END)
            
            # Find matching columns
            all_columns = self.original_csv_df.columns.tolist()
            exact_matches = []
            partial_matches = []
            
            for col in all_columns:
                col_str = str(col).lower()
                if col_str == search_text:
                    exact_matches.append(col)
                elif search_text in col_str:
                    partial_matches.append(col)
            
            # If no exact or partial matches, try fuzzy matching
            if not exact_matches and not partial_matches and len(search_text) > 2:
                # Use difflib for fuzzy matching
                import difflib
                fuzzy_matches = difflib.get_close_matches(search_text, 
                                                         [str(col).lower() for col in all_columns], 
                                                         n=10, 
                                                         cutoff=0.6)
                
                # Get the original case for these matches
                fuzzy_matches = [col for col in all_columns 
                                if str(col).lower() in fuzzy_matches]
            else:
                fuzzy_matches = []
            
            # Sort matches for better usability
            exact_matches.sort(key=lambda x: str(x).lower())
            partial_matches.sort(key=lambda x: str(x).lower())
            fuzzy_matches.sort(key=lambda x: str(x).lower())
            
            # Helper function to create a callback for a specific column
            def make_callback(column):
                def callback():
                    self.column_search_var.set(column)
                    self.last_searched_column = column
                return callback
            
            # Add header for exact matches if any
            if exact_matches:
                self.column_search_menu.add_command(
                    label="=== Exact Matches ===", 
                    state=tk.DISABLED,
                    background='#E0E0E0'
                )
                
                for col in exact_matches:
                    self.column_search_menu.add_command(
                        label=col,
                        command=make_callback(col)
                    )
                
                # Add separator if we have both exact and partial matches
                if partial_matches or fuzzy_matches:
                    self.column_search_menu.add_separator()
            
            # Add header for partial matches if any
            if partial_matches:
                self.column_search_menu.add_command(
                    label="=== Partial Matches ===", 
                    state=tk.DISABLED,
                    background='#E0E0E0'
                )
                
                # Group partial matches if there are many
                if len(partial_matches) > 15:
                    # Create submenus for groups of columns
                    group_size = 10
                    for i in range(0, len(partial_matches), group_size):
                        group = partial_matches[i:i+group_size]
                        start_letter = str(group[0])[0].upper()
                        end_letter = str(group[-1])[0].upper()
                        
                        submenu = tk.Menu(self.column_search_menu, tearoff=0)
                        for col in group:
                            submenu.add_command(
                                label=col,
                                command=make_callback(col)
                            )
                        
                        self.column_search_menu.add_cascade(
                            label=f"{start_letter}-{end_letter} ({len(group)} columns)",
                            menu=submenu
                        )
                else:
                    # Add all partial matches directly to the menu
                    for col in partial_matches:
                        self.column_search_menu.add_command(
                            label=col,
                            command=make_callback(col)
                        )
                
                # Add separator if we have both partial and fuzzy matches
                if fuzzy_matches:
                    self.column_search_menu.add_separator()
            
            # Add header for fuzzy matches if any
            if fuzzy_matches:
                self.column_search_menu.add_command(
                    label="=== Similar Matches ===", 
                    state=tk.DISABLED,
                    background='#E0E0E0'
                )
                
                for col in fuzzy_matches:
                    self.column_search_menu.add_command(
                        label=col,
                        command=make_callback(col)
                    )
            
            # If no matches found, show a message
            if not exact_matches and not partial_matches and not fuzzy_matches:
                self.column_search_menu.add_command(
                    label=f"No columns matching '{search_text}'",
                    state=tk.DISABLED
                )
            
            # Add a separator and additional options
            self.column_search_menu.add_separator()
            
            # Add Move to Start option
            if self.last_searched_column:
                self.column_search_menu.add_command(
                    label=f"Move '{self.last_searched_column}' to Start",
                    command=self.move_searched_column_to_start
                )
                self.column_search_menu.add_separator()
            
            self.column_search_menu.add_command(
                label="Clear Search",
                command=lambda: self.column_search_var.set("")
            )
            
            # Show the menu at the event position
            if event:
                self.column_search_menu.post(event.x_root, event.y_root)
            else:
                # If called programmatically, show near the search entry
                x = self.column_search_entry.winfo_rootx()
                y = self.column_search_entry.winfo_rooty() + self.column_search_entry.winfo_height()
                self.column_search_menu.post(x, y)
            
        except Exception as e:
            print(f"Error in show_column_search_menu: {e}")
            traceback.print_exc()
    
    def focus_column_search(self, event=None):
        """Focus on the column search box"""
        if hasattr(self, 'column_search_entry'):
            self.column_search_entry.focus_set()
            # Select all text if there's any
            self.column_search_entry.select_range(0, tk.END)
            return "break"  # Prevent default behavior

    def create_menu(self):
        """Create the application menu"""
        menubar = tk.Menu(self)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Directory", command=self.browse_directory)  # Use the browse_directory method
        file_menu.add_command(label="Open CSV File", command=self.open_csv_file)
        
        # Add recent directories submenu
        self.recent_dirs_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Directories", menu=self.recent_dirs_menu)
        self.update_recent_directories_menu()
        
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)  # Use self.quit instead of self.master.quit
        menubar.add_cascade(label="File", menu=file_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Horizontal Layout", command=self.set_horizontal_layout)
        view_menu.add_command(label="Vertical Layout", command=self.set_vertical_layout)
        view_menu.add_separator()
        view_menu.add_command(label="Find Column (Ctrl+F)", command=self.focus_column_search)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.config(menu=menubar)  # Use self.config instead of self.master.config

    def set_horizontal_layout(self):
        """Set the layout to horizontal (file browser on left, CSV viewer on right)"""
        if not self.is_horizontal:
            # Remove existing panes
            for widget in self.paned.panes():
                self.paned.forget(widget)
                
            # Change orientation
            self.paned.configure(orient=tk.HORIZONTAL)
            self.is_horizontal = True
            
            # Re-add the panes
            self.paned.add(self.file_frame, weight=1)
            self.paned.add(self.csv_container, weight=3)
            
            # Set sash position
            self.after(100, lambda: self.paned.sashpos(0, 400))
            
    def set_vertical_layout(self):
        """Set the layout to vertical (file browser on top, CSV viewer on bottom)"""
        if self.is_horizontal:
            # Remove existing panes
            for widget in self.paned.panes():
                self.paned.forget(widget)
                
            # Change orientation
            self.paned.configure(orient=tk.VERTICAL)
            self.is_horizontal = False
            
            # Re-add the panes
            self.paned.add(self.file_frame, weight=1)
            self.paned.add(self.csv_container, weight=3)
            
            # Set sash position
            self._schedule_vertical_sash_adjustment()
    
    def show_about(self):
        """Show the about dialog"""
        about_text = """CSV Browser

A tool for browsing and viewing CSV files with advanced column search functionality.

Features:
- File browser with:
  - Sorting by name, date, size, and filename fields
  - Dynamic columns based on filename structure
  - Filter functionality across all fields
  - Horizontal scrolling for many fields
- CSV file preview in second panel
- Vertical and horizontal layout options
- Directory selection
- File operations (move, delete)
"""
        messagebox.showinfo("About CSV Browser", about_text)
    
    def browse_directory(self):
        """Open a directory chooser dialog and update the file list"""
        print("\n=== Browse directory called ===")  # Debug print
        directory = filedialog.askdirectory(
            initialdir=self.current_directory
        )
        if directory:
            print(f"Selected directory: {directory}")  # Debug print
            self.current_directory = directory
            
            # Add to recent directories list
            self.add_to_recent_directories(directory)
            # Force explicit menu update
            self.update_recent_directories_menu()
            print(f"Recent directories menu updated with {len(self.recent_directories)} items")
            # Save settings explicitly
            print("Explicitly saving settings after directory change")
            self.save_settings()
            
            self.include_subfolders.set(False)  # Reset to not include subfolders
            
            # Update file list
            self.update_file_list()
            
            # Update max fields
            old_max = self.max_fields
            self.max_fields = self.get_max_fields()
            print(f"Max fields changed from {old_max} to {self.max_fields}")  # Debug print
            

    def add_to_recent_directories(self, directory):
        """Add a directory to the recent directories list"""
        try:
            print(f"Adding to recent directories: {directory}")
            
            # Remove the directory if it already exists in the list
            if directory in self.recent_directories:
                self.recent_directories.remove(directory)
                
            # Add the directory to the beginning of the list
            self.recent_directories.insert(0, directory)
            
            # Trim the list to max_recent_directories
            if len(self.recent_directories) > self.max_recent_directories:
                self.recent_directories = self.recent_directories[:self.max_recent_directories]
                
            # Update the recent directories menu only if it exists
            if hasattr(self, 'recent_dirs_menu'):
                self.update_recent_directories_menu()
            else:
                print("Recent directories menu not yet created, skipping menu update")
            
            # Save recent directories to file
            self.save_settings()
            
            # Verify recent directories were updated
            print(f"Recent directories after update: {self.recent_directories}")
            
        except Exception as e:
            print(f"Error adding to recent directories: {e}")
            traceback.print_exc()

    def open_csv_file(self):
        """Open a CSV file chooser dialog and load the selected file"""
        print("\n=== Open CSV file called ===")  # Debug print
        file_path = filedialog.askopenfilename(
            initialdir=self.current_directory,
            title="Select CSV file",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )
        if file_path:
            print(f"Selected CSV file: {file_path}")  # Debug print
            # Update current directory to the directory of the selected file
            self.current_directory = os.path.dirname(file_path)
            
            # Load the selected CSV file
            self.load_csv_file(file_path)

    def move_searched_column_to_start(self):
        """Move the last searched column to the start of the dataframe"""
        try:
            if not hasattr(self, 'last_searched_column') or not self.last_searched_column:
                print("No column was searched")
                return
                
            if not hasattr(self, 'original_csv_df') or self.original_csv_df is None:
                print("No CSV file loaded")
                return
                
            column = self.last_searched_column
            
            # Check if the column exists in the dataframe
            if column not in self.original_csv_df.columns:
                print(f"Column '{column}' not found in dataframe")
                return
                
            print(f"\n=== Moving column '{column}' to start ===")
            
            # Get all columns and move the specified one to the start
            cols = list(self.original_csv_df.columns)
            if column in cols:
                cols.remove(column)
                cols.insert(0, column)
                
                # Reorder the dataframe columns
                self.original_csv_df = self.original_csv_df[cols]
                
                # If we have a filtered dataframe, reorder that too
                if hasattr(self, 'filtered_csv_df') and self.filtered_csv_df is not None:
                    # Only reorder if the column exists in the filtered dataframe
                    if column in self.filtered_csv_df.columns:
                        filtered_cols = list(self.filtered_csv_df.columns)
                        filtered_cols.remove(column)
                        filtered_cols.insert(0, column)
                        self.filtered_csv_df = self.filtered_csv_df[filtered_cols]
                
                # Update the displayed dataframe
                self._update_csv_display()
                
                # Highlight the column
                self.highlight_column(column)
        except Exception as e:
            print(f"Error in move_searched_column_to_start: {e}")
            traceback.print_exc()
    
    def _update_csv_display(self):
        """Update the CSV display with the current dataframe"""
        if hasattr(self, 'csv_table') and hasattr(self.csv_table, 'model'):
            self.csv_table.model.df = self.original_csv_df
            self.csv_table.redraw()
    
    def highlight_column(self, column):
        """Highlight a column in the CSV table"""
        if hasattr(self, 'csv_table') and hasattr(self.csv_table, 'columncolors'):
            self.csv_table.columncolors[column] = '#C6F4D6'  # Light green
            self.csv_table.redraw()
    
    def _apply_column_filter_to_filtered_data(self):
        """Apply the stored column filter to the row-filtered data"""
        # Check if we have valid data to work with
        if not hasattr(self, 'filtered_csv_df') or self.filtered_csv_df is None or not hasattr(self, 'visible_columns') or not self.visible_columns:
            print("No filtered data or visible columns to apply filter to")
            return
            
        try:
            print(f"DEBUG: _apply_column_filter_to_filtered_data - Current file: {getattr(self, 'current_csv_file', 'None')}")
            print(f"DEBUG: _apply_column_filter_to_filtered_data - Filtered DataFrame index type: {type(self.filtered_csv_df.index)}")
            print(f"DEBUG: _apply_column_filter_to_filtered_data - Filtered DataFrame index name: {self.filtered_csv_df.index.name}")
            
            # Verify the filtered data matches the current file's data structure
            if not hasattr(self, 'original_csv_df') or self.original_csv_df is None:
                print("Warning: No original CSV data available to verify filtered data against")
                return
                
            # Get valid columns that exist in both visible_columns and the filtered dataframe
            valid_columns = [col for col in self.visible_columns if col in self.filtered_csv_df.columns]
            
            if not valid_columns:
                print("No valid columns for this file, showing all columns")
                filtered_df = self.filtered_csv_df.copy()
            else:
                # Apply column filter using .loc to ensure index preservation
                try:
                    filtered_df = self.filtered_csv_df.loc[:, valid_columns].copy()
                    print(f"DEBUG: _apply_column_filter_to_filtered_data - After column filter - DataFrame shape: {filtered_df.shape}")
                    print(f"DEBUG: _apply_column_filter_to_filtered_data - After column filter - Index type: {type(filtered_df.index)}")
                    print(f"DEBUG: _apply_column_filter_to_filtered_data - After column filter - Index name: {filtered_df.index.name}")
                except Exception as e:
                    print(f"Error applying column filter: {e}")
                    traceback.print_exc()
                    return
            
            # Update the table model with the filtered dataframe
            try:
                self.csv_table.model.df = filtered_df
                self.csv_table.redraw()
                
                print(f"DEBUG: _apply_column_filter_to_filtered_data - After redraw - DataFrame index type: {type(self.csv_table.model.df.index)}")
                print(f"DEBUG: _apply_column_filter_to_filtered_data - After redraw - DataFrame index name: {self.csv_table.model.df.index.name}")
                print(f"DEBUG: _apply_column_filter_to_filtered_data - After redraw - DataFrame index sample: {self.csv_table.model.df.index[:5] if len(self.csv_table.model.df) > 0 else 'Empty DataFrame'}")
                
                # Check if index was reset and restore it if needed
                if hasattr(self, 'filtered_csv_df') and not self.csv_table.model.df.index.equals(filtered_df.index):
                    print("Warning: Index was reset during redraw, restoring...")
                    self.csv_table.model.df.index = filtered_df.index.copy()
                    print(f"DEBUG: _apply_column_filter_to_filtered_data - After index restoration - DataFrame index type: {type(self.csv_table.model.df.index)}")
                    print(f"DEBUG: _apply_column_filter_to_filtered_data - After index restoration - DataFrame index name: {self.csv_table.model.df.index.name}")
                
                # Preserve the index
                self._safe_preserve_index()
                
                # Update status
                row_count = len(self.csv_table.model.df)
                col_count = len(self.csv_table.model.df.columns)
                self.status_var.set(f"Showing {row_count} rows × {col_count} columns")
                
                # Adjust column widths to fit content
                self.adjust_column_widths()
                
            except Exception as e:
                print(f"Error updating table with filtered data: {e}")
                traceback.print_exc()
                
        except Exception as e:
            import traceback
            error_msg = f"Error in _apply_column_filter_to_filtered_data: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.status_var.set(f"Error: {str(e)}")
            # Restore original data on error
            if hasattr(self, 'filtered_csv_df') and self.filtered_csv_df is not None:
                try:
                    self.csv_table.model.df = self.filtered_csv_df
                    self.csv_table.redraw()
                except Exception as restore_error:
                    print(f"Error restoring filtered data: {restore_error}")
                    self.csv_table.redraw()
                traceback.print_exc()
    
    def filter_columns(self, *args):
        """
        Filter the CSV table to show only columns matching the filter text.
        
        Features:
        - Multiple column names can be specified using comma, space, or semicolon as separators
        - By default, performs partial matching (case-insensitive)
        - Use quotes for exact matches (e.g., "Date" matches only "Date" column, not "Update Date")
        - Use ! prefix to exclude matching columns (e.g., !temp to exclude columns containing 'temp')
        - Use "*" to include all remaining columns not explicitly specified
        - The filter persists when switching files
        
        Examples:
        - `date, time` - Shows columns containing "date" or "time"
        - `"Date", "Time"` - Shows only columns exactly named "Date" or "Time"
        - `"Date", temp` - Shows column exactly named "Date" and any columns containing "temp"
        - `!temp` - Exclude all columns containing 'temp'
        - `!"Date", *` - Show all columns except those exactly named "Date"
        - `"*"` - Shows all columns (resets filter)
        - `"Date", *, "Time"` - Shows "Date" and "Time" columns first, then all others
        """
        print("\n=== Column filter called ===")
        
        if hasattr(self, 'csv_table') and self.original_csv_df is not None:
            try:
                # Store the current index for preservation
                current_index = None
                if hasattr(self.csv_table, 'model') and hasattr(self.csv_table.model, 'df'):
                    current_index = self.csv_table.model.df.index.copy()
                    print(f"Stored current index with {len(current_index)} rows for preservation")
                
                filter_text = self.column_filter_var.get().strip()
                print(f"Column filter text: '{filter_text}'")
                
                # If filter text is empty, show all columns
                if not filter_text:
                    self.reset_column_filter()
                    return
                
                # Split filter text by comma, space, or semicolon
                filter_terms = [term.strip() for term in filter_text.replace(',', ' ').replace(';', ' ').split()]
                filter_terms = [term for term in filter_terms if term]  # Remove empty terms
                
                if not filter_terms:
                    self.reset_column_filter()
                    return
                
                print(f"Column filter terms: {filter_terms}")
                
                # Get all column names
                all_columns = self.original_csv_df.columns.tolist()
                
                # Check if wildcard is present
                include_remaining = "*" in filter_terms
                if include_remaining:
                    filter_terms.remove("*")
                    print("Wildcard '*' found - will include all remaining columns")
                
                # Find matching columns (supporting exact matches with quoted strings and exclusions)
                include_columns = []
                exclude_columns = set()
                
                for term in filter_terms:
                    term = term.strip()
                    if not term:
                        continue
                        
                    # Check for exclusion term (starts with !)
                    exclude = term.startswith('!')
                    if exclude:
                        term = term[1:].strip()  # Remove the !
                        if not term:  # Skip if term was just "!"
                            continue
                    
                    # Check if term is wrapped in quotes
                    exact_match = False
                    if (term.startswith('"') and term.endswith('"')) or (term.startswith("'") and term.endswith("'")):
                        exact_match = True
                        term = term[1:-1]  # Remove the quotes
                        if not term:  # Skip empty quoted terms
                            continue
                    
                    # Process the term for all columns
                    for col in all_columns:
                        col_lower = col.lower()
                        term_lower = term.lower()
                        
                        # Determine if this column matches the term
                        matches = (term_lower == col_lower) if exact_match else (term_lower in col_lower)
                        
                        if matches:
                            if exclude:
                                exclude_columns.add(col)
                            elif col not in include_columns:
                                include_columns.append(col)
                            
                # If wildcard is present, include all remaining columns that aren't excluded
                if include_remaining:
                    remaining_columns = [col for col in all_columns 
                                       if col not in include_columns 
                                       and col not in exclude_columns]
                    include_columns.extend(remaining_columns)
                    print(f"Added {len(remaining_columns)} remaining columns due to wildcard")
                
                # Apply exclusions
                matching_columns = [col for col in include_columns if col not in exclude_columns]
                
                if exclude_columns:
                    print(f"Excluded columns: {', '.join(sorted(exclude_columns))}")
                
                if not matching_columns and not include_remaining:
                    print("Warning: No columns match the filter criteria")

                if matching_columns:
                    # Store the visible columns for persistence
                    self.visible_columns = matching_columns
                    
                    # Apply the column filter
                    if hasattr(self, 'filtered_csv_df') and self.filtered_csv_df is not None:
                        self._apply_column_filter_to_filtered_data()
                    else:
                        self._apply_column_filter()
                else:
                    # No matches found, silently ignore and keep current view
                    print("No matching columns found, keeping current view")
                    return
                
                # Column filtering doesn't change rows, so index should be preserved automatically
                # Only restore if the index values actually match (more robust check)
                if current_index is not None:
                    current_df = self.csv_table.model.df
                    if len(current_df) == len(current_index):
                        # Verify the indices are actually compatible before restoring
                        if set(current_df.index) == set(current_index):
                            try:
                                current_df.index = current_index
                                print(f"Restored index with {len(current_index)} rows after filtering")
                            except ValueError as e:
                                print(f"Warning: Could not restore index - {e}")
                        else:
                            print("Index values don't match, skipping restoration to avoid misalignment")
                    else:
                        print(f"Warning: Cannot restore index - length mismatch. DataFrame: {len(current_df)}, Index: {len(current_index)}")
                
                # Preserve the index
                self._safe_preserve_index()

            except Exception as e:
                print(f"Error in filter_columns: {e}")
                traceback.print_exc()

    def _safe_preserve_index(self):
        """
        Safely preserve the index after operations that might reset it,
        handling the case where the index name is already a column
        """
        if hasattr(self, 'csv_table') and hasattr(self.csv_table, 'model') and hasattr(self.csv_table.model, 'df'):
            try:
                # Get the current DataFrame
                df = self.csv_table.model.df
                
                print(f"DEBUG: _safe_preserve_index - Starting - DataFrame index type: {type(df.index)}")
                print(f"DEBUG: _safe_preserve_index - Starting - DataFrame index name: {df.index.name}")
                print(f"DEBUG: _safe_preserve_index - Starting - DataFrame index sample: {df.index[:5]}")
                
                # Store the current index
                current_index = df.index.copy()
                index_name = df.index.name
                
                # Check if the index name is already a column
                if index_name is not None and index_name in df.columns:
                    print(f"Index column '{index_name}' already exists in DataFrame")
                    
                    # Create a temporary name for the index
                    temp_name = f"{index_name}_index_temp"
                    while temp_name in df.columns:
                        temp_name = f"{temp_name}_temp"
                    
                    # Rename the index
                    df.index.name = temp_name
                
                # Force the table to show the index
                self.csv_table.showindex = True
                print(f"DEBUG: _safe_preserve_index - After setting showindex - Table showindex: {self.csv_table.showindex}")
                
                # Force a redraw of the row header
                if hasattr(self.csv_table, 'rowheader'):
                    self.csv_table.rowheader.redraw()
                    
                # Make sure the index is visible
                try:
                    self.csv_table.showIndex()
                    print(f"DEBUG: _safe_preserve_index - After showIndex() - DataFrame index type: {type(df.index)}")
                    print(f"DEBUG: _safe_preserve_index - After showIndex() - DataFrame index name: {df.index.name}")
                    print(f"DEBUG: _safe_preserve_index - After showIndex() - DataFrame index sample: {df.index[:5]}")
                except Exception as e:
                    print(f"Warning: Error showing index: {e}")
                    
                    # Try a more direct approach - reset and restore the index
                    try:
                        # Create a temporary column with the index values
                        temp_col = "__temp_index__"
                        while temp_col in df.columns:
                            temp_col = f"{temp_col}_temp"
                        
                        print(f"DEBUG: _safe_preserve_index - Using direct approach with temp column: {temp_col}")
                        
                        # Store index values in a temporary column
                        df[temp_col] = current_index
                        
                        # Reset the index (this will create a new default numeric index)
                        df.reset_index(drop=True, inplace=True)
                        
                        # Set the index back to the stored values
                        df.set_index(temp_col, inplace=True)
                        
                        # Rename the index back to its original name
                        if index_name is not None:
                            df.index.name = index_name
                        
                        # Remove the temporary column if it still exists
                        if temp_col in df.columns:
                            df.drop(columns=[temp_col], inplace=True)
                        
                        print(f"DEBUG: _safe_preserve_index - After direct approach - DataFrame index type: {type(df.index)}")
                        print(f"DEBUG: _safe_preserve_index - After direct approach - DataFrame index name: {df.index.name}")
                        print(f"DEBUG: _safe_preserve_index - After direct approach - DataFrame index sample: {df.index[:5]}")
                        
                        # Force a redraw
                        self.csv_table.redraw()
                    except Exception as e2:
                        print(f"Failed to restore index: {e2}")
                        
            except Exception as e:
                print(f"Warning: Error in _safe_preserve_index: {e}")

    def _safe_draw_selected_columns(self):
        """Validate and render the currently selected plot columns safely"""
        if not hasattr(self, 'csv_table'):
            return False

        table = self.csv_table
        if not hasattr(table, 'multiplecollist') or not table.multiplecollist:
            return False

        df = getattr(getattr(table, 'model', None), 'df', None)
        if df is None:
            print("Warning: No DataFrame available to highlight selected columns")
            return False

        total_cols = len(df.columns)
        if total_cols == 0:
            print("Warning: No columns available to highlight")
            table.multiplecollist = []
            return False

        valid_cols = []
        for col_idx in table.multiplecollist:
            try:
                idx = int(col_idx)
            except (TypeError, ValueError):
                continue
            if 0 <= idx < total_cols:
                valid_cols.append(idx)

        if not valid_cols:
            print("Warning: Selected plot columns are no longer available; clearing selection")
            table.multiplecollist = []
            return False

        if valid_cols != table.multiplecollist:
            print("DEBUG: _safe_draw_selected_columns - Filtered invalid column indices")
            table.multiplecollist = valid_cols

        if hasattr(table, 'drawSelectedCol'):
            try:
                table.drawSelectedCol()
                return True
            except Exception as e:
                print(f"Warning: Failed to draw selected columns safely: {e}")

        return False

    def _preserve_index(self):
        """Ensure the index is preserved after operations that might reset it"""
        if hasattr(self, 'csv_table') and hasattr(self.csv_table, 'model') and hasattr(self.csv_table.model, 'df'):
            # Store the current index name
            index_name = self.csv_table.model.df.index.name
            
            # Make sure the index is visible
            self.csv_table.showIndex()
            
            # Restore the index name if it was lost
            if index_name is not None and self.csv_table.model.df.index.name is None:
                self.csv_table.model.df.index.name = index_name

    def _apply_column_filter(self):
        """Apply the stored column filter to the current CSV data"""
        if self.original_csv_df is not None and self.visible_columns:
            try:
                print(f"DEBUG: _apply_column_filter - Original DataFrame index type: {type(self.original_csv_df.index)}")
                print(f"DEBUG: _apply_column_filter - Original DataFrame index name: {self.original_csv_df.index.name}")
                print(f"DEBUG: _apply_column_filter - Original DataFrame index sample: {self.original_csv_df.index[:5]}")
                
                # Get valid columns (in case we switched to a file with different columns)
                valid_columns = [col for col in self.visible_columns if col in self.original_csv_df.columns]
                
                if not valid_columns:
                    print("No valid columns for this file, showing all columns")
                    filtered_df = self.original_csv_df.copy()
                else:
                    # Apply column filter
                    # Use .loc to ensure the index is preserved
                    filtered_df = self.original_csv_df.loc[:, valid_columns].copy()
                    print(f"DEBUG: _apply_column_filter - Filtered DataFrame index type: {type(filtered_df.index)}")
                    print(f"DEBUG: _apply_column_filter - Filtered DataFrame index name: {filtered_df.index.name}")
                    print(f"DEBUG: _apply_column_filter - Filtered DataFrame index sample: {filtered_df.index[:5]}")
                
                self.csv_table.model.df = filtered_df
                
                # Redraw the table
                self.csv_table.redraw()
                
                print(f"DEBUG: _apply_column_filter - After redraw - DataFrame index type: {type(self.csv_table.model.df.index)}")
                print(f"DEBUG: _apply_column_filter - After redraw - DataFrame index name: {self.csv_table.model.df.index.name}")
                print(f"DEBUG: _apply_column_filter - After redraw - DataFrame index sample: {self.csv_table.model.df.index[:5]}")
                
                # Check if index was reset and restore it if needed
                if not self.csv_table.model.df.index.equals(filtered_df.index):
                    print("Warning: Index was reset during redraw, restoring...")
                    self.csv_table.model.df.index = filtered_df.index.copy()
                    print(f"DEBUG: _apply_column_filter - After index restoration - DataFrame index type: {type(self.csv_table.model.df.index)}")
                    print(f"DEBUG: _apply_column_filter - After index restoration - DataFrame index name: {self.csv_table.model.df.index.name}")
                    print(f"DEBUG: _apply_column_filter - After index restoration - DataFrame index sample: {self.csv_table.model.df.index[:5]}")
                
                # Preserve the index
                self._safe_preserve_index()
                
                # Adjust column widths to fit content
                self.adjust_column_widths()
                
            except Exception as e:
                print(f"Error applying column filter: {e}")
                traceback.print_exc()

    def adjust_column_widths(self):
        """Adjust column widths to fit content"""
        if hasattr(self, 'csv_table') and self.csv_table.model.df is not None:
            try:
                # Get the current dataframe
                df = self.csv_table.model.df
                
                if df.empty:
                    return
                
                # Iterate over columns and adjust widths
                for col in df.columns:
                    # Get column name length
                    col_name_length = len(str(col))
                    
                    # Sample data to determine maximum width needed
                    # Use head and tail to avoid processing the entire dataset for large files
                    sample_data = pd.concat([df[col].head(20), df[col].tail(20)])
                    
                    # Convert to string and get max length
                    try:
                        max_data_length = sample_data.astype(str).str.len().max()
                    except:
                        # Fallback if conversion fails
                        max_data_length = max([len(str(x)) for x in sample_data if x is not None and pd.notna(x)] or [0])
                    
                    # Use the maximum of column name length and data length
                    max_length = max(col_name_length, max_data_length)
                    
                    # Calculate pixel width (approximately 8 pixels per character)
                    # Set minimum width of 50 pixels and maximum of 300 pixels
                    pixel_width = max(min(max_length * 8, 300), 50)
                    
                    # Set the column width
                    self.csv_table.columnwidths[col] = pixel_width
                
                # Apply the new column widths
                self.csv_table.redraw()
                
                print("Column widths adjusted to fit content")
                
            except Exception as e:
                print(f"Error adjusting column widths: {e}")
                traceback.print_exc()
    
    def reset_column_filter(self):
        """Reset the column filter to show all columns"""
        # Guard against recursive calls (setting column_filter_var triggers filter_columns)
        if getattr(self, '_resetting_column_filter', False):
            return
        self._resetting_column_filter = True
        try:
            self.visible_columns = None
            
            if hasattr(self, 'csv_table') and self.original_csv_df is not None:
                # Reset to original data (but keep any row filters)
                current_filter = self.csv_filter_text.get().strip()
                
                # Apply the current row filter to the full dataset
                if current_filter:
                    self.row_filter()
                else:
                    self.csv_table.model.df = self.original_csv_df.copy()
                    self.csv_table.redraw()
                
                print("Column filter reset, showing all columns")
            
            # Clear the filter text
            self.column_filter_var.set("")
            
        except Exception as e:
            print(f"Error resetting column filter: {e}")
            traceback.print_exc()
        finally:
            self._resetting_column_filter = False

    def setup_column_filter_context_menu(self):
        """Create a context menu for column filter with instructions and examples"""
        try:
            if hasattr(self, 'column_filter_entry'):
                # Create right-click context menu
                self.column_filter_menu = tk.Menu(self.column_filter_entry, tearoff=0)
                
                # Title
                self.column_filter_menu.add_command(
                    label="Column Filter Instructions", 
                    state='disabled', 
                    font=('Arial', 10, 'bold')
                )
                self.column_filter_menu.add_separator()
                
                # Basic Instructions
                self.column_filter_menu.add_command(
                    label="• Enter column names separated by spaces, commas, or semicolons", 
                    state='disabled'
                )
                self.column_filter_menu.add_command(
                    label="• Use quotes for exact matches (e.g., \"Date\" matches only \"Date\")", 
                    state='disabled'
                )
                self.column_filter_menu.add_command(
                    label="• Without quotes, matches any column containing the text", 
                    state='disabled'
                )
                self.column_filter_menu.add_command(
                    label="• Use ! to exclude columns (e.g., !temp or !\"exact\")", 
                    state='disabled'
                )
                self.column_filter_menu.add_command(
                    label="• Use * to include all other non-excluded columns", 
                    state='disabled'
                )
                self.column_filter_menu.add_command(
                    label="• Filter persists when switching files", 
                    state='disabled'
                )
                self.column_filter_menu.add_command(
                    label="• Leave empty to show all columns", 
                    state='disabled'
                )
                
                self.column_filter_menu.add_separator()
                
                # Examples Section
                self.column_filter_menu.add_command(
                    label="Examples:", 
                    state='disabled', 
                    font=('Arial', 10, 'bold')
                )
                self.column_filter_menu.add_command(
                    label="  date price: Shows columns containing 'date' or 'price'", 
                    state='disabled'
                )
                self.column_filter_menu.add_command(
                    label="  \"Date\" \"Time\": Shows only columns exactly named 'Date' or 'Time'", 
                    state='disabled'
                )
                self.column_filter_menu.add_command(
                    label="  !temp: Exclude all columns containing 'temp'", 
                    state='disabled'
                )
                self.column_filter_menu.add_command(
                    label="  !\"Date\", *: Show all except columns exactly named 'Date'", 
                    state='disabled'
                )
                self.column_filter_menu.add_command(
                    label="  \"Date\", *, \"Time\": Show 'Date' and 'Time' columns first, then others", 
                    state='disabled'
                )
                self.column_filter_menu.add_command(
                    label="  open,high,low,close: Show columns with any of these terms", 
                    state='disabled'
                )
                
                # Bind right-click to show menu
                self.column_filter_entry.bind('<Button-3>', self.show_column_filter_menu)
                
        except Exception as e:
            print(f"Error setting up column filter context menu: {e}")
            traceback.print_exc()
    
    def show_column_filter_menu(self, event):
        """Display the context menu for column filter"""
        try:
            if hasattr(self, 'column_filter_menu'):
                self.column_filter_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            print(f"Error showing column filter menu: {e}")
            traceback.print_exc()

    def save_to_filtered_csv(self):
        """Save the currently filtered CSV data to a new CSV file"""
        try:
            # Check if we have data to save
            if not hasattr(self, 'csv_table') or not hasattr(self.csv_table, 'model') or self.csv_table.model.df is None:
                messagebox.showinfo("No Data", "No CSV data available to save.")
                return
                
            # Get the current dataframe (filtered or not)
            current_df = self.csv_table.model.df
            
            if current_df.empty:
                messagebox.showerror("Empty Data", "The current data is empty and cannot be saved.")
                return
            
            # Generate filename based on original file
            if not hasattr(self, 'current_csv_file') or not self.current_csv_file:
                messagebox.showinfo("No Source File", "Cannot determine source file to create filtered filename.")
                return
                
            # Get the directory and filename from the current file
            file_dir = os.path.dirname(self.current_csv_file)
            if not os.path.exists(file_dir):
                file_dir = self.current_directory
            
            # Get the filename without extension
            base_filename = os.path.basename(self.current_csv_file)
            filename_no_ext, ext = os.path.splitext(base_filename)
            
            # Create new filename with "_filtered" suffix
            new_filename = f"{filename_no_ext}_filtered{ext}"
            file_path = os.path.join(file_dir, new_filename)
            
            # Check if file already exists and create a unique name if needed
            counter = 1
            original_path = file_path
            while os.path.exists(file_path):
                file_path = os.path.join(file_dir, f"{filename_no_ext}_filtered_{counter}{ext}")
                counter += 1
                
            # Save the dataframe to CSV
            try:
                current_df.to_csv(file_path, index=False)
                print(f"Successfully saved filtered data to: {file_path}")
                messagebox.showinfo("Save Successful", f"Data saved to:\n{file_path}")
                
                # Refresh the file list to show the new file
                self.refresh_file_list()
                
            except Exception as save_error:
                print(f"Error saving CSV: {save_error}")
                messagebox.showerror("Save Error", f"Failed to save CSV file:\n{str(save_error)}")
                
        except Exception as e:
            print(f"Error in save_to_filtered_csv: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"An error occurred while saving:\n{str(e)}")

    def _advanced_file_read(self, file_path):
        """Advanced file reading method with comprehensive diagnostics and long path handling"""
        try:
            print(f"\n=== Advanced file read for: {file_path} ===")
            
            # Normalize and handle long paths
            normalized_path = self.normalize_long_path(file_path)
            
            # Try to read the file with various encodings
            encodings = ['utf-8', 'latin1', 'ISO-8859-1', 'cp1252', 'utf-16']
            
            # Try different reading methods
            for encoding in encodings:
                try:
                    print(f"Attempting to read with encoding: {encoding}")
                    df = pd.read_csv(normalized_path, encoding=encoding)
                    if df is not None and not df.empty:
                        print(f"Successfully read with encoding: {encoding}")
                        return df
                except Exception as e:
                    print(f"Reading with {encoding} failed: {e}")
            
            # Try with Python engine and error handling
            try:
                print("Attempting to read with Python engine and error handling")
                df = pd.read_csv(normalized_path, encoding='utf-8', engine='python', on_bad_lines='skip')
                if df is not None and not df.empty:
                    print("Successfully read with Python engine")
                    return df
            except Exception as e:
                print(f"Reading with Python engine failed: {e}")
            
            # Last resort: try to read as text and parse manually
            print("All standard reading methods failed, attempting manual parsing")
            return None
            
        except Exception as e:
            print(f"Advanced file read failed: {e}")
            traceback.print_exc()
            return None

    def _manual_csv_parse(self, file_path, encoding):
        """Manual CSV parsing with error handling"""
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                lines = f.readlines()
            
            # Remove problematic lines
            clean_lines = [line for line in lines if len(line.split(',')) > 1]
            
            # Create a DataFrame from the clean lines
            df = pd.DataFrame([line.strip().split(',') for line in clean_lines])
            
            # Try to convert columns to numeric types
            df = df.apply(pd.to_numeric, errors='coerce')
            
            return df
        
        except Exception as e:
            print(f"Error in manual CSV parsing: {e}")
            return None

    def reveal_in_explorer(self):
        """Reveal the selected file(s) in File Explorer"""
        selected_rows = self.table.multiplerowlist
        if not selected_rows:
            messagebox.showinfo("Info", "Please select a file to reveal in Explorer")
            return
    
        try:
            # Get the filtered/displayed DataFrame
            displayed_df = self.table.model.df
            
            for row in selected_rows:
                if row < len(displayed_df):
                    file_path = displayed_df.iloc[row]['File_Path']
                    
                    # Normalize the path to handle potential issues
                    file_path = os.path.normpath(file_path)
                    
                    # Ensure the file path exists
                    if not os.path.exists(file_path):
                        messagebox.showerror("Error", f"File not found: {file_path}")
                        continue
                    
                    # Use Windows-specific command to open and select file
                    subprocess.Popen(f'explorer /select,"{file_path}"', shell=True)
    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reveal file in Explorer:\n{str(e)}")

    def save_current_filter(self):
        """Save the current filter configuration"""
        try:
            # Get the current filter settings
            row_filter = self.csv_filter_text.get().strip()
            column_filter = self.column_filter_var.get().strip()
            
            # Skip if both filters are empty
            if not row_filter and not column_filter:
                messagebox.showinfo("Empty Filter", "No filter is currently active")
                return
            
            # Ask for a name for this filter configuration
            filter_name = simpledialog.askstring("Save Filter", "Enter a name for this filter:")
            if not filter_name:
                return  # User canceled
            
            # Create a filter configuration dictionary
            filter_config = {
                "name": filter_name,
                "row_filter": row_filter,
                "column_filter": column_filter
            }
            
            # Check if a filter with this name already exists
            for i, saved_filter in enumerate(self.saved_filters):
                if saved_filter.get("name") == filter_name:
                    # Ask if user wants to overwrite
                    if messagebox.askyesno("Filter Exists", f"A filter named '{filter_name}' already exists. Overwrite?"):
                        self.saved_filters[i] = filter_config
                        messagebox.showinfo("Filter Saved", f"Filter '{filter_name}' updated")
                    return
            
            # Add the new filter to the list
            self.saved_filters.append(filter_config)
            
            # Save settings to file
            self.save_settings()
            
            # Show a confirmation message
            messagebox.showinfo("Filter Saved", f"Filter '{filter_name}' saved")
            
        except Exception as e:
            print(f"Error saving filter: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to save filter:\n{str(e)}")
            
    def show_saved_filters(self):
        """Show the saved filters and allow the user to select one"""
        try:
            # Check if there are any saved filters
            if not self.saved_filters:
                messagebox.showinfo("No Saved Filters", "You don't have any saved filters yet")
                return
                
            # Create a dialog to show the saved filters
            dialog = tk.Toplevel(self)
            dialog.title("Saved Filters")
            dialog.geometry("500x300")
            
            # Make dialog modal
            dialog.transient(self)
            dialog.grab_set()
            
            # Create a frame for the listbox and scrollbar
            list_frame = ttk.Frame(dialog)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Add a scrollbar
            scrollbar = ttk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Create listbox with scrollbar
            filter_listbox = tk.Listbox(list_frame, width=50, height=10, yscrollcommand=scrollbar.set)
            filter_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=filter_listbox.yview)
            
            # Add column headers
            filter_listbox.insert(tk.END, "Name | Row Filter | Column Filter")
            filter_listbox.insert(tk.END, "-" * 60)
            
            # Add saved filters to the listbox
            for filter_config in self.saved_filters:
                filter_name = filter_config.get("name", "Unnamed")
                row_filter = filter_config.get("row_filter", "")
                column_filter = filter_config.get("column_filter", "")
                
                # Format the display string
                display_text = f"{filter_name} | {row_filter} | {column_filter}"
                filter_listbox.insert(tk.END, display_text)
            
            # Select the first item
            if len(self.saved_filters) > 0:
                filter_listbox.selection_set(2)  # Skip the headers
            
            def on_apply():
                # Get the selected filter
                selected_index = filter_listbox.curselection()
                if not selected_index or selected_index[0] < 2:  # Skip headers
                    messagebox.showinfo("No Selection", "Please select a filter to apply")
                    return
                    
                # Get the selected filter configuration
                filter_config = self.saved_filters[selected_index[0] - 2]  # Adjust for headers
                self.apply_saved_filter(filter_config)
                dialog.destroy()
            
            def on_delete():
                # Get the selected filter
                selected_index = filter_listbox.curselection()
                if not selected_index or selected_index[0] < 2:  # Skip headers
                    messagebox.showinfo("No Selection", "Please select a filter to delete")
                    return
                    
                # Confirm deletion
                filter_name = self.saved_filters[selected_index[0] - 2].get("name", "Unnamed")
                if messagebox.askyesno("Confirm Delete", f"Delete filter '{filter_name}'?"):
                    # Delete the filter
                    del self.saved_filters[selected_index[0] - 2]  # Adjust for headers
                    
                    # Save settings to file
                    self.save_settings()
                    
                    # Refresh the listbox
                    filter_listbox.delete(0, tk.END)
                    filter_listbox.insert(tk.END, "Name | Row Filter | Column Filter")
                    filter_listbox.insert(tk.END, "-" * 60)
                    
                    for filter_config in self.saved_filters:
                        filter_name = filter_config.get("name", "Unnamed")
                        row_filter = filter_config.get("row_filter", "")
                        column_filter = filter_config.get("column_filter", "")
                        display_text = f"{filter_name} | {row_filter} | {column_filter}"
                        filter_listbox.insert(tk.END, display_text)
            
            def on_cancel():
                dialog.destroy()
            
            # Add buttons
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=10)
            ttk.Button(button_frame, text="Apply", command=on_apply).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Delete", command=on_delete).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
            
            # Center the dialog on the screen
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f'{width}x{height}+{x}+{y}')

        except Exception as e:
            print(f"Error showing saved filters: {e}")
            traceback.print_exc()
            
    def reset_all_filters(self):
        """Reset both row and column filters"""
        try:
            # Reset the row filter
            self.csv_filter_text.set("")
            
            # Reset the column filter
            self.reset_column_filter()
            
            # Show a confirmation message
            print("All filters have been reset")
            
        except Exception as e:
            print(f"Error resetting filters: {e}")
            traceback.print_exc()

    def save_file_filter(self):
        """Save the current file filter configuration"""
        try:
            # Get the current file filter
            file_filter = self.filter_text.get().strip()
            
            # Skip if filter is empty
            if not file_filter:
                messagebox.showinfo("Empty Filter", "No file filter is currently active")
                return
            
            # Ask for a name for this filter configuration
            filter_name = simpledialog.askstring("Save File Filter", "Enter a name for this file filter:")
            if not filter_name:
                return  # User canceled
            
            # Create a filter configuration dictionary
            filter_config = {
                "name": filter_name,
                "filter": file_filter
            }
            
            # Check if a filter with this name already exists
            for i, saved_filter in enumerate(self.saved_file_filters):
                if saved_filter.get("name") == filter_name:
                    # Ask if user wants to overwrite
                    if messagebox.askyesno("Filter Exists", f"A file filter named '{filter_name}' already exists. Overwrite?"):
                        self.saved_file_filters[i] = filter_config
                        messagebox.showinfo("Filter Saved", f"File filter '{filter_name}' updated")
                    return
            
            # Add the new filter to the list
            self.saved_file_filters.append(filter_config)
            
            # Save settings to file
            self.save_settings()
            
            # Show a confirmation message
            messagebox.showinfo("Filter Saved", f"File filter '{filter_name}' saved")
            
        except Exception as e:
            print(f"Error saving file filter: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to save file filter:\n{str(e)}")
            
    def show_saved_file_filters(self):
        """Show the saved file filters and allow the user to select one"""
        try:
            # Check if there are any saved filters
            if not self.saved_file_filters:
                messagebox.showinfo("No Saved Filters", "You don't have any saved file filters yet")
                return
                
            # Create a dialog to show the saved filters
            dialog = tk.Toplevel(self)
            dialog.title("Saved File Filters")
            dialog.geometry("500x300")
            
            # Make dialog modal
            dialog.transient(self)
            dialog.grab_set()
            
            # Create a frame for the listbox and scrollbar
            list_frame = ttk.Frame(dialog)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Add a scrollbar
            scrollbar = ttk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Create listbox with scrollbar
            filter_listbox = tk.Listbox(list_frame, width=50, height=10, yscrollcommand=scrollbar.set)
            filter_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=filter_listbox.yview)
            
            # Add column headers
            filter_listbox.insert(tk.END, "Name | Filter")
            filter_listbox.insert(tk.END, "-" * 60)
            
            # Add saved filters to the listbox
            for filter_config in self.saved_file_filters:
                filter_name = filter_config.get("name", "Unnamed")
                file_filter = filter_config.get("filter", "")
                
                # Format the display string
                display_text = f"{filter_name} | {file_filter}"
                filter_listbox.insert(tk.END, display_text)
            
            # Select the first item
            if len(self.saved_file_filters) > 0:
                filter_listbox.selection_set(2)  # Skip the headers
            
            def on_apply():
                # Get the selected filter
                selected_index = filter_listbox.curselection()
                if not selected_index or selected_index[0] < 2:  # Skip headers
                    messagebox.showinfo("No Selection", "Please select a filter to apply")
                    return
                    
                # Get the selected filter configuration
                filter_config = self.saved_file_filters[selected_index[0] - 2]  # Adjust for headers
                self.apply_saved_file_filter(filter_config)
                dialog.destroy()
            
            def on_delete():
                # Get the selected filter
                selected_index = filter_listbox.curselection()
                if not selected_index or selected_index[0] < 2:  # Skip headers
                    messagebox.showinfo("No Selection", "Please select a filter to delete")
                    return
                    
                # Confirm deletion
                filter_name = self.saved_file_filters[selected_index[0] - 2].get("name", "Unnamed")
                if messagebox.askyesno("Confirm Delete", f"Delete file filter '{filter_name}'?"):
                    # Delete the filter
                    del self.saved_file_filters[selected_index[0] - 2]  # Adjust for headers
                    
                    # Save settings to file
                    self.save_settings()
                    
                    # Refresh the listbox
                    filter_listbox.delete(0, tk.END)
                    filter_listbox.insert(tk.END, "Name | Filter")
                    filter_listbox.insert(tk.END, "-" * 60)
                    
                    for filter_config in self.saved_file_filters:
                        filter_name = filter_config.get("name", "Unnamed")
                        file_filter = filter_config.get("filter", "")
                        display_text = f"{filter_name} | {file_filter}"
                        filter_listbox.insert(tk.END, display_text)
            
            def on_cancel():
                dialog.destroy()
            
            # Add buttons
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=10)
            
            ttk.Button(button_frame, text="Apply", command=on_apply).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Delete", command=on_delete).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
            
            # Center the dialog on the screen
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f'{width}x{height}+{x}+{y}')

        except Exception as e:
            print(f"Error showing saved file filters: {e}")
            traceback.print_exc()
            
    def apply_saved_file_filter(self, filter_config):
        """Apply a saved file filter configuration"""
        try:
            # Get the filter setting
            file_filter = filter_config.get("filter", "")
            
            # Apply the file filter
            if file_filter:
                self.filter_text.set(file_filter)
                # Note: filter_files will be called automatically due to the trace
            else:
                # Clear the filter if empty
                self.filter_text.set("")
                
            # Show a confirmation message
            filter_name = filter_config.get("name", "Selected")
            messagebox.showinfo("Filter Applied", f"File filter '{filter_name}' has been applied")
            
        except Exception as e:
            print(f"Error applying saved file filter: {e}")
            traceback.print_exc()
            
    def update_recent_directories_menu(self):
        """Update the recent directories menu with current list of directories"""
        try:
            # First check if the menu attribute exists
            if not hasattr(self, 'recent_dirs_menu'):
                print("Recent directories menu not yet created")
                return
                
            print(f"Updating recent dirs menu")
            
            # Clear existing menu items
            self.recent_dirs_menu.delete(0, tk.END)
            
            # Force update of the menu widget
            self.recent_dirs_menu.update()
            
            # Add each recent directory to the menu
            if self.recent_directories and len(self.recent_directories) > 0:
                for directory in self.recent_directories:
                    # Skip empty or None entries
                    if not directory:
                        continue
                        
                    # Format directory for display (shorten if too long)
                    display_name = directory
                    if len(display_name) > 50:
                        display_name = "..." + display_name[-47:]
                    
                    print(f"Adding menu item: {display_name}")
                    
                    # Use a lambda with a default argument to avoid late binding issues
                    self.recent_dirs_menu.add_command(
                        label=display_name, 
                        command=lambda dir=directory: self.open_recent_directory(dir)
                    )
                    
                    # Add a debug print to verify the command is correctly set
                    print(f"Added menu item for directory: {directory}")
            else:
                # If no recent directories, add a disabled item
                print("No recent directories to add to menu")
                self.recent_dirs_menu.add_command(label="No recent directories", state="disabled")
                
        except Exception as e:
            print(f"Error updating recent directories menu: {e}")
            traceback.print_exc()
            
    def open_recent_directory(self, directory):
        """Open a directory from the recent directories list"""
        try:
            print(f"Opening recent directory: {directory}")
            
            # Check if directory exists
            if not os.path.isdir(directory):
                messagebox.showerror("Directory Not Found", f"The directory no longer exists:\n{directory}")
                # Remove from recent directories
                if directory in self.recent_directories:
                    self.recent_directories.remove(directory)
                    self.update_recent_directories_menu()
                    self.save_settings()  # Save after removing invalid directory
                return
                
            # Set as current directory
            self.current_directory = directory
            
            # Move to top of recent list
            self.add_to_recent_directories(directory)
            
            # Update file list
            self.update_file_list()

            # Update the file dataframe and refresh the browser
            self.update_file_dataframe()
            self.setup_file_browser()
            
            # Update max fields
            old_max = self.max_fields
            self.max_fields = self.get_max_fields()
            print(f"Max fields changed from {old_max} to {self.max_fields}")
            
        except Exception as e:
            print(f"Error opening recent directory: {e}")
            traceback.print_exc()

    def load_settings(self):
        """Load settings from file"""
        try:
            print(f"Attempting to load settings from: {self.settings_file}")
            
            if os.path.exists(self.settings_file):
                print(f"File exists, reading content...")
                with open(self.settings_file, 'r') as f:
                    file_content = f.read()
                    print(f"Raw file content: {file_content}")
                    
                    if file_content.strip():
                        settings = json.loads(file_content)
                        print(f"Loaded settings: {settings}")
                        
                        # Load recent directories
                        self.recent_directories = settings.get("recent_directories", [])
                        print(f"Loaded {len(self.recent_directories)} recent directories")
                        if hasattr(self, 'recent_dirs_menu'):
                            self.update_recent_directories_menu()
                            print("Updated recent directories menu after loading settings")
                        else:
                            print("Recent directories menu not yet created, will update later")
                        # Load saved filters
                        self.saved_filters = settings.get("saved_filters", [])
                        print(f"Loaded {len(self.saved_filters)} saved filters")
                        
                        # Load saved file filters
                        self.saved_file_filters = settings.get("saved_file_filters", [])
                        print(f"Loaded {len(self.saved_file_filters)} saved file filters")
                        
                        # Load plot settings
                        self.saved_plot_settings = settings.get("plot_settings", None)
                        print(f"Loaded plot settings: {self.saved_plot_settings}")
                    else:
                        print("File exists but is empty")
            else:
                print(f"No settings file found at {self.settings_file}")
        except Exception as e:
            print(f"Error loading settings: {e}")
            traceback.print_exc()
            # Initialize with empty lists in case of error
            self.recent_directories = []
            self.saved_filters = []
            self.saved_file_filters = []
            self.saved_plot_settings = None

    def _safe_replot_with_index_preservation(self, pf):
        """
        Safely replot with proper index preservation when column filtering is active
        """
        try:
            # Validate input
            if pf is None:
                print("Warning: Cannot replot - plot viewer is None")
                return False
                
            # Check if we have a saved index column that should be set
            if hasattr(self, 'saved_table_settings') and self.saved_table_settings is not None:
                if 'index_column' in self.saved_table_settings and self.saved_table_settings['index_column'] is not None:
                    saved_index_column = self.saved_table_settings['index_column']
                    
                    # Check if this column exists in the current DataFrame
                    df = self.csv_table.model.df
                    if saved_index_column in df.columns:
                        print(f"Setting {saved_index_column} as index column before replot")
                        # Get the column index
                        col_idx = list(df.columns).index(saved_index_column)
                        # Set the index using pandastable's method
                        self.csv_table.model.setindex([col_idx])
                        # Make sure the index is shown
                        self.csv_table.showIndex()
                    else:
                        print(f"Index column {saved_index_column} not found, using first column for plotting")
                        # Set useindex to False in plot options
                        if hasattr(pf, 'mplopts') and hasattr(pf.mplopts, 'kwds'):
                            pf.mplopts.kwds['useindex'] = False
                            if hasattr(pf.mplopts, 'useindexvar'):
                                pf.mplopts.useindexvar.set(0)
                            
            # Check if we have column filtering active
            has_column_filter = hasattr(self, 'visible_columns') and self.visible_columns is not None
            
            if has_column_filter:
                # When column filtering is active, ensure the index is preserved
                try:
                    # First, ensure the index is properly preserved
                    self._safe_preserve_index()
                    
                    # Make sure the selected columns are valid for the current DataFrame
                    if hasattr(self.csv_table, 'multiplecollist') and self.csv_table.multiplecollist:
                        # Get the current DataFrame
                        df = self.csv_table.model.df
                        
                        # Verify that all selected columns exist in the filtered DataFrame
                        valid_cols = []
                        for col_idx in self.csv_table.multiplecollist:
                            if col_idx < len(df.columns):
                                valid_cols.append(col_idx)
                        
                        # Update the selected columns list
                        if valid_cols:
                            self.csv_table.multiplecollist = valid_cols
                            self.csv_table.drawSelectedCol()
                        else:
                            print("Warning: No valid columns selected for plotting")
                            return False
                    
                    # Ensure the index is properly preserved
                    try:
                        # Force the table to show the index
                        self.csv_table.showindex = True
                        if hasattr(self.csv_table, 'rowheader'):
                            self.csv_table.rowheader.redraw()
                        
                        # Make sure the index is visible
                        try:
                            self.csv_table.showIndex()
                        except Exception as e:
                            print(f"Warning: Error showing index before replot: {e}")
                    except Exception as e:
                        print(f"Warning: Error preserving index before replot: {e}")
                    
                    # Now try to replot with the validated columns and preserved index
                    try:
                        # Try the standard replot first
                        pf.replot()
                    except Exception as e:
                        print(f"Standard replot failed, trying alternative approach: {e}")
                        # If that fails, try a more direct approach
                        try:
                            pf.plotCurrent()
                        except Exception as e2:
                            print(f"Alternative replot also failed: {e2}")
                            return False
                    
                    return True
                except Exception as e:
                    print(f"Warning: Error during safe replot with column filter: {e}")
                    traceback.print_exc()
                    
                    # Try an even safer fallback approach
                    try:
                        # Reset any problematic state in the plot viewer
                        if hasattr(pf, 'local_labels'):
                            delattr(pf, 'local_labels')
                        if hasattr(pf, 'total_curves'):
                            delattr(pf, 'total_curves')
                        
                        # Ensure index is visible
                        self.csv_table.showindex = True
                        if hasattr(self.csv_table, 'rowheader'):
                            self.csv_table.rowheader.redraw()
                        
                        # Try to replot with minimal settings
                        pf.plotCurrent()
                        return True
                    except Exception as e2:
                        print(f"Warning: Fallback replot also failed: {e2}")
                        return False
            else:
                # Standard replot when no column filtering is active
                try:
                    pf.replot()
                    return True
                except Exception as e:
                    print(f"Standard replot failed: {e}")
                    try:
                        # Try alternative approach
                        pf.plotCurrent()
                        return True
                    except Exception as e2:
                        print(f"Alternative replot also failed: {e2}")
                        return False
        except Exception as e:
            print(f"Error during safe replot: {e}")
            traceback.print_exc()
            return False
    
    def convert_numpy_types(self, obj):
        """Convert NumPy types to native Python types for JSON serialization"""
        import numpy as np
        
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self.convert_numpy_types(value)for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_numpy_types(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self.convert_numpy_types(item) for item in obj)
        else:
            return obj    


    def save_settings(self):
        """Save settings to file"""
        print(f"Settings file absolute path: {os.path.abspath(self.settings_file)}")
        try:
            # Create settings directory if it doesn't exist
            directory = os.path.dirname(self.settings_file)
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"Created directory: {directory}")
            
            # Ensure recent_directories is a list
            if not hasattr(self, 'recent_directories') or self.recent_directories is None:
                self.recent_directories = []
                
            settings = {
                "recent_directories": self.recent_directories,
                "saved_filters": self.saved_filters,
                "saved_file_filters": self.saved_file_filters,
                "plot_settings": self.saved_plot_settings,
                "table_settings": self.saved_table_settings
            }
            
            # Convert NumPy types to native Python types
            settings = self.convert_numpy_types(settings)
            
            # Debug print before saving
            print(f"Saving settings: {settings}")
            # Add this after line 3954 (inside the save_settings method)
            print(f"Writing settings to file: {self.settings_file}")
            print(f"File exists before writing: {os.path.exists(self.settings_file)}")
            print(f"Directory exists: {os.path.exists(os.path.dirname(self.settings_file))}")
            print(f"Directory is writable: {os.access(os.path.dirname(self.settings_file), os.W_OK)}")
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
            
            # Verify the file was created and has content
            if os.path.exists(self.settings_file):
                file_size = os.path.getsize(self.settings_file)
                print(f"Settings file saved successfully. Size: {file_size} bytes")
            else:
                print(f"Error: Settings file was not created at {self.settings_file}")
                
        except Exception as e:
            print(f"Error saving settings: {e}")
            traceback.print_exc()

    def quit(self):
        """Save settings and quit the application"""
        try:
            # Save settings to file
            self.save_settings()
            
            # Destroy the window and exit
            self.destroy()
            
        except Exception as e:
            print(f"Error during quit: {e}")
            traceback.print_exc()
            # Still try to exit even if there was an error
            self.destroy()

    def save_table_settings(self):
        """Save the current table settings including index column and selected columns"""
        try:
            # Check if the CSV table exists
            if not hasattr(self, 'csv_table'):
                return
            
            # Create a dictionary to store table settings
            settings = {}
            
            # Save index column information
            if hasattr(self.csv_table, 'model') and hasattr(self.csv_table.model, 'df'):
                # Save the current index name
                index_name = self.csv_table.model.df.index.name
                if index_name is not None:
                    # Check if this is a temporary index name (ends with _index_temp or similar)
                    original_name = index_name
                    if "_index_temp" in index_name:
                        # Extract the original column name
                        original_name = index_name.split("_index_temp")[0]
                        print(f"Detected temporary index name, using original name: {original_name}")
                    
                    # Save both names
                    settings['index_column'] = original_name
                    settings['temp_index_column'] = index_name
                    print(f"Saved index column: {original_name}")
                
                # Save plot columns if available
                if hasattr(self.csv_table, 'multiplecollist') and self.csv_table.multiplecollist:
                    try:
                        # Convert column indices to column names, handling potential out-of-bounds indices
                        col_indices = self.csv_table.multiplecollist
                        col_names = []
                        
                        for i in col_indices:
                            try:
                                if i < len(self.csv_table.model.df.columns):
                                    col_names.append(self.csv_table.model.df.columns[i])
                            except Exception as e:
                                print(f"Warning: Could not access column index {i}: {e}")
                        
                        if col_names:  # Only save if we have valid column names
                            settings['plot_columns'] = col_names
                            print(f"Saved plot columns: {col_names}")
                    except Exception as e:
                        print(f"Error saving plot columns: {e}")
                        traceback.print_exc()
            
            # Save visible columns
            if hasattr(self, 'visible_columns') and self.visible_columns is not None:
                settings['visible_columns'] = list(self.visible_columns)
            
            # Save column order if available
            if hasattr(self.csv_table, 'columnorder'):
                settings['column_order'] = self.csv_table.columnorder
            
            # Save column widths if available
            if hasattr(self.csv_table, 'columnwidths'):
                # Convert to a serializable format (dict of string keys)
                col_widths = {}
                for col, width in self.csv_table.columnwidths.items():
                    col_widths[str(col)] = width
                settings['column_widths'] = col_widths
            
            # Save current sort column and order if available
            if hasattr(self.csv_table, 'sortkey'):
                settings['sort_key'] = self.csv_table.sortkey
            if hasattr(self.csv_table, 'sortOrder'):
                settings['sort_order'] = self.csv_table.sortOrder
            
            # Save the settings
            self.saved_table_settings = settings
            
        except Exception as e:
            print(f"Error saving table settings: {e}")
            traceback.print_exc()

    def restore_table_settings(self):
        """Restore previously saved table settings to the current table"""
        try:
            # Check if we have saved settings and if the table exists
            if not hasattr(self, 'saved_table_settings') or self.saved_table_settings is None or not hasattr(self, 'csv_table'):
                return
            
            settings = self.saved_table_settings
            
            print(f"DEBUG: restore_table_settings - Starting - DataFrame index type: {type(self.csv_table.model.df.index)}")
            print(f"DEBUG: restore_table_settings - Starting - DataFrame index name: {self.csv_table.model.df.index.name}")
            print(f"DEBUG: restore_table_settings - Starting - DataFrame index sample: {self.csv_table.model.df.index[:5]}")
            
            # Restore index column if specified
            if 'index_column' in settings and settings['index_column'] is not None:
                try:
                    # Check if the column exists in the current dataframe
                    index_column = settings['index_column']
                    print(f"DEBUG: restore_table_settings - Trying to restore index column: {index_column}")
                    
                    if index_column in self.csv_table.model.df.columns:
                        # Get the column index
                        col_idx = list(self.csv_table.model.df.columns).index(index_column)
                        print(f"DEBUG: restore_table_settings - Found index column at position: {col_idx}")
                        
                        # Set the index using the column index
                        self.csv_table.model.setindex([col_idx])
                        
                        # Make sure the index is shown
                        self.csv_table.showindex = True
                        self.csv_table.showIndex()
                        
                        print(f"DEBUG: restore_table_settings - After restoring index - DataFrame index type: {type(self.csv_table.model.df.index)}")
                        print(f"DEBUG: restore_table_settings - After restoring index - DataFrame index name: {self.csv_table.model.df.index.name}")
                        print(f"DEBUG: restore_table_settings - After restoring index - DataFrame index sample: {self.csv_table.model.df.index[:5]}")
                        
                        print(f"Restored index column: {index_column}")
                    else:
                        print(f"DEBUG: restore_table_settings - Index column {index_column} not found in current DataFrame")
                except Exception as e:
                    print(f"Error restoring index column: {e}")
                    traceback.print_exc()
            
            # Restore visible columns if specified
            if 'visible_columns' in settings and settings['visible_columns'] is not None:
                try:
                    # Store the visible columns
                    self.visible_columns = settings['visible_columns']
                    
                    # Apply the column filter
                    self._apply_column_filter()
                    print(f"Restored visible columns: {len(self.visible_columns)} columns")
                except Exception as e:
                    print(f"Error restoring visible columns: {e}")
                    traceback.print_exc()
            
            # Restore column order if specified
            if 'column_order' in settings and settings['column_order'] is not None:
                try:
                    self.csv_table.columnorder = settings['column_order']
                    print(f"Restored column order")
                except Exception as e:
                    print(f"Error restoring column order: {e}")
                    traceback.print_exc()
            
            # Restore column widths if specified
            if 'column_widths' in settings and settings['column_widths'] is not None:
                try:
                    # Convert back from string keys to original format
                    col_widths = {}
                    for col_str, width in settings['column_widths'].items():
                        try:
                            # Try to convert to int if it's a numeric string
                            col = int(col_str)
                        except ValueError:
                            # Otherwise keep as string
                            col = col_str
                        col_widths[col] = width
                    
                    self.csv_table.columnwidths = col_widths
                    print(f"Restored column widths")
                except Exception as e:
                    print(f"Error restoring column widths: {e}")
                    traceback.print_exc()
            
            # Restore sort settings if specified
            if 'sort_key' in settings and settings['sort_key'] is not None:
                try:
                    self.csv_table.sortkey = settings['sort_key']
                    print(f"Restored sort key: {settings['sort_key']}")
                except Exception as e:
                    print(f"Error restoring sort key: {e}")
                    traceback.print_exc()
                    
            if 'sort_order' in settings and settings['sort_order'] is not None:
                try:
                    self.csv_table.sortOrder = settings['sort_order']
                    print(f"Restored sort order: {settings['sort_order']}")
                except Exception as e:
                    print(f"Error restoring sort order: {e}")
                    traceback.print_exc()
            
            # Restore selected columns for plotting
            if 'plot_columns' in settings and settings['plot_columns'] is not None:
                try:
                    if not hasattr(self.csv_table, 'model') or not hasattr(self.csv_table.model, 'df'):
                        print("Warning: No DataFrame model available to restore plot columns")
                        return
                        
                    # Get the current column names in the DataFrame
                    current_columns = list(self.csv_table.model.df.columns)
                    
                    # Convert column names to indices, handling missing columns
                    col_names = settings['plot_columns']
                    col_indices = []
                    
                    for col_name in col_names:
                        try:
                            if col_name in current_columns:
                                col_idx = current_columns.index(col_name)
                                col_indices.append(col_idx)
                            else:
                                print(f"Warning: Column '{col_name}' not found in current DataFrame")
                        except Exception as e:
                            print(f"Warning: Error processing column '{col_name}': {e}")
                    
                    if col_indices:
                        try:
                            self.csv_table.multiplecollist = col_indices
                            # Draw the selected columns in the UI with validation
                            self._safe_draw_selected_columns()
                            print(f"Restored {len(col_indices)} plot columns")
                        except Exception as e:
                            print(f"Error applying column selection: {e}")
                            traceback.print_exc()
                    else:
                        print("No valid columns found to restore for plotting")
                        
                except Exception as e:
                    print(f"Error restoring plot columns: {e}")
                    traceback.print_exc()
            
            # Redraw the table to apply all settings
            self.csv_table.redraw()
            
            # At the end, after redraw
            print(f"DEBUG: restore_table_settings - End - DataFrame index type: {type(self.csv_table.model.df.index)}")
            print(f"DEBUG: restore_table_settings - End - DataFrame index name: {self.csv_table.model.df.index.name}")
            print(f"DEBUG: restore_table_settings - End - DataFrame index sample: {self.csv_table.model.df.index[:5]}")
            
        except Exception as e:
            print(f"Error restoring table settings: {e}")
            traceback.print_exc()

    def save_plot_settings_to_file(self):
        """Save the current plot settings to a file"""
        try:
            # Check if the plot frame exists and has been initialized
            if not hasattr(self, 'csv_table') or not hasattr(self.csv_table, 'pf'):
                return
            
            # Get the PlotViewer instance
            pf = self.csv_table.pf
            
            # Create a dictionary to store plot settings
            settings = {}
            
            # Save global options
            if hasattr(pf, 'globalopts'):
                settings['globalopts'] = copy.deepcopy(pf.globalopts)
            
            # Save matplotlib options
            if hasattr(pf, 'mplopts') and hasattr(pf.mplopts, 'kwds'):
                # Create a copy to avoid modifying the original
                mpl_options = copy.deepcopy(pf.mplopts.kwds)
                
                # Fix for 'color' and 'colormap' conflict - only save one of them
                if 'color' in mpl_options and 'colormap' in mpl_options:
                    # Prioritize 'color' over 'colormap'
                    del mpl_options['colormap']
                
                settings['mplopts'] = mpl_options
            
            # Save layout options
            if hasattr(pf, 'layoutopts'):
                settings['layout'] = {
                    'rows': pf.layoutopts.rows,
                    'cols': pf.layoutopts.cols
                }
                # Save mode if available
                if hasattr(pf.layoutopts, 'modevar'):
                    settings['layout']['mode'] = pf.layoutopts.modevar.get()
            
            # Save 3D options
            if hasattr(pf, 'mplopts3d') and hasattr(pf.mplopts3d, 'kwds'):
                # Create a copy to avoid modifying the original
                mpl_3d_options = copy.deepcopy(pf.mplopts3d.kwds)
                
                # Fix for 'color' and 'colormap' conflict in 3D options
                if 'color' in mpl_3d_options and 'colormap' in mpl_3d_options:
                    del mpl_3d_options['colormap']
                
                settings['mplopts3d'] = mpl_3d_options
            
            # Save label options
            if hasattr(pf, 'labelopts') and hasattr(pf.labelopts, 'kwds'):
                settings['labelopts'] = copy.deepcopy(pf.labelopts.kwds)
            
            # Ask user where to save the settings
            base_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialdir=os.path.dirname(self.current_file) if self.current_file else None,
                initialfile=f"plot_settings-{os.path.basename(self.current_file) if self.current_file else 'default'}"
            )
            
            if base_path:
                # Remove .json extension if present
                base_path = base_path.rsplit('.json', 1)[0]
                base_path = os.path.normpath(os.path.abspath(base_path))
                base_path = self.normalize_long_path(base_path)

                # Save the settings to file
                with open(base_path + '.json', 'w') as f:
                    json.dump(settings, f)
                
                print(f"Plot settings saved to: {base_path}.json")
                messagebox.showinfo("Save Successful", f"Plot settings saved to:\n{base_path}.json")
                
        except Exception as e:
            print(f"Error saving plot settings: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to save plot settings:\n{str(e)}")
            
    def load_plot_settings_from_file(self):
        """Load plot settings from a file and apply them to the current plot"""
        try:
            # Ask user to select a settings file
            file_path = filedialog.askopenfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialdir=os.path.dirname(self.current_file) if self.current_file else None,
                title="Select Plot Settings File"
            )
            
            if not file_path:
                return
                
            # Load settings from the file
            with open(file_path, 'r') as f:
                settings = json.load(f)
                
            # Store the settings
            self.saved_plot_settings = settings
            
            # Apply settings if a plot is currently open
            if hasattr(self, 'csv_table'):
                # Store the settings in the table for later use when plot is shown
                self.csv_table.custom_plot_settings = settings
                
                # If the plot viewer is already open, apply settings immediately
                if hasattr(self.csv_table, 'pf'):
                    pf = self.csv_table.pf
                    
                    # Apply global options
                    if 'globalopts' in settings and hasattr(pf, 'globalopts'):
                        for k, v in settings['globalopts'].items():
                            pf.globalopts[k] = v
                            if hasattr(pf, 'globalvars') and k in pf.globalvars:
                                pf.globalvars[k].set(v)
                    
                    # Apply matplotlib options with conflict resolution
                    if 'mplopts' in settings and hasattr(pf, 'mplopts'):
                        # Create a copy to avoid modifying the original
                        mpl_options = settings['mplopts'].copy()
                        
                        # Fix for 'color' and 'colormap' conflict
                        if 'color' in mpl_options and 'colormap' in mpl_options:
                            # Prioritize 'color' over 'colormap'
                            del mpl_options['colormap']
                        
                        pf.mplopts.kwds.update(mpl_options)
                        if hasattr(pf.mplopts, 'updateFromDict'):
                            pf.mplopts.updateFromDict(mpl_options)
                    
                    # Apply layout options
                    if 'layout' in settings and hasattr(pf, 'layoutopts'):
                        if 'rows' in settings['layout']:
                            pf.layoutopts.rows = settings['layout']['rows']
                        if 'cols' in settings['layout']:
                            pf.layoutopts.cols = settings['layout']['cols']
                        if 'mode' in settings['layout'] and hasattr(pf.layoutopts, 'modevar'):
                            pf.layoutopts.modevar.set(settings['layout']['mode'])
                    
                    # Apply 3D options with conflict resolution
                    if 'mplopts3d' in settings and hasattr(pf, 'mplopts3d'):
                        # Create a copy to avoid modifying the original
                        mpl_3d_options = settings['mplopts3d'].copy()
                        
                        # Fix for 'color' and 'colormap' conflict in 3D options
                        if 'color' in mpl_3d_options and 'colormap' in mpl_3d_options:
                            del mpl_3d_options['colormap']
                        
                        pf.mplopts3d.kwds.update(mpl_3d_options)
                        if hasattr(pf.mplopts3d, 'updateFromDict'):
                            pf.mplopts3d.updateFromDict(mpl_3d_options)
                    
                    # Apply label options
                    if 'labelopts' in settings and hasattr(pf, 'labelopts'):
                        pf.labelopts.kwds.update(settings['labelopts'])
                        if hasattr(pf.labelopts, 'updateFromDict'):
                            pf.labelopts.updateFromDict(settings['labelopts'])
                    
                    # Suppress warnings globally for this session
                    import warnings
                    warnings.filterwarnings('ignore', message='.*color.*and.*colormap.*cannot be used simultaneously.*')
                    warnings.filterwarnings('ignore', message='.*Tight layout not applied.*')
                    
                    # Replot with the new settings
                    if hasattr(pf, 'replot') and callable(pf.replot):
                        try:
                            pf.replot()
                        except Exception as e:
                            print(f"Warning: Error during replot: {e}")
                
                # If plot viewer is not open, patch the showPlot method to apply settings when opened
                else:
                    # Monkey patch the showPlot method to apply our settings
                    original_showPlot = self.csv_table.showPlot
                    
                    def patched_showPlot(self, *args, **kwargs):
                        # Call the original method first
                        result = original_showPlot(*args, **kwargs)
                        
                        # Now apply our saved settings
                        if hasattr(self, 'custom_plot_settings') and hasattr(self, 'pf'):
                            pf = self.pf
                            settings = self.custom_plot_settings
                            
                            # Apply global options
                            if 'globalopts' in settings and hasattr(pf, 'globalopts'):
                                for k, v in settings['globalopts'].items():
                                    pf.globalopts[k] = v
                                    if hasattr(pf, 'globalvars') and k in pf.globalvars:
                                        pf.globalvars[k].set(v)
                            
                            # Apply matplotlib options with conflict resolution
                            if 'mplopts' in settings and hasattr(pf, 'mplopts'):
                                # Create a copy to avoid modifying the original
                                mpl_options = settings['mplopts'].copy()
                                
                                # Fix for 'color' and 'colormap' conflict
                                if 'color' in mpl_options and 'colormap' in mpl_options:
                                    # Prioritize 'color' over 'colormap'
                                    del mpl_options['colormap']
                                
                                pf.mplopts.kwds.update(mpl_options)
                                if hasattr(pf.mplopts, 'updateFromDict'):
                                    pf.mplopts.updateFromDict(mpl_options)
                            
                            # Apply layout options
                            if 'layout' in settings and hasattr(pf, 'layoutopts'):
                                if 'rows' in settings['layout']:
                                    pf.layoutopts.rows = settings['layout']['rows']
                                if 'cols' in settings['layout']:
                                    pf.layoutopts.cols = settings['layout']['cols']
                                if 'mode' in settings['layout'] and hasattr(pf.layoutopts, 'modevar'):
                                    pf.layoutopts.modevar.set(settings['layout']['mode'])
                            
                            # Apply 3D options with conflict resolution
                            if 'mplopts3d' in settings and hasattr(pf, 'mplopts3d'):
                                # Create a copy to avoid modifying the original
                                mpl_3d_options = settings['mplopts3d'].copy()
                                
                                # Fix for 'color' and 'colormap' conflict in 3D options
                                if 'color' in mpl_3d_options and 'colormap' in mpl_3d_options:
                                    del mpl_3d_options['colormap']
                                
                                pf.mplopts3d.kwds.update(mpl_3d_options)
                                if hasattr(pf.mplopts3d, 'updateFromDict'):
                                    pf.mplopts3d.updateFromDict(mpl_3d_options)
                            
                            # Apply label options
                            if 'labelopts' in settings and hasattr(pf, 'labelopts'):
                                pf.labelopts.kwds.update(settings['labelopts'])
                                if hasattr(pf.labelopts, 'updateFromDict'):
                                    pf.labelopts.updateFromDict(settings['labelopts'])
                            
                            # Suppress warnings globally for this session
                            import warnings
                            warnings.filterwarnings('ignore', message='.*color.*and.*colormap.*cannot be used simultaneously.*')
                            warnings.filterwarnings('ignore', message='.*Tight layout not applied.*')
                            
                            # Replot with the new settings
                            if hasattr(pf, 'replot') and callable(pf.replot):
                                try:
                                    pf.replot()
                                except Exception as e:
                                    print(f"Warning: Error during replot: {e}")
                        
                        return result
                    
                    # Replace the original method with our patched version
                    self.csv_table.showPlot = types.MethodType(patched_showPlot, self.csv_table)
            
            # Save to application settings
            self.save_settings()
            
            print(f"Plot settings loaded from: {file_path}")
            messagebox.showinfo("Load Successful", f"Plot settings loaded from:\n{file_path}")
            
        except Exception as e:
            print(f"Error loading plot settings: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load plot settings:\n{str(e)}")
            
    def save_plot_settings(self):
        """Save the current plot settings from the pandastable PlotViewer"""
        try:
            # Check if the plot frame exists and has been initialized
            if not hasattr(self, 'csv_table') or not hasattr(self.csv_table, 'pf'):
                return
            
            # Get the PlotViewer instance
            pf = self.csv_table.pf
            
            # Create a dictionary to store plot settings
            settings = {}
            
            # Save global options
            if hasattr(pf, 'globalopts'):
                settings['globalopts'] = copy.deepcopy(pf.globalopts)
            
            # Save matplotlib options
            if hasattr(pf, 'mplopts') and hasattr(pf.mplopts, 'kwds'):
                # Create a copy to avoid modifying the original
                mpl_options = copy.deepcopy(pf.mplopts.kwds)
                
                # Fix for 'color' and 'colormap' conflict - only save one of them
                if 'color' in mpl_options and 'colormap' in mpl_options:
                    # Prioritize 'color' over 'colormap'
                    del mpl_options['colormap']
                
                settings['mplopts'] = mpl_options
            
            # Save layout options
            if hasattr(pf, 'layoutopts'):
                settings['layout'] = {
                    'rows': pf.layoutopts.rows,
                    'cols': pf.layoutopts.cols
                }
                # Save mode if available
                if hasattr(pf.layoutopts, 'modevar'):
                    settings['layout']['mode'] = pf.layoutopts.modevar.get()
            
            # Save 3D options
            if hasattr(pf, 'mplopts3d') and hasattr(pf.mplopts3d, 'kwds'):
                # Create a copy to avoid modifying the original
                mpl_3d_options = copy.deepcopy(pf.mplopts3d.kwds)
                
                # Fix for 'color' and 'colormap' conflict in 3D options
                if 'color' in mpl_3d_options and 'colormap' in mpl_3d_options:
                    del mpl_3d_options['colormap']
                
                settings['mplopts3d'] = mpl_3d_options
            
            # Save label options
            if hasattr(pf, 'labelopts') and hasattr(pf.labelopts, 'kwds'):
                settings['labelopts'] = copy.deepcopy(pf.labelopts.kwds)
            
            # Store the settings
            self.saved_plot_settings = settings
            
            # Save settings to file
            self.save_settings()
            
            print("Plot settings saved successfully")
            
        except Exception as e:
            print(f"Error saving plot settings: {e}")
            traceback.print_exc()
            
    def restore_plot_settings(self):
        """Restore previously saved plot settings to the pandastable PlotViewer"""
        try:
            # Check if plot settings exist
            if not hasattr(self, 'saved_plot_settings') or not self.saved_plot_settings:
                print("No plot settings to restore")
                return False
                
            # Check if csv_table exists
            if not hasattr(self, 'csv_table'):
                print("No table to apply plot settings to")
                return False
                
            # IMPORTANT: Check if plot viewer exists before proceeding
            if not hasattr(self.csv_table, 'pf') or self.csv_table.pf is None:
                print("Plot viewer not open, skipping plot settings restoration")
                return False            

            # The PlotViewer is created on demand when showPlot is called
            # We'll add a custom method to the csv_table that will apply our settings when the plot is shown
            self.csv_table.custom_plot_settings = self.saved_plot_settings
            
            # Check if plot viewer is already open
            if hasattr(self.csv_table, 'pf') and self.csv_table.pf is not None:
                pf = self.csv_table.pf
                settings = self.saved_plot_settings
                
                # Apply settings to the open plot viewer
                if not self._apply_plot_settings_to_viewer(pf, settings):
                    print("Warning: Failed to apply plot settings to viewer")
                    return False
                
                # Automatically replot with the selected columns
                if hasattr(self.csv_table, 'multiplecollist') and self.csv_table.multiplecollist:
                    try:
                        # Draw the selected columns in the UI with validation
                        self._safe_draw_selected_columns()

                        # Use our safe replot method that ensures index preservation
                        if self._safe_replot_with_index_preservation(pf):
                            print("Automatically replotted with the selected columns")
                        else:
                            print("Warning: Could not automatically replot")
                    except Exception as e:
                        print(f"Warning: Error during automatic replot: {e}")
                        traceback.print_exc()
                
                return True
            else:
                # Monkey patch the showPlot method to apply our settings
                try:
                    original_showPlot = self.csv_table.showPlot
                    
                    def patched_showPlot(self, *args, **kwargs):
                        # Call the original method first
                        result = original_showPlot(*args, **kwargs)
                        
                        # Now apply our saved settings
                        if hasattr(self, 'custom_plot_settings') and hasattr(self, 'pf') and self.pf is not None:
                            pf = self.pf
                            settings = self.custom_plot_settings
                            
                            # Apply settings to the newly opened plot viewer
                            app = self.table.app if hasattr(self.table, 'app') else None
                            if app and hasattr(app, '_apply_plot_settings_to_viewer'):
                                app._apply_plot_settings_to_viewer(pf, settings)
                        
                        return result
                    
                    # Replace the original method with our patched version
                    self.csv_table.showPlot = types.MethodType(patched_showPlot, self.csv_table)
                    return True
                except Exception as e:
                    print(f"Warning: Error patching showPlot method: {e}")
                    traceback.print_exc()
                    return False
            
        except Exception as e:
            print(f"Error restoring plot settings: {e}")
            traceback.print_exc()
            return False    

    def _apply_plot_settings_to_viewer(self, pf, settings):
        """Apply the given settings to a plot viewer instance"""
        try:
            # Validate inputs first
            if pf is None or settings is None:
                print("Warning: Cannot apply plot settings - plot viewer or settings are None")
                return False
                
            # Apply global options
            if 'globalopts' in settings and hasattr(pf, 'globalopts'):
                for k, v in settings['globalopts'].items():
                    pf.globalopts[k] = v
                    if hasattr(pf, 'globalvars') and k in pf.globalvars:
                        pf.globalvars[k].set(v)
            
            # Apply matplotlib options with conflict resolution
            if 'mplopts' in settings and hasattr(pf, 'mplopts'):
                # Create a copy to avoid modifying the original
                mpl_options = settings['mplopts'].copy()
                
                # Fix for 'color' and 'colormap' conflict
                if 'color' in mpl_options and 'colormap' in mpl_options:
                    # Prioritize 'color' over 'colormap'
                    del mpl_options['colormap']
                
                pf.mplopts.kwds.update(mpl_options)
                if hasattr(pf.mplopts, 'updateFromDict'):
                    pf.mplopts.updateFromDict(mpl_options)
            
            # Apply layout options
            if 'layout' in settings and hasattr(pf, 'layoutopts'):
                if 'rows' in settings['layout']:
                    pf.layoutopts.rows = settings['layout']['rows']
                if 'cols' in settings['layout']:
                    pf.layoutopts.cols = settings['layout']['cols']
                if 'mode' in settings['layout'] and hasattr(pf.layoutopts, 'modevar'):
                    pf.layoutopts.modevar.set(settings['layout']['mode'])
            
            # Apply 3D options with conflict resolution
            if 'mplopts3d' in settings and hasattr(pf, 'mplopts3d'):
                # Create a copy to avoid modifying the original
                mpl_3d_options = settings['mplopts3d'].copy()
                
                # Fix for 'color' and 'colormap' conflict in 3D options
                if 'color' in mpl_3d_options and 'colormap' in mpl_3d_options:
                    del mpl_3d_options['colormap']
                
                pf.mplopts3d.kwds.update(mpl_3d_options)
                if hasattr(pf.mplopts3d, 'updateFromDict'):
                    pf.mplopts3d.updateFromDict(mpl_3d_options)
            
            # Apply label options - Add extra validation here
            if 'labelopts' in settings and hasattr(pf, 'labelopts') and hasattr(pf.labelopts, 'kwds'):
                try:
                    pf.labelopts.kwds.update(settings['labelopts'])
                    if hasattr(pf.labelopts, 'updateFromDict'):
                        pf.labelopts.updateFromDict(settings['labelopts'])
                except Exception as e:
                    print(f"Warning: Error applying label options: {e}")
            
            # Suppress warnings globally for this session
            import warnings
            warnings.filterwarnings('ignore', message='.*color.*and.*colormap.*cannot be used simultaneously.*')
            warnings.filterwarnings('ignore', message='.*Tight layout not applied.*')
            
            return True
            
        except Exception as e:
            print(f"Error applying plot settings: {e}")
            traceback.print_exc()
            return False

if __name__ == "__main__":
    app = CSVBrowser()
    app.mainloop()        