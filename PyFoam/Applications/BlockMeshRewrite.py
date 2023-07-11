"""
Application-class that implements pyFoamBlockMeshRewrite.py
"""
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from PyFoam.Basics.RestructuredTextHelper import RestructuredTextHelper
from PyFoam.Basics.FoamOptionParser import Subcommand

from PyFoam.RunDictionary.BlockMesh import BlockMesh

from os import path
import sys,re

from PyFoam.ThirdParty.six import print_

class BlockMeshRewrite(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
This utility manipulates blockMeshDict. Manipulation happens on a textual basis .
This means that the utility assumes that the blockMeshDict is sensibly formated
(this means for instance that there is only one block/vertex per line and they only
go over one line
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog COMMAND <blockMeshDict>",
                                   changeVersion=False,
                                   subcommands=True,
                                   **kwargs)

    def addOptions(self):
        # Building the subcommands
        refineCmd=Subcommand(name='refine',
                             help="Refine the blocks in the blockMesh by multiplying them with a fixed factor",
                             aliases=("resolution",),
                             nr=0,
                             exactNr=False)
        self.parser.addSubcommand(refineCmd)
        refineGrp=OptionGroup(refineCmd.parser,
                              "Refinement",
                              "Parameters for refining the mesh")
        refineCmd.parser.add_option_group(refineGrp)
        refineGrp.add_option("--factor",
                             action="store",
                             dest="factor",
                             default=None,
                             help="Factor to scale the mesh with. Either a single scalar to multiply all directions with or three comma-separated scalars (one for each direction). This option is required")
        refineGrp.add_option("--offsets",
                             action="store",
                             dest="offsets",
                             default=None,
                             help="Offset to add to the scaling. Three comma-separated scalars (one for each direction). Not required")

        numberCmd=Subcommand(name='number',
                             help="Add comments with the vertex numbers to the mesh-file",
                             aliases=("count",),
                             nr=0,
                             exactNr=False)
        self.parser.addSubcommand(numberCmd)
        numberGrp=OptionGroup(numberCmd.parser,
                              "Numbering",
                              "Parameters for the numbering of the vertices")
        numberCmd.parser.add_option_group(numberGrp)
        numberGrp.add_option("--prefix",
                             action="store",
                             dest="numberPrefix",
                             default="Vertex Nr.",
                             help="Text to be added before the vertex number. Default: %default")

        stripCmd=Subcommand(name='stripNumber',
                             help="Remove comments after the vertex number",
                             aliases=("strip",),
                             nr=0,
                             exactNr=False)
        self.parser.addSubcommand(stripCmd)

        mergeCmd=Subcommand(name='mergeVertices',
                            help="Merge",
                            aliases=("add",),
                            nr=0,
                            exactNr=False)
        self.parser.addSubcommand(mergeCmd)
        mergeGrp=OptionGroup(mergeCmd.parser,
                              "Merging",
                              "Parameters for the merging of vertices")
        mergeCmd.parser.add_option_group(mergeGrp)
        mergeGrp.add_option("--other-mesh",
                             action="store",
                             dest="otherMesh",
                             default=None,
                             help="The blockMeshDict from which vertexes are to be added")

        renumberCmd=Subcommand(name='renumberVertices',
                            help="Renumber vertices so that they match the vertices of another blockMeshDict",
                            aliases=("add",),
                            nr=0,
                            exactNr=False)
        self.parser.addSubcommand(renumberCmd)
        renumberGrp=OptionGroup(renumberCmd.parser,
                              "Merging",
                              "Parameters for the merging of vertices")
        renumberCmd.parser.add_option_group(renumberGrp)
        renumberGrp.add_option("--other-mesh",
                             action="store",
                             dest="otherMesh",
                             default=None,
                             help="The blockMeshDict from which numbers are to be taken and renumbered")

        normalizeCmd=Subcommand(name='normalizePatches',
                            help="Normalize patches by rotating the vertices in the patch so that the smalles number comes first",
                            aliases=("rotate",),
                            nr=0,
                            exactNr=False)
        self.parser.addSubcommand(normalizeCmd)

        for cmd in [refineCmd,numberCmd,stripCmd,mergeCmd,renumberCmd,
                    normalizeCmd]:
            inputGrp=OptionGroup(cmd.parser,
                                 "blockMeshDict In",
                                 "Where the blockMeshDict is read from")
            cmd.parser.add_option_group(inputGrp)

            inputGrp.add_option("--from-stdin",
                                action="store_true",
                                dest="stdin",
                                default=False,
                                help="Instead of reading from file read from stdin (used for piping into other commands)")

            outputGrp=OptionGroup(cmd.parser,
                                  "blockMeshDict Out",
                                  "Where the processed blockMeshDict is written to")
            cmd.parser.add_option_group(outputGrp)
            outputGrp.add_option("--to-stdout",
                                 action="store_true",
                                 dest="stdout",
                                 default=False,
                                 help="Instead of writing to file write to stdout (used for piping into other commands)")
            outputGrp.add_option("--overwrite",
                                 action="store_true",
                                 dest="overwrite",
                                 default=False,
                                 help="Overwrite the original file")
            outputGrp.add_option("--outfile",
                                 action="store",
                                 dest="outfile",
                                 default=None,
                                 help="File to write the result to")

    def run(self):
        if self.opts.stdin:
            if len(self.parser.getArgs())>0:
                self.error("If --from-stdin specified no arguments are allowed but we have",self.parser.getArgs())
        else:
            if len(self.parser.getArgs())!=1:
                self.error("Only one blockMeshDict can be specified")

        outOptNr=(1 if self.opts.stdout else 0)+(1 if self.opts.overwrite else 0)+(1 if self.opts.outfile else 0)

        if outOptNr!=1:
            self.error("Specify one (and only one) of the options '--to-stdout', '--overwrite', '--outfile'")
        if self.opts.stdin and self.opts.overwrite:
            self.error("'--from-stdin' and '--overwrite' are incompatible")

        if self.opts.stdin:
            srcMesh=BlockMesh(self.stdin)
        else:
            srcMesh=BlockMesh(self.parser.getArgs()[0])

        if self.cmdname=="refine":
            if self.opts.factor==None:
                self.error("Unspecified option '--factor'")
            try:
                factor=float(self.opts.factor)
            except ValueError:
                factor=eval("("+self.opts.factor+")")
                if len(factor)!=3:
                    self.error("--factor must either be a scalar or 3 comma-separated values")
            offset=(0,0,0)
            if self.opts.offsets:
                offset=eval("("+self.opts.offsets+")")
            srcMesh.refineMesh(factor,offset,getContent=True,addOld=False)
        elif self.cmdname=="number":
            srcMesh.numberVertices(self.opts.numberPrefix)
        elif self.cmdname=="stripNumber":
            srcMesh.stripVertexNumber()
        elif self.cmdname=="mergeVertices":
            if self.opts.otherMesh==None:
                self.error("'--other-mesh' has to be specified for this")
            srcMesh.mergeVertices(self.opts.otherMesh)
        elif self.cmdname=="renumberVertices":
            if self.opts.otherMesh==None:
                self.error("'--other-mesh' has to be specified for this")
            srcMesh.renumberVertices(self.opts.otherMesh)
        elif self.cmdname=="normalizePatches":
            srcMesh.normalizePatches()
        else:
            self.error("Unimplemented sub-command",self.cmdname)

        if self.opts.stdout:
            sys.stdout.write(srcMesh.content)
        elif self.opts.overwrite:
            srcMesh.writeFile()
        else:
            srcMesh.writeFileAs(self.opts.outfile)

# Should work with Python3 and Python2
