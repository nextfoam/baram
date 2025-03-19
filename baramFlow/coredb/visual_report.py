#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from typing import ClassVar
from uuid import UUID

from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkUnstructuredGrid



from baramFlow.coredb.reporting_scaffold import ReportingScaffold


@dataclass
class VisualReport(QObject):
    instanceUpdated: ClassVar[Signal] = Signal(UUID)
    reportingScaffoldAdded:  ClassVar[Signal] = Signal(UUID)
    reportingScaffoldRemoving:  ClassVar[Signal] = Signal(UUID)
    reportingScaffoldRemoved:  ClassVar[Signal] = Signal(UUID)

    uuid: UUID
    name: str

    time: str = '0'

    polyMesh: vtkMultiBlockDataSet = None  # Not a configuration, Not saved in CoreDB
    internalMesh: vtkUnstructuredGrid = None  # Not a configuration, Not saved in CoreDB

    reportingScaffolds: dict[UUID, ReportingScaffold] = field(default_factory=dict)

    def __post_init__(self):
        super().__init__()

    @classmethod
    def fromElement(cls, e):
        raise NotImplementedError

    def toElement(self):
        raise NotImplementedError

    def notifyReportUpdated(self):
        self._saveToCoreDB()
        self.instanceUpdated.emit(self.uuid)

    def notifyReportingScaffoldAdded(self, uuid: UUID):
        self.reportingScaffoldAdded.emit(uuid)

    def notifyScaffoldRemoving(self, uuid: UUID):
        self.reportingScaffoldRemoving.emit(uuid)

    def notifyReportingScaffoldRemoved(self, uuid: UUID):
        self.reportingScaffoldRemoved.emit(uuid)

    def _saveToCoreDB(self):
        raise NotImplementedError