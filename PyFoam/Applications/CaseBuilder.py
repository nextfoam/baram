"""
Application-class that implements pyFoamCaseBuilder.py
"""
from optparse import OptionGroup
from os import path
import shutil

from .PyFoamApplication import PyFoamApplication
from .CaseBuilderBackend import CaseBuilderFile
from .CommonCaseBuilder import CommonCaseBuilder

from PyFoam.Error import error

from PyFoam.ThirdParty.six import print_

class CaseBuilder(PyFoamApplication,
                  CommonCaseBuilder):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Gets a XML-file that describes how to build a case from a case
template and some parameters
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog <DescriptionFile>",
                                   interspersed=True,
                                   nr=0,
                                   exactNr=False,
                                   **kwargs)

    def addOptions(self):
        info=OptionGroup(self.parser,
                         "Information",
                         "Information about the case")
        self.parser.add_option_group(info)

        info.add_option("--short-description",
                        action="store_true",
                        dest="short",
                        default=False,
                        help="Print a short description of the case and exit")

        info.add_option("--arguments",
                        action="store_true",
                        dest="args",
                        default=False,
                        help="Describes the additional arguments")

        info.add_option("--help-text",
                        action="store_true",
                        dest="help",
                        default=False,
                        help="Prints the help text in the description file")

        info.add_option("--boundaries",
                        action="store_true",
                        dest="bounds",
                        default=False,
                        help="Describes the boundaries")

        info.add_option("--long-description",
                        action="store_true",
                        dest="long",
                        default=False,
                        help="Print a long description of the case and exit")

        CommonCaseBuilder.addOptions(self)

        how=OptionGroup(self.parser,
                         "How",
                         "How the case should be built")
        self.parser.add_option_group(how)

        how.add_option("--force",
                        action="store_true",
                        dest="force",
                        default=False,
                        help="Remove the case-directory if it exists")

    def printTitle(self,title):
        print_()
        print_(title)
        print_("="*len(title))

    def run(self):
        if self.pathInfo():
            return

        if len(self.parser.getArgs())<1:
            error("No description file given")

        fName=self.searchDescriptionFile(self.parser.getArgs()[0])

        desc=CaseBuilderFile(fName)

        print_("Read case description",desc.name())

        stopIt=False

        if self.opts.long:
            self.opts.short=True
            self.opts.args=True
            self.opts.bounds=True
            self.opts.help=True

        if self.opts.short:
            print_()
            print_("Description:      ",desc.description())
            print_("Template:         ",desc.templatePath())
            print_("Initial Condition:",desc.initialDir())
            stopIt=True

        if self.opts.help:
            self.printTitle("Help")
            print_(desc.helpText())
            stopIt=True

        if self.opts.args:
            args=desc.arguments()
            mLen=max(*list(map(len,args)))
            aDesc=desc.argumentDescriptions()
            format="%%%ds : %%s" % mLen

            self.printTitle("Arguments")
            for a in args:
                print_(format % (a,aDesc[a]))
            stopIt=True

        if self.opts.bounds:
            bounds=desc.boundaries()
            mLen=max(*list(map(len,bounds)))
            bDesc=desc.boundaryDescriptions()
            bPat=desc.boundaryPatternDict()
            format="%%%ds : %%s \n\tPattern: '%%s'" % mLen

            self.printTitle("Boundaries")
            for i,a in enumerate(bounds):
                print_(format % (a,bDesc[a],bPat[a]))
            stopIt=True

        if stopIt:
            print_()
            print_("Not doing anything")
            return

        args=desc.arguments()

        if len(self.parser.getArgs())<2:
            error("Missing a casename:",self.buildUsage(args))

        cName=self.parser.getArgs()[1]
        if len(self.parser.getArgs())!=len(args)+2:
            error("Wrong number of arguments:",self.buildUsage(args))

        aDict={}
        for i,a in enumerate(args):
            tmp=self.parser.getArgs()[2+i]
            if (tmp[0]=='"' or tmp[0]=="'") and tmp[0]==tmp[-1]:
                tmp=tmp[1:-1]
            aDict[a]=tmp

        if path.exists(cName):
            if self.opts.force:
                shutil.rmtree(cName)
            else:
                error("Case directory",cName,"already exists")

        print_("Building case",cName)

        msg=desc.verifyArguments(aDict)
        if msg:
            error("Error verifying arguments:",msg)

        desc.buildCase(cName,aDict)

    def buildUsage(self,args):
        usage="<casename>"
        for a in args:
            usage+=" <"+a+">"
        return usage

# Should work with Python3 and Python2
