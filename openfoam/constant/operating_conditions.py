#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from view.setup.cell_zone_conditions.cell_zone_db import CellZoneDB
from openfoam.dictionary_file import DictionaryFile


class OperatingConditions(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(self.constantLocation(rname), 'OperatingConditions')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return self

        db = coredb.CoreDB()

        pressure = db.getValue(CellZoneDB.OPERATING_CONDITIONS_XPATH + '/pressure')

        self._data = {
            "Op": ('Op [1 -1 -2 0 0 0 0]', pressure)
        }

        return self
