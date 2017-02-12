#!/usr/bin/env python3
"""
    DataExplore plugin for embedded IPython console.
    Created Oct 2015

    This is a modified version of source code from the Accerciser project
    (http://live.gnome.org/accerciser). The original code is released under a
    BSD license. This version has been updated to work with Python >3.3 and
    with fixes for the Tkinter text widget.
"""

from __future__ import absolute_import, division, print_function
try:
    from tkinter import *
    from tkinter.ttk import *
except:
    from Tkinter import *
    from ttk import *
import re
import sys
import os
import io
import platform
import subprocess
import IPython
from pkg_resources import parse_version
from pandastable.plugin import Plugin
from pandastable import images, dialogs, util

class IterableIPShell:
    def __init__(self,argv=None,user_ns=None,user_global_ns=None,
                 cin=None, cout=None,cerr=None, input_func=None):
        '''
        @param argv: Command line options for IPython
        @type argv: list
        @param user_ns: User namespace.
        @type user_ns: dictionary
        @param user_global_ns: User global namespace.
        @type user_global_ns: dictionary.
        @param cin: Console standard input.
        @type cin: IO stream
        @param cout: Console standard output.
        @type cout: IO stream
        @param cerr: Console standard error.
        @type cerr: IO stream
        @param input_func: Replacement for builtin raw_input()
        @type input_func: function
        '''

        io = IPython.utils.io
        if input_func:
          if parse_version(IPython.release.version) >= parse_version("1.2.1"):
            IPython.terminal.interactiveshell.raw_input_original = input_func
          else:
            IPython.frontend.terminal.interactiveshell.raw_input_original = input_func
        if cin:
          io.stdin = io.IOStream(cin)
        if cout:
          io.stdout = io.IOStream(cout)
        if cerr:
          io.stderr = io.IOStream(cerr)

        # This is to get rid of the blockage that occurs during
        # IPython.Shell.InteractiveShell.user_setup()

        io.raw_input = lambda x: None

        os.environ['TERM'] = 'dumb'
        excepthook = sys.excepthook

        #temp fix to import warning in frozen app
        if getattr(sys, 'frozen', False):
            import warnings
            warnings.simplefilter("ignore")

        #from IPython.config.loader import Config
        from traitlets.config.loader import Config
        cfg = Config()
        cfg.InteractiveShell.colors = "Linux"

        # InteractiveShell's __init__ overwrites io.stdout,io.stderr with
        # sys.stdout, sys.stderr, this makes sure they are right
        #
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = io.stdout.stream, io.stderr.stream

        # InteractiveShell inherits from SingletonConfigurable, so use instance()
        #
        if parse_version(IPython.release.version) >= parse_version("1.2.1"):
          self.IP = IPython.terminal.embed.InteractiveShellEmbed.instance(\
                  config=cfg, user_ns=user_ns)
        else:
          self.IP = IPython.frontend.terminal.embed.InteractiveShellEmbed.instance(\
                  config=cfg, user_ns=user_ns)

        sys.stdout, sys.stderr = old_stdout, old_stderr

        self.IP.system = lambda cmd: self.shell(self.IP.var_expand(cmd),
                                                header='IPython system call: ')
                                                #local_ns=user_ns)
                                                #global_ns=user_global_ns)
                                                #verbose=self.IP.rc.system_verbose)

        self.IP.raw_input = input_func
        sys.excepthook = excepthook
        self.iter_more = 0
        self.history_level = 0
        self.complete_sep =  re.compile('[\s\{\}\[\]\(\)]')
        self.updateNamespace({'exit':lambda:None})
        self.updateNamespace({'quit':lambda:None})
        #self.IP.readline_startup_hook(self.IP.pre_readline)
        # Workaround for updating namespace with sys.modules
        #
        self.__update_namespace()
        return

    def __update_namespace(self):
        '''
        Update self.IP namespace for autocompletion with sys.modules
        '''
        for k, v in list(sys.modules.items()):
            if not '.' in k:
              self.IP.user_ns.update({k:v})

    def execute(self):
        '''
        Executes the current line provided by the shell object.
        '''
        self.history_level = 0
        orig_stdout = sys.stdout
        sys.stdout = IPython.utils.io.stdout

        orig_stdin = sys.stdin
        sys.stdin = IPython.utils.io.stdin;
        self.prompt = self.generatePrompt(self.iter_more)

        self.IP.hooks.pre_prompt_hook()
        if self.iter_more:
            try:
                self.prompt = self.generatePrompt(True)
            except:
                self.IP.showtraceback()
            if self.IP.autoindent:
                self.IP.rl_do_indent = True

        try:
          line = self.IP.raw_input(self.prompt)
        except KeyboardInterrupt:
          self.IP.write('\nKeyboardInterrupt\n')
          self.IP.input_splitter.reset()
        except:
          self.IP.showtraceback()
        else:
          self.IP.input_splitter.push(line)
          self.iter_more = self.IP.input_splitter.push_accepts_more()
          self.prompt = self.generatePrompt(self.iter_more)
          if (self.IP.SyntaxTB.last_syntax_error and
              self.IP.autoedit_syntax):
              self.IP.edit_syntax_error()
          if not self.iter_more:
              if parse_version(IPython.release.version) >= parse_version("2.0.0-dev"):
                source_raw = self.IP.input_splitter.raw_reset()
              else:
                source_raw = self.IP.input_splitter.source_raw_reset()[1]
              self.IP.run_cell(source_raw, store_history=True)
              self.IP.rl_do_indent = False
          else:
              # TODO: Auto-indent
              #
              self.IP.rl_do_indent = True
              pass

        sys.stdout = orig_stdout
        sys.stdin = orig_stdin

    def generatePrompt(self, is_continuation):
        '''
        Generate prompt depending on is_continuation value

        @param is_continuation
        @type is_continuation: boolean

        @return: The prompt string representation
        @rtype: string

        '''

        # Backwards compatibility with ipyton-0.11
        #
        ver = IPython.__version__
        if '0.11' in ver:
            prompt = self.IP.hooks.generate_prompt(is_continuation)
        else:
            if is_continuation:
                prompt = self.IP.prompt_manager.render('in2')
            else:
                prompt = self.IP.prompt_manager.render('in')

        return prompt


    def historyBack(self):
        '''
        Provides one history command back.

        @return: The command string.
        @rtype: string
        '''
        self.history_level -= 1
        if not self._getHistory():
          self.history_level +=1
        return self._getHistory()

    def historyForward(self):
        '''
        Provides one history command forward.

        @return: The command string.
        @rtype: string
        '''
        if self.history_level < 0:
          self.history_level += 1
        return self._getHistory()

    def _getHistory(self):
        '''
        Get's the command string of the current history level.

        @return: Historic command string.
        @rtype: string
        '''
        try:
          rv = self.IP.user_ns['In'][self.history_level].strip('\n')
        except IndexError:
          rv = ''
        return rv

    def updateNamespace(self, ns_dict):
        '''
        Add the current dictionary to the shell namespace.

        @param ns_dict: A dictionary of symbol-values.
        @type ns_dict: dictionary
        '''
        self.IP.user_ns.update(ns_dict)

    def complete(self, line):
        '''
        Returns an auto completed line and/or posibilities for completion.

        @param line: Given line so far.
        @type line: string

        @return: Line completed as for as possible,
        and possible further completions.
        @rtype: tuple
        '''
        import functools
        split_line = self.complete_sep.split(line)
        if split_line[0]:
            possibilities = self.IP.complete(split_line[0])
        else:
            completed = line
            possibilities = ['', []]
        if possibilities:
          def _commonPrefix(str1, str2):
            '''
            Reduction function. returns common prefix of two given strings.

            @param str1: First string.
            @type str1: string
            @param str2: Second string
            @type str2: string

            @return: Common prefix to both strings.
            @rtype: string
            '''
            for i in range(len(str1)):
                if not str2.startswith(str1[:i+1]):
                    return str1[:i]
            return str1
          if possibilities[1]:
            common_prefix = functools.reduce(_commonPrefix, possibilities[1]) or line[-1]
            completed = line[:-len(split_line[-1])]+common_prefix
          else:
            completed = line
        else:
          completed = line
        return completed, possibilities[1]

    def shell(self, cmd,verbose=0,debug=0,header=''):
        '''
        Replacement method to allow shell commands without them blocking.

        @param cmd: Shell command to execute.
        @type cmd: string
        @param verbose: Verbosity
        @type verbose: integer
        @param debug: Debug level
        @type debug: integer
        @param header: Header to be printed before output
        @type header: string
        '''
        stat = 0
        if verbose or debug:
            print (header+cmd)
        # flush stdout so we don't mangle python's buffering
        if not debug:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, shell=True,
                                  close_fds=True)
            (input, output) = (p.stdin, p.stdout)
            out = output.read().decode("utf-8").split('\n')
            for line in out:
                print (line.rstrip())
        return

