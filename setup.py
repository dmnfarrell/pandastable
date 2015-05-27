from setuptools import setup
import sys,os
home=os.path.expanduser('~')

setup(
    name = 'pandastable',
    version = '0.2.1',
    description = 'Library for embedding tables in Tkinter using pandas DataFrames',
    url='https://github.com/dmnfarrell/pandastable',
    license='GPL v3',
    author = 'Damien Farrell',
    author_email = 'farrell.damien[at]gmail.com',
    packages = ['pandastable'],
	install_requires=['numpy>=1.5',
                      'matplotlib>=1.1',
                      'pandas>=0.16',
		      'xlrd>=0.9'],
    entry_points = { 'gui_scripts': [
                     'dataexplore = pandastable.app:main']},
    classifiers = ["Operating System :: OS Independent",
            "Programming Language :: Python :: 3",
            "Topic :: Software Development :: User Interfaces",
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
            "Development Status :: 4 - Beta",
            "Intended Audience :: Science/Research"],
    keywords = ['tkinter', 'spreadsheet', 'table', 'pandas', 'data analysis'],
)
