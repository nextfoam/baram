#  ICE Revision: $Id$ 
""" Base class for the wrapping of graphical objects

The actual object is accessed via the member variable src.
Just adds some simple things like bounding boxes etc"""

from math import sqrt

from PyFoam.Basics.DataStructures import Vector

class SourceBase(object):
    """Base class for the sources

    The member src is the actual source object"""

    def __init__(self,src):
        """:param src: the actual source proxy"""
        self.src = src
        
    def getBounds(self):
        """Get the bounding box of the object"""
        bnds=self.src.GetDataInformation().GetBounds()

        return (bnds[0:2],bnds[2:4],bnds[4:6])

    def getMin(self):
        """Get the minimum-vector of the bounds"""
        bnd=self.getBounds()
        return Vector(bnd[0][0],bnd[1][0],bnd[2][0])
            
    def getMax(self):
        """Get the minimum-vector of the bounds"""
        bnd=self.getBounds()
        return Vector(bnd[0][1],bnd[1][1],bnd[2][1])
            
    def getCenter(self):
        """Return the center of the object"""
        return 0.5*(self.getMax()+self.getMin())
    
    def getExtent(self):
        """Return the center of the object"""
        return self.getMax()-self.getMin()
    
    def characteristicLength(self):
        """The characteristic length of the object"""

        return abs(self.getExtent())

    def makeVector(self,orig):
        """Convert a list or a tuple of length 3 to a vector for easier calculations"""

        return Vector(orig[0],orig[1],orig[2])
    
       
        
