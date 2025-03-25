#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from uuid import UUID

from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkUnstructuredGrid

from baramFlow.coredb.reporting_scaffold import ReportingScaffold
from libbaram.async_signal import AsyncSignal


@dataclass
class VisualReport:
    instanceUpdated: AsyncSignal = field(init=False)
    reportingScaffoldAdded: AsyncSignal = field(init=False)
    reportingScaffoldRemoving: AsyncSignal = field(init=False)
    reportingScaffoldRemoved: AsyncSignal = field(init=False)

    uuid: UUID
    name: str

    time: str = '0'

    polyMesh: vtkMultiBlockDataSet = None  # Not a configuration, Not saved in CoreDB
    internalMesh: vtkUnstructuredGrid = None  # Not a configuration, Not saved in CoreDB

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
        self._saveToCoreDB()
        await self.instanceUpdated.emit(self.uuid)

    async def notifyReportingScaffoldAdded(self, uuid: UUID):
        await self.reportingScaffoldAdded.emit(uuid)

    async def notifyScaffoldRemoving(self, uuid: UUID):
        await self.reportingScaffoldRemoving.emit(uuid)

    async def notifyReportingScaffoldRemoved(self, uuid: UUID):
        await self.reportingScaffoldRemoved.emit(uuid)

    def _saveToCoreDB(self):
        raise NotImplementedError