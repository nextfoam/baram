#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baram.coredb import coredb
from baram.coredb.general_db import GeneralDB
from baram.openfoam.dictionary_file import DictionaryFile


class G(DictionaryFile):
    DIMENSIONS = '[0 1 -2 0 0 0 0]'

    def __init__(self):
        super().__init__(self.constantLocation(), 'g')

    def build(self):
        if self._data is not None:
            return self

        db = coredb.CoreDB()

        self._data = {
            'dimensions': self.DIMENSIONS,
            'value': db.getVector(GeneralDB.OPERATING_CONDITIONS_XPATH + '/gravity/direction')
        }

        return self
