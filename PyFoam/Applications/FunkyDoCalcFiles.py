"""
Application class that implements pyFoamFunkyDoCalcFiles.py
"""

from optparse import OptionGroup
from .PyFoamApplication import PyFoamApplication
from PyFoam.Basics.FoamOptionParser import Subcommand
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator as gen
from PyFoam.Error import error

from os import path
from collections import OrderedDict
from pprint import pprint,pformat

from PyFoam.ThirdParty.six import print_,iteritems

smallEps=1e-15

class FunkyDoCalcData:
    def __init__(self,d):
        self.data=d

    def __repr__(self):
        return pformat(self.data)

    def __binop(self,other,op):
        def doOp(a,b):
            result={}
            for k,va in iteritems(a):
                try:
                    vb=b[k]
                    try:
                        result[k]=op(va,vb)
                    except TypeError:
                        if hasattr(va,"keys"):
                            result[k]=doOp(va,vb)
                        else:
                            result[k]=[r if abs(r)>smallEps else 0.
                                       for r in [op(aa,bb) for aa,bb in zip(va,vb)]]
                except KeyError:
                    pass
            return result

        return FunkyDoCalcData(doOp(self.data,other.data))

    def __getitem__(self,k):
        return self.data[k]

    def __sub__(self,other):
        return self.__binop(other,lambda x,y:x-y)

    def __div__(self,other):
        def secureDiv(a,b):
            if abs(b)<smallEps:
                b=0
            try:
                return float(a)/b
            except ZeroDivisionError:
                return float("NaN")
        return self.__binop(other,secureDiv)

