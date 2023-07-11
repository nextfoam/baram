"""
Represents the actual CaseBuilder-File and other things that have to do with the Casebuilder
"""

from xml.dom.minidom import parse
from os import path
import os
import shutil
import glob

from PyFoam.Error import error
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile,FoamStringParser
from PyFoam.Execution.BasicRunner import BasicRunner
from PyFoam.FoamInformation import oldAppConvention as oldApp
from .CreateBoundaryPatches import CreateBoundaryPatches
from PyFoam import configuration as config
from PyFoam.Basics.DataStructures import Vector

from PyFoam.ThirdParty.six import exec_

class CaseBuilderDescriptionList(object):
    """Gets a list of the case-builder files found in the current path"""
    def __init__(self):
        dirList=config().get("CaseBuilder","descriptionpath")
        self.list=[]
        for d in dirList:
            for f in glob.glob(path.join(d,"*.pfcb")):
                nm=path.basename(f)
                cb=CaseBuilderFile(f)
                self.list.append((nm,f,cb.name(),cb.description()))

    def __iter__(self):
        for f in self.list:
            yield f

    def __len__(self):
        return len(self.list)

    def __getitem__(self,i):
        return self.list[i]

class ArgWrapper(object):
    """Wraps the argument element for convenient access"""
    def __init__(self,el):
        self.el=el

    def __getattr__(self,name):
        if name=="type":
            tmp=self.el.getElementsByTagName("verify")
            if len(tmp)!=1:
                return None
            val=tmp[0].getElementsByTagName("validator")
            if len(val)!=1:
                return None
            else:
                return val[0].getAttribute("type")
        elif name=="values":
            tmp=self.el.getElementsByTagName("verify")
            if len(tmp)!=1:
                return None
            val=tmp[0].getElementsByTagName("validator")
            if len(val)!=1:
                return None
            else:
                return list(map(str,val[0].getAttribute("values").split("|")))
        else:
            return self.el.getAttribute(name)

