"""
Class that implements the common functionality for treatment of the standard output
"""

from optparse import OptionGroup
from os import path

class CommonStandardOutput(object):
    """ The class that defines options for standard output
    """

    def addOptions(self,logname=None,longProgress=False):
        grp=OptionGroup(self.parser,
                        "Standard Output",
                        "Treatment of the standard output that is captured from the OpenFOAM-application")
        grp.add_option("--progress",
                       action="store_true",
                       default=False,
                       dest="progress",
                       help="Only prints the progress of the simulation, but swallows all the other output")
        if longProgress:            
            grp.add_option("--long-progress",
                           action="store_true",
                           default=False,
                           dest="longProgress",
                           help="Only prints the progress of the simulation in a long format")
        grp.add_option("--silent",
                       action="store_true",
                       default=False,
                       dest="silent",
                       help="Do not print any output")
        grp.add_option("--echo-command-prefix",
                       action="store",
                       default=None,
                       dest="echoCommandPrefix",
                       help="Do not print any output")
        grp.add_option("--logname",
                       dest="logname",
                       default=logname,
                       help="Name of the logfile")
        grp.add_option("--compress",
                       action="store_true",
                       dest="compress",
                       default=False,
                       help="Compress the logfile into a gzip file. Possible loss of data if the run fails")
        grp.add_option("--no-log",
                       action="store_true",
                       dest="noLog",
                       default=False,
                       help="Do not output a log-file")
        grp.add_option("--log-tail",
                       action="store",
                       dest="logTail",
                       default=None,
                       type="int",
                       help="Only write the last N lines to the logfile. Too small values might cause performance problems")

        self.parser.add_option_group(grp)

        inf=OptionGroup(self.parser,
                        "Run Info",
                        "Additional information about the run")
        inf.add_option("--remark",
                       dest="remark",
                       default=None,
                       help="Text string with a remark about the run")
        inf.add_option("--job-id",
                       dest="jobId",
                       default=None,
                       help="Text string with the job-ID of the queuing system (usually unused)")
        inf.add_option("--parameter",
                       dest="runParameters",
                       default=[],
        action="append",
        help="Parameter that is being added to the runInfo. Of the form <key>:<value>. Can be specified more than once")
        self.parser.add_option_group(inf)

    def getRunParameters(self):
        """Return a dictionary with the parameters"""
        parameters={}
        for p in self.opts.runParameters:
            try:
                k,v=p.split(":",1)
                try:
                    v=int(v)
                except ValueError:
                    try:
                        v=float(v)
                    except ValueError:
                        pass
                        # keep as a string
                parameters[k]=v
            except ValueError:
                parameters[k]=p
        return parameters

    def setLogname(self,
                   default="PyFoamRunner",
                   useApplication=True,
                   force=False):
        """Builds a logfile-name
        :param default: Default value if no prefix for the logfile-has been defined
        :param useApplication: append the name of the application to the prefix"""

        if self.opts.logname==None or force:
            self.opts.logname=default
        if useApplication:
            self.opts.logname+="."+path.basename(
                self.replaceAutoInArgs(self.parser.getArgs())[0])
