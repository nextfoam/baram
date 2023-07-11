"""Gets information about the mesh of a case. Makes no attempt to manipulate
the mesh, because this is better left to the OpenFOAM-utilities"""

from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.RunDictionary.ListFile import ListFile
from PyFoam.Error import PyFoamException
from PyFoam.RunDictionary.ParsedParameterFile import ParsedFileHeader

from os import path
import re

class MeshInformation:
    """Reads Information about the mesh on demand"""
    
    def __init__(self,
                 case,
                 time="constant",
                 processor=None,
                 region=None):
        """:param case: Path to the case-directory
        :param time: Time for which the  mesh should be looked at
        :param processor: Name of the processor directory for decomposed cases"""
        self.sol=SolutionDirectory(case,paraviewLink=False,archive=None,region=region)
        self.time=time
        self.processor=processor
        
    def nrOfFaces(self):
        try:
            return self.faces
        except AttributeError:
            try:
                faces=ListFile(self.sol.polyMeshDir(time=self.time,processor=self.processor),"faces")
                self.faces=faces.getSize()
            except IOError:
                faces=ListFile(self.sol.polyMeshDir(processor=self.processor),"faces")
                self.faces=faces.getSize()
                
            return self.faces

    def nrOfPoints(self):
        try:
            return self.points
        except AttributeError:
            try:
                points=ListFile(self.sol.polyMeshDir(time=self.time,processor=self.processor),"points")
                self.points=points.getSize()
            except IOError:
                points=ListFile(self.sol.polyMeshDir(processor=self.processor),"points")
                self.points=points.getSize()

            return self.points

    def nrOfCells(self):
        try:
            return self.cells
        except:
            try:
                try:
                    owner=ParsedFileHeader(path.join(self.sol.polyMeshDir(time=self.time,processor=self.processor),"owner"))
                except IOError:
                    owner=ParsedFileHeader(path.join(self.sol.polyMeshDir(processor=self.processor),"owner"))

                mat=re.compile('.+nCells: *([0-9]+) .+').match(owner["note"])
                self.cells=int(mat.group(1))
                return self.cells
            except:
                raise PyFoamException("Not Implemented")
