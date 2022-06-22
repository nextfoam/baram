#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator

from coredb import coredb


class OperatingConditions:
    def __init__(self, rname: str):
        self._rname = rname
        self._data = None

    def __str__(self):
        return self.asstr()

    def _build(self):
        if self._data is not None:
            return

        db = coredb.CoreDB()

        pressure = db.getValue('.//operatingConditions/pressure')

        self._data = {
            "Op": ('Op [1 -1 -2 0 0 0 0]', pressure)
        }

    def asdict(self):
        self._build()
        return self._data

    def asstr(self):
        HEADER = {
            'version': '2.0',
            'format': 'ascii',
            'class': 'dictionary',
            'location': f'constant/{self._rname}',
            'object': 'operatingConditions'
        }
        self._build()
        return str(FoamFileGenerator(self._data, header=HEADER))
