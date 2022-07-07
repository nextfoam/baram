#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from view.setup.cell_zone_conditions.cell_zone_db import CellZoneListIndex, CellZoneDB, ZoneType
from openfoam.dictionary_file import DictionaryFile
from openfoam.porous import Porous


class FvOptions(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(self.constantLocation(rname), 'fvOptions')

        self._rname = rname
        self._db = coredb.CoreDB()

    def build(self):
        if self._data is not None:
            return

        self._data = {}

        cellZones = self._db.getCellZones(self._rname)
        for c in cellZones:
            name = c[CellZoneListIndex.NAME.value]
            czid = c[CellZoneListIndex.ID.value]
            xpath = CellZoneDB.getXPath(czid)
            type_ = self._db.getValue(xpath + '/zoneType')

            if type_ == ZoneType.POROUS.value:
                self._data[name] = Porous(czid).buildDict()
            elif type_ == ZoneType.ACTUATOR_DISK.value:
                pass

        return self
