#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from lxml import etree
from uuid import UUID

from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkPolyData, vtkStaticCellLocator
from vtkmodules.vtkFiltersCore import vtkPointDataToCellData, vtkResampleWithDataSet
from vtkmodules.vtkFiltersSources import vtkDiskSource

from baramFlow.coredb import coredb
from baramFlow.coredb.libdb import nsmap
from baramFlow.base.scaffold.scaffold import Scaffold
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

    outerRadius: str = '1'
    innerRadius: str = '0'

    radialSamples: int = 10
    circumferentialSamples: int = 20

    @classmethod
    def parseScaffolds(cls) -> dict[UUID, Scaffold]:
        scaffolds: dict[UUID, Scaffold] = {}

        for e in coredb.CoreDB().getElements(Scaffold.SCAFFOLDS_PATH + '/diskScaffolds/diskScaffold'):
            s = DiskScaffold.fromElement(e)
            scaffolds[s.uuid] = s

        return scaffolds

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

        outerRadius = e.find('outerRadius', namespaces=nsmap).text
        innerRadius = e.find('innerRadius', namespaces=nsmap).text

        radialSamples = int(e.find('radialSamples', namespaces=nsmap).text)
        circumferentialSamples = int(e.find('circumferentialSamples', namespaces=nsmap).text)

        return DiskScaffold(uuid=uuid,
                          name=name,
                          centerX=centerX,
                          centerY=centerY,
                          centerZ=centerZ,
                          normalX=normalX,
                          normalY=normalY,
                          normalZ=normalZ,
                          outerRadius=outerRadius,
                          innerRadius=innerRadius,
                          radialSamples=radialSamples,
                          circumferentialSamples=circumferentialSamples)

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
                 f'    <outerRadius>{self.outerRadius}</outerRadius>'
                 f'    <innerRadius>{self.innerRadius}</innerRadius>'
                 f'    <radialSamples>{str(self.radialSamples)}</radialSamples>'
                 f'    <circumferentialSamples>{str(self.circumferentialSamples)}</circumferentialSamples>'
                  '</diskScaffold>')
        return etree.fromstring(string)

    def xpath(self):
        return f'/diskScaffold[uuid="{str(self.uuid)}"]'

    def addElement(self):
        coredb.CoreDB().addElement(Scaffold.SCAFFOLDS_PATH + '/diskScaffolds', self.toElement())

    def removeElement(self):
        coredb.CoreDB().removeElement(Scaffold.SCAFFOLDS_PATH + '/diskScaffolds' + self.xpath())

    async def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        mesh = await collectInternalMesh(mBlock)

        disk = vtkDiskSource()
        disk.SetCenter(float(self.centerX), float(self.centerY), float(self.centerZ))
        disk.SetNormal(float(self.normalX), float(self.normalY), float(self.normalZ))
        disk.SetOuterRadius(float(self.outerRadius))
        disk.SetInnerRadius(float(self.innerRadius))
        disk.SetRadialResolution(self.radialSamples)
        disk.SetCircumferentialResolution(self.circumferentialSamples)

        resample = vtkResampleWithDataSet()
        locator = vtkStaticCellLocator()
        resample.SetCellLocatorPrototype(locator)
        resample.ComputeToleranceOff()  #  Computed tolerance is too small so that some field values are not interpolated
        resample.SetTolerance(1.0)  # "1.0" is the default value for "Tolerance" in vtkResampleWithDataSet
        resample.PassPartialArraysOn()
        resample.SetSourceData(mesh)
        resample.SetInputConnection(disk.GetOutputPort())

        p2c = vtkPointDataToCellData()
        p2c.PassPointDataOn()
        p2c.ProcessAllArraysOn()
        p2c.SetInputConnection(resample.GetOutputPort())

        await vtk_run_in_thread(p2c.Update)

        return p2c.GetPolyDataOutput()