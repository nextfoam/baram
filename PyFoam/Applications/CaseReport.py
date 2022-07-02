#  ICE Revision: $Id$
"""
Application class that implements pyFoamCasedReport.py
"""

import sys
from optparse import OptionGroup

from fnmatch import fnmatch

from .PyFoamApplication import PyFoamApplication
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.RunDictionary.BoundaryDict import BoundaryDict
from PyFoam.RunDictionary.MeshInformation import MeshInformation
from PyFoam.RunDictionary.ParsedParameterFile import PyFoamParserError,ParsedBoundaryDict,ParsedParameterFile
from PyFoam.Basics.RestructuredTextHelper import RestructuredTextHelper
from PyFoam.Basics.DataStructures import DictProxy,Field

from PyFoam.Error import error,warning

from PyFoam.ThirdParty.six import print_,iteritems,string_types

from math import log10,ceil
from os import path

class CaseReport(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Produces human-readable reports about a case. Attention: the amount of
information in the reports is limited. The truth is always in the
dictionary-files.

The format of the output is restructured-text so it can be run through
a postprocessor like rst2tex or rst2html to produce PDF or HTML
respectivly
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <casedir>",
                                   nr=1,
                                   changeVersion=False,
                                   interspersed=True,
                                   **kwargs)

    def addOptions(self):
        report=OptionGroup(self.parser,
                           "Reports",
                           "What kind of reports should be produced")
        self.parser.add_option_group(report)
        select=OptionGroup(self.parser,
                           "Selection",
                           "Which data should be used for the reports")
        self.parser.add_option_group(select)
        internal=OptionGroup(self.parser,
                             "Internal",
                             "Details of the parser")
        self.parser.add_option_group(internal)

        format=OptionGroup(self.parser,
                             "Formatting",
                             "Restructured Text formatting")
        self.parser.add_option_group(format)

        format.add_option("--heading-level",
                          action="store",
                          type="int",
                          default=2,
                          dest="headingLevel",
                          help="Default level of the headings. Valid values from 0 to 5. Default: %default")

        output=OptionGroup(self.parser,
                             "Output",
                             "How Output should be generated")
        self.parser.add_option_group(output)

        output.add_option("--file",
                          action="store",
                          default=None,
                          dest="file",
                          help="Write the output to a file instead of the console")

        report.add_option("--full-report",
                          action="store_true",
                          default=False,
                          dest="all",
                          help="Print all available reports at once")

        report.add_option("--short-bc-report",
                          action="store_true",
                          default=False,
                          dest="shortBCreport",
                          help="Gives a short overview of the boundary-conditions in the case")

        report.add_option("--long-bc-report",
                          action="store_true",
                          default=False,
                          dest="longBCreport",
                          help="Gives a full overview of the boundary-conditions in the case")

        report.add_option("--dimensions",
                          action="store_true",
                          default=False,
                          dest="dimensions",
                          help="Show the dimensions of the fields")

        report.add_option("--internal-field",
                          action="store_true",
                          default=False,
                          dest="internal",
                          help="Show the internal value of the fields (the initial conditions)")

        report.add_option("--linear-solvers",
                          action="store_true",
                          default=False,
                          dest="linearSolvers",
                          help="Print the linear solvers and their tolerance")

        report.add_option("--relaxation-factors",
                          action="store_true",
                          default=False,
                          dest="relaxationFactors",
                          help="Print the relaxation factors (if there are any)")

        select.add_option("--time",
                          action="store",
                          type="float",
                          default=None,
                          dest="time",
                          help="Time to use as the basis for the reports")

        select.add_option("--region",
                          dest="region",
                          default=None,
                          help="Do the report for a special region for multi-region cases")

        select.add_option("--all-regions",
                          dest="allRegions",
                          action="store_true",
                          default=False,
                          help="Do the report for all regions for multi-region cases")

        select.add_option("--parallel",
                          action="store_true",
                          default=False,
                          dest="parallel",
                          help="Get times from the processor-directories")

        internal.add_option("--long-field-threshold",
                            action="store",
                            type="int",
                            default=100,
                            dest="longlist",
                            help="Fields that are longer than this won't be parsed, but read into memory (and compared as strings). Default: %default")
        internal.add_option("--no-do-macro-expansion",
                          action="store_false",
                          default=True,
                          dest="doMacros",
                          help="Don't expand macros with $ and # in the field-files")

        internal.add_option("--treat-binary-as-ascii",
                          action="store_true",
                          default=False,
                          dest="treatBinaryAsASCII",
                          help="Try to treat binary dictionaries as ASCII anyway")

        internal.add_option("--no-treat-boundary-binary-as-ascii",
                          action="store_false",
                          default=True,
                          dest="boundaryTreatBinaryAsASCII",
                          help="If 'boundary'-files are written as binary read them as such (default assumes that these files are ASCII whatever the header says)")

        select.add_option("--patches",
                          action="append",
                          default=None,
                          dest="patches",
                          help="Patches which should be processed (pattern, can be used more than once)")

        select.add_option("--exclude-patches",
                          action="append",
                          default=None,
                          dest="expatches",
                          help="Patches which should not be processed (pattern, can be used more than once)")

        report.add_option("--processor-matrix",
                          action="store_true",
                          default=False,
                          dest="processorMatrix",
                          help="Prints the matrix how many faces from one processor interact with another")

        report.add_option("--case-size",
                          action="store_true",
                          default=False,
                          dest="caseSize",
                          help="Report the number of cells, points and faces in the case")

        report.add_option("--decomposition",
                               action="store_true",
                               default=False,
                               dest="decomposition",
                               help="Reports the size of the parallel decomposition")

    def run(self):
        oldStdout=None

        try:
            if self.opts.file:
                oldStdout=sys.stdout
                if isinstance(self.opts.file,string_types):
                    sys.stdout=open(self.opts.file,"w")
                else:
                    sys.stdout=self.opts.file

            if self.opts.allRegions:
                sol=SolutionDirectory(self.parser.getArgs()[0],
                                      archive=None,
                                      parallel=self.opts.parallel,
                                      paraviewLink=False)
                for r in sol.getRegions():
                    self.doRegion(r)
            else:
                self.doRegion(self.opts.region)
        finally:
            if oldStdout:
                sys.stdout=oldStdout

    def doRegion(self,theRegion):
        ReST=RestructuredTextHelper(defaultHeading=self.opts.headingLevel)

        if self.opts.allRegions:
            print_(ReST.buildHeading("Region: ",theRegion,level=self.opts.headingLevel-1))

        sol=SolutionDirectory(self.parser.getArgs()[0],
                              archive=None,
                              parallel=self.opts.parallel,
                              paraviewLink=False,
                              region=theRegion)

        if self.opts.all:
            self.opts.caseSize=True
            self.opts.shortBCreport=True
            self.opts.longBCreport=True
            self.opts.dimensions=True
            self.opts.internal=True
            self.opts.linearSolvers=True
            self.opts.relaxationFactors=True
            self.opts.processorMatrix=True
            self.opts.decomposition=True

        if self.opts.time:
            try:
                self.opts.time=sol.timeName(sol.timeIndex(self.opts.time,minTime=True))
            except IndexError:
                error("The specified time",self.opts.time,"doesn't exist in the case")
            print_("Using time t="+self.opts.time+"\n")

        needsPolyBoundaries=False
        needsInitialTime=False

        if self.opts.longBCreport:
            needsPolyBoundaries=True
            needsInitialTime=True
        if self.opts.shortBCreport:
            needsPolyBoundaries=True
            needsInitialTime=True
        if self.opts.dimensions:
            needsInitialTime=True
        if self.opts.internal:
            needsInitialTime=True
        if self.opts.decomposition:
            needsPolyBoundaries=True

        defaultProc=None
        if self.opts.parallel:
            defaultProc=0

        if needsPolyBoundaries:
            proc=None
            boundary=BoundaryDict(sol.name,
                                  region=theRegion,
                                  time=self.opts.time,
                                  treatBinaryAsASCII=self.opts.boundaryTreatBinaryAsASCII,
                                  processor=defaultProc)

            boundMaxLen=0
            boundaryNames=[]
            for b in boundary:
                if b.find("procBoundary")!=0:
                    boundaryNames.append(b)
            if self.opts.patches!=None:
                tmp=boundaryNames
                boundaryNames=[]
                for b in tmp:
                    for p in self.opts.patches:
                        if fnmatch(b,p):
                            boundaryNames.append(b)
                            break

            if self.opts.expatches!=None:
                tmp=boundaryNames
                boundaryNames=[]
                for b in tmp:
                    keep=True
                    for p in self.opts.expatches:
                        if fnmatch(b,p):
                            keep=False
                            break
                    if keep:
                        boundaryNames.append(b)

            for b in boundaryNames:
                boundMaxLen=max(boundMaxLen,len(b))
            boundaryNames.sort()

        if self.opts.time==None:
            procTime="constant"
        else:
            procTime=self.opts.time

        if needsInitialTime:
            fields={}

            if self.opts.time==None:
                try:
                    time=sol.timeName(0)
                except IndexError:
                    error("There is no timestep in the case")
            else:
                time=self.opts.time

            tDir=sol[time]

            nameMaxLen=0

            for f in tDir:
                try:
                    fields[f.baseName()]=f.getContent(listLengthUnparsed=self.opts.longlist,
                                                      treatBinaryAsASCII=self.opts.treatBinaryAsASCII,
                                                      doMacroExpansion=self.opts.doMacros)
                    nameMaxLen=max(nameMaxLen,len(f.baseName()))
                except PyFoamParserError:
                    e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                    warning("Couldn't parse",f.name,"because of an error:",e," -> skipping")

            fieldNames=list(fields.keys())
            fieldNames.sort()

        if self.opts.caseSize:
            print_(ReST.heading("Size of the case"))

            nFaces=0
            nPoints=0
            nCells=0
            if self.opts.parallel:
                procs=list(range(sol.nrProcs()))
                print_("Accumulated from",sol.nrProcs(),"processors")
            else:
                procs=[None]

            for p in procs:
                info=MeshInformation(sol.name,
                                     processor=p,
                                     region=theRegion,
                                     time=self.opts.time)
                nFaces+=info.nrOfFaces()
                nPoints+=info.nrOfPoints()
                try:
                    nCells+=info.nrOfCells()
                except:
                    nCells="Not available"
            tab=ReST.table()
            tab[0]=("Faces",nFaces)
            tab[1]=("Points",nPoints)
            tab[2]=("Cells",nCells)
            print_(tab)

        if self.opts.decomposition:
            print_(ReST.heading("Decomposition"))

            if sol.nrProcs()<2:
                print_("This case is not decomposed")
            else:
                print_("Case is decomposed for",sol.nrProcs(),"processors")
                print_()

                nCells=[]
                nFaces=[]
                nPoints=[]
                for p in sol.processorDirs():
                    info=MeshInformation(sol.name,
                                         processor=p,
                                         region=theRegion,
                                         time=self.opts.time)
                    nPoints.append(info.nrOfPoints())
                    nFaces.append(info.nrOfFaces())
                    nCells.append(info.nrOfCells())

                digits=int(ceil(log10(max(sol.nrProcs(),
                                          max(nCells),
                                          max(nFaces),
                                          max(nPoints)
                                          ))))+2
                nameLen=max(len("Points"),boundMaxLen)

                tab=ReST.table()
                tab[0]=["CPU"]+list(range(sol.nrProcs()))

                tab.addLine()

                tab[1]=["Points"]+nPoints
                tab[2]=["Faces"]+nFaces
                tab[3]=["Cells"]+nCells
                tab.addLine(head=True)

                nr=3
                for b in boundaryNames:
                    nr+=1
                    tab[(nr,0)]=b
                    for i,p in enumerate(sol.processorDirs()):
                        try:
                            nFaces= ParsedBoundaryDict(sol.boundaryDict(processor=p,
                                                                        region=theRegion,
                                                                        time=self.opts.time),
                                                       treatBinaryAsASCII=self.opts.boundaryTreatBinaryAsASCII
                                                       )[b]["nFaces"]
                        except IOError:
                            nFaces= ParsedBoundaryDict(sol.boundaryDict(processor=p,
                                                                        region=theRegion),
                                                       treatBinaryAsASCII=self.opts.boundaryTreatBinaryAsASCII
                                                       )[b]["nFaces"]
                        except KeyError:
                            nFaces=0

                        tab[(nr,i+1)]=nFaces

                print_(tab)

        if self.opts.longBCreport:
            print_(ReST.heading("The boundary conditions for t =",time))

            for b in boundaryNames:
                print_(ReST.buildHeading("Boundary: ",b,level=self.opts.headingLevel+1))
                bound=boundary[b]
                print_(":Type:\t",bound["type"])
                if "physicalType" in bound:
                    print_(":Physical:\t",bound["physicalType"])
                print_(":Faces:\t",bound["nFaces"])
                print_()
                heads=["Field","type"]
                tab=ReST.table()
                tab[0]=heads
                tab.addLine(head=True)
                for row,fName in enumerate(fieldNames):
                    tab[(row+1,0)]=fName
                    f=fields[fName]
                    if "boundaryField" not in f:
                        tab[(row+1,1)]="Not a field file"
                    elif b not in f["boundaryField"]:
                        tab[(row+1,1)]="MISSING !!!"
                    else:
                        bf=f["boundaryField"][b]

                        for k in bf:
                            try:
                                col=heads.index(k)
                            except ValueError:
                                col=len(heads)
                                tab[(0,col)]=k
                                heads.append(k)
                            cont=str(bf[k])
                            if type(bf[k])==Field:
                                if bf[k].isBinary():
                                    cont= bf[k].binaryString()

                            if cont.find("\n")>=0:
                                tab[(row+1,col)]=cont[:cont.find("\n")]+"..."
                            else:
                                tab[(row+1,col)]=cont
                print_(tab)

        if self.opts.shortBCreport:
            print_(ReST.heading("Table of boundary conditions for t =",time))

            types={}
            hasPhysical=False
            for b in boundary:
                if "physicalType" in boundary[b]:
                    hasPhysical=True

                types[b]={}

                for fName in fields:
                    f=fields[fName]
                    try:
                        if b not in f["boundaryField"]:
                            types[b][fName]="MISSING"
                        else:
                            types[b][fName]=f["boundaryField"][b]["type"]
                    except KeyError:
                        types[b][fName]="Not a field"

            tab=ReST.table()
            tab[0]=[""]+boundaryNames
            tab.addLine()
            tab[(1,0)]="Patch Type"
            for i,b in enumerate(boundaryNames):
                tab[(1,i+1)]=boundary[b]["type"]

            nr=2
            if hasPhysical:
                tab[(nr,0)]="Physical Type"
                for i,b in enumerate(boundaryNames):
                    if "physicalType" in boundary[b]:
                        tab[(nr,i+1)]=boundary[b]["physicalType"]
                nr+=1

            tab[(nr,0)]="Length"
            for i,b in enumerate(boundaryNames):
                tab[(nr,i+1)]=boundary[b]["nFaces"]
            nr+=1
            tab.addLine(head=True)

            for fName in fieldNames:
                tab[(nr,0)]=fName
                for i,b in enumerate(boundaryNames):
                    tab[(nr,i+1)]=types[b][fName]
                nr+=1

            print_(tab)

        if self.opts.dimensions:
            print_(ReST.heading("Dimensions of fields for t =",time))

            tab=ReST.table()
            tab[0]=["Name"]+"[ kg m s K mol A cd ]".split()[1:-1]
            tab.addLine(head=True)
            for i,fName in enumerate(fieldNames):
                f=fields[fName]
                try:
                    dim=str(f["dimensions"]).split()[1:-1]
                except KeyError:
                    dim=["-"]*7
                tab[i+1]=[fName]+dim
            print_(tab)

        if self.opts.internal:
            print_(ReST.heading("Internal value of fields for t =",time))

            tab=ReST.table()
            tab[0]=["Name","Value"]
            tab.addLine(head=True)
            for i,fName in enumerate(fieldNames):
                f=fields[fName]

                try:
                    if f["internalField"].isBinary():
                        val=f["internalField"].binaryString()
                    else:
                        cont=str(f["internalField"])
                        if cont.find("\n")>=0:
                            val=cont[:cont.find("\n")]+"..."
                        else:
                            val=cont
                except KeyError:
                    val="Not a field file"
                tab[i+1]=[fName,val]
            print_(tab)

        if self.opts.processorMatrix:
            print_(ReST.heading("Processor matrix"))

            if sol.nrProcs()<2:
                print_("This case is not decomposed")
            else:
                matrix=[ [0,]*sol.nrProcs() for i in range(sol.nrProcs())]

                for i,p in enumerate(sol.processorDirs()):
                    try:
                        bound=ParsedBoundaryDict(sol.boundaryDict(processor=p,
                                                                  region=theRegion,
                                                                  time=self.opts.time)
                                                 ,treatBinaryAsASCII=self.opts.boundaryTreatBinaryAsASCII)
                    except IOError:
                        bound=ParsedBoundaryDict(sol.boundaryDict(processor=p,
                                                                  treatBinaryAsASCII=self.opts.boundaryTreatBinaryAsASCII,
                                                                  region=theRegion)
                                                 ,treatBinaryAsASCII=self.opts.boundaryTreatBinaryAsASCII)

                    for j in range(sol.nrProcs()):
                        name="procBoundary%dto%d" %(j,i)
                        name2="procBoundary%dto%d" %(i,j)
                        if name in bound:
                            matrix[i][j]=bound[name]["nFaces"]
                        if name2 in bound:
                            matrix[i][j]=bound[name2]["nFaces"]

                print_("Matrix of processor interactions (faces)")
                print_()

                tab=ReST.table()
                tab[0]=["CPU"]+list(range(sol.nrProcs()))
                tab.addLine(head=True)

                for i,col in enumerate(matrix):
                    tab[i+1]=[i]+matrix[i]

                print_(tab)

        if self.opts.linearSolvers:
            print_(ReST.heading("Linear Solvers"))

            linTable=ReST.table()

            fvSol=ParsedParameterFile(path.join(sol.systemDir(),"fvSolution"),
                                      treatBinaryAsASCII=self.opts.treatBinaryAsASCII)
            allInfo={}
            for sName in fvSol["solvers"]:
                raw=fvSol["solvers"][sName]
                info={}
                if type(raw) in [dict,DictProxy]:
                    # fvSolution format in 1.7
                    try:
                        info["solver"]=raw["solver"]
                    except KeyError:
                        info["solver"]="<none>"
                    solverData=raw
                else:
                    info["solver"]=raw[0]
                    solverData=raw[1]

                if type(solverData) in [dict,DictProxy]:
                    try:
                        info["tolerance"]=solverData["tolerance"]
                    except KeyError:
                        info["tolerance"]=1.
                    try:
                        info["relTol"]=solverData["relTol"]
                    except KeyError:
                        info["relTol"]=0.
                else:
                    # the old (pre-1.5) fvSolution-format
                    info["tolerance"]=solverData
                    info["relTol"]=raw[2]

                allInfo[sName]=info

            linTable[0]=["Name","Solver","Abs. Tolerance","Relative Tol."]
            linTable.addLine(head=True)

            nr=0
            for n,i in iteritems(allInfo):
                nr+=1
                linTable[nr]=(n,i["solver"],i["tolerance"],i["relTol"])
            print_(linTable)

        if self.opts.relaxationFactors:
            print_(ReST.heading("Relaxation"))

            fvSol=ParsedParameterFile(path.join(sol.systemDir(),"fvSolution"),
                                      treatBinaryAsASCII=self.opts.treatBinaryAsASCII)
            if "relaxationFactors" in fvSol:
                relax=fvSol["relaxationFactors"]
                tab=ReST.table()
                tab[0]=["Name","Factor"]
                tab.addLine(head=True)
                nr=0
                if "fields" in relax or "equations" in relax:
                    # New syntax
                    for k in ["fields","equations"]:
                        if k in relax:
                            for n,f in iteritems(relax[k]):
                                nr+=1
                                tab[nr]=[k+": "+n,f]
                else:
                    for n,f in iteritems(relax):
                        nr+=1
                        tab[nr]=[n,f]
                print_(tab)
            else:
                print_("No relaxation factors defined for this case")

# Should work with Python3 and Python2
