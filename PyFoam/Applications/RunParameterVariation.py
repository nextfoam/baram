#  ICE Revision: $Id$
"""
Application class that implements pyFoamPrepareCase
"""

from optparse import OptionGroup
from os import path

from .PrepareCase import PrepareCase

from PyFoam.Basics.DataStructures import DictProxy
from PyFoam.Execution.AnalyzedRunner import AnalyzedRunner
from PyFoam.LogAnalysis.BoundingLogAnalyzer import BoundingLogAnalyzer
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.RunDictionary.RegionCases import RegionCases
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
try:
    from PyFoam.Basics.RunDatabase import RunDatabase
    hasDatabase=True
except ImportError:
    hasDatabase=False

from PyFoam.Error import warning

from .CommonPlotLines import CommonPlotLines
from .CommonReportUsage import CommonReportUsage
from .CommonReportRunnerData import CommonReportRunnerData
from .CommonStandardOutput import CommonStandardOutput
from .CommonParallel import CommonParallel
from .CommonServer import CommonServer
from .CommonPrePostHooks import CommonPrePostHooks

from PyFoam.Basics.CustomPlotInfo import resetCustomCounter
from PyFoam.Basics.TimeLineCollection import allLines
from PyFoam.Basics.GeneralPlotTimelines import allPlots

from PyFoam.ThirdParty.six import print_

class RunParameterVariation(PrepareCase,
                            CommonPlotLines,
                            CommonReportUsage,
                            CommonReportRunnerData,
                            CommonParallel,
                            CommonServer,
                            CommonStandardOutput,
                            CommonPrePostHooks):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Takes a template case and a file that specifies the parameters to be varied.
Using the machinery from pyFoamPrepareCase.py it sets up the case with each
parameters and runs the solver on it. Collects the results in a database

The format of the parameter file is a regular OpenFOAM-dictionary file
without a header. There is one required entry: a dictionary with the name
values. Each entry is one parameter to varied. The possible values are in a list.
The entries in the list are either single values or dictionaries. If the entries
are dictionaries then the dictionary values are used. A required entry for 'values'
is 'solver' that specifies at least one solver to be used.

An optional entry for the dictionary is a dictionary called 'defaults'. The values
here are added to the parameters unless being overwritten by the variation values.
This is useful with variation values that are dictionaries"""

        examples="""\
Do all the variations in the template case:

%prog --inplace-execution templateCase parameter.file

One case for every variation and start with the 4th variant

