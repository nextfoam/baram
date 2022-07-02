#  ICE Revision: $Id$
"""
Application class that implements pyFoamSurfacePlot.py
"""

import sys,string
from os import path
from optparse import OptionGroup
from copy import copy
from math import sqrt

from .PyFoamApplication import PyFoamApplication
from PyFoam.RunDictionary.SurfaceDirectory import SurfaceDirectory

from PyFoam.Error import error

from .PlotHelpers import cleanFilename

from PyFoam.ThirdParty.six import print_
from PyFoam.ThirdParty.six.moves import input

class SurfacePlot(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Searches for sampled surface in the VTK-format in a directory and
makes pictures from them
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <casedir>",
                                   nr=1,
                                   changeVersion=False,
                                   interspersed=True,
                                   **kwargs)

    def addOptions(self):
        data=OptionGroup(self.parser,
                          "Data",
                          "Select the data to plot")
        self.parser.add_option_group(data)

        data.add_option("--surface",
                        action="append",
                        default=None,
                        dest="surface",
                        help="The sampled surface for which the data is plotted (can be used more than once)")
        data.add_option("--field",
                        action="append",
                        default=None,
                        dest="field",
                        help="The fields that are plotted (can be used more than once). If none are specified all found fields are used")
        data.add_option("--directory-name",
                        action="store",
                        default="surfaces",
                        dest="dirName",
                        help="Alternate name for the directory with the samples (Default: %default)")

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

        output=OptionGroup(self.parser,
                           "Appearance",
                           "How it should be plotted")
        self.parser.add_option_group(output)

        output.add_option("--unscaled",
                          action="store_false",
                          dest="scaled",
                          default=True,
                          help="Don't scale a value to the same range for all plots")
        output.add_option("--interpolate-to-point",
                          action="store_true",
                          dest="toPoint",
                          default=False,
                          help="Plot data interpolated to point values (although the real truth lies in the cells)")
        output.add_option("--scale-all",
                          action="store_true",
                          dest="scaleAll",
                          default=False,
                          help="Use the same scale for all fields (else use one scale for each field)")
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
        output.add_option("--clean-filename",
                          action="store_true",
                          dest="cleanFilename",
                          default=False,
                          help="Clean filenames so that they can be used in HTML or Latex-documents")

        colorMaps=["blueToRed","redToBlue","blackToWhite","redToWhite"]
        #        colorMaps.append("experimental")

        output.add_option("--color-map",
                          type="choice",
                          dest="colorMap",
                          default="blueToRed",
                          choices=colorMaps,
                          help="Sets the used colormap to one of "+", ".join(colorMaps)+" with the default: %default")

        data.add_option("--info",
                        action="store_true",
                        dest="info",
                        default=False,
                        help="Print info about the sampled data and exit")

        camera=OptionGroup(self.parser,
                           "Camera",
                           "How to look at things")
        self.parser.add_option_group(camera)
        camera.add_option("--no-auto-camera",
                          action="store_false",
                          dest="autoCamera",
                          default=True,
                          help="The position of the camera should not be determined automagically")
        camera.add_option("--dolly-factor",
                          action="store",
                          dest="dollyFactor",
                          type="float",
                          default=1,
                          help="The dolly-factor used to focus the camera: %default")
        camera.add_option("--width-of-bitmap",
                          action="store",
                          type="int",
                          dest="width",
                          default=720,
                          help="The width that the render-window should have. Default: %default")
        camera.add_option("--height-of-bitmap",
                          action="store",
                          dest="height",
                          type="int",
                          default=None,
                          help="The height that the render-window should have. If unspecified it is determined from the size of the data")
        camera.add_option("--focal-point-offset",
                          action="store",
                          dest="focalOffset",
                          default="0,0,0",
                          help="Offset of the focal point from the center of the data. Only used in manual-camera mode. Default: %default")
        camera.add_option("--camera-offset",
                          action="store",
                          dest="cameraOffset",
                          default="0,0,1",
                          help="Offset of the position of the camera from the center of the data. Only used in manual-camera mode. Default: %default")
        camera.add_option("--up-direction",
                          action="store",
                          dest="upDirection",
                          default="0,1,0",
                          help="Which direction is up. Only used in manual-camera mode. Default: %default")
        camera.add_option("--report-camera",
                          action="store_true",
                          dest="reportCamera",
                          default=False,
                          help="Report the used settings for the camera")

        behave=OptionGroup(self.parser,
                           "Behaviour",
                           "How the program affects its environment")
        self.parser.add_option_group(behave)
        behave.add_option("--offscreen",
                          action="store_true",
                          dest="offscreen",
                          default=False,
                          help="Try to render the image offscreen (without a window)")
        behave.add_option("--silent",
                          action="store_true",
                          dest="silent",
                          default=False,
                          help="Don't write progress to the terminal")
        behave.add_option("--wait",
                          action="store_true",
                          dest="wait",
                          default=False,
                          help="Keep window open until a key is pressed")

    def setupPipeline(self,fName):
        if self.opts.offscreen:
            grap=vtk.vtkGraphicsFactory()
            grap.SetOffScreenOnlyMode(1)
            grap.SetUseMesaClasses(1)
            img=vtk.vtkImagingFactory()
            img.SetUseMesaClasses(1)

        self.reader = vtk.vtkDataSetReader()
        self.reader.SetFileName(fName)
        self.output = self.reader.GetOutput()
        if self.opts.toPoint:
            self.toPoint = vtk.vtkCellDataToPointData()
        self.surfMapper = vtk.vtkDataSetMapper()
        self.surfMapper.SetColorModeToMapScalars()
        self.lut = vtk.vtkLookupTable()
        if self.opts.colorMap=="blueToRed":
            self.lut.SetHueRange(0.667,0)
        elif self.opts.colorMap=="redToBlue":
            self.lut.SetHueRange(0,0.667)
        elif self.opts.colorMap=="blackToWhite":
            self.lut.SetHueRange(1,1)
            self.lut.SetValueRange(0,1)
            self.lut.SetSaturationRange(0,0)
        elif self.opts.colorMap=="redToWhite":
            self.lut.SetHueRange(0,0.2)
            self.lut.SetValueRange(1,1)
            self.lut.SetSaturationRange(1,0.2)
        else:
            self.warning("Unknown colormap",self.opts.colorMap)

        self.surfMapper.SetLookupTable(self.lut)
        self.surfActor = vtk.vtkActor()
        self.surfActor.SetMapper(self.surfMapper)
        self.textActor = vtk.vtkTextActor()
        self.textActor.SetDisplayPosition(90, 50)
        self.textActor.SetTextScaleModeToViewport()
        self.textActor.SetWidth(0.75)

        self.barActor = vtk.vtkScalarBarActor()
        self.barActor.SetLookupTable(self.lut)
        self.barActor.SetDisplayPosition(90, 300)
        self.barActor.SetOrientationToHorizontal()
        self.barActor.SetHeight(0.15)
        self.barActor.SetWidth(0.75)

#        self.axes=vtk.vtkCubeAxesActor()
#        self.axes.SetFlyModeToClosestTriad()
        #        self.axes.SetCornerOffset(0.1)
        #        self.axes.SetXLabelFormat("%6.1f")
        #        self.axes.SetYLabelFormat("%6.1f")
        #        self.axes.SetZLabelFormat("%6.1f")
        # Create graphics stuff
        self.ren = vtk.vtkRenderer()
        self.renWin = vtk.vtkRenderWindow()
        if self.opts.offscreen:
            self.renWin.SetOffScreenRendering(1)
        self.renWin.AddRenderer(self.ren)

        self.ren.AddActor(self.surfActor)
        self.ren.AddActor2D(self.textActor)
        self.ren.AddActor2D(self.barActor)
#        self.ren.AddViewProp(self.axes)

#        self.axes.SetCamera(self.ren.GetActiveCamera())

        self.ren.SetBackground(0.7, 0.7, 0.7)

        self.hasPipeline=True

    def setFilename(self,fName):
        if not self.hasPipeline:
            self.setupPipeline(fName)
        else:
            self.reader.SetFileName(fName)

        self.reader.Update()
        self.output = self.reader.GetOutput()
        if self.opts.toPoint:
            self.toPoint.SetInput(self.output)
            self.surfMapper.SetInput(self.toPoint.GetOutput())
        else:
            self.surfMapper.SetInput(self.output)
        self.cData=self.output.GetCellData()
        self.cData.SetScalars(self.cData.GetArray(0))
        self.surfMapper.SetScalarRange(self.reader.GetOutput().GetScalarRange())

    def setRange(self,rng):
        self.surfMapper.SetScalarRange(rng)

    def setTitles(self,title,bar):
        self.textActor.SetInput(title)
        self.barActor.SetTitle(bar)

    def getCurrentRange(self):
        return self.reader.GetOutput().GetScalarRange()

    def getVector(self,opt):
        return list(map(float,opt.split(',')))

    def writePicture(self,fName):
        self.ren.ResetCamera()

        xMin,xMax,yMin,yMax,zMin,zMax=self.output.GetBounds()
