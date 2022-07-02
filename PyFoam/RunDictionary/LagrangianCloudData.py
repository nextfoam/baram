"""Read a directory of lagrangian cloud data"""

from os import path,listdir
from .ParsedParameterFile import ParsedParameterFile,PyFoamParserError
from PyFoam.Error import warning,error
from .LagrangianPatchData import globalId

import re

import numpy as np
import pandas as pd

classTable = {
    "scalarField" : {
        "re": r'(\S+)' ,
        "dtype" : [("val",np.float64)]
    },
    "labelField" : {
        "re": r'(\S+)' ,
        "dtype" : [("val",np.int64)]
    },
    "vectorField" : {
        "re" : r'\((\S+)\s+(\S+)\s+(\S+)\)',
        "dtype" :[("val_"+c,np.float64) for c in "xyz"]
    },
    "positions" : {
        "re" : r'\((\S+)\s+(\S+)\s+(\S+)\)\s+(\S+)',
        "dtype" :[("P"+c,np.float64) for c in "xyz"]+[("cellI",np.int64)]
    }
}

class LagrangianCloudDataDirectory:
    """Read all the cloud data in a directory and put it in a Pandas dataframe"""

    def __init__(self,dirPath):
        self.dir=path.abspath(dirPath)

        size=None

        lst=listdir(self.dir)
        posName=None
        for n in ["positions","positions.gz"]:
            if n in lst:
                lst.remove(n)
                posName=n
        if posName is None:
            error("No positions-file in",dirPath)

        for f in [posName]+lst:
            fullFile=path.join(self.dir,f)

            if path.isdir(fullFile):
                continue

            nm,ext=path.splitext(fullFile)
            name=path.basename(nm)

            # zipped version takes precedence
            if ext=="":
                if path.exists(fullFile+".gz"):
                    continue
            else:
                fullFile=path.join(self.dir,nm)

            try:
                # print("Reading",name)
                cont=ParsedParameterFile(fullFile,
                                         listDictWithHeader=True,
                                         listLengthUnparsed=-1,
                                         preserveComments=False)
            except:
                warning("File",nm,"is not a proper Foam-file. Skipping")
                continue

            try:
                ofClass=cont.header["class"]
            except KeyError:
                warning("File",nm,"has no 'class' in header.Skipping")
                continue

            if name in classTable:
                spec=classTable[name]
            elif ofClass in classTable:
                spec=classTable[ofClass]
            else:
                warning("File",nm,"has unknown class",ofClass,".Skipping")
                continue

            # print("toNumpy")
            parsed=cont.content.toNumpy(spec["re"],spec["dtype"])
            cont=None   # Free memory
            parsed.dtype.names=[n.replace("val",name) for n in parsed.dtype.names]

            if size is None:
                size=parsed.size
            elif size!=parsed.size:
                error("Field",name,"has different size",parsed.size,"than others:",size)

            # print("to DataFrame")
            if name=="positions":
                self.data=pd.DataFrame(parsed)
            else:
                self.data=self.data.join(pd.DataFrame(parsed))

            parsed=None  # Free memory

        if "origId" in self.data and "origProcId" in self.data:
            # print("Sorting")
            self.data["globalId"]=globalId(self.data.origProcId,self.data.origId)
            # self.data["globalId"]="p"+self.data.origProcId.apply(lambda x:"%04d"%x)+"i"+self.data.origId.apply(lambda x:"%08d"%x)
            self.data.sort_values("globalId",
                                  inplace=True)

class LagrangianCloudData:
    """Read the cloud data from a time-step (serial or parallel)"""

    def __init__(self,caseName,cloudName,timeName,parallel=False):
        dirs=[]
        if parallel:
            pNums=[int(f[len("processor"):]) for f in listdir(caseName) if f.find("processor")==0]
            pNums.sort()
            if len(pNums)==0:
                error("No processor directories in",caseName)
            for p in pNums:
                tDir=path.join(caseName,"processor"+str(p),timeName)
                if not path.isdir(tDir):
                    error("No time directory",tDir)
                dirs.append(path.join(tDir,"lagrangian",cloudName))
        else:
            tDir=path.join(caseName,timeName)
            if not path.isdir(tDir):
                error("No time directory",tDir)
            dirs.append(path.join(tDir,"lagrangian",cloudName))

        for d in dirs:
            if not path.isdir(d):
                error("Cloud directory",d,"is missing")

        data=[]
        for i,d in enumerate(dirs):
            d=LagrangianCloudDataDirectory(d).data
            d["nowCpu"]=i
            d["writeTime"]=float(timeName)
            data.append(d)

        self.data=pd.concat(data)
        if "globalId" in self.data:
            # print("Sorting")
            self.data.sort_values("globalId",
                                  inplace=True)
