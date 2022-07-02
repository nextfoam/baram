#  ICE Revision: $Id$
"""
Class that implements pyFoamPVSnapshot
"""

from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from .PrepareCase import PrepareCase

from .CommonSelectTimesteps import CommonSelectTimesteps

from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile,FoamStringParser

from PyFoam.Paraview.ServermanagerWrapper import ServermanagerWrapper as SM
from PyFoam.Paraview.StateFile import StateFile
from PyFoam.Paraview import version as PVVersion

from PyFoam.FoamInformation import foamVersion

from PyFoam.ThirdParty.six import print_

from os import path,unlink
import sys,string

class PVSnapshot(PyFoamApplication,
                 CommonSelectTimesteps ):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Generates snapshots of an OpenFOAM-case and a predefined
paraview-State-File using the PV3FoamReader that comes with OpenFOAM.

The state-file can be generated using a different case (the script
adjusts it before using) but the original case has to have a similar
structure to the current one. Also exactly one PV3Reader has to be
used in the state-file (this requirement is fullfilled if the
StateFile was generated using paraFoam)

In TextSources the string "%(casename)s" gets replaced by the
casename. Additional replacements can be specified

If the utility has Mesa in the name then instead of the native
OpenGL Mesa is used (if compiled into the used Paraview)

