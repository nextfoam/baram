#  ICE Revision: $Id$
"""
Application class that implements pyFoamComparator
"""

import sys
import re
import string
from xml.dom.minidom import parse
import xml.dom
from os import path,environ,mkdir
from optparse import OptionGroup

from PyFoam.Error import error
from PyFoam.Basics.Utilities import execute,rmtree,copytree
from PyFoam.Execution.AnalyzedRunner import AnalyzedRunner
from PyFoam.Execution.ConvergenceRunner import ConvergenceRunner
from PyFoam.Execution.BasicRunner import BasicRunner
from PyFoam.Execution.UtilityRunner import UtilityRunner
from PyFoam.Execution.ParallelExecution import LAMMachine
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.LogAnalysis.BoundingLogAnalyzer import BoundingLogAnalyzer
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.Basics.CSVCollection import CSVCollection

from .PyFoamApplication import PyFoamApplication
from PyFoam.FoamInformation import changeFoamVersion,injectVariables

from .Decomposer import Decomposer

from PyFoam.ThirdParty.six import print_,iteritems,exec_

class Comparator(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Reads an XML-file that specifies a base case and a parameter-variation
and executes all the variations of that case
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <xmlfile>",
                                   nr=1,
                                   interspersed=True,
                                   **kwargs)

    def addOptions(self):
        solver=OptionGroup(self.parser,
                           "Solver",
                           "Controls the behaviour of the solver")
        self.parser.add_option_group(solver)
        result=OptionGroup(self.parser,
                           "Results",
                           "What should be done with the solver results")
        self.parser.add_option_group(solver)
        behave=OptionGroup(self.parser,
                           "Behaviour",
                           "What should be done and output")
        self.parser.add_option_group(behave)

        behave.add_option("--test",
                          action="store_true",
                          default=False,
                          dest="test",
                          help="Only does the preparation steps but does not execute the actual solver an the end")

        result.add_option("--removeOld",
                          action="store_true",
                          default=False,
                          dest="removeOld",
                          help="Remove the directories from an old run without asking")

        result.add_option("--purge",
                          action="store_true",
                          default=False,
                          dest="purge",
                          help="Remove the case directories after evaluating")

        result.add_option("--no-purge",
                          action="store_true",
                          default=False,
                          dest="nopurge",
                          help="Don't remove the case directories after evaluating")

        solver.add_option("--steady",
                          action="store_true",
                          default=False,
                          dest="steady",
                          help="Only runs the solver until convergence")

        behave.add_option("--showDictionary",
                          action="store_true",
                          default=False,
                          dest="showDict"
                          ,help="Shows the parameter-dictionary after the running of the solver")

        solver.add_option("--no-server",
                          dest="server",
                          default=True,
                          action="store_false",
                          help="Don't start the process-control-server")

    def run(self):
        fName=self.parser.getArgs()[0]

        dom=parse(fName)
        doc=dom.documentElement

        if doc.tagName!='comparator':
            error("Wrong root-element",doc.tagName,"Expected: 'comparator'")

        self.data=ComparatorData(doc)

        purge=False
        if doc.hasAttribute('purge'):
            purge=eval(doc.getAttribute('purge'))
        if self.opts.purge:
            purge=self.opts.purge
        if self.opts.nopurge:
            purge=False

        steady=False
        if doc.hasAttribute('steady'):
            steady=eval(doc.getAttribute('steady'))
        if self.opts.steady:
            purge=self.opts.steady

        print_(" Parameters read OK ")
        print_()

        aLog=open(self.data.id+".overview","w")
        csv=CSVCollection(self.data.id+".csv")

        rDir=self.data.id+".results"
        rmtree(rDir)
        mkdir(rDir)

        calculated=0
        format="%%0%dd" % len(str(len(self.data)))

        for i in range(len(self.data)):
            runID=(format % i)
            print_(runID,end=" ",file=aLog)
            csv["ID"]=runID

            use,para=self.data[i]
            para["template"]=self.data.template
            para["extension"]=self.data.extension
            para["id"]=self.data.id

            if use:
                calculated+=1

            print_("Executing Variation",i+1,"of",len(self.data),end=" ")
            if calculated!=i+1:
                print_("(",calculated,"actually calculated)")
            else:
                print_()

            print_("Parameters:",end=" ")
            for k,v in iteritems(para):
                print_("%s='%s' " % (k,v),end=" ")
                if v.find(" ")>=0 or v.find("\t")>=0:
                    v="'"+v+"'"
                print_(v,end=" ",file=aLog)
                csv[k]=v

            print_()

            if not use:
                print_("Skipping because not all conditions are satisfied")
                csv.clear()
                print_()
                continue

            cName=("%s."+format) % (self.data.id, i)
            log=open(cName+".log","w")

            para["case"]=cName
            print_("Case-directory:",cName)
            para["results"]=path.join(rDir,runID)
            print_("Results directory:",para["results"])
            mkdir(para["results"])

            if path.exists(cName):
                if self.opts.removeOld:
                    print_("   Removing old case-directory")
                    rmtree(cName)
                else:
                    error("Case-directory",cName,"exists")

            print_("   copying template")
            out=copytree(self.data.template,cName)
            print_("---- Copying",file=log)
            for l in out:
                print_(l,end=" ",file=log)

            print_("   preparing")
            ok,erg=self.data.prep.execute(para,log)
            print_(ok,end=" ",file=aLog)
            csv["prepare OK"]=ok

            for i in range(len(erg)):
                print_(erg[i],end=" ",file=aLog)
                csv["Prepare %02d" % i]=erg[i]

            aLog.flush()

            if self.opts.test:
                print_("   Skipping execution")
            else:
                print_("   running the solver")
                sys.stdout.flush()

                if steady:
                    runnerClass=ConvergenceRunner
                else:
                    runnerClass=AnalyzedRunner

                run=runnerClass(BoundingLogAnalyzer(doTimelines=True,progress=True),
                                argv=[self.data.solver,".",cName],
                                silent=True,
                                lam=Command.parallel,
                                server=self.opts.server)

                run.start()
                ok=run.runOK()
                if ok:
                    print_("   executed OK")
                else:
                    print_("   fatal error")

                for aName in run.listAnalyzers():
                    a=run.getAnalyzer(aName)
                    if 'titles' in dir(a):
                        for tit in a.lines.getValueNames():
                            t,v=a.getTimeline(tit)
                            if len(v)>0:
                                para["result_"+aName+"_"+tit]=v[-1]

                print_(run.runOK(),run.lastTime(),run.run.wallTime(),end=" ",file=aLog)
                csv["Run OK"]=run.runOK()
                csv["End Time"]=run.lastTime()
                csv["Wall Time"]=run.run.wallTime()
                csv["Wall Time (Foam)"]=run.totalClockTime()
                csv["CPU Time"]=run.totalCpuTime()
                csv["Wall Time First Step"]=run.firstClockTime()
                csv["CPU Time First Step"]=run.firstCpuTime()

                para["endTime"]=run.lastTime()
                para["runlog"]=run.logFile

                if self.opts.showDict:
                    print_(para)

                print_("   evaluating results")

                ok,erg=self.data.post.execute(para,log)

                if Command.parallel!=None:
                    print_("  Stoping LAM")
                    Command.parallel.stop()
                    Command.parallel=None

                if ok:
                    print_("  Evaluation OK",end=" ")
                else:
                    print_("  Evaluation failed",end=" ")

                if len(erg)>0:
                    print_(":",erg,end=" ")
                print_()

                print_(ok,end=" ",file=aLog)
                for i in range(len(erg)):
                    print_(erg[i],end=" ",file=aLog)
                    csv["Post %02d" % i]=erg[i]

            if purge:
                print_("   removing the case-directory")
                out=rmtree(cName)
                print_("---- Removing",file=log)
                for l in out:
                    print_(l,end=" ",file=log)

            log.close()
            print_()
            print_(file=log)
            aLog.flush()
            csv.write()

        aLog.close()

