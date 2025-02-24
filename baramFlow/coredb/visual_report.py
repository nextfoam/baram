#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from uuid import UUID



from baramFlow.coredb.reporting_scaffold import ReportingScaffold


@dataclass
class VisualReport:
    uuid: UUID
    name: str

    time: str = '0'

    scaffolds: list[ReportingScaffold] = field(default_factory=list)

    @classmethod
    def fromElement(cls, e):
        raise NotImplementedError

    def toElement(self):
        raise NotImplementedError