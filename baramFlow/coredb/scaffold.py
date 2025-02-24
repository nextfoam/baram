#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from vtkmodules.vtkCommonDataModel import vtkCompositeDataIterator, vtkCompositeDataSet, vtkDataObject, vtkMultiBlockDataSet, vtkPolyData


class ScaffoldType(Enum):
    BOUNDARY	    = 'boundary'
    ISO_SURFACE	    = 'isoSurface'

@dataclass
class Scaffold:
    uuid: UUID
    name: str

    @classmethod
    def fromElement(cls, e):
        raise NotImplementedError

    def toElement(self):
        raise NotImplementedError

    def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        raise NotImplementedError

    def _collectInternalMesh(self, mBlock: vtkMultiBlockDataSet) -> list[vtkDataObject]:
        meshes = []
        iterator: vtkCompositeDataIterator = mBlock.NewIterator()
        while not iterator.IsDoneWithTraversal():
            if not iterator.HasCurrentMetaData():
                iterator.GoToNextItem()
                continue

            name = iterator.GetCurrentMetaData().Get(vtkCompositeDataSet.NAME())
            if name != 'internalMesh':
                iterator.GoToNextItem()
                continue

            dobj = iterator.GetCurrentDataObject()
            if dobj is not None:
                meshes.append(dobj)

            iterator.GoToNextItem()

        return meshes


