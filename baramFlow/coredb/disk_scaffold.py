#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from uuid import UUID

from lxml import etree

from vtkmodules.vtkCommonDataModel import vtkCylinder, vtkDataObject, vtkImplicitBoolean, vtkMultiBlockDataSet, vtkPlane, vtkPolyData, vtkSphere
from vtkmodules.vtkFiltersCore import vtkAppendPolyData, vtkContourFilter, vtkCutter
from vtkmodules.vtkFiltersGeneral import vtkClipDataSet

from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.post_field import COORDINATE, Field, VectorComponent, getFieldInstance
from baramFlow.coredb.post_field import VELOCITY
from baramFlow.coredb.scaffold import Scaffold
from baramFlow.openfoam.solver_field import getSolverFieldName
from libbaram.openfoam.polymesh import collectInternalMesh
from libbaram.vtk_threads import vtk_run_in_thread


@dataclass
class DiskScaffold(Scaffold):
    centerX: str = '0'
    centerY: str = '0'
    centerZ: str = '0'

    normalX: str = '1'
    normalY: str = '0'
    normalZ: str = '0'

    radius: str = '1'

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text

        centerX = e.find('center/x', namespaces=nsmap).text
        centerY = e.find('center/y', namespaces=nsmap).text
        centerZ = e.find('center/z', namespaces=nsmap).text

        normalX = e.find('normal/x', namespaces=nsmap).text
        normalY = e.find('normal/y', namespaces=nsmap).text
        normalZ = e.find('normal/z', namespaces=nsmap).text

        radius = e.find('radius', namespaces=nsmap).text

        return DiskScaffold(uuid=uuid,
                          name=name,
                          centerX=centerX,
                          centerY=centerY,
                          centerZ=centerZ,
                          normalX=normalX,
                          normalY=normalY,
                          normalZ=normalZ,
                          radius=radius)

    def toElement(self):
        string = ('<diskScaffold xmlns="http://www.baramcfd.org/baram">'
                 f'    <uuid>{str(self.uuid)}</uuid>'
                 f'    <name>{self.name}</name>'
                 f'    <center>'
                 f'        <x>{self.centerX}</x>'
                 f'        <y>{self.centerY}</y>'
                 f'        <z>{self.centerZ}</z>'
                 f'    </center>'
                 f'    <normal>'
                 f'        <x>{self.normalX}</x>'
                 f'        <y>{self.normalY}</y>'
                 f'        <z>{self.normalZ}</z>'
                 f'    </normal>'
                 f'    <radius>{self.radius}</radius>'
                  '</diskScaffold>')
        return etree.fromstring(string)

    def xpath(self):
        return f'/diskScaffold[uuid="{str(self.uuid)}"]'

    async def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        mesh = collectInternalMesh(mBlock)

        cylinder = vtkCylinder()
        cylinder.SetCenter(float(self.centerX), float(self.centerY), float(self.centerZ))
        cylinder.SetAxis(float(self.normalX), float(self.normalY), float(self.normalZ))
        cylinder.SetRadius(float(self.radius))

        plane = vtkPlane()
        plane.SetOrigin(0, 0, 0)
        plane.SetOrigin(float(self.centerX), float(self.centerY), float(self.centerZ))
        plane.SetNormal(float(self.normalX), float(self.normalY), float(self.normalZ))


        clip = vtkClipDataSet()
        clip.InsideOutOn()
        clip.SetClipFunction(cylinder)
        clip.SetInputData(mesh)

        # boolean = vtkImplicitBoolean()
        # boolean.SetOperationTypeToIntersection()
        # boolean.AddFunction(cylinder)
        # boolean.AddFunction(plane)

        cutter = vtkCutter()
        cutter.SetInputConnection(clip.GetOutputPort())
        cutter.SetCutFunction(plane)

        await vtk_run_in_thread(cutter.Update)

        return cutter.GetOutput()
