"""
Application class that implements pyFoamJoinTimeline.py
"""

import sys
from os import path,makedirs
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from PyFoam.RunDictionary.TimelineDirectory import TimelineDirectory
from PyFoam.ThirdParty.six import print_


class JoinTimelines(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Searches a timeline directory for timelines from different times (restarts) and
joins them into a single timeline
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <timelinedir1> ...",
                                   nr=1,
                                   exactNr=False,
                                   changeVersion=False,
                                   interspersed=True,
                                   **kwargs)

    def addOptions(self):
        output=OptionGroup(self.parser,
                          "Output",
                          "Where and how to output")
        self.parser.add_option_group(output)
        output.add_option("--target-directory",
                          action="store",
                          dest="targetDirectory",
                          default=None,
                          help="Directory in which the updated timelines should be stored. If unspecified then in the same directory as the original directory a dictionary 'joinedTimelines' is created")
        how=OptionGroup(self.parser,
                        "How",
                        "How the utility should work")
        self.parser.add_option_group(how)
        how.add_option("--quiet",
                          action="store_false",
                          dest="verbose",
                          default=True,
                          help="Do not print which files are being processed now")

    def report(self,*args):
        if self.opts.verbose:
            print_(*args)

    def run(self):
        for tlName in self.parser.getArgs():
            self.report("Reading timelines from",tlName)
            tlName=path.abspath(tlName)
            cName=path.dirname(tlName)
            tName=path.basename(tlName)
            if self.opts.targetDirectory is None:
                destDir=path.join(cName,"joinedTimelines",tName)
            else:
                destDir=path.join(path.abspath(self.opts.targetDirectory),tName)

            tl=TimelineDirectory(dirName=tlName)
            times=tl.writeTimes
            if len(times)==0:
                self.report("No times found. Skipping")
                continue

            tDir=path.join(destDir,times[0])
            self.report("Writing to",tDir)
            if not path.exists(tDir):
                makedirs(tDir)
            for val in tl.values:
                self.report("Processing value",val)
                with open(path.join(tDir,val),"w") as outFile:
                    first=True
                    for ti in range(len(times)):
                        try:
                            tLimit=float(times[ti+1])
                        except IndexError:
                            tLimit=1e40
                        with open(path.join(tlName,times[ti],val)) as inFile:
                            for l in inFile.readlines():
                                parts=l.split()
                                try:
                                    tVal=float(parts[0])
                                    if tVal<=tLimit:
                                        outFile.write(l)
                                    else:
                                        break
                                except ValueError:
                                    if first:
                                        outFile.write(l)
                        first=False
