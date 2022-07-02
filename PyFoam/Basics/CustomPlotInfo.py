#  ICE Revision: $Id: CustomPlotInfo.py,v 52a98a5ace0c 2020-01-31 21:09:38Z bgschaid $
"""Information about custom plots"""

from PyFoam.Basics.TimeLineCollection import TimeLineCollection
from PyFoam.Basics.FoamFileGenerator import makeString
from PyFoam.RunDictionary.ParsedParameterFile import FoamStringParser,PyFoamParserError

from PyFoam.Error import error
from PyFoam.ThirdParty.six import iteritems

from os import path

def cleanString(data):
    if type(data)==str:
        if len(data)>0:
            if data[0]=='"' and data[-1]=='"':
                data=data[1:-1]
            elif data in ["true","on","yes"]:
                data=True
            elif data in ["false","off","no"]:
                data=False
    return data

def encloseString(data):
    if type(data)!=str:
        return data
    if data.find(' ')<0:
        return data
    else:
        return '"'+data+'"'

class CustomPlotInfo(object):
    """Information about a custom plot"""

    nr=1

    def __init__(self,raw=None,name=None,enabled=True):
        """:param raw: The raw data. Either a string for the two legacy-formats or a
        dictionary for the new format
        :param name: Name of the expression (only to be used for the new format)
        :param enabled: Should this plot be actually used?"""
        self.nr=CustomPlotInfo.nr
        CustomPlotInfo.nr+=1

        # Setting sensible default values
        self.name="Custom%02d" % self.nr
        self.theTitle="Custom %d" % self.nr
        if name:
            self.name+="_"+name
            self.id=name
            self.theTitle += " - "+name
        else:
            self.id=self.name

        self.expr=None
        self.titles=[]
        self.accumulation="first"
        self.start=None
        self.end=None
        self.persist=False
        self.raisit=False
        self.enhanced=False
        self.with_="lines"
        self.specialwith={}
        #        self.with_="points"
        self.type="regular";
        self.publisher=None
        self.master=None
        self.alternateTime=None
        self.progress=None
        self.enabled=enabled
        self.xlabel="Time [s]"
        self.ylabel=None
        self.xvalue=None
        self.gnuplotCommands=[]
        self.enhanced=False
        self.stringValues=None
        self.dataTransformations=None
        self.namePrefix=None
        self.timeName=None
        self.validData=None
        self.validMatchRegexp=None
        self.csvName=None
        self.txtName=None
        self.excelName=None
        self.skip_header=0
        self.stripCharacters=None
        self.replaceFirstLine=None
        self.writeFiles=False

        # Legacy format
        if raw==None:
            self.expr=""
        elif type(raw)==str:
            if raw[0]=='{':
                data=eval(raw)
                self.expr=data["expr"]
                if "name" in data:
                    self.name+="_"+data["name"]
                    self.name=self.name.replace(" ","_").replace(path.sep,"Slash")
                    self.theTitle+=" - "+data["name"]
                if "titles" in data:
                    self.titles=data["titles"]
                for o in ["alternateAxis","logscale","alternateLogscale","with","ylabel","y2label"]:
                    if o=="with":
                        use="with_"
                    else:
                        use=o
                    if o in data:
                        self.set(use,data[o])
                if "accumulation" in data:
                    self.accumulation=data["accumulation"]
            else:
                self.expr=raw
        # New format
        else:
            for k in raw:
                data=raw[k]
                if type(data)==str:
                    data=cleanString(data)
                elif type(data)==list:
                    data=[cleanString(d) for d in data]
                if k=="with":
                    k="with_"
                self.set(k,data)

        if self.master is not None and self.publisher is None:
            self.publisher = self.master

        # Sanity check the data
        if self.accumulation not in TimeLineCollection.possibleAccumulations:
            error("Accumulation",self.accumulation,"not in the possible values",TimeLineCollection.possibleAccumulations)

        if self.type in ["data", "dataslave", "datacollector"]:
            if self.csvName is None and self.txtName is None and self.excelName is None:
                error("type 'data' needs either 'csvName' or 'txtName' or 'excelName'",
                      raw)
        elif self.expr==None:
            error("No expression set by data",raw)

    def set(self,key,value):
        setattr(self,key,value)


    def __str__(self):
        return makeString({self.id:self.getDict(wrapStrings=True)})

    def __is_attribute(self,d):
        return isinstance(getattr(self,d),(str,bool,int,list,dict,float)) and d.find("__")<0

    def getDict(self,wrapStrings=False):
        result={}

        for d in dir(self):
            if self.__is_attribute(d):
                if d=="id" or d=="nr":
                    pass
                else:
                    key=d.replace("_","")
                    val=getattr(self,d)
                    if wrapStrings:
                        if type(val)==str:
                            val=encloseString(val)
                        elif type(val)==list:
                            val=[encloseString(v) for v in val]

                result[key]=val
        return result

    def __getattr__(self,name):
        if name.find("__")==0:
            return

        raise AttributeError("'{}' not in custom plot spec:\n{}".format(name,self))

def readCustomPlotInfo(rawData,useName=None):
    """Determines which of the three possible formats for custom-plotting is used
    and returns a list of CustomPlotInfo-objects
    :param rawData: a string that contains the raw data"""
    info=[]

    try:
        data=FoamStringParser(rawData,
                              duplicateCheck=True,
                              doMacroExpansion=True,
                              duplicateFail=False)
        for k,d in iteritems(data.data):
            info.append(CustomPlotInfo(d,name=k))
    except PyFoamParserError:
        for i,l in enumerate(rawData.split('\n')):
            if len(l)>0:
                name=useName
                if i>0 and name!=None:
                    name+=("_%d" % i)
                info.append(CustomPlotInfo(l,name=name))

    return info

def resetCustomCounter():
    """Reset the counter. Use with care"""
    CustomPlotInfo.nr=1

# Should work with Python3 and Python2
