#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from uuid import UUID


@dataclass
class Scaffold:
    uuid: UUID
    name: str

    @classmethod
    def fromElement(cls, e):
        raise NotImplementedError

    def toElement(self):
        raise NotImplementedError