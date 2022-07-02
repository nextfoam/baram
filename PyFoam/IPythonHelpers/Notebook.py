#  ICE Revision: $Id$
"""Read and create IPython-Notebooks
"""

import json
from copy import deepcopy
from time import asctime

from PyFoam.Error import error,warning

from PyFoam.ThirdParty.six import string_types,text_type,u

class Notebook(object):
    """Class that represents an IPython-notebook in memory"""

    def __init__(self,input=None,
                 nbformat=3,
                 nbformat_minor=0,
                 name=None):
        """:param input: If this is a string then it is interpreted as
        a filename. Otherwise as a filehandle. If unset then an empty
        notebook is contructed
        :param name: name of the notebook. Only used if a new notebook is created
        """
        self.__content={}
        if input==None:
            if name==None:
                error("Specify at least a name")
            self.__content={
                u("metadata") : {
                    u("name"):text_type(name),
                    u("pyFoam") : {
                        u("createdBy") : "pyFoam",
                        u("createdTime") : asctime()
                    }
                },
                u("nbformat") : nbformat,
                u("nbformat_minor") : nbformat_minor,
                u("worksheets") : [
                    {
                        u("cells"):[]
                    }
                ]
            }
        else:
            if isinstance(input,string_types):
                fh=open(input)
            else:
                fh=input
            self.__content=json.load(fh)
            if ("metadata" not in self.__content or
                "name" not in self.__content["metadata"] or
                "nbformat" not in self.__content or
                "worksheets" not in self.__content):
                error(str(input),"Notebook does not have the expected format")
            if len(self.__content["worksheets"])>1:
                warning(str(input),"has more than one worksheet. Only using the first")
            elif len(self.__content["worksheets"])==0:
                error(str(input),"has no worksheets")
            if "cells" not in self.__content["worksheets"][0]:
                error(str(input),"has no cells")
            self.reset([Cell(**c) for c in self])
            if u("pyFoam") not in self.__content[u("metadata")]:
                self.__content[u("metadata")][u("pyFoam")]={
                    u("createdBy") : "other",
                    u("createdTime") : "unknown"
                }

    @property
    def raw(self):
        return self.__content

    @property
    def name(self):
        return self.__content["metadata"]["name"]

    @name.setter
    def name(self,newName):
        self.__content["metadata"]["name"]=newName

    def _cells(self):
        return self.__content["worksheets"][0]["cells"]

    def reset(self,new):
        self.__content["worksheets"][0]["cells"]=new

    def __iter__(self):
        for c in self._cells():
            yield c

    def __len__(self):
        return len(self._cells())

    def __addCell(self,**kwargs):
        data=Cell(**kwargs)
        for ct in ["input","source"]:
            if ct in data:
                if isinstance(data[ct],string_types):
                    raw=[text_type(l) for l in data[ct].split("\n")]
                    data[ct]=[l+"\n" for l in raw[:-1]]+raw[-1:]
        self._cells().append(data)

    def pyFoamMetaData(self):
        """Our very own metadata-dictionary"""
        try:
            return self.__content["metadata"]["pyFoam"]
        except KeyError:
            self.__content["metadata"]["pyFoam"]={}
            return self.__content["metadata"]["pyFoam"]

    def addHeading(self,title,level=1,**kwargs):
        self.__addCell(cell_type=u("heading"),
                       source=title,
                       level=level,
                       **kwargs)

    def addCode(self,input,collapsed=False,language=u("python"),**kwargs):
        self.__addCell(cell_type=u("code"),
                       collapsed=collapsed,
                       input=input,
                       language=text_type(language),
                       outputs=[],
                       **kwargs)

    def addMarkdown(self,text,**kwargs):
        self.__addCell(cell_type=u("markdown"),
                       source=text,
                       **kwargs)

    def addRaw(self,text,**kwargs):
        self.__addCell(cell_type=u("raw"),
                       source=text,
                       **kwargs)

    def writeToFile(self,fName):
        self.__content[u("metadata")][u("pyFoam")][u("modificationTime")]=asctime()
        with open(fName,"w") as fh:
            json.dump(self.__content,
                      fh,
                      indent=1)

class Cell(dict):
    """Wrapper for the dictionaries that represent notebook cells.
    Mostly for conveniently querying metadata"""

    def __init__(self,classes=(),pyFoam={},**kwargs):
        dict.__init__(self,deepcopy(kwargs))
        if not u("metadata") in self:
            self[u("metadata")]={}
        if len(classes)>0 or  len(pyFoam)>0:
            py=deepcopy(pyFoam)
            if not "pyFoam" in self[u("metadata")]:
                self[u("metadata")]["pyFoam"]=py
            else:
                self[u("metadata")]["pyFoam"].update(py)
        if len(classes)>0:
            if isinstance(classes,string_types):
                self[u("metadata")]["pyFoam"]["classes"]=(classes,)
            else:
                cl=deepcopy(classes)
                self[u("metadata")]["pyFoam"]["classes"]=tuple(cl)

    def meta(self):
        return self[u("metadata")]

    def isClass(self,name):
        """Checks whether a cell is of a specific class. If a string is passed
        the string is checked. Otherwise it is assumed that it is a container
        and the """
        try:
            if isinstance(name,string_types):
                return name in self[u("metadata")]["pyFoam"]["classes"]
            else:
                for n in name:
                    if n in self[u("metadata")]["pyFoam"]["classes"]:
                        return True
                return False

        except KeyError:
            return False
