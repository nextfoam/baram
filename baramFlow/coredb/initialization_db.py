#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb import coredb


class InitializationDB:
    @classmethod
    def getXPath(cls, rname):
        return f'regions/region[name="{rname}"]/initialization'

    @classmethod
    def getSectionXPath(cls, rname, sectionName):
        return f'{cls.getXPath(rname)}/advanced/sections/section[name="{sectionName}"]'

    @classmethod
    def getInitialScalarValue(cls, rname, scalarID):
        try:
            return coredb.CoreDB().getValue(
                f'{cls.getXPath(rname)}/initialValues/userDefinedScalars/scalar[scalarID="{scalarID}"]/value')
        except LookupError:
            return 0

    @classmethod
    def buildSectionUserDefinedScalar(cls, scalarId, value):
        return ('<scalar xmlns="http://www.baramcfd.org/baram">'
                f'  <scalarID>{scalarId}</scalarID>'
                f'  <value disabled="{"false" if value else "true"}">{value if value else 0}</value>'
                '</scalar>')