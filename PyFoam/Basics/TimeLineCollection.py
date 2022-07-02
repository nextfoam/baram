#  ICE Revision: $Id$
"""Collection of array of timelines"""

from PyFoam.Error import error
from math import ceil
from copy import deepcopy
from threading import Lock
import sys

from PyFoam.ThirdParty.six import print_,iteritems

transmissionLock=Lock()

def mean(a,b):
    """Mean value of a and b"""
    return 0.5*(a+b)

def signedMax(a,b):
    """Absolute Maximum of a and b with the sign preserved"""
    if a<0. or b<0.:
        return min(a,b)
    else:
        return max(a,b)

class TimeLinesRegistry(object):
    """Collects references to TimeLineCollection objects"""

    nr=1

    def __init__(self):
        self.lines={}

    def clear(self):
        self.lines={}
        TimeLinesRegistry.nr=1

    def add(self,line,nr=None):
        if nr:
            if nr in self.lines:
                 error("Number",nr,"already existing")
            TimeLinesRegistry.nr=max(nr+1,TimeLinesRegistry.nr)
        else:
            nr=TimeLinesRegistry.nr
            TimeLinesRegistry.nr+=1
        self.lines[nr]=line

        return nr

    def get(self,nr):
        try:
            return self.lines[nr]
        except KeyError:
            error(nr,"not a known data set:",list(self.lines.keys()))

    def prepareForTransfer(self):
        """Makes sure that the data about the timelines is to be transfered via XMLRPC"""

#        print("Get transmission")
        transmissionLock.acquire()
#        print("Got transmission")

        lst={}
        for i,p in iteritems(self.lines):
            collectors=[]
            for s in p.collectors:
                collectors.append(s.lineNr)

            lst[str(i)]={ "nr"    : i,
                     "times" : deepcopy(p.times),
                     "values": deepcopy(p.values),
                     "lastValid" : deepcopy(p.lastValid),
                     "collectors": collectors }

        transmissionLock.release()

        return lst

    def resolveSlaves(self):
        self.resolveCollectors()

    def resolveCollectors(self):
        """Looks through all the registered lines and replaces integers with
        the actual registered line"""
        for i,p in iteritems(self.lines):
            if len(p.collectors)>0:
                collectors=[]
                for s in p.collectors:
                    if type(s)==int:
                        try:
                            collectors.append(self.lines[s])
                        except KeyError:
                            error(s,"not a known data set:",list(self.lines.keys()))
                    else:
                        collectors.append(s)
                p.collectors=collectors

_allLines=TimeLinesRegistry()

def allLines():
    return _allLines

class TimeLineCollection(object):

    possibleAccumulations=["first", "last", "min", "max", "average", "sum","count"]

    def __init__(self,
                 deflt=float("NaN"),
                 extendCopy=False,
                 splitThres=None,
                 split_fraction_unchanged=0.2,
                 splitFun=None,
                 noEmptyTime=True,
                 advancedSplit=False,
                 preloadData=None,
                 accumulation="first",
                 registry=None):
        """:param deflt: default value for timelines if none has been defined before
        :param extendCopy: Extends the timeline by cpying the last element
        :param splitThres: Threshold after which the number of points is halved
        :param splitFun: Function that is used for halving. If none is specified the mean function is used
        :param noEmptyTime: if there is no valid entry no data is stored for this time
        :param advancedSplit: Use another split algorithm than one that condenses two values into one
        :param preloadData: a dictionary with a dictionary to initialize the values
        :param accumulation: if more than one value is given at any time-step, how to accumulate them (possible values: "first", "last", "min", "max", "average", "sum","count")
        """

        self.cTime=None
        self.addTimeOnDemand=False
        self.times=[]
        self.values={}
        self.lastValid={}
        self.setDefault(deflt)
        self.setExtend(extendCopy)
        self.thres=None
        self.fun=None
        self.is_parametric = False

        if not (accumulation in TimeLineCollection.possibleAccumulations):
            error("Value",accumulation,"not in list of possible values:",TimeLineCollection.possibleAccumulations)
        self.accumulation=accumulation
        self.accumulations={}
        self.occured={}

        self.collectors=[]

        self.setSplitting(splitThres=splitThres,
                          split_fraction_unchanged=split_fraction_unchanged,
                          splitFun=splitFun,
                          advancedSplit=advancedSplit,
                          noEmptyTime=noEmptyTime)

        self.lineNr=None
        if preloadData:
            self.times=preloadData["times"]
            self.values=preloadData["values"]
            self.collectors=preloadData["collectors"]
            self.lineNr=int(preloadData["nr"])
            if "lastValid" in preloadData:
                self.lastValid=preloadData["lastValid"]
            else:
                self.resetValid(val=True)

        if registry==None:
            registry=allLines()
        self.lineNr=registry.add(self,self.lineNr)

    def resetValid(self,val=False):
        """Helper function that resets the information whether the last entry is valid"""
        self.lastValid={}
        for n in self.values:
            self.lastValid[n]=val
        for s in self.collectors:
            s.resetValid(val=val)

    def nrValid(self):
        """Helper function that gets the number of valid values"""
        nr=list(self.lastValid.values()).count(True)
        for s in self.collectors:
            nr+=s.nrValid()
        return nr

    def addSlave(self,slave):
        self.addCollector(slave)

    def addCollector(self,collector):
        """Adds a collector time-line-collection"""
        self.collectors.append(collector)
        collector.setSplitting(splitThres=self.thres,
                               split_fraction_unchanged=self.split_fraction_unchanged,
                               splitFun=self.fun,
                               advancedSplit=self.advancedSplit,
                               noEmptyTime=self.noEmptyTime)

    def setAccumulator(self,name,accu):
        """Sets a special accumulator fopr a timeline
        :param name: Name of the timeline
        :param accu: Name of the accumulator"""
        if not (accu in TimeLineCollection.possibleAccumulations):
            error("Value",accu,"not in list of possible values:",TimeLineCollection.possibleAccumulations,"When setting for",name)
        self.accumulations[name]=accu

    def setSplitting(self,
                     splitThres=None,
                     split_fraction_unchanged=0.2,
                     splitFun=None,
                     advancedSplit=False,
                     noEmptyTime=True):
        """Sets the parameters for splitting"""

        self.advancedSplit = advancedSplit
        if self.advancedSplit:
            self.splitLevels = []
        if splitThres:
            self.thres=splitThres
            if (self.thres % 2)==1:
                self.thres+=1

        if splitFun:
            self.fun=splitFun
        elif not self.fun:
            self.fun=mean

        for s in self.collectors:
            s.setSplitting(splitThres=splitThres,
                           split_fraction_unchanged=split_fraction_unchanged,
                           splitFun=splitFun,
                           advancedSplit=advancedSplit,
                           noEmptyTime=noEmptyTime)

        self.noEmptyTime=noEmptyTime

        self.split_fraction_unchanged = split_fraction_unchanged

    def setDefault(self,deflt):
        """:param deflt: default value to be used"""
        self.defaultValue=float(deflt)

    def setExtend(self,mode):
        """:param mode: whether or not to extend the timeline by copying or setting the default value"""
        self.extendCopy=mode

    def nr(self):
        """Number of elements in timelines"""
        return len(self.times)

    def setTime(self,time,noLock=False,forceAppend=False):
        """Sets the time. If time is new all the timelines are extended
        :param time: the new current time
        :param noLock: do not acquire the lock that ensures consistent data transmission"""

        if not noLock:
            transmissionLock.acquire()

        dTime=float(time)

        append=False
        self.addTimeOnDemand=False

        if dTime!=self.cTime:
            self.cTime=dTime
            append=True
            if self.noEmptyTime and not forceAppend:
                if self.nrValid()==0:
                    # no valid data yet. Extend the timeline when the first data set is added
                    append=False
                    self.addTimeOnDemand=True
            if append:
                self.times.append(self.cTime)
                for v in list(self.values.values()):
                    if len(v)>0 and self.extendCopy:
                        val=v[-1]
                    else:
                        val=self.defaultValue
                    v.append(val)
            else:
                if len(self.times)>0:
                    self.times[-1]=self.cTime

            self.resetValid()

            if self.thres and append and not self.is_parametric:
              try:
                if len(self.times)>=self.thres:
                    if self.advancedSplit:
                        # self._advanced_split()
                        self._time_resolution_split()
                    else:
                        self.times = self.split(self.times, min)
                        for k in list(self.values.keys()):
                            self.values[k] = self.split(self.values[k], self.fun)
              except Exception:
                   e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                   err, detail, tb = sys.exc_info()
                   print_(e)
                   error("Problem splitting",e)

            self.occured={}

        if not self.is_parametric:
            for s in self.collectors:
                s.setTime(time,noLock=True,forceAppend=append)

        if not noLock:
            transmissionLock.release()

    def _time_resolution_split(self):
        # This algorithm tries to have an evenly spacing of the values
        # and preserve maxima and minima and their order

        def concatenate(lists):
            result = lists[0]
            for l in lists[1:]:
                result.extend(l)
            return result

        def time_ranges(orig, delta):
            lngth = len(orig)
            ranges = []
            t, ind = orig[0], 0
            tend = orig[-1]
            last = orig[0]
            while ind < lngth:
                limit = orig[ind] + delta
                start = ind
                while ind < lngth and orig[ind] < limit:
                    ind += 1
                if ind == lngth:
                    limit = orig[-1]
                ranges.append((start, ind, last, limit))
                last = limit
            return ranges

        def base_times(orig, ranges):
            bases = []
            for start, stop, base, end in ranges:
                nr = stop-start
                assert nr > 0
                if nr == 1:
                    bases.append(([orig[start]], (start, stop)))
                elif nr==2:
                    bases.append(([orig[start], orig[start+1]], (start, stop)))
                else:
                    delta = end - base
                    bases.append(([base + 0.25*delta, base + 0.75*delta], (start, stop)))
            return bases

        def reduce_value(vals, bases):
            result = []
            for _, ind in bases:
                start, stop = ind
                if (stop-start) <= 2:
                    result.append(list(vals[start:stop]))
                else:
                    v_min, i_min = vals[start], 0
                    v_max, i_max = vals[start], 0
                    for i,v in enumerate(vals[(start+1):stop]):
                        if v < v_min:
                            v_min = v
                            i_min = i + 1
                        if v > v_max:
                            v_max = v
                            i_max = i + 1
                    if i_max < i_min:
                        result.append([v_max, v_min])
                    else:
                        result.append([v_min, v_max])
            return concatenate(result)

        nr_points = min(max(int(self.thres/2), 20), len(self.times))
        nr_back = max(int(nr_points*self.split_fraction_unchanged), 5)
        nr_rest = nr_points - nr_back

        times_back = self.times[-nr_back:]
        times = self.times[:-nr_back]
        vals_back = {k: self.values[k][-nr_back:] for k in self.values}
        vals = {k: self.values[k][:-nr_back] for k in self.values}
        delta = (times[-1]-times[0])/nr_rest
        bases = base_times(times, time_ranges(times, delta))

        self.times = concatenate([b[0] for b in bases]) + times_back
        for k in self.values:
            self.values[k] = reduce_value(vals[k], bases) + vals_back[k]

    def _advanced_split(self):
        # Clumsy algorithm where the maximum and the minimum of a
        # data-window are preserved in that order
        if len(self.splitLevels)<len(self.times):
            self.splitLevels+=[0]*(len(self.times)-len(self.splitLevels))
        splitTill=int(len(self.times)*0.75)
        if self.splitLevels[splitTill]!=0:
            # Shouldn't happen. But just in case
            splitTill=self.splitLevels.index(0)
        splitFrom=0
        maxLevel=self.splitLevels[0]
        for l in range(maxLevel):
             try:
                 li=self.splitLevels.index(l)
                 if li>=0 and li<splitTill/2:
                     splitFrom=li
                     break
             except ValueError:
                 pass
        window=4
        if ((splitTill-splitFrom)/window)!=0:
            splitTill=splitFrom+window*int(ceil((splitTill-splitFrom)/float(window)))

        # prepare data that will not be split
        times=self.times[:splitFrom]
        levels=self.splitLevels[:splitFrom]
        values={}
        for k in self.values:
            values[k]=self.values[k][:splitFrom]

        for start in range(splitFrom,splitTill,window):
            end=start+window-1
            sTime=self.times[start]
            eTime=self.times[end]
            times+=[sTime,(eTime-sTime)*(2./3)+sTime]
            levels+=[self.splitLevels[start]+1,self.splitLevels[end]+1]
            for k in self.values:
                minV=self.values[k][start]
                minI=0
                maxV=self.values[k][start]
                maxI=0
                for j in range(1,window):
                    val=self.values[k][start+j]
                    if val>maxV:
                        maxV=val
                        maxI=j
                    if val<minV:
                        minV=val
                        minI=j
                if minI<maxI:
                    values[k]+=[minV,maxV]
                else:
                    values[k]+=[maxV,minV]
        firstUnsplit=int(splitTill/window)*window
        self.times=times+self.times[firstUnsplit:]
        self.splitLevels=levels+self.splitLevels[firstUnsplit:]

        for k in self.values:
            self.values[k]=values[k]+self.values[k][firstUnsplit:]
            assert len(self.times)==len(self.values[k])

    def split(self,array,func):
        """Makes the array smaller by joining every two points
        :param array: the field to split
        :param func: The function to use for joining two points"""

        newLen=len(array)/2
        newArray=[0.]*newLen

        for i in range(newLen):
            newArray[i]=func(array[2*i],array[2*i+1])

        return newArray

    def getTimes(self,name=None):
        """:return: A list of the time values"""
        tm=None
        if name in self.values or name is None:
            tm=self.times
        else:
            for s in self.collectors:
                if name in s.values:
                    tm=s.times
                    break
        return tm

    def getValueNames(self):
        """:return: A list with the names of the safed values"""
        names=list(self.values.keys())
        for i,s in enumerate(self.collectors):
            for n in s.getValueNames():
                names.append("%s-collector%02d" % (n,i))
        return names

    def getValues(self,name):
        """Gets a timeline
        :param name: Name of the timeline
        :return: List with the values"""

        if name not in self.values:
            if len(self.collectors)>0:
                if name.rfind("-collector")>0:
                    nr=int(name[-2:])
                    nm=name[:name.rfind("-collector")]
                    return self.collectors[nr].getValues(nm)
            self.values[name]=self.nr()*[self.defaultValue]
        return self.values[name]

    def setValue(self,name,value):
        """Sets the value of the last element in a timeline
        :param name: name of the timeline
        :param value: the last element"""

        val=float(value)

        transmissionLock.acquire()
        if self.addTimeOnDemand:
            self.times.append(self.cTime)
            for v in list(self.values.values()):
                if len(v)>0 and self.extendCopy:
                    val=v[-1]
                else:
                    val=self.defaultValue
                v.append(val)
            self.addTimeOnDemand=False

        data=self.getValues(name)
        if len(data)>0:
            accu=self.accumulation
            if name not in self.occured:
                if accu=="count":
                    newValue=1 # =1L
                else:
                    newValue=val
                self.occured[name]=1
            else:
                oldValue=data[-1]
                n=self.occured[name]
                self.occured[name]+=1
                if name in self.accumulations:
                    accu=self.accumulations[name]
                if accu=="first":
                    newValue=oldValue
                elif accu=="last":
                    newValue=val
                elif accu=="max":
                    newValue=max(val,oldValue)
                elif accu=="min":
                    newValue=min(val,oldValue)
                elif accu=="sum":
                    newValue=val+oldValue
                elif accu=="average":
                    newValue=(n*oldValue+val)/(n+1)
                elif accu=="count":
                    newValue=n+1
                else:
                    error("Unimplemented accumulator",accu,"for",name)

            data[-1]=newValue

        self.lastValid[name]=True

        transmissionLock.release()

    def getData(self):
        """Return the whole current data as a SpreadsheetData-object"""

        from .SpreadsheetData import SpreadsheetData

        try:
            import numpy
        except ImportError:
            # assume this is pypy and retry
            import numpypy
            import numpy

        names=["time"]+list(self.values.keys())
        data=[]
        data.append(self.times)
        for k in list(self.values.keys()):
            data.append(self.values[k])

        return SpreadsheetData(names=names,data=numpy.asarray(data).transpose())

    def getLatestData(self,structured=False):
        """Return a dictionary with the latest values from all data sets"""

        result={}

        for n,d in iteritems(self.values):
            if len(d)>0:
                if self.lastValid[n] or len(d)<2:
                    result[n]=d[-1]
                else:
                    result[n]=d[-2]

        return result

# Should work with Python3 and Python2
