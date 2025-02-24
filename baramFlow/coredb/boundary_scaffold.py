#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from uuid import UUID

from lxml import etree
from vtkmodules.vtkCommonCore import VTK_MULTIBLOCK_DATA_SET, VTK_POLY_DATA
from vtkmodules.vtkCommonDataModel import vtkCompositeDataSet, vtkMultiBlockDataSet, vtkPolyData

from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.scaffold import Scaffold


@dataclass
class BoundaryScaffold(Scaffold):
    bcid: str = '0'

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text
        bcid = e.find('bcid', namespaces=nsmap).text

        return BoundaryScaffold(uuid=uuid,
                          name=name,
                          bcid=bcid)

    def toElement(self):
        string = ('<boundary xmlns="http://www.baramcfd.org/baram">'
                 f'    <uuid>{str(self.uuid)}</uuid>'
                 f'    <name>{self.name}</name>'
                 f'    <bcid>{self.bcid}</bcid>'
                  '</boundary>')

        return etree.fromstring(string)

    def xpath(self):
        return f'/boundary[uuid="{str(self.uuid)}"]'

    def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        rname = BoundaryDB.getBoundaryRegion(self.bcid)
        bcname = BoundaryDB.getBoundaryName(self.bcid)

        if rname != '':  # multi-region
            block = self._findBlock(mBlock, rname, VTK_MULTIBLOCK_DATA_SET)
            if block is None:
                raise AssertionError('Corrupted Case: Region not exists')
        else:
            block = mBlock

        block = self._findBlock(block, 'boundary', VTK_MULTIBLOCK_DATA_SET)
        if block is None:
            raise AssertionError('Corrupted Case: boundary group not exists')

        polyData = self._findBlock(block, bcname, VTK_POLY_DATA)
        if polyData is None:
            raise AssertionError('Corrupted Case: boundary not exists')

        return polyData

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

