from setuptools import setup
import sys,os
home=os.path.expanduser('~')

setup(
    name = 'pandastable',
    version = '0.0.1',
    description = 'Tkinter frontend for pandas dataframes',
    url='http://code.google.com/p/pandastable/',
    license='GPL v3',
    author = 'Damien Farrell',
    author_email = 'farrell.damien[at]gmail.com',   
	install_requires=['numpy>=1.5',
                      'matplotlib>=1.1',
                      'pandas>=0.13'],
    entry_points = { 'gui_scripts': [
                     'pandastableapp = pandastable.app:main']},
    classifiers = ["Operating System :: OS Independent",
            "Programming Language :: Python :: 3",
            "Topic :: Software Development :: User Interfaces",
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
            "Development Status :: 4 - Beta",        
            "Intended Audience :: Science/Research"],
    keywords = ['tkinter', 'spreadsheet', 'table', 'pandas', 'data analysis'],
)
