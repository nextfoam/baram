#  ICE Revision: $Id$ 
""" Simple sources

Builds and displays simple sources. Grants easy access to the actual source
and the representation objects"""

from paraview import servermanager

from PyFoam.Paraview import proxyManager as pm
from PyFoam.Paraview import renderView as rv
from PyFoam.Paraview import characteristicLength as lc
from PyFoam.Paraview import getCenter as gc
from PyFoam.Paraview import transformsModule as tm

from SourceBase import SourceBase

import math

class SimpleSource(SourceBase):
    """Base class for the simple sources

    The member src is the actual source object.
    The member repr is the representation object"""

    def __init__(self,name,src):
        """:param name: The name under which the thing should be displayed
        :param src: the actual source proxy"""
        SourceBase.__init__(self,src)
        self.name = name
        pm.RegisterProxy("sources",self.name,self.src)
        self.repr=servermanager.CreateRepresentation(self.src,rv())
        pm.RegisterProxy("representations",self.name+"_repr",self.repr)

    def unregister(self):
        """Unregister the Proxies, but keept the objects"""
        pm.UnRegisterProxy("sources",self.name,self.src)
        pm.UnRegisterProxy("representations",self.name+"_repr",self.repr)
        
    def __del__(self):
        """Does not yet work properly"""
        self.unregister()
        del self.src
        del self.repr

class Sphere(SimpleSource):
    """Displays a sphere"""

    def __init__(self,name,center,relRadius=0.01,absRadius=None):
        """:param name: name under which the sphere should be displayed
        :param center: the center of the sphere
        :param relRadius: radius relative to the characteristic length
        :param absRadius: absolute radius. Overrides relRadius if set"""

        try:
            sphr=servermanager.sources.SphereSource()
        except AttributeError:
            sphr=servermanager.sources.Sphere()

        sphr.Center=list(center)
        if absRadius:
            sphr.Radius=absRadius
        else:
            sphr.Radius=lc()*relRadius

        SimpleSource.__init__(self,name,sphr)
        
class Point(SimpleSource):
    """Displays a point"""

    def __init__(self,name,center):
        """:param name: name under which the point should be displayed
        :param center: the center of the point"""

        pt=servermanager.sources.PointSource()
        pt.Center = list(center)
        SimpleSource.__init__(self,name,pt)
        
class Line(SimpleSource):
    """Displays a line"""

    def __init__(self,name,pt1,pt2):
        """:param name: name under which the line should be displayed
        :param pt1: the start of the line
        :param pt2: the end of the line"""

        try:
            ln=servermanager.sources.LineSource()
        except AttributeError:
            ln=servermanager.sources.Line()

        ln.Point1 = list(pt1)
        ln.Point2 = list(pt2)
        SimpleSource.__init__(self,name,ln)
        
class Plane(SimpleSource):
    """Displays a plane"""

    def __init__(self,name,origin,pt1,pt2):
        """:param name: name under which the plane should be displayed
        :param origin: the origin of the plane
        :param pt1: one point the plane spans to
        :param pt2: the other point the plane spans to"""

        try:
            pl=servermanager.sources.PlaneSource()
        except AttributeError:
            pl=servermanager.sources.Plane()

        pl.Origin = list(origin)
        pl.Point1 = list(pt1)
        pl.Point2 = list(pt2)
        SimpleSource.__init__(self,name,pl)
        
class Cube(SimpleSource):
    """Displays a cube"""

    def __init__(self,name,pt1,pt2):
        """:param name: name under which the cube should be displayed
        :param pt1: Point one that describes the box
        :param pt2: Point two that describes the box"""

        pt1=self.makeVector(pt1)
        pt2=self.makeVector(pt2)
        try:
            box=servermanager.sources.CubeSource()
        except AttributeError:
            box=servermanager.sources.Box()
        box.Center=list(0.5*(pt1+pt2))
        diff=pt1-pt2
        box.XLength=abs(diff[0])
        box.YLength=abs(diff[1])
        box.ZLength=abs(diff[2])
        
        SimpleSource.__init__(self,name,box)
        
