#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator

from coredb import coredb


class G(object):
    def __init__(self, rname: str):
        self._rname = rname
        self._data = None

    def __str__(self):
        return self.asStr()

    def _build(self):
        if self._data is not None:
            return

        db = coredb.CoreDB()

        self._data = {
            'dimensions': '[0 1 -2 0 0 0 0]',
            'value': db.getVector('.//operatingConditions/gravity/direction')
        }

    def asDict(self):
        self._build()
        return self._data

    def asStr(self):
        HEADER = {
            'version': '2.0',
            'format': 'ascii',
            'class': 'dictionary',
            'location': f'constant/{self._rname}',
            'object': 'turbulenceProperties'
        }
        self._build()
        return str(FoamFileGenerator(self._data, header=HEADER))
