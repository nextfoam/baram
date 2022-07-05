#  ICE Revision: $Id:$
"""Working with a directory of surface samples

Should be able to generalize this with SampleDirectory, but not right now"""

from os import path,listdir
from glob import glob
from PyFoam.Error import error
import math

class SurfaceDirectory(object):
    """A directory of sampled times"""

    def __init__(self,case,dirName="surfaces"):
        """:param case: The case directory
        :param dirName: Name of the directory with the surfaces"""

        self.dir=path.join(case,dirName)
        self.times=[]

        for d in listdir(self.dir):
            if path.isdir(path.join(self.dir,d)):
                try:
                    v=float(d)
                    self.times.append(d)
                except ValueError:
                    pass

        self.times.sort(key=float)

    def __iter__(self):
        for t in self.times:
            yield SurfaceTime(self.dir,t)

    def __getitem__(self,time):
        if time in self:
            return SurfaceTime(self.dir,time)
        else:
            raise KeyError(time)

    def __contains__(self,time):
        return time in self.times

    def surfaces(self):
        """Returns all the found surfaces"""

        surfaces=[]

        for t in self:
            for l in t.surfaces:
                if l not in surfaces:
                    surfaces.append(l)
        surfaces.sort()

        return surfaces

    def values(self):
        """Returns all the found surface values"""

        values=[]

        for t in self:
            for v in t.values:
                if v not in values:
                    values.append(v)
        values.sort()

        return values

    def getData(self,surface=None,value=None,time=None):
        """Get Surface sets
        :param line: name of the line. All
        if unspecified
        :param value: name of the surfaced value. All
        if unspecified
        :param time: times for which the surfaces are to be got. All
        if unspecified"""

        if surface==None:
            surface=self.surfaces()
        if value==None:
            value=list(self.values())
        if time==None:
            time=self.times

        sets=[]

        for t in time:
            for l in surface:
                for v in value:
                    try:
                        d=self[t][(l,v)]
                        sets.append(d)
                    except KeyError:
                        pass

        return sets

def extractSurface(fName):
    """Extract the name of the line from a filename"""
    return fName.split("_")[1].split(".")[0]

def extractValue(fName):
    """Extracts the names of the contained Values from a filename"""
    return fName.split("_")[0]


class SurfaceTime(object):
    """A directory with one surfaced time"""

    def __init__(self,sDir,time):
        """:param sDir: The surface-dir
        :param time: the timename"""

        self.dir=path.join(sDir,time)
        self.surfaces=[]
        self.values=[]
        self.time=time

        for pth in glob(path.join(self.dir,"*.vtk")):
            f=path.basename(pth)
            nm=extractSurface(f)
            val=extractValue(f)
            if nm not in self.surfaces:
                self.surfaces.append(nm)
            if val not in self.values:
                self.values.append(val)

        self.surfaces.sort()
        self.values.sort()

        self.cache={}

    def __getitem__(self,key):
        """Get the data for a value on a specific line
        :param key: A tuple with the surface-name and the value-name
        :returns: a path to the VTK-file"""

        if key in self.cache:
            return self.cache[key]

        surface,val=key
        if surface not in self.surfaces or val not in self.values:
            raise KeyError(key)

        fName=None

        for pth in glob(path.join(self.dir,"*.vtk")):
            f=path.basename(pth)
            if surface==extractSurface(f) and val==extractValue(f):
                fName=f
                break

        if fName==None:
            error("Can't find a file for the surface",line,"and the value",val,"in the directory",self.dir)

        self.cache[key]=(path.join(self.dir,fName),self.time,surface,val)

        return self.cache[key]

# Should work with Python3 and Python2