class STL(SimpleSource):
    """Displays a STL-File"""

    def __init__(self,name,stlFile):
        """:param name: name under which the surface should be displayed
        :param stlFile: the STL-file"""

        try:
            stl=servermanager.sources.stlreader()
        except AttributeError:
            stl=servermanager.sources.STLReader()
            
        stl.FileNames=[stlFile]
        stl.UpdatePipeline()

        SimpleSource.__init__(self,name,stl)

class Text(SimpleSource):
    """Displays a Vector-Text"""

    def __init__(self,name,text,scale=1,position=None):
        """:param name: name under which the sphere should be displayed
        :param text: the text that will be displayed
        :param scale: the scaling of the text (in terms ofcharacterist length of the geometry
        :param position: the actual position at which the object should be centered"""

        try:
            txt=servermanager.sources.VectorText()
        except AttributeError:
            txt=servermanager.sources.a3DText()
            
        txt.Text=text
        
        SimpleSource.__init__(self,name,txt)

        if not position:
            position=gc()

        try:
            self.repr.Translate=list(position)
        except AttributeError:
            self.repr.Position=list(position)
        
        self.repr.Origin=list(position)
        
        scale*=lc()/self.characteristicLength()
        
        self.repr.Scale=(scale,scale,scale)

class DirectedSource(SimpleSource):
    """A Source that looks in a specific direction.
    Assumes that the original base is located at (0 0 0)"""

    def __init__(self,name,src,base,tip):
        """:param name: name under which the arrow will be displayed
        :param src: The source objects
        :param base: the base the arrow points away from
        :param tip: the point the arrow points to"""
        SimpleSource.__init__(self,name,src)
        self.base=base
        self.tip =tip
        self.recalc()
#        self.arrow=SimpleSource(name,ar)
#        tf=servermanager.filters.TransformFilter(Input = ar)
#        trafo=tm().Transform()
#        trafo.Position = list(base)
#        trafo.Scale = [abs(base-tip)]*3       
#        tf.Transform = trafo


    def recalc(self):
        """Recalculate the orientation of the object according to the tip and
        the base"""
        diff=self.tip-self.base
        r=abs(diff)
        phi=math.acos(diff[0]/(r+1e-15))*180/math.pi
        theta=math.atan2(diff[1],-diff[2])*180/math.pi
        self.repr.Scale=[r]*3
        self.repr.Position=list(self.base)
        self.repr.Orientation=[theta,phi,0]

    def setBase(self,base):
        """Reset the base point"""
        self.base=base
        self.recalc()
        
    def setTip(self,tip):
        """Reset the tip point"""
        self.tip=tip
        self.recalc()
        
class Arrow(DirectedSource):
    """Displays a simple arrow"""

    def __init__(self,name,base,tip):
        """:param name: name under which the arrow will be displayed
        :param base: the base the arrow points away from
        :param tip: the point the arrow points to"""
        
        try:
            DirectedSource.__init__(self,
                                    name,
                                    servermanager.sources.ArrowSource(),
                                    base,
                                    tip)
        except AttributeError:
            DirectedSource.__init__(self,
                                    name,
                                    servermanager.sources.Arrow(),
                                    base,
                                    tip)

class Glyph(DirectedSource):
    """Displays a simple glyph"""

    def __init__(self,name,base,tip):
        """:param name: name under which the glyph will be displayed
        :param base: the base the glyph points away from
        :param tip: the point the glyph points to"""

        try:
            DirectedSource.__init__(self,
                                    name,
                                    servermanager.sources.GlyphSource2D(),
                                    base,
                                    tip)
        except AttributeError:
            DirectedSource.__init__(self,
                                    name,
                                    servermanager.sources.a2DGlyph(),
                                    base,
                                    tip)
