"""
Class that implements reading vom a pickled file. Every utility that
gets input from a pipe should use it
"""
from optparse import OptionGroup

from PyFoam.ThirdParty.six.moves import cPickle as pickle
from PyFoam.ThirdParty.six import print_

import sys

class CommonPickledDataInput(object):
    """ The class that defines the options for reading from a pickled plot
    """

    def addOptions(self):
        pickled=OptionGroup(self.parser,
                            "Pickled file reading",
                            "Options for reading from a pickled file")
        self.parser.add_option_group(pickled)
        pickled.add_option("--pickled-file",
                           action="store",
                           default=None,
                           dest="pickledFileRead",
                           help="""
File from which the pickled data should be read. If this is set to
'stdin' then the data is read from the standard-input to allow using
the pipe into it. If unset and stdin is not a terminal, then it is
automatically chosen""")

        pickled.add_option("--print-data",
                           action="store_true",
                           default=False,
                           dest="printPickledData",
                           help="print the pickled data after is has been read")

        pickled.add_option("--print-stdout",
                           action="store_true",
                           default=False,
                           dest="printStdout",
                           help="Print the standard-output (if it has been safed into the pickled file)")

    def readPickledData(self):
        if "inputData" in self:
            if self.opts.pickledFileRead:
                self.error("--pickled-file specified, when input data was provided via the Python-API")
            data=self["inputData"]
        else:
            if not self.opts.pickledFileRead:
                if sys.stdin.isatty():
                    self.error("The option --pickled-file has to be set")
                else:
                    self.opts.pickledFileRead="stdin"

            if self.opts.pickledFileRead=="stdin":
                pick=pickle.Unpickler(sys.stdin)
            else:
                pick=pickle.Unpickler(open(self.opts.pickledFileRead,"rb"))
            data=pick.load()
            del pick

        if self.opts.printStdout:
            try:
                print_(data["stdout"])
            except KeyError:
                print_("<No stdout in data>")
        if self.opts.printPickledData:
            import pprint
            printer=pprint.PrettyPrinter()
            printer.pprint(data)

        return data

# Should work with Python3 and Python2
