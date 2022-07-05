#  ICE Revision: $Id:$
"""Working with a directory of samples"""

from os import path,listdir
from PyFoam.Error import error
import math
import re

from PyFoam.Basics.SpreadsheetData import SpreadsheetData

class SampleDirectory(object):
    """A directory of sampled times"""

    def __init__(self,
                 case,
                 dirName="samples",
                 postfixes=[],
                 prefixes=[],
                 valueNames=None,
                 linePattern=None,
                 namesFromFirstLine=False,
                 needsExtension=True):
        """:param case: The case directory
        :param dirName: Name of the directory with the samples
        :param postfixes: list of possible extensions to a field name of the form
        name_postfix to help splitting such field names.
        :param prefixes: list of possible extensions to a field name of the form
        prefix_name to help splitting such field names
        :param valueNames: List of value names. If specified then the classes do
        not try to determine the names automatically
        :param linePattern: Regular expression to determine the name of the line
        from the filename. The first group in the expression is the name. If unset
        the linename is determined automatically
        :param needsExtension: whether a file needs an extension"""

        self.dir=path.join(case,dirName)
        self.times=[]

        self.__defaultNames=valueNames
        self.__linePattern=linePattern
        self.__needsExtension=needsExtension
        self.__namesFromFirstLine=namesFromFirstLine

        self.prefixes=prefixes
        self.postfixes=postfixes

        for d in listdir(self.dir):
            if path.isdir(path.join(self.dir,d)):
                try:
                    float(d)
                    self.times.append(d)
                except ValueError:
                    pass

        self.times.sort(key=float)

    def __len__(self):
        return len(self.times)

    def __iter__(self):
        for t in self.times:
            yield SampleTime(self.dir,
                             t,
                             prefixes=self.prefixes,
                             postfixes=self.postfixes,
                             valueNames=self.__defaultNames,
                             namesFromFirstLine=self.__namesFromFirstLine,
                             linePattern=self.__linePattern,
                             needsExtension=self.__needsExtension)

    def __getitem__(self,time):
        if time in self:
            return SampleTime(self.dir,
                              time,
                              prefixes=self.prefixes,
                              postfixes=self.postfixes,
                              valueNames=self.__defaultNames,
                              namesFromFirstLine=self.__namesFromFirstLine,
                              linePattern=self.__linePattern,
                              needsExtension=self.__needsExtension)
        else:
            raise KeyError(time)

    def __contains__(self,time):
        return time in self.times

    def lines(self):
        """Returns all the found sample lines"""

        lines=[]

        for t in self:
            for l in t.lines:
                if l not in lines:
                    lines.append(l)
        lines.sort()

        return lines

    def values(self):
        """Returns all the found sampled values"""

        values=[]

        for t in self:
            for v in t.values:
                if v not in values:
                    values.append(v)
        values.sort()

        return values

    def getData(self,
                line=None,
                value=None,
                time=None,
                note="",
                scale=(1,1),
                offset=(0,0)):
        """Get Sample sets
        :param line: name of the line. All
        if unspecified
        :param value: name of the sampled value. All
        if unspecified
        :param time: times for which the samples are to be got. All
        if unspecified
        :param note: A short annotation (for plots)
        :param scale: pair of factors with which the data is scaled when being plotted
        :param offset: pair of offsets"""

        if line==None:
            line=self.lines()
        if value==None:
            value=list(self.values())
        if time==None:
            time=self.times

        sets=[]

        for t in time:
            for l in line:
                for v in value:
                    try:
                        d=self[t][(l,v)]
                        if d==None:
                            continue
                        d.note=note
                        d.scale=scale
                        d.offset=offset
                        sets.append(d)
                    except KeyError:
                        pass

        return sets

