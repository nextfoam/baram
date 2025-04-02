#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from uuid import UUID

from lxml import etree
from vtkmodules.vtkCommonCore import VTK_MULTIBLOCK_DATA_SET, VTK_POLY_DATA
from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkPolyData
from vtkmodules.vtkFiltersCore import vtkAppendPolyData

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.scaffold import Scaffold
from libbaram.openfoam.polymesh import findBlock
from libbaram.vtk_threads import vtk_run_in_thread


@dataclass
class BoundaryScaffold(Scaffold):
    boundaries: list[str] = field(default_factory=list)

    @classmethod
    def parseScaffolds(cls) -> dict[UUID, Scaffold]:
        scaffolds: dict[UUID, Scaffold] = {}

        for e in coredb.CoreDB().getElements(Scaffold.SCAFFOLDS_PATH + '/boundaries/boundary'):
            s = BoundaryScaffold.fromElement(e)
            scaffolds[s.uuid] = s

        return scaffolds

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text
        boundaries = e.find('boundaries', namespaces=nsmap).text.split()

        return BoundaryScaffold(uuid=uuid,
                          name=name,
                          boundaries=boundaries)

    def toElement(self):
        string = ('<boundary xmlns="http://www.baramcfd.org/baram">'
                 f'    <uuid>{str(self.uuid)}</uuid>'
                 f'    <name>{self.name}</name>'
                 f'    <boundaries>{" ".join(self.boundaries)}</boundaries>'
                  '</boundary>')

        return etree.fromstring(string)

    def xpath(self):
        return f'/boundary[uuid="{str(self.uuid)}"]'

    def addElement(self):
        coredb.CoreDB().addElement(Scaffold.SCAFFOLDS_PATH + '/boundaries', self.toElement())

    def removeElement(self):
        coredb.CoreDB().removeElement(Scaffold.SCAFFOLDS_PATH + '/boundaries' + self.xpath())

    async def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        polyData = vtkAppendPolyData()

        for bcid in self.boundaries:
            rname = BoundaryDB.getBoundaryRegion(bcid)
            bcname = BoundaryDB.getBoundaryName(bcid)

            if rname != '':  # multi-region
                block = findBlock(mBlock, rname, VTK_MULTIBLOCK_DATA_SET)
                if block is None:
                    raise AssertionError('Corrupted Case: Region not exists')
            else:
                block = mBlock

            block = findBlock(block, 'boundary', VTK_MULTIBLOCK_DATA_SET)
            if block is None:
                raise AssertionError('Corrupted Case: boundary group not exists')

            data = findBlock(block, bcname, VTK_POLY_DATA)
            if data is None:
                raise AssertionError('Corrupted Case: boundary not exists')

            polyData.AddInputData(data)

        await vtk_run_in_thread(polyData.Update)

        return polyData.GetOutput()