"""
Class that implements the common functionality for reporting the usage of a run
"""

from PyFoam.ThirdParty.six import print_

class CommonReportUsage(object):
    """ The class that reports the resource usage
    """

    def addOptions(self):
        self.ensureGeneralOptions()
        self.generalOpts.add_option("--report-usage",
                                    action="store_true",
                                    default=False,
                                    dest="reportUsage",
                                    help="After the execution the maximum memory usage is printed to the screen")

    def reportUsage(self,run):
        if self.opts.reportUsage:
            print_("\n  Used Memory: ",run.run.usedMemory(),"MB")

# Should work with Python3 and Python2
