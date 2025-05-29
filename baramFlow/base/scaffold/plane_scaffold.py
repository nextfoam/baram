#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from lxml import etree
from uuid import UUID

from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkPlane, vtkPolyData
from vtkmodules.vtkFiltersCore import vtkCutter

from baramFlow.coredb import coredb
from baramFlow.coredb.libdb import nsmap
from baramFlow.base.scaffold.scaffold import Scaffold
from libbaram.openfoam.polymesh import collectInternalMesh
from libbaram.vtk_threads import vtk_run_in_thread


@dataclass
class PlaneScaffold(Scaffold):
    originX: str = '0'
    originY: str = '0'
    originZ: str = '0'

    normalX: str = '1'
    normalY: str = '0'
    normalZ: str = '0'

    @classmethod
    def parseScaffolds(cls) -> dict[UUID, Scaffold]:
        scaffolds: dict[UUID, Scaffold] = {}

        for e in coredb.CoreDB().getElements(Scaffold.SCAFFOLDS_PATH + '/planeScaffolds/planeScaffold'):
            s = PlaneScaffold.fromElement(e)
            scaffolds[s.uuid] = s

        return scaffolds

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text

        originX = e.find('origin/x', namespaces=nsmap).text
        originY = e.find('origin/y', namespaces=nsmap).text
        originZ = e.find('origin/z', namespaces=nsmap).text

        normalX = e.find('normal/x', namespaces=nsmap).text
        normalY = e.find('normal/y', namespaces=nsmap).text
        normalZ = e.find('normal/z', namespaces=nsmap).text

        return PlaneScaffold(uuid=uuid,
                          name=name,
                          originX=originX,
                          originY=originY,
                          originZ=originZ,
                          normalX=normalX,
                          normalY=normalY,
                          normalZ=normalZ)

    def toElement(self):
        string = ('<planeScaffold xmlns="http://www.baramcfd.org/baram">'
                 f'    <uuid>{str(self.uuid)}</uuid>'
                 f'    <name>{self.name}</name>'
                 f'    <origin>'
                 f'        <x>{self.originX}</x>'
                 f'        <y>{self.originY}</y>'
                 f'        <z>{self.originZ}</z>'
                 f'    </origin>'
                 f'    <normal>'
                 f'        <x>{self.normalX}</x>'
                 f'        <y>{self.normalY}</y>'
                 f'        <z>{self.normalZ}</z>'
                 f'    </normal>'
                  '</planeScaffold>')
        return etree.fromstring(string)

    def xpath(self):
        return f'/planeScaffold[uuid="{str(self.uuid)}"]'

    def addElement(self):
        coredb.CoreDB().addElement(Scaffold.SCAFFOLDS_PATH + '/planeScaffolds', self.toElement())

    def removeElement(self):
        coredb.CoreDB().removeElement(Scaffold.SCAFFOLDS_PATH + '/planeScaffolds' + self.xpath())

    async def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        mesh = await collectInternalMesh(mBlock)

        plane = vtkPlane()
        plane.SetOrigin(float(self.originX), float(self.originY), float(self.originZ))
        plane.SetNormal(float(self.normalX), float(self.normalY), float(self.normalZ))

        cutter = vtkCutter()
        cutter.SetInputData(mesh)
        cutter.SetCutFunction(plane)

        await vtk_run_in_thread(cutter.Update)

        return cutter.GetOutput()