"""
Application-class that implements pyFoamCopyLastToFirst.py
"""

from .PyFoamApplication import PyFoamApplication

from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory

from PyFoam.Error import error

from PyFoam.ThirdParty.six import print_

class CopyLastToFirst(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Copies the contents of the last time-step of the source case to the
first time-step of the destination case (thus using it as initial
conditions)

Whether or not the data fits the destination case is not the problem
of this script"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <source caseDirectory> <destination caseDirectory>",
                                   interspersed=True,
                                   changeVersion=False,
                                   nr=2,
                                   **kwargs)

    def addOptions(self):
        self.parser.add_option("--no-overwrite",
                               action="store_false",
                               dest="overwrite",
                               default=True,
                               help="Don't overwrite fields that are already present")
        self.parser.add_option("--must-exist",
                               action="store_true",
                               dest="mustExist",
                               default=False,
                               help="Only copy fields if they already exist in the destination")
        self.parser.add_option("--purge",
                               action="store_true",
                               dest="purge",
                               default=False,
                               help="Remove all files in the destination directory before running")
        self.parser.add_option("--exclude",
                               action="append",
                               default=None,
                               dest="exclude",
                               help="Patterns of files that should be excluded from copying")
        self.parser.add_option("--include",
                               action="append",
                               default=None,
                               dest="include",
                               help="Patterns of files that should be include from copying (default is all. If this option is set ONLY the specified files will be copied)")
        self.parser.add_option("--silent",
                               action="store_false",
                               dest="verbose",
                               default=True,
                               help="Don't do any output")

    def run(self):
        if len(self.parser.getArgs())!=2:
            error("Need two arguments.",len(self.parser.getArgs()),"found")

        sName=self.parser.getArgs()[0]
        dName=self.parser.getArgs()[1]

        if self.opts.include==None:
            include=["*"]
        else:
            include=self.opts.include

        if self.opts.exclude==None:
            exclude=[]
        else:
            exclude=self.opts.exclude

        source=SolutionDirectory(sName,archive=None,paraviewLink=False)
        dest=SolutionDirectory(dName,archive=None,paraviewLink=False)

        sDir=source[-1]
        dDir=dest[0]

        if self.opts.verbose:
            print_("   Copying from source-time",sDir.baseName(),"to destination-time",dDir.baseName())

        copied=dDir.copy(sDir,
                         include=include,exclude=exclude,
                         overwrite=self.opts.overwrite,
                         mustExist=self.opts.mustExist,
                         purge=self.opts.purge)

        if self.opts.verbose:
            if len(copied)>0:
                print_("  Copied the fields",end=" ")
                for v in copied:
                    print_(v,end=" ")
                print_()
            else:
                print_("  Nothing copied")

        self.addToCaseLog(dest.name,"From",sDir.name,"to",dDir.name)

# Should work with Python3 and Python2