%prog --every-variant-one-case-execution templateCase parameter.file --start=4
        """
        CommonPlotLines.__init__(self)
        PrepareCase.__init__(self,
                             nr=2,
                             usage="%prog <case> <parameterFile>",
                             exactNr=True,
                             args=args,
                             interspersed=True,
                             description=description,
                             examples=examples,
                             **kwargs)

    def addOptions(self):
        CommonReportUsage.addOptions(self)
        CommonReportRunnerData.addOptions(self)
        CommonStandardOutput.addOptions(self)
        CommonParallel.addOptions(self)
        CommonPlotLines.addOptions(self)
        CommonServer.addOptions(self)
        CommonPrePostHooks.addOptions(self)

        PrepareCase.addOptions(self)

        variation=OptionGroup(self.parser,
                              "Parameter variation",
                              "Parameters specific to the parameter variation")
        self.parser.add_option_group(variation)

        variation.add_option("--inplace-execution",
                             action="store_true",
                             dest="inplaceExecution",
                             default=False,
                             help="Do everything in the template case (preparation and execution)")
        variation.add_option("--one-cloned-case-execution",
                             action="store_true",
                             dest="oneClonedCase",
                             default=False,
                             help="Clone to one case and do everything in that case (preparation and execution)")
        variation.add_option("--every-variant-one-case-execution",
                             action="store_true",
                             dest="everyVariantOneCase",
                             default=False,
                             help="Every variation gets its own case (that is not erased)")
        variation.add_option("--no-execute-solver",
                             action="store_true",
                             dest="noExecuteSolver",
                             default=False,
                             help="Only prepare the cases but do not execute the solver")
        variation.add_option("--cloned-case-prefix",
                             action="store",
                             dest="clonedCasePrefix",
                             default=None,
                             help="Prefix of the cloned cases. If unspecified the name of parameter file is used")
        variation.add_option("--cloned-case-postfix",
                             action="store",
                             dest="clonedCasePostfix",
                             default=None,
                             help="Postfix of the cloned cases. If unspecified an empty string. Helps to distinguish different sets of variations")
        variation.add_option("--clone-to-directory",
                             action="store",
                             dest="cloneToDirectory",
                             default=None,
                             help="Directory to clone to. If unspecified use the directory in which the original case resides")
        variation.add_option("--single-variation",
                             action="store",
                             type="int",
                             dest="singleVariation",
                             default=None,
                             help="Single variation to run")
        variation.add_option("--start-variation-number",
                             action="store",
                             type="int",
                             dest="startVariation",
                             default=None,
                             help="Variation number to start with")
        variation.add_option("--end-variation-number",
                             action="store",
                             type="int",
                             dest="endVariation",
                             default=None,
                             help="Variation number to end with")
        variation.add_option("--database",
                             action="store",
                             dest="database",
                             default=None,
                             help="Path to the database. If unset the name of parameter-file appended with '.results' will be used")
        variation.add_option("--create-database",
                             action="store_true",
                             dest="createDatabase",
                             default=False,
                             help="Create a new database file. Fail if it already exists")
        variation.add_option("--auto-create-database",
                             action="store_true",
                             dest="autoCreateDatabase",
                             default=False,
                             help="Create a new database file if it doesn't exist yet'")
        variation.add_option("--list-variations",
                             action="store_true",
                             dest="listVariations",
                             default=False,
                             help="List the selected variations but don't do anything")
        variation.add_option("--no-database-write",
                             action="store_true",
                             dest="noDatabaseWrite",
                             default=False,
                             help="Do not write to the database")

    def printPhase(self,*args):
        out=" ".join([str(a) for a in args])
        print_()
        print_("="*len(out))
        print_(out)
        print_("="*len(out))
        print_()

    def run(self):
        origPath=self.parser.getArgs()[0]
        parameterFile=self.parser.getArgs()[1]

        self.addLocalConfig(origPath)
        self.checkCase(origPath)

        nrModes=(1 if self.opts.inplaceExecution else 0) + \
                (1 if self.opts.oneClonedCase else 0) + \
                (1 if self.opts.listVariations else 0) + \
                (1 if self.opts.everyVariantOneCase else 0)
        if nrModes==0:
            self.error("Specify one of the modes --list-variations, --inplace-execution, --one-cloned-case-execution or --every-variant-one-case-execution")
        elif nrModes>1:
            self.error("The modes --list-variations, --inplace-execution, --one-cloned-case-execution or --every-variant-one-case-execution are mutual exclusive")
        if self.opts.noExecuteSolver:
            if not self.opts.everyVariantOneCase and self.opts.singleVariation==None and not self.opts.listVariations:
                self.error("--no-execute-solver only works with --every-variant-one-case-execution")

        if not self.opts.clonedCasePrefix:
            self.opts.clonedCasePrefix=path.basename(parameterFile)
        if not self.opts.clonedCasePostfix:
            self.opts.clonedCasePostfix=""
        else:
            self.opts.clonedCasePostfix="."+self.opts.clonedCasePostfix
        if not self.opts.cloneToDirectory:
            self.opts.cloneToDirectory=path.dirname(path.abspath(origPath))
        if not self.opts.database:
            self.opts.database=parameterFile+".database"

        variationData=ParsedParameterFile(parameterFile,
                                          noHeader=True,
                                          noVectorOrTensor=True).getValueDict()
        if not "values" in variationData:
            self.error("Entry 'values' (dictionary) needed in",parameterFile)
        if not "solver" in variationData["values"]:
            self.error("Entry 'solver' (list or string) needed in 'values' in",parameterFile)

        fixed={}
        defaults={}
        varied=[]
        nrVariations=1

        for k in variationData["values"]:
            v=variationData["values"][k]
            if type(v)!=list:
                self.error("Entry",k,"is not a list")
            if len(v)==1:
                fixed[k]=v[0]
            elif len(v)>1:
                varied.append((k,v))
                nrVariations*=len(v)
            else:
                self.warning("Entry",k,"is empty")

        if "defaults" in variationData:
            defaults=variationData["defaults"]

        if len(varied)==0:
            self.error("No parameters to vary")

        self.printPhase(nrVariations,"variations with",len(varied),"parameters")

        def makeVariations(vList):
            name,vals=vList[0]
            if len(vList)>1:
                var=makeVariations(vList[1:])
                variation=[]
                for orig in var:
                    for v in vals:
                        d=orig.copy()
                        if isinstance(v,(dict,DictProxy)):
                            d.update(v)
                        else:
                            d[name]=v
                        variation.append(d)
                return variation
            else:
                return [v if isinstance(v,(dict,DictProxy)) else {name:v} for v in vals]

        variations=[dict(defaults,**d) for d in makeVariations(varied)]
        self["variations"]=variations
        self["fixed"]=fixed

        if self.opts.startVariation!=None:
            start=self.opts.startVariation
        else:
            start=0
        if self.opts.endVariation!=None:
            end=self.opts.endVariation
            if end>=len(variations):
                end=len(variations)-1
        else:
            end=len(variations)-1

        if self.opts.singleVariation!=None:
            if self.opts.startVariation or self.opts.endVariation:
                self.error("--single-variation not possible with --end-variation-number or --start-variation-number")
            if self.opts.singleVariation<0:
                self.error("--single-variation must be greater or equal to 0")
            if self.opts.singleVariation>=len(variations):
                self.error("Only",len(variations))
            start=self.opts.singleVariation
            end  =self.opts.singleVariation

        if end<start:
            self.error("Start value",start,"bigger than end value",end)

        if self.opts.listVariations:
            self.printPhase("Listing variations")
            for i in range(start,end+1):
                print_("Variation",i,":",variations[i])
            return

        if not hasDatabase or self.opts.noDatabaseWrite:
            if path.exists(self.opts.database) and self.opts.createDatabase:
                self.error("database-file",self.opts.database,"exists already.")
            elif not path.exists(self.opts.database) and not self.opts.createDatabase and not self.opts.autoCreateDatabase:
                self.error("database-file",self.opts.database,"does not exist")

        createDatabase=self.opts.createDatabase
        if self.opts.autoCreateDatabase and not path.exists(self.opts.database):
            createDatabase=True

        if not hasDatabase or self.opts.noDatabaseWrite:
            db=None
        else:
            db=RunDatabase(self.opts.database,
                           create=createDatabase,
                           verbose=self.opts.verbose)

        origCase=SolutionDirectory(origPath,archive=None)
        if self.opts.oneClonedCase:
            self.printPhase("Cloning work case")
            workCase=origCase.cloneCase(path.join(self.opts.cloneToDirectory,
                                                  self.opts.clonedCasePrefix+"_"+path.basename(origPath))+self.opts.clonedCasePostfix)

        self.printPhase("Starting actual variations")

        for i in range(start,end+1):
            self.printPhase("Variation",i,"of [",start,",",end,"]")

            usedVals=variations[i].copy()
            usedVals.update(fixed)

            self.prepareHooks()

            clone=False
            if self.opts.inplaceExecution:
                workCase=origCase
            elif self.opts.oneClonedCase:
                pass
            else:
                self.printPhase("Cloning work case")
                workCase=origCase.cloneCase(path.join(self.opts.cloneToDirectory,
                                                  self.opts.clonedCasePrefix+"_"+
                                                      ("%05d" % i)+"_"+path.basename(origPath))+self.opts.clonedCasePostfix)

            self.processPlotLineOptions(autoPath=workCase.name)

            self.printPhase("Setting up the case")

            self.prepare(workCase,overrideParameters=usedVals)

            if self.opts.noExecuteSolver:
                self.printPhase("Not executing the solver")
                continue

            if self.opts.oneClonedCase or self.opts.inplaceExecution:
                self.setLogname(self.opts.clonedCasePrefix+("_%05d_"%i)+usedVals["solver"],
                                useApplication=False,
                                force=True)
            else:
                self.setLogname(self.opts.clonedCasePrefix+"_"+usedVals["solver"],
                                useApplication=False,
                                force=True)

            lam=self.getParallel(workCase)

            allLines().clear()
            allPlots().clear()
            resetCustomCounter()

            run=AnalyzedRunner(BoundingLogAnalyzer(progress=self.opts.progress,
                                                   doFiles=self.opts.writeFiles,
                                                   singleFile=self.opts.singleDataFilesOnly,
                                                   doTimelines=True),
                               silent=self.opts.progress or self.opts.silent,
                               splitThres=self.opts.splitDataPointsThreshold if self.opts.doSplitDataPoints else None,
                               split_fraction_unchanged=self.opts.split_fraction_unchanged,
                               argv=[usedVals["solver"],"-case",workCase.name],
                               server=self.opts.server,
                               lam=lam,
                               logname=self.opts.logname,
                               compressLog=self.opts.compress,
                               logTail=self.opts.logTail,
                               noLog=self.opts.noLog,
                               remark=self.opts.remark,
                               parameters=usedVals,
                               echoCommandLine=self.opts.echoCommandPrefix,
                               jobId=self.opts.jobId)

            run.createPlots(customRegexp=self.lines_,
                            splitThres=self.opts.splitDataPointsThreshold if self.opts.doSplitDataPoints else None,
                            split_fraction_unchanged=self.opts.split_fraction_unchanged,
                            writeFiles=self.opts.writeFiles)

            self.runPreHooks()

            self.printPhase("Running")

            run.start()

            self.printPhase("Getting data")

            self["run%05d" % i]=run.data
            if db:
                db.add(run.data)

            self.runPostHooks()

            self.reportUsage(run)
            self.reportRunnerData(run)

        self.printPhase("Ending variation")
# Should work with Python3 and Python2