class CaseBuilderFile(object):
    """
This class reads an XML-file that describes how to build a case
and gives information about the case and if asked to builds the actual case
"""

    def __init__(self,fName):
        """:param fName: the XML-file that describes how to build the case"""

        dom=parse(fName)
        self.doc=dom.documentElement

        if self.doc.tagName!='casebuilder':
            error("Wrong root-element",self.doc.tagName,"Expected: 'casebuilder'")

    def name(self):
        return self.doc.getAttribute("name")

    def description(self):
        return self.doc.getAttribute("description")

    def helpText(self):
        ht=self.getSingleElement(self.doc,"helptext",optional=True)
        if ht:
            return ht.firstChild.nodeValue
        else:
            return "<No help text>"

    def argTree(self):
        return self.getSingleElement(self.doc,"arguments")

    def varTree(self):
        return self.getSingleElement(self.doc,"variables",optional=True)

    def filesTree(self):
        return self.getSingleElement(self.doc,"files")

    def boundaryTree(self):
        return self.getSingleElement(self.filesTree(),"boundaries")

    def fieldTree(self):
        return self.getSingleElement(self.filesTree(),"fieldfiles")

    def parameterTree(self):
        return self.getSingleElement(self.filesTree(),"parameterfiles")

    def templatePath(self):
        return self.expandVars(self.doc.getAttribute("template"))

    def initialDir(self):
        tmp=self.doc.getAttribute("initialdir")
        if tmp=="":
            tmp="0"
        return tmp

    def expandVars(self,orig,keys=None):
        orig=path.expanduser(orig)
        orig=path.expandvars(orig)
        if keys!=None:
            orig=orig % keys
        return orig

    def boundaries(self):
        bounds=[]

        for a in self.boundaryTree().getElementsByTagName("boundary"):
            bounds.append(a.getAttribute("name"))

        return bounds

    def boundaryPatterns(self):
        bounds=[]

        for a in self.boundaryTree().getElementsByTagName("boundary"):
            bounds.append((a.getAttribute("name"),a.getAttribute("pattern")))

        return bounds

    def boundaryPatternDict(self):
        res={}
        for nm,pat in self.boundaryPatterns():
            res[nm]=pat
        return res

    def boundaryDescriptions(self):
        bounds={}

        for a in self.boundaryTree().getElementsByTagName("boundary"):
            bounds[a.getAttribute("name")]=a.getAttribute("description")

        return bounds

    def argumentGroups(self):
        args=[]

        for a in self.argTree().getElementsByTagName("argumentgroup"):
            args.append(a.getAttribute("name"))

        return args

    def argumentGroupDescription(self):
        args={}

        for a in self.argTree().getElementsByTagName("argumentgroup"):
            args[a.getAttribute("name")]=a.getAttribute("description")

        return args

    def arguments(self):
        args=[]

        for a in self.argTree().getElementsByTagName("arg"):
            args.append(a.getAttribute("name"))

        return args

    def argumentDict(self):
        args={}

        for a in self.argTree().getElementsByTagName("arg"):
            args[a.getAttribute("name")]=ArgWrapper(a)

        return args

    def groupArguments(self,name=None):
        """Returns a list with the arguments belongin to a specific group
        :param name: Name of the group. If none is given, then all the arguments
        belonging to no group are returned"""

        result=[]

        for c in self.argTree().childNodes:
            if "tagName" in dir(c):
                if c.tagName=="arg" and name==None:
                    result.append(c.getAttribute("name"))
                elif c.tagName=="argumentgroup":
                    if c.getAttribute("name")==name:
                        for e in c.getElementsByTagName("arg"):
                            result.append(e.getAttribute("name"))

        return result

    def argumentDescriptions(self):
        args={}

        for a in self.argTree().getElementsByTagName("arg"):
            args[a.getAttribute("name")]=a.getAttribute("description")

        return args

    def argumentDefaults(self):
        args={}

        for a in self.argTree().getElementsByTagName("arg"):
            args[a.getAttribute("name")]=a.getAttribute("default")

        return args

    def getSingleElement(self,parent,name,optional=False):
        """Get an element and check that it is the only one
        :param parent: the parent element
        :param name: The name of the element"""

        tmp=parent.getElementsByTagName(name)
        if len(tmp)<1:
            if optional:
                return None
            else:
                error("Element",name,"does not exist")
        if len(tmp)>1:
            error("More than one element",name,"does exist")
        return tmp[0]

    def makeBC(self,node,args):
        result="'type':'"+node.getAttribute("type")+"'"
        para=self.expandVars(node.getAttribute("parameters"),args)
        if para!="":
            result+=","+para
        return "{"+result+"}"

    def verifyArguments(self,args):
        """Validate the arguments with the provided code (if it exists)"""
        totalMsg=""
        for a in self.argTree().getElementsByTagName("arg"):
            msg=None
            nm=a.getAttribute("name")
            verify=self.getSingleElement(a,"verify",optional=True)
            if verify:
                valid=self.getSingleElement(verify,"validator",optional=True)
                script=self.getSingleElement(verify,"script",optional=True)
                if valid and script:
                    error("Variable",nm,"has script and validator. Only one of them supported")
                elif valid:
                    typ=valid.getAttribute("type")
                    arg=args[nm]
                    isNumeric=False
                    if typ=="float":
                        isNumeric=True
                        try:
                            tmp=float(arg)
                        except ValueError:
                            msg="Not a floating point number"
                    elif typ=="integer":
                        isNumeric=True
                        try:
                            tmp=int(arg)
                        except ValueError:
                            msg="Not an integer number"
                    elif typ=="file":
                        if not path.exists(arg):
                            msg="File "+arg+" does not exist"
                    elif typ=="selection":
                            vals=valid.getAttribute("values").split("|")
                            if not arg in vals:
                                msg="Not in list of possible values: "+", ".join(vals)
                    elif typ=="vector":
                        tmp=FoamStringParser("a "+arg+";")
                        if type(tmp['a'])!=Vector:
                            msg="Is not a valid vector"
                    else:
                        error("No validator implemented for type",typ,"in variable",nm)
                    if isNumeric and not msg:
                        if valid.hasAttribute("min"):
                            if float(arg)<float(valid.getAttribute("min")):
                                msg="Must be bigger than "+valid.getAttribute("min")
                        if valid.hasAttribute("max"):
                            if float(arg)>float(valid.getAttribute("max")):
                                msg="Must be smaller than "+valid.getAttribute("max")

                elif script:
                    if script.getAttribute("plugin")!="python":
                        error("Only plugin-type 'python' is supported for variable",nm)
                    code=script.firstChild.nodeValue
                    arg=args[nm]
                    exec_(code)
                if msg:
                    totalMsg+=nm+": "+msg+"   "

        if totalMsg=="":
            totalMsg=None

        return totalMsg

    def calculateVariables(self,_args_):
        """Add derived variables to the argument dictionary"""

        for _a_ in _args_:
            exec_("%s = '%s'" % (_a_,_args_[_a_]))

        if self.varTree():
            for _a_ in self.varTree().getElementsByTagName("var"):
                _nm_=_a_.getAttribute("name")
                if _nm_ in ["_args_","_a_","_nm_"]:
                    error("Variable",_nm_,"is needed for this routine to work")

                if len(_a_.firstChild.nodeValue)>0:
                    exec_(_a_.firstChild.nodeValue)
                    exec_("_args_['"+_nm_+"']=str("+_nm_+")")

        return _args_

    def buildCase(self,cName,args):
        """Builds the case
        :param cName: The name of the case directory
        :param args: The arguments (as a dictionary)"""

        args=self.calculateVariables(args)

        os.mkdir(cName)

        for d in self.parameterTree().getElementsByTagName("directory"):
            dName=path.join(cName,d.getAttribute("name"))
            if not path.isdir(dName):
                os.mkdir(dName)
            sName=path.join(self.templatePath(),d.getAttribute("name"))
            for f in d.getElementsByTagName("file"):
                dFile=path.join(dName,f.getAttribute("name"))
                shutil.copy(path.join(sName,f.getAttribute("name")),dFile)
                if len(f.getElementsByTagName("parameter"))>0:
                    pf=ParsedParameterFile(dFile)
                    for p in f.getElementsByTagName("parameter"):
                        pName=p.getAttribute("name")
                        pValue=self.expandVars(p.getAttribute("value"),args)
                        exec_("pf"+pName+"="+pValue)
                    pf.writeFile()

        prep=self.getSingleElement(self.doc,"meshpreparation")
        util=prep.getElementsByTagName("utility")
        copy=self.getSingleElement(prep,"copy",optional=True)

        if len(util)>0 and copy:
            error("Copy and utilitiy mesh preparation specified")
        elif len(util)>0:
            for u in util:
                app=u.getAttribute("command")
                arg=self.expandVars(u.getAttribute("arguments"),args)
                argv=[app,"-case",cName]+arg.split()
                if oldApp():
                    argv[1]="."
                run=BasicRunner(argv=argv,silent=True,logname="CaseBuilder.prepareMesh."+app)
                run.start()
                if not run.runOK():
                    error(app,"failed. Check the logs")
        elif copy:
            source=self.expandVars(copy.getAttribute("template"),args)
            time=self.expandVars(copy.getAttribute("time"),args)
            if time=="":
                time="constant"
            shutil.copytree(path.join(source,time,"polyMesh"),
                             path.join(cName,"constant","polyMesh"))
        else:
            error("Neither copy nor utilitiy mesh preparation specified")

        dName=path.join(cName,self.initialDir())
        if not path.isdir(dName):
            os.mkdir(dName)
        sName=path.join(self.templatePath(),self.initialDir())
        for f in self.fieldTree().getElementsByTagName("field"):
            dFile=path.join(dName,f.getAttribute("name"))
            shutil.copy(path.join(sName,f.getAttribute("name")),dFile)
            default=self.makeBC(self.getSingleElement(f,"defaultbc"),args)

            CreateBoundaryPatches(args=["--fix-types",
                                        "--overwrite",
                                        "--clear",
                                        "--default="+default,
                                        dFile])
            bcDict={}
            bounds=self.boundaries()
            for b in f.getElementsByTagName("bc"):
                nm=b.getAttribute("name")
                if nm not in bounds:
                    error("Boundary",nm,"not in list",bounds,"for field",f.getAttribute("name"))
                bcDict[nm]=b

            for name,pattern in self.boundaryPatterns():
                if name in bcDict:
                    default=self.makeBC(bcDict[name],args)
                    CreateBoundaryPatches(args=["--filter="+pattern,
                                                "--overwrite",
                                                "--default="+default,
                                                dFile])

            ic=self.expandVars(self.getSingleElement(f,"ic").getAttribute("value"),args)
            pf=ParsedParameterFile(dFile)
            pf["internalField"]="uniform "+ic
            pf.writeFile()

# Should work with Python3 and Python2
