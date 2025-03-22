#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar
from uuid import UUID

from PySide6.QtGui import QColor
from lxml import etree
from vtkmodules.vtkFiltersFlowPaths import vtkStreamTracer

from baramFlow.coredb import coredb
from baramFlow.coredb.reporting_scaffold import ReportingScaffold
from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.post_field import FIELD_TEXTS, VELOCITY, Field, FieldType, VectorComponent, getFieldInstance
from baramFlow.coredb.visual_report import VisualReport
from baramFlow.coredb.color_scheme import ColormapScheme


class StreamlineIntegratorType(Enum):
    RUNGE_KUTTA2 = 'rungeKutta2'
    RUNGE_KUTTA4 = 'rungeKutta4'
    RUNGE_KUTTA45 = 'rungeKutta45'

    @property
    def vtkType(self):
        if self == StreamlineIntegratorType.RUNGE_KUTTA2:
            return vtkStreamTracer.RUNGE_KUTTA2
        elif self == StreamlineIntegratorType.RUNGE_KUTTA4:
            return vtkStreamTracer.RUNGE_KUTTA4
        elif self == StreamlineIntegratorType.RUNGE_KUTTA45:
            return vtkStreamTracer.RUNGE_KUTTA45
        else:
            raise AssertionError


class StreamlineType(Enum):
    LINE = 'line'
    RIBBON = 'ribbon'


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

    integrateForward: bool = True
    integrateBackward: bool = False
    stepSize: str = '0.001'
    maxSteps: int = 2000
    maxLength: str = '1.0'
    accuracyControl: bool = False
    tolerance: str = '1.0e-6'
    streamlineType: StreamlineType = StreamlineType.RIBBON
    lineWidth: str = '0.01'

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

        integrateForward = True if e.find('integrateForward', namespaces=nsmap).text == 'true' else False
        integrateBackward = True if e.find('integrateBackward', namespaces=nsmap).text == 'true' else False
        stepSize = e.find('stepSize', namespaces=nsmap).text
        maxSteps = int(e.find('maxSteps', namespaces=nsmap).text)
        maxLength = e.find('maxLength', namespaces=nsmap).text
        accuracyControl = True if e.find('accuracyControl', namespaces=nsmap).text == 'true' else False
        tolerance = e.find('tolerance', namespaces=nsmap).text
        streamlineType = StreamlineType(e.find('streamlineType', namespaces=nsmap).text)
        lineWidth = e.find('lineWidth', namespaces=nsmap).text

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
                          reportingScaffolds=reportingScaffolds,
                          integrateForward=integrateForward,
                          integrateBackward=integrateBackward,
                          stepSize=stepSize,
                          maxSteps=maxSteps,
                          maxLength=maxLength,
                          accuracyControl=accuracyControl,
                          tolerance=tolerance,
                          streamlineType=streamlineType,
                          lineWidth=lineWidth)

        for rs in reportingScaffolds.values():
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
                   f'    <integrateForward>{"true" if self.integrateForward else "false"}</integrateForward>'
                   f'    <integrateBackward>{"true" if self.integrateBackward else "false"}</integrateBackward>'
                   f'    <stepSize>{self.stepSize}</stepSize>'
                   f'    <maxSteps>{str(self.maxSteps)}</maxSteps>'
                   f'    <maxLength>{self.maxLength}</maxLength>'
                   f'    <accuracyControl>{"true" if self.accuracyControl else "false"}</accuracyControl>'
                   f'    <tolerance>{self.tolerance}</tolerance>'
                   f'    <streamlineType>{self.streamlineType.value}</streamlineType>'
                   f'    <lineWidth>{self.lineWidth}</lineWidth>'
                   f'    <scaffolds/>'
                   f'</contour>')

        element = etree.fromstring(string)

        scaffoldsElement = element.find('scaffolds', namespaces=nsmap)

        for rs in self.reportingScaffolds.values():
            scaffoldsElement.append(rs.toElement())

        return element

    def xpath(self):
        return f'/contour[uuid="{str(self.uuid)}"]'

    def _saveToCoreDB(self):
        coredb.CoreDB().removeElement(self.VISUAL_REPORTS_PATH + self.xpath())
        coredb.CoreDB().addElement(self.VISUAL_REPORTS_PATH, self.toElement())

    def _reportingScaffoldUpdated(self, scaffold: UUID):
        self._saveToCoreDB()

    def notifyReportingScaffoldAdded(self, uuid: UUID):
        super().notifyReportingScaffoldAdded(uuid)
        self._saveToCoreDB()

    def notifyReportingScaffoldRemoved(self, uuid: UUID):
        super().notifyReportingScaffoldRemoved(uuid)
        self._saveToCoreDB()

    def getValueRange(self, useNodeValues: bool, relevantScaffoldsOnly: bool) -> tuple[float, float]:
        if len(self.reportingScaffolds) == 0:
            return 0, 1

        rMin = float('inf')
        rMax = float('-inf')

        for rs in self.reportingScaffolds.values():
            if relevantScaffoldsOnly:
                if  not rs.visibility or rs.solidColor:
                    continue

            if self.field.type == FieldType.VECTOR:
                valueRange = rs.getVectorRange(self.field, self.fieldComponent, useNodeValues)
            else:
                valueRange = rs.getScalarRange(self.field, useNodeValues)

            rMin = min(rMin, valueRange[0])
            rMax = max(rMax, valueRange[1])

        return rMin, rMax

