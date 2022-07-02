#  ICE Revision: $Id$
"""Base class for pyFoam-applications

Classes can also be called with a command-line string"""

from optparse import OptionGroup
from PyFoam.Basics.FoamOptionParser import FoamOptionParser,SubcommandFoamOptionParser
from PyFoam.Error import error,warning,FatalErrorPyFoamException,PyFoamException,isatty
from PyFoam.RunDictionary.SolutionDirectory import NoTouchSolutionDirectory
from PyFoam.FoamInformation import ensureDynamicLibraries

from PyFoam.Basics.TerminalFormatter import TerminalFormatter
from PyFoam import configuration

from .CursesApplicationWrapper import cursesWrap,CWindow,hasCurses

format=TerminalFormatter()
format.getConfigFormat("error")
format.getConfigFormat("warn")

import sys
from os import path,getcwd,environ
from copy import deepcopy

from PyFoam.ThirdParty.six import print_
from PyFoam.ThirdParty.six import iteritems,string_types


class PyFoamApplicationException(FatalErrorPyFoamException):
     def __init__(self,app, *text):
          self.app=app
          FatalErrorPyFoamException.__init__(self, *text, up=3)

     def __str__(self):
          return FatalErrorPyFoamException.__str__(self)+" in Application-class: "+self.app.__class__.__name__


def pyFoamExceptionHook(type,value,tb,debugOnSyntaxError=False):
    if hasattr(sys,'ps1'):
        warning("Interactive mode. No debugger")
        sys.__excepthook__(type,value,tb)
    elif not (isatty(sys.stderr) and isatty(sys.stdin) and isatty(sys.stdout)) and not (path.basename(sys.executable) in ["pvpython"]):
        warning("Not on a terminal. No debugger")
        sys.__excepthook__(type,value,tb)
    elif issubclass(type,SyntaxError) and not debugOnSyntaxError:
        warning("Syntax error. No debugger")
        sys.__excepthook__(type,value,tb)
    else:
        import traceback
        try:
             import ipdb as pdb
        except ImportError:
             import pdb
        except AttributeError:
             # ipdb doesn't work in pvpython
             import pdb
        traceback.print_exception(type,value,tb)
        print_()
        pdb.pm()

def pyFoamSIG1HandlerPrintStack(nr,frame):
     print_("Signal Nr",nr,"sent")
     raise FatalErrorPyFoamException("Signal nr",nr,"sent")

_LocalConfigurationFile=None

class PyFoamApplication(object):
    """This class is the base for all pyFoam-utilities"""
    class iDict(dict):
         "This class is a quick and dirty wrapper to use a dictionary like a struct"
         def __getattr__(self,key):
              try:
                   return self[key]
              except KeyError:
                   raise AttributeError(key)

    CWindowType=CWindow

    def __init__(self,
                 args=None,
                 description=None,
                 epilog=None,
                 examples=None,
                 usage=None,
                 interspersed=False,
                 nr=None,
                 changeVersion=True,
                 exactNr=True,
                 subcommands=None,
                 inputApp=None,
                 localConfigurationFile=None,
                 findLocalConfigurationFile=None,
                 allowCurses=True,
                 **kwArgs):
        """
        :param description: description of the command
        :param epilog: text to be printed after the options-help
        :param examples: usage examples to be printed after the epilog
        :param usage: Usage
        :param interspersed: Is the command line allowed to be interspersed (options after the arguments)
        :param args: Command line arguments when using the Application as a 'class' from a script
        :param nr: Number of required arguments
        :param changeVersion: May this application change the version of OF used?
        :param exactNr: Must not have more than the required number of arguments
        :param subcommands: parse and use subcommands from the command line. Either True or a list with subcommands
        :param inputApp: Application with input data. Used to allow a 'pipe-like' behaviour if the class is used from a Script
        :param localConfigurationFile: Use this file (or list of files) as a local configuration
        :param findLocalConfigurationFile: Method to find a configuration file BEFORE the actual parameters are parsed
        :param allowCurses: This application can wrap the output in a curses-window
        """

        global _LocalConfigurationFile

        self.allowCurses=allowCurses
        self.cursesWindow=None

        if _LocalConfigurationFile is not None:
             configuration().addFile(_LocalConfigurationFile)

        if isinstance(localConfigurationFile,string_types):
             configuration().addFile(localConfigurationFile)
        elif localConfigurationFile is not None:
             for c in localConfigurationFile:
                  configuration().addFile(c)

        if subcommands:
             self.subs=True
             if interspersed:
                  self.error("Subcommand parser does not work with 'interspersed'")
             if subcommands==True:
                  subcommands=[]
             self.parser=SubcommandFoamOptionParser(args=args,
                                                    description=description,
                                                    epilog=epilog,
                                                    examples=examples,
                                                    usage=usage,
                                                    subcommands=subcommands)
             nr=None
             exactNr=False
        else:
             self.subs=False
             self.parser=FoamOptionParser(args=args,
                                          description=description,
                                          epilog=epilog,
                                          examples=examples,
                                          usage=usage,
                                          interspersed=interspersed)

        try:
             self.calledName=sys.argv[0]
        except AttributeError:
             self.calledName="unknown"

        self.calledAsClass=(args!=None)
        if self.calledAsClass:
            try:
                self.calledName=self.__class__.__name__+" used by "+sys.argv[0]
            except AttributeError:
                self.calledName= self.__class__.__name__+" used by unknown program"
            self.parser.prog=self.calledName
        elif not _LocalConfigurationFile and findLocalConfigurationFile:
            if args:
                usedArgs=args
            else:
                try:
                     usedArgs=sys.argv[1:]
                except AttributeError:
                     usedArgs=[]
            _LocalConfigurationFile=findLocalConfigurationFile(usedArgs)
            if _LocalConfigurationFile and not path.exists(_LocalConfigurationFile):
                # Fix functions that do not check for the existence
                _LocalConfigurationFile=None
            if _LocalConfigurationFile:
                 configuration().addFile(_LocalConfigurationFile)

        self.generalOpts=None

        self.__appData=self.iDict()
        if inputApp:
            self.__appData["inputData"]=inputApp.getData()

        grp=OptionGroup(self.parser,
                        "Default",
                        "Options common to all PyFoam-applications")

        if changeVersion:
            # the options are evaluated in Basics.FoamOptionParser
            grp.add_option("--foamVersion",
                           dest="foamVersion",
                           default=None,
                           help="Change the OpenFOAM-version that is to be used. To get a list of know Foam-versions use the pyFoamVersion.py-utility")
            if "WM_PROJECT_VERSION" in environ:
                grp.add_option("--currentFoamVersion",
                               dest="foamVersion",
                               const=environ["WM_PROJECT_VERSION"],
                               default=None,
                               action="store_const",
                               help="Use the current OpenFOAM-version "+environ["WM_PROJECT_VERSION"])

            grp.add_option("--force-32bit",
                           dest="force32",
                           default=False,
                           action="store_true",
                           help="Forces the usage of a 32-bit-version if that version exists as 32 and 64 bit. Only used when --foamVersion is used")
            grp.add_option("--force-64bit",
                           dest="force64",
                           default=False,
                           action="store_true",
                           help="Forces the usage of a 64-bit-version if that version exists as 32 and 64 bit. Only used when --foamVersion is used")
            grp.add_option("--force-debug",
                           dest="compileOption",
                           const="Debug",
                           default=None,
                           action="store_const",
                           help="Forces the value Debug for the WM_COMPILE_OPTION. Only used when --foamVersion is used")
            grp.add_option("--force-opt",
                           dest="compileOption",
                           const="Opt",
                           default=None,
                           action="store_const",
                           help="Forces the value Opt for the WM_COMPILE_OPTION. Only used when --foamVersion is used")
            grp.add_option("--force-system-compiler",
                           dest="foamCompiler",
                           const="system",
                           default=None,
                           action="store_const",
                           help="Force using a 'system' compiler (compiler installed in the system)")
            grp.add_option("--force-openfoam-compiler",
                           dest="foamCompiler",
                           const="OpenFOAM",
                           default=None,
                           action="store_const",
                           help="Force using a 'OpenFOAM' compiler (compiler installed in ThirdParty)")
            grp.add_option("--force-compiler",
                           dest="wmCompiler",
                           default=None,
                           action="store",
                           help="Overwrite value for WM_COMPILER (for instance Gcc47 ...)")

        grp.add_option("--psyco-accelerated",
                       dest="psyco",
                       default=False,
                       action="store_true",
                       help="Accelerate the script using the psyco-library (EXPERIMENTAL and requires a separatly installed psyco)")
        grp.add_option("--profile-python",
                       dest="profilePython",
                       default=False,
                       action="store_true",
                       help="Profile the python-script (not the OpenFOAM-program) - mostly of use for developers")
        grp.add_option("--profile-cpython",
                       dest="profileCPython",
                       default=False,
                       action="store_true",
                       help="Profile the python-script (not the OpenFOAM-program) using the better cProfile library - mostly of use for developers")
        grp.add_option("--profile-hotshot",
                       dest="profileHotshot",
                       default=False,
                       action="store_true",
                       help="Profile the python-script using the hotshot-library (not the OpenFOAM-program) - mostly of use for developers - DEPRECATED as this library will by removed from standard python and is no longer supported")
        grp.add_option("--profile-line-profiler",
                       dest="profileLineProfiler",
                       default=False,
                       action="store_true",
                       help="Profile the python-script using the line_profiler-library (not the OpenFOAM-program) - mostly of use for developers - EXPERIMENTAL")

        dbg=OptionGroup(self.parser,
                        "Debugging",
                        "Options mainly used for debugging PyFoam-Utilities")

        dbg.add_option("--location-of-local-config",
                       dest="locationOfLocalConfig",
                       default=False,
                       action="store_true",
                       help="Prints the location of the found LocalConfigPyFoam-file that is used (if any)")
        dbg.add_option("--traceback-on-error",
                       dest="traceback",
                       default=False,
                       action="store_true",
                       help="Prints a traceback when an error is encountered (for debugging)")
        dbg.add_option("--interactive-debugger",
                       dest="interactiveDebug",
                       default=False,
                       action="store_true",
                       help="In case of an exception start the interactive debugger PDB. Also implies --traceback-on-error")
        dbg.add_option("--catch-USR1-signal",
                       dest="catchUSR1Signal",
                       default=False,
                       action="store_true",
                       help="If the USR1-signal is sent to the application with 'kill -USR1 <pid>' the application ens and prints a traceback. If interactive debugging is enabled then the debugger is entered. Use to investigate hangups")
        dbg.add_option("--also-catch-TERM-signal",
                       dest="alsoCatchTERMsignal",
                       default=False,
                       action="store_true",
                       help="In addition to USR1 catch the regular TERM-kill")
        dbg.add_option("--keyboard-interrupt-trace",
                       dest="keyboardInterrupTrace",
                       default=False,
                       action="store_true",
                       help="Make the application behave like with --catch-USR1-signal if <Ctrl>-C is pressed")
        dbg.add_option("--syntax-error-debugger",
                       dest="syntaxErrorDebugger",
                       default=False,
                       action="store_true",
                       help="Only makes sense with --interactive-debugger: Do interactive debugging even when a syntax error was encountered")
        dbg.add_option("--i-am-a-developer",
                       dest="developerMode",
                       default=False,
                       action="store_true",
                       help="Switch on all of the above options. Usually this makes only sense if you're developing PyFoam'")
        dbg.add_option("--interactive-after-execution",
                       dest="interacticeAfterExecution",
                       default=False,
                       action="store_true",
                       help="Instead of ending execution drop to an interactive shell (which is IPython if possible)")

        grp.add_option("--dump-application-data",
                       dest="dumpAppData",
                       default=False,
                       action="store_true",
                       help="Print the dictionary with the generated application data after running")
        grp.add_option("--pickle-application-data",
                       dest="pickleApplicationData",
                       default=None,
                       action="store",
                       type="string",
                       help="""\
Write a pickled version of the application data to a file. If the
filename given is 'stdout' then the pickled data is written to
stdout. The usual standard output is then captured and added to the
application data as an entry 'stdout' (same for 'stderr'). Be careful
with these option for commands that generate a lot of output""")

        self.parser.add_option_group(grp)
        self.parser.add_option_group(dbg)

        if self.allowCurses:
             crs=OptionGroup(self.parser,
                             "Curses",
                             "Wrap and color output using the curses-library")
             crs.add_option("--curses-wrap",
                            dest="cursesWrap",
                            default=False,
                            action="store_true",
                            help="Switch on curses wrapping (if possible)")
             crs.add_option("--output-buffer-curses",
                            dest="outputBufferCurses",
                            default=2000,
                            action="store",
                            type="int",
                            help="Number of lines that the curses buffer should store. Default: %default")
             crs.add_option("--sleep-time-end-curses",
                            dest="sleepTimeEndCurses",
                            default=0,
                            action="store",
                            type="int",
                            help="Number of seconds to sleep before dropping back onto the regular terminal when the command ended. Default: %default")
             crs.add_option("--no-powerline-font",
                            dest="powerlineFont",
                            default=True,
                            action="store_false",
                            help="The current terminal does not use a powerline-font and therefor the delimiters look weird (Powerline only works with Python3 because it needs native Unicode-support)")

             self.parser.add_option_group(crs)

        self.addOptions()
        self.parser.parse(nr=nr,exactNr=exactNr)
        ensureDynamicLibraries()
        if len(kwArgs)>0:
            self.parser.processKeywordArguments(kwArgs)
        self.opts=self.parser.getOptions()
        if self.subs:
            self.cmdname=self.parser.cmdname

        if self.opts.locationOfLocalConfig:
            if _LocalConfigurationFile:
                print_("Local configuration found at",
                      _LocalConfigurationFile)
            else:
                print_("No LocalConfigPyFoam-file found")

        if "WM_PROJECT_VERSION" not in environ:
             warning("$WM_PROJECT_VERSION unset. PyFoam will not be able to determine the OpenFOAM-version and behave strangely")
        if self.opts.developerMode:
             self.opts.syntaxErrorDebugger=True
             self.opts.keyboardInterrupTrace=True
             self.opts.alsoCatchTERMsignal=True
             self.opts.catchUSR1Signal=True
             self.opts.interactiveDebug=True
             self.opts.traceback=True

        if self.opts.interactiveDebug:
            sys.excepthook=lambda a1,a2,a3:pyFoamExceptionHook(a1,
                                                               a2,
                                                               a3,
                                                               debugOnSyntaxError=self.opts.syntaxErrorDebugger)
            self.opts.traceback=True
        if self.opts.catchUSR1Signal:
             import signal
             signal.signal(signal.SIGUSR1,pyFoamSIG1HandlerPrintStack)
             if self.opts.alsoCatchTERMsignal:
                  signal.signal(signal.SIGTERM,pyFoamSIG1HandlerPrintStack)
             self.opts.traceback=True

        if self.opts.keyboardInterrupTrace:
             import signal
             signal.signal(signal.SIGINT,pyFoamSIG1HandlerPrintStack)
             self.opts.traceback=True

        if self.opts.psyco:
            try:
                import psyco
                psyco.full()
            except ImportError:
                warning("No psyco installed. Continuing without acceleration")
        profOptions=sum([self.opts.profilePython,
                         self.opts.profileCPython,
                         self.opts.profileHotshot,
                         self.opts.profileLineProfiler])
        if profOptions>0:
            if profOptions>1:
                self.error("Only one profiling option can be specified at a time")
            print_("Running profiled")
            fnAdd=""
            if self.opts.profilePython:
                import profile
            elif self.opts.profileCPython:
                import cProfile as profile
            elif self.opts.profileLineProfiler:
                import line_profiler
                profile=line_profiler.LineProfiler(self.run)
                import PyFoam.RunDictionary.SolutionDirectory
                profile.add_module(PyFoam.RunDictionary.SolutionDirectory)
                fnAdd=".lineProfiler"
            else:
                import hotshot
            profileData=path.basename(sys.argv[0])+fnAdd+".profile"
            if self.opts.profilePython or self.opts.profileCPython:
                profile.runctx('self.run()',None,{'self':self},profileData)
                print_("Reading python profile")
                import pstats
                stats=pstats.Stats(profileData)
            elif self.opts.profileLineProfiler:
                import inspect
                nr=profile.add_module(inspect.getmodule(self))
                self.warning("Adding",nr,"functions for line-profiling")
                profile.runctx('self.run()',None,{'self':self})
                profile.dump_stats(profileData)
                profile.print_stats(open(profileData+".printed","w"))
                stats=None
            else:
                profileData+=".hotshot"
                prof=hotshot.Profile(profileData)
                prof.runctx('self.run()',{},{'self':self})
                print_("Writing and reading hotshot profile")
                prof.close()
                import hotshot.stats
                stats=hotshot.stats.load(profileData)
            if stats:
                stats.strip_dirs()
                stats.sort_stats('time','calls')
                stats.print_stats(20)

            self.parser.restoreEnvironment()
        else:
            try:
                doCurses=False
                if self.allowCurses:
                     if self.opts.cursesWrap:
                          if not sys.__stdout__.isatty():
                               self.warning("Stdout is not a terminal. Not using curses for output wrapping")
                          elif getattr(self.opts,"progress",False):
                               self.warning("Not using curses with progress")
                          elif getattr(self.opts,"silent",False):
                               self.warning("Not using curses with silent")
                          elif not hasCurses:
                               self.warning("Python has no curses library")
                          else:
                               doCurses=True

                if self.opts.pickleApplicationData=="stdout":
                    # Redirect output to memory
                    from PyFoam.ThirdParty.six.moves import StringIO

                    oldStdout=sys.stdout
                    oldStderr=sys.stderr
                    sys.stdout=StringIO()
                    sys.stderr=StringIO()
                    doCurses=False

                if doCurses:
                     result=cursesWrap(self,
                                       bufflen=self.opts.outputBufferCurses,
                                       powerline=self.opts.powerlineFont,
                                       endSleepTime=self.opts.sleepTimeEndCurses)
                else:
                     result=self.run()

                # do this at the earliest possible moment
                self.parser.restoreEnvironment()

                if self.opts.pickleApplicationData=="stdout":
                    # restore stdout
                    self.__appData["stdout"]=sys.stdout.getvalue()
                    self.__appData["stderr"]=sys.stderr.getvalue()
                    sys.stdout=oldStdout
                    sys.stderr=oldStderr

                if self.opts.pickleApplicationData:
                    from PyFoam.ThirdParty.six.moves import cPickle as pickle
                    if self.opts.pickleApplicationData=="stdout":
                        pick=pickle.Pickler(sys.stdout)
                    else:
                        pick=pickle.Pickler(open(self.opts.pickleApplicationData,'wb'))
                    pick.dump(self.__appData)
                    del pick
                if self.opts.dumpAppData:
                    import pprint
                    print_("Application data:")
                    printer=pprint.PrettyPrinter()
                    printer.pprint(self.__appData)

                if self.opts.interacticeAfterExecution:
                     print_("\nDropping to interactive shell ... ",end="")
                     ns={}
                     ns.update(locals())
                     ns.update(globals())
                     try:
                          import IPython
                          print_("found IPython ...",end="")
                          if "embed" in dir(IPython):
                               print_("up-to-date IPython\n")
                               IPython.embed(user_ns=ns)
                          else:
                               print_("old-school IPython\n")
                               IPython.Shell.IPythonShellEmbed(argv="",user_ns=ns)()

                     except ImportError:
                          print_("no IPython -> regular shell\n")
                          from code import InteractiveConsole
                          c=InteractiveConsole(ns)
                          c.interact()
                     print_("\nEnding interactive shell\n")
                return result
            except PyFoamException:
                e=sys.exc_info()[1]
                if self.opts.traceback or self.calledAsClass:
                    raise
                else:
                    self.errorPrint(str(e))

    def __getitem__(self,key):
        """Get application data"""
        try:
            return self.__appData[key]
        except KeyError:
            print_("available keys:",list(self.__appData.keys()))
            raise

    def __setitem__(self,key,value):
        """Set data. Only if key does not exist (data can only be set once)"""
        if key in self.__appData:
            self.error(key,"does already exist in app-data")
        self.__appData[key]=deepcopy(value)

    def __iter__(self):
        """Iterate over the application data"""
        for k in self.__appData:
            yield k

    def iterkeys(self):
        return iter(list(self.__appData.keys()))

    def iteritems(self):
        return iter(list(self.__appData.items()))

    def __getattr__(self,key):
         try:
              return self.__appData[key]
         except KeyError:
              raise AttributeError(key)

    def getData(self):
        """Get the application data"""
        return deepcopy(self.__appData)

    def setData(self,data):
        """Set the application data

        :param data: dictionary whose entries will be added to the
        application data (possibly overwriting old entries of the same name)"""
        for k,v in iteritems(data):
            self.__appData[k]=deepcopy(v)

    def ensureGeneralOptions(self):
        if self.generalOpts==None:
            self.generalOpts=OptionGroup(self.parser,
                                         "General",
                                         "General options for the control of OpenFOAM-runs")
            self.parser.add_option_group(self.generalOpts)

    def addOptions(self):
        """
        Add options to the parser
        """
        pass

    def run(self):
        """
        Run the real application
        """
        error("Not a valid application")


    def error(self,*args):
         """Raise a error exception. How it will be handled is a different story
        :param args: Arguments to the exception
         """
         raise PyFoamApplicationException(self, *args)

    def errorPrint(self,*args):
        """
        Prints an error message and exits
        :param args: Arguments that are to be printed
        """
        if isatty(sys.stdout):
            print_(format.error, end=' ')
        print_("Error in",self.calledName,":", end=' ')
        for a in args:
            print_(a, end=' ')
        if isatty(sys.stdout):
            print_(format.reset)
        else:
            print_()
        sys.exit(-1)

    def warning(self,*args):
        """
        Prints a warning message
        :param args: Arguments that are to be printed
        """
        if isatty(sys.stdout):
            print_(format.warn, end=' ')
        print_("Warning in",self.calledName,":", end=' ')
        for a in args:
            print_(a, end=' ')
        if isatty(sys.stdout):
            print_(format.reset)
        else:
            print_()

    def depreciationWarning(self,reason):
         self.warning("\n",
                      "This utility is now deprecated because",reason,
                      "\n",
                      "It will be removed in future versions of PyFoam\n")

    def silent(self,*args):
        """
        Don't print a warning message
        :param args: Arguments that are to be printed
        """
        pass

    def checkCase(self,name,fatal=True,verbose=True):
        """
        Check whether this is a valid OpenFOAM-case
        :param name: the directory-bame that is supposed to be the case
        :param fatal: If this is not a case then the application ends
        :param verbose: If this is not a case no warning is issued
        """
        if fatal:
            func=self.error
        elif verbose:
            func=self.warning
        else:
            func=self.silent

        if not path.exists(name):
            func("Case",name,"does not exist")
            return False
        if not path.isdir(name):
            func("Case",name,"is not a directory")
            return False
        if not path.exists(path.join(name,"system")):
            func("Case",name,"does not have a 'system' directory")
            return False
        if not path.exists(path.join(name,"constant")):
            func("Case",name,"does not have a 'constant' directory")
            return False

        return True

    def escapeArgument(self,arg):
        """
        Check if this argument has spaces etc and surround it with
        " to make it copy\pastable
        """
        import string
        hasSpace=False
        forbidden="'\""
        for c in arg:
            if c in string.whitespace+forbidden:
                hasSpace=True
                break
        if not hasSpace:
            return arg
        isLongArg=False
        if len(arg)>2:
            if arg[:2]=="--" and arg.find("="):
               isLongArg=True
        if not isLongArg:
           return '"'+arg.replace('"','\\"')+'"'
        pos=arg.find('=')+1
        return arg[:pos]+'"'+arg[pos:].replace('"','\\"')+'"'

    def addToCaseLog(self,name,*text):
        """
        Add information about the application that was run to the case-log
        """
        hasSpace=0

        logline=[NoTouchSolutionDirectory(name)]
        if self.calledName==sys.argv[0]:
            logline+=["Application:",
                      path.basename(sys.argv[0])]+ \
                      [self.escapeArgument(a) for a in sys.argv[1:]]
        else:
            logline+=["Application:",self.calledName]

        logline+=[" | with cwd",getcwd()," | "]
        logline+=text
        NoTouchSolutionDirectory.addToHistory(*logline)

    def addLocalConfig(self,directory=None):
        """
        Adds a local directory (assuming it is found)
        """
        if directory!=None:
            configuration().addFile(path.join(directory,"LocalConfigPyFoam"),silent=True)

    def getCasePath(self,args):
        """Try to determine the actual case location from the arguments"""
        from os import path
        val="."
        for i in range(len(args)-1):
            if args[i]=="-case":
                val=args[i+1]
        val=path.abspath(val)
        if not path.isdir(val):
           self.warning("Specified case",val,"is not a directory")
        return val

    def replaceAutoInArgs(self,args):
        """
        If the first argument is 'auto' replace it with the 'application' entry from
        the controlDict
        """
        if len(args)==0:
            return args
        if args[0]!="auto":
            return args

        if not hasattr(self,"_replacedSolver"):
            from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
            sol=SolutionDirectory(self.getCasePath(args))
            try:
                self._replacedSolver=sol.getDictionaryContents("system","controlDict")["application"]
                self.warning("Replacing solver 'auto' with",
                             self._replacedSolver,"in arguments")
            except KeyError:
                self.warning("No entry 'application' in controlDict. Staying with 'auto'")
                return args
        return [self._replacedSolver]+args[1:]

    def getApplication(self):
        if not hasattr(self,"_replacedSolver"):
             return self.parser.getApplication()
        else:
             return self.parser.getApplication()+" ("+self._replacedSolver+")"

    def localConfigFromCasename(self,args):
        """Look for the local configuration assuming that the first argument
        after '-case' is the case directory"""
        for i in range(len(args)):
            if args[i]=="-case":
               return path.join(args[i+1],"LocalConfigPyFoam")
        return self.localConfigInCWD(args)

    def localConfigInArgs(self,args):
        """Assume that the first argument that is no option and a directory
        can have a local configuration"""
        for a in args:
            if len(a)>0 and a[0]!="-":
               if path.isdir(a):
                   confPath=path.join(a,"LocalConfigPyFoam")
                   if path.exists(confPath):
                       return confPath
                   else:
                       return None
        return None

    def localConfigInArgsFile(self,args):
        """Assume that the first argument that is no option and a file
        can has a local configuration in the same directory"""
        for a in args:
            if len(a)>0 and a[0]!="-":
               if path.exists(a):
                   confPath=path.join(path.dirname(path.realpath(a)),"LocalConfigPyFoam")
                   if path.exists(confPath):
                       return confPath
                   else:
                       return None
        return None

    def localConfigInCWD(self,args):
        """find the local configuration in the current directory"""
        import os
        confPath=path.join(os.getcwd(),"LocalConfigPyFoam")
        if path.exists(confPath):
             return confPath
        else:
             return None

# Should work with Python3 and Python2