class ComparatorData(object):
    """ The object that holds the actual data"""

    def __init__(self,doc):
        """
        :param doc: the parsed XML-data from which the object is constructed
        """
        self.name=doc.getAttribute("name")
        if self.name=="":
            error("No name for 'comparator' given")

        base=doc.getElementsByTagName("base")
        if base.length!=1:
            error("One 'base'-element needed. Found",base.length)
        self.__parseBase(base[0])

        self.vList=[]
        for v in doc.getElementsByTagName("variation"):
            self.vList.append(Variation(v))

    def __parseBase(self,e):
        """:param e: The 'base'-element"""

        self.template=path.expandvars(e.getAttribute("template"))
        if self.template=="":
            error("No template is given")
        if not path.exists(self.template):
            error("Template",self.template,"does not exist")
        self.id=path.basename(self.template)
        if e.hasAttribute('extension'):
            self.extension=e.getAttribute('extension')
            self.id+="."+self.extension
        else:
            self.extension=""
        self.solver=e.getAttribute("solver")
        if self.solver=="":
            error("No solver is given")
        prep=e.getElementsByTagName("preparation")
        if prep.length!=1:
            error("One 'preparation'-element needed. Found",prep.length)
        self.prep=PreparationChain(prep[0])
        post=e.getElementsByTagName("evaluation")
        if post.length!=1:
            error("One 'evaluation'-element needed. Found",post.length)
        self.post=EvaluationChain(post[0])

    def __len__(self):
        """:return: The total number of variations"""
        if len(self.vList)==0:
            return 0
        else:
            nr=1
            for v in self.vList:
                nr*=len(v)
            return nr

    def __getitem__(self,nr):
        """:param nr: Number of the variation
        :return:  dictionary with the variation"""
        if nr>=len(self):
            error("Index",nr,"of variation out of bounds: [0,",len(self)-1,"]")
        result={}
        tmp=nr
        conditions=[]
        for v in self.vList:
            if (tmp % len(v))!=0:
                conditions.append(v.condition)

            k,val=v[tmp % len(v)]
            result[k]=val
            tmp/=len(v)

        assert tmp==0

        use=True
        for c in conditions:
            cond=replaceValues(c,result)
            use=use and eval(cond)

        return use,result

