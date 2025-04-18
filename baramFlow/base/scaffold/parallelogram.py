#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from lxml import etree
from uuid import UUID

from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkPolyData, vtkStaticCellLocator
from vtkmodules.vtkFiltersCore import vtkPointDataToCellData, vtkResampleWithDataSet
from vtkmodules.vtkFiltersSources import vtkPlaneSource

from baramFlow.coredb import coredb
from baramFlow.coredb.libdb import nsmap
from baramFlow.base.scaffold.scaffold import Scaffold
from libbaram.openfoam.polymesh import collectInternalMesh
from libbaram.vtk_threads import vtk_run_in_thread


@dataclass
class Parallelogram(Scaffold):
    originX: str = '0'
    originY: str = '0'
    originZ: str = '0'

    point1X: str = '0'
    point1Y: str = '0'
    point1Z: str = '0'

    point2X: str = '1'
    point2Y: str = '0'
    point2Z: str = '0'

    point1Samples: int = 10
    point2Samples: int = 10

    @classmethod
    def parseScaffolds(cls) -> dict[UUID, Scaffold]:
        scaffolds: dict[UUID, Scaffold] = {}

        for e in coredb.CoreDB().getElements(Scaffold.SCAFFOLDS_PATH + '/parallelograms/parallelogram'):
            s = Parallelogram.fromElement(e)
            scaffolds[s.uuid] = s

        return scaffolds

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text

        originX = e.find('origin/x', namespaces=nsmap).text
        originY = e.find('origin/y', namespaces=nsmap).text
        originZ = e.find('origin/z', namespaces=nsmap).text

        point1X = e.find('point1/x', namespaces=nsmap).text
        point1Y = e.find('point1/y', namespaces=nsmap).text
        point1Z = e.find('point1/z', namespaces=nsmap).text

        point2X = e.find('point2/x', namespaces=nsmap).text
        point2Y = e.find('point2/y', namespaces=nsmap).text
        point2Z = e.find('point2/z', namespaces=nsmap).text

        point1Samples = int(e.find('point1Samples', namespaces=nsmap).text)
        point2Samples = int(e.find('point2Samples', namespaces=nsmap).text)

        return Parallelogram(uuid=uuid,
                          name=name,
                          originX=originX,
                          originY=originY,
                          originZ=originZ,
                          point1X=point1X,
                          point1Y=point1Y,
                          point1Z=point1Z,
                          point2X=point2X,
                          point2Y=point2Y,
                          point2Z=point2Z,
                          point1Samples=point1Samples,
                          point2Samples=point2Samples)

    def toElement(self):
        string = ('<parallelogram xmlns="http://www.baramcfd.org/baram">'
                 f'    <uuid>{str(self.uuid)}</uuid>'
                 f'    <name>{self.name}</name>'
                 f'    <origin>'
                 f'        <x>{self.originX}</x>'
                 f'        <y>{self.originY}</y>'
                 f'        <z>{self.originZ}</z>'
                 f'    </origin>'
                 f'    <point1>'
                 f'        <x>{self.point1X}</x>'
                 f'        <y>{self.point1Y}</y>'
                 f'        <z>{self.point1Z}</z>'
                 f'    </point1>'
                 f'    <point2>'
                 f'        <x>{self.point2X}</x>'
                 f'        <y>{self.point2Y}</y>'
                 f'        <z>{self.point2Z}</z>'
                 f'    </point2>'
                 f'    <point1Samples>{str(self.point1Samples)}</point1Samples>'
                 f'    <point2Samples>{str(self.point2Samples)}</point2Samples>'
                  '</parallelogram>')
        return etree.fromstring(string)

    def xpath(self):
        return f'/parallelogram[uuid="{str(self.uuid)}"]'

    def addElement(self):
        coredb.CoreDB().addElement(Scaffold.SCAFFOLDS_PATH + '/parallelograms', self.toElement())

    def removeElement(self):
        coredb.CoreDB().removeElement(Scaffold.SCAFFOLDS_PATH + '/parallelograms' + self.xpath())

    async def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        mesh = await collectInternalMesh(mBlock)

        plane = vtkPlaneSource()
        plane.SetOrigin(float(self.originX), float(self.originY), float(self.originZ))
        plane.SetPoint1(float(self.point1X), float(self.point1Y), float(self.point1Z))
        plane.SetPoint2(float(self.point2X), float(self.point2Y), float(self.point2Z))
        plane.SetXResolution(self.point1Samples)
        plane.SetYResolution(self.point2Samples)

        resample = vtkResampleWithDataSet()
        locator = vtkStaticCellLocator()
        resample.SetCellLocatorPrototype(locator)
        resample.ComputeToleranceOff()  #  Computed tolerance is too small so that some field values are not interpolated
        resample.SetTolerance(1.0)  # "1.0" is the default value for "Tolerance" in vtkResampleWithDataSet
        resample.PassPartialArraysOn()
        resample.SetSourceData(mesh)
        resample.SetInputConnection(plane.GetOutputPort())

        p2c = vtkPointDataToCellData()
        p2c.PassPointDataOn()
        p2c.ProcessAllArraysOn()
        p2c.SetInputConnection(resample.GetOutputPort())

        await vtk_run_in_thread(p2c.Update)

        return p2c.GetPolyDataOutput()