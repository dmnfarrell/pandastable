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

from pandastable.app import ViewerApp

def main():
    """Run the application from outside the module - used for
       deploying as frozen app"""
    
    import sys, os
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="projfile",
                        help="Open a dataframe viewer project file", metavar="FILE")
    opts, remainder = parser.parse_args()
    if opts.projfile != None:
        app = ViewerApp(projfile=opts.projfile)
    else:
        app = ViewerApp()
    app.mainloop()
    return

if __name__ == '__main__':
    main()
