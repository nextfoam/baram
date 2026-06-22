#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass


@dataclass
class PolyMeshRegion:
    rname: str
    boundaries: dict
    cellZones: list
