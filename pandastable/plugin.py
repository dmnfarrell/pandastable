#!/usr/bin/env python
"""
    Implements the dataexplore plugin class.
    Created Oct 2015
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

import sys
import os
import inspect

class Plugin(object):
    """Base Plugin class, should be inherited by any plugin"""

    capabilities = []
    requires = []

    def __init__(self, parent=None):
        self.parent = parent
        return

    def _getmethods(self):
        """Get a list of all available public methods"""

        mems = inspect.getmembers(self, inspect.ismethod)
        methods = [m for m in mems if not m[0].startswith('_')]
        return methods

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.capabilities)

    def quit(self, evt=None):
        if hasattr(self, 'mainwin'):
            self.mainwin.destroy()
        return

def load_plugins(plugins):

    failed = []
    for plugin in plugins:
        try:
            __import__(plugin, None, None, [''])
        except Exception as e:
            print('failed to load %s plugin' %plugin)
            print(e)
            failed.append((plugin,e))
    return failed

def init_plugin_system(folders):
    for folder in folders:
        if not os.path.exists(folder):
            continue
        if not folder in sys.path:
             sys.path.insert(0, folder)
        plugins = parsefolder(folder)
        print (plugins)
        failed = load_plugins(plugins)
    return failed

def find_plugins():
    return Plugin.__subclasses__()

def parsefolder(folder):
    """Parse for all .py files in plugins folder or zip archive"""

    filenms=[]
    homedir = os.path.expanduser("~")
    if os.path.isfile(folder):
        #if in zip file, we need to handle that (installer distr)
        import zipfile
        zf = zipfile.ZipFile(folder,'r')
        dirlist = zf.namelist()
        for x in dirlist:
            if 'plugins' in x and x.endswith('.py'):
                print (x)
                zf.extract(x)
        zf.close()
        #copy plugins to home dir where they will be found
        shutil.copytree('plugins', os.path.join(homedir,'plugins'))

    elif os.path.isdir(folder):
        dirlist = os.listdir(folder)
        filenm=""
        for x in dirlist:
             filenm = x
             if filenm.endswith("py"):
                 filenms.append(os.path.splitext(filenm)[0])
        filenms.sort()
        filenameslist = [os.path.basename(y) for y in filenms]
        return filenameslist

_instances = {}

def get_plugins_by_capability(capability):

    result = []
    for plugin in Plugin.__subclasses__():
        print (plugin)
        if capability in plugin.capabilities:
            if not plugin in _instances:
                _instances[plugin] = plugin()
            result.append(_instances[plugin])
    return result

def describe_class(obj):
    """ Describe the class object passed as argument,
       including its methods """

    import inspect
    methods = []
    cl = obj.__class__
    print ('Class: %s' % cl.__name__)
    count = 0
    for name in cl.__dict__:
       item = getattr(cl, name)
       if inspect.ismethod(item):
           count += 1
           #describe_func(item, True)
           methods.append(item)

    if count==0:
      print ('No members')
    return methods


def describe_func(obj, method=False):
   """ Describe the function object passed as argument.
   If this is a method object, the second argument will
   be passed as True """

   try:
       arginfo = inspect.getargspec(obj)
   except TypeError:
      print
      return

   args = arginfo[0]
   argsvar = arginfo[1]

   if args:
       if args[0] == 'self':
           wi('\t%s is an instance method' % obj.__name__)
           args.pop(0)

       wi('\t-Method Arguments:', args)

       if arginfo[3]:
           dl = len(arginfo[3])
           al = len(args)
           defargs = args[al-dl:al]
           wi('\t--Default arguments:',zip(defargs, arginfo[3]))

   if arginfo[1]:
       wi('\t-Positional Args Param: %s' % arginfo[1])
   if arginfo[2]:
       wi('\t-Keyword Args Param: %s' % arginfo[2])