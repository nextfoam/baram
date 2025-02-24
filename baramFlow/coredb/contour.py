#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from uuid import UUID

from lxml import etree

from baramFlow.coredb.reporting_scaffold import ReportingScaffold
from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.post_field import X_VELOCITY, Field, getFieldInstance
from baramFlow.coredb.visual_report import VisualReport


@dataclass
class Contour(VisualReport):
    field: Field = X_VELOCITY

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text

        fieldType = e.find('fieldType', namespaces=nsmap).text
        fieldName = e.find('fieldName', namespaces=nsmap).text
        field = getFieldInstance(fieldType, fieldName)

        time = e.find('time', namespaces=nsmap).text

        scaffoldsElement = e.find('scaffolds', namespaces=nsmap)

        scaffolds = []
        for scaffoldElement in scaffoldsElement.findall('scaffold', namespaces=nsmap):
            scaffold = ReportingScaffold.fromElement(scaffoldElement)
            scaffolds.append(scaffold)

        return Contour(uuid=uuid,
                          name=name,
                          field=field,
                          time=time,
                          scaffolds=scaffolds)

    def toElement(self):
        string =   ('<contour xmlns="http://www.baramcfd.org/baram">'
                   f'    <uuid>{str(self.uuid)}</uuid>'
                   f'    <name>{self.name}</name>'
                   f'    <fieldType>{self.field.type}</fieldType>'
                   f'    <fieldName>{self.field.name}</fieldName>'
                   f'    <time>{self.time}</time>'
                   f'    <scaffolds/>'
                   f'</contour>')

        element = etree.fromstring(string)

        scaffoldsElement = element.find('scaffolds', namespaces=nsmap)

        for s in self.scaffolds:
            scaffoldsElement.append(s)

        return etree.fromstring(string)

    def xpath(self):
        return f'/contour[uuid="{str(self.uuid)}"]'