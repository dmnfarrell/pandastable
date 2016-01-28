"""
    Manages preferences for Table class.

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import os, sys
import pickle

class Preferences:

    def __init__(self,program,defaults):
        """Find and load the preferences file"""

        filename='.'+program+'_preferences'
        dirs=self.get_dirs()
        self.noprefs = False
        try:
            for ldir in dirs:
                fn=os.path.join(ldir,filename)

                if os.path.isfile(fn):
                    self.load_prefs(fn)
                    self.save_prefs()
                    return
                else:
                    self.noprefs = True
            if self.noprefs == True:
                raise
        except:
            # If we didn't find a file then set to default and save
            #print('Did not find preferences!!!')
            self.prefs=defaults.copy()
	        #print(dirs)
            self.pref_file=os.path.join(dirs[0],filename)
            self.prefs['_prefdir']=dirs[0]
            self.prefs['_preffile']=self.pref_file
            self.save_prefs()

            if 'HOMEPATH' in os.environ:
                self.prefs['datadir']=os.environ['HOMEPATH']
            if 'HOME' in os.environ:
                self.prefs['datadir']=os.environ['HOME']

            if hasattr(self.prefs,'datadir'):
                mydocs=os.path.join(self.prefs['datadir'],'My Documents')
                if os.path.isdir(mydocs):
                    self.prefs['datadir']=mydocs
            self.save_prefs()
        return

    def __del__(self):
        self.save_prefs()
        return

    def set(self,key,value):
        self.prefs[key]=value
        self.save_prefs()
        return

    def get(self,key):
        if key in self.prefs:
            return self.prefs[key]
        else:
            raise NameError('No such key')
        return

    def delete(self,key):
        if key in self.prefs:
            del self.prefs[key]

        self.save_prefs()
        return

    def get_dirs(self):

        dirs=[]
        keys=['HOME','HOMEPATH','HOMEDRIVE']
        for key in keys:
            if key in os.environ:
                dirs.append(os.environ[key])
        if 'HOMEPATH' in os.environ:

            dirs.append(os.environ['HOMEPATH'])

        possible_dirs=["C:\\","D:\\","/"]
        for pdir in possible_dirs:
            if os.path.isdir(pdir):
                dirs.append(pdir)

        rdirs=[]
        for dirname in dirs:
            if os.path.isdir(dirname):
                rdirs.append(dirname)
        return rdirs

    def load_prefs(self,filename):

        self.pref_file=filename
        #print(("loading prefs from ",self.pref_file))
        try:
            fd=open(filename)
            self.prefs=pickle.load(fd)
            fd.close()
        except:
            fd.close()
            fd=open(filename,'rb')
            self.prefs=pickle.load(fd)
            fd.close()
        return

    def save_prefs(self):
        try:
            fd=open(self.pref_file,'wb')
        except:
            print('could not save')
            return
        pickle.dump(self.prefs,fd)
        fd.close()
        return