View numbers are reordered by the upper left corner because the order
seems to change non-deterministically
"""
        CommonSelectTimesteps.__init__(self)

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <case>",
                                   interspersed=True,
                                   nr=1,
                                   **kwargs)

    picTypeTable={"png"  :  "vtkPNGWriter",
                  "jpg"  :  "vtkJPEGWriter"}

    geomTypeTable={"x3d"   : "X3DExporter",
                   "x3db"  : "X3DExporterBinary",
                   "vrml"  : "VRMLExporter",
                   "wgl"   : "WebGLExporter",
                   "pov"   : "POVExporter"}

    def addOptions(self):
        CommonSelectTimesteps.addOptions(self,defaultUnique=True)

        paraview=OptionGroup(self.parser,
                           "Paraview specifications",
                           "Options concerning paraview")
        paraview.add_option("--state-file",
                            dest="state",
                            default=None,
                            help="The pvsm-file that should be used. If none is specified the file 'default.pvsm' in the case-directory is used")
        paraview.add_option("--magnification",
                            dest="magnification",
                            default=1,
                            type="int",
                            help="Magnification factor of the picture (integer). Default: %default")
        paraview.add_option("--quality",
                            dest="quality",
                            default=50,
                            type="int",
                            help="Quality of the picture. 100: best, 0: worst. This also influneces the amount of memory the picture uses. Default: %default")
        paraview.add_option("--type",
                            dest="picType",
                            type="choice",
                            choices=list(self.picTypeTable.keys()),
                            default="png",
                            help="The type of the bitmap-file. Possibilities are "+", ".join(self.picTypeTable.keys())+". Default: %default")
        paraview.add_option("--no-progress",
                            dest="progress",
                            action="store_false",
                            default=True,
                            help="Paraview will not print the progress of the filters")
        paraview.add_option("--no-offscreen-rendering",
                            dest="offscreenRender",
                            action="store_false",
                            default=True,
                            help="Do not do offscreen rendering (use if offscreen rendering produces a segmentation fault)")
        if PVVersion()>=(4,2):
            paraview.add_option("--no-layouts",
                                dest="doLayouts",
                                action="store_false",
                                default=True,
                                help="Do not use the layouts but generate separate pictures of the view (this is the behaviour before Paraview 4.2)")
        if PVVersion()>=(5,4):
            paraview.add_option("--separator-width",
                                dest="separatorWidth",
                                default=0,
                                type="int",
                                help="Width of the separator between views in pixels. Default: %default")
            paraview.add_option("--transparent-background",
                                dest="transparentBackground",
                                action="store_true",
                                default=False,
                                help="Make the background transparent")
            paraview.add_option("--x-resolution",
                                dest="xRes",
                                default=None,
                                type="int",
                                help="If set then the image is scaled to this width. --magnification is ignored. If --y-resolution is set as well then the image is fixed to this size")
            paraview.add_option("--y-resolution",
                                dest="yRes",
                                default=None,
                                type="int",
                                help="If set then the image is scaled to this width. --magnification is ignored. If --x-resolution is set as well then the image is fixed to this size")

        self.parser.add_option_group(paraview)

        geometry=OptionGroup(self.parser,
                             "Geometry specification",
                             "Options for writing out geometry files")
        geometry.add_option("--geometry-type",
                            dest="geomType",
                            type="choice",
                            choices=list(self.geomTypeTable.keys()),
                            default=None,
                            help="The type of the geometry-files. Possibilities are "+", ".join(self.geomTypeTable.keys())+". Default: unset. Nothing is written")
        geometry.add_option("--no-picture-with-geometry",
                            dest="pictureWithGeometry",
                            action="store_false",
                            default=True,
                            help="Do not write a picture if geometries are written. Default is that pictures are written as well")
        geometry.add_option("--get-sources-list",
                            dest="sourcesList",
                            action="store_true",
                            default=False,
                            help="Get a list of all the sources. Nothing is written")
        geometry.add_option("--get-view-list",
                            dest="viewList",
                            action="store_true",
                            default=False,
                            help="Get a list of all the views. Nothing is written")
        geometry.add_option("--sources",
                           dest="sources",
                           default=[],
                           action="append",
                           help="Only write sources where the name matches this substring. Can be specified more than once (will write more than one file)")
        self.parser.add_option_group(geometry)

        filename=OptionGroup(self.parser,
                             "Filename specifications",
                             "The names of the resulting files")
        filename.add_option("--file-prefix",
                            dest="prefix",
                            default="Snapshot",
                            help="Start of the filename for the bitmap-files")
        filename.add_option("--no-casename",
                            dest="casename",
                            action="store_false",
                            default=True,
                            help="Do not add the casename to the filename")
        filename.add_option("--no-timename",
                          dest="timename",
                          action="store_false",
                          default=True,
                          help="Do not append the string 't=<time>' to the filename")
        filename.add_option("--no-color-prefix",
                            dest="colorPrefix",
                            action="store_false",
                            default=True,
                            help="Do not generate an automatic filename prefix if --colors-for-filters is used")
        filename.add_option("--consecutive-index-for-timesteps",
                            dest="consecutiveIndex",
                            action="store_true",
                            default=False,
                            help="Instead of using the index of the time-steps from the case number the timesteps witgh consecutive numbers (if all timesteps are selected this should be the same)")
        self.parser.add_option_group(filename)

        replace=OptionGroup(self.parser,
                            "Replacements etc",
                            "Manipuations of the statefile")
        replace.add_option("--replacements",
                            dest="replacements",
                            default="{}",
                            help="Dictionary with replacement strings. May also be in OpenFOAM-format.  Default: %default")
        replace.add_option("--casename-key",
                            dest="casenameKey",
                            default="casename",
                            help="Key with which the caename should be replaced. Default: %default")
        decoChoices=["keep","decomposed","reconstructed","auto"]
        replace.add_option("--decompose-mode",
                           dest="decomposeMode",
                           type="choice",
                           default="auto",
                           choices=decoChoices,
                           help="Whether the decomposed or the reconstructed data should be used. Possible values are"+", ".join(decoChoices)+" with default value %default. 'auto' means that the data set where more time-steps are present is used. 'keep' doesn't change the mode in the state-file. Default: %default")
        replace.add_option("--list-replacements",
                           dest="listReplacements",
                           action="store_true",
                           default=False,
                           help="Print a list with all the possible replacement keys and their values for this case")
        replace.add_option("--add-prepare-case-parameters",
                           dest="addPrepareCaseParameters",
                           action="store_true",
                           default=False,
                           help="Add parameters from the file "+PrepareCase.parameterOutFile+" to the replacements if such a file is present in the case")
        self.parser.add_option_group(replace)

        manipulate=OptionGroup(self.parser,
                               "Manipulation",
                               "How the state should be manipulated before rendering a bitmap")
        manipulate.add_option("--colors-for-filters",
                              dest="filterColors",
                              default="{}",
                              help="Dictionary which assigns colors to sources. Only working for Paraview 4.2 and higher. Note: the color function saved in the state file is used. If none is saved in the state-file a default is used (which probably is unsuitable). Default: %default. Entries are either of the form 'Clip1':'T' (then the currently used association is used) or of the form 'Clip1':('POINTS','T') or  'Clip1':('CELLS','T') then the associations are switched to point or cell values. For state files with multiple views it is also possible to specify a different color for every view by using a dictionary where the view number is the key: 'Clip1':{0:'T',2:'U'}")
        manipulate.add_option("--no-color-bar",
                              dest="noColorbar",
                              action="append",
                              default=[],
                              help="To be used with --color-for-filters: If the source is specified here the script does not attempt to add a colorbar. Can be specified more than once")
        manipulate.add_option("--views-with-colorbars",
                              dest="colorbarView",
                              action="append",
                              type="int",
                              default=[],
                              help="To be used with --color-for-filters: On which views the colorbars should be created. Can be specified more than once. If unspecified all views are used")
        manipulate.add_option("--default-field-for-colors",
                              dest="defaultField",
                              default=None,
                              help="To be used with --color-for-filters: If the color is unspecified then this color is used")
        manipulate.add_option("--rescale-color-to-source",
                              dest="rescaleToSource",
                              default=[],
                              action="append",
                              help="Looks at the specified source and rescale the field that this source is colored with to the range present in the source data. Done after everything else is set up. Can be specified more than once. Only available for Paraview 4.2 and later")
        manipulate.add_option("--color-ranges",
                              dest="colorRanges",
                              default="{}",
                              help="Dictionary with color ranges for fields. Ranges are tuples. If one of the entries is None the current minimum/maximum of the range is used. Default: %default. Example: {'T':(300,400),'U':(None,1e-3)}. Only available for Paraview 4.2 and later. If set then this value overrules --rescale-color-to-source")
        manipulate.add_option("--percentile-ranges",
                              dest="percentileRanges",
                              default="{}",
                              help="Dictionary with percentile ranges for fields. Used together wit --rescale-color-to-source. Instead of the minimum or maximum smallest and biggest cells are ignored. This allows eliminating outliers. Ranges are tuples. If one of the entries is None then 0 or 100 is used. Default: %default. Example: {'T':(1,1),'U':(None,0.5)} means that for 'T' the lowest and highest 1% are ignored. For 'U' the highest 0.5% are ignored. Only available for Paraview 4.2 and later")
        self.parser.add_option_group(manipulate)

        behaviour=OptionGroup(self.parser,
                            "Behaviour",
                            "General behaviour of the utility")
        behaviour.add_option("--verbose",
                            dest="verbose",
                            action="store_true",
                            default=False,
                            help="Print more information")
        behaviour.add_option("--analyze-state-file",
                             dest="analyzeState",
                             action="store_true",
                             default=False,
                             help="Print important properties about the state file and exit")
        behaviour.add_option("--rewrite-only",
                             dest="rewriteOnly",
                             action="store_true",
                             default=False,
                             help="Stop execution after rewriting")
        behaviour.add_option("--list-properties",
                             dest="listProperties",
                             action="store",
                             default=None,
                             help="List the properties for this source and stop")
        behaviour.add_option("--set-property",
                             dest="setProperties",
                             action="append",
                             default=[],
                             help="Set the property for a filter. The syntax of an entry is <source>:<property>:<id>=<value> which sets the value of a property of the source. The index entry is optional (then the index 0 is used). If the source or the property is not found then the utility fails. Can be specified more than once")
        self.parser.add_option_group(behaviour)

    def say(self,*stuff):
        if not self.opts.verbose:
            return
        print_("Say:",*stuff)

    def setColorTransferFunction(self,name,rng):
        from paraview.simple import GetColorTransferFunction
        tf=GetColorTransferFunction(name)
        oldMin=min(tf.RGBPoints[0::4])
        oldMax=max(tf.RGBPoints[0::4])
        newMin,newMax=rng
        if newMin==None:
            newMin=oldMin
        if newMax==None:
            newMax=oldMax
        oldRange=oldMax-oldMin
        if oldRange<1e-10:
            oldRange=1e-10
        for i in range(0,len(tf.RGBPoints),4):
            tf.RGBPoints[i]=newMin+(newMax-newMin)*((tf.RGBPoints[i]-oldMin)/oldRange)

    def _getDataRangeGeneral(self,src,nm,getRangeFunc):
        import vtk.numpy_interface.dataset_adapter as dsa
        import numpy as np

        def getRange(fld,whichComponent=-1):
            if isinstance(fld,(dsa.VTKArray,)):
                data=[fld]
            elif  isinstance(fld,(dsa.VTKCompositeDataArray,)):
                data=[f for f in fld.Arrays if isinstance(f,(dsa.VTKArray,))]
                if len(data)==0:
                    return None
            elif  isinstance(fld,(dsa.VTKNoneArray,)):
                return None
            else:
                self.error("Unimplemented GetRange for",type(fld),"when scaling",nm)

            cmpt=0
            if len(data[0].shape)==1:
                cmpt=1
            elif len(data[0].shape)==2:
                cmpt=data[0].shape[1]
                if whichComponent<0:
                    data=[np.sqrt((a**2).sum(axis=1)) for a in data]
                elif whichComponent<cmpt:
                    data=[a[:,whichComponent] for a in data]
                else:
                    self.error("Asked for component",whichComponent,
                               "but only 0 to ",cmpt-1,"available")
            else:
                self.error("Unsupported shape",data[0].shape,"for",nm)

            return getRangeFunc(data)

        from paraview.simple import servermanager as sv
        wrapped=dsa.WrapDataObject(sv.Fetch(src))

        try:
            rng=getRange(wrapped.CellData[nm])
            if rng is None:
                rng=getRange(wrapped.PointData[nm])
            if rng is None:
                rng=getRange(wrapped.FieldData[nm])
        except AttributeError:
            try:
                rng=getRange(wrapped.PointData[nm])
                if rng is None:
                    rng=getRange(wrapped.FieldData[nm])
            except AttributeError:
                try:
                    rng=getRange(wrapped.FieldData[nm])
                except AttributeError:
                    rng=None
        return rng

    def getDataRange(self,src,nm):
        def getRangeFunc(fld):
            miVals=[f.min() for f in fld]
            maVals=[f.max() for f in fld]
            return (min(miVals),max(maVals))

        return self._getDataRangeGeneral(src,nm,getRangeFunc)

    def getDataRangePercentile(self,src,nm,low=1,high=99):
        import numpy as np
        from vtk.numpy_interface.dataset_adapter import WrapDataObject

        def getRangeFunc(fld):
            full=np.concatenate(fld)
            return np.percentile(a=full,q=(low,high))

        return self._getDataRangeGeneral(src,nm,getRangeFunc)

    def run(self):
        doPic=True
        doGeom=False
        doSources=False
        if self.opts.geomType:
             if PVVersion()<(3,9):
                  self.error("This paraview version does not support geometry writing")
             doGeom=True
             doPic=self.opts.pictureWithGeometry
             if len(self.opts.sources)==0:
                 self.opts.sources=[""] # add empty string as token
        if self.opts.sourcesList or self.opts.viewList:
             doPic=False
             doGeom=False
             doSources=True

        try:
            filterColors=eval(self.opts.filterColors)
        except TypeError:
            filterColors=self.opts.filterColors

        for f in filterColors:
            c=filterColors[f]
            if isinstance(c,(tuple,)):
                if not c[1]:
                    filterColors[f]=(c[0],self.opts.defaultField)
            elif isinstance(c,(dict,)):
                for k in c:
                    v=c[k]
                    if isinstance(v,(tuple,)):
                        if not v[1]:
                            c[k]=(v[0],self.opts.defaultField)
                    else:
                        if not v:
                            c[k]=self.opts.defaultField
            else:
                if not c:
                    filterColors[f]=self.opts.defaultField

        try:
            colorRanges=eval(self.opts.colorRanges)
        except TypeError:
            colorRanges=self.opts.colorRanges

        try:
            percentileRanges=eval(self.opts.percentileRanges)
        except TypeError:
            percentileRanges=self.opts.percentileRanges

        self.say("Paraview version",PVVersion(),"FoamVersion",foamVersion())
#        if PVVersion()>=(3,6):
#            self.warning("This is experimental because the API in Paraview>=3.6 has changed. But we'll try")

        case=path.abspath(self.parser.getArgs()[0])
        short=path.basename(case)

        stateString=""
        if self.opts.state==None:
            self.opts.state=path.join(case,"default.pvsm")
        else:
            stateString="_"+path.splitext(path.basename(self.opts.state))[0]

        if not path.exists(self.opts.state):
            self.error("The state file",self.opts.state,"does not exist")

        timeString=""

        if self.opts.casename:
            timeString+="_"+short
        timeString+="_%(nr)05d"
        if self.opts.timename:
            timeString+="_t=%(t)s"

        sol=SolutionDirectory(case,
                              paraviewLink=False,
                              archive=None)

        self.say("Opening state file",self.opts.state)
        sf=StateFile(self.opts.state)

        if self.opts.analyzeState:
            print_("\n\nReaders:\n   ","\n    ".join([p.type_()+" \t: "+p.getProperty("FileName") for p in sf.getProxy(".+Reader",regexp=True)]))
            print_("Source Proxies:")
            for i,name in sf.sourceIds():
                print_("  ",name," \t: ",sf[i].type_())
            return

        if self.opts.listProperties:
            print_("\n\nProperties for",self.opts.listProperties,":")
            srcs=[]
            for i,name in sf.sourceIds():
                srcs.append(name)
                if name==self.opts.listProperties:
                    for namee,el in sf[i].listProperties():
                        print_("  ",namee," \t: ",end=" ")
                        if len(el)==1:
                            print_("Single element:",el[0][1],end=" ")
                        elif len(el)>1:
                            print_(len(el),"Elements:",end=" ")
                            for j,v in el:
                                print_("%d:%s" % (j,v),end=" ")
                        else:
                            print_("No value",end=" ")
                        print_()
                    return
            self.error("Not found. Available:"," ".join(srcs))

        decoResult=None
        newParallelMode=None
        if self.opts.decomposeMode=="keep":
            pass
        elif self.opts.decomposeMode=="decomposed":
            decoResult=sf.setDecomposed(True)
            newParallelMode=True
        elif self.opts.decomposeMode=="reconstructed":
            decoResult=sf.setDecomposed(False)
            newParallelMode=False
        elif self.opts.decomposeMode=="auto":
            nrTimes=len(sol.getTimes())
            nrParTimes=len(sol.getParallelTimes())
            if nrTimes>nrParTimes:
                newParallelMode=False
                decoResult=sf.setDecomposed(False)
            else:
                newParallelMode=True
                decoResult=sf.setDecomposed(True)
        else:
            self.error("Setting decompose mode",self.opts.decomposeMode,"is not implemented")
        if decoResult:
            self.warning("Setting decomposed type to",self.opts.decomposeMode,":",decoResult)

        if newParallelMode:
            if self.opts.parallelTimes!=newParallelMode:
                self.warning("Resetting parallel mode",newParallelMode)
                self.opts.parallelTimes=newParallelMode

        if self.opts.consecutiveIndex:
            times=self.processTimestepOptions(sol)
            times=zip(times,range(0,len(times)))
        else:
            times=self.processTimestepOptionsIndex(sol)

        if len(times)<1:
            self.warning("Can't continue without time-steps")
            return

        dataFile=path.join(case,short+".OpenFOAM")
        createdDataFile=False
        if not path.exists(dataFile):
            self.say("Creating",dataFile)
            createdDataFile=True
            f=open(dataFile,"w")
            f.close()

        self.say("Setting data to",dataFile)
        sf.setCase(dataFile)

        values={}
        if self.opts.addPrepareCaseParameters:
            fName=path.join(case,PrepareCase.parameterOutFile)
            if path.exists(fName):
                self.say("Adding vaules from",fName)
                pf=ParsedParameterFile(fName,noHeader=True)
                values.update(pf.content)
            else:
                self.say("No file",fName)

        replString=self.opts.replacements.strip()
        if replString[0]=='{' and replString[-1]=='}':
            values.update(eval(self.opts.replacements))
        else:
            values.update(FoamStringParser(replString).data)
        values[self.opts.casenameKey]=short
        if self.opts.listReplacements:
            rKeys=sorted(values.keys())
            kLen=max([len(k) for k in rKeys])
            maxLen=100
            vLen=min(max([len(str(values[k])) for k in rKeys]),maxLen)
            kFormat=" %"+str(kLen)+"s | %"+str(vLen)+"s"
            print_()
            print_(kFormat % ("Key","Value"))
            print_("-"*(kLen+2)+"|"+"-"*(vLen+2))
            for k in rKeys:
                valStr=str(values[k])
                if len(valStr)>maxLen:
                    valStr=valStr[:maxLen]+" .. cut"
                print_(kFormat % (k,valStr))
            print_()

        sf.rewriteTexts(values)

        for setProp in self.opts.setProperties:
            parts=setProp.split("=",1)
            if len(parts)!=2:
                self.error("'=' missing in",setProp)
            value=parts[1]
            left=parts[0].split(":")
            if len(left)==2:
                src,prop=left
                index=None
            elif len(left)==3:
                src,prop,index=left
            else:
                self.error(setProp,"not a proper left side")

            print_("Setting on",src,"the property",prop,"index",index,"to",value)
            srcs=[]
            for i,name in sf.sourceIds():
                srcs.append(name)
                if name==src:
                    srcs=None
                    props=[]
                    for namee,el in sf[i].listProperties():
                        props.append(namee)
                        if namee==prop:
                            props=None
                            sf[i].setProperty(name=prop,index=index,value=value)
                            break
                    if props is not None:
                        self.error("No propery",prop,"in",src,
                                   "Available:"," ".join(props))
                    break
            if srcs is not None:
                self.error(src,"not found. Available:"," ".join(srcs))

        newState=sf.writeTemp()

        if self.opts.rewriteOnly:
            print_("Written new statefile to",newState)
            return

        self.say("Setting session manager with reader type",sf.readerType())
        sm=SM(requiredReader=sf.readerType())
        exporterType=None
        if doGeom:
             self.say("Getting geometry exporter",self.geomTypeTable[self.opts.geomType])
             exporters=sm.createModule("exporters")
             exporterType=getattr(exporters,self.geomTypeTable[self.opts.geomType])

        # make sure that the first snapshot is rendered correctly
        import paraview.simple as pvs

        pvs._DisableFirstRenderCameraReset()

        if not self.opts.progress:
            self.say("Toggling progress")
            sm.ToggleProgressPrinting()

        self.say("Loading state")
        sm.LoadState(newState)

        self.say("Getting Views")
        rViews=sm.GetRenderViews()
        views=pvs.GetViews()
        if (len(views)>1 and PVVersion()<(4,2)) or not self.opts.doLayouts:
            self.warning("More than 1 view in state-file. Generating multiple series")
            timeString="_View%(view)02d"+timeString
        timeString=self.opts.prefix+timeString+stateString

        self.say("Setting Offscreen rendering")
        offWarn=True

        viewOrder=[]
        for iView,view in enumerate(views):
            self.say("Processing view",iView,"of",len(views))
            viewOrder.append((iView,view.GetProperty("ViewPosition")))
            if self.opts.offscreenRender and PVVersion()<(5,6):
                view.UseOffscreenRenderingForScreenshots=True
                if offWarn:
                    self.warning("Trying offscreen rendering. If writing the file fails with a segmentation fault try --no-offscreen-rendering")
            elif offWarn:
                self.warning("No offscreen rendering. Camera perspective will probably be wrong")
            offWarn=False

        viewOrder.sort(key=lambda x:(x[1][1],x[1][0]))

        viewReorder={viewOrder[k][0]:k for k in range(len(viewOrder))}

        allSources=None
        alwaysSources=None

        self.say("Starting times",times[0][0],"(Index",times[0][1],")")
        for t,i in times:
            self.say("Nr",i,"time",t)
            print_("Snapshot ",i," for t=",t,end=" ")
            sys.stdout.flush()
            self.say()
            layouts=[]

            colorPrefix=""

            # from paraview.simple import UpdatePipeline
            # UpdatePipeline(time=float(t))

            if len(colorRanges)>0:
                for c in colorRanges:
                    rng=colorRanges[c]
                    self.say("Setting color",c,"to range",rng)
                    self.setColorTransferFunction(c,rng)

            if PVVersion()>=(4,2) and len(filterColors)>0:
                self.say("Switch colors")
                from paraview.simple import GetSources,GetDisplayProperties,GetColorTransferFunction,GetScalarBar,HideUnusedScalarBars,UpdatePipeline,ColorBy,SetActiveView,GetRepresentations
                sources=GetSources()
                changedSources=set()
                for j,view in enumerate(views):
                    viewNr=viewReorder[j]
                    for n in sources:
                        if n[0] in filterColors:
                            if view in rViews:
                                # print(dir(view),view.ListProperties())
                                # print(view.GetProperty("ViewSize"),view.GetProperty("ViewPosition"))
                                self.say("Found",n[0],"in view",viewNr,"to be switched")
                                # This does not work as expected.
    #                            dp=GetDisplayProperties(sources[n],view)
                                display=sm.GetRepresentation(sources[n],view)
                                if display==None:
                                    self.say("No representation for",n[0],"in this view")
                                    continue
                                if display.Visibility==0:
                                    self.say("Not switching",n[0],"because it is not visible in this view")
                                    # Invisible Sources don't need a color-change
                                    # Currently Visibily does not work as I expect it (is always 1)
                                    continue

                                if isinstance(filterColors[n[0]],(dict,)):
                                    try:
                                        if type(filterColors[n[0]][viewNr])==tuple:
                                            assoc,col=filterColors[n[0]][viewNr]
                                        else:
                                            assoc,col=display.ColorArrayName[0],filterColors[n[0]][viewNr]
                                    except KeyError:
                                        self.say("No color specified for",n[0],"in view",viewNr)
                                        continue
                                elif type(filterColors[n[0]])==tuple:
                                    assoc,col=filterColors[n[0]]
                                else:
                                    assoc,col=display.ColorArrayName[0],filterColors[n[0]]
                                if display.ColorArrayName==[assoc,col]:
                                    self.say("Color already set to",assoc,col,".Skipping")
                                    continue
                                ColorBy(display,[assoc,col])
                                self.say("Color",n,"in view",viewNr,"with",(assoc,col))
                                # display.ColorArrayName=[assoc,col]
                                changedSources.add(n[0])
                                color=GetColorTransferFunction(col)
                                # display.ColorArrayName=filterColors[n[0]]
                                # display.LookupTable=color
    #                            UpdatePipeline(proxy=sources[n])

                                if n[0] not in self.opts.noColorbar and (len(self.opts.colorbarView)==0 or viewNr in self.opts.colorbarView):
                                    self.say("Adding a colorbar")
                                    scalar=GetScalarBar(color,view)
                                    scalar.Visibility=1
                                    if scalar.Title=="Name":
                                        scalar.Title=col
                                    if scalar.ComponentTitle=="Component":
                                        scalar.ComponentTitle=""
                            elif sources[n].__class__.__name__=="Histogram" \
                                   and view.__class__.__name__=="BarChartView":
                                self.say(n,"is a Histogram")
                                # dp=GetDisplayProperties(sources[n],view)
                                assoc,oldCol=sources[n].SelectInputArray
                                col=filterColors[n[0]]
                                self.say("Setting color from",oldCol,"to",col)
                                sources[n].SelectInputArray=[assoc,col]
                            else:
                                # self.say(n,"is unsuppored Source:",sources[n],
                                #         "View:",view)
                                pass
                    HideUnusedScalarBars(view)

                if self.opts.colorPrefix:
                    for s in changedSources:
                        if isinstance(filterColors[s],(tuple,)):
                            colorPrefix+=s+"="+filterColors[s][1]+"_"
                        if isinstance(filterColors[s],(dict,)):
                            spc=filterColors[s]
                            colorPrefix+=s+"="+":".join(["%d:%s"%(v,spc[v]) for v in spc])+"_"
                        else:
                            colorPrefix+=s+"="+filterColors[s]+"_"

            for c in self.opts.rescaleToSource:
                found=False
                from paraview.simple import GetSources
                sources=GetSources()
                for n in sources:
                    if n[0]==c:
                        src=sources[n]
                        found=True
                        for view in views:
                            display=sm.GetRepresentation(sources[n],view)
                            if display==None:
                                continue
                            if display.Visibility==0:
                                continue
                            col=display.ColorArrayName[1]
                            src.UpdatePipeline(time=float(t))
                            if col in percentileRanges:
                                low,hig=percentileRanges[col]
                                if low is None:
                                    low=0
                                if hig is None:
                                    hig=100
                                else:
                                    hig=100-hig
                                rng=self.getDataRangePercentile(src,col,low=low,high=hig)
                            else:
                                rng=self.getDataRange(src,col)

                            if not rng is None:
                                self.say("Resetting color function",col,"to range",rng,"because of data set",c)
                                if col in colorRanges:
                                    low,hig=colorRanges[col]
                                    if low is not None:
                                        rng=low,rng[1]
                                    if hig is not None:
                                        rng=rng[0],hig
                                    self.say("Extremes overruled to",rng,"for resetting")
                                self.setColorTransferFunction(col,rng)
                            else:
                                self.warning("No field",col,"found on",c)
                        break

                if not found:
                    self.warning("Source",c,"not found")

            for j,view in enumerate(views):
                self.say("Preparing views")
                view.ViewTime=float(t)

            for j,view in enumerate(views):
                if len(views)>0:
                    print_("View %d" % j,end=" ")
                    sys.stdout.flush()
                    self.say()

                if doPic:
                     print_(self.opts.picType,end=" ")
                     sys.stdout.flush()

                     fn = (timeString % {'nr':i,'t':t,'view':j})+"."+self.opts.picType
                     if PVVersion()<(3,6):
                         self.say("Very old Paraview writing")
                         view.WriteImage(fn,
                                         self.picTypeTable[self.opts.picType],
                                         self.opts.magnification)
                     elif PVVersion()<(4,2):
                         self.say("Old Paraview writing")
                         from paraview.simple import SetActiveView,Render,WriteImage
                         self.say("Setting view")
                         SetActiveView(view)
                         self.say("Rendering")
                         Render()
                         self.say("Writing image",fn,"type",self.picTypeTable[self.opts.picType])
                         # This may produce a segmentation fault with offscreen rendering
                         WriteImage(fn,
                                    view,
     #                               Writer=self.picTypeTable[self.opts.picType],
                                    Magnification=self.opts.magnification)
                         self.say("Finished writing")
                     elif PVVersion()<(5,4):
                         doRender=True
                         usedView=view
                         self.say("New Paraview writing")
                         from paraview.simple import SetActiveView,SaveScreenshot,GetLayout,GetSources

                         layout=GetLayout(view)
                         if self.opts.doLayouts:
                             usedView=None
                             if layout in layouts:
                                 doRender=False
                             else:
                                 layouts.append(layout)
                         else:
                             layout=None
                         if doRender:
                             self.say("Writing image",colorPrefix+fn,"type",self.picTypeTable[self.opts.picType])
                             # This may produce a segmentation fault with offscreen rendering
                             SaveScreenshot(colorPrefix+fn,
                                            view=usedView,
                                            layout=layout,
                                            quality=100-self.opts.quality,
                                            magnification=self.opts.magnification)
                         else:
                             self.say("Skipping image",colorPrefix+fn)
                         self.say("Finished writing")
                     else:
                         doRender=True
                         usedView=view
                         self.say("Paraview >5.4 writing")
                         from paraview.simple import SetActiveView,SaveScreenshot,GetLayout,GetSources

                         layout=GetLayout(view)
                         if self.opts.doLayouts:
                             usedView=None
                             if layout in layouts:
                                 doRender=False
                             else:
                                 layouts.append(layout)
                             exts=[0]*4
                             layout.GetLayoutExtent(exts)
                             size = [exts[1]-exts[0]+1, exts[3]-exts[2]+1]
                         else:
                             layout=None
                             size=usedView.ViewSize

                         if doRender:
                             self.say("Writing image",colorPrefix+fn,"type",self.picTypeTable[self.opts.picType])
                             # This may produce a segmentation fault with offscreen rendering
                             if self.opts.xRes:
                                 if self.opts.yRes:
                                     size=self.opts.xRes,self.opts.yRes
                                 else:
                                     size=self.opts.xRes,int(self.opts.xRes*size[1]/float(size[0]))
                             elif self.opts.yRes:
                                 size=int(self.opts.yRes*size[0]/float(size[1])),self.opts.yRes
                             else:
                                 size=size[0]*self.opts.magnification,size[1]*self.opts.magnification
                             SaveScreenshot(colorPrefix+fn,
                                            viewOrLayout=usedView or layout,
                                            SeparatorWidth=self.opts.separatorWidth,
                                            ImageResolution=size,
                                            TransparentBackground=self.opts.transparentBackground,
                                            ImageQuality=100-self.opts.quality)
                         else:
                             self.say("Skipping image",colorPrefix+fn)
                         self.say("Finished writing")
                if doGeom:
                     from paraview.simple import Show,Hide,GetSources

                     print_(self.opts.geomType,end=" ")
                     sys.stdout.flush()
                     for select in self.opts.sources:
                         fn = (timeString % {'nr':i,'t':t,'view':j})
                         if select!="":
                             print_("*"+select+"*",end=" ")
                             sys.stdout.flush()
                             fn+="_"+select
                             sources=GetSources()
                             for n,s in sources.iteritems():
                                 if n[0].find(select)>=0:
                                     Show(s,view)
                                 else:
                                     Hide(s,view)
                         fn += "."+self.opts.geomType
                         self.say("Creating exporter for file",fn)
                         ex=exporterType(FileName=fn)
                         ex.SetView(view)
                         ex.Write()
                if doSources:
                    if self.opts.viewList:
                        print_("View Nr %s: Position %s Size: %s" % (viewReorder[j],view.GetProperty("ViewPosition"),view.GetProperty("ViewSize")))
                    if self.opts.sourcesList:
                        from paraview.simple import GetSources
                        srcNames=[]
                        sources=GetSources()
                        for n in sources:
                            srcNames.append(n[0])
                        if allSources==None:
                             allSources=set(srcNames)
                             alwaysSources=set(srcNames)
                        else:
                             allSources|=set(srcNames)
                             alwaysSources&=set(srcNames)
            print_()

        if doSources:
             print_()
             print_("List of found sources (* means that it is present in all timesteps)")
             for n in allSources:
                  if n in alwaysSources:
                       flag="*"
                  else:
                       flag=" "
                  print_("  %s  %s" % (flag,n))

        if createdDataFile:
            self.warning("Removing pseudo-data-file",dataFile)
            unlink(dataFile)

        del sm
