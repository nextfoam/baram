"""Implements a trigger that manipulates the controlDict in
such a way that every time-step is written to disk"""

import sys

from os import path
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.Error import warning

class CommonWriteAllTrigger(object):
    """ The class that does the actual triggering
    """

    def addOptions(self):
        self.ensureGeneralOptions()
        self.generalOpts.add_option("--write-all-timesteps",
                                    action="store_true",
                                    dest="writeAll",
                                    default=False,
                                    help="Write all the timesteps to disk")
        self.generalOpts.add_option("--purge-write",
                                    action="store",
                                    type="int",
                                    dest="purgeWrite",
                                    default=None,
                                    help="Together with write-all-timesteps determines the number of time-steps that is kept on disc. All will be kept if unset")
        self.generalOpts.add_option("--run-until",
                                    action="store",
                                    type="float",
                                    dest="runUntil",
                                    default=None,
                                    help="Change the endTime so that the case only runs until this time")

    def addWriteAllTrigger(self,run,sol):
        if self.opts.purgeWrite!=None and not self.opts.writeAll:
            warning("purgeWrite of",self.opts.purgeWrite,"ignored because write-all-timesteps unused")

        if self.opts.writeAll or self.opts.runUntil!=None:
            warning("Adding Trigger and resetting to safer start-settings")
            trig=WriteAllTrigger(sol,
                                 self.opts.writeAll,
                                 self.opts.purgeWrite,
                                 self.opts.runUntil)
            run.addEndTrigger(trig.resetIt)

class WriteAllTrigger:
    def __init__(self,sol,writeAll,purge,until):
        self.control=ParsedParameterFile(path.join(sol.systemDir(),"controlDict"),
                                         backup=True,
                                         doMacroExpansion=True)

        self.fresh=True

        try:
            if writeAll:
                self.control["writeControl"]="timeStep"
                self.control["writeInterval"]="1"
                if purge!=None:
                    self.control["purgeWrite"]=purge

            if until!=None:
                self.control["endTime"]=until

            self.control.writeFile()
        except Exception:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            warning("Restoring defaults")
            self.control.restore()
            raise e

    def resetIt(self):
        if self.fresh:
            warning("Trigger called: Resetting the controlDict")
            self.control.restore()
            self.fresh=False

# Should work with Python3 and Python2
