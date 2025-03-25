#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkPolyData

from libbaram.async_signal import AsyncSignal


class ScaffoldType(Enum):
    BOUNDARY	    = 'boundary'
    ISO_SURFACE	    = 'isoSurface'


@dataclass
class Scaffold:
    instanceUpdated: AsyncSignal = field(init=False)

    uuid: UUID
    name: str

    def __post_init__(self):
        self.instanceUpdated = AsyncSignal(UUID)

    @classmethod
    def fromElement(cls, e):
        raise NotImplementedError

    def toElement(self):
        raise NotImplementedError

    async def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        raise NotImplementedError

    async def markUpdated(self):
        await self.instanceUpdated.emit(self.uuid)
