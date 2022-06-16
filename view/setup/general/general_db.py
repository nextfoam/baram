#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb


class GeneralDB:
    MODEL_XPATH = './/general/timeTransient'
    FLOW_TYPE_XPATH = './/general/flowType'

    _db = coredb.CoreDB()

    @classmethod
    def isTimeTransient(cls):
        return cls._db.getValue(cls.MODEL_XPATH) == 'true'

    @classmethod
    def isCompressible(cls):
        return cls._db.getValue(cls.FLOW_TYPE_XPATH) == 'compressible'
