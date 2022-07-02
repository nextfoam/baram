"""Building blocks for a blockMeshDict"""

import re,os
import copy
import math
from PyFoam.Basics.LineReader import LineReader
from PyFoam.RunDictionary.FileBasis import FileBasisBackup
from PyFoam.RunDictionary.BlockMesh import BlockMesh
from PyFoam.RunDictionary.ParsedBlockMeshDict import ParsedBlockMeshDict
from PyFoam.Basics.DataStructures import *
from math import ceil
from PyFoam.Error import error

class BlockMeshComponent(object):
    def __init__(self, dimension):
        self.dimension=dimension

class BlockMeshEdge(BlockMeshComponent):
    def __init__(self, start, end, center, points):
        self.start=start
        self.end=end
        self.center=center
        self.points=copy.deepcopy(points)
        if(center==None and points!=None):
            self.edgeType='spline'
        else:
            self.edgeType='arc'

    def __repr__(self):
        result=""
        if self.edgeType=='spline':
            result='\t'+"spline"+' '+str(self.start)+' '+str(self.end)+"\n\t("
            for point in  self.points:
                result+='\n\t\t\t'+"("+' '.join(str(n) for n in point)+ ")"
            result+='\n\t'+")"
        elif self.edgeType=='arc':
            result='\t'+"arc"+' '+str(self.start)+' '+str(self.end)+"  ("+' '.join(str(n) for n in self.center)+ ")"
        return result
    def __str__(self):
        result=""
        if self.edgeType=='spline':
            result='\t'+"spline"+' '+str(self.start)+' '+str(self.end)+"\n\t("
            for point in  self.points:
                result+='\n\t\t\t'+str(point)
            result+='\n\t'+")"
        elif self.edgeType=='arc':
            result='\t'+"arc"+' '+str(self.start)+' '+str(self.end)+' '+str(self.center)
        return result

class BlockMeshBoundary(BlockMeshComponent):
    def __init__(self, name, boundaryType, faces):
        self.name=name
        self.boundaryType=boundaryType
        self.faces=faces

    def __repr__(self):
        result='\t'+self.name+'\n\t'+"{"+'\n\t\t'+"type "+self.boundaryType+";"+'\n\t\t'+"faces"+"\n\t\t("
        for face in  self.faces:
            result+='\n\t\t\t'+"("+' '.join(str(n) for n in face)+ ")"
        result+='\n\t\t'+");"+"\n\t}"
        return result
    def __str__(self):
        result='\t'+self.name+'\n\t'+"{"+'\n\t\t'+"type "+self.boundaryType+";"+'\n\t\t'+"faces"+"\n\t\t("
        for face in  self.faces:
            result+='\n\t\t\t'+"("+' '.join(str(n) for n in face)+ ")"
        result+='\n\t\t'+");"+"\n\t}"
        return result

class BlockMeshVertex(BlockMeshComponent):
    def __init__(self,origin,coordinates):
        self.coordinates=coordinates
        self.origin=origin
        if(len(self.coordinates) is 2):
            self.dimension=2
        elif(len(coordinates) is 3):
            self.dimension=3
        else:
            self.dimension=None

    def extend(self,extensionType,value):
        newvertex=deepcopy(self)
        if(extensionType is "EXTRUDE"):
            newvertex.coordinates.append(value)
        elif(extensionType is "ROTATEY"):
            newvertex.coordinates.append(
                abs(self.coordinates[0]-self.origin[0])
                *
                math.sin(math.radians(value)))
        elif(extensionType is "ROTATEX"):
            newvertex.coordinates.append(
                abs(self.coordinates[1]-self.origin[1])
                *
                math.sin(math.radians(value)))
        return newvertex
    def __str__(self):
        result="("+' '.join(str(n) for n in self.coordinates)+ ")"
        return result
