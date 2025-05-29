#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from dataclasses import field as dataClassField
from enum import Enum
from typing import ClassVar
from uuid import UUID

from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkPolyData

from libbaram.async_signal import AsyncSignal


class ScaffoldType(Enum):
    BOUNDARY	    = 'boundary'
    DISK_SCAFFOLD   = 'diskScaffold'
    ISO_SURFACE	    = 'isoSurface'
    LINE_SCAFFOLD   = 'lineScaffold'
    PARALLELOGRAM   = 'parallelogram'
    PLANE_SCAFFOLD  = 'planeScaffold'
    SPHERE_SCAFFOLD = 'sphereScaffold'


@dataclass
class Scaffold:
    SCAFFOLDS_PATH: ClassVar[str] = '/scaffolds'

    instanceUpdated: AsyncSignal = dataClassField(init=False)

    uuid: UUID
    name: str

    def __post_init__(self):
        self.instanceUpdated = AsyncSignal(UUID)

    @classmethod
    def fromElement(cls, e):
        raise NotImplementedError

    def toElement(self):
        raise NotImplementedError

    def xpath(self) -> str:
        raise NotImplementedError

    def addElement(self):
        raise NotImplementedError

    def removeElement(self):
        raise NotImplementedError

    async def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        raise NotImplementedError

    async def markUpdated(self):
        await self.instanceUpdated.emit(self.uuid)