class CommandChain(object):
    """Abstract base class for a number of commands"""
    def __init__(self,c):
        """:param c: XML-Subtree that represents the chain"""
        self.commands=[]
        for e in c.childNodes:
            if e.nodeType!=xml.dom.Node.ELEMENT_NODE:
                continue
            if not e.tagName in list(self.table.keys()):
                error("Tagname",e.tagName,"not in table of valid tags",list(self.table.keys()))
            self.commands.append(self.table[e.tagName](e))

    def execute(self,para,log):
        """Executes the chain
        :param para:A dictionary with the parameters
        :param log: Logfile to write to"""

        result=[]
        status=True
        for c in self.commands:

            if c.doIt(para):
                ok,erg=c.execute(para,log)
            else:
                ok,erg=True,[]

            status=ok and status
            if erg!=None:
                if type(erg)==list:
                    result+=erg
                else:
                    result.append(erg)

        return status,result

    def hasObjectOfType(self,typ):
        """Checks whether there is an object of a specific type"""

        for o in self.commands:
            if type(o)==typ:
                return True

        return False

class PreparationChain(CommandChain):
    """Chain of Preparation commands"""
    def __init__(self,c):
        self.table={"genericcommand":GenericCommand,
                    "derived":DerivedCommand,
                    "foamcommand":FoamCommand,
                    "foamutility":FoamUtilityCommand,
                    "initial":InitialCommand,
                    "dictwrite":DictWriteCommand,
                    "setdictionary":SetDictionaryCommand,
                    "decompose":DecomposeCommand,
                    "foamversion":FoamVersionCommand,
                    "changeenvironment":ChangeEnvironmentCommand,
                    "setenv":SetEnvironmentCommand,
                    "boundary":BoundaryCommand}
        CommandChain.__init__(self,c)

