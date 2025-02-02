#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


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