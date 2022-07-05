#  ICE Revision: $Id$
"""
Application class that implements pyFoamSamplePlot.py
"""

import sys,string
from os import path
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from PyFoam.RunDictionary.SampleDirectory import SampleDirectory
from PyFoam.Basics.SpreadsheetData import WrongDataSize

from PyFoam.Error import error,warning

from .PlotHelpers import cleanFilename

from PyFoam.ThirdParty.six import print_

class SamplePlot(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Reads data from the sample-dictionary and generates appropriate
gnuplot-commands. As an option the data can be written to a CSV-file.
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <casedir>",
                                   nr=1,
                                   changeVersion=False,
                                   interspersed=True,
                                   **kwargs)

    modeChoices=["separate","timesInOne","fieldsInOne","linesInOne","complete"]

    def addOptions(self):
        data=OptionGroup(self.parser,
                          "Data",
                          "Select the data to plot")
        self.parser.add_option_group(data)

        data.add_option("--line",
                        action="append",
                        default=None,
                        dest="line",
                        help="Thesample line from which data is plotted (can be used more than once)")
        data.add_option("--field",
                        action="append",
                        default=None,
                        dest="field",
                        help="The fields that are plotted (can be used more than once). If none are specified all found fields are used")
        data.add_option("--pattern-for-line",
                        action="store",
                        default=None,
                        dest="linePattern",
                        help="Usually the name of the line is automatically determined from the file name by taking the first part. If this regular expression is specified then it is used: the first group in the pattern will be the line name")
        data.add_option("--default-value-names",
                        action="store",
                        default=None,
                        dest="valueNames",
                        help="Usually the names of the values automatically determined from the file. If they are specified (as a comma separated list of names) then these names are used and all the files MUST have these values")
        data.add_option("--no-extension-needed",
                        action="store_false",
                        default=True,
                        dest="needsExtension",
                        help="The files do not have an extension")
        data.add_option("--is-distribution",
                        action="store_true",
                        default=False,
                        dest="isDistribution",
                        help="The files in the directory are distributions. This sets the names of the lines and fields accordingly")
        data.add_option("--postfix-for-field-names",
                        action="append",
                        default=[],
                        dest="fieldPostfix",
                        help="Possible postfix for field names of the form 'name_postfix'. Note that this should not be a possible field name")
        data.add_option("--prefix-for-field-names",
                        action="append",
                        default=[],
                        dest="fieldPrefix",
                        help="Possible prefix for field names of the form 'prefix_name'. Note that this should not be a possible field name")
        data.add_option("--directory-name",
                        action="store",
                        default="samples",
                        dest="dirName",
                        help="Alternate name for the directory with the samples (Default: %default)")
        data.add_option("--preferred-component",
                        action="store",
                        type="int",
                        default=None,
                        dest="component",
                        help="The component that should be used for vectors. Otherwise the absolute value is used")
        data.add_option("--reference-directory",
                        action="store",
                        default=None,
                        dest="reference",
                        help="A reference directory. If fitting sample data is found there it is plotted alongside the regular data")
        data.add_option("--reference-case",
                        action="store",
                        default=None,
                        dest="referenceCase",
                        help="A reference case where a directory with the same name is looked for. Mutual exclusive with --reference-directory")

        scale=OptionGroup(self.parser,
                          "Scale",
                          "Scale the data before comparing (not used during plotting)")
        self.parser.add_option_group(scale)
        scale.add_option("--scale-data",
                         action="store",
                         type="float",
                         default=1,
                         dest="scaleData",
                         help="Scale the data by this factor. Default: %default")
        scale.add_option("--offset-data",
                         action="store",
                         type="float",
                         default=0,
                         dest="offsetData",
                         help="Offset the data by this factor. Default: %default")
        scale.add_option("--scale-x-axis",
                         action="store",
                         type="float",
                         default=1,
                         dest="scaleXAxis",
                         help="Scale the x-axis by this factor. Default: %default")
        scale.add_option("--offset-x-axis",
                         action="store",
                         type="float",
                         default=0,
                         dest="offsetXAxis",
                         help="Offset the x-axis by this factor. Default: %default")

        scale.add_option("--scale-reference-data",
                         action="store",
                         type="float",
                         default=1,
                         dest="scaleReferenceData",
                         help="Scale the reference data by this factor. Default: %default")
        scale.add_option("--offset-reference-data",
                         action="store",
                         type="float",
                         default=0,
                         dest="offsetReferenceData",
                         help="Offset the reference data by this factor. Default: %default")
        scale.add_option("--scale-reference-x-axis",
                         action="store",
                         type="float",
                         default=1,
                         dest="scaleReferenceXAxis",
                         help="Scale the reference x-axis by this factor. Default: %default")
        scale.add_option("--offset-reference-x-axis",
                         action="store",
                         type="float",
                         default=0,
                         dest="offsetReferenceXAxis",
                         help="Offset the reference x-axis by this factor. Default: %default")

        time=OptionGroup(self.parser,
                         "Time",
                         "Select the times to plot")
        self.parser.add_option_group(time)

        time.add_option("--time",
                        action="append",
                        default=None,
                        dest="time",
                        help="The times that are plotted (can be used more than once). If none are specified all found times are used")
        time.add_option("--min-time",
                        action="store",
                        type="float",
                        default=None,
                        dest="minTime",
                        help="The smallest time that should be used")
        time.add_option("--max-time",
                        action="store",
                        type="float",
                        default=None,
                        dest="maxTime",
                        help="The biggest time that should be used")
        time.add_option("--fuzzy-time",
                        action="store_true",
                        default=False,
                        dest="fuzzyTime",
                        help="Try to find the next timestep if the time doesn't match exactly")
        time.add_option("--latest-time",
                        action="store_true",
                        default=False,
                        dest="latestTime",
                        help="Take the latest time from the data")
        time.add_option("--reference-time",
                        action="store",
                        default=None,
                        dest="referenceTime",
                        help="Take this time from the reference data (instead of using the same time as the regular data)")
        time.add_option("--tolerant-reference-time",
                        action="store_true",
                        default=False,
                        dest="tolerantReferenceTime",
                        help="Take the reference-time that is nearest to the selected time")

        output=OptionGroup(self.parser,
                           "Appearance",
                           "How it should be plotted")
        self.parser.add_option_group(output)

        output.add_option("--mode",
                          type="choice",
                          default="separate",
                          dest="mode",
                          action="store",
                          choices=self.modeChoices,
                          help="What kind of plots are generated: a) separate for every time, line and field b) all times of a field in one plot c) all fields of a time in one plot d) all lines in one plot e) everything in one plot (Names: "+", ".join(self.modeChoices)+") Default: %default")
        output.add_option("--unscaled",
                          action="store_false",
                          dest="scaled",
                          default=True,
                          help="Don't scale a value to the same range for all plots")
        output.add_option("--scale-all",
                          action="store_true",
                          dest="scaleAll",
                          default=False,
                          help="Use the same scale for all fields (else use one scale for each field)")
        output.add_option("--scale-domain",
                          action="store_true",
                          dest="scaleDomain",
                          default=False,
                          help="Automatically scale the x-domain to the same length for all plots")
        output.add_option("--domain-minimum",
                          action="store",
                          type="float",
                          dest="domainMin",
                          default=None,
                          help="Use this value as the minimum for the x-domain for all plots")
        output.add_option("--domain-maximum",
                          action="store",
                          type="float",
                          dest="domainMax",
                          default=None,
                          help="Use this value as the maximum for the x-domain for all plots")
        output.add_option("--gnuplot-file",
                          action="store",
                          dest="gnuplotFile",
                          default=None,
                          help="Write the necessary gnuplot commands to this file. Else they are written to the standard output")
        output.add_option("--picture-destination",
                          action="store",
                          dest="pictureDest",
                          default=None,
                          help="Directory the pictures should be stored to")
        output.add_option("--name-prefix",
                          action="store",
                          dest="namePrefix",
                          default=None,
                          help="Prefix to the picture-name")
        output.add_option("--csv-file",
                          action="store",
                          dest="csvFile",
                          default=None,
                          help="Write the data to a CSV-file instead of the gnuplot-commands")
        output.add_option("--excel-file",
                          action="store",
                          dest="excelFile",
                          default=None,
                          help="Write the data to a Excel-file instead of the gnuplot-commands")
        output.add_option("--pandas-data",
                          action="store_true",
                          dest="pandasData",
                          default=False,
                          help="Pass the raw data in pandas-format")
        output.add_option("--numpy-data",
                          action="store_true",
                          dest="numpyData",
                          default=False,
                          help="Pass the raw data in numpy-format")

        data.add_option("--info",
                        action="store_true",
                        dest="info",
                        default=False,
                        help="Print info about the sampled data and exit")
        output.add_option("--style",
                          action="store",
                          default="lines",
                          dest="style",
                          help="Gnuplot-style for the data (Default: %default)")
        output.add_option("--clean-filename",
                          action="store_true",
                          dest="cleanFilename",
                          default=False,
                          help="Clean filenames so that they can be used in HTML or Latex-documents")
        output.add_option("--index-instead-of-time",
                          action="store_true",
                          dest="indexInsteadOfTime",
                          default=False,
                          help="Use an index instead of the time in the filename (mainly needed if the files are used to make a movie with FFMPEG)")
        output.add_option("--reference-prefix",
                          action="store",
                          dest="refprefix",
                          default="Reference",
                          help="Prefix that gets added to the reference lines. Default: %default")
        output.add_option("--resample-reference",
                          action="store_true",
                          dest="resampleReference",
                          default=False,
                          help="Resample the reference value to the current x-axis (for CSV or Excel-output)")
        output.add_option("--extend-data",
                          action="store_true",
                          dest="extendData",
                          default=False,
                          help="Extend the data range if it differs (for CSV or Excel-files)")
        output.add_option("--silent",
                          action="store_true",
                          dest="silent",
                          default=False,
                          help="Don't write to screen (with the silent and the compare-options)")

        numerics=OptionGroup(self.parser,
                             "Quantify",
                             "Metrics of the data and numerical comparisons")
        self.parser.add_option_group(numerics)
        numerics.add_option("--metrics",
                            action="store_true",
                            dest="metrics",
                            default=None,
                            help="Print the metrics of the data sets")
        numerics.add_option("--compare",
                            action="store_true",
                            dest="compare",
                            default=None,
                            help="Compare all data sets that are also in the reference data")
        numerics.add_option("--common-range-compare",
                            action="store_true",
                            dest="commonRange",
                            default=None,
                            help="When comparing two datasets only use the common time range")
        numerics.add_option("--index-tolerant-compare",
                            action="store_true",
                            dest="indexTolerant",
                            default=None,
                            help="Compare two data sets even if they have different indizes")
        numerics.add_option("--use-reference-for-comparison",
                            action="store_false",
                            dest="compareOnOriginal",
                            default=True,
                            help="Use the reference-data as the basis for the numerical comparison. Otherwise the original data will be used")

    def run(self):
        if self.opts.isDistribution:
            if self.opts.valueNames or self.opts.linePattern:
                self.error("The option --is-distribution can not be used with --pattern-for-line or --default-value-names")
            #            self.opts.valueNames="normalized,raw"
            self.opts.linePattern=".+istribution_(.+)"
            self.opts.needsExtension=False

        # remove trailing slashif present
        if self.opts.dirName[-1]==path.sep:
            self.opts.dirName=self.opts.dirName[:-1]

        usedDirName=self.opts.dirName.replace("/","_")

        if self.opts.valueNames==None:
            usedValueNames=None
        else:
            usedValueNames=self.opts.valueNames.split(",")

        samples=SampleDirectory(self.parser.getArgs()[0],
                                dirName=self.opts.dirName,
                                postfixes=self.opts.fieldPostfix,
                                prefixes=self.opts.fieldPrefix,
                                valueNames=usedValueNames,
                                namesFromFirstLine=self.opts.isDistribution,
                                linePattern=self.opts.linePattern,
                                needsExtension=self.opts.needsExtension)
        reference=None
        if self.opts.reference and self.opts.referenceCase:
            self.error("Options --reference-directory and --reference-case are mutual exclusive")
        if (self.opts.csvFile or self.opts.excelFile or self.opts.pandasData or self.opts.numpyData)  and (self.opts.compare or self.opts.metrics):
            self.error("Options --csv-file/--excel-file/--pandas-data/--numpy-data and --compare/--metrics are mutual exclusive")

        if self.opts.reference:
            reference=SampleDirectory(self.parser.getArgs()[0],
                                      dirName=self.opts.reference,
                                      postfixes=self.opts.fieldPostfix,
                                      prefixes=self.opts.fieldPrefix)
        elif self.opts.referenceCase:
            reference=SampleDirectory(self.opts.referenceCase,
                                      dirName=self.opts.dirName,
                                      postfixes=self.opts.fieldPostfix,
                                      prefixes=self.opts.fieldPrefix)

        if reference:
            if path.samefile(reference.dir,samples.dir):
                self.error("Used sample directory",samples.dir,
                           "and reference directory",reference.dir,
                           "are the same")

        lines=samples.lines()
        times=samples.times

        if self.opts.info:
            if not self.opts.silent:
                print_("Times : ",samples.times)
                print_("Lines : ",samples.lines())
                print_("Fields: ",list(samples.values()))

            self.setData({'times'  : samples.times,
                          'lines'  : samples.lines(),
                          'values' : list(samples.values())})

            if reference:
                if not self.opts.silent:
                    print_("\nReference Data:")
                    print_("Times : ",reference.times)
                    print_("Lines : ",reference.lines())
                    print_("Fields: ",list(reference.values()))
                self.setData({'reference':{'times'  : samples.times,
                                           'lines'  : samples.lines(),
                                           'values' : list(samples.values())}})

            return 0

        if self.opts.line==None:
            #            error("At least one line has to be specified. Found were",samples.lines())
            self.opts.line=lines
        else:
            for l in self.opts.line:
                if l not in lines:
                    error("The line",l,"does not exist in",lines)

        if self.opts.latestTime:
            if self.opts.time:
                self.opts.time.append(samples.times[-1])
            else:
                self.opts.time=[samples.times[-1]]

        if self.opts.maxTime or self.opts.minTime:
            if self.opts.time:
                error("Times",self.opts.time,"and range [",self.opts.minTime,",",self.opts.maxTime,"] set: contradiction")
            self.opts.time=[]
            if self.opts.maxTime==None:
                self.opts.maxTime= 1e20
            if self.opts.minTime==None:
                self.opts.minTime=-1e20

            for t in times:
                if float(t)<=self.opts.maxTime and float(t)>=self.opts.minTime:
                    self.opts.time.append(t)

            if len(self.opts.time)==0:
                error("No times in range [",self.opts.minTime,",",self.opts.maxTime,"] found: ",times)
        elif self.opts.time:
            iTimes=self.opts.time
            self.opts.time=[]
            for t in iTimes:
                if t in samples.times:
                    self.opts.time.append(t)
                elif self.opts.fuzzyTime:
                    tf=float(t)
                    use=None
                    dist=1e20
                    for ts in samples.times:
                        if abs(tf-float(ts))<dist:
                            use=ts
                            dist=abs(tf-float(ts))
                    if use and use not in self.opts.time:
                        self.opts.time.append(use)
                else:
                    pass
                #                    self.warning("Time",t,"not found in the sample-times. Use option --fuzzy")
        if self.opts.tolerantReferenceTime:
            if self.opts.referenceTime:
                self.error("--tolerant-reference-time and --reference-time can't be used at the same time")
            refTimes={}
            for t in self.opts.time:
                dist=1e20
                for rt in reference.times:
                    if abs(float(t)-float(rt))<dist:
                        refTimes[t]=rt
                        dist=abs(float(t)-float(rt))

        plots=[]
        oPlots=[]
        rPlots=[]

        if self.opts.mode=="separate":
            if self.opts.time==None:
                self.opts.time=samples.times
            if self.opts.field==None:
                self.opts.field=list(samples.values())
            if self.opts.line==None:
                self.opts.line=samples.lines()
            for t in self.opts.time:
                for f in self.opts.field:
                    for l in self.opts.line:
                        plot=samples.getData(line=[l],
                                             value=[f],
                                             time=[t],
                                             scale=(self.opts.scaleXAxis,
                                                    self.opts.scaleData),
                                             offset=(self.opts.offsetXAxis,
                                                     self.opts.offsetData))
                        oPlots.append(plot[:])
                        if reference:
                            rT=[t]
                            if self.opts.referenceTime:
                                rT=[self.opts.referenceTime]
                            elif self.opts.tolerantReferenceTime:
                                rT=[refTimes[t]]
                            p=reference.getData(line=[l],
                                                value=[f],
                                                time=rT,
                                                note=self.opts.refprefix+" ",
                                                scale=(self.opts.scaleReferenceXAxis,
                                                       self.opts.scaleReferenceData),
                                                offset=(self.opts.offsetReferenceXAxis,
                                                        self.opts.offsetReferenceData))
                            rPlots.append(p)
                            plot+=p
                        plots.append(plot)

        elif self.opts.mode=="timesInOne":
            if self.opts.field==None:
                self.opts.field=list(samples.values())
            if self.opts.line==None:
                self.opts.line=samples.lines()
            for f in self.opts.field:
                for l in self.opts.line:
                    plot=samples.getData(line=[l],
                                         value=[f],
                                         time=self.opts.time)
                    oPlots.append(plot[:])

                    if reference:
                        rT=self.opts.time
                        if self.opts.referenceTime:
                            rT=[self.opts.referenceTime]
                        elif self.opts.tolerantReferenceTime:
                            rT=[refTimes[t]]
                        p=reference.getData(line=[l],
                                            value=[f],
                                            time=rT,
                                            note=self.opts.refprefix+" ")
                        rPlots.append(p)
                        plot+=p

                    plots.append(plot)

        elif self.opts.mode=="fieldsInOne":
            if self.opts.scaled and not self.opts.scaleAll:
                warning("In mode '",self.opts.mode,"' all fields are scaled to the same value")
                self.opts.scaleAll=True

            if self.opts.time==None:
                self.opts.time=samples.times
            if self.opts.line==None:
                self.opts.line=samples.lines()
            for t in self.opts.time:
                for l in self.opts.line:
                    plot=samples.getData(line=[l],
                                         value=self.opts.field,
                                         time=[t])
                    oPlots.append(plot[:])
                    if reference:
                        rT=t
                        if self.opts.referenceTime:
                            rT=self.opts.referenceTime
                        elif self.opts.tolerantReferenceTime:
                            rT=refTimes[t]
                        p=reference.getData(line=[l],
                                            value=self.opts.field,
                                            time=[rT],
                                            note=self.opts.refprefix+" ")
                        rPlots.append(p)
                        plot+=p

                    plots.append(plot)

        elif self.opts.mode=="linesInOne":
            if self.opts.field==None:
                self.opts.field=list(samples.values())
            if self.opts.time==None:
                self.opts.time=samples.times
            for f in self.opts.field:
                for t in self.opts.time:
                    plot=samples.getData(line=self.opts.line,
                                         value=[f],
                                         time=[t])
                    oPlots.append(plot[:])

                    if reference:
                        rT=t
                        if self.opts.referenceTime:
                            rT=self.opts.referenceTime
                        elif self.opts.tolerantReferenceTime:
                            rT=refTimes[t]
                        p=reference.getData(line=self.opts.line,
                                            value=[f],
                                            time=[rT],
                                            note=self.opts.refprefix+" ")
                        rPlots.append(p)
                        plot+=p

                    plots.append(plot)

        elif self.opts.mode=="complete":
            if self.opts.scaled and not self.opts.scaleAll:
                warning("In mode '",self.opts.mode,"' all fields are scaled to the same value")
                self.opts.scaleAll=True

            plot=samples.getData(line=self.opts.line,
                                 value=self.opts.field,
                                 time=self.opts.time)
            oPlots.append(plot[:])
            if reference:
                rT=self.opts.time
                if self.opts.referenceTime:
                    rT=[self.opts.referenceTime]
                elif self.opts.tolerantReferenceTime:
                    rT=[refTimes[t]]
                p=reference.getData(line=self.opts.line,
                                    value=self.opts.field,
                                    time=rT,
                                    note=self.opts.refprefix+" ")
                plot+=p
                rPlots.append(p)

            plots.append(plot)

        xMin,xMax=None,None
        if self.opts.scaleDomain:
            if self.opts.domainMin or self.opts.domainMax:
                self.error("--scale-domain used. Can't use --domain-minimum or --domain-maximum")
            xMin,xMax=1e40,-1e40
            for p in plots:
                for d in p:
                    mi,mx=d.domain()
                    xMin=min(xMin,mi)
                    xMax=max(xMax,mx)
        else:
            xMin,xMax=self.opts.domainMin,self.opts.domainMax

        if self.opts.scaled:
            if self.opts.scaleAll:
                vRange=None
            else:
                vRanges={}

            for p in plots:
                for d in p:
                    mi,ma=d.range(component=self.opts.component)
                    nm=d.name
                    if not self.opts.scaleAll:
                        if nm in vRanges:
                            vRange=vRanges[nm]
                        else:
                            vRange=None

                    if vRange==None:
                        vRange=mi,ma
                    else:
                        vRange=min(vRange[0],mi),max(vRange[1],ma)
                    if not self.opts.scaleAll:
                        vRanges[nm]=vRange

        result="set term png\n"

        plots=[p for p in plots if len(p)>0]

        if len(plots)<1:
            self.error("No plots produced. Nothing done")

        for p in plots:
            if len(p)<1:
                continue

            name=""

            if self.opts.namePrefix:
                name+=self.opts.namePrefix+"_"
            name+=usedDirName
            title=None
            tIndex=times.index(p[0].time())

            #            name+="_"+"_".join(self.opts.line)

            if self.opts.mode=="separate":
                name+="_%s"        % (p[0].line())
                if self.opts.indexInsteadOfTime:
                    name+="_%s_%04d"   % (p[0].name,tIndex)
                else:
                    name+="_%s_t=%f"   % (p[0].name,float(p[0].time()))

                title="%s at t=%f on %s" % (p[0].name,float(p[0].time()),p[0].line())
            elif self.opts.mode=="timesInOne":
                name+="_%s"        % (p[0].line())
                if self.opts.time!=None:
                    name+="_"+"_".join(["t="+t for t in self.opts.time])
                name+="_%s" % p[0].name
                title="%s on %s"  % (p[0].name,p[0].line())
            elif self.opts.mode=="fieldsInOne":
                name+="_%s"        % (p[0].line())
                if self.opts.field!=None:
                    name+="_"+"_".join(self.opts.field)
                if self.opts.time!=None:
                    name+="_"+"_".join(["t="+t for t in self.opts.time])
                name+="_%04d" % tIndex
                title="t=%f on %s" % (float(p[0].time()),p[0].line())
            elif self.opts.mode=="linesInOne":
                name+="_%s"        % (p[0].name)
                if self.opts.line!=None:
                    name+="_"+"_".join(self.opts.line)
                if self.opts.indexInsteadOfTime:
                    name+="_%04d" % tIndex
                else:
                    name+="_t=%f" % float(p[0].time())
                title="%s at t=%f" % (p[0].name,float(p[0].time()))
            elif self.opts.mode=="complete":
                pass

            name+=".png"
            if self.opts.pictureDest:
                name=path.join(self.opts.pictureDest,name)

            if self.opts.cleanFilename:
                name=cleanFilename(name)

            result+='set output "%s"\n' % name
            if title!=None:
                result+='set title "%s"\n' % title.replace("_","\\_")

            result+="plot "
            if self.opts.scaled:
                if not self.opts.scaleAll:
                    vRange=vRanges[p[0].name]

                # only scale if extremas are sufficiently different
                if abs(vRange[0]-vRange[1])>1e-5*max(abs(vRange[0]),abs(vRange[1])) and max(abs(vRange[0]),abs(vRange[1]))>1e-10:
                    yRange="[%g:%g] " % vRange
                else:
                    yRange="[]"
            else:
                yRange="[]"

            if xMin or xMax:
                xRange="["
                if xMin:
                    xRange+=str(xMin)
                xRange+=":"
                if xMax:
                    xRange+=str(xMax)
                xRange+="]"
            else:
                xRange="[]"

            if self.opts.scaled or xMin or xMax:
                result+=xRange+yRange

            first=True

            for d in p:
                if first:
                    first=False
                else:
                    result+=", "

                colSpec=d.index+1
                if d.isVector():
                    if self.opts.component!=None:
                        colSpec=d.index+1+self.opts.component
                    else:
                        colSpec="(sqrt($%d**2+$%d**2+$%d**2))" % (d.index+1,d.index+2,d.index+3)

                        #                result+='"%s" using 1:%s ' % (d.file,colSpec)

                def makeCol(spec,sc,off):
                    if type(spec)==str:
                        pre=""
                    else:
                        pre="$"
                        spec=str(spec)
                    if sc==1:
                        if off==0:
                            return spec
                        else:
                            return "(%s%s+%f)" % (pre,spec,off)
                    else:
                        if off==0:
                            return "(%s%s*%f)" % (pre,spec,sc)
                        else:
                            return "(%s%s*%f+%f)" % (pre,spec,sc,off)

                result+='"%s" using %s:%s ' % (d.file,
                                              makeCol(1,d.scale[0],d.offset[0]),
                                              makeCol(colSpec,d.scale[1],d.offset[1]))

                title=d.note
                if self.opts.mode=="separate":
                    title+=""
                elif self.opts.mode=="timesInOne":
                    title+="t=%f" % float(d.time())
                elif self.opts.mode=="fieldsInOne":
                    title+="%s"   % d.name
                elif self.opts.mode=="linesInOne":
                    title+="t=%f"   % float(d.time())
                elif self.opts.mode=="complete":
                    title+="%s at t=%f" % (d.name,float(d.time()))

                if len(self.opts.line)>1:
                    title+=" on %s" % d.line()

                if title=="":
                    result+="notitle "
                else:
                    result+='title "%s" ' % title.replace("_","\\_")

                result+="with %s " % self.opts.style

            result+="\n"

        if self.opts.csvFile or self.opts.excelFile or self.opts.pandasData or self.opts.numpyData:
            tmp=sum(plots,[])
            c=tmp[0]()
            for p in tmp[1:]:
                try:
                    c+=p()
                except WrongDataSize:
                    if self.opts.resampleReference:
                        sp=p()
                        for n in sp.names()[1:]:
                            data=c.resample(sp,
                                            n,
                                            extendData=self.opts.extendData)
                            try:
                                c.append(n,data)
                            except ValueError:
                                c.append(self.opts.refprefix+" "+n,data)
                    else:
                        self.warning("Try the --resample-option")
                        raise

            if self.opts.csvFile:
                c.writeCSV(self.opts.csvFile)
            if self.opts.excelFile:
                c.getData().to_excel(self.opts.excelFile)
            if self.opts.pandasData:
                self.setData({"series":c.getSeries(),
                              "dataFrame":c.getData()})
            if self.opts.numpyData:
                self.setData({"data":c.data.copy()})

        elif self.opts.compare or self.opts.metrics:
            statData={}
            if self.opts.compare:
                statData["compare"]={}
            if self.opts.metrics:
                statData["metrics"]={}
            for p in self.opts.line:
                if self.opts.compare:
                    statData["compare"][p]={}
                if self.opts.metrics:
                    statData["metrics"][p]={}

            oPlots=[item for sublist in oPlots for item in sublist]
            rPlots=[item for sublist in rPlots for item in sublist]
            if len(rPlots)!=len(oPlots) and self.opts.compare:
                self.error("Number of original data sets",len(oPlots),
                           "is not equal to the reference data sets",
                           len(rPlots))
            if len(rPlots)==0 and self.opts.metrics:
                rPlots=[None]*len(oPlots)

            for o,r in zip(oPlots,rPlots):
                data=o(scaleData=self.opts.scaleData,
                       offsetData=self.opts.offsetData,
                       scaleX=self.opts.scaleXAxis,
                       offsetX=self.opts.offsetXAxis)
                if self.opts.compare:
                    if o.name!=r.name or (o.index!=r.index and not self.opts.indexTolerant):
                        self.error("Data from original",o.name,o.index,
                                   "and reference",r.name,r.index,
                                   "do not match. Try --index-tolerant-compare if you're sure that the data is right")
                    ref=r(scaleData=self.opts.scaleReferenceData,
                          offsetData=self.opts.offsetReferenceData,
                          scaleX=self.opts.scaleReferenceXAxis,
                          offsetX=self.opts.offsetReferenceXAxis)
                else:
                    ref=None
                for i,n in enumerate(data.names()):
                    if i==0:
                        continue
                    indexName=o.name
                    if n.split(" ")[-1]!=indexName:
                        indexName=n.split(" ")[-1]

                    if self.opts.metrics:
                        if not self.opts.silent:
                            print_("Metrics for",indexName,"(Path:",o.file,")")
                        result=data.metrics(data.names()[i],
                                            minTime=self.opts.minTime,
                                            maxTime=self.opts.maxTime)
                        statData["metrics"][o.line()][indexName]=result
                        if not self.opts.silent:
                            print_("  Min                :",result["min"])
                            print_("  Max                :",result["max"])
                            print_("  Average            :",result["average"])
                            print_("  Weighted average   :",result["wAverage"])
                            if not self.opts.compare:
                                print_("Data size:",data.size())
                            print_("  Time Range         :",result["tMin"],result["tMax"])
                    if self.opts.compare:
                        oname=data.names()[i]
                        if self.opts.referenceTime or self.opts.tolerantReferenceTime:
                            oname=ref.names()[i]
                        if not self.opts.silent:
                            print_("Comparing",indexName,"with name",oname,"(Path:",r.file,")",end="")
                        if self.opts.compareOnOriginal:
                            if not self.opts.silent:
                                print_("on original data points")
                            result=data.compare(ref,
                                                data.names()[i],
                                                otherName=oname,common=self.opts.commonRange,
                                                minTime=self.opts.minTime,
                                                maxTime=self.opts.maxTime)
                        else:
                            if not self.opts.silent:
                                print_("on reference data points")
                            result=ref.compare(data,
                                               oname,
                                               otherName=data.names()[i],
                                               common=self.opts.commonRange,
                                               minTime=self.opts.minTime,
                                               maxTime=self.opts.maxTime)
                        statData["compare"][o.line()][indexName]=result
                        if not self.opts.silent:
                            print_("  Max difference     :",result["max"],"(at",result["maxPos"],")")
                            print_("  Average difference :",result["average"])
                            print_("  Weighted average   :",result["wAverage"])
                            print_("Data size:",data.size(),"Reference:",ref.size())
                            if not self.opts.metrics:
                                print_("  Time Range         :",result["tMin"],result["tMax"])
                    if not self.opts.silent:
                        print_()

            self.setData(statData)
        else:
            dest=sys.stdout
            if self.opts.gnuplotFile:
                dest=open(self.opts.gnuplotFile,"w")

            dest.write(result)

# Should work with Python3 and Python2
