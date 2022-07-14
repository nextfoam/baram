#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb


class GeneralDB:
    MODEL_XPATH = './/general/timeTransient'
    FLOW_TYPE_XPATH = './/general/flowType'

    @classmethod
    def isTimeTransient(cls):
        return coredb.CoreDB().getValue(cls.MODEL_XPATH) == 'true'

    @classmethod
    def isCompressible(cls):
        return coredb.CoreDB().getValue(cls.FLOW_TYPE_XPATH) == 'compressible'
