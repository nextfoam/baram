#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from PySide6.QtGui import QColor
from lxml import etree

from baramFlow.coredb import coredb
from baramFlow.coredb.reporting_scaffold import ReportingScaffold
from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.post_field import FIELD_TEXTS, VELOCITY, Field, VectorComponent, getFieldInstance
from baramFlow.coredb.visual_report import VisualReport
from baramFlow.coredb.color_scheme import ColormapScheme


@dataclass
class Contour(VisualReport):
    VISUAL_REPORTS_PATH: ClassVar[str] = '/visualReports/contours'

    field: Field = VELOCITY
    fieldComponent: VectorComponent = VectorComponent.MAGNITUDE

    fieldDisplayName: str = FIELD_TEXTS[VELOCITY]
    numberOfLevels: int = 256
    useNodeValues: bool = False
    relevantScaffoldsOnly: bool = False
    useCustomRange: bool = False
    customRangeMin: str = '0.0'
    customRangeMax: str = '0.0'
    clipToRange: bool = False
    useCustomColorScheme: bool = False
    colorScheme: ColormapScheme = ColormapScheme.Turbo
    customMinColor: QColor = QColor.fromString('#000000')
    customMaxColor: QColor = QColor.fromString('#ffffff')

    includeVectors: bool = False
    vectorField: Field = VELOCITY
    vectorScaleFactor: str = '1.0'
    vectorOnRatio: int = 1
    vectorNumMax: int = 1000

    rangeMin: float = 0  # Not a configuration, Not saved in CoreDB
    rangeMax: float = 0  # Not a configuration, Not saved in CoreDB

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text

        fieldCategory = e.find('fieldCategory', namespaces=nsmap).text
        fieldCodeName = e.find('fieldCodeName', namespaces=nsmap).text
        field = getFieldInstance(fieldCategory, fieldCodeName)

        fieldComponent = VectorComponent(int(e.find('fieldComponent', namespaces=nsmap).text))

        time = e.find('time', namespaces=nsmap).text

        fieldDisplayName = e.find('fieldDisplayName', namespaces=nsmap).text
        numberOfLevels = int(e.find('numberOfLevels', namespaces=nsmap).text)
        useNodeValues = True if e.find('useNodeValues', namespaces=nsmap).text == 'true' else False
        relevantScaffoldsOnly = True if e.find('relevantScaffoldsOnly', namespaces=nsmap).text == 'true' else False
        useCustomRange = True if e.find('useCustomRange', namespaces=nsmap).text == 'true' else False
        customRangeMin = e.find('customRangeMin', namespaces=nsmap).text
        customRangeMax = e.find('customRangeMax', namespaces=nsmap).text
        clipToRange = True if e.find('clipToRange', namespaces=nsmap).text == 'true' else False
        useCustomColorScheme = True if e.find('useCustomColorScheme', namespaces=nsmap).text == 'true' else False
        colorScheme = ColormapScheme(int(e.find('colorScheme', namespaces=nsmap).text))
        customMinColor = QColor.fromString(e.find('customMinColor', namespaces=nsmap).text)
        customMaxColor = QColor.fromString(e.find('customMaxColor', namespaces=nsmap).text)

        includeVectors = True if e.find('includeVectors', namespaces=nsmap).text == 'true' else False
        vectorFieldCategory = e.find('vectorFieldCategory', namespaces=nsmap).text
        vectorFieldCodeName = e.find('vectorFieldCodeName', namespaces=nsmap).text
        vectorField = getFieldInstance(vectorFieldCategory, vectorFieldCodeName)
        vectorScaleFactor = e.find('vectorScaleFactor', namespaces=nsmap).text
        vectorOnRatio = int(e.find('vectorOnRatio', namespaces=nsmap).text)
        vectorNumMax = int(e.find('vectorNumMax', namespaces=nsmap).text)

        scaffoldsElement = e.find('scaffolds', namespaces=nsmap)

        reportingScaffolds: dict[UUID, ReportingScaffold] = {}
        for scaffoldElement in scaffoldsElement.findall('scaffold', namespaces=nsmap):
            rs = ReportingScaffold.fromElement(scaffoldElement)
            reportingScaffolds[rs.scaffoldUuid] = rs

        contour = Contour(uuid=uuid,
                          name=name,
                          field=field,
                          fieldComponent=fieldComponent,
                          time=time,
                          fieldDisplayName=fieldDisplayName,
                          numberOfLevels=numberOfLevels,
                          useNodeValues=useNodeValues,
                          relevantScaffoldsOnly=relevantScaffoldsOnly,
                          useCustomRange=useCustomRange,
                          customRangeMin=customRangeMin,
                          customRangeMax=customRangeMax,
                          clipToRange=clipToRange,
                          useCustomColorScheme=useCustomColorScheme,
                          colorScheme=colorScheme,
                          customMinColor=customMinColor,
                          customMaxColor=customMaxColor,
                          includeVectors=includeVectors,
                          vectorField=vectorField,
                          vectorScaleFactor=vectorScaleFactor,
                          vectorOnRatio=vectorOnRatio,
                          vectorNumMax=vectorNumMax,
                          reportingScaffolds=reportingScaffolds)

        for rs in reportingScaffolds:
            rs.instanceUpdated.connect(contour._reportingScaffoldUpdated)

        return contour

    def toElement(self):
        string =   ('<contour xmlns="http://www.baramcfd.org/baram">'
                   f'    <uuid>{str(self.uuid)}</uuid>'
                   f'    <name>{self.name}</name>'
                   f'    <fieldCategory>{self.field.category}</fieldCategory>'
                   f'    <fieldCodeName>{self.field.codeName}</fieldCodeName>'
                   f'    <fieldComponent>{self.fieldComponent.value}</fieldComponent>'
                   f'    <time>{self.time}</time>'
                   f'    <fieldDisplayName>{self.fieldDisplayName}</fieldDisplayName>'
                   f'    <numberOfLevels>{str(self.numberOfLevels)}</numberOfLevels>'
                   f'    <useNodeValues>{"true" if self.useNodeValues else "false"}</useNodeValues>'
                   f'    <relevantScaffoldsOnly>{"true" if self.relevantScaffoldsOnly else "false"}</relevantScaffoldsOnly>'
                   f'    <useCustomRange>{"true" if self.useCustomRange else "false"}</useCustomRange>'
                   f'    <customRangeMin>{self.customRangeMin}</customRangeMin>'
                   f'    <customRangeMax>{self.customRangeMax}</customRangeMax>'
                   f'    <clipToRange>{"true" if self.clipToRange else "false"}</clipToRange>'
                   f'    <useCustomColorScheme>{"true" if self.useCustomColorScheme else "false"}</useCustomColorScheme>'
                   f'    <colorScheme>{str(self.colorScheme.value)}</colorScheme>'
                   f'    <customMinColor>{self.customMinColor.name()}</customMinColor>'
                   f'    <customMaxColor>{self.customMaxColor.name()}</customMaxColor>'
                   f'    <includeVectors>{"true" if self.includeVectors else "false"}</includeVectors>'
                   f'    <vectorFieldCategory>{self.vectorField.category}</vectorFieldCategory>'
                   f'    <vectorFieldCodeName>{self.vectorField.codeName}</vectorFieldCodeName>'
                   f'    <vectorScaleFactor>{self.vectorScaleFactor}</vectorScaleFactor>'
                   f'    <vectorOnRatio>{str(self.vectorOnRatio)}</vectorOnRatio>'
                   f'    <vectorNumMax>{str(self.vectorNumMax)}</vectorNumMax>'
                   f'    <scaffolds/>'
                   f'</contour>')

        element = etree.fromstring(string)

        scaffoldsElement = element.find('scaffolds', namespaces=nsmap)

        for rs in self.reportingScaffolds.values():
            scaffoldsElement.append(rs.toElement())

        return etree.fromstring(string)

    def xpath(self):
        return f'/contour[uuid="{str(self.uuid)}"]'

    def _saveToCoreDB(self):
        coredb.CoreDB().removeElement(self.VISUAL_REPORTS_PATH + self.xpath())
        coredb.CoreDB().addElement(self.VISUAL_REPORTS_PATH, self.toElement())

    def _reportingScaffoldUpdated(self, scaffold: UUID):
        self._saveToCoreDB()