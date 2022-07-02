#  ICE Revision: $Id$
"""
Application class that implements pyFoamExecute
"""

from PyFoam.Applications.PyFoamApplication import PyFoamApplication
from PyFoam.Basics.Utilities import which
from PyFoam import configuration as conf

from .CommonBlink1 import CommonBlink1

from PyFoam.ThirdParty.six import print_

from subprocess import call
from optparse import OptionGroup

class Execute(PyFoamApplication,
              CommonBlink1):

    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Runs a command, but first switches the environment to a specific
OpenFOAM-version. Is of use for using wmake for a specific version
        """

        PyFoamApplication.__init__(self,
                                   nr=1,
                                   exactNr=False,
                                   args=args,
                                   usage="%prog [options] <command> [arguments]",
                                   description=description,
                                   **kwargs)

    def addOptions(self):
        debug=OptionGroup(self.parser,
                          "Run in Debugger",
                          "Run the executable in the debugger")
        self.parser.add_option_group(debug)

        debug.add_option("--run-in-debugger",
                         action="store_true",
                         dest="runInDebugger",
                         default=False,
                         help="Run the program in a debugger. Drops to the the shell o the debugger in the case of a problem")
        debug.add_option("--debugger-call",
                         action="store",
                         dest="debuggerCall",
                         default=conf().getArch("Execution","DebuggerCall"),
                         help="The command used to call the compiler. The string {exe} is replaced with the name of the executable. The string {args} with the arguments (if arguments were given). Default: '%default'")
        CommonBlink1.addOptions(self,withExecute=True)

    def run(self):
        self.initBlink()
        if self.blink1:
            self.blink1.playRepeated(self.opts.blink1executepattern,
                                     self.opts.blink1executeinterleave)
        if not self.opts.runInDebugger:
            result=call(self.parser.getArgs())
            if result!=0:
                print_("\nError result:",result)
        else:
            exe=which(self.parser.getArgs()[0])
            args=self.parser.getArgs()[1:]
            pre,post=self.opts.debuggerCall.split("{args}")
            preString=pre.format(exe=exe)
            postString=post.format(exe=exe)
            call(preString.split()+args+postString.split())
        self.stopBlink()

# Should work with Python3 and Python2
