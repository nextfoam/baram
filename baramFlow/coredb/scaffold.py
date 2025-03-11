#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar
from uuid import UUID

from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkCommonDataModel import vtkCompositeDataIterator, vtkCompositeDataSet, vtkDataObject, vtkMultiBlockDataSet, vtkPolyData


class ScaffoldType(Enum):
    BOUNDARY	    = 'boundary'
    ISO_SURFACE	    = 'isoSurface'


@dataclass
class Scaffold(QObject):
    instanceUpdated: ClassVar[Signal] = Signal(UUID)

    uuid: UUID
    name: str

    def __post_init__(self):
        super().__init__()

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

    def markUpdated(self):
        self.instanceUpdated.emit(self.uuid)
