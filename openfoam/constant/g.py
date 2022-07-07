#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from view.setup.cell_zone_conditions.cell_zone_db import CellZoneDB
from openfoam.dictionary_file import DictionaryFile


class G(DictionaryFile):
    DIMENSIONS = '[0 1 -2 0 0 0 0]'

    def __init__(self, rname: str):
        super().__init__(self.constantLocation(rname), 'g')

        self._rname = rname

    def build(self):
        if self._data is not None:
            return

        db = coredb.CoreDB()

        self._data = {
            'dimensions': self.DIMENSIONS,
            'value': db.getVector(CellZoneDB.OPERATING_CONDITIONS_XPATH + '/gravity/direction')
        }

        return self
