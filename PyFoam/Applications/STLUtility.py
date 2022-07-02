"""
Application-class that implements pyFoamSTLUtility.py
"""
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from PyFoam.Basics.STLFile import STLFile
from PyFoam.Basics.RestructuredTextHelper import RestructuredTextHelper
from PyFoam.Basics.FoamOptionParser import Subcommand

from os import path
import sys,re

from PyFoam.ThirdParty.six import print_

class STLUtility(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
This utility does some basic manipulations with STL-files
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog COMMAND [<source1.stl> <source2.stl> ...]",
                                   changeVersion=False,
                                   subcommands=True,
                                   **kwargs)

    def addOptions(self):
        # Building the subcommands
        joinCmd=Subcommand(name='join',
                           help="Join STL-files into one",
                           aliases=("cat",),
                           nr=2,
                           exactNr=False)
        self.parser.addSubcommand(joinCmd)

        namesCmd=Subcommand(name='names',
                            help="Report names of patches in the STLs",
                            aliases=("list",),
                            nr=0,
                            exactNr=False)
        self.parser.addSubcommand(
            namesCmd,
            usage="%prog COMMAND [<source.stl> ... ]")

        infoCmd=Subcommand(name='info',
                           help="Reports about the STL-files",
                           aliases=("report",),
                           nr=0,
                           exactNr=False)
        self.parser.addSubcommand(
            infoCmd,
            usage="%prog COMMAND [<source.stl> ... ]")

        removeCmd=Subcommand(name='remove',
                             help="Remove patches from the STL-file",
                             aliases=("erase","blank",),
                             nr=0,
                             exactNr=False)
        self.parser.addSubcommand(
            removeCmd,
            usage="%prog COMMAND [<source.stl>]")

        mergeCmd=Subcommand(name='merge',
                             help="Merge patches and put them into a new patch",
                             aliases=("move",),
                             nr=0,
                             exactNr=False)
        self.parser.addSubcommand(mergeCmd)
        mergeCmd.parser.add_option("--new-patch-name",
                                   action="store",
                                   dest="newName",
                                   default=None,
                                   help="Name of the patch that is added")

        # Add option groups to parsers
        for cmd in [joinCmd,removeCmd,mergeCmd]:
            outOpts=OptionGroup(cmd.parser,
                                "Write Options",
                                "Where the resulting STL is written to")
            outOpts.add_option("--to-stdout",
                               action="store_true",
                               dest="stdout",
                               default=False,
                               help="Instead of writing to file write to stdout (used for piping into other commands)")
            outOpts.add_option("--force-write",
                               action="store_true",
                               dest="forceWrite",
                               default=False,
                               help="Force writing if the file already exists")
            outOpts.add_option("--stl-file",
                               action="store",
                               dest="stlFile",
                               default=None,
                               help="Write to this filename")
            cmd.parser.add_option_group(outOpts)

        for cmd in [namesCmd,infoCmd,removeCmd,mergeCmd]:
            inOpts=OptionGroup(cmd.parser,
                               "Read Options",
                               "Which STLs are read")
            inOpts.add_option("--from-stdin",
                              action="store_true",
                              dest="stdin",
                              default=False,
                              help="Instead of reading from file read from stdin (used for piping into other commands)")
            cmd.parser.add_option_group(inOpts)

        for cmd in [removeCmd,mergeCmd]:
            patchOpts=OptionGroup(cmd.parser,
                                  "Patch selection",
                                  "Which patches to operate on")
            patchOpts.add_option("--patch-name",
                                 action="append",
                                 dest="patchNames",
                                 default=[],
                                 help="Name of the patch to work on. Can be selected more than once")
            patchOpts.add_option("--select-expression",
                                 action="append",
                                 dest="patchExpr",
                                 default=[],
                                 help="Regular expressions fitting the patches. Can be selected more than once")

            cmd.parser.add_option_group(patchOpts)

    def run(self):
        sources=None
        if "stdin" in self.opts.__dict__:
            if self.opts.stdin:
                if len(self.parser.getArgs())>0:
                    self.error("If --from-stdin specified no arguments are allowed but we have",self.parser.getArgs())
                sources=[STLFile(sys.stdin)]
        if sources==None:
            sources=[STLFile(f) for f in self.parser.getArgs()]

        if self.cmdname in ["remove","merge"]:
            if len(sources)!=1:
                self.error("Only one input allowed for",self.cmdname)

        if self.cmdname in ["remove","merge"]:
            if len(self.opts.patchExpr)==0 and len(self.opts.patchNames)==0:
                self.error("Neither --patch-name nor --select-expression specified")
            for e in self.opts.patchExpr:
                expr=re.compile(e)
                for s in sources:
                    for p in s.patchInfo():
                        if expr.match(p["name"]):
                            self.opts.patchNames.append(p["name"])
            if len(self.opts.patchNames)==0:
                self.error("No patches fit the provided regular expressions")

        if self.cmdname in ["remove","join","merge"]:
            # Check whether output is correct
            if self.opts.stdout and self.opts.stlFile:
                self.error("Can't specify --to-stdout and --stl-file at the same time")

            if self.opts.stlFile:
                if path.exists(self.opts.stlFile):
                    if not self.opts.forceWrite:
                        self.error("File",self.opts.stlFile,"does allready exist. Use --force-write to overwrite")
                outputTo=self.opts.stlFile
            elif self.opts.stdout:
                outputTo=sys.stdout
            else:
                self.error("Specify either --to-stdout or --stld-file")

        rst=RestructuredTextHelper()

        if self.cmdname=="names":
            print_(rst.buildHeading("Patch names",level=RestructuredTextHelper.LevelSection))
            for s in sources:
                print_(rst.buildHeading(s.filename(),level=RestructuredTextHelper.LevelSubSection))
                for p in s.patchInfo():
                    print_(p["name"])

        elif self.cmdname=="info":
            print_(rst.buildHeading("Patch info",level=RestructuredTextHelper.LevelSection))
            for s in sources:
                print_(rst.buildHeading(s.filename(),level=RestructuredTextHelper.LevelSubSection))
                tab=rst.table()
                tab[0]=["name","facets","range in file","bounding box"]
                tab.addLine(head=True)
                for i,p in enumerate(s.patchInfo()):
                    tab[(i+1,0)]=p["name"]
                    tab[(i+1,1)]=p["facets"]
                    tab[(i+1,2)]="%d-%d" % (p["start"],p["end"])
                    tab[(i+1,3)]="(%g %g %g) - (%g %g %g)" % tuple(p["min"]+p["max"])

                print_(tab)

        elif self.cmdname=="join":
            result=STLFile()
            for s in sources:
                result+=s

            result.writeTo(outputTo)
        elif self.cmdname=="remove":
            s=sources[0]
            s.erasePatches(self.opts.patchNames)
            s.writeTo(outputTo)
        elif self.cmdname=="merge":
            if self.opts.newName==None:
                self.error("Specify --new-patch-name")
            s=sources[0]
            s.mergePatches(self.opts.patchNames,self.opts.newName)
            s.writeTo(outputTo)
        else:
            self.error("Unimplemented subcommand",self.cmdname)

# Should work with Python3 and Python2
