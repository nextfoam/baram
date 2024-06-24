#!/usr/bin/env python
# -*- coding: utf-8 -*-


class InitializationDB:
    @classmethod
    def getXPath(cls, rname):
        return f'regions/region[name="{rname}"]/initialization'

    @classmethod
    def getSectionXPath(cls, rname, sectionName):
        return f'{cls.getXPath(rname)}/advanced/sections/section[name="{sectionName}"]'

    @classmethod
    def buildSectionUserDefinedScalar(cls, scalarId, value):
        return ('<scalar xmlns="http://www.baramcfd.org/baram">'
                f'  <scalarID>{scalarId}</scalarID>'
                f'  <value disabled="{"false" if value else "true"}">{value if value else 0}</value>'
                '</scalar>')