#        self.axes.SetBounds(self.output.GetBounds())
        boundRange=[(xMax-xMin,0),
                    (yMax-yMin,1),
                    (zMax-zMin,2)]
        boundRange.sort(key=lambda a:a[0],reverse=True)
        focalPoint=[0.5*(xMax+xMin),0.5*(yMax+yMin),0.5*(zMax+zMin)]
        position=copy(focalPoint)
        if self.opts.autoCamera:
            ratio=max(0.2,boundRange[1][0]/max(boundRange[0][0],1e-10))
            self.opts.height=int(self.opts.width*ratio)+70
            camOffset=[0,0,0]
            camOffset[boundRange[2][1]]=boundRange[1][0]*3
            up=[0,0,0]
            up[boundRange[1][1]]=1.
        else:
            if self.opts.height==None:
                self.opts.height=int(self.opts.width/sqrt(2))
            offset=self.getVector(self.opts.focalOffset)
            for i in range(3):
                focalPoint[i]+=offset[i]
            camOffset=self.getVector(self.opts.cameraOffset)
            up=self.getVector(self.opts.upDirection)

        for i in range(3):
            position[i]+=camOffset[i]

        if self.opts.reportCamera:
            print_("Picture size:",self.opts.width,self.opts.height)
            print_("Data bounds:",xMin,xMax,yMin,yMax,zMin,zMax)
            print_("Focal point:",focalPoint)
            print_("Up-direction:",up)
            print_("Camera position:",position)

        self.renWin.SetSize(self.opts.width,self.opts.height)
        self.barActor.SetDisplayPosition(int(self.opts.width*0.124), 20)
        self.textActor.SetDisplayPosition(int(self.opts.width*0.124),self.opts.height-30)
        self.ren.GetActiveCamera().SetFocalPoint(focalPoint)
        self.ren.GetActiveCamera().SetViewUp(up)
        self.ren.GetActiveCamera().SetPosition(position)
        self.ren.GetActiveCamera().Dolly(self.opts.dollyFactor)
        self.ren.ResetCameraClippingRange()

        self.renWin.Render()

        self.renderLarge = vtk.vtkRenderLargeImage()
        self.renderLarge.SetInput(self.ren)
        self.renderLarge.SetMagnification(1)

        self.writer = vtk.vtkPNGWriter()
        self.writer.SetInputConnection(self.renderLarge.GetOutputPort())

        self.writer.SetFileName(fName)
        self.writer.Write()

        if self.opts.wait:
            input("waiting for key")

    def run(self):
        global vtk
        import vtk

        caseName=path.basename(path.abspath(self.parser.getArgs()[0]))
        samples=SurfaceDirectory(self.parser.getArgs()[0],dirName=self.opts.dirName)
        self.hasPipeline=False

        if self.opts.info:
            print_("Times    : ",samples.times)
            print_("Surfaces : ",samples.surfaces())
            print_("Values   : ",list(samples.values()))
            sys.exit(0)

        surfaces=samples.surfaces()
        times=samples.times
        values=list(samples.values())

        if self.opts.surface==None:
            #            error("At least one line has to be specified. Found were",samples.lines())
            self.opts.surface=surfaces
        else:
            for l in self.opts.surface:
                if l not in surfaces:
                    error("The line",l,"does not exist in",lines)

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
                    self.warning("Time",t,"not found in the sample-times. Use option --fuzzy")

        if not self.opts.silent:
            print_("Getting data about plots")
        plots=[]

        if self.opts.time==None:
            self.opts.time=samples.times
        elif len(self.opts.time)==0:
            self.error("No times specified. Exiting")
        if self.opts.field==None:
            self.opts.field=list(samples.values())
        for s in self.opts.surface:
            for t in self.opts.time:
                for f in self.opts.field:
                    plt=samples.getData(surface=[s],
                                        value=[f],
                                        time=[t])
                    if plt:
                        plots+=plt

        vRanges=None
        if self.opts.scaled:
            if not self.opts.silent:
                print_("Getting ranges")
            if self.opts.scaleAll:
                vRange=None
            else:
                vRanges={}

            for p in plots:
                f,tm,surf,nm=p
                self.setFilename(f)

                mi,ma=self.getCurrentRange()
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

        for p in plots:
            f,time,surf,nm=p

            name=""
            if self.opts.namePrefix:
                name+=self.opts.namePrefix+"_"
            name+=self.opts.dirName
            tIndex=times.index(time)

            name+="_"+surf

            name+="_%s_%04d"   % (nm,tIndex)
            title="%s : %s - %s   t=%f" % (caseName,self.opts.dirName,surf,float(time))

            name+=".png"
            if self.opts.cleanFilename:
                name=cleanFilename(name)

            if self.opts.pictureDest:
                name=path.join(self.opts.pictureDest,name)

            self.setFilename(f)
            if self.opts.scaleAll:
                if vRange:
                    self.setRange(vRange)
            else:
                if vRanges:
                    if nm in vRanges:
                        self.setRange(vRanges[nm])

            self.setTitles(title,nm)

            if not self.opts.silent:
                print_("Writing picture",name)

            self.writePicture(name)

# Should work with Python3 and Python2
