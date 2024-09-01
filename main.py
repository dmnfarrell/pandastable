#!/usr/bin/env python
"""
    DataExplore Application based on pandastable.
    Created January 2014
    Copyright (C) Damien Farrell

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 3
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from pandastable.app import DataExplore, TestApp

def main():
    """Run the application from outside the module - used for
       deploying as frozen app"""

    import sys, os
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="msgpack",
                        help="Open a dataframe as msgpack", metavar="FILE")
    parser.add_option("-p", "--project", dest="projfile",
                        help="Open a dataexplore project file", metavar="FILE")
    parser.add_option("-i", "--csv", dest="csv",
                        help="Open a csv file by trying to import it", metavar="FILE")
    parser.add_option("-x", "--excel", dest="excel",
                        help="Import an excel file", metavar="FILE")
    parser.add_option("-t", "--test", dest="test",  action="store_true",
                        default=False, help="Run a basic test app")

    opts, remainder = parser.parse_args()
    if opts.test:
        app = TestApp()
    else:
        if opts.projfile is not None:
            app = DataExplore(projfile=opts.projfile)
        elif opts.msgpack is not None:
            app = DataExplore(msgpack=opts.msgpack)
        elif opts.csv is not None:
            app = DataExplore()
            t = app.getCurrentTable()
            t.importCSV(opts.csv, dialog=True)
        elif opts.excel is not None:
            app = DataExplore()
            app.importExcel(opts.excel)
        else:
            app = DataExplore()
    app.mainloop()


if __name__ == '__main__':
    main()