ansi_colors =  {'0;30': 'Black',
                '0;31': 'Red',
                '0;32': 'Green',
                '0;33': 'Brown',
                '0;34': 'Blue',
                '0;35': 'Purple',
                '0;36': 'Cyan',
                '0;37': 'LightGray',
                '1;30': 'DarkGray',
                '1;31': 'DarkRed',
                '1;32': 'SeaGreen',
                '1;33': 'Yellow',
                '1;34': 'LightBlue',
                '1;35': 'MediumPurple',
                '1;36': 'LightCyan',
                '1;37': 'White'}

class TkConsoleView(Text):
    def __init__(self,root):
        Text.__init__(self, root, width=60, height=16)

        if 'Windows' in platform.system():
            font = ('Courier New',10)
        else:
            font = 'monospace 10'
        self.config(font=font)
        # As the stdout,stderr etc. get fiddled about with we need to put any
        # debug output into a file
        self.debug=0
        if self.debug:
            self.o = open('debug.out','w')

        # Keeps track of where the insert cursor should be on the entry line
        self.mark = 'scroll_mark'
        self.mark_set(self.mark, END)
        self.mark_gravity(self.mark, RIGHT)

        # Set the tags for colouring the text
        for code in ansi_colors:
          self.tag_config(code,
                          foreground=ansi_colors[code])

        self.tag_config('notouch')

        # colour_pat matches the colour tags and places these in a group
        # match character with hex value 01 (start of heading?) zero or more times, followed by
        # the hex character 1b (escape)  then "[" and group ...things.. followed by m (?) and then
        # hex character 02 (start of text) zero or more times
        self.color_pat = re.compile('\x01?\x1b\[(.*?)m\x02?')

        self.line_start = 'line_start' # Tracks start of user input on the line (excluding prompt)
        self.mark_set(self.line_start, INSERT)
        self.mark_gravity(self.line_start, LEFT)

        self._setBindings()

    def write(self, text, editable=False):

        segments = self.color_pat.split(text)
        # First is blank line
        segment = segments.pop(0)

        # Keep track of where we started entering text so we can set as non-editable
        self.start_mark = 'start_mark'
        self.mark_set(self.start_mark, INSERT)
        self.mark_gravity(self.start_mark, LEFT)
        self.insert(END, segment)

        if segments:
            # Just return the colour tags
            ansi_tags = self.color_pat.findall(text)

            for tag in ansi_tags:
                i = segments.index(tag)
                self.insert(END,segments[i+1],tag)
                segments.pop(i)

        if not editable:
            if self.debug:
                print ("adding notouch between %s : %s" % ( self.index(self.start_mark),\
                                 self.index(INSERT)))

            self.tag_add('notouch',self.start_mark,"%s-1c" % INSERT)
        self.mark_unset(self.start_mark)
        return

    def showBanner(self,banner):
        """Print the supplied banner on starting the shell"""
        self.write(banner)

    def showPrompt(self, prompt):
        self.write(prompt)
        self.mark_set(self.line_start, INSERT)
        self.see(INSERT) #Make sure we can always see the prompt

    def changeLine(self, text):
        self.delete(self.line_start,"%s lineend" % self.line_start)
        self.write(text, True)

    def getCurrentLine(self):
        rv = self.get(self.line_start, END)
        if self.debug:
            print ("getCurrentline: %s" % rv)
            print ("INSERT: %s" % END)
            print ("END: %s" % INSERT)
            print ("line_start: %s" % self.index(self.line_start))
        return rv

    def showReturned(self, text):
        self.tag_add('notouch',self.line_start,"%s lineend" % self.line_start )
        self.write('\n'+text)
        if text:
          self.write('\n')
        self.showPrompt(self.prompt)

    def _setBindings(self):
        """ Bind the keys we require.
            REM: if a bound function returns "break" then no other bindings are called
            If it returns None, then the other default bindings are called.
        """
        self.bind("<Key>",self.processKeyPress)
        self.bind("<Return>",self.processEnterPress)
        self.bind("<Up>",self.processUpPress)
        self.bind("<Down>",self.processDownPress)
        self.bind("<Tab>",self.processTabPress)
        self.bind("<BackSpace>",self.processBackSpacePress)

    def isEditable(self):
        """ Scan the notouch tag range in pairs and see if the INSERT index falls
            between any of them.
        """
        ranges = self.tag_ranges('notouch')
        first=None
        for idx in ranges:
            if not first:
                first=idx
                continue
            else:
                if self.debug:
                    print ("Comparing %s between %s : %s " % (self.index(IPythonINSERT),first,idx))

                if self.compare( INSERT,'>=',first ) and \
                   self.compare( INSERT,'<=',idx ):
                    return False
            first=None
        return True

    def processKeyPress(self,event):

        if self.debug:
            print ("processKeyPress got key: %s" % event.char)
            print ("processKeyPress INSERT: %s" % self.index(INSERT))
            print ("processKeyPress END: %s" % self.index(END))

        if not self.isEditable():
            # Move cursor mark to start of line
            self.mark_set(INSERT,self.mark)

        # Make sure line_start follows inserted text
        self.mark_set(self.mark,"%s+1c" %INSERT)

    def processBackSpacePress(self,event):
        if not self.isEditable():
            return "break"

    def processEnterPress(self,event):
        self._processLine()
        return "break" # Need break to stop the other bindings being called

    def processUpPress(self,event):
        self.changeLine(self.historyBack())
        return "break"

    def processDownPress(self,event):
        self.changeLine(self.historyForward())
        return "break"

    def processTabPress(self,event):
        """Do tab completion"""
        if not self.getCurrentLine().strip():
            return
        completed, possibilities = self.complete(self.getCurrentLine())
        if len(possibilities) > 1:
            slice = self.getCurrentLine()
            self.write('\n')
            #for symbol in possibilities:
            #    self.write(symbol+'\n')
            n=3
            for i in range(0, len(possibilities), n):
                chunk = possibilities[i:i+n]
                for symbol in chunk:
                    s = "%-22s" %symbol
                    self.write(s)
                self.write('\n')
            self.showPrompt(self.prompt)
        self.changeLine(completed or slice)
        return "break"

    def setFont(self):

        sizes = list(range(8,30,2))
        fonts = util.getFonts()
        d = dialogs.MultipleValDialog(title='Font',
                              initialvalues=(fonts,sizes),
                              labels=('Font:', 'Size:'),
                              types=('combobox','combobox'),
                              parent = self)
        if d.result == None:
            return
        font = d.results[0]
        size = d.results[1]
        self.config(font='"%s" %s' %(font, size))
        return

