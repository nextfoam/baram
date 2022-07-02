#  ICE Revision: $Id$
"""
Class that implements common functionality for selecting timesteps
"""

from optparse import OptionGroup

from PyFoam.ThirdParty.six import print_

class CommonSelectTimesteps(object):
    """
    This class compiles a list of timesteps that should be processed
    """
    def __init__(self):
        pass

    def addOptions(self,defaultUnique,singleTime=False):
        """Add the necessary options
        :param defaultUnique: whether timesteps are unique by default
        :param singleTime: only a single timestep may be selected"""

        self.singleTime=singleTime

        time=OptionGroup(self.parser,
                         "Time Specification",
                         "Which times should be processed")
        time.add_option("--time",
                        type="float",
                        dest="time",
                        default=[],
                        action="append",
                        help="Timestep that should be processed."+"" if singleTime else "Can be used more than once")
        time.add_option("--latest-time",
                        dest="latest",
                        action="store_true",
                        default=False,
                        help="Use the latest time")
        if not self.singleTime:
            time.add_option("--all-times",
                            dest="all",
                            action="store_true",
                            default=False,
                            help="Process all times")
            time.add_option("--after-time",
                            type="float",
                            dest="afterTime",
                            action="store",
                            default=None,
                            help="Process all after this time")
            time.add_option("--before-time",
                            type="float",
                            dest="beforeTime",
                            action="store",
                            default=None,
                            help="Process all before this time")

        if defaultUnique:
            time.add_option("--duplicate-times",
                            dest="unique",
                            action="store_false",
                            default=True,
                            help="Allow using a time-directory onlymore than once")
        else:
            time.add_option("--unique-times",
                            dest="unique",
                            action="store_true",
                            default=False,
                            help="Use each time-directory only once")

        time.add_option("--show-times",
                        dest="showTimes",
                        action="store_true",
                        default=False,
                        help="Show the times in the case and the times that will be used")

        time.add_option("--parallel-times",
                        dest="parallelTimes",
                        action="store_true",
                        default=False,
                        help="Use the information from 'processor0' to determine the available times")

        self.parser.add_option_group(time)

    def processTimestepOptions(self,
                               sol):
        """Process the options
        :param sol: the solution-directory that is to be worked with"""

        if self.opts.parallelTimes:
            sol.setToParallel()

        if self.opts.latest:
            self.opts.time.append(float(sol.getLast()))
        if self.singleTime:
            if len(self.opts.time)>1:
                self.error("Only a single time allow. We got",len(self.opts.time)," : ",
                           ", ".join(self.opts.time))
        else:
            if self.opts.all:
                for t in sol.getTimes():
                    self.opts.time.append(float(t))
            if self.opts.beforeTime or self.opts.afterTime:
                start=float(sol.getFirst())
                end=float(sol.getLast())
                if self.opts.beforeTime:
                    end=self.opts.beforeTime
                if self.opts.afterTime:
                    start=self.opts.afterTime
                for t in sol.getTimes():
                    tVal=float(t)
                    if tVal>=start and tVal<=end:
                        self.opts.time.append(tVal)

        self.opts.time.sort()

        times=[]

        for s in self.opts.time:
            times.append(sol.timeName(s,minTime=True))

        if self.opts.unique:
            tmp=[]
            last=None
            cnt=0
            for s in times:
                if last!=s:
                    tmp.append(s)
                else:
                    cnt+=1
                last=s
            if cnt>0:
                self.warning("Removed",cnt,"duplicate times")
            times=tmp

        if len(times)==0:
            self.warning("No valid times specified")

        if self.opts.showTimes:
            print_("Times in case:",sol.getTimes())
            print_("Used times:",times)

        return times
    def processTimestepOptionsIndex(self,sol):
        """Process the time options and return a list of (time,index) tuples"""
        times=self.processTimestepOptions(sol)

        return [(t,sol.timeIndex(t,True)) for t in times]

# Should work with Python3 and Python2
