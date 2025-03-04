#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from uuid import UUID

from PySide6.QtCore import QObject, Signal



from baramFlow.coredb.reporting_scaffold import ReportingScaffold


class VisualReportObserver(QObject):
    instanceUpdated = Signal(UUID)


@dataclass
class VisualReport(VisualReportObserver):
    uuid: UUID
    name: str

    time: str = '0'

    scaffolds: list[ReportingScaffold] = field(default_factory=list)

    def __post_init__(self):
        super().__init__()

    @classmethod
    def fromElement(cls, e):
        raise NotImplementedError

    def toElement(self):
        raise NotImplementedError

    def markUpdated(self):
        self.instanceUpdated.emit(self.uuid)

