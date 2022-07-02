"""Read files written by the Lagrangian function object that writes patch incidents
and transforms the data into a NumPy-array"""

from PyFoam.ThirdParty.six import BytesIO,b
from .FileBasis import CleanCharactersFile
from .TimeDirectory import TimeDirectory
from .SolutionDirectory import SolutionDirectory

from PyFoam.Error import error

import numpy as np
from os import path

def globalId(proc,theId):
    return proc.astype(np.int64)*1000000000+theId.astype(np.int64)

class LagrangianPatchData:
    """Class to read lagrangian patch data and store it as a NumPy-array"""
    def __init__(self,fName):
        aPath=path.abspath(fName)
        pSep=aPath.split(path.sep)
        self.name=path.splitext(pSep[-1])[0]
        self.time=float(pSep[-2])
        self.function=pSep[-3]
        self.cloudName=pSep[-4]

        f=CleanCharactersFile(fName,charsToRemove="()")
        r=BytesIO(b(f.content))
        hLine=str(r.readline().strip()).replace("'","")

        # missing in some libraries
        if hLine.find("cellI tetFaceI")>0:
            hLine=hLine.replace("cellI tetFaceI","cellI faceI stepFraction tetFaceI")

        header=[str(n) for n in hLine.split()[1:]]
        spec=[]

        for name in header:
            if name in ["currentProc","cellI","faceI","tetFaceI","tetPtI","origProc","origId","typeId"]:
                spec.append((name,"i8"))
            elif name in ["active"]:
                spec.append((name,np.bool_))
            else:
                spec.append((str(name),"f8"))

        self.data=np.recfromtxt(r,dtype=spec)

    def pandas(self):
        """Return data as a pandas Data-frame"""
        import pandas as pd
        df=pd.DataFrame(self.data,index=range(self.data.size)) # index needed for single-line files
        df["cloudName"]=self.cloudName
        df["patchName"]=self.name.replace(".post","")
        df["writeTime"]=self.time
        df["functionName"]=self.function
        df["globalId"]=globalId(df.origProc,df.origId)

        return df

class LagrangianPatchDataTime:
    """Read the lagrangian patch data from a whole timestep"""
    def __init__(self,timeDirName):
        if isinstance(timeDirName,TimeDirectory):
            self.dir=timeDirName.name
            d=timeDirName
        else:
            self.dir=path.abspath(timeDirName)
            d=TimeDirectory(path.dirname(self.dir),path.basename(self.dir))
        self.data={}
        for n in d:
            p=LagrangianPatchData(n.name)
            self.data[p.name]=p
        if len(self.data)<=0:
            error("Directory",self.dir,"has no patch incident data")

    def pandas(self):
        """Return the whole data as one big pandas table"""
        import pandas as pd
        return pd.concat(self.data[n].pandas() for n in self.data)

class LagrangianPatchDataAll:
    """Read the lagrangian patch data for a cloud for a whole cloud (all times)"""
    def __init__(self,cloudDirName):
        self.dir=path.abspath(cloudDirName)
        d=SolutionDirectory(self.dir,paraviewLink=False)
        self.data={}
        for t in d:
            self.data[float(t.baseName())]=LagrangianPatchDataTime(t)

    def pandas(self):
        """Return one huge, ugly pandas table"""
        import pandas as pd
        return pd.concat(self.data[n].pandas() for n in self.data)
