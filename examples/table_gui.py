import pandas as pd
import tkinter as tk
from tkinter import filedialog as fd
from pandastable import Table, TableModel


main_window = attr_table  = None
title_prefix, dataset_filename = "PandasTable Tester", ""


def reset_table(table):
    #if table.model.getRowCount() > 0:
    #table.model.deleteRows()
    table.updateModel(TableModel(pd.DataFrame()))
    table.redraw()


def load_csv():
    global attr_table, main_window, dataset_filename
    filetypes = [("CSV files", "*.csv"), ("TSV files", "*.tsv")]
    dataset_filename = fd.askopenfilename(title='Choose a file', filetypes=filetypes)
    if dataset_filename is None or len(dataset_filename) == 0:
        return
    sep = {"csv": ",", "tsv": "\t"}
    df = pd.read_csv(dataset_filename, sep=sep[dataset_filename[-3:]])
    attr_table.updateModel(TableModel(df))
    attr_table.redraw()
    main_window.title(title_prefix + " - " + dataset_filename)
    main_window.update()


if __name__ == "__main__":
    main_window = tk.Tk()
    main_window.title(title_prefix)
    # main_window.geometry("1200x800")

    frame = tk.Frame(main_window)
    frame.rowconfigure([0, 1, 2], weight=1)
    frame.columnconfigure([0, 1], weight=1)
    frame.pack(expand=True, fill='both')

    buttons_frame = tk.Frame(frame)
    buttons_frame.rowconfigure(0, weight=1)
    buttons_frame.columnconfigure([0, 1, 2, 3, 4, 5, 6], weight=1)
    load_button = tk.Button(buttons_frame, text="Load CSV", command=load_csv)
    load_button.grid(row=0, column=0, padx=0, pady=0)
    buttons_frame.grid(row=0, columnspan=7, padx=10, pady=10, sticky="nsew")

    bk_frame = tk.Frame(frame)
    bk_frame.rowconfigure(0, weight=2)
    bk_frame.columnconfigure([0, 1], weight=1)
    attr_table_frame = tk.LabelFrame(bk_frame, text="Attributes")
    attr_table = Table(attr_table_frame, dataframe=pd.DataFrame(),
                       showtoolbar=False, showstatusbar=True, rows=20, cols=5, editable=False, enable_menus=False)
    attr_table.show()
    attr_table_frame.grid(row=0, column=0, padx=5, pady=0, sticky="nsew")

    vb_frame = tk.Frame(bk_frame)
    vb_frame.rowconfigure(0, weight=1)
    vb_frame.columnconfigure([0, 1], weight=1)
    vb_frame.grid(row=0, column=1, padx=5, pady=0, sticky='nsew')
    bk_frame.grid(row=1, columnspan=2, padx=10, pady=5, sticky='nsew')

    main_window.mainloop()
