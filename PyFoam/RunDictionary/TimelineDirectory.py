#  ICE Revision: $Id:$
"""Working with a directory of timelines

Currently not optimal as it reads the files more often than necessary"""

from os import path,listdir

from PyFoam.Error import error,warning
import math

try:
    from sys.float_info import max as float_maximum
except ImportError:
    # needed py python2.5
    float_maximum=1e301

from PyFoam.Basics.SpreadsheetData import SpreadsheetData

from PyFoam.ThirdParty.six import PY3

if PY3:
    from functools import reduce

class TimelineDirectory(object):
    """A directory of sampled times"""

    def __init__(self,case=None,dirName="probes",writeTime=None):
        """:param case: The case directory
        :param dirName: Name of the directory with the timelines
        :param writeTime: The write time-directory where the data in question is to be plotted"""

        if case is None:
            self.dir=dirName
        else:
            self.dir=path.join(case,dirName)
        self.writeTimes=[]

        nearest=None

        for d in listdir(self.dir):
            if path.isdir(path.join(self.dir,d)):
                try:
                    v=float(d)
                    self.writeTimes.append(d)
                    if writeTime:
                        if nearest==None:
                            nearest=d
                        else:
                            if abs(float(writeTime)-v)<abs(float(writeTime)-float(nearest)):
                                nearest=d
                except ValueError:
                    pass

        self.writeTimes.sort(key=float)
        if nearest==None:
            self.usedTime=self.writeTimes[0]
        else:
            self.usedTime=nearest

        self.dir=path.join(self.dir,self.usedTime)

        self.values=[]
        self.vectors=[]
        for v in listdir(self.dir):
            if v[0]=='.':
                continue # Skip dot-files
            tv=TimelineValue(self.dir,v,self.usedTime)
            if tv.isValid:
                self.values.append(v)
                if tv.isVector:
                    self.vectors.append(v)

        self.allPositions=None

    def __iter__(self):
        for t in self.values:
            yield TimelineValue(self.dir,t,self.usedTime)

    def __getitem__(self,value):
        if value in self:
            return TimelineValue(self.dir,value,self.usedTime)
        else:
            raise KeyError(value)

    def __contains__(self,value):
        return value in self.values

    def __len__(self):
        return len(self.values)

    def positions(self):
        """Returns all the found positions"""

        if self.allPositions==None:
            positions=[]
            first=True

            for t in self:
                for v in t.positions:
                    if v not in positions:
                        if first:
                            positions.append(v)
                        else:
                            error("Found positions",t.positions,"are inconsistent with previous",positions)
                if first:
                    self.positionIndex=t.positionIndex
                first=False
            self.allPositions=positions

        return self.allPositions

    def timeRange(self):
        """Return the range of possible times"""
        minTime=1e80
        maxTime=-1e80

        for v in self:
            mi,ma=v.timeRange()
            minTime=min(mi,minTime)
            maxTime=max(ma,maxTime)

        return minTime,maxTime

    def getDataLocation(self,value=None,position=None,vectorMode=None):
        """Get Timeline sets
        :param value: name of the value. All
        if unspecified
        :param position: name of the position of the value. All
        if unspecified"""

        if value==None:
            value=self.values
        if position==None:
            position=self.positions()

        sets=[]

        for v in value:
            for p in position:
                fName=path.join(self.dir,v)
                if not "positionIndex" in self:
                    self.positions()
                pos=self.positionIndex[self.positions().index(p)]
                if v in self.vectors:
                    fName="< tr <%s -d '()'" %fName
                    pos=pos*3
                    if vectorMode=="x":
                        pass
                    elif vectorMode=="y":
                        pos+=1
                    elif vectorMode=="z":
                        pos+=2
                    elif vectorMode=="mag":
                        pos+=2
                        pos="(sqrt($%d*$%d+$%d*$%d+$%d*$%d))" % (pos,pos,
                                                                 pos+1,pos+1,
                                                                 pos+2,pos+2)
                    else:
                        error("Unsupported vector mode",vectorMode,"for",value)
                try:
                    sets.append((fName,v,p,pos,TimelineValue(self.dir,v,self.usedTime)))
                except IOError:
                    # seems like the file/field is not there
                    pass

        return sets

    def getData(self,times,value=None,position=None,vectorMode=None):
        """Get data that mstches the given times most closely
        :param times: a list with times
        :param value: name of the value. All
        if unspecified
        :param position: name of the position of the value. All
        if unspecified
        :param vectorMode: which component of the vector to use"""

        if value==None:
            value=self.values
        if position==None:
            position=self.positions()

        sets=[]
        posIndex=[]
        for p in position:
            posIndex.append(self.positions().index(p))

        for v in value:
            val=TimelineValue(self.dir,v,self.usedTime)
            data=val.getData(times,vectorMode=vectorMode)
            for i,t in enumerate(times):
                used=[]
                for p in posIndex:
                    used.append(data[i][p])

                sets.append((v,t,used))

        return sets

class TimelineValue(object):
    """A file with one timelined value"""

    def __init__(self,sDir,val,time):
        """:param sDir: The timeline-dir
        :param val: the value
        :param time: the timename"""

        self.isValid=False
        self.val=val
        self.time=time
        self.file=path.join(sDir,val)
        poses=[]

        self.isVector=False

        data=open(self.file)
        l1=data.readline()
        if len(l1)<1 or l1[0]!='#':
            error("Data file",self.file,"has no description of the fields")
        l2=data.readline()

        self._isProbe=True
        try:
            if l2[0]!='#':
                # Not a probe-file. The whole description is in the first line
                poses=l1[1:].split()[1:]
                firstData=l2
                self._isProbe=False
            else:
                import re
                newProbe=re.compile(r"# Probe [0-9]+ (\(.+ .+ .+\))")
                if newProbe.match(l1):
                    probeStrings=[l1]
                    while newProbe.match(l2):
                        probeStrings.append(l2)
                        l2=data.readline()
                    probeNrString=l2
                    probeTimeString=data.readline()
                    poses=[newProbe.match(l).group(1) for l in probeStrings]
                    if probeNrString[0]!="#" or probeTimeString[0]!="#":
                        warning("This does not seem to be the format we were lookin for")
                else:
                    # probe-file so we need one more line
                    l3=data.readline()
                    x=l1[1:].split()[1:]
                    y=l2[1:].split()[1:]
                    z=l3[1:].split()[1:]
                    for i in range(len(x)):
                        poses.append("(%s %s %s)" % (x[i],y[i],z[i]))
                    data.readline()
                firstData=data.readline()
        except IndexError:
            warning("Could not determine the type of",self.file)
            return

        self.positions=[]
        self.positionIndex=[]
        if len(poses)+1==len(firstData.split()):
            #scalar
            for i,v in enumerate(firstData.split()[1:]):
                try:
                    if abs(float(v))<float_maximum:
                        self.positions.append(poses[i])
                        self.positionIndex.append(i)
                except ValueError:
                    # Assuming string
                    self.positions.append(poses[i])
                    self.positionIndex.append(i)
        elif 3*len(poses)+1==len(firstData.split()):
            self.isVector=True
            for i,v in enumerate(firstData.split()[2::3]):
                if abs(float(v))<float_maximum:
                    self.positions.append(poses[i])
                    self.positionIndex.append(i)
        else:
            warning(self.file,
                    "is an unsupported type (neither vector nor scalar). Skipping")
            return

        self.cache={}
        self.isValid=True

    def __repr__(self):
        if self.isVector:
            vect=" (vector)"
        else:
            vect=""

        return "TimelineData of %s%s on %s at t=%s " % (self.val,vect,str(self.positions),self.time)

    def isProbe(self):
        """Is this a probe-file"""
        return self._isProbe

    def timeRange(self):
        """Range of times"""
        lines=open(self.file).readlines()
        for l in lines:
            v=l.split()
            if v[0][0]!='#':
                minRange=float(v[0])
                break
        lines.reverse()
        for l in lines:
            v=l.split()
            if len(v)>=len(self.positions)+1:
                maxRange=float(v[0])
                break

        return minRange,maxRange

    def getData(self,times,vectorMode=None):
        """Get the data values that are nearest to the actual times"""
        if self.isVector and vectorMode==None:
            vectorMode="mag"

        dist=len(times)*[1e80]
        data=len(times)*[len(self.positions)*[1e80]]

        lines=open(self.file).readlines()

        for l in lines:
            v=l.split()
            if v[0][0]!='#':
                try:
                    time=float(v[0])
                    vals=[x.replace('(','').replace(')','') for x in v[1:]]
                    for i,t in enumerate(times):
                        if abs(t-time)<dist[i]:
                            dist[i]=abs(t-time)
                            data[i]=vals
                except ValueError:
                    pass
        result=[]
        for d in data:
            tmp=[]
            if self.isVector:
                for p in range(len(self.positions)):
                    if vectorMode=="x":
                        tmp.append(float(d[p]))
                    elif vectorMode=="y":
                        tmp.append(float(d[p+1]))
                    elif vectorMode=="z":
                        tmp.append(float(d[p+2]))
                    elif vectorMode=="mag":
                        tmp.append(math.sqrt(reduce(lambda a,b:a+b,[float(v)**2 for v in d[p:p+3]],0)))
                    else:
                        error("Unknown vector mode",vectorMode)
            else:
                for v in d:
                    try:
                        if abs(float(v))<1e40:
                            tmp.append(float(v))
                    except ValueError:
                        tmp.append(v)
            result.append(tmp)

        return result

    def __call__(self,addTitle=True):
        """Return the data as a SpreadsheetData-object"""

        def safeFloat(v):
            try:
                return float(v)
            except ValueError:
                return v
        lines=open(self.file).readlines()
        data=[]
        for l in lines:
            v=l.split()
            if v[0][0]!='#':
                data.append([safeFloat(x.replace('(','').replace(')','')) for x in v])
        names=["time"]
        if self.isVector:
            for p in self.positions:
                names+=[p+" x",p+" y",p+" z"]
        else:
            names+=self.positions

        return SpreadsheetData(data=data,
                               names=names,
                               title="%s_t=%s" % (self.val,self.time) if addTitle else None)

# Should work with Python3 and Python2
