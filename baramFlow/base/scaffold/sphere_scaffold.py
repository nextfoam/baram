#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from lxml import etree
from uuid import UUID

from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkPolyData, vtkStaticCellLocator
from vtkmodules.vtkFiltersCore import vtkPointDataToCellData, vtkResampleWithDataSet
from vtkmodules.vtkFiltersSources import vtkSphereSource

from baramFlow.coredb import coredb
from baramFlow.coredb.libdb import nsmap
from baramFlow.base.scaffold.scaffold import Scaffold
from libbaram.openfoam.polymesh import collectInternalMesh
from libbaram.vtk_threads import vtk_run_in_thread


@dataclass
class SphereScaffold(Scaffold):
    centerX: str = '0'
    centerY: str = '0'
    centerZ: str = '0'

    radius: str = '1'

    longitudeSamples: int = 40
    latitudeSamples: int = 20

    @classmethod
    def parseScaffolds(cls) -> dict[UUID, Scaffold]:
        scaffolds: dict[UUID, Scaffold] = {}

        for e in coredb.CoreDB().getElements(Scaffold.SCAFFOLDS_PATH + '/sphereScaffolds/sphereScaffold'):
            s = SphereScaffold.fromElement(e)
            scaffolds[s.uuid] = s

        return scaffolds

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text

        centerX = e.find('center/x', namespaces=nsmap).text
        centerY = e.find('center/y', namespaces=nsmap).text
        centerZ = e.find('center/z', namespaces=nsmap).text

        radius = e.find('radius', namespaces=nsmap).text

        longitudeSamples = int(e.find('longitudeSamples', namespaces=nsmap).text)
        latitudeSamples = int(e.find('latitudeSamples', namespaces=nsmap).text)

        return SphereScaffold(uuid=uuid,
                          name=name,
                          centerX=centerX,
                          centerY=centerY,
                          centerZ=centerZ,
                          radius=radius,
                          longitudeSamples=longitudeSamples,
                          latitudeSamples=latitudeSamples)

    def toElement(self):
        string = ('<sphereScaffold xmlns="http://www.baramcfd.org/baram">'
                 f'    <uuid>{str(self.uuid)}</uuid>'
                 f'    <name>{self.name}</name>'
                 f'    <center>'
                 f'        <x>{self.centerX}</x>'
                 f'        <y>{self.centerY}</y>'
                 f'        <z>{self.centerZ}</z>'
                 f'    </center>'
                 f'    <radius>{self.radius}</radius>'
                 f'    <longitudeSamples>{str(self.longitudeSamples)}</longitudeSamples>'
                 f'    <latitudeSamples>{str(self.latitudeSamples)}</latitudeSamples>'
                  '</sphereScaffold>')
        return etree.fromstring(string)

    def xpath(self):
        return f'/sphereScaffold[uuid="{str(self.uuid)}"]'

    def addElement(self):
        coredb.CoreDB().addElement(Scaffold.SCAFFOLDS_PATH + '/sphereScaffolds', self.toElement())

    def removeElement(self):
        coredb.CoreDB().removeElement(Scaffold.SCAFFOLDS_PATH + '/sphereScaffolds' + self.xpath())

    async def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        mesh = await collectInternalMesh(mBlock)

        sphere = vtkSphereSource()
        sphere.SetCenter(float(self.centerX), float(self.centerY), float(self.centerZ))
        sphere.SetRadius(float(self.radius))
        sphere.SetThetaResolution(self.longitudeSamples)
        sphere.SetPhiResolution(self.latitudeSamples)

        resample = vtkResampleWithDataSet()
        locator = vtkStaticCellLocator()
        resample.SetCellLocatorPrototype(locator)
        resample.ComputeToleranceOff()  #  Computed tolerance is too small so that some field values are not interpolated
        resample.SetTolerance(1.0)  # "1.0" is the default value for "Tolerance" in vtkResampleWithDataSet
        resample.PassPartialArraysOn()
        resample.SetSourceData(mesh)
        resample.SetInputConnection(sphere.GetOutputPort())

        p2c = vtkPointDataToCellData()
        p2c.PassPointDataOn()
        p2c.ProcessAllArraysOn()
        p2c.SetInputConnection(resample.GetOutputPort())

        await vtk_run_in_thread(p2c.Update)

        return p2c.GetPolyDataOutput()