#  ICE Revision: $Id$
"""Encapsulate a case and give convenient access to certain applications
"""

from os import path

from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory

from PyFoam.Applications.CaseReport import CaseReport
from PyFoam.Applications.TimelinePlot import TimelinePlot
from PyFoam.Applications.SamplePlot import SamplePlot
from PyFoam.Applications.RedoPlot import RedoPlot

from PyFoam.ThirdParty.six import string_types,StringIO,print_
from PyFoam.ThirdParty.six.moves import cPickle as pickle
from PyFoam.Error import error

from PyFoam.IPythonHelpers import create_code_cell
from PyFoam.IPythonHelpers.PermanentStorage import PermanentStorage

try:
    from docutils.core import publish_parts
except ImportError:
    print_("docutils needs to be installed for this module to work")

try:
    from IPython.display import HTML,display
    import ipywidgets as widgets
    from IPython import get_ipython
except ImportError:
    print_("IPython and ipywidgets need to be installed for this module to work")

class Case(object):
    """This class is initialized with a path and gives access to
    reporting functions

    """

    def __init__(self,input):
        """:param input: either a SolutionDirectory-instance or a string
        with a pathname"""
        if isinstance(input,SolutionDirectory):
            self.__sol=input
        elif isinstance(input,string_types):
            self.__sol=SolutionDirectory(input,
                                         paraviewLink=False,
                                         archive=None)
        else:
            error(type(input),"not supported")

    @property
    def sol(self):
        """The actual solution directory"""
        return self.__sol

    @property
    def path(self):
        """The path to the solution"""
        return self.__sol.name

    @property
    def regions(self):
        """Regions in the case"""
        return self.__sol.getRegions(defaultRegion=True)

    def __callCaseReport(self,region=None,level=3,**kwargs):
        """Helper function that does the actual calling of CaseReport
        and returning of the HTML-formatted output"""
        s=StringIO()

        if region!=None:
            level=level+1

        CaseReport(args=[self.path],
                   region=region,
                   file=s,
                   headingLevel=level,
                   **kwargs)
        return HTML(publish_parts(s.getvalue(),
                                  writer_name='html',
                                  settings_overrides={
                                      "initial_header_level":level,
                                      "doctitle_xform":False
                                  })['html_body'])

    def size(self,region=None,**kwargs):
        return self.__callCaseReport(region=region,
                                     caseSize=True,
                                     **kwargs)

    def boundaryConditions(self,region=None,**kwargs):
        return self.__callCaseReport(region=region,
                                     shortBcReport=True,
                                     **kwargs)

    def longBoundaryConditions(self,region=None,**kwargs):
        return self.__callCaseReport(region=region,
                                     longBcReport=True,
                                     **kwargs)

    def dimensions(self,region=None,**kwargs):
        return self.__callCaseReport(region=region,
                                     dimensions=True,
                                     **kwargs)

    def internalField(self,region=None,**kwargs):
        return self.__callCaseReport(region=region,
                                     internalField=True,
                                     **kwargs)

    def linearSolvers(self,region=None,**kwargs):
        return self.__callCaseReport(region=region,
                                     linearSolvers=True,
                                     **kwargs)

    def relaxationFactors(self,region=None,**kwargs):
        return self.__callCaseReport(region=region,
                                     relaxationFactors=True,
                                     **kwargs)

    def processorMatrix(self,region=None,**kwargs):
        return self.__callCaseReport(region=region,
                                     processorMatrix=True,
                                     **kwargs)

    def decomposition(self,region=None,**kwargs):
        return self.__callCaseReport(region=region,
                                     decomposition=True,
                                     **kwargs)

    def timeline(self,directory,fieldname):
        if isinstance(fieldname,string_types):
            f=[fieldname]
        else:
            f=fieldname
        return TimelinePlot(args=[self.path],
                            directoryName=directory,
                            fields=f,
                            basicMode="lines",
                            pandasData=True)["dataFrame"]

    def timelineInfo(self,directory):
        return TimelinePlot(args=[self.path],
                            directoryName=directory,
                            info=True,
                            silent=True).getData()

    def sampleTime(self,directory,line,time):
        return SamplePlot(args=[self.path],
                          directoryName=directory,
                          line=[line],
                          time=[time],
                          fuzzyTime=True,
                          mode="separate",
                          pandasData=True)["dataFrame"]

    def sampleField(self,directory,line,field):
        return SamplePlot(args=[self.path],
                          directoryName=directory,
                          line=[line],
                          field=[field],
                          mode="separate",
                          pandasData=True)["dataFrame"]

    def sampleInfo(self,directory):
        return SamplePlot(args=[self.path],
                          directoryName=directory,
                          info=True,
                          silent=True).getData()

    def distributionInfo(self,directory):
        return SamplePlot(args=[self.path],
                          directoryName=directory,
                          isDistribution=True,
                          info=True,
                          silent=True).getData()

    def distribution(self,directory,line,time):
        return SamplePlot(args=[self.path],
                          directoryName=directory,
                          isDistribution=True,
                          line=[line],
                          time=[time],
                          fuzzyTime=True,
                          mode="separate",
                          pandasData=True)["dataFrame"]

    def pickledPlots(self,pickleFile):
        return RedoPlot(
            args=[path.join(self.path,pickleFile)],
            pickleFile=True,
            pandasData=True)["plotData"]

    def pickledData(self,pickleFile):
        return pickle.Unpickler(open(path.join(self.path,pickleFile),"rb")).load()

    def __getObjectName(self,obj):
        for ns in get_ipython().all_ns_refs:
            for n,v in ns.items():
                if obj is v:
                    if n[0]!="_":
                        return n
        return "unknown"

    def __getStorageName(self):
        for ns in get_ipython().all_ns_refs:
            for n,v in ns.items():
                if isinstance(v,PermanentStorage):
                   return n,v
        return None

    def timelineSelector(self,directoryName):
        info=self.timelineInfo(directoryName)
        lst=[widgets.Label(value="Fields:")]
        fieldsSelected=set()
        storeButton=widgets.Button(description="Store to",disabled=True)
        def make_field_toggle(fName):
            def f(name,value):
                if value:
                    fieldsSelected.add(fName)
                else:
                    try:
                        fieldsSelected.remove(fName)
                    except KeyError:
                        pass # this should not happen, but hey!
                if len(fieldsSelected)>0:
                    storeButton.disabled=False
                else:
                    storeButton.disabled=True
            return f
        for f in info["fields"]:
            w=widgets.ToggleButton(description=f)
            w.on_trait_change(make_field_toggle(f), 'value')
            lst.append(w)
        fields=widgets.Box(description="Fields",children=lst)
        fields.add_class("hbox")
        varName=widgets.Text(description="Variable Name")
        def varname_change(name,value):
            storeButton.description="Store to "+value
            if len(value)==0 or len(fieldsSelected)==0:
                storeButton.disabled=True
            else:
                dis=False
                if not value[0].isalpha():
                    dis=True
                storeButton.disabled=dis
        varName.on_trait_change(varname_change, 'value')
        def store_clicked(b):
            v=varName.value
            f=list(fieldsSelected)
            print_("Storing",f,"from",directoryName,"in",self.path,"to variable",v)
            name=self.__getObjectName(self)
            store=self.__getStorageName()
            cmd="%s.timeline('%s',%s)" % (name,directoryName,str(f))
            if store:
                sname,sval=store
                create_code_cell(
                    "%s=%s('%s',lambda:%s)" % (v,sname,v,cmd),
                    "below")
                val=sval(v,lambda:self.timeline(directoryName,f))
            else:
                create_code_cell(
                    "%s=%s" % (v,cmd),
                    "below")
                val=self.timeline(directoryName,f)
            get_ipython().push({v:val})
            varName.value=""
        storeButton.on_click(store_clicked)
        total=widgets.Box(children=[fields,varName,storeButton])
        total.add_class("vbox")
        display(total)

    def sampleSelector(self,directoryName):
        info=self.sampleInfo(directoryName)
        mode=widgets.ToggleButtons(description="Mode",values=["Time","Field"])
        field=widgets.Dropdown(description="Field",values=info["values"])
        time=widgets.Dropdown(description="Time",values=info["times"])
                              # ,value=info["times"][-1])
        line=widgets.Dropdown(description="Sample line",values=info["lines"])
        varName=widgets.Text(description="Variable Name")
        storeButton=widgets.Button(description="Store to",disabled=True)
        def mode_changed(name,value):
            if value=="Time":
                time.disabled=False
                field.disabled=True
            else:
                time.disabled=True
                field.disabled=False
        mode.on_trait_change(mode_changed,'value')
        mode_changed('value',mode.value)
        def varname_change(name,value):
            storeButton.description="Store to "+value
            if len(value)==0:
                storeButton.disabled=True
            else:
                dis=False
                if not value[0].isalpha():
                    dis=True
                storeButton.disabled=dis
        varName.on_trait_change(varname_change, 'value')
        def store_clicked(b):
            l=line.value
            v=varName.value
            name=self.__getObjectName(self)
            store=self.__getStorageName()
            if mode.value=="Time":
                t=time.value
                print_("Storing fields at t=",t,"on line",l,"from",directoryName,"in",self.path,"to variable",v)
                cmdBase="%s.sampleTime('%s','%s','%s')" % (name,directoryName,l,t)
                if store:
                    sname,sval=store
                    cmd="%s=%s('%s',lambda:%s)" % (v,sname,v,cmdBase)
                    val=sval(v,lambda:self.sampleTime(directoryName,l,t))
                else:
                    cmd="%s=%s" % (v,cmdBase)
                    val=self.sampleTime(directoryName,l,t)
            elif mode.value=="Field":
                f=field.value
                print_("Storing fields",f," at all times on line",l,"from",directoryName,"in",self.path,"to variable",v)
                cmdBase="%s.sampleField('%s','%s','%s')" % (name,directoryName,l,f)
                if store:
                    sname,sval=store
                    cmd="%s=%s('%s',lambda:%s)" % (v,sname,v,cmdBase)
                    val=sval(v,lambda:self.sampleField(directoryName,l,f))
                else:
                    cmd="%s=%s" % (v,cmdBase)
                    val=self.sampleField(directoryName,l,f)
            else:
                print_("Unknown mode",mode)
                return
            create_code_cell(cmd,"below")
            get_ipython().push({v:val})
            varName.value=""
        storeButton.on_click(store_clicked)
        total=widgets.Box(children=[mode,line,field,time,varName,storeButton])
        total.add_class("vbox")
        display(total)

    def distributionSelector(self,directoryName):
        info=self.distributionInfo(directoryName)
        time=widgets.Dropdown(description="Time",values=info["times"],value=info["times"][-1])
        line=widgets.Dropdown(description="Sample line",values=info["lines"])
        varName=widgets.Text(description="Variable Name")
        storeButton=widgets.Button(description="Store to",disabled=True)
        def varname_change(name,value):
            storeButton.description="Store to "+value
            if len(value)==0:
                storeButton.disabled=True
            else:
                dis=False
                if not value[0].isalpha():
                    dis=True
                storeButton.disabled=dis
        varName.on_trait_change(varname_change, 'value')
        def store_clicked(b):
            l=line.value
            v=varName.value
            name=self.__getObjectName(self)
            store=self.__getStorageName()
            t=time.value
            print_("Storing distribution at t=",t,"on line",l,"from",directoryName,"in",self.path,"to variable",v)
            cmd="%s.distribution('%s','%s','%s')" % (name,directoryName,l,t)
            if store:
                sname,sval=store
                create_code_cell(
                    "%s=%s('%s',lambda:%s)" % (v,sname,v,cmd),
                    "below")
                val=sval(v,lambda:self.distribution(directoryName,l,t))
            else:
                create_code_cell(
                    "%s=%s" % (v,cmd),
                    "below")
                val=self.distribution(directoryName,l,t)
            get_ipython().push({v:val})
            varName.value=""
        storeButton.on_click(store_clicked)
        total=widgets.Box(children=[line,time,varName,storeButton])
        total.add_class("vbox")
        display(total)

    def pickledPlotSelector(self):
        pPlot=widgets.Dropdown(description="Pickled plot file",
                                     values=self.sol.pickledPlots,
                                     value=self.sol.pickledPlots[0])
        varName=widgets.Text(description="Variable Name")
        storeButton=widgets.Button(description="Store to",disabled=True)
        def varname_change(name,value):
            storeButton.description="Store to "+value
            if len(value)==0:
                storeButton.disabled=True
            else:
                dis=False
                if not value[0].isalpha():
                    dis=True
                storeButton.disabled=dis
        varName.on_trait_change(varname_change, 'value')
        def store_clicked(b):
            p=pPlot.value
            v=varName.value
            name=self.__getObjectName(self)
            store=self.__getStorageName()
            print_("Storing Pickled Plot data from",p,"to variable",v)
            cmd="%s.pickledPlots('%s')" % (name,p)
            if store:
                sname,sval=store
                create_code_cell(
                    "%s=%s('%s',lambda:%s)" % (v,sname,v,cmd),
                    "below")
                val=sval(v,lambda:self.pickledPlots(p))
            else:
                create_code_cell(
                    "%s=%s" % (v,cmd),
                    "below")
                val=self.pickledPlots(p)
            get_ipython().push({v:val})
            varName.value=""
        storeButton.on_click(store_clicked)
        total=widgets.Box(children=[pPlot,varName,storeButton])
        total.add_class("vbox")
        display(total)

    def pickledDataSelector(self):
        pData=widgets.Dropdown(description="Pickled data file",
                                     values=self.sol.pickledData,
                                     value=self.sol.pickledData[0])
        varName=widgets.Text(description="Variable Name")
        storeButton=widgets.Button(description="Store to",disabled=True)
        def varname_change(name,value):
            storeButton.description="Store to "+value
            if len(value)==0:
                storeButton.disabled=True
            else:
                dis=False
                if not value[0].isalpha():
                    dis=True
                storeButton.disabled=dis
        varName.on_trait_change(varname_change, 'value')
        def store_clicked(b):
            p=pData.value
            v=varName.value
            name=self.__getObjectName(self)
            store=self.__getStorageName()
            print_("Storing Pickled Data from",p,"to variable",v)
            cmd="%s.pickledData('%s')" % (name,p)
            if store:
                sname,sval=store
                create_code_cell(
                    "%s=%s('%s',lambda:%s)" % (v,sname,v,cmd),
                    "below")
                val=sval(v,lambda:self.pickledData(p))
            else:
                create_code_cell(
                    "%s=%s" % (v,cmd),
                    "below")
                val=self.pickledData(p)
            get_ipython().push({v:val})
            varName.value=""
        storeButton.on_click(store_clicked)
        total=widgets.Box(children=[pData,varName,storeButton])
        total.add_class("vbox")
        display(total)