class IPythonView(TkConsoleView, IterableIPShell):
    def __init__(self,root,banner=None):
        TkConsoleView.__init__(self,root)
        self.cout = io.StringIO()
        IterableIPShell.__init__(self, cout=self.cout,cerr=self.cout,
                         input_func=self.raw_input)

        if banner:
          self.showBanner(banner)
        self.execute()
        self.cout.truncate(0)
        self.showPrompt(self.prompt)
        self.interrupt = False
        return

    def raw_input(self, prompt=''):
        if self.interrupt:
          self.interrupt = False
          raise KeyboardInterrupt
        return self.getCurrentLine()

    def _processLine(self):
        self.history_pos = 0
        self.execute()
        rv = self.cout.getvalue()
        #print (rv)
        rv = self.strip_non_ascii(rv)
        if self.debug:
            print ("_processLine got rv: %s" % rv)
        if rv:
            rv = rv.strip('\n')
        self.showReturned(rv)
        self.cout.truncate(0)
        return

    def strip_non_ascii(self, string):
        ''' Returns the string without non ASCII characters'''
        stripped = (c for c in string if 0 < ord(c) < 127)
        return ''.join(stripped)

class IPythonPlugin(Plugin):
    """Plugin for ipython console"""

    capabilities = ['gui','uses_sidepane']
    requires = ['']
    menuentry = 'IPython Console'
    version = '0.1'

    def __init__(self):
        return

    def main(self, parent):

        if parent==None:
            return
        self.parent = parent
        self._doFrame()
        s = IPythonView(self.mainwin)
        s.pack(side=LEFT, fill=BOTH,expand=1)
        #scroll=Scrollbar(self.mainwin)
        #scroll.pack(side=LEFT,fill=Y)
        #s.configure(yscrollcommand=scroll.set)
        bf = Frame(self.mainwin)
        bf.pack(side=RIGHT,fill=BOTH)
        dialogs.addButton(bf, 'Close', self.quit, images.cross(), 'close', side=TOP)
        dialogs.addButton(bf, 'Font', s.setFont, images.font(), 'font', side=TOP)

        self.table = self.parent.getCurrentTable()
        df = self.table.model.df
        import pandas as pd
        import numpy as np
        import pandastable as pt
        s.updateNamespace({'df':df, 'table':self.table,
                           'app':self.parent,
                           'pd':pd, 'np':np, 'pt':pt})
        return

if __name__ == '__main__':
    root = Tk()
    s = IPythonView(root)
    s.pack()
    root.mainloop()
