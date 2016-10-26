# coding: utf-8


"""
hello_pandastable_world.py
"""


from os import remove as rm
from os.path import isfile

from tkinter import Tk, Frame, TOP
from tkinter.ttk import Notebook

from pandastable import Table    

from textwrap import dedent as dd


TMP_CSV = "hello_pandastable.csv"

def setup():
    with open(TMP_CSV, "w") as f:
        f.write(dd(
            """
            ID, Hello
            1, PandasTable
            2, World!
            """
        ))


def pandas_gui():
    root = Tk()
    root.title("Hello PandasTable World!")

    notebook = Notebook(root)

    frame = Frame(notebook)

    table = Table(frame)
    table.show()
    table.importCSV(TMP_CSV)
    table.redraw()

    notebook.add(frame, text = "Pandas Table",compound = TOP)
    notebook.pack()

    root.mainloop()


def cleanup(): 
    if isfile(TMP_CSV):
        rm(TMP_CSV)    


def main():
    setup()
    pandas_gui()
    cleanup()    


if __name__ == '__main__':
    main()