class FunkyDoCalcFile:
    """The actual file"""

    def __init__(self,fName):
        self.__content=ParsedParameterFile(fName,
                                           doMacroExpansion=True,
                                           noHeader=True)
        self.fName=fName
        rawData=[]
        for k,v in iteritems(self.__content["data"]):
            rawData.append((v["time"],v))
        rawData.sort(key=lambda x:float(x[0]))
        self.__data=OrderedDict()
        self.entries=None

        for k,v in rawData:
            self.__data[k]=v
            if self.entries is None:
                self.entries=OrderedDict()
                for k2,v2 in iteritems(v):
                    if k2=="time":
                        continue
                    e=OrderedDict()
                    for k3,v3 in iteritems(v2):
                        try:
                            e[k3]=len(list(v3))
                        except TypeError:
                            e[k3]=1

                    self.entries[k2]=e
            else:
                for k2,v2 in iteritems(v):
                    if k2=="time":
                        continue
                    val=0
                    for k3,v3 in iteritems(v2):
                        try:
                            val=len(list(v3))
                        except TypeError:
                            val=1
                        if val!=self.entries[k2][k3]:
                            error("Inconsistency in data for time",k,
                                  ": expected",self.entries[k2][k3],"values for",
                                  k2,"/",k3,". Got",val)

    def compare(self,other,digits=5,times=None,additionalDigits=0):
        problems=[]
        checks=0
        if "tolerances" not in self.__content:
            tolerances=self.calcTolerances(digits)["tolerances"]
            problems.append("No 'tolerances' specified in file {}".format(self.fName))
            factor=1
        else:
            tolerances=self.__content["tolerances"]
            from math import pow
            factor=pow(10.,-additionalDigits)

        if times is None:
            times=self.times

        usedTimes=set()
        span=self.span
        amax=self.absmax

        for t in times:
            aVal=self[t]
            if t not in self.times:
                problems.append("Specified time {} not in {}. "
                                "Using {} instead (shift {})".format(t,
                                                                     self.fName,
                                                                     aVal["time"],
                                                                     aVal["time"]-t))
                t=aVal["time"]
            if t in usedTimes:
                problems.append("Time {} was aready used (Duplicate). Skipping".format(t))
                continue
            usedTimes.add(t)

            bVal=other[t]
            diffVal=aVal-bVal
            if t not in other.times:
                problems.append("No exact match for time {} in {}. "
                              "Using {} instead (difference {})".format(t,
                                                                        other.fName,
                                                                        bVal["time"],
                                                                        diffVal["time"]))
            for key,tol in iteritems(tolerances):
                for acc,spec in iteritems(tol):
                    try:
                        a=aVal[key][acc]
                    except KeyError:
                        problems.append("Missin/A: Item {}/{} missing for t={}".format(
                            key,acc,t))
                        continue
                    try:
                        b=bVal[key][acc]
                    except KeyError:
                        problems.append("Missin/B: Item {}/{} missing for t={}".format(
                            key,acc,t))
                        continue
                    d=diffVal[key][acc]
                    sp=span[key][acc]
                    am=amax[key][acc]
                    if len(spec)==1:
                        a=[a]
                        b=[b]
                        d=[d]
                        sp=[sp]
                        am=[am]

                    for i in range(len(spec)):
                        s=spec[i]
                        specString="t={} Key: {} Accumulation: {} Component: {}" \
                            .format(t,key,acc,i)
                        eps=smallEps
                        if "smallEps" in s and s["smallEps"] is not None:
                            eps=float(s["smallEps"])
                        allowZero=False
                        if "allowZero" in s and s["allowZero"] is not None:
                            allowZero=bool(s["allowZero"])
                        if "abstol" in s and s["abstol"] is not None:
                            try:
                                checks+=1
                                if abs(d[i])>float(s["abstol"])*factor:
                                    problems.append("Abstol {}"
                                                  " Difference |{}|>{} (Orig: {} Real: {})"
                                                  .format(specString,
                                                          d[i],s["abstol"]*factor,
                                                          a[i],b[i]))
                            except ValueError:
                                problems.append("SpecError: {} - 'abstol' "
                                                "{} is of type {}".format(specString,
                                                                          s["abstol"],
                                                                          type(s["abstol"])))
                        if "reltol" in s and s["reltol"] is not None:
                            for typ in ["value","amax","span"]:
                                typName=typ+"Rel"
                                if typName in s and s[typName]==True:
                                    checks+=1
                                    if typ=="value":
                                        val=0.5*(abs(a[i])+abs(b[i]))
                                    elif typ=="amax":
                                        val=am[i]
                                    elif typ=="span":
                                        val=sp[i]
                                    try:
                                        if abs(val)<eps:
                                            if not allowZero:
                                                problems.append("AlmostZero/{} {}:"
                                                                " Reference value for {} is almost zero (eps={}): {}"
                                                                .format(typ,specString,typ,eps,val))
                                            continue
                                        relError=d[i]/val
                                        if abs(relError)>float(s["reltol"])*factor:
                                            problems.append("Reltol/{} {}"
                                                            " Relative error |{}|>{} (Orig: {} Real: {} Ref: {})"
                                                          .format(typ,specString,
                                                                  relError,s["reltol"]*factor,
                                                                  a[i],b[i],val))
                                    except ZeroDivisionError:
                                        problems.append("Zero/{}: {} - Value is zero. No relative error".format(typ,specString))
                                    except ValueError:
                                        problems.append("SpecError/{}: {} - 'reltol' "
                                                        "{} is of type {}".format(typ,specString,
                                                                                  s["reltol"],
                                                                                  type(s["reltol"])))

        return checks,problems

    def calcTolerances(self,digits):
        from math import log10,floor,pow
        def calcDigits(w):
            try:
                return int(floor(log10(w)))
            except ValueError:
                return -digits
        tol=OrderedDict()
        span=self.span
        amax=self.absmax

        def tolDict(span,amax):
            try:
                relspan=float(span)/amax
            except ZeroDivisionError:
                relspan=None
            if span>amax: # Don't calc relative tolerance if min and max have different signs
                relspan=None

            return { "abstol" : max(pow(10,calcDigits(span)-digits),
                                    pow(10,calcDigits(amax)-digits)),
                     "reltol" : None if relspan is None else min(pow(10,calcDigits(relspan)),
                                                                 pow(10,-digits)),
                     "valueRel" : True,
                     "spanRel" : True,
                     "amaxRel" : True,
                     "span" : span,
                     "amax" : amax ,
                     "smallEps" : 1e-15,
                     "allowZero" : False }

        for k,v in iteritems(self.entries):
            t=OrderedDict()
            for n,nr in iteritems(v):
               s=span[k][n]
               a=amax[k][n]
               if nr==1:
                   s=[s]
                   a=[a]
               t[n]=[tolDict(*par) for par in zip(s,a)]
            tol[k]=t
        return {'tolerances':tol}

    def __accumulate(self,func):
        ranges={}
        init=self[self.times[0]]
        for k1,v1 in iteritems(init.data):
            if k1=="time":
                continue
            ranges[k1]={}
            for k2,v2 in iteritems(v1):
                ranges[k1][k2]=v2
        for t in self.times[1:]:
            val=self[t]
            for k1,v1 in iteritems(val.data):
                if k1=="time":
                    continue
                for k2,v2 in iteritems(v1):
                    old=ranges[k1][k2]
                    if self.entries[k1][k2]==1:
                        ranges[k1][k2]=func(old,v2)
                    else:
                        r=[]
                        for i in range(self.entries[k1][k2]):
                            r.append(func(old[i],v2[i]))
                        ranges[k1][k2]=r

        return FunkyDoCalcData(ranges)

    @property
    def min(self):
        return self.__accumulate(min)

    @property
    def max(self):
        return self.__accumulate(max)

    @property
    def absmax(self):
        return self.__accumulate(lambda x,y:max(abs(x),abs(y)))

    @property
    def span(self):
        return self.max-self.min

    @property
    def spec(self):
        return self.__content["spec"]

    @property
    def expressions(self):
        return self.__content["expressions"]

    @property
    def times(self):
        return self.__data.keys()

    def __getitem__(self,tm):
        nearest=None
        for t in self.times:
            if nearest is None:
                nearest=t
                continue
            if abs(float(nearest)-float(tm))>abs(float(t)-float(tm)):
                nearest=t
        return FunkyDoCalcData(self.__data[nearest])

