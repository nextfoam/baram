"""Implements a trigger that sets and resets 'safer' settings for
Steady runs"""

import re
import sys

from os import path
from optparse import OptionGroup
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.Error import warning

class CommonSafeTrigger(object):
    """ The class that does the actual triggering
    """

    def addOptions(self):
        grp=OptionGroup(self.parser,
                        "Safe settings",
                        "Set safer settings for steady runs")
        grp.add_option("--safe-until",
                       type="float",
                       dest="safeUntil",
                       default=None,
                       help="Sets lower under-relaxation and lower-order convection-schemes for the start of the simulation")
        grp.add_option("--safe-relaxation-factor",
                               type="float",
                               dest="safeRelaxation",
                               default=0.5,
                               help="The factor by which the relaxation-factors should be scaled down (when calculating safe). Default: %default")
        self.parser.add_option_group(grp)

    def addSafeTrigger(self,run,sol,steady=True):
        if self.opts.safeUntil:
            if not steady:
                warning("This is an unsteady run. No safe settings set")
            else:
                warning("Adding Trigger and resetting to safer start-settings")
                trig=SafeTrigger(sol,self.opts.safeRelaxation)
                run.addTrigger(self.opts.safeUntil,trig.resetIt)
                run.addEndTrigger(trig.resetIt)


class SafeTrigger:
    def __init__(self,sol,factor):
        self.solution=ParsedParameterFile(path.join(sol.systemDir(),"fvSolution"),backup=True)
        self.schemes=ParsedParameterFile(path.join(sol.systemDir(),"fvSchemes"),backup=True)

        self.fresh=True

        try:
            relax=self.solution["relaxationFactors"]
            for var in relax:
                relax[var]*=factor

            cExp=re.compile("div\((.+),(.+)\)")
            conv=self.schemes["divSchemes"]
            for nm in conv:
                if cExp.match(nm) or nm=="default":
                    conv[nm]="Gauss upwind"

            self.solution.writeFile()
            self.schemes.writeFile()
        except Exception:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            warning("Restoring defaults")
            self.solution.restore()
            self.schemes.restore()
            raise e

    def resetIt(self):
        if self.fresh:
            warning("Trigger called: Resetting fvSchemes and fvSolution")
            self.solution.restore()
            self.schemes.restore()
            self.fresh=False

# Should work with Python3 and Python2
