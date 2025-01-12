#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from uuid import UUID

from lxml import etree

from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.post_field import X_VELOCITY, Field, getFieldInstance
from baramFlow.coredb.scaffold import Scaffold


@dataclass
class IsoSurface(Scaffold):
    field: Field = X_VELOCITY
    isoValues: str = '0'
    surfacePerValue: int = 1
    spacing: str = '1'

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text
        fieldType = e.find('fieldType', namespaces=nsmap).text
        fieldName = e.find('fieldName', namespaces=nsmap).text
        field = getFieldInstance(fieldType, fieldName)
        isoValues = e.find('isoValues', namespaces=nsmap).text
        surfacePerValue = int(e.find('surfacesPerValue', namespaces=nsmap).text)
        spacing = e.find('spacing', namespaces=nsmap).text

        return IsoSurface(uuid=uuid,
                          name=name,
                          field=field,
                          isoValues=isoValues,
                          surfacePerValue=surfacePerValue,
                          spacing=spacing)

    def toElement(self):
        string = ('<surface xmlns="http://www.baramcfd.org/baram">'
                 f'    <uuid>{str(self.uuid)}</uuid>'
                 f'    <name>{self.name}</name>'
                 f'    <fieldType>{self.field.type}</fieldType>'
                 f'    <fieldName>{self.field.name}</fieldName>'
                 f'    <isoValues>{self.isoValues}</isoValues>'
                 f'    <surfacesPerValue>{self.surfacePerValue}</surfacesPerValue>'
                 f'    <spacing>{self.spacing}</spacing>'
                  '</surface>')
        return etree.fromstring(string)
