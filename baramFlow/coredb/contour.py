#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from uuid import UUID

from PySide6.QtGui import QColor
from lxml import etree

from baramFlow.coredb.reporting_scaffold import ReportingScaffold
from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.post_field import FIELD_TEXTS, X_VELOCITY, Field, getFieldInstance
from baramFlow.coredb.visual_report import VisualReport
from baramFlow.coredb.color_scheme import ColormapScheme


@dataclass
class Contour(VisualReport):
    field: Field = X_VELOCITY

    fieldDisplayName: str = FIELD_TEXTS[X_VELOCITY]
    numberOfLevels: int = 256
    useCustomRange: bool = False
    customRangeMin: str = '0.0'
    customRangeMax: str = '0.0'
    clipToRange: bool = False
    useCustomColorScheme: bool = False
    colorScheme: ColormapScheme = ColormapScheme.Turbo
    customMinColor: QColor = QColor.fromString('#000000')
    customMaxColor: QColor = QColor.fromString('#ffffff')

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text

        fieldType = e.find('fieldType', namespaces=nsmap).text
        fieldName = e.find('fieldName', namespaces=nsmap).text
        field = getFieldInstance(fieldType, fieldName)

        time = e.find('time', namespaces=nsmap).text

        fieldDisplayName = e.find('fieldDisplayName', namespaces=nsmap).text
        numberOfLevels = int(e.find('numberOfLevels', namespaces=nsmap).text)
        useCustomRange = True if e.find('useCustomRange', namespaces=nsmap).text == 'true' else False
        customRangeMin = e.find('customRangeMin', namespaces=nsmap).text
        customRangeMax = e.find('customRangeMax', namespaces=nsmap).text
        clipToRange = True if e.find('clipToRange', namespaces=nsmap).text == 'true' else False
        useCustomColorScheme = True if e.find('useCustomColorScheme', namespaces=nsmap).text == 'true' else False
        colorScheme = ColormapScheme(int(e.find('colorScheme', namespaces=nsmap).text))
        customMinColor = QColor.fromString(e.find('customMinColor', namespaces=nsmap).text)
        customMaxColor = QColor.fromString(e.find('customMaxColor', namespaces=nsmap).text)

        scaffoldsElement = e.find('scaffolds', namespaces=nsmap)

        scaffolds = []
        for scaffoldElement in scaffoldsElement.findall('scaffold', namespaces=nsmap):
            scaffold = ReportingScaffold.fromElement(scaffoldElement)
            scaffolds.append(scaffold)

        return Contour(uuid=uuid,
                          name=name,
                          field=field,
                          time=time,
                          fieldDisplayName=fieldDisplayName,
                          numberOfLevels=numberOfLevels,
                          useCustomRange=useCustomRange,
                          customRangeMin=customRangeMin,
                          customRangeMax=customRangeMax,
                          clipToRange=clipToRange,
                          useCustomColorScheme=useCustomColorScheme,
                          colorScheme=colorScheme,
                          customMinColor=customMinColor,
                          customMaxColor=customMaxColor,
                          scaffolds=scaffolds)

    def toElement(self):
        string =   ('<contour xmlns="http://www.baramcfd.org/baram">'
                   f'    <uuid>{str(self.uuid)}</uuid>'
                   f'    <name>{self.name}</name>'
                   f'    <fieldType>{self.field.type}</fieldType>'
                   f'    <fieldName>{self.field.name}</fieldName>'
                   f'    <time>{self.time}</time>'
                   f'    <fieldDisplayName>{self.fieldDisplayName}</fieldDisplayName>'
                   f'    <numberOfLevels>{str(self.numberOfLevels)}</numberOfLevels>'
                   f'    <useCustomRange>{"true" if self.useCustomRange else "false"}</useCustomRange>'
                   f'    <customRangeMin>{self.customRangeMin}</customRangeMin>'
                   f'    <customRangeMax>{self.customRangeMax}</customRangeMax>'
                   f'    <clipToRange>{"true" if self.clipToRange else "false"}</clipToRange>'
                   f'    <useCustomColorScheme>{"true" if self.useCustomColorScheme else "false"}</useCustomColorScheme>'
                   f'    <colorScheme>{str(self.colorScheme.value)}</colorScheme>'
                   f'    <customMinColor>{self.customMinColor.name()}</customMinColor>'
                   f'    <customMaxColor>{self.customMaxColor.name()}</customMaxColor>'
                   f'    <scaffolds/>'
                   f'</contour>')

        element = etree.fromstring(string)

        scaffoldsElement = element.find('scaffolds', namespaces=nsmap)

        for s in self.scaffolds:
            scaffoldsElement.append(s)

        return etree.fromstring(string)

    def xpath(self):
        return f'/contour[uuid="{str(self.uuid)}"]'