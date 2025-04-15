#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from uuid import UUID

from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkUnstructuredGrid

from baramFlow.coredb.reporting_scaffold import ReportingScaffold
from baramFlow.coredb.scaffolds_db import ScaffoldsDB
from baramFlow.openfoam.openfoam_reader import OpenFOAMReader
from libbaram.async_signal import AsyncSignal
from libbaram.openfoam.polymesh import collectInternalMesh


@dataclass
class VisualReport:
    instanceUpdated: AsyncSignal = field(init=False)
    reportingScaffoldAdded: AsyncSignal = field(init=False)
    reportingScaffoldRemoving: AsyncSignal = field(init=False)
    reportingScaffoldRemoved: AsyncSignal = field(init=False)

    uuid: UUID
    name: str

    time: str = '0'

    # Not a configuration, Not saved in CoreDB
    polyMesh: vtkMultiBlockDataSet = None

    # Not a configuration, Not saved in CoreDB.
    # It is calculated and stored for caching.
    internalMesh: vtkUnstructuredGrid = None

    reportingScaffolds: dict[UUID, ReportingScaffold] = field(default_factory=dict)

    def __post_init__(self):
        self.instanceUpdated = AsyncSignal(UUID)
        self.reportingScaffoldAdded = AsyncSignal(UUID)
        self.reportingScaffoldRemoving = AsyncSignal(UUID)
        self.reportingScaffoldRemoved = AsyncSignal(UUID)

    @classmethod
    def fromElement(cls, e):
        raise NotImplementedError

    def toElement(self):
        raise NotImplementedError

    async def notifyReportUpdated(self):
        self.saveToCoreDB()
        await self.instanceUpdated.emit(self.uuid)

    async def notifyReportingScaffoldAdded(self, uuid: UUID):
        await self.reportingScaffoldAdded.emit(uuid)

    async def notifyScaffoldRemoving(self, uuid: UUID):
        await self.reportingScaffoldRemoving.emit(uuid)

    async def notifyReportingScaffoldRemoved(self, uuid: UUID):
        await self.reportingScaffoldRemoved.emit(uuid)

    def saveToCoreDB(self):
        raise NotImplementedError

    async def updatePolyMesh(self):
        async with OpenFOAMReader() as reader:
            reader.setTimeValue(float(self.time))
            await reader.update()
            mBlock = reader.getOutput()

        self.polyMesh = mBlock
        self.internalMesh = await collectInternalMesh(mBlock)

        for rs in self.reportingScaffolds.values():
            scaffold = ScaffoldsDB().getScaffold(rs.scaffoldUuid)
            rs.dataSet = await scaffold.getDataSet(self.polyMesh)

        self.rangeMin, self.rangeMax = self.getValueRange(self.useNodeValues, self.relevantScaffoldsOnly)

        await self.instanceUpdated.emit(self.uuid)