class EvaluationChain(CommandChain):
    """Chain of evaluation commands"""
    def __init__(self,c):
        self.table={"genericcommand":GenericCommand,
                    "derived":DerivedCommand,
                    "foamutility":FoamUtilityCommand,
                    "foamcommand":FoamCommand,
                    "dictionary":DictionaryCommand,
                    "reconstruct":ReconstructCommand,
                    "lastresult":LastResultCommand,
                    "changeenvironment":ChangeEnvironmentCommand,
                    "setenv":SetEnvironmentCommand,
                    "copylog":CopyLogCommand}
        CommandChain.__init__(self,c)

def getNonEmpty(e,name,default=None):
    result=e.getAttribute(name)
    if result=="":
        if default==None:
            error("Missing attribute",name,"in element",e.tagName)
        else:
            return default
    return result

def replaceValues(orig,para):
    """Replaces all strings enclosed by $$ with the parameters
    :param orig: the original string
    :param para: dictionary with the parameters"""

    exp=re.compile("\$[^$]*\$")
    tmp=orig

    m=exp.search(tmp)
    while m:
        a,e=m.span()
        pre=tmp[0:a]
        post=tmp[e:]
        mid=tmp[a+1:e-1]

        if not mid in list(para.keys()):
            error("Key",mid,"not existing in keys",list(para.keys()))

        tmp=pre+para[mid]+post

        m=exp.search(tmp)

    return tmp

class Command(object):

    parallel=None

    """Abstract base class of all commands"""
    def __init__(self,c):
        self.data=c

    def doIt(self,para):
        cond=getNonEmpty(self.data,"condition",default="True")
        cond=replaceValues(cond,para)
        return eval(cond)

    def execute(self,vals,log):
        """:param vals: Dictionary with the keywords
        :return: A boolean whether it completed successfully and a list with results (None if no results are generated)"""
        error("Execute not implemented for",type(self))

class GenericCommand(Command):
    """Executes a shell command"""
    def __init__(self,c):
        Command.__init__(self,c)
        self.command=c.firstChild.data

    def execute(self,para,log):
        cmd=replaceValues(self.command,para)
        print_("     Executing ",cmd,end=" ")
        sys.stdout.flush()
        out=execute(cmd)

        if len(out)>0:
            print_(" -->",len(out),"lines output")
            for l in out:
                print_("---- Command:",cmd,file=log)
                print_(l,end=" ",file=log)
        else:
            print_()

        return True,None

class DerivedCommand(Command):
    """Derives an additional value"""
    def __init__(self,c):
        Command.__init__(self,c)
        self.name=getNonEmpty(c,"name")
        self.expression=getNonEmpty(c,"expression")

    def execute(self,para,log):
        tmp=replaceValues(self.expression,para)
        try:
            val=eval(tmp)
        except SyntaxError:
            error("Syntax error in",tmp)
        print_("     Setting",self.name,"to",val)
        para[self.name]=str(val)

        return True,None

class DictionaryCommand(Command):
    """Returns values from the chains dictionaries"""
    def __init__(self,c):
        Command.__init__(self,c)
        self.key=getNonEmpty(c,"key")

    def execute(self,para,log):
        if self.key in para:
            return True,para[self.key]
        else:
            print_("-----> ",self.key,"not in set of valid keys",list(para.keys()))
            print_(self.key,"not in set of valid keys of dictionary",para,file=log)
            return False,None

class SetDictionaryCommand(Command):
    """Sets value in the chains dictionaries"""
    def __init__(self,c):
        Command.__init__(self,c)
        self.key=getNonEmpty(c,"key")
        self.value=getNonEmpty(c,"value")

    def execute(self,para,log):
        para[self.key]=self.value
        return True,None

class FoamVersionCommand(Command):
    """Changes the used OpenFOAM-version"""
    def __init__(self,c):
        Command.__init__(self,c)
        self.version=getNonEmpty(c,"version")

    def execute(self,para,log):
        print_("     Changing OpenFOAM-Version to",self.version)
        changeFoamVersion(self.version)

        return True,None

