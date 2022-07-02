"""
Class that implements common functionality for collecting plot-lines
"""

import re
from os import path
from optparse import OptionGroup

from PyFoam.Basics.CustomPlotInfo import readCustomPlotInfo,resetCustomCounter
from PyFoam.ThirdParty.six import print_

ruleList=[]

def addRegexpInclude(option,opt,value,parser,*args,**kwargs):
    ruleList.append((True,value))

def addRegexpExclude(option,opt,value,parser,*args,**kwargs):
    ruleList.append((False,value))


class CommonPlotLines(object):
    """ This class collects the lines that should be plotted
    """

    def __init__(self):
        self.lines_=[]

    def plotLines(self):
        return self.lines_

    def addPlotLine(self,line):
        """Add a single line"""
        self.lines_+=readCustomPlotInfo(line)

    def addPlotLines(self,lines,name=None):
        """Adds a list of lines"""
        if lines:
            for i,l in enumerate(lines):
                if name:
                    useName="%s_%i" % (name,i)
                else:
                    useName=None
                self.lines_+=readCustomPlotInfo(l,useName=useName)

    def addFileRegexps(self,fName):
        """Adds the lines from a file to the custom regular expressions
        :param fName: The name of the file"""
        f=open(fName)
        txt=f.read()
        f.close()
        self.lines_+=readCustomPlotInfo(txt)

    def addOptions(self):
        grp=OptionGroup(self.parser,
                        "Regular expression",
                        "Where regular expressions for custom plots are found")

        grp.add_option("--custom-regexp",
                       action="append",
                       default=None,
                       dest="customRegex",
                       help="Add a custom regular expression to be plotted (can be used more than once)")

        grp.add_option("--regexp-file",
                       action="append",
                       default=None,
                       dest="regexpFile",
                       help="A file with regulare expressions that are treated like the expressions given with --custom-regexp")

        grp.add_option("--no-auto-customRegexp",
                       action="store_false",
                       default=True,
                       dest="autoCustom",
                       help="Do not automatically load the expressions from the file customRegexp")
        grp.add_option("--no-parent-customRegexp",
                       action="store_false",
                       default=True,
                       dest="parentCustom",
                       help="Do not look for additional customRegexp in upward directories")

        grp.add_option("--dump-custom-regegexp",
                       action="store_true",
                       default=False,
                       dest="dumpCustomRegexp",
                       help="Dump the used regular expressions in a format suitable to put into a customRegexp-file and finish the program")

        grp.add_option("--list-custom-Regexp",
                       action="store_true",
                       default=False,
                       dest="listCustomRegexp",
                       help="List the customRegexp by name. A * before the name means that it is enabled")

        grp.add_option("--include-regexp-fitting",
                       action="callback",
                       callback=addRegexpInclude,
                       type="string",
                       help="Add all the customRegex whose name fits this regular expression. This option can be used as often as liked ")

        grp.add_option("--exclude-regexp-fitting",
                       action="callback",
                       callback=addRegexpExclude,
                       type="string",
                       help="Remove all the customRegex whose name fits this regular expression. This option can be used as often as liked ")

        self.parser.add_option_group(grp)

        grp2=OptionGroup(self.parser,
                        "Data files",
                        "How data files are written")
        grp2.add_option("--single-data-files-only",
                       action="store_true",
                       default=False,
                       dest="singleDataFilesOnly",
                       help="Don't create consecutive data files 'value', 'value_2', 'value_3' etc but put all the data into a single file")
        grp2.add_option("--write-files",
                        action="store_true",
                        default=False,
                        dest="writeFiles",
                        help="Writes the parsed data to files")

        self.parser.add_option_group(grp2)

        grp3 = OptionGroup(self.parser,
                           "Data reduction",
                           "How data will be reduced to less numbers if the amount of data points becomes to large")
        grp3.add_option("--split-data-points-threshold",
                        action="store",
                        default=2048,
                        dest="splitDataPointsThreshold",
                        type="int",
                        help="If the number of data points exceeds the threshold then the number of data points is reduced. Default: %default")
        grp3.add_option("--fraction-unchanged-by-splitting",
                        action="store",
                        default=0.2,
                        dest="split_fraction_unchanged",
                        type="float",
                        help="Fraction of data points (at the end) that are not reduced. Default: %default")
        grp3.add_option("--no-split-data-points",
                        action="store_false",
                        default=True,
                        dest="doSplitDataPoints",
                        help="Do no do the splitting of data")

        self.parser.add_option_group(grp3)

    def processPlotLineOptions(self,autoPath=None):
        """Process the options that have to do with plot-lines"""

        # make sure that every object starts with a new batch
        resetCustomCounter()

        self.addPlotLines(self.opts.customRegex)

        if self.opts.regexpFile!=None:
            for f in self.opts.regexpFile:
                print_(" Reading regular expressions from",f)
                self.addFileRegexps(f)


        if autoPath!=None and  self.opts.autoCustom:
            ap=path.abspath(autoPath)
            dirs=[ap]
            if self.opts.parentCustom:
                while path.dirname(ap)!=ap:
                    ap=path.dirname(ap)
                    dirs=[ap]+dirs
            # add additional paths to the current directory
            if path.realpath(autoPath)!=path.os.getcwd():
                common=path.commonprefix([path.realpath(autoPath),path.os.getcwd()])
                if common==path.os.getcwd():
                    parts=path.split(path.relpath(autoPath,path.os.getcwd()))
                    dirs=reversed([path.join(*([path.os.getcwd()]+list(parts[:i+1]))) for i in range(len(parts))])

            for d in dirs:
                autoFile=path.join(d,"customRegexp")
                if path.exists(autoFile):
                    print_(" Reading regular expressions from",autoFile)
                    self.addFileRegexps(autoFile)
                    #                    break

        for include,expr in ruleList:
            rexp=re.compile(expr)
            for l in self.lines_:
                if rexp.search(l.id):
                    if include:
                        l.enabled=True
                    else:
                        l.enabled=False

        if self.opts.dumpCustomRegexp:
            print_("\nDumping customRegexp:\n")
            for l in self.lines_:
                print_(l)
            return -1

        if self.opts.listCustomRegexp:
            print_("\nListing the customRegexp:\n")
            for l in self.lines_:
                if l.enabled:
                    prefix="*"
                else:
                    prefix=" "

                print_(prefix,l.id)

            if len(ruleList)>0:
                print_("\nAccording to list of rules:")
                for incl,expr in ruleList:
                    if incl:
                        prefix="Include"
                    else:
                        prefix="Exclude"
                    print_(prefix,"matching",'"%s"' % expr)

            return -1

# Should work with Python3 and Python2