class SampleTime(object):
    """A directory with one sampled time"""

    def __init__(self,
                 sDir,
                 time,
                 postfixes=[],
                 prefixes=[],
                 valueNames=None,
                 namesFromFirstLine=False,
                 linePattern=None,
                 needsExtension=True):
        """:param sDir: The sample-dir
        :param time: the timename
        :param postfixes: list of possible extensions to a field name of the form
        name_postfix to help splitting such field names.
        :param prefixes: list of possible extensions to a field name of the form
        prefix_name to help splitting such field names"""

        self.dir=path.join(sDir,time)
        self.lines=[]
        self.values=[]

        self.prefixes=prefixes
        self.postfixes=postfixes

        self.__valueNames=None
        self.__defaultValueNames=valueNames
        self.__linePattern=linePattern
        self.__namesFromFirstLine=namesFromFirstLine

        for f in listdir(self.dir):
            if f[0]=='.' or f[-1]=='~' or (f.find(".")<0 and needsExtension):
                continue
            nm=self.extractLine(f)
            if nm==None:
                continue
            vals=self.extractValues(f)
            if nm not in self.lines:
                self.lines.append(nm)
            for v in vals:
                if v not in self.values:
                    self.values.append(v)

        self.lines.sort()
        self.values.sort()

        self.cache={}

    def extractLine(self,fName):
        """Extract the name of the line from a filename"""
        if self.__linePattern:
            expr=re.compile(self.__linePattern)
            try:
                return expr.match(fName).groups(1)[0]
            except AttributeError:
                return None
        else:
            return fName.split("_")[0]

    def extractValues(self,fName):
        """Extracts the names of the contained Values from a filename"""

        if self.__defaultValueNames:
            self.__valueNames=self.__defaultValueNames[:]
            return self.__valueNames

        if self.__namesFromFirstLine:
            line=open(path.join(self.dir,fName)).readline().split()
            if line[0]!="#":
                error("First line of",path.join(self.dir,fName),
                      "does not start with a '#'")
            return line[2:]

        def preUnder(m):
            return "&"+m.group(1)+m.group(2)
        def postUnder(m):
            return m.group(1)+m.group(2)+"&"

        for p in self.prefixes:
            fName=re.sub("([_&.]|^)("+p+")_",postUnder,fName)
        for p in self.postfixes:
            fName=re.sub("_("+p+")([_&.]|$)",preUnder,fName)

        self.__valueNames=[]
        try:
            tmp=fName.split("_")[1:]
            tmp[-1]=tmp[-1].split(".")[0]

            for t in tmp:
                self.__valueNames.append(t.replace("&","_"))
        except IndexError:
            pass

        return self.__valueNames

    def __getitem__(self,key):
        """Get the data for a value on a specific line
        :param key: A tuple with the line-name and the value-name
        :returns: A SampleData-object"""

        if key in self.cache:
            return self.cache[key]

        line,val=key
        if line not in self.lines or val not in self.values:
            raise KeyError(key)

        fName=None

        for f in listdir(self.dir):
            if line==self.extractLine(f) and val in self.extractValues(f):
                fName=f
                break

        if fName==None:
            error("Can't find a file for the line",line,"and the value",val,"in the directory",self.dir)

        first=True
        coord=[]
        data=[]
        index=None

        for l in open(path.join(self.dir,fName)).readlines():
            if l.strip()[0]=='#':
                continue

            tmp=l.split()
            if self.__defaultValueNames:
                if len(tmp)!=len(self.__defaultValueNames)+1:
                    error("Number of items in line",l,
                          "is not consistent with predefined name",
                          self.__defaultValueNames)
            if first:
                first=False
                vector,index=self.determineIndex(fName,val,tmp)

            coord.append(float(tmp[0]))
            try:
                if vector:
                    data.append(tuple(map(float,tmp[index:index+3])))
                else:
                    data.append(float(tmp[index]))
            except IndexError:
                raise KeyError(key)

        if index!=None:
            self.cache[key]=SampleData(fName=path.join(self.dir,fName),
                                       name=val,
                                       line=self.extractLine(fName),
                                       index=index,
                                       coord=coord,
                                       data=data)

            return self.cache[key]
        else:
            return None

    def determineIndex(self,fName,vName,data):
        """Determines the index of the data from the filename and a dataset
        :param fName: name of the file
        :param vName: Name of the quantity
        :param data: A list with the data
        :returns: A tuple of a boolean (whether the data is supposed to be
        a vector or a scalar) and an integer (the index of the data set -
        or the first component of the vector"""

        vals=self.extractValues(fName)

        if len(vals)+1==len(data):
            vector=False
        elif len(vals)*3+1==len(data):
            vector=True
        else:
            error("The data in file",fName,"is neither vector nor scalar:",data)

        index=vals.index(vName)
        if vector:
            index=index*3+1
        else:
            index=index+1

        return vector,index

class SampleData(object):
    """Data from a sample-set"""

    def __init__(self,
                 fName,
                 name,
                 line,
                 index,
                 coord,
                 data,
                 note="",
                 scale=(1,1),
                 offset=(0,0)):
        """:param fName: Name of the file
        :param name: Name of the value
        :param index: Index of the data in the file
        :param coord: Values that identify the data (the location)
        :param data: The actual data
        :param scale: pair of factors with which the data is scaled when being plotted
        :param offset: pair of offsets"""

        self.file=fName
        self.coord=coord
        self.data=data
        self.name=name
        self.__line=line
        self.index=index
        self.note=note
        self.scale=scale
        self.offset=offset

    def __repr__(self):
        if self.isVector():
            vect=" (vector)"
        else:
            vect=""

        return "SampleData of %s%s on %s at t=%s " % (self.name,vect,self.line(),self.time())

    def line(self):
        """Get the line of the sample"""
        return self.__line

    def time(self):
        """Get the time of the sample (as a string)"""
        return path.basename(path.dirname(self.file))

    def isVector(self):
        """Is this vector or scalar data?"""
        if type(self.data[0])==tuple:
            return True
        else:
            return False

    def range(self,component=None):
        """Range of the data"""
        data=self.component(component)

        return (min(data),max(data))

    def domain(self):
        """Range of the data domain"""
        return (min(self.coord),max(self.coord))

    def component(self,component=None):
        """Return the data as a number of single scalars.
        :param component: If None for vectors the absolute value is taken.
        else the number of the component"""

        if self.isVector():
            data=[]
            if component==None:
                for d in self.data:
                    data.append(math.sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]))
            else:
                if component<0 or component>=len(self.data[0]):
                    error("Requested component",component,"does not fit the size of the data",len(self.data[0]))
                for d in self.data:
                    data.append(d[component])
            return data
        else:
            return self.data

    def __call__(self,
                 scaleX=1.,
                 scaleData=1,
                 offsetData=0,
                 offsetX=0):
        """Return the data as SpreadsheetData-object"""

        data=[]
        if self.isVector():
            for i,c in enumerate(self.coord):
                data.append([scaleX*c+offsetX]+[scaleData*v+offsetData for v in self.data[i]])
        else:
            for i,c in enumerate(self.coord):
                data.append([scaleX*c+offsetX,scaleData*self.data[i]+offsetData])

        names=["coord"]
        if self.isVector():
            names+=[self.name+"_x",self.name+"_y",self.name+"_z"]
        else:
            names.append(self.name)

        return SpreadsheetData(data=data,
                               names=names,
                               title="%s_t=%s" % (self.line(),self.time()))

# Should work with Python3 and Python2