class SetEnvironmentCommand(Command):
    """Sets an environment variable"""
    def __init__(self,c):
        Command.__init__(self,c)
        self.var=getNonEmpty(c,"variable")
        self.val=getNonEmpty(c,"value")

    def execute(self,para,log):
        val=replaceValues(self.val,para)
        var=replaceValues(self.var,para)
        print_("     Setting variable",var,"to",val)
        environ[var]=val

        return True,None

class ChangeEnvironmentCommand(Command):
    """Changes Environment variables by executing a script-file"""
    def __init__(self,c):
        Command.__init__(self,c)
        self.script=getNonEmpty(c,"scriptfile")

    def execute(self,para,log):
        script=replaceValues(self.script,para)
        print_("     Changing environment variables by executing",script)
        injectVariables(script)

        return True,None

class DecomposeCommand(Command):
    """Decomposes a case and generates the LAM"""
    def __init__(self,c):
        Command.__init__(self,c)
        self.cpus=getNonEmpty(c,"cpus")
        self.hostfile=getNonEmpty(c,"hostfile",default="")
        self.options=getNonEmpty(c,"options",default="")

    def execute(self,para,log):
        nr=int(replaceValues(self.cpus,para))
        machines=replaceValues(self.hostfile,para)
        options=replaceValues(self.options,para)

        if nr>1:
            print_("     Decomposing for",nr,"CPUs")
            Decomposer(args=[para['case'],str(nr)]+options.split()+["--silent"])
            Command.parallel=LAMMachine(nr=nr,machines=machines)
        else:
            print_("     No decomposition done")

        return True,None

class ReconstructCommand(Command):
    """Reconstructs a case and deleted the LAM"""
    def __init__(self,c):
        Command.__init__(self,c)
        self.onlyLatest=False
        if c.hasAttribute('onlyLatest'):
            self.onlyLatest=eval(c.getAttribute('onlyLatest'))

    def execute(self,para,log):
        if Command.parallel!=None:
            print_("     Doing reconstruction")
            argv=["reconstructPar",".",para['case']]
            if self.onlyLatest:
                argv.append("-latestTime")
            run=BasicRunner(argv=argv,silent=True,logname="Reconstruction")
            run.start()
            Command.parallel.stop()
        else:
            print_("     No reconstruction done")
        Command.parallel=None

        return True,None

class FoamCommand(Command):
    """Executes a OpenFOAM-utility"""
    def __init__(self,c):
        Command.__init__(self,c)
        self.utility=getNonEmpty(c,"utility")
        self.options=c.getAttribute("options")

    def execute(self,para,log):
        argv=[self.utility,".",para['case']]+self.options.split()
        print_("     Executing"," ".join(argv),end=" ")
        sys.stdout.flush()
        run=BasicRunner(argv,silent=True,lam=Command.parallel,logname="_".join(argv))
        run.start()
        if run.runOK():
            print_()
        else:
            print_("---> there was a problem")

        return run.runOK(),None

class FoamUtilityCommand(FoamCommand):
    """Executes a OpenFOAM-utility and extracts information"""
    def __init__(self,c):
        FoamCommand.__init__(self,c)
        self.regexp=getNonEmpty(c,"regexp")

    def execute(self,para,log):
        argv=[self.utility,".",para['case']]+self.options.split()
        print_("     Executing and analyzing"," ".join(argv),end=" ")
        sys.stdout.flush()
        run=UtilityRunner(argv,silent=True,lam=Command.parallel,logname="_".join(argv))
        run.add("data",self.regexp)
        run.start()
        data=run.analyzer.getData("data")
        result=None
        if data!=None:
            result=[]
            for a in data:
                result.append(a)
        if result==None:
            print_("no data",end=" ")
        else:
            print_(result,end=" ")

        if run.runOK():
            print_()
        else:
            print_("---> there was a problem")

        return run.runOK(),result

