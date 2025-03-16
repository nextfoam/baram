#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from uuid import UUID

from lxml import etree
from vtkmodules.vtkCommonCore import VTK_MULTIBLOCK_DATA_SET, VTK_POLY_DATA
from vtkmodules.vtkCommonDataModel import vtkCompositeDataSet, vtkMultiBlockDataSet, vtkPolyData
from vtkmodules.vtkFiltersCore import vtkAppendPolyData

from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.scaffold import Scaffold


@dataclass
class BoundaryScaffold(Scaffold):
    boundaries: list[str] = field(default_factory=list)

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

    def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        polyData = vtkAppendPolyData()

        for bcid in self.boundaries:
            rname = BoundaryDB.getBoundaryRegion(bcid)
            bcname = BoundaryDB.getBoundaryName(bcid)

            if rname != '':  # multi-region
                block = self._findBlock(mBlock, rname, VTK_MULTIBLOCK_DATA_SET)
                if block is None:
                    raise AssertionError('Corrupted Case: Region not exists')
            else:
                block = mBlock

            block = self._findBlock(block, 'boundary', VTK_MULTIBLOCK_DATA_SET)
            if block is None:
                raise AssertionError('Corrupted Case: boundary group not exists')

            data = self._findBlock(block, bcname, VTK_POLY_DATA)
            if data is None:
                raise AssertionError('Corrupted Case: boundary not exists')

            polyData.AddInputData(data)

        polyData.Update()

        return polyData.GetOutput()

    def _findBlock(self, mBlock: vtkMultiBlockDataSet, name: str, type_: int):
        n = mBlock.GetNumberOfBlocks()
        for i in range(0, n):
            if not mBlock.HasMetaData(i):
                continue

            if name != mBlock.GetMetaData(i).Get(vtkCompositeDataSet.NAME()):
                continue

            ds = mBlock.GetBlock(i)
            dsType = ds.GetDataObjectType()

            if dsType != type_:
                continue

            if ds.GetNumberOfCells() == 0:
                continue

            return ds

        return None

