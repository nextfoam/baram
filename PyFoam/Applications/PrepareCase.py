"""
Application-class that implements pyFoamPrepareCase.py
"""
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication

from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.Basics.DataStructures import DictProxy
from PyFoam.Basics.Utilities import rmtree,copytree,execute,remove,find
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile,WriteParameterFile,FoamStringParser
from PyFoam.Basics.TemplateFile import TemplateFile
from PyFoam.Execution.BasicRunner import BasicRunner
from PyFoam.Basics.RestructuredTextHelper import RestructuredTextHelper

from PyFoam.FoamInformation import foamFork,foamVersion

from .CommonTemplateFormat import CommonTemplateFormat
from .CommonTemplateBehaviour import CommonTemplateBehaviour

from PyFoam.ThirdParty.six import print_,iteritems,exec_

from PyFoam import configuration

from os import path,listdir,mkdir
from shutil import copymode,copy,move
from collections import OrderedDict
import time
import re

from .CursesApplicationWrapper import addExpr

prepareExpr=[r'^Executing',
             r'^Looking for',
             r'^Skipping',
             r'^Found template']

for e in prepareExpr:
    addExpr(e)

def buildFilenameExtension(paraList,valueStrings):
    ext=""
    if len(paraList)>0:
        ext="_".join([path.basename(p) for p in paraList])
    if len(valueStrings)>0:
        d={}
        for v in valueStrings:
            d.update(eval(v))
        ext+="_"+"_".join(["%s=%s" % (n,str(v)) for n,v in iteritems(d)])
    if ext=="":
        return "_vanilla"
    else:
        return "_"+ext

class PrepareCase(PyFoamApplication,
                  CommonTemplateBehaviour,
                  CommonTemplateFormat):

    parameterOutFile="PyFoamPrepareCaseParameters"

    def __init__(self,
                 args=None,
                 exactNr=True,
                 interspersed=True,
                 usage="%prog <caseDirectory>",
                 examples=None,
                 nr=1,
                 description=None,
                 **kwargs):
        self.defaultClearCase=configuration().get("PrepareCase","ClearCaseScript")
        self.defaultMeshCreate=configuration().get("PrepareCase","MeshCreateScript")
        self.defaultPostCopy=configuration().get("PrepareCase","PostCopyScript")
        self.defaultCaseSetup=configuration().get("PrepareCase","CaseSetupScript")
        self.defaultDecomposeMesh=configuration().get("PrepareCase","DecomposeMeshScript")
        self.defaultDecomposeFields=configuration().get("PrepareCase","DecomposeFieldsScript")
        self.defaultDecomposeCase=configuration().get("PrepareCase","DecomposeCaseScript")
        self.defaultParameterFile=configuration().get("PrepareCase","DefaultParameterFile")
        self.defaultIgnoreDirecotries=configuration().getList("PrepareCase","IgnoreDirectories")

        description2="""\
Prepares a case for running. This is intended to be the replacement for
boiler-plate scripts. The steps done are

  1. Read parameters from default.parameters (if present) and
  parameter files and parameters specified on the command line

  2. Execute a script derviedParamters.py to calculate new values

  3. Clear old data from the case (including processor
  directories). If present uses script clearCase.sh

  4. if a folder 0.org or 0.orig is present remove the 0 folder too

  5. go through all folders and for every found file with the extension .template
do template expansion using the pyratemp-engine (automatically create variables
casePath and caseName)

  6. create a mesh (either by using a script or if a blockMeshDict is present by
running blockMesh. If none of these is present assume that there is a valid mesh
present). Afterwards (if present) a script decomposeMesh.sh is executed

  7. copy every foo.org that is found to to foo (recursively if directory).

  8. If present exectute a script postCopy.sh

  9. If present (and if a parallel run) a script decomposeFields.sh is executed

  10. do template-expansion for every file with the extension .postTemplate

  11. execute another preparation script (caseSetup.sh). If no such script is found
but a setFieldsDict in system then setFields is executed. Afterwards (if present) a script decomposeCase.sh is executed

  12. do final template-expansion for every file with the extension .finalTemplate

The used parameters are written to a file 'PyFoamPrepareCaseParameters' and are used by other utilities
"""
        examples2="""\
%prog . --paramter-file=parameters.base

  Prepare the current case with the parameters list in parameters.base

%prog . --paramter-file=parameters.base --values-string="{'visco':1e-3}"

  Changes the value of the parameter visco

%prog . --no-mesh-create

  Skip the mesh creation phase

%prog exampleCase --paramter-file=parameters.base --build-example --clone-case=originalCase

  Build a case named exampleCase from the case originalCase using the parameter file parameter.base (creates an Allrun-script )
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description if description else description2,
                                   usage=usage,
                                   examples=examples if examples else examples2,
                                   interspersed=interspersed,
                                   nr=nr,
                                   exactNr=exactNr,
                                   findLocalConfigurationFile=self.localConfigInArgs,
                                   **kwargs)

    def addOptions(self):
        output=OptionGroup(self.parser,
                         "Output",
                         "What information should be given")
        self.parser.add_option_group(output)
        output.add_option("--fatal",
                          action="store_true",
                          dest="fatal",
                        default=False,
                        help="If non-cases are specified the program should abort")
        output.add_option("--no-complain",
                          action="store_true",
                          dest="noComplain",
                          default=False,
                          help="Don't complain about non-case-files")
        output.add_option("--quiet",
                          action="store_false",
                          dest="verbose",
                          default=True,
                          help="Do not report what is being done")
        output.add_option("--no-write-parameters",
                          action="store_false",
                          dest="writeParameters",
                          default=True,
                          help="Usually a file '"+self.parameterOutFile+"' with a dictionary of the used parameters is written to the case directory. ")
        output.add_option("--no-write-report",
                          action="store_false",
                          dest="writeReport",
                          default=True,
                          help="Usually a file '"+self.parameterOutFile+".rst' with a ReST-file that reports the used parameters is written to the case directory. ")
        output.add_option("--warn-on-wrong-options",
                          action="store_false",
                          dest="failOnWrongOption",
                          default=True,
                          help="Only issue a warning if a value was set that is not found in the list of valid options")

        extensions=OptionGroup(self.parser,
                               "Extensions",
                               "File extensions that are used in actions")
        self.parser.add_option_group(extensions)
        extensions.add_option("--template-extension",
                              action="store",
                              dest="templateExt",
                              default=".template",
                              help="Extension for template files. Default: %default")
        extensions.add_option("--post-template-extension",
                              action="store",
                              dest="postTemplateExt",
                              default=".postTemplate",
                              help="Extension for post-template files. Default: %default")
        extensions.add_option("--final-template-extension",
                              action="store",
                              dest="finalTemplateExt",
                              default=".finalTemplate",
                              help="Extension for final-template files. Default: %default")
        extensions.add_option("--original-extension",
                              action="store",
                              dest="originalExt",
                              default=".org",
                              help="Extension for files and directories that are copied. Default: %default")
        extensions.add_option("--zero-time-original-extensions",
                              action="append",
                              dest="zeroTimeOriginalExtensions",
                              default=[".orig"],
                              help="Additional extensions to be used for the original of the zero time directory. The first one is used. Default: %default")
        extensions.add_option("--extension-addition",
                              action="append",
                              dest="extensionAddition",
                              default=[],
                              help="Addtional extension that is added to templates and originals to allow overrides. For instance if an addition 'steady' is specified and a file 'T.template' and 'T.template.steady' is found then the later is used. Can be specied more than once. The last instance is used.")

        inputs=OptionGroup(self.parser,
                           "Inputs",
                           "Inputs for the templating process")
        self.parser.add_option_group(inputs)

        inputs.add_option("--parameter-file",
                          action="append",
                          default=[],
                          dest="valuesDicts",
                          help="Name of a dictionary-file in OpenFOAM-format. Can be specified more than once. Values in later files override old values. If a file "+self.defaultParameterFile+" is present it is read before all other paraemter files")
        inputs.add_option("--no-default-parameter-file",
                          action="store_false",
                          default=True,
                          dest="useDefaultParameterFile",
                          help="Even if present do NOT use the file "+self.defaultParameterFile+" before the other parameter files")
        inputs.add_option("--values-string",
                          action="append",
                          default=[],
                          dest="values",
                          help="String with the values that are to be inserted into the template as a dictionaty in Python-format if the string starts with '{' and ends with '}'. Otherwise it is assumed that the string is a dictionary in OpenFOAM-format. Can be specified more than once and overrides values from the parameter-files")

        special=OptionGroup(self.parser,
                           "Special files and directories",
                           "Files and directories that get special treatment")
        self.parser.add_option_group(special)

        special.add_option("--directories-to-clean",
                          action="append",
                          default=["0"],
                          dest="cleanDirectories",
                          help="Directory from which templates are cleaned (to avoid problems with decomposePar). Can be specified more than once. Default: %default")
        special.add_option("--overload-directory",
                           action="append",
                           default=[],
                           dest="overloadDirs",
                           help="Before starting the preparation process load files from this directory recursively into this case. Caution: existing files will be overwritten. Can be specified more than once. Directories are then copied in the specified order")
        special.add_option("--clone-case",
                          default=None,
                          dest="cloneCase",
                           help="If this is set then this directory is cloned to the specified directory and setup is done there (the target directory must not exist except if the name is build with --automatic-casename)")
        special.add_option("--automatic-casename",
                           action="store_true",
                           dest="autoCasename",
                           default=False,
                           help="If used with --clone-case then the casename is built from the original casename, the names of the parameter-files and the set values")
        special.add_option("--ignore-directories",
                           action="append",
                           dest="ignoreDirectories",
                           default=list(self.defaultIgnoreDirecotries),
                           help="Regular expression. Directories that match this expression are ignored. Can be used more than once. Already set: "+", ".join(["r'"+e+"'" for e in self.defaultIgnoreDirecotries]))
        CommonTemplateFormat.addOptions(self)
        CommonTemplateBehaviour.addOptions(self)

        mode=OptionGroup(self.parser,
                           "Mode",
                           "How the utility should work")
        self.parser.add_option_group(mode)
        mode.add_option("--execute-in-case-directory",
                        action="store_true",
                        dest="executeInCaseDirectory",
                        default=False,
                        help="Execute in the specified case directory. This means that paths to parameter files etc can be relative (or in) that directory")
        mode.add_option("--build-example",
                        action="store_true",
                        dest="buildExample",
                        default=False,
                        help="Build an example case that can be executed without pyFoam. Only evaluates the templates, builds a AllRun-script and removes unnecessary files. Does not work for all configurations")

        if configuration().getboolean("PrepareCase","ZipExtensionlessTemplateResults"):
            mode.add_option("--no-zip-extensionless-template-results",
                            action="store_false",
                            dest="zipExtensionlessTemplateResults",
                            default=True,
                            help="Do not automatically zip extensionless template results")
        else:
            mode.add_option("--zip-extensionless-template-results",
                            action="store_true",
                            dest="zipExtensionlessTemplateResults",
                            default=False,
                            help="Zip the results of template evaluations. So a template file foo.template gets written to a zipped file foo.gz. This is only done if foo has no extension")

        defaultZipableExtensions=configuration().getList("PrepareCase","ZipableExtensions")

        mode.add_option("--zipable-extensions",
                        action="append",
                        dest="zipableExtensions",
                        default=list(defaultZipableExtensions),
                        help="Template Results with these extensions are also zipped. Extensions have to include the '.' in the beginning. Already set: "+", ".join(["'"+e+"'" for e in defaultZipableExtensions]))

        stages=OptionGroup(self.parser,
                           "Stages",
                           "Which steps should be executed")
        self.parser.add_option_group(stages)

        stages.add_option("--only-variables",
                          action="store_true",
                          dest="onlyVariables",
                          default=False,
                          help="Do nothing. Only read the variables")

        stages.add_option("--no-clear",
                          action="store_false",
                          dest="doClear",
                          default=True,
                          help="Do not clear the case")

        stages.add_option("--keep-zero",
                          action="store_true",
                          dest="keepZero",
                          default=False,
                          help="Do not remove the 0 directory even if a 0.org (or equivalent) is there")

        stages.add_option("--no-templates",
                          action="store_false",
                          dest="doTemplates",
                          default=True,
                          help="Do not rework the templates")

        stages.add_option("--stop-after-templates",
                          action="store_true",
                          dest="stopAfterTemplates",
                          default=False,
                          help="Stop after the templates were done")

        stages.add_option("--no-mesh-create",
                          action="store_false",
                          dest="doMeshCreate",
                          default=True,
                          help="Do not execute a script to create a mesh")

        stages.add_option("--no-post-copy",
                          action="store_false",
                          dest="doPostCopy",
                          default=True,
                          help="Do not execute a script after the copying of 0.org")

        stages.add_option("--force-mesh-decompose",
                          action="store_true",
                          dest="doMeshDecompose",
                          default=False,
                          help="Execute the script for mesh decomposition even if the mesh has not been created")

        stages.add_option("--no-copy",
                          action="store_false",
                          dest="doCopy",
                          default=True,
                          help="Do not copy original directories")

        stages.add_option("--force-decompose-field",
                          action="store_true",
                          dest="doFieldDecompose",
                          default=False,
                          help="Execute a script to decompose the fields even if no originals were copied")
        stages.add_option("--no-post-templates",
                          action="store_false",
                          dest="doPostTemplates",
                          default=True,
                          help="Do not rework the post-templates")

        stages.add_option("--no-case-setup",
                          action="store_false",
                          dest="doCaseSetup",
                          default=True,
                          help="Do not execute a script to set initial conditions etc")
        stages.add_option("--force-case-decompose",
                          action="store_true",
                          dest="doCaseDecompose",
                          default=False,
                          help="Execute the script for case decomposition even if the case setup was not done")

        stages.add_option("--no-final-templates",
                          action="store_false",
                          dest="doFinalTemplates",
                          default=True,
                          help="Do not rework the final-templates")

        stages.add_option("--no-template-clean",
                          action="store_false",
                          dest="doTemplateClean",
                          default=True,
                          help="Do not clean template files from 0-directory")

        stages.add_option("--no-paraview-file",
                          action="store_false",
                          dest="paraviewFile",
                          default=True,
                          help="Do not create a .foam file that allows paraview to open the case")

        scripts=OptionGroup(self.parser,
                            "Scripts",
                            "Specification of scripts to be executed")
        self.parser.add_option_group(scripts)

        scripts.add_option("--case-clear-script",
                          action="store",
                          dest="clearCaseScript",
                          default=None,
                          help="Script that is executed in addition to the regular clearing of the case data. If not specified then the utility looks for "+self.defaultClearCase+" and executes this.")
        scripts.add_option("--additional-clear-case-scripts",
                           action="append",
                           dest="additionalClearCase",
                           default=["Allclean"],
                           help="Additional script names to try if no case clearing script is found. Can be used more than once Default: %default")
        scripts.add_option("--mesh-create-script",
                          action="store",
                          dest="meshCreateScript",
                          default=None,
                          help="Script that is executed after the template expansion to create the mesh. If not specified then the utility looks for "+self.defaultMeshCreate+" and executes this. If this is also not found blockMesh is executed if a blockMeshDict is found")
        scripts.add_option("--post-copy-script",
                          action="store",
                          dest="postCopyScript",
                          default=None,
                          help="Script that is executed after the 0.org directory was copied to 0. If not specified then the utility looks for "+self.defaultPostCopy+" and executes this.")
        scripts.add_option("--decompose-mesh-script",
                          action="store",
                          dest="decomposeMeshScript",
                          default=None,
                           help="Script that is executed after the mesh is created. If not specified then the utility looks for "+self.defaultDecomposeMesh+" and executes this.")
        scripts.add_option("--decompose-fields-script",
                          action="store",
                          dest="decomposeFieldsScript",
                          default=None,
                           help="Script that is executed after the mesh is created and decomposed. If not specified then the utility looks for "+self.defaultDecomposeFields+" and executes this")
        scripts.add_option("--additional-mesh-create-scripts",
                           action="append",
                           dest="additionalMeshCreate",
                           default=["Allrun.pre","Allrun.mesh"],
                           help="Additional script names to try if no mesh creation script is found. Can be used more than once Default: %default")
        stages.add_option("--no-keep-zero-directory-from-mesh-create",
                          action="store_false",
                          dest="keepZeroDirectoryFromMesh",
                          default=True,
                          help="If the script that creates the mesh generates a '0'-directory with data then this data will be removed. Otherwise it is kept")
        scripts.add_option("--case-setup-script",
                          action="store",
                          dest="caseSetupScript",
                          default=None,
                          help="Script that is executed after the original files have been copied to set initial conditions or similar. If not specified then the utility looks for "+self.defaultCaseSetup+" and executes this.")
        scripts.add_option("--decompose-case-script",
                           action="store",
                           dest="decomposeCaseScript",
                           default=None,
                           help="Script that is executed after the case setup is finished. If not specified then the utility looks for "+self.defaultDecomposeCase+" and executes this")
        scripts.add_option("--derived-parameters-script",
                          action="store",
                          dest="derivedParametersScript",
                          default="derivedParameters.py",
                          help="If this script is found then it is executed after the parameters are read. All variables set in this script can then be used in the templates. Default: %default")
        scripts.add_option("--allow-derived-changes",
                          action="store_true",
                          dest="allowDerivedChanges",
                          default=False,
                          help="Allow that the derived script changes existing values")
        scripts.add_option("--continue-on-script-failure",
                          action="store_false",
                          dest="failOnScriptFailure",
                          default=True,
                          help="Don't fail the whole process even if a script fails")

        variables=OptionGroup(self.parser,
                              "Variables",
                              "Variables that are automatically defined")
        self.parser.add_option_group(variables)
        variables.add_option("--number-of-processors",
                             action="store",
                             type=int,
                             dest="numberOfProcessors",
                             default=1,
                             help="Value of the variable numberOfProcessors. Default: %default")

    def info(self,*args):
        """Information output"""
        if self.opts.verbose:
            print_(*args)

    def listdir(self,d,ext):
        """Private copy of listdir. Returns a list of pairs: first element is
        the real file-name. Second the name with the extensions stripped off or
        None if the file doesn't match any extensions"""

        extAdditions=[""]+["."+e for e in self.opts.extensionAddition]
        allFiles=listdir(d)
        result=[]
        templated=set()

        for f in allFiles:
            isPlain=True
            for e in extAdditions:
                ee=ext+e
                if len(f)>len(ee):
                    if f[-len(ee):]==ee:
                        isPlain=False
                        templated.add(f[:-len(ee)])
            if isPlain:
                result.append((f,None))

        for t in templated:
            found=None
            for e in extAdditions:
                tt=t+ext+e
                if tt in allFiles:
                    found=tt
            if found==None:
                self.error("This should not happen. Nothing found for",t,"with extensions",
                           extAdditions,"in files",allFiles)
            else:
                result.append((found,t))

        return result

    def copyOriginals(self,startDir,extension=None,recursive=True):
        """Go recursivly through directories and copy foo.org to foo"""
        self.info("Looking for originals in",startDir)
        if extension is None:
            extension=self.opts.originalExt
        for f,t in self.listdir(startDir,extension):
            if f[0]==".":
                self.info("Skipping",f)
                continue
            src=path.join(startDir,f)
            if t!=None:
                dst=path.join(startDir,t)
                if path.exists(dst):
                    self.info("Replacing",dst,"with",src)
                    rmtree(dst)
                else:
                    self.info("Copying",src,"to",dst)
                copytree(src,dst,force=True)
            elif path.isdir(src) and recursive:
                self.copyOriginals(src,
                                   extension=extension,
                                   recursive=recursive)

    def cleanExtension(self,
                       startDir,
                       ext):
        """Go recursivly through directories and remove all files that have a specific extension"""
        self.info("Looking for extension",ext,"in",startDir)
        for f in listdir(startDir):
            if f[0]==".":
                self.info("Skipping",f)
                continue

            src=path.join(startDir,f)
            if path.splitext(src)[1]==ext or path.splitext(path.splitext(src)[0])[1]==ext:
                if not path.isdir(src):
                    self.info("Removing",src)
                    remove(src)
            if path.isdir(src):
                self.cleanExtension(src,ext)

    def searchAndReplaceTemplates(self,
                                  startDir,
                                  values,
                                  templateExt,
                                  ignoreDirectories=[]):
        """Go through the directory recursively and replate foo.template with
        foo after inserting the values"""
        self.info("Looking for templates with extension",templateExt,"in ",startDir)
        for f,t in self.listdir(startDir,templateExt):
            if f[0]==".":
                self.info("Skipping",f)
                continue
            if path.isdir(path.join(startDir,f)):
                matches=None
                for p in ignoreDirectories:
                    if re.compile(p+"$").match(f):
                        matches=p
                        break
                if matches:
                    self.info("Skipping directory",f,"because it matches",matches)
                    continue
                self.searchAndReplaceTemplates(
                    path.join(startDir,f),
                    values,
                    templateExt)
            elif t!=None:
                tName=path.join(startDir,t)
                fName=path.join(startDir,f)
                self.info("Found template for",tName)
                t=TemplateFile(name=fName,
                               tolerantRender=self.opts.tolerantRender,
                               allowExec=self.opts.allowExec or configuration().getboolean("Template","AllowExecution"),
                               expressionDelimiter=self.opts.expressionDelimiter,
                               assignmentDebug=self.pickAssignmentDebug(fName),
                               assignmentLineStart=self.opts.assignmentLineStart)

                ext = path.splitext(tName)[1]
                if self.opts.zipExtensionlessTemplateResults and (ext == "" or ext in self.opts.zipableExtensions):
                    gzip = True
                else:
                    gzip = False

                written = t.writeToFile(tName, values, gzip=gzip)
                copymode(fName, written)

    def overloadDir(self,here,there):
        """Copy files recursively. Overwrite local copies if they exist"""
        for f in listdir(there):
            fSrc=path.join(there,f)
            fDst=path.join(here,f)
            if path.isdir(fSrc):
                if not path.exists(fDst):
                    self.info("Creating directory",fDst)
                    mkdir(fDst)
                elif not path.isdir(fDst):
                    self.error("Destination path",fDst,"exists, but is no directory")
                self.overloadDir(fDst,fSrc)
            elif path.isfile(fSrc):
                isThere=False
                rmDest=None
                if path.exists(fDst):
                    isThere=True
                elif path.splitext(fSrc)[1]==".gz" and \
                     path.exists(path.splitext(fDst)[0]):
                    rmDest=path.splitext(fDst)[0]
                elif path.splitext(fSrc)[1]=="" and \
                     path.exists(fDst+".gz"):
                    rmDest=fDst+".gz"

                if rmDest:
                    remove(rmDest)
                if isThere:
                    if not path.isfile(fDst):
                        self.error("Desination",fDst,"exists but is no file")

                self.info("Copying",fSrc,"to",fDst)
                copy(fSrc,fDst)
            else:
                self.error("Source file",fSrc,"is neither file nor directory")

    def run(self):
        cName=self.parser.getArgs()[0]
        if self.opts.buildExample and not self.opts.cloneCase:
            self.error("For --build-example the option --clone-case is necessary")

        if self.opts.buildExample:
            # self.opts.writeParameters=False
            # self.opts.writeReport=False
            pass

        if self.opts.cloneCase:
            if self.opts.autoCasename:
                cName=path.join(cName,
                                path.basename(self.opts.cloneCase)+
                                buildFilenameExtension(self.opts.valuesDicts,
                                                       self.opts.values))
            if path.exists(cName):
                self.error(cName,"already existing (case should not exist when used with --clone-case)")
            if self.checkCase(self.opts.cloneCase,
                              fatal=self.opts.fatal,
                              verbose=not self.opts.noComplain):
                self.addLocalConfig(self.opts.cloneCase)
            orig=SolutionDirectory(self.opts.cloneCase,
                                   archive=None,paraviewLink=False)
            sol=orig.cloneCase(cName,
                               paraviewLink=self.opts.paraviewFile)
        else:
            if self.checkCase(cName,
                              fatal=self.opts.fatal,
                              verbose=not self.opts.noComplain):
                self.addLocalConfig(cName)
            sol=SolutionDirectory(cName,archive=None,
                                  parallel=True,
                                  paraviewLink=self.opts.paraviewFile)

        previousDirectory = None
        if self.opts.executeInCaseDirectory:
            previousDirectory = path.abspath(path.curdir)

            from os import chdir
            if path.realpath(cName)==path.realpath(path.curdir):
                self.warning("Not changing directory because Already in",path.realpath(path.curdir))
            else:
                chdir(path.realpath(cName))
                cName=path.curdir

        try:
            self.__lastMessage=None
            self.prepare(sol,cName=cName)
        except:
            if self.__lastMessage:
                self.__writeToStateFile(sol,self.__lastMessage+" failed")
            raise

        if previousDirectory:
            # Change back if this is used in a script
            chdir(previousDirectory)

    def __strip(self,val):
        """Strip extra " from strings"""
        if isinstance(val,(str,)):
            if len(val)>2:
                if val[0]=='"' and val[-1]=='"':
                    return val[1:-1]
        return val

    def processDefault(self,raw):
        """Process a dictionary and return a 'flattened' dictionary with the
        values and a dictionary with the meta-data"""
        values=OrderedDict()
        meta=OrderedDict()
        meta[""]={}

        for k,v in iteritems(raw):
            isNormal=True

            if isinstance(v,(DictProxy,dict)):
                if "description" in v:
                    if "default" in v:
                        if "values" in v:
                            self.warning(k+" has also a 'values'-entry. Might be a subgroup")
                        vMeta={}
                        for a in v:
                            if a=="description":
                                vMeta[a]=self.__strip(v[a])
                            else:
                                vMeta[a]=v[a]
                        meta[""][k]=vMeta
                    elif "values" in v:
                        isNormal=False

            if isNormal:
                if k in values:
                    self.error(k,"defined twice in defaults")
                if not k in meta[""]:
                    meta[""][k]={"default":v}
                    values[k]=v
                else:
                    values[k]=meta[""][k]["default"]
            else:
                pVal,pMeta=self.processDefault(v["values"])
                meta[k]=(self.__strip(v["description"]),pMeta)
                for a in pVal:
                    if a in values:
                        self.error(a,"already defined in sub-directory")
                    else:
                        values[a]=pVal[a]

        return values,meta

    def getDefaultValues(self,cName):
        """Process the file with the default values - if present
        Returns a dictionary with the values and a dictionary with the meta-data
        about the parameters"""
        defFile=path.join(path.abspath(cName),self.defaultParameterFile)
        if self.opts.useDefaultParameterFile and path.exists(defFile):
            self.info("Using default values from",defFile)
            return self.processDefault(
                ParsedParameterFile(defFile,
                                    noHeader=True,
                                    doMacroExpansion=True).getValueDict())
        else:
            return {},{}

    def addDictValues(self,name,description,values):
        """Add values from a dictionary"""
        meta=dict([(k,{"default":v}) for k,v in iteritems(values)])
        self.metaData[name]=(description,{"":meta})
        return values

    def makeReport(self,values,level=2,meta=None):
        if meta is None:
            meta=self.metaData
        helper=RestructuredTextHelper(defaultHeading=level)
        val=""

        for k in meta:
            if k=="":
                if len(meta[k])==0:
                    continue
                tab=helper.table(labeled=True)
                for kk in meta[k]:
                    if "default" in meta[k][kk] and values[kk]!=meta[k][kk]["default"]:
                        changed=True
                        tab.addRow(helper.strong(kk))
                    else:
                        changed=False
                        tab.addRow(kk)
                    for a,v in iteritems(meta[k][kk]):
                        tab.addItem(a,v)
                    if changed:
                        tab.addItem("Value",helper.strong(values[kk]))
                    else:
                        tab.addItem("Value",values[kk])
                val+=str(tab)
            else:
                descr,newMeta=meta[k]
                val+=helper.heading(descr)
                val+="\nShort name: "+helper.literal(k)+"\n"
                val+=self.makeReport(values,
                                     level=level+1,
                                     meta=newMeta)
        return val

    def checkCorrectOptions(self,values,meta=None):
        if meta is None:
            meta=self.metaData

        for k in meta:
            if k=="":
                for kk in meta[k]:
                    if "options" in meta[k][kk] and values[kk] not in meta[k][kk]["options"]:
                        if self.opts.failOnWrongOption:
                            func=self.error
                        else:
                            func=self.warning

                        func("Value",values[kk],"for parameter",kk,
                             "not in listv of allowed options:",
                             ", ".join([str(v) for v in meta[k][kk]["options"]]))
            else:
                self.checkCorrectOptions(values,meta[k][1])

    def executeScript(self,
                      scriptName,
                      workdir,
                      echo,
                      allrun=None):
        """Execute a script and write a corresponding logfile"""
        if allrun:
            allrun.write("\nrunApplication "+
                         path.join(path.curdir,path.basename(scriptName))+
                         "\n")
            return

        import sys,os,shutil

        scriptRun=scriptName
        if sys.platform in ["darwin"]:
            scriptRun=path.join(path.dirname(scriptName),
                                "runOnMacVersionOf_"+path.basename(scriptName))
            with open(scriptName) as i:
                with open(scriptRun,"w") as o:
                    o.write(i.readline())
                    o.write("\n# Necessary because Mac OS X does not pass this variable\n")
                    o.write("export LD_LIBRARY_PATH="+os.environ["LD_LIBRARY_PATH"]+"\n\n")
                    o.write(i.read())
            shutil.copymode(scriptName,scriptRun)

            self.warning("Executing modified script",scriptRun,
                         "instead of",scriptName)

        with open(scriptName+".log","w") as outfile:
            ret,txt=execute([scriptRun],
                            workdir=workdir,
                            echo=echo,
                            outfile=outfile,
                            getReturnCode=True)

        if ret not in [0,None]:
            self.info(scriptName,"failed with code",ret)
            if self.opts.failOnScriptFailure:
                self.error("Script",scriptName,"failed with code",ret)

    def __writeToStateFile(self,sol,message):
        """Write a message to a state file"""
        self.__lastMessage=message
        open(path.join(sol.name,"PyFoamState.TheState"),"w").write("Prepare: "+message+"\n")

    def prepare(self,sol,
                cName=None,
                overrideParameters=None,
                numberOfProcessors=None):
        """Do the actual preparing
        :param numberOfProcessors: If set this overrides the value set in the
        command line"""

        didDecompose=False

        if cName==None:
            cName=sol.name

        if self.opts.onlyVariables:
            self.opts.verbose=True

        vals={}
        vals,self.metaData=self.getDefaultValues(cName)
        vals.update(self.addDictValues("System",
                                       "Automatically defined values",
                                       {
                                           "casePath" : '"'+path.abspath(cName)+'"',
                                           "caseName" : '"'+path.basename(path.abspath(cName))+'"',
                                           "foamVersion" : foamVersion(),
                                           "foamFork" : foamFork(),
                                           "numberOfProcessors" : numberOfProcessors if numberOfProcessors!=None else self.opts.numberOfProcessors
                                       }))

        if len(self.opts.extensionAddition)>0:
            vals.update(self.addDictValues("ExtensionAdditions",
                                           "Additional extensions to be processed",
                                           dict((e,True) for e in self.opts.extensionAddition)))

        valsWithDefaults=set(vals.keys())

        self.info("Looking for template values",cName)
        for f in self.opts.valuesDicts:
            self.info("Reading values from",f)
            vals.update(ParsedParameterFile(f,
                                            noHeader=True,
                                            doMacroExpansion=True).getValueDict())

        setValues={}
        for v in self.opts.values:
            v=v.strip()
            self.info("Updating values",v)
            if v[0]=="{" and v[-1]=="}":
                newValues=eval(v)
            else:
                newValues=FoamStringParser(v).data
            vals.update(newValues)
            setValues.update(newValues)

        if overrideParameters:
            vals.update(overrideParameters)

        unknownValues=set(vals.keys())-valsWithDefaults
        if len(unknownValues)>0:
            self.warning("Values for which no default was specified: "+
                         ", ".join(unknownValues))

        if self.opts.verbose and len(vals)>0:
            print_("\nUsed values\n")
            nameLen=max(len("Name"),
                        max([len(k) for k in vals.keys()]))
            format="%%%ds - %%s" % nameLen
            print_(format % ("Name","Value"))
            print_("-"*40)
            for k,v in sorted(iteritems(vals)):
                print_(format % (k,v))
            print_("")
        else:
            self.info("\nNo values specified\n")

        self.checkCorrectOptions(vals)

        derivedScript=path.join(cName,self.opts.derivedParametersScript)
        derivedAdded=None
        derivedChanged=None
        if path.exists(derivedScript):
            self.info("Deriving variables in script",derivedScript)
            scriptText=open(derivedScript).read()
            def printError(*args):
                raise(Exception("Problem in "+derivedScript+"\n"+
                                " ".join(str(a) for a in args)))
            glob={'error':printError}
            oldVals=vals.copy()
            try:
                exec_(scriptText,glob,vals)
            except Exception as e:
                print_(e)
                self.error("Problem in",derivedScript)
            derivedAdded=[]
            derivedChanged=[]
            for k,v in iteritems(vals):
                if k not in oldVals:
                    derivedAdded.append(k)
                elif vals[k]!=oldVals[k]:
                    derivedChanged.append(k)
            if len(derivedChanged)>0 and (not self.opts.allowDerivedChanges and not configuration().getboolean("PrepareCase","AllowDerivedChanges")):
                self.error(self.opts.derivedParametersScript,
                           "changed values of"," ".join(derivedChanged),
                           "\nTo allow this set --allow-derived-changes or the configuration item 'AllowDerivedChanges'")
            if len(derivedAdded)>0:
                self.info("Added values:"," ".join(derivedAdded))
            if len(derivedChanged)>0:
                self.info("Changed values:"," ".join(derivedChanged))
            if len(derivedAdded)==0 and len(derivedChanged)==0:
                self.info("Nothing added or changed")
            if len(derivedAdded+derivedChanged)>0:
                derived=derivedAdded+derivedChanged
                if self.opts.verbose and len(vals)>0:
                    print("\nDerived Values\n")
                    nameLen=max(len("Name"),
                                max([len(k) for k in derived]))
                    format="%%%ds - %%s" % nameLen
                    print_(format % ("Name","Value"))
                    print_("-"*40)
                    for k in sorted(derived):
                        print_(format % (k,vals[k]))
                    print_("")
        else:
            self.info("No script",derivedScript,"for derived values")

        if self.opts.onlyVariables:
            return

        self.__writeToStateFile(sol,"Starting")

        if self.opts.buildExample:
            allrun=open(path.join(cName,"Allrun"),"w")
            allrun.write("""#!/bin/sh
cd ${0%/*} || exit 1                        # Run from this directory
. $WM_PROJECT_DIR/bin/tools/RunFunctions    # Tutorial run functions
""")
        else:
            allrun=None

        if self.opts.doClear:
            self.info("Clearing",cName)
            self.__writeToStateFile(sol,"Clearing")
            if self.opts.buildExample:
                allclean=open(path.join(cName,"Allclean"),"w")
                allclean.write("""#!/bin/sh
cd ${0%/*} || exit 1                        # Run from this directory
. $WM_PROJECT_DIR/bin/tools/RunFunctions    # Tutorial run functions
. $WM_PROJECT_DIR/bin/tools/CleanFunctions  # Tutorial clean functions
    """)
            else:
                allclean=None

            sol.clear(processor=True,
                      pyfoam=True,
                      vtk=True,
                      verbose=True,
                      removeAnalyzed=True,
                      keepParallel=False,
                      clearHistory=False,
                      clearParameters=True,
                      additional=["postProcessing"])
            if allclean:
                allclean.write("\ncleanCase0\n")

            if self.opts.clearCaseScript:
                scriptName=path.join(sol.name,self.opts.clearCaseScript)
                if not path.exists(scriptName):
                    self.error("Script",scriptName,"does not exist")
            elif path.exists(path.join(sol.name,self.defaultClearCase)):
                scriptName=path.join(sol.name,self.defaultClearCase)
            else:
                scriptName=None
                for scr in self.opts.additionalClearCase:
                    s=path.join(sol.name,scr)
                    if path.exists(s):
                        scriptName=s
                        break
            if scriptName:
                self.info("Executing",scriptName,"for case clearing")
                if self.opts.verbose:
                    echo="Clearing: "
                else:
                    echo=None
                if allclean and path.basename(scriptName)!="Allclean":
                    self.executeScript(scriptName,
                                       workdir=sol.name,
                                       echo=echo,
                                       allrun=allclean)
            if allclean:
                allclean.write("\n#------------------------------------------------------------------------------\n")
                allclean.close()

            self.__writeToStateFile(sol,"Done clearing")

        if self.opts.writeParameters:
            fName=path.join(cName,self.parameterOutFile)
            self.info("Writing parameters to",fName)
            with WriteParameterFile(fName,noHeader=True) as w:
                w.content.update(vals,toString=True)
                w["foamVersion"]=vals["foamVersion"]
                w.writeFile()

        if self.opts.writeReport:
            fName=path.join(cName,self.parameterOutFile+".rst")
            self.info("Writing report to",fName)
            with open(fName,"w") as w:
                helper=RestructuredTextHelper(defaultHeading=1)
                w.write(".. title:: "+self.__strip(vals["caseName"])+"\n")
                w.write(".. sectnum::\n")
                w.write(".. header:: "+self.__strip(vals["caseName"])+"\n")
                w.write(".. header:: "+time.asctime()+"\n")
                w.write(".. footer:: ###Page### / ###Total###\n\n")

                w.write("Parameters set in case directory "+
                        helper.literal(self.__strip(vals["casePath"]))+" at "+
                        helper.emphasis(time.asctime())+"\n\n")
                w.write(".. contents::\n\n")
                if len(self.opts.valuesDicts):
                    w.write(helper.heading("Parameter files"))
                    w.write("Parameters read from files\n\n")
                    w.write(helper.enumerateList([helper.literal(f) for f in self.opts.valuesDicts]))
                    w.write("\n")
                if len(setValues)>0:
                    w.write(helper.heading("Overwritten parameters"))
                    w.write("These parameters were set from the command line\n\n")
                    w.write(helper.definitionList(setValues))
                    w.write("\n")
                w.write(helper.heading("Parameters with defaults"))
                w.write(self.makeReport(vals))
                if len(unknownValues)>0:
                    w.write(helper.heading("Unspecified parameters"))
                    w.write("If these parameters are actually used then specify them in "+
                            helper.literal(self.defaultParameterFile)+"\n\n")
                    tab=helper.table(True)
                    for u in unknownValues:
                        tab.addRow(u)
                        tab.addItem("Value",vals[u])
                    w.write(str(tab))
                if not derivedAdded is None:
                    w.write(helper.heading("Derived Variables"))
                    w.write("Script with derived Parameters"+
                            helper.literal(derivedScript)+"\n\n")
                    if len(derivedAdded)>0:
                        w.write("These values were added:\n")
                        tab=helper.table(True)
                        for a in derivedAdded:
                            tab.addRow(a)
                            tab.addItem("Value",str(vals[a]))
                        w.write(str(tab))
                    if len(derivedChanged)>0:
                        w.write("These values were changed:\n")
                        tab=helper.table(True)
                        for a in derivedChanged:
                            tab.addRow(a)
                            tab.addItem("Value",str(vals[a]))
                            tab.addItem("Old",str(oldVals[a]))
                        w.write(str(tab))
                    w.write("The code of the script:\n")
                    w.write(helper.code(scriptText))

        self.addToCaseLog(cName)

        for over in self.opts.overloadDirs:
            self.info("Overloading files from",over)
            self.__writeToStateFile(sol,"Overloading")
            self.overloadDir(sol.name,over)

        self.__writeToStateFile(sol,"Initial")

        zeroOrig=None
        for ext in [self.opts.originalExt]+self.opts.zeroTimeOriginalExtensions:
            zo=path.join(sol.name,"0"+ext)
            if path.exists(zo):
                zeroOrig=zo
                break
        if zeroOrig is None:
            zeroOrig=path.join(sol.name,"0.org")
        zeroOrigShort=path.basename(zeroOrig)
        hasOrig=path.exists(zeroOrig)
        cleanZero=True

        if not hasOrig or self.opts.keepZero:
            self.info("Not going to clean '0'")
            if "0" in self.opts.cleanDirectories:
                self.opts.cleanDirectories.remove("0")
            cleanZero=False
        elif allrun:
            allrun.write("\nrm -rf 0\n")

        if self.opts.doCopy:
            if hasOrig and not self.opts.keepZero:
                self.info("Found",zeroOrigShort,". Clearing 0")
                zeroDir=path.join(sol.name,"0")
                if path.exists(zeroDir):
                    rmtree(zeroDir)
                else:
                    self.info("No 0-directory")

            self.info("")
        else:
            cleanZero=False

        if self.opts.doTemplates:
            self.__writeToStateFile(sol,"Templates")
            self.searchAndReplaceTemplates(sol.name,
                                           vals,
                                           self.opts.templateExt,
                                           ignoreDirectories=self.opts.ignoreDirectories)

            self.info("")

        backupZeroDir=None

        if self.opts.stopAfterTemplates:
            self.info("Stopping because of user request")
            self.__writeToStateFile(sol,"Finished OK")
            return

        if self.opts.doMeshCreate:
            self.__writeToStateFile(sol,"Meshing")
            if self.opts.meshCreateScript:
                scriptName=path.join(sol.name,self.opts.meshCreateScript)
                if not path.exists(scriptName):
                    self.error("Script",scriptName,"does not exist")
            elif path.exists(path.join(sol.name,self.defaultMeshCreate)):
                scriptName=path.join(sol.name,self.defaultMeshCreate)
            else:
                scriptName=None
                for scr in self.opts.additionalMeshCreate:
                    s=path.join(sol.name,scr)
                    if path.exists(s):
                        scriptName=s
                        break
            if scriptName:
                self.info("Executing",scriptName,"for mesh creation")
                if self.opts.verbose:
                    echo="Mesh: "
                else:
                    echo=None
                self.executeScript(scriptName,
                                   workdir=sol.name,
                                   echo=echo,
                                   allrun=allrun)
            else:
                self.info("No script for mesh creation found. Looking for 'blockMeshDict'")
                if sol.blockMesh()!="":
                    self.info(sol.blockMesh(),"found. Executing 'blockMesh'")
                    if allrun:
                        allrun.write("\nrunApplication blockMesh\n")
                    else:
                        bm=BasicRunner(argv=["blockMesh","-case",sol.name])
                        bm.start()
                        if not bm.runOK():
                            self.error("Problem with blockMesh")
                for r in sol.regions():
                    self.info("Checking region",r)
                    s=SolutionDirectory(sol.name,region=r,
                                        archive=None,paraviewLink=self.opts.paraviewFile)
                    if s.blockMesh()!="":
                        self.info(s.blockMesh(),"found. Executing 'blockMesh'")
                        if allrun:
                            allrun.write("\nrunApplication blockMesh -region "+r+"\n")
                        else:
                            bm=BasicRunner(argv=["blockMesh","-case",sol.name,
                                                 "-region",r])
                            bm.start()
                            if not bm.runOK():
                                self.error("Problem with blockMesh")

            self.info("")

            if cleanZero and path.exists(zeroDir):
                self.warning("Mesh creation recreated 0-directory")
                if self.opts.keepZeroDirectoryFromMesh:
                    backupZeroDir=zeroDir+".bakByPyFoam"
                    self.info("Backing up",zeroDir,"to",backupZeroDir)
                    move(zeroDir,backupZeroDir)
                else:
                    self.info("Data in",zeroDir,"will be removed")
            self.__writeToStateFile(sol,"Done Meshing")

        if self.opts.doMeshCreate or self.opts.doMeshDecompose:
            self.__writeToStateFile(sol,"Decompose Mesh")
            if self.opts.decomposeMeshScript:
                scriptName=path.join(sol.name,self.opts.decomposeMeshScript)
                if not path.exists(scriptName):
                    self.error("Script",scriptName,"does not exist")
            elif path.exists(path.join(sol.name,self.defaultDecomposeMesh)):
                scriptName=path.join(sol.name,self.defaultDecomposeMesh)
            else:
                scriptName=None
            if vals["numberOfProcessors"]>1 and scriptName:
                self.info("Executing",scriptName,"for mesh decomposition")
                if self.opts.verbose:
                    echo="Decompose Mesh: "
                else:
                    echo=None
                self.executeScript(scriptName,
                                   workdir=sol.name,
                                   echo=echo,
                                   allrun=allrun)
                didDecompose=True
            else:
                if vals["numberOfProcessors"]>1:
                    self.info("No script for mesh decomposition found")
                else:
                    self.info("No mesh decomposition necessary")

        if self.opts.doCopy:
            self.__writeToStateFile(sol,"Copying")
            self.copyOriginals(sol.name)
            if path.splitext(zeroOrig)[1]!=self.opts.originalExt:
                self.copyOriginals(sol.name,
                                 extension=path.splitext(zeroOrig)[1],
                                 recursive=False)
            self.info("")

            if backupZeroDir:
                self.info("Copying backups from",backupZeroDir,"to",zeroDir)
                self.overloadDir(zeroDir,backupZeroDir)
                self.info("Removing backup",backupZeroDir)
                rmtree(backupZeroDir)

            if hasOrig and allrun:
                allrun.write("\ncp -r "+path.basename(zeroOrig)+" "+
                             path.basename(path.splitext(zeroOrig)[0])+"\n")

        if self.opts.doPostCopy:
            self.__writeToStateFile(sol,"After copying of 0.org")
            if self.opts.postCopyScript:
                scriptName=path.join(sol.name,self.opts.postCopyScript)
                if not path.exists(scriptName):
                    self.error("Script",scriptName,"does not exist")
            elif path.exists(path.join(sol.name,self.defaultPostCopy)):
                scriptName=path.join(sol.name,self.defaultPostCopy)
            else:
                scriptName=None
            if scriptName:
                self.info("Executing",scriptName,"after copying of 0.org")
                if self.opts.verbose:
                    echo="PostCopy: "
                else:
                    echo=None
                self.executeScript(scriptName,
                                   workdir=sol.name,
                                   echo=echo,
                                   allrun=allrun)

        if self.opts.doCopy or self.opts.doFieldDecompose:
            self.__writeToStateFile(sol,"Decompose Fields")
            if self.opts.decomposeFieldsScript:
                scriptName=path.join(sol.name,self.opts.decomposeFieldsScript)
                if not path.exists(scriptName):
                    self.error("Script",scriptName,"does not exist")
            elif path.exists(path.join(sol.name,self.defaultDecomposeFields)):
                scriptName=path.join(sol.name,self.defaultDecomposeFields)
            else:
                scriptName=None
            if vals["numberOfProcessors"]>1 and scriptName:
                self.info("Executing",scriptName,"for fields decomposition")
                if self.opts.verbose:
                    echo="Decompose Fields: "
                else:
                    echo=None
                self.executeScript(scriptName,
                                   workdir=sol.name,
                                   echo=echo,
                                   allrun=allrun)
                didDecompose=True
            else:
                if vals["numberOfProcessors"]>1:
                    self.info("No script for fields decomposition found")
                else:
                    self.info("No field decomposition necessary")

        if self.opts.doPostTemplates:
            self.__writeToStateFile(sol,"Post-templates")
            self.searchAndReplaceTemplates(sol.name,
                                           vals,
                                           self.opts.postTemplateExt,
                                           ignoreDirectories=self.opts.ignoreDirectories)

            self.info("")

        if self.opts.doCaseSetup:
            self.__writeToStateFile(sol,"Case setup")
            if self.opts.caseSetupScript:
                scriptName=path.join(sol.name,self.opts.caseSetupScript)
                if not path.exists(scriptName):
                    self.error("Script",scriptName,"does not exist")
            elif path.exists(path.join(sol.name,self.defaultCaseSetup)):
                scriptName=path.join(sol.name,self.defaultCaseSetup)
            else:
                scriptName=None

            if scriptName:
                self.info("Executing",scriptName,"for case setup")
                if self.opts.verbose:
                    echo="Case:"
                else:
                    echo=None
                self.executeScript(scriptName,
                                   workdir=sol.name,
                                   echo=echo,
                                   allrun=allrun)
            elif path.exists(path.join(sol.name,"system","setFieldsDict")):
                self.info("So setup script found. But 'setFieldsDict'. Executing setFields")
                if allrun:
                    allrun.write("\nrunApplication setFields\n")
                else:
                    sf=BasicRunner(argv=["setFields","-case",sol.name])
                    sf.start()
                    if not sf.runOK():
                        self.error("Problem with setFields")
            else:
                self.info("No script for case-setup found. Nothing done")
            self.info("")
            self.__writeToStateFile(sol,"Done case setup")


        if self.opts.doCaseSetup or self.opts.doCaseDecompose:
            self.__writeToStateFile(sol,"Decompose Case")
            if self.opts.decomposeCaseScript:
                scriptName=path.join(sol.name,self.opts.decomposeCaseScript)
                if not path.exists(scriptName):
                    self.error("Script",scriptName,"does not exist")
            elif path.exists(path.join(sol.name,self.defaultDecomposeCase)):
                scriptName=path.join(sol.name,self.defaultDecomposeCase)
            else:
                scriptName=None
            if vals["numberOfProcessors"]>1 and scriptName:
                self.info("Executing",scriptName,"for case decomposition")
                if self.opts.verbose:
                    echo="Decompose Case: "
                else:
                    echo=None
                self.executeScript(scriptName,
                                   workdir=sol.name,
                                   echo=echo,
                                   allrun=allrun)
                didDecompose=True
            else:
                if vals["numberOfProcessors"]>1:
                    self.info("No script for case decomposition found")
                else:
                    self.info("No case decomposition necessary")

        if self.opts.doFinalTemplates:
            self.__writeToStateFile(sol,"Final templates")
            self.searchAndReplaceTemplates(sol.name,
                                           vals,
                                           self.opts.finalTemplateExt,
                                           ignoreDirectories=self.opts.ignoreDirectories)

        if self.opts.doTemplateClean:
            self.info("Clearing templates")
            if self.opts.buildExample:
                self.opts.cleanDirectories.append(path.curdir)
            for d in self.opts.cleanDirectories:
                for e in [self.opts.templateExt,
                          self.opts.postTemplateExt,
                          self.opts.finalTemplateExt]:
                    self.cleanExtension(path.join(sol.name,d),e)
            self.info("")

        sol.reread(force=True)
        nProcs = sol.nrProcs()

        if vals["numberOfProcessors"]>1 and not didDecompose:
            if nProcs!=vals["numberOfProcessors"]:
                f=self.error
            else:
                f=self.warning
            f("Case should be decomposed to",vals["numberOfProcessors"],
                       "cpus but no decompose script (",self.defaultDecomposeMesh,
                       self.defaultDecomposeFields,self.defaultDecomposeCase,") found")
        if vals["numberOfProcessors"]>1:
            if nProcs!=vals["numberOfProcessors"] and not self.opts.buildExample:
                self.error("Requested",vals["numberOfProcessors"],"but",nProcs,
                           "processor directories present")
        elif nProcs>1:
            self.error(nProcs,"processor directories present although no decomposition was requested")
        self.info("Case setup finished")

        if allrun:
            if vals["numberOfProcessors"]>1:
                allrun.write("runParallel $(getApplication)\n")
            else:
                allrun.write("runApplication $(getApplication)\n")

            allrun.write("\n#------------------------------------------------------------------------------")
            allrun.close()

        if self.opts.buildExample:
            self.info("\nFinal preparations to make this an example case\n")
            import stat,os
            for a in ["Allrun","Allclean"]:
                f=path.join(cName,a)
                self.info("Making",f,"executable")
                st = os.stat(f)
                os.chmod(f, st.st_mode | stat.S_IEXEC)

            from glob import glob as gglob
            for p in ["PyFoamState.TheState","*.foam","*.parameters",self.opts.derivedParametersScript]:
                for f in gglob(path.join(cName,p)):
                    self.info("Removing",f)
                    remove(f)

        self.__writeToStateFile(sol,"Finished OK")
