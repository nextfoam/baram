#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb


class GeneralDB:
    GENERAL_XPATH = './/general'
    OPERATING_CONDITIONS_XPATH = './/operatingConditions'

    @classmethod
    def isTimeTransient(cls):
        return coredb.CoreDB().getValue(cls.GENERAL_XPATH + '/timeTransient') == 'true'

    @classmethod
    def isCompressible(cls):
        return coredb.CoreDB().getValue(cls.GENERAL_XPATH + '/flowType') == 'compressible'

    @classmethod
    def isGravityModelOn(cls):
        return coredb.CoreDB().getAttribute(cls.OPERATING_CONDITIONS_XPATH + '/gravity', 'disabled') == 'false'

