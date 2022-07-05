"""
Old implementation using Tkinter. This is no longer supported.
If possible use the Qt-Variant
"""

import sys

from PyFoam.RunDictionary.ParsedBlockMeshDict import ParsedBlockMeshDict
from PyFoam.Applications.PyFoamApplication import PyFoamApplication
from PyFoam.Error import error,warning

from PyFoam.ThirdParty.six import print_

def doImports():
    try:
        global tkinter
        from PyFoam.ThirdParty.six.moves import tkinter
        global vtk
        try:
            import vtk
            print_("Using system-VTK")
        except ImportError:
            print_("Trying VTK implementation from Paraview")
            from paraview import vtk
        global vtkTkRenderWindowInteractor
        from vtk.tk.vtkTkRenderWindowInteractor import vtkTkRenderWindowInteractor
    except ImportError:
        e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
        error("Error while importing modules:",e)

class DisplayBlockMesh(PyFoamApplication):
    def __init__(self):
        description="""\
Reads the contents of a blockMeshDict-file and displays the vertices
as spheres (with numbers). The blocks are sketched by lines. One block
can be seceted with a slider. It will be displayed as a green cube
with the local directions x1,x2 and x3. Also a patch that is selected
by a slider will be sketched by blue squares.  This implementation
uses Tkinter and is no longer activly developed.  Use the QT-version.
        """
        PyFoamApplication.__init__(self,
                                   description=description,
                                   usage="%prog [options] <blockMeshDict>",
                                   interspersed=True,
                                   nr=1)

    def run(self):
        doImports()

        self.renWin = vtk.vtkRenderWindow()
        self.ren = vtk.vtkRenderer()
        self.renWin.AddRenderer(self.ren)
        self.renWin.SetSize(600, 600)
        self.ren.SetBackground(0.7, 0.7, 0.7)
        self.ren.ResetCamera()
        self.cam = self.ren.GetActiveCamera()

        self.axes = vtk.vtkCubeAxesActor2D()
        self.axes.SetCamera(self.ren.GetActiveCamera())

        self.undefinedActor=vtk.vtkTextActor()
        self.undefinedActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
        self.undefinedActor.GetPositionCoordinate().SetValue(0.05,0.2)
        self.undefinedActor.GetTextProperty().SetColor(1.,0.,0.)
        self.undefinedActor.SetInput("")

        try:
            self.readFile()
        except Exception:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            warning("While reading",self.parser.getArgs()[0],"this happened:",e)
            raise e

        self.ren.ResetCamera()

        self.root = tkinter.Tk()
        self.root.withdraw()

        # Create the toplevel window
        self.top = tkinter.Toplevel(self.root)
        self.top.title("blockMesh-Viewer")
        self.top.protocol("WM_DELETE_WINDOW", self.quit)

        # Create some frames
        self.f1 = tkinter.Frame(self.top)
        self.f2 = tkinter.Frame(self.top)

        self.f1.pack(side="top", anchor="n", expand=1, fill="both")
        self.f2.pack(side="bottom", anchor="s", expand="f", fill="x")

        # Create the Tk render widget, and bind the events
        self.rw = vtkTkRenderWindowInteractor(self.f1, width=400, height=400, rw=self.renWin)
        self.rw.pack(expand="t", fill="both")

        self.blockHigh=tkinter.IntVar()
        self.blockHigh.set(-1)

        self.oldBlock=-1
        self.blockActor=None
        self.blockTextActor=None

        self.patchHigh=tkinter.IntVar()
        self.patchHigh.set(-1)

        self.oldPatch=-1
        self.patchActor=None
        self.patchTextActor=vtk.vtkTextActor()
        self.patchTextActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
        self.patchTextActor.GetPositionCoordinate().SetValue(0.05,0.1)
        self.patchTextActor.GetTextProperty().SetColor(0.,0.,0.)
        self.patchTextActor.SetInput("Patch: <none>")

        self.scroll=tkinter.Scale(self.f2,orient='horizontal',
                                  from_=-1,to=len(self.blocks)-1,resolution=1,tickinterval=1,
                                  label="Block (-1 is none)",
                                  variable=self.blockHigh,command=self.colorBlock)

        self.scroll.pack(side="top", expand="t", fill="x")

        self.scroll2=tkinter.Scale(self.f2,orient='horizontal',
                                   from_=-1,to=len(list(self.patches.keys()))-1,resolution=1,tickinterval=1,
                                   label="Patch (-1 is none)",
                                   variable=self.patchHigh,command=self.colorPatch)

        self.scroll2.pack(side="top", expand="t", fill="x")

        self.f3 = tkinter.Frame(self.f2)
        self.f3.pack(side="bottom", anchor="s", expand="f", fill="x")

        self.b1 = tkinter.Button(self.f3, text="Quit", command=self.quit)
        self.b1.pack(side="left", expand="t", fill="x")
        self.b2 = tkinter.Button(self.f3, text="Reread blockMeshDict", command=self.reread)
        self.b2.pack(side="left", expand="t", fill="x")

        self.root.update()

        self.iren = self.renWin.GetInteractor()
        self.istyle = vtk.vtkInteractorStyleSwitch()

        self.iren.SetInteractorStyle(self.istyle)
        self.istyle.SetCurrentStyleToTrackballCamera()

        self.addProps()

        self.iren.Initialize()
        self.renWin.Render()
        self.iren.Start()

        self.root.mainloop()

    def readFile(self):
        self.blockMesh=ParsedBlockMeshDict(self.parser.getArgs()[0])

        self.vertices=self.blockMesh.vertices()
        self.vActors=[None]*len(self.vertices)

        self.blocks=self.blockMesh.blocks()
        self.patches=self.blockMesh.patches()

        self.vRadius=self.blockMesh.typicalLength()/50

        for i in range(len(self.vertices)):
            self.addVertex(i)

        self.setAxes()

        self.undefined=[]

        for i in range(len(self.blocks)):
            self.addBlock(i)

        for a in self.blockMesh.arcs():
            self.makeArc(a)

        if len(self.undefined)>0:
            self.undefinedActor.SetInput("Undefined vertices: "+str(self.undefined))
        else:
            self.undefinedActor.SetInput("")

    def addUndefined(self,i):
        if not i in self.undefined:
            self.undefined.append(i)

    def addProps(self):
        self.ren.AddViewProp(self.axes)
        self.ren.AddActor2D(self.patchTextActor)
        self.ren.AddActor2D(self.undefinedActor)

    def addPoint(self,coord,factor=1):
        sphere=vtk.vtkSphereSource()
        sphere.SetRadius(self.vRadius*factor)
        sphere.SetCenter(coord)
        mapper=vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        self.ren.AddActor(actor)

        return actor

    def addVertex(self,index):
        coord=self.vertices[index]
        self.vActors[index]=self.addPoint(coord)
        text=vtk.vtkVectorText()
        text.SetText(str(index))
        tMapper=vtk.vtkPolyDataMapper()
        tMapper.SetInput(text.GetOutput())
        tActor = vtk.vtkFollower()
        tActor.SetMapper(tMapper)
        tActor.SetScale(2*self.vRadius,2*self.vRadius,2*self.vRadius)
        tActor.AddPosition(coord[0]+self.vRadius,coord[1]+self.vRadius,coord[2]+self.vRadius)
        tActor.SetCamera(self.cam)
        tActor.GetProperty().SetColor(1.0,0.,0.)
        self.ren.AddActor(tActor)

    def addLine(self,index1,index2):
        try:
            c1=self.vertices[index1]
            c2=self.vertices[index2]
        except:
            if index1>=len(self.vertices):
                self.addUndefined(index1)
            if index2>=len(self.vertices):
                self.addUndefined(index2)
            return None
        line=vtk.vtkLineSource()
        line.SetPoint1(c1)
        line.SetPoint2(c2)
        mapper=vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(line.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        self.ren.AddActor(actor)
        return actor

    def makeDirection(self,index1,index2,label):
        try:
            c1=self.vertices[index1]
            c2=self.vertices[index2]
        except:
            return None,None
        line=vtk.vtkLineSource()
        line.SetPoint1(c1)
        line.SetPoint2(c2)
        tube=vtk.vtkTubeFilter()
        tube.SetRadius(self.vRadius*0.5)
        tube.SetNumberOfSides(10)
        tube.SetInput(line.GetOutput())
        text=vtk.vtkVectorText()
        text.SetText(label)
        tMapper=vtk.vtkPolyDataMapper()
        tMapper.SetInput(text.GetOutput())
        tActor = vtk.vtkFollower()
        tActor.SetMapper(tMapper)
        tActor.SetScale(self.vRadius,self.vRadius,self.vRadius)
        tActor.AddPosition((c1[0]+c2[0])/2+self.vRadius,(c1[1]+c2[1])/2+self.vRadius,(c1[2]+c2[2])/2+self.vRadius)
        tActor.SetCamera(self.cam)
        tActor.GetProperty().SetColor(0.0,0.,0.)
        return tube.GetOutput(),tActor

    def makeSpline(self,lst):
        points = vtk.vtkPoints()
        for i in range(len(lst)):
            v=lst[i]
            points.InsertPoint(i,v[0],v[1],v[2])
        spline=vtk.vtkParametricSpline()
        spline.SetPoints(points)
        spline.ClosedOff()
        splineSource=vtk.vtkParametricFunctionSource()
        splineSource.SetParametricFunction(spline)
        mapper=vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(splineSource.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        self.ren.AddActor(actor)

    def makeArc(self,data):
        try:
            self.makeSpline([self.vertices[data[0]],data[1],self.vertices[data[2]]])
        except:
            if data[0]>=len(self.vertices):
                self.addUndefined(data[0])
            if data[2]>=len(self.vertices):
                self.addUndefined(data[2])

        self.addPoint(data[1],factor=0.5)

    def makeFace(self,lst):
        points = vtk.vtkPoints()
        side = vtk.vtkCellArray()
        side.InsertNextCell(len(lst))
        for i in range(len(lst)):
            try:
                v=self.vertices[lst[i]]
            except:
                self.addUndefined(lst[i])
                return None
            points.InsertPoint(i,v[0],v[1],v[2])
            side.InsertCellPoint(i)
        result=vtk.vtkPolyData()
        result.SetPoints(points)
        result.SetPolys(side)

        return result

    def addBlock(self,index):
        b=self.blocks[index]

        self.addLine(b[ 0],b[ 1])
        self.addLine(b[ 3],b[ 2])
        self.addLine(b[ 7],b[ 6])
        self.addLine(b[ 4],b[ 5])
        self.addLine(b[ 0],b[ 3])
        self.addLine(b[ 1],b[ 2])
        self.addLine(b[ 5],b[ 6])
        self.addLine(b[ 4],b[ 7])
        self.addLine(b[ 0],b[ 4])
        self.addLine(b[ 1],b[ 5])
        self.addLine(b[ 2],b[ 6])
        self.addLine(b[ 3],b[ 7])

    def setAxes(self):
        append=vtk.vtkAppendPolyData()
        for a in self.vActors:
            if a!=None:
                append.AddInput(a.GetMapper().GetInput())
        self.axes.SetInput(append.GetOutput())


    # Define a quit method that exits cleanly.
    def quit(self):
        self.root.quit()

    def reread(self):
        self.ren.RemoveAllViewProps()
        self.patchActor=None
        self.blockActor=None
        self.blockTextActor=None
        self.addProps()
        self.readFile()

        tmpBlock=int(self.blockHigh.get())
        if not tmpBlock<len(self.blocks):
            tmpBlock=len(self.blocks)-1
        self.scroll.config(to=len(self.blocks)-1)
        self.blockHigh.set(tmpBlock)
        self.colorBlock(tmpBlock)

        tmpPatch=int(self.patchHigh.get())
        if not tmpPatch<len(list(self.patches.keys())):
            tmpPatch=len(list(self.patches.keys()))-1
        self.scroll2.config(to=len(list(self.patches.keys()))-1)
        self.patchHigh.set(tmpPatch)
        self.colorPatch(tmpPatch)

        self.renWin.Render()

    def colorBlock(self,value):
        newBlock=int(value)
        if self.oldBlock>=0 and self.blockActor!=None:
            self.ren.RemoveActor(self.blockActor)
            for ta in self.blockTextActor:
                self.ren.RemoveActor(ta)
            self.blockActor=None
            self.blockTextActor=None
        if newBlock>=0:
            append=vtk.vtkAppendPolyData()
            append2=vtk.vtkAppendPolyData()
            b=self.blocks[newBlock]
            append.AddInput(self.makeFace([b[0],b[1],b[2],b[3]]))
            append.AddInput(self.makeFace([b[4],b[5],b[6],b[7]]))
            append.AddInput(self.makeFace([b[0],b[1],b[5],b[4]]))
            append.AddInput(self.makeFace([b[3],b[2],b[6],b[7]]))
            append.AddInput(self.makeFace([b[0],b[3],b[7],b[4]]))
            append.AddInput(self.makeFace([b[1],b[2],b[6],b[5]]))
            d,t1=self.makeDirection(b[0],b[1],"x1")
            append.AddInput(d)
            self.ren.AddActor(t1)
            d,t2=self.makeDirection(b[0],b[3],"x2")
            append.AddInput(d)
            self.ren.AddActor(t2)
            d,t3=self.makeDirection(b[0],b[4],"x3")
            append.AddInput(d)
            self.ren.AddActor(t3)
            self.blockTextActor=(t1,t2,t3)
            mapper=vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(append.GetOutputPort())
            self.blockActor = vtk.vtkActor()
            self.blockActor.SetMapper(mapper)
            self.blockActor.GetProperty().SetColor(0.,1.,0.)
            self.blockActor.GetProperty().SetOpacity(0.3)
            self.ren.AddActor(self.blockActor)

        self.oldBlock=newBlock
        self.renWin.Render()

    def colorPatch(self,value):
        newPatch=int(value)
        if self.oldPatch>=0 and self.patchActor!=None:
            self.ren.RemoveActor(self.patchActor)
            self.patchActor=None
            self.patchTextActor.SetInput("Patch: <none>")
        if newPatch>=0:
            name=list(self.patches.keys())[newPatch]
            subs=self.patches[name]
            append=vtk.vtkAppendPolyData()
            for s in subs:
                append.AddInput(self.makeFace(s))
            mapper=vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(append.GetOutputPort())
            self.patchActor = vtk.vtkActor()
            self.patchActor.SetMapper(mapper)
            self.patchActor.GetProperty().SetColor(0.,0.,1.)
            self.patchActor.GetProperty().SetOpacity(0.3)
            self.ren.AddActor(self.patchActor)
            self.patchTextActor.SetInput("Patch: "+name)

        self.oldPatch=newPatch
        self.renWin.Render()

# Should work with Python3 and Python2
