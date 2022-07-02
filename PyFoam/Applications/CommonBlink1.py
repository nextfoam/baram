"""Common options for blink(1)-devices"""

try:
    from PyFoam.Infrastructure.Blink1 import Blink1
    hasBlink=True
except ImportError:
    hasBlink=False

from optparse import OptionGroup
from PyFoam import configuration as conf

import sys

from PyFoam.Error import PyFoamException

class CommonBlink1(object):
    """Common options for blink1-devices"""
    def addOptions(self,withExecute=False):
        self.__blink1=None
        if hasBlink:
            self.blink1grp=OptionGroup(self.parser,
                                       "Blink(1)",
                                       "Options for signalling on a blink(1)-device")
            self.blink1grp.add_option("--use-blink1",
                                      action="store_true",
                                      default=False,
                                      dest="useBlink1",
                                      help="Should we use the blink1 for notifications on this utility")
            self.blink1grp.add_option("--blink-timestep-color",
                                      dest="blink1stepcolor",
                                      default=conf().get("Blink1","timestepcolor"),
                                      help="The default color for time-steps. Default: %default")
            if withExecute:
                self.blink1grp.add_option("--blink-execute-pattern",
                                          dest="blink1executepattern",
                                          default=conf().get("Blink1","executepattern"),
                                          help="The default pattern to play during execution. Default: %default")
                self.blink1grp.add_option("--blink-execute-interleave",
                                          dest="blink1executeinterleave",
                                          type=float,
                                          default=conf().getfloat("Blink1","executeinterleave"),
                                          help="The default pause between playing the pattern during execution. Default: %default")

            self.parser.add_option_group(self.blink1grp)

    def initBlink(self):
        if hasBlink:
            if self.opts.useBlink1:
                try:
                    self.__blink1=Blink1(ticColor=self.opts.blink1stepcolor)
                except PyFoamException:
                    e=sys.exc_info()[1]
                    self.warning("Problem initializing blink(1):",e)

    def stopBlink(self):
        if self.__blink1:
            self.__blink1.stop()

    @property
    def blink1(self):
        return self.__blink1
