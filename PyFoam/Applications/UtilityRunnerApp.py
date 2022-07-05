#  ICE Revision: $Id$
"""
Application class that implements pyFoamUtilityRunner
"""

from .PyFoamApplication import PyFoamApplication

from PyFoam.Execution.UtilityRunner import UtilityRunner

from PyFoam.ThirdParty.six import print_

import sys
from os import path

class UtilityRunnerApp(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Runs a OpenFoam Utility and analyzes the output.  Needs a regular
expression to look for.  The next 3 arguments are the usual OpenFoam
argumens (<solver> <directory> <case>) and passes them on (plus
additional arguments).  Output is sent to stdout and a logfile inside
the case directory (PyFoamUtility.logfile).  The Directory
PyFoamUtility.analyzed contains a file test with the information of
the regexp (the pattern groups).
        """

        PyFoamApplication.__init__(self,
                                   exactNr=False,
                                   args=args,
                                   description=description,
                                   **kwargs)

    def addOptions(self):
        self.parser.add_option("-r",
                               "--regexp",
                               action="append",
                               dest="regexp",
                               help="The regular expression to look for. With more than one the expresions get appended")

        self.parser.add_option("-n",
                               "--name",
                               type="string",
                               dest="name",
                               default="test",
                               help="The name for the resulting file")

        self.parser.add_option("--echo",
                               action="store_true",
                               dest="echo",
                               default=False,
                               help="Echo the result file after the run")

        self.parser.add_option("--silent",
                               action="store_true",
                               dest="silent",
                               default=False,
                               help="Don't print the output of the utility to the console")

    def run(self):
        if self.opts.regexp==None:
            self.parser.error("Regular expression needed")

        cName=self.parser.casePath()

        run=UtilityRunner(argv=self.parser.getArgs(),
                          silent=self.opts.silent,
                          server=True)

        for i,r in enumerate(self.opts.regexp):
            name=self.opts.name
            if len(self.opts.regexp)>1:
                name="%s_%d" % (name,i)
            run.add(name,r)

        self.addToCaseLog(cName,"Starting")

        run.start()

        self.addToCaseLog(cName,"Ending")

        allData=run.data

        for i,r in enumerate(self.opts.regexp):
            name=self.opts.name
            if len(self.opts.regexp)>1:
                name="%s_%d" % (name,i)

            fn=path.join(run.getDirname(),name)

            data=run.analyzer.getData(name)
            allData["analyzed"][name]=data

            if data==None:
                print_(sys.argv[0]+": No data found for expression",r)
            else:
                if self.opts.echo:
                    fh=open(fn)
                    print_(fh.read())
                    fh.close()
                else:
                    print_(sys.argv[0]+": Output written to file "+fn)

        self.setData(allData)

# Should work with Python3 and Python2