class SetterCommand(Command):
    """Common class for commands that operate on dictionaries"""
    def __init__(self,c):
        Command.__init__(self,c)
        self.value=c.getAttribute("value")

    def execute(self,para,log):
        f=replaceValues(self.filename,para)
        v=replaceValues(self.value,para)
        s=replaceValues(self.subexpression,para)
        k=replaceValues(self.key,para)

        try:
            dictFile=ParsedParameterFile(f,backup=True)
            val=dictFile[k]
        except KeyError:
            self.error("Key: ",k,"not existing in File",f)
        except IOError:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            self.error("Problem with file",k,":",e)

        try:
            exec_("dictFile[k]"+s+"=v")
        except Exception:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            error("Problem with subexpression:",sys.exc_info()[0],":",e)

        dictFile.writeFile()

        return True,None

class FieldSetterCommand(SetterCommand):
    """Common class for commands that set values on fields"""
    def __init__(self,c):
        SetterCommand.__init__(self,c)
        self.field=c.getAttribute("field")
        self.filename=path.join("$case$","0",self.field)

class InitialCommand(FieldSetterCommand):
    """Sets an initial condition"""
    def __init__(self,c):
        FieldSetterCommand.__init__(self,c)
        self.key="internalField"
        self.subexpression=""

    def execute(self,para,log):
        print_("     Setting initial condition for",self.field)
        return FieldSetterCommand.execute(self,para,log)

class BoundaryCommand(FieldSetterCommand):
    """Sets a boundary condition"""
    def __init__(self,c):
        FieldSetterCommand.__init__(self,c)
        self.patch=c.getAttribute("patch")
        self.key="boundaryField"
        self.subexpression="['"+self.patch+"']"
        self.element=c.getAttribute("element")
        if self.element=="":
            self.element="value"
        self.subexpression+="['"+self.element+"']"

    def execute(self,para,log):
        print_("     Setting",self.element,"on",self.patch,"for",self.field)
        return FieldSetterCommand.execute(self,para,log)

class DictWriteCommand(SetterCommand):
    """Writes a value to a dictionary"""
    def __init__(self,c):
        SetterCommand.__init__(self,c)
        self.dir=c.getAttribute("directory")
        self.dict=c.getAttribute("dictionary")
        self.filename=path.join("$case$",self.dir,self.dict)
        self.key=c.getAttribute("key")
        self.subexpression=c.getAttribute("subexpression")
        self.value=c.getAttribute("value")

    def execute(self,para,log):
        print_("     Manipulating",self.key,"in",self.dict)
        return SetterCommand.execute(self,para,log)

class LastResultCommand(Command):
    """Copies the result of the last time-step to the resultsd directory"""
    def __init__(self,c):
        Command.__init__(self,c)

    def execute(self,para,log):
        print_("     Copy last result")
        sol=SolutionDirectory(para["case"],archive=None)
        sol.addToClone(sol.getLast())
        sol.cloneCase(path.join(para["results"],para["id"]))
        return True,None

class CopyLogCommand(Command):
    """Copies the log file to the results"""
    def __init__(self,c):
        Command.__init__(self,c)

    def execute(self,para,log):
        print_("     Copy logfile")
        copyfile(para["runlog"],para["results"])
        return True,None

class Variation(object):
    """Represents one variation"""

    def __init__(self,e):
        """:param e: the XML-data from which it is created"""

        self.name=e.getAttribute("name")
        if self.name=="":
            error("No name for 'variation' given")
        self.key=e.getAttribute("key")
        if self.key=="":
            error("No key for 'variation'",self.name," given")
        self.condition=e.getAttribute("condition")
        if self.condition=="":
            self.condition="True"
        self.values=[]
        for v in e.getElementsByTagName("value"):
            self.values.append(str(v.firstChild.data))

    def __str__(self):
        return "Variation "+self.name+" varies "+self.key+" over "+str(self.values)

    def __len__(self):
        """:return: number of values"""
        return len(self.values)

    def __getitem__(self,key):
        return self.key,self.values[key]

# Should work with Python3 and Python2
