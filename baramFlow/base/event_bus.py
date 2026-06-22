#!/usr/bin/env python
# -*- coding: utf-8 -*-


from enum import Enum
from threading import Lock
from typing import TypedDict

# from baramFlow.coredb.boundary_db import BoundaryType # Enum type instead of BoundaryType is used to avoid circular import
from libbaram.async_signal import AsyncSignal
from libbaram.sync_signal import SyncSignal


_mutex = Lock()


class RegionComponents(TypedDict):
    cellZones:  dict[str, str]  # {<czname>: <czid>}
    boundaries: dict[str, str]  # {<bcname>: <bcid>}


class EventBus:
    def __new__(cls, *args, **kwargs):
        with _mutex:
            if not hasattr(cls, '_instance'):
                cls._instance = super(EventBus, cls).__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self):
        with _mutex:
            if hasattr(self, '_initialized'):
                return
            else:
                self._initialized = True

        self.onMeshLoading = AsyncSignal(dict[str, RegionComponents], dict[str, RegionComponents])
        self.onProjectOpen = AsyncSignal()
        self.onProjectClose = AsyncSignal()
        # self.onBoundaryTypeChange = AsyncSignal(str, BoundaryType, BoundaryType)  # bcid, oldType, newType
        self.onBoundaryTypeChange = AsyncSignal(str, Enum, Enum)  # Enum type is used to avoid circular import

        self.onSaving = SyncSignal()
        self.onConfigChanged = SyncSignal()