# coding: utf-8

#  ICE Revision: $Id: $
"""
Data that can go into a spreadsheet (title line and rectangular data)
"""

try:
    import numpy
except ImportError:
    # assume this is pypy and retry
    import numpypy
    import numpy

import copy
import re

from PyFoam.Error import error,FatalErrorPyFoamException,warning

from PyFoam.ThirdParty.six import PY3
from PyFoam.ThirdParty.six import b as toByte

class WrongDataSize(FatalErrorPyFoamException):
    def __init__(self,txt="Size of the arrays differs"):
        FatalErrorPyFoamException.__init__(self,txt)

class SpreadsheetData(object):
    """
    Collects data that could go into a spreadsheet. The focus of this class is on
    storing all the data at once
    """
    def __init__(self,
                 timeName=None,
                 validData=None,
                 validMatchRegexp=False,
                 csvName=None,
                 txtName=None,
                 excelName=None,
                 data=None,
                 names=None,
                 isSampleFile=False,
                 skip_header=0,
                 stripCharacters=None,
                 replaceFirstLine=None,
                 title=None):
        """Either this is constructed from a file or from the data and the column headers

        :param timeName: the data colum that is to be considered the time in this file
        :param validData: names of the valid data columns (all others should be discarded)
        :param validMatchRegexp: Should the validData be interpreted as regular expressions
        :param csvName: name of the CSV-file the data should be constructed from,
        :param txtName: name of a file the data should be constructed from,
        :param excelName: name of a Excel-file the data should be constructed from (uses the first sheet in the file),
        :param data: the actual data to use
        :param names: the names for the column header
        :param isSampleFile: file produced by sample/set. Field names are determined from the filename
        :param stripCharacters: String with characters that should be removed before reading
        :param replaceFirstLine: String with a line that should replace the first line (usually to replace the header)
        :param title: a name that is used to make unique heades names"""

        def filterChars(fName):
            if "readlines" in dir(fName):
                f=fName
            else:
                f=open(fName)
            first=True
            for l in f.readlines():
                if first and replaceFirstLine:
                    l=replaceFirstLine+"\n"
                elif stripCharacters:
                    l=l.translate(None,stripCharacters)
                first=False
                try:
                    yield toByte(l)
                except AttributeError:
                    yield l
            if "close" in dir(f):
                f.close()
        self.title=title

        nrFileSpec=len([1 for i in [csvName,txtName,excelName] if not i is None])

        if (nrFileSpec>0) and not data is None:
            error("SpreadsheetData is either constructed from data or from a file")

        if data is None and nrFileSpec>1:
            error("Only one file specification allowed")

        if csvName:
            try:
                rec=numpy.recfromcsv(filterChars(csvName),
                                     names=True if names is None else names,
                                     skip_header=skip_header)
                data=[tuple(float(x) for x in i) for i in rec]
                names=list(rec.dtype.names)
            except AttributeError:
                # for old numpy-versions
                data=[tuple(d) for d in numpy.loadtxt(csvName,
                                                      delimiter=',',
                                                      skiprows=1)]
                names=open(csvName).readline().strip().split(',')

            # redo this to make sure that everything is float
            self.data=numpy.array(data,dtype=list(zip(names,['f8']*len(names))))
        elif txtName:
            try:
                if isSampleFile:
                    from os import path

                    raw=numpy.recfromtxt(filterChars(txtName))
                    rawName=path.splitext(path.basename(txtName))[0].split("_")[1:]
                    pData=[list(raw[:,0])]
                    names=["coord"]
                    if raw.shape[1]==len(rawName)+1:
                        # scalars
                        for i,n in enumerate(rawName):
                            pData.append(list(raw[:,1+i]))
                            names.append(n)
                    elif raw.shape[1]==3*len(rawName)+1:
                        for i,n in enumerate(rawName):
                            for j,c in enumerate(["x","y","z"]):
                                pData.append(list(raw[:,1+i*3+j]))
                                names.append(n+"_"+c)
                            vals=[raw[:,1+i*3+j] for j in range(3)]
                            pData.append(list(numpy.sqrt(vals[0]*vals[0]+
                                                         vals[1]*vals[1]+
                                                         vals[2]*vals[2])))
                            names.append(n+"_mag")
                    else:
                        error("List of names",rawName,"does not fit number of colums",
                              raw.shape[1],"should be",len(rawName)+1,
                              "for scalars or",len(rawName)*3+1,"for vector")
                    data=[tuple(v) for v in numpy.asarray(pData).T]
                else:
                    rec=numpy.recfromtxt(filterChars(txtName),names=True)
                    data=[tuple(float(x) for x in i) for i in rec]
                    if names is None:
                        names=list(rec.dtype.names)
                    else:
                        nr=len(list(rec.dtype.names))
                        if title is None:
                            off=len(names)-nr+1
                            self.title="_".join(names[:off])
                            names=names[:off]+["index"]+names[off:]
                        names=names[-nr:]
            except AttributeError:
                # for old numpy-versions
                data=[tuple(v) for v in numpy.loadtxt(txtName)]
                names=open(txtName).readline().strip().split()[1:]

            # redo this to make sure that everything is float
            self.data=numpy.array(data,dtype=list(zip(names,['f8']*len(names))))
        elif excelName:
            import pandas
            rec=pandas.read_excel(excelName).to_records()
            data=[tuple(float(x) for x in i) for i in rec]
            names=list(rec.dtype.names)

            self.data=numpy.array(data,dtype=list(zip(names,['f8']*len(names))))
        else:
            if data is not None and names is None:
                error("No names given for the data")

            types=[]
            for d in data[0]:
                try:
                    float(d)
                    types.append('f8')
                except ValueError:
                    types.append('S')

            for i,t in enumerate(types):
                if t=="S":
                    l=max(len(str(d[i])) for d in data)+1
                    types[i]="S%d" % l
            self.data=numpy.array([tuple(v) for v in data],
                                  dtype=list(zip(names,types)))
        if timeName:
            try:
                index=list(self.data.dtype.names).index(timeName)
            except ValueError:
                error("Time name",timeName,"not in",self.data.dtype.names)
        else:
            index=0
        self.time=self.data.dtype.names[index]

        self.eliminatedNames=None

        if validData:
            usedData=[]
            usedNames=[]

            for n in self.data.dtype.names:
                if n==self.time or self.validName(n,validData,validMatchRegexp):
                    usedData.append(tuple(self.data[n]))
                    usedNames.append(n)

            self.eliminatedNames=set(self.data.dtype.names)-set(usedNames)

            usedData=numpy.array(usedData).transpose()
            self.data=numpy.array([tuple(v) for v in usedData],
                                  dtype=list(zip(usedNames,['f8']*len(usedNames))))
            index=list(self.data.dtype.names).index(self.time)

        if self.title!=None:
            self.data.dtype.names=[self.title+" "+x for x in self.data.dtype.names[0:index]]+[self.data.dtype.names[index]]+[self.title+" "+x for x in self.data.dtype.names[index+1:]]

    def validName(self,n,validData,validMatchRegexp=False):
        if n in validData:
            return True
        elif validMatchRegexp:
            for r in validData:
                exp=None
                try:
                    exp=re.compile(r)
                except:
                    pass
                if not exp is None:
                    if exp.search(n):
                        return True
        return False

    def names(self,withTime=True):
        if withTime:
            return copy.copy(self.data.dtype.names)
        else:
            ind=self.data.dtype.names.index(self.timeName())
            return self.data.dtype.names[:ind]+self.data.dtype.names[ind+1:]

    def timeName(self):
        return self.time

    def rename(self,f,renameTime=False):
        """Rename all the columns according to a function. Time only if specified"""
        newNames=[]
        for c in self.data.dtype.names:
            if not renameTime and c==self.time:
                newNames.append(c)
            else:
                newNames.append(f(c))
                if c==self.time:
                    self.time=newNames[-1]
        self.data.dtype.names=newNames

    def size(self):
        return self.data.size

    def writeCSV(self,fName,
                 delimiter=","):
        """Write data to a CSV-file
        :param fName: Name of the file
        :param delimiter: Delimiter to be used in the CSV-file"""

        f=open(fName,"wb")
        if PY3:
            f.write(toByte(delimiter.join(self.names())+"\n"))
        else:
            f.write(delimiter.join(self.names())+"\n")

        numpy.savetxt(f,self.data,delimiter=delimiter)
        f.close()

    def tRange(self,time=None):
        """Return the range of times
        :param time: name of the time. If None the first column is used"""
        if time==None:
            time=self.time
        t=self.data[time]

        return (t[0],t[-1])

    def join(self,other,time=None,prefix=None):
        """Join this object with another. Assume that they have the same
        amount of rows and that they have one column that designates the
        time and is called the same and has the same values
        :param other: the other array
        :param time: name of the time. If None the first column is used
        :param prefix: String that is added to the other names. If none is given then
        the title is used"""
        if time==None:
            time=self.time
        if prefix==None:
            prefix=other.title
            if prefix==None:
                prefix="other_"
            else:
                prefix+="_"

        t1=self.data[time]
        t2=other.data[time]
        if len(t1)!=len(t2):
            raise WrongDataSize()
        if max(abs(t1-t2))>1e-10:
            raise WrongDataSize("Times do not have the same values")

        names=[]
        data=[]
        for n in self.names():
            names.append(n)
            data.append(self.data[n])

        for n in other.names():
            if n!=time:
                if n in self.names():
                    names.append(prefix+n)
                else:
                    names.append(n)
                data.append(other.data[n])

        return SpreadsheetData(names=names,
                               data=numpy.array(data).transpose())

    def __add__(self,other):
        """Convinience function for joining data"""
        return self.join(other)

    def recalcData(self,name,expr,create=False):
        """Recalc or add a column to the data
        :param name: the colum (must exist if it is not created. Otherwise it must not exist)
        :param expr: the expression to calculate. All present column names are usable as variables.
        There is also a variable data for subscripting if the data is not a valid variable name. If
        the column is not create then there is also a variable this that is an alias for the name
        :param create: whether a new data item should be created"""
        if create and name in self.names():
            error("Item",name,"already exists in names",self.names())
        elif not create and not name in self.names():
            error("Item",name,"not in names",self.names())

        result=eval(expr,dict([(n,self.data[n]) for n in self.names()]+[("data",self.data)]+
                              ([("this",self.data[name] if not create else [])])))

        if not create:
            self.data[name]=result
        else:
            self.append(name,result)

    def append(self,
               name,
               data,
               allowDuplicates=False):
        """Add another column to the data. Assumes that the number of rows is right
        :param name: the name of the column
        :param data: the actual data
        :param allowDuplicates: If the name already exists make it unique by appending _1, _2 ..."""

        arr = numpy.asarray(data)
        newname=name
        if newname in self.names() and allowDuplicates:
            cnt=1
            while newname in self.names():
                newname="%s_%d" % (name,cnt)
                cnt+=1
            warning("Changing name",name,"to",newname,"bacause it already exists in the data")
        newdtype = numpy.dtype(self.data.dtype.descr + [(newname, 'f8')])
        newrec = numpy.empty(self.data.shape, dtype=newdtype)
        for field in self.data.dtype.fields:
            newrec[field] = self.data[field]
            newrec[name] = arr

        self.data=newrec

    def __call__(self,
                 t,
                 name=None,
                 time=None,
                 invalidExtend=False,
                 noInterpolation=False):
        """'Evaluate' the data at a specific time by linear interpolation
        :param t: the time at which the data should be evaluated
        :param name: name of the data column to be evaluated. Assumes that that column
        is ordered in ascending order. If unspecified a dictionary with the values from all columns is returned
        :param time: name of the time column. If none is given then the first column is assumed
        :param invalidExtend: if t is out of the valid range then use the smallest or the biggest value. If False use nan
        :param noInterpolation: if t doesn't exactly fit a data-point return 'nan'"""

        if time==None:
            time=self.time

        if name is None:
            result={}
            for n in self.names():
                if n!=time:
                    result[n]=self(t,
                                   name=n,
                                   time=time,
                                   invalidExtend=invalidExtend,
                                   noInterpolation=noInterpolation)
            return result

        x=self.data[time]
        y=self.data[name]

        isString=y.dtype!=numpy.float64

        # get extremes
        if t<x[0]:
            if invalidExtend:
                return y[0]
            else:
                return float('nan') if not isString else ""
        elif t>x[-1]:
            if invalidExtend:
                return y[-1]
            else:
                return float('nan') if not isString else ""

        if noInterpolation:
            if t==x[0]:
                return y[0]
            elif t==x[-1]:
                return y[-1]

        iLow=0
        iHigh=len(x)-1

        while (iHigh-iLow)>1:
            iNew = iLow + int((iHigh-iLow)/2)

            if x[iNew]==t:
                # we got lucky
                return y[iNew]
            elif t < x[iNew]:
                iHigh=iNew
            else:
                iLow=iNew
        if noInterpolation:
            return float('nan') if not isString else ""
        else:
            if isString:
                return y[iLow] if (t-x[iLow])/(x[iHigh]-x[iLow])<0.5 else y[iHigh]
            else:
                return y[iLow] + (y[iHigh]-y[iLow])*(t-x[iLow])/(x[iHigh]-x[iLow])

    def addTimes(self,times,time=None,interpolate=False,invalidExtend=False):
        """Extend the data so that all new times are represented (add rows
        if they are not there)
        :param time: the name of the column with the time
        :param times: the times that shoild be there
        :param interpolate: interpolate the data in new rows. Otherwise
        insert 'nan'
        :param invalidExtend: if t is out of the valid range then use
        the smallest or the biggest value. If False use nan"""

        if time==None:
            time=self.time

        if len(times)==len(self.data[time]):
            same=True
            for i in range(len(times)):
                if times[i]!=self.data[time][i]:
                    same=False
                    break
            if same:
                # No difference between the times
                return

        newData=[]
        otherI=0
        originalI=0
        while otherI<len(times):
            goOn=originalI<len(self.data[time])
            while goOn and times[otherI]>self.data[time][originalI]:
                newData.append(self.data[originalI])
                originalI+=1
                goOn=originalI<len(self.data[time])

            append=True
            if originalI<len(self.data[time]):
                if times[otherI]==self.data[time][originalI]:
                    newData.append(self.data[originalI])
                    originalI+=1
                    otherI+=1
                    append=False

            if append:
                t=times[otherI]
                newRow=[]
                for n in self.names():
                    if n==time:
                        newRow.append(t)
                    elif interpolate:
                        newRow.append(self(t,n,time=time,invalidExtend=invalidExtend))
                    else:
                        newRow.append(float('nan'))
                newData.append(newRow)
                otherI+=1

        while originalI<len(self.data[time]):
            newData.append(self.data[originalI])
            originalI+=1

        self.data=numpy.array([tuple(v) for v in newData],dtype=self.data.dtype)

    def resample(self,
                 other,
                 name,
                 otherName=None,
                 time=None,
                 invalidExtend=False,
                 extendData=False,
                 noInterpolation=False):
        """Calculate values from another dataset at the same times as in this data-set
        :param other: the other data-set
        :param name: name of the data column to be evaluated. Assumes that that column
        is ordered in ascending order
        :param time: name of the time column. If none is given then the first column is assumed
        :param invalidExtend: see __call__
        :param extendData: if the time range of x is bigger than the range then extend the range before resampling
        :param noInterpolation: if t doesn't exactly fit a data-point return 'nan'"""
        if time==None:
            time=self.time

        if extendData and (
            self.data[time][0] > other.data[time][0] or \
            self.data[time][-1] < other.data[time][-1]):
            pre=[]
            i=0
            while other.data[time][i] < self.data[time][0]:
                data=[]
                for n in self.names():
                    if n==time:
                        data.append(other.data[time][i])
                    else:
                        data.append(float('nan'))
                pre.append(data)
                i+=1
                if i>=len(other.data[time]):
                    break
            if len(pre)>0:
                self.data=numpy.concatenate((numpy.array([tuple(v) for v in pre],
                                                         dtype=self.data.dtype),
                                             self.data))

            post=[]
            i=-1
            while other.data[time][i] > self.data[time][-1]:
                data=[]
                for n in self.names():
                    if n==time:
                        data.append(other.data[time][i])
                    else:
                        data.append(float('nan'))
                post.append(data)
                i-=1
                if abs(i)>=len(other.data[time])+1:
                    break

            post.reverse()
            if len(post)>0:
                self.data=numpy.concatenate((self.data,numpy.array([tuple(p) for p in post],
                                                                   dtype=self.data.dtype)))

        result=[]

        for t in self.data[time]:
            nm=name
            if otherName:
                nm=otherName
            result.append(other(t,nm,
                                time=time,
                                invalidExtend=invalidExtend,
                                noInterpolation=noInterpolation))

        return result

    def compare(self,
                other,
                name,
                otherName=None,
                time=None,
                common=False,
                minTime=None,
                maxTime=None):
        """Compare this data-set with another. The time-points of this dataset are used as
        a reference. Returns a dictionary with a number of norms: maximum absolute
        difference, average absolute difference
        on all timepoints, average absolute difference weighted by time
        :param other: the other data-set
        :param name: name of the data column to be evaluated. Assumes that that column
        is ordered in ascending order
        :param time: name of the time column. If none is given then the first column is assumed
        :param common: cut off the parts where not both data sets are defined
        :param minTime: first time which should be compared
        :param maxTime: last time to compare"""

        if time==None:
            time=self.time

        x=self.data[time]
        y=self.data[name]
        y2=self.resample(other,name,otherName=otherName,time=time,invalidExtend=True)

        minT,maxT=minTime,maxTime
        if common:
            minTmp,maxTmp=max(x[0],other.data[time][0]),min(x[-1],other.data[time][-1])
            for i in range(len(x)):
                if minTmp<=x[i]:
                    minT=x[i]
                    break
            for i in range(len(x)):
                val=x[-(i+1)]
                if maxTmp>=val:
                    maxT=val
                    break
        else:
            minT,maxT=x[0],x[-1]

        result = { "max" : None,
                   "maxPos" : None,
                   "average" : None,
                   "wAverage" : None,
                   "tMin": None,
                   "tMax": None }

        if minT==None or maxT==None:
            return result

        if minTime:
            if minTime>minT:
                minT=minTime

        if maxTime:
            if maxTime<maxT:
                maxT=maxTime

        if maxT<minT:
            return result

        maxDiff=0
        maxPos=x[0]
        sumDiff=0
        sumWeighted=0
        cnt=0

        for i,t in enumerate(x):
            if t<minT or t>maxT:
                continue
            cnt+=1

            val1=y[i]
            val2=y2[i]
            diff=abs(val1-val2)
            if diff>maxDiff:
                maxDiff=diff
                maxPos=x[i]
            sumDiff+=diff
            weight=0
            if t>minT:
                weight+=(t-x[i-1])/2
            if t<maxT:
                weight+=(x[i+1]-t)/2
            sumWeighted+=weight*diff

        return { "max" : maxDiff,
                 "maxPos" : maxPos,
                 "average" : sumDiff/cnt,
                 "wAverage" : sumWeighted/(maxT-minT),
                 "tMin": minT,
                 "tMax": maxT}

    def metrics(self,
                name,
                time=None,
                minTime=None,
                maxTime=None):
        """Calculates the metrics for a data set. Returns a dictionary
        with a number of norms: minimum, maximum, average, average weighted by time
        :param name: name of the data column to be evaluated. Assumes that that column
        is ordered in ascending order
        :param time: name of the time column. If none is given then the first column is assumed
        :param minTime: first time to take metrics from
        :param maxTime: latest time to take matrics from"""

        if time==None:
            time=self.time

        x=self.data[time]
        y=self.data[name]

        minVal=1e40
        maxVal=-1e40
        sum=0
        sumWeighted=0

        minT,maxT=x[0],x[-1]

        if minTime:
            if minTime>minT:
                minT=minTime

        if maxTime:
            if maxTime<maxT:
                maxT=maxTime

        cnt=0

        for i,t in enumerate(x):
            if t<minT or t>maxT:
                continue
            cnt+=1
            val=y[i]
            maxVal=max(val,maxVal)
            minVal=min(val,minVal)
            sum+=val
            weight=0
            if i>0:
                weight+=(t-x[i-1])/2
            if i<(len(x)-1):
                weight+=(x[i+1]-t)/2
            sumWeighted+=weight*val

        return { "max" : maxVal,
                 "min" : minVal,
                 "average" : sum/max(cnt,1),
                 "wAverage" : sumWeighted/(maxT-minT),
                 "tMin": x[0],
                 "tMax": x[-1]}

    def getData(self,reindex=True):
        """Return a dictionary of the data in the DataFrame format of pandas
        :param: drop duplicate times (setting it to False might break certain Pandas-operations)"""
        try:
            from PyFoam.Wrappers.Pandas import PyFoamDataFrame
        except ImportError:
            warning("No pandas-library installed. Returning None")
            return None

        return PyFoamDataFrame(self.getSeries(reindex=reindex))

    def getSeries(self,reindex=True):
        """Return a dictionary of the data-columns in the Series format of pandas
        :param: drop duplicate times (setting it to False might break certain Pandas-operations)"""
        try:
            import pandas
        except ImportError:
            warning("No pandas-library installed. Returning None")
            return None
        data={}

        if reindex:
            realindex=numpy.unique(self.data[self.time])

        for n in self.names():
            if n!=self.time:
                data[n]=pandas.Series(self.data[n],
                                      index=self.data[self.time],
                                      name=n)
                if reindex:
                    if len(data[n])!=len(realindex):
                        try:
                            data[n].axes[0].is_unique=True
                        except:
                            # Newer Pandas versions don't allow setting this. Just drop duplicates
                            data[n]=data[n].drop_duplicates()
                        data[n]=data[n].reindex_axis(realindex)

        return data

# Should work with Python3 and Python2