class FunkyDoCalcFiles(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
This utility helps handling the dictionary files produced by the funkyDoCalc-utility from the swak4Foam-package
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog COMMAND <dict-file>",
                                   changeVersion=False,
                                   examples="""To use this command you must first create a result file with
funkyDoCalc from the swak4Foam-packages. Assume that the result file is called 'checkValues'. The command

  %prog info checkValues

gives an overview of the values in that dict that can be compared (including the time-steps). Calls like

  %prog max checkValues

  %prog span checkValues

print statistics about the data. The data from one timestep can be printed with

  %prog get checkValues 0.5

if there is no time 0.5 the nearest time will be used. Similarily the command

  %prog difftime checkValues 0.1 0.5

compares the data from two timesteps.

Based on the data the command

  %prog defaults checkValues 3

prints an example dictionary with tolerances that can be copy/pasted
into 'checkValues' and edited (change the calues and remove unwanted comparisons).
The tolerances are calculated under the assumption
that you want a precision of 3 digits

The command

  %prog diff checkValues ../otherCase/checkValues

compares the results assuming that they were generated with the same
funkyDoCalc-dictionary. If there is a 'tolerances' dictionary in the
first file then this is used. Otherwise the values that the 'defaults' command
genenerates will be used. If results differ by more than the specifies tolerances
an output is done. Otherwise only the number of comparisons is printed

The entries of a tolerances-specification are

  abstol: the absolute tolerance for this value. If missing no absolute difference is compared

  reltol: the relative tolerance. If missing no relative tolerance is calculated

There are 3 different ways to calculate the relative tolerance depending
on which value the error is calculated relative to: the average of the absolute values,
the maximum of the absolute value over all times or the span over all times. These
can be switched on with the entries valueRel, amaxRel and spanRel respectively""",
                                   subcommands=True,
                                   **kwargs)

    def addOptions(self):
        infoCmd=Subcommand(name='info',
                           help="Information about the dictionary",
                           aliases=('print',),
                           nr=1,
                           exactNr=True)
        self.parser.addSubcommand(infoCmd)

        minCmd=Subcommand(name='min',
                          help="Minimum over all the time-steps",
                          aliases=('minimum',),
                          nr=1,
                          exactNr=True)
        self.parser.addSubcommand(minCmd)

        maxCmd=Subcommand(name='max',
                          help="Maximum over all the time-steps",
                          aliases=('maximum',),
                          nr=1,
                          exactNr=True)
        self.parser.addSubcommand(maxCmd)

        maxCmd=Subcommand(name='absmax',
                          help="Maximum of the absolute values over all the time-steps",
                          nr=1,
                          exactNr=True)
        self.parser.addSubcommand(maxCmd)

        spanCmd=Subcommand(name='span',
                           help="Span of the values",
                           aliases=('width',),
                           nr=1,
                           exactNr=True)
        self.parser.addSubcommand(spanCmd)

        rspanCmd=Subcommand(name='relativespan',
                            help="Relative span of the values (compared to the absolute values)",
                            aliases=('rspan',),
                            nr=1,
                            exactNr=True)
        self.parser.addSubcommand(rspanCmd)

        getCmd=Subcommand(name='get',
                          help="Get data for a specific time",
                          nr=2,
                          exactNr=True)
        self.parser.addSubcommand(getCmd,
                                  usage="%prog COMMAND <dict-file> <time>")

        difftimeCmd=Subcommand(name='difftimes',
                               help="Compare two times",
                               nr=3,
                               exactNr=True)
        self.parser.addSubcommand(difftimeCmd,
                                  usage="%prog COMMAND <dict-file> <time1> <time2>")

        defaultCmd=Subcommand(name='defaults',
                              help="Calculate a 'tolerances' dictionary to insert into the data. Specify the number of digits you want to be relevant",
                              nr=2,
                              exactNr=True)
        self.parser.addSubcommand(defaultCmd,
                                  usage="%prog COMMAND <dict-file> <digits>")

        diffCmd=Subcommand(name='diff',
                           help="Compare two dictionaries assuming that they were made with the same specification",
                           aliases=("compare","diffcases"),
                           nr=2,
                           exactNr=True)
        self.parser.addSubcommand(diffCmd,
                                  usage="%prog COMMAND <dict-file1> <dict-file2>")

        diffCmd.parser.add_option("--digits",
                                  action="store",
                                  dest="nrDigits",
                                  type="int",
                                  default=3,
                                  help="Number of digits that are relevant if no 'tolerances' dictionary is found. Default: 3")

        diffCmd.parser.add_option("--additional-digits",
                                  action="store",
                                  dest="addDigits",
                                  type="int",
                                  default=0,
                                  help="Number of digits to add if a 'tolerances' dictionary is found. Default: 0")

        for cmd in [diffCmd]:
            timeGrp=OptionGroup(cmd.parser,
                                "Time selection",
                                "Select time-steps to operate on. These options can be used at the same time and only add time-steps")
            timeGrp.add_option("--time",
                               action="append",
                               dest="times",
                               type="float",
                               default=[],
                               help="Select a time. Can be used more than once. If unset all times are used")
            timeGrp.add_option("--after-time",
                               dest="afterTime",
                               default=None,
                               type="float",
                               help="Select all times after this time")
            timeGrp.add_option("--before-time",
                               dest="beforeTime",
                               default=None,
                               type="float",
                               help="Select all times before this time")
            cmd.parser.add_option_group(timeGrp)

    def run(self):

        def selectTimes(data):
            if len(self.opts.times)==0 and self.opts.afterTime is None and self.opts.beforeTime is None:
                return None
            times=self.opts.times[:]
            availTimes=data.times
            if self.opts.afterTime is not None:
                times+=[t for t in availTimes if float(t)>=self.opts.afterTime]
            if self.opts.beforeTime is not None:
                times+=[t for t in availTimes if float(t)<=self.opts.beforeTime]

            times=list(set(times))
            times.sort()
            return times

        args=self.parser.getArgs()
        if self.cmdname=="info":
            f=FunkyDoCalcFile(args[0])
            times=f.times
            if len(times)==0:
                print_("No times")
            else:
                if len(times)==1:
                    print_("Single time:",times[0])
                else:
                    print_(len(times),"times from",times[0],"to",times[-1])
            print_("\nValues:")
            maxlen=max(len(k) for k in f.entries.keys())
            form="%%%ds : " % (maxlen+1)
            for k,v in iteritems(f.entries):
                print_(form % k,", ".join("%s (%d values)"%i for i in iteritems(v)))
        elif self.cmdname=="min":
            f=FunkyDoCalcFile(args[0])
            pprint(f.min)
        elif self.cmdname=="absmax":
            f=FunkyDoCalcFile(args[0])
            pprint(f.absmax)
        elif self.cmdname=="max":
            f=FunkyDoCalcFile(args[0])
            pprint(f.max)
        elif self.cmdname=="span":
            f=FunkyDoCalcFile(args[0])
            pprint(f.span)
        elif self.cmdname=="relativespan":
            f=FunkyDoCalcFile(args[0])
            pprint(f.span/f.absmax)
        elif self.cmdname=="get":
            f=FunkyDoCalcFile(args[0])
            t=float(args[1])
            pprint(f[t])
        elif self.cmdname=="defaults":
            f=FunkyDoCalcFile(args[0])
            d=int(args[1])
            print_(gen(f.calcTolerances(d)))
        elif self.cmdname=="difftimes":
            f=FunkyDoCalcFile(args[0])
            t1=float(args[1])
            t2=float(args[2])
            pprint(f[t1]-f[t2])
            #            print_(gen(f[t]))
        elif self.cmdname=="diff":
            f1=FunkyDoCalcFile(args[0])
            f2=FunkyDoCalcFile(args[1])
            times=selectTimes(f1)
            checks,problems=f1.compare(f2,
                                       digits=self.opts.nrDigits,
                                       additionalDigits=self.opts.addDigits,
                                       times=times)
            print_("\n".join(problems))
            if len(problems)>0:
                print_("\n\n {} problems".format(len(problems)))
            print_(checks,"Checks done")
        else:
            self.error("Subcommand",self.cmdname,"not implemeted")
