"""
Application-class that implements pyFoamIPythonNotebook.py
"""
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from PyFoam.IPythonHelpers.Notebook import Notebook
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.Basics.FoamOptionParser import Subcommand

from os import path
import sys,re

from PyFoam.ThirdParty.six import print_,u

class IPythonNotebook(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
This utility creates and manipulates IPython-Notebooks that are related to
OpenFOAM-cases. The Notebooks are only used as a start for the own evaluations of the user
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog COMMAND [<arguments>]",
                                   changeVersion=False,
                                   subcommands=True,
                                   **kwargs)

    def addOptions(self):
        # Building the subcommands
        createCmd=Subcommand(name='create',
                             help="Create a new IPython-notebook for a case",
                             aliases=("new","mk",),
                             nr=1,
                             exactNr=True)
        self.parser.addSubcommand(createCmd,
                                  usage="%prog COMMAND <caseDirectory>")

        copyCmd=Subcommand(name='copy',
                            help="Gets an existing notebook and rewrites it to fit a new case (this assumes that the original notebook was built with this utility)",
                            aliases=("cp",),
                            nr=2,
                            exactNr=True)
        self.parser.addSubcommand(copyCmd,
                                  usage="%prog COMMAND <originalNotebook> <caseDirectory>")

        infoCmd=Subcommand(name='info',
                           help="Check whether an IPython-Notebook is created by this Utility and print info",
                           aliases=("report",),
                           nr=1,
                           exactNr=False)
        self.parser.addSubcommand(infoCmd,
                                  usage="%prog COMMAND <notebookFile> [<more notebook files>]")

        cleanCmd=Subcommand(name='clean',
                            help="Remove unneeded cells from the notebook",
                            aliases=("purge",),
                            nr=1,
                            exactNr=True)
        self.parser.addSubcommand(cleanCmd,
                                  usage="%prog COMMAND <notebookFile>")

        # Add option groups to parsers
        for cmd in [copyCmd,createCmd]:
            outOpts=OptionGroup(cmd.parser,
                                "Write Options",
                                "Where the Notebook should be created")
            outOpts.add_option("--force-write",
                               action="store_true",
                               dest="forceWrite",
                               default=False,
                               help="Force writing if the file already exists")
            outOpts.add_option("--destination-file",
                               action="store",
                               dest="destinationFile",
                               default=None,
                               help="Write to this filename. If unset the notebook is written to the case it is created for as <casename>.ipynb. If the destination is directory the file is created in this directory as <casename>.ipynb. Otherwise the fie is created according to specification")
            outOpts.add_option("--relative-path",
                               action="store_false",
                               dest="absolutePath",
                               default=True,
                               help="Keep the relative path to the directory as specified by the user. Otherwise the path is rewritten as an absolute path")
            outOpts.add_option("--case-variable-name",
                               action="store",
                               dest="caseVariable",
                               default="case",
                               help="Name of the variable representing the case in the notebook. Defaut: %default")
            cmd.parser.add_option_group(outOpts)

        for cmd in [cleanCmd]:
            cleanOpts=OptionGroup(cmd.parser,
                                    "Clean Options",
                                    "What should be cleaned")
            cleanOpts.add_option("--keep-selector",
                                 action="store_false",
                                 dest="cleanSelector",
                                 default=True,
                                 help="Keep the data selectors")
            cleanOpts.add_option("--keep-developer",
                                 action="store_false",
                                 dest="cleanDeveloper",
                                 default=True,
                                 help="Clean out the developer stuff")
            cleanOpts.add_option("--clean-comments",
                                 action="store_true",
                                 dest="cleanComment",
                                 default=False,
                                 help="Clean out the comments created by this utility")
            cleanOpts.add_option("--clean-headings",
                                 action="store_true",
                                 dest="cleanHeading",
                                 default=False,
                                 help="Clean out the headings created by this utility")
            cleanOpts.add_option("--clean-report",
                                 action="store_true",
                                 dest="cleanReport",
                                 default=False,
                                 help="Clean out the case report created by this utility")
            cleanOpts.add_option("--clean-info",
                                 action="store_true",
                                 dest="cleanInfo",
                                 default=False,
                                 help="Clean out information statements")
            cleanOpts.add_option("--clean-output",
                                 action="store_true",
                                 dest="cleanOutput",
                                 default=False,
                                 help="Strip out the output cells (results)")
            cleanOpts.add_option("--clean-custom-tag",
                                 action="append",
                                 dest="customTags",
                                 default=[],
                                 help="Clean cells tagged with this custom tag. Can be specified more than once")
            cmd.parser.add_option_group(cleanOpts)

            outOpts=OptionGroup(cmd.parser,
                                "Write Options",
                                "How the cleaned notebook should be written")
            outOpts.add_option("--overwrite",
                               action="store_true",
                               dest="overwrite",
                               default=False,
                               help="Overwrite the old notebook")
            outOpts.add_option("--outfile",
                               action="store",
                               dest="outfile",
                               default=None,
                               help="Write to a new notebook here")
            outOpts.add_option("--force",
                               action="store_true",
                               dest="force",
                               default=False,
                               help="If the outfile already exists overwrite it")
            cmd.parser.add_option_group(outOpts)

        for cmd in [createCmd]:
            contentOpts=OptionGroup(cmd.parser,
                                    "Content Options",
                                    "What should be added to the notebook")
            contentOpts.add_option("--no-case-report",
                               action="store_false",
                               dest="caseReport",
                               default=True,
                               help="Do not give a general overview of the case")
            contentOpts.add_option("--no-additional-imports",
                               action="store_false",
                               dest="additional",
                               default=True,
                               help="Do not import packages that make the notebook neater")
            contentOpts.add_option("--long-boundary-conditions",
                               action="store_true",
                               dest="longBCs",
                               default=False,
                               help="Long boundary conditions")
            contentOpts.add_option("--no-parallel-report",
                               action="store_false",
                               dest="parallelReport",
                               default=True,
                               help="Do not report about parallelization")
            contentOpts.add_option("--no-postprocessing",
                               action="store_false",
                               dest="postprocessing",
                               default=True,
                               help="Do not report about available postprocessing data")
            contentOpts.add_option("--no-data-selectors",
                               action="store_false",
                               dest="selectors",
                               default=True,
                               help="Do not add data selectors for the available postprocessing data")
            cmd.parser.add_option_group(contentOpts)

    def run(self):
        if self.cmdname in ["create","copy"]:
            if self.cmdname=="create":
                dest=self.parser.getArgs()[0]
            else:
                dest=self.parser.getArgs()[1]
            sol=SolutionDirectory(dest,
                                  paraviewLink=False,
                                  archive=None)
            fName=path.join(sol.name,path.basename(sol.name)+".ipynb")
            if self.opts.destinationFile:
                fName=self.opts.destinationFile
                if path.isdir(fName):
                    fName=path.join(fName,path.basename(sol.name))
                if path.splitext(fName)[1]!=".ipynb":
                    fName+=".ipynb"
            if self.opts.absolutePath:
                 usedDest=sol.name
            else:
                 usedDest=path.relpath(sol.name,
                                       start=path.dirname(path.abspath(
                                                          fName)))
            if path.exists(fName):
                if not self.opts.forceWrite:
                    self.error("File",fName,"already existing")
                else:
                    self.warning("Overwriting",fName)
            nb=Notebook(name=path.basename(sol.name))
            nb.pyFoamMetaData()["description"]="Created by "+self.parser.get_prog_name()
            if self.cmdname=="create":
                nb.addHeading("Imports and administrative stuff",
                              level=1,classes="heading")
                if self.opts.developerMode:
                     nb.addMarkdown("This part only needed by developers (reload imports)",
                                    classes=("comment","developer"))
                     nb.addCode("%load_ext autoreload",classes="developer")
                     nb.addCode("%autoreload 2",classes="developer")
                nb.addMarkdown("Make sure that plots are inlined",
                               classes="comment")
                nb.addCode("%matplotlib inline")
                if self.opts.additional:
                    nb.addHeading("Additional imports for convenience",
                                  level=2,classes=("heading","additional"))
                    nb.addMarkdown("Allow panning and zooming in plots. Slower than regular plotting so for big data you might want to use `mpld3.disable_notebook()` and erase this cell.",
                                   classes=("comment","additional"))
                    nb.addCode(
"""try:
    import mpld3
    mpld3.enable_notebook()
except ImportError:
    print 'No mpld3-library. No interactive plots'""",classes="additional")
                    nb.addMarkdown(
"""Uncomment this code to change the size of the plots""")
                    nb.addCode(
"""# import matplotlib.pylab as pylab
# pylab.rcParams["figure.figsize"]=(12,8)""")
                    nb.addMarkdown(
"""Wrapper with additional functionality to the regular Pandas-`DataFrame`:

* `addData()` for adding columns from other data sets (with resampling
* `integrals()` and `weightedAverage()`. Also extended `descripe()` that returns this data

Most Pandas-operations (like slicing) will return a Pandas-`DataFrame`. By enclosing this in `DataFrame(...)` you can 'add' this functionality to your data. PyFoam operations return this extended  `DataFrame` automatically""",
                                   classes=("comment","additional"))
                    nb.addCode("from PyFoam.Wrappers.Pandas import PyFoamDataFrame as DataFrame",classes="additional")
                nb.addHeading("Data storage",
                              level=2,classes=("heading"))
                nb.addMarkdown("This is the support for permanently storing data into the notebook",
                               classes="comment")
                nb.addCode("from PyFoam.IPythonHelpers import storage")
                nb.addMarkdown("Due to technical problems the next line has to be executed 'by hand' (it will not work poperly if called from `Run All` or similar). When reopening the page the JavaScript-error is normal (it will go away once the cell is executed). Reading can take some time and the next command will appear to 'hang'",
                               classes="comment")
                nb.addCode("store=storage()")
                nb.addMarkdown("The next line switches on the behaviour that items specified with `store(name,func)` will be stored permanently in the notebook. Uncomment if you want this behaviour",
                               classes="comment")
                nb.addCode("# store.autowriteOn()")
                nb.addMarkdown("The next line switches off the default behaviour that for items specified with `store(name,func)` if `name` is already specified in the permant storage this value is used and `func` is ignored",
                               classes="comment")
                nb.addCode("# store.autoreadOff()")
                nb.addHeading("Case data",
                              level=2,classes=("heading"))
                nb.addMarkdown("This class makes it easy to access case data. Use tab-completion for available methods",
                               classes="comment")
                nb.addCode("from PyFoam.IPythonHelpers.Case import Case")
                nb.addHeading("The Case",classes="heading")
                v=self.opts.caseVariable
                nb.addCode("%s=Case('%s')" % (v,usedDest),classes="case",
                           pyFoam={"caseVar":v,"usedDirectory":usedDest,
                                   "casePath":sol.name})
                if self.opts.caseReport:
                     nb.addHeading("Case Report",level=2,
                                   classes=("report","heading"))
                     regions=sorted(sol.getRegions(defaultRegion=True))
                     namedRegions=[r for r in regions if r!=None]
                     if len(namedRegions)>0:
                          nb.addMarkdown("Contains named regions *"+
                                         ", ".join(namedRegions)+"*",
                                         classes=("info","report"))
                     if sol.procNr>0:
                          nb.addMarkdown("Case seems to be decomposed to "+
                                         str(sol.procNr)+" processors",
                                         classes=("info","report"))
                     for region in regions:
                          if region==None:
                               level=3
                               regionStr=""
                          else:
                               nb.addHeading("Region "+region,
                                             level=3,classes=("heading","report"))
                               level=4
                               regionStr="region='%s'," % region
                          nb.addCode("%s.size(%slevel=%d)" % (v,regionStr,level),
                                     classes="report")
                          nb.addCode("%s.boundaryConditions(%slevel=%d)" % (v,regionStr,level),
                                     classes="report")
                          nb.addCode("%s.dimensions(%slevel=%d)" % (v,regionStr,level),
                                     classes="report")
                          nb.addCode("%s.internalField(%slevel=%d)" % (v,regionStr,level),
                                     classes="report")
                          if self.opts.longBCs:
                               nb.addCode("%s.longBoundaryConditions(%slevel=%d)" % (regionStr,v,level),
                                          classes="report")
                          if sol.procNr>0 and self.opts.parallelReport:
                               nb.addCode("%s.decomposition(%slevel=%d)" % (v,regionStr,level),
                                          classes="report")
                               nb.addCode("%s.processorMatrix(%slevel=%d)" % (v,regionStr,level),
                                          classes="report")
                if self.opts.postprocessing:
                     nb.addHeading("Postprocessing data",classes="heading")
                     if len(sol.timelines)>0:
                          nb.addMarkdown("Timelines",classes="info")
                          nb.addCode("%s.sol.timelines" % v,classes="info")
                     if len(sol.samples)>0:
                          nb.addMarkdown("Samples",classes="info")
                          nb.addCode("%s.sol.samples" % v,classes="info")
                     if len(sol.surfaces)>0:
                          nb.addMarkdown("Surfaces",classes="info")
                          nb.addCode("%s.sol.surfaces" % v,classes="info")
                     if len(sol.distributions)>0:
                          nb.addMarkdown("Distributions",classes="info")
                          nb.addCode("%s.sol.distributions" % v,classes="info")
                     if len(sol.pickledData)>0:
                          nb.addMarkdown("Pickled data files",classes="info")
                          nb.addCode("%s.sol.pickledData" % v,classes="info")
                     if len(sol.pickledPlots)>0:
                          nb.addMarkdown("Pickled plot files",classes="info")
                          nb.addCode("%s.sol.pickledPlots" % v,classes="info")
                     if self.opts.selectors:
                          sel=[("timeline",sol.timelines),
                               ("sample",sol.samples),
                               ("distribution",sol.distributions)]
                          for desc,items in sel:
                               if len(items)>0:
                                    nb.addHeading(desc.capitalize()+
                                                  " selectors",level=3,
                                                  classes=("heading","selector"))
                                    for i in items:
                                         nb.addCode("%s.%sSelector('%s')" %
                                                    (v,desc,i),
                                                    classes="selector")
                          if len(sol.pickledPlots)>0 or len(sol.pickledData)>0:
                              nb.addHeading("Data selectors",level=3,
                                            classes=("heading","selector"))
                              if len(sol.pickledPlots)>0:
                                  nb.addCode("%s.pickledPlotSelector()" % v,classes="selector")
                              if len(sol.pickledData)>0:
                                  nb.addCode("%s.pickledDataSelector()" % v,classes="selector")

                nb.addHeading("User evaluations",classes="heading")
                nb.addMarkdown("Now add your own stuff",classes="comment")
            elif self.cmdname=="copy":
                src=self.parser.getArgs()[0]
                nb=Notebook(src)
                cnt=0
                for c in nb:
                    if c.isClass("case"):
                        cnt+=1
                        if cnt>1:
                            self.error(src,"has more than one 'case'-cell")
                        py=c.meta()[u("pyFoam")]
                        used=py["usedDirectory"]
                        input=[]
                        changed=False
                        for l in c["input"]:
                            if l.find(used)>=0:
                                input.append(l.replace(used,usedDest))
                                changed=True
                            else:
                                input.append(l)
                        if not changed:
                            self.warning(used,"not found")
                        py["usedDirectory"]=usedDest
                        py["casePath"]=sol.name
                        c["input"]=input
            else:
                self.error("Unimplemented:",self.cmdname)
            nb.writeToFile(fName)
        elif self.cmdname=="info":
            for n in self.parser.getArgs():
                print_(n)
                print_("-"*len(n))
                nb=Notebook(n)
                meta=nb.pyFoamMetaData()
                try:
                    origin=meta["createdBy"]
                except KeyError:
                    origin="unknown"
                try:
                    created=meta["createdTime"]
                except KeyError:
                    created="unknown"
                try:
                    created=meta["createdTime"]
                except KeyError:
                    created="unknown"
                try:
                    modified=meta["modificationTime"]
                except KeyError:
                    modified="unknown"
                print_("Created by",origin,"at",created,
                       "modified",modified)
                classes={}
                cases={}
                nrOutput=0
                for c in nb:
                    if "outputs" in c:
                        if len(c["outputs"])>0:
                            nrOutput+=1
                    try:
                        py=c.meta()[u("pyFoam")]
                    except KeyError:
                        continue
                    try:
                        cl=py["classes"]
                        for c in cl:
                            try:
                                classes[c]+=1
                            except KeyError:
                                classes[c]=1
                    except KeyError:
                        pass
                    if "caseVar" in py:
                        try:
                            cases[py["caseVar"]]=py["casePath"]
                        except KeyError:
                            pass
                print_(len(nb),"cells. Classes:",
                       ", ".join([k+":"+str(classes[k]) for k in sorted(classes.keys())]))
                print_("Cells with output:",nrOutput)
                print("Case-Variables:")
                for k in sorted(cases.keys()):
                    print_("  ",k,":",cases[k])

                print_()
        elif self.cmdname=="clean":
            nb=Notebook(self.parser.getArgs()[0])
            if not self.opts.overwrite and not self.opts.outfile:
                self.error("Either specify --overwrite or --outfile")
            if self.opts.overwrite and  self.opts.outfile:
                self.error("Only specify --overwrite or --outfile")
            if self.opts.outfile:
                if path.exists(self.opts.outfile):
                    if not self.opts.force:
                        self.error("File",self.opts.outfile,"exists")
                    else:
                        self.warning("Overwriting",self.opts.outfile)
                else:
                    if path.splitext(self.opts.outfile)[1]!=".ipynb":
                        self.warning("Appending '.ipynb' to",self.opts.outfile)
                        self.opts.outfile+=".ipynb"
            if self.opts.overwrite:
                toFile=self.parser.getArgs()[0]
            else:
                toFile=self.opts.outfile

            removeClasses=self.opts.customTags[:]
            if self.opts.cleanSelector:
                removeClasses.append("selector")
            if self.opts.cleanDeveloper:
                removeClasses.append("developer")
            if self.opts.cleanHeading:
                removeClasses.append("heading")
            if self.opts.cleanComment:
                removeClasses.append("comment")
            if self.opts.cleanReport:
                removeClasses.append("report")
            if self.opts.cleanInfo:
                removeClasses.append("info")

            print_("Cleaning cells tagged with: "+" ".join(sorted(removeClasses)))

            nb.reset([c for c in nb if not c.isClass(removeClasses)])
            if self.opts.cleanOutput:
                print_("Removing output")
                for c in nb:
                    if "outputs" in c:
                        c["outputs"]=[]

            nb.writeToFile(toFile)
        else:
            self.error("Unimplemented command",self.cmdname)

# Should work with Python3 and Python2
