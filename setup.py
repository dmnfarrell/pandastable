from setuptools import setup
import sys,os
home=os.path.expanduser('~')

setup(
    name = 'pandastable',
    version = '0.8.1',
    description = 'Library for embedding tables in Tkinter using pandas DataFrames',
    url='https://github.com/dmnfarrell/pandastable',
    license='GPL v3',
    author = 'Damien Farrell',
    author_email = 'farrell.damien[at]gmail.com',
    packages = ['pandastable'],
    package_data={'pandastable': ['dataexplore.gif','datasets/*.mpk',
                                  'plugins/*.py']},
    install_requires=['matplotlib>=2.0',
                      'pandas>=0.18',
                      'numexpr>=2.4',
                      'xlrd>=0.9',
                      'future'],
    entry_points = { 'gui_scripts': [
                     'dataexplore = pandastable.app:main']},
    classifiers = ['Operating System :: OS Independent',
            'Programming Language :: Python :: 3',
            'Operating System :: MacOS :: MacOS X',
            'Operating System :: Microsoft :: Windows',
            'Operating System :: POSIX',
            'Topic :: Software Development :: User Interfaces',
            'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
            'Development Status :: 4 - Beta',
            'Intended Audience :: Science/Research'],
    keywords = ['tkinter', 'ttk', 'spreadsheet', 'table', 'pandas', 'data analysis'],
)
