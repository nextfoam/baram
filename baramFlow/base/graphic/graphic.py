#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from dataclasses import field as dataClassField
from enum import Enum
from typing import ClassVar
from uuid import UUID

from PySide6.QtGui import QColor
from lxml import etree

from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkUnstructuredGrid
from vtkmodules.vtkFiltersFlowPaths import vtkStreamTracer

from baramFlow.base.constants import FieldCategory, FieldType, VectorComponent
from baramFlow.base.field import COORDINATE, VECTOR_COMPONENT_TEXTS, VELOCITY, Field, getFieldInstance
from baramFlow.base.scaffold.scaffolds_db import ScaffoldsDB
from baramFlow.coredb import coredb
from baramFlow.base.graphic.display_item import DisplayItem
from baramFlow.coredb.libdb import nsmap
from baramFlow.base.graphic.color_scheme import ColormapScheme
from baramFlow.openfoam.openfoam_reader import OpenFOAMReader
from baramFlow.openfoam.solver_field import getSolverFieldName
from libbaram.async_signal import AsyncSignal
from libbaram.openfoam.polymesh import addCoordinateVector, collectInternalMesh


class StreamlineIntegratorType(Enum):
    RUNGE_KUTTA2  = 'rungeKutta2'
    RUNGE_KUTTA4  = 'rungeKutta4'
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


@dataclass(kw_only=True)
class Graphic:
    GRAPHICS_PATH: ClassVar[str] = '/graphics'

    instanceUpdated: AsyncSignal = dataClassField(init=False)
    displayItemAdded: AsyncSignal = dataClassField(init=False)
    displayItemRemoving: AsyncSignal = dataClassField(init=False)
    displayItemRemoved: AsyncSignal = dataClassField(init=False)

    uuid: UUID
    name: str

    time: str = '0'

    # Not a configuration, Not saved in CoreDB
    polyMesh: vtkMultiBlockDataSet = None

    # Not a configuration, Not saved in CoreDB.
    # It is calculated and stored for caching.
    internalMesh: vtkUnstructuredGrid = None

    displayItems: dict[UUID, DisplayItem] = dataClassField(default_factory=dict)
    field: Field = VELOCITY
    fieldComponent: VectorComponent = VectorComponent.MAGNITUDE

    fieldDisplayName: str = ''
    numberOfLevels: int = 256
    useNodeValues: bool = True
    relevantScaffoldsOnly: bool = False
    useCustomRange: bool = False
    customRangeMin: str = '0.0'
    customRangeMax: str = '0.0'
    clipToRange: bool = False
    useCustomColorScheme: bool = False
    colorScheme: ColormapScheme = ColormapScheme.BlueToRedRainbow
    customMinColor: QColor = dataClassField(default_factory=lambda: QColor.fromString('#000000'))
    customMaxColor: QColor = dataClassField(default_factory=lambda: QColor.fromString('#FFFFFF'))

    includeVectors: bool = False
    vectorField: Field = VELOCITY
    vectorScaleFactor: str = '1.0'
    vectorNumMax: int = 1000
    vectorFixedLength: bool = False

    stepSize: str = '0.1'
    maxSteps: int = 2000
    maxLength: str = '10.0'
    accuracyControl: bool = False
    tolerance: str = '1.0e-6'
    streamlineType: StreamlineType = StreamlineType.RIBBON
    lineWidth: str = '0.01'

    rangeMin: float = 0  # Not a configuration, Not saved in CoreDB
    rangeMax: float = 0  # Not a configuration, Not saved in CoreDB

    def __post_init__(self):
        self.instanceUpdated = AsyncSignal(UUID)
        self.displayItemAdded = AsyncSignal(UUID)
        self.displayItemRemoving = AsyncSignal(UUID)
        self.displayItemRemoved = AsyncSignal(UUID)
        if not self.fieldDisplayName:  # this means empty string ('')
            self.fieldDisplayName = self.getDefaultFieldDisplayName()

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text

        fieldCategory = FieldCategory(e.find('fieldCategory', namespaces=nsmap).text)
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
        colorScheme = ColormapScheme(e.find('colorScheme', namespaces=nsmap).text)
        customMinColor = QColor.fromString(e.find('customMinColor', namespaces=nsmap).text)
        customMaxColor = QColor.fromString(e.find('customMaxColor', namespaces=nsmap).text)

        includeVectors = True if e.find('includeVectors', namespaces=nsmap).text == 'true' else False
        vectorFieldCategory = FieldCategory(e.find('vectorFieldCategory', namespaces=nsmap).text)
        vectorFieldCodeName = e.find('vectorFieldCodeName', namespaces=nsmap).text
        vectorField = getFieldInstance(vectorFieldCategory, vectorFieldCodeName)
        vectorScaleFactor = e.find('vectorScaleFactor', namespaces=nsmap).text
        vectorNumMax = int(e.find('vectorNumMax', namespaces=nsmap).text)
        vectorFixedLength = True if e.find('vectorFixedLength', namespaces=nsmap).text == 'true' else False

        stepSize = e.find('stepSize', namespaces=nsmap).text
        maxSteps = int(e.find('maxSteps', namespaces=nsmap).text)
        maxLength = e.find('maxLength', namespaces=nsmap).text
        accuracyControl = True if e.find('accuracyControl', namespaces=nsmap).text == 'true' else False
        tolerance = e.find('tolerance', namespaces=nsmap).text
        streamlineType = StreamlineType(e.find('streamlineType', namespaces=nsmap).text)
        lineWidth = e.find('lineWidth', namespaces=nsmap).text

        displayItemsElement = e.find('displayItems', namespaces=nsmap)

        displayItems: dict[UUID, DisplayItem] = {}
        for displayItemElement in displayItemsElement.findall('displayItem', namespaces=nsmap):
            item = DisplayItem.fromElement(displayItemElement)
            displayItems[item.scaffoldUuid] = item

        graphic = Graphic(uuid=uuid,
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
                          vectorNumMax=vectorNumMax,
                          vectorFixedLength=vectorFixedLength,
                          displayItems=displayItems,
                          stepSize=stepSize,
                          maxSteps=maxSteps,
                          maxLength=maxLength,
                          accuracyControl=accuracyControl,
                          tolerance=tolerance,
                          streamlineType=streamlineType,
                          lineWidth=lineWidth)

        for item in displayItems.values():
            item.instanceUpdated.asyncConnect(graphic._displayItemUpdated)

        return graphic

    def toElement(self):
        string =   ('<graphic xmlns="http://www.baramcfd.org/baram">'
                   f'    <uuid>{str(self.uuid)}</uuid>'
                   f'    <name>{self.name}</name>'
                   f'    <fieldCategory>{self.field.category.value}</fieldCategory>'
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
                   f'    <colorScheme>{self.colorScheme.value}</colorScheme>'
                   f'    <customMinColor>{self.customMinColor.name()}</customMinColor>'
                   f'    <customMaxColor>{self.customMaxColor.name()}</customMaxColor>'
                   f'    <includeVectors>{"true" if self.includeVectors else "false"}</includeVectors>'
                   f'    <vectorFieldCategory>{self.vectorField.category.value}</vectorFieldCategory>'
                   f'    <vectorFieldCodeName>{self.vectorField.codeName}</vectorFieldCodeName>'
                   f'    <vectorScaleFactor>{self.vectorScaleFactor}</vectorScaleFactor>'
                   f'    <vectorNumMax>{str(self.vectorNumMax)}</vectorNumMax>'
                   f'    <vectorFixedLength>{"true" if self.vectorFixedLength else "false"}</vectorFixedLength>'
                   f'    <stepSize>{self.stepSize}</stepSize>'
                   f'    <maxSteps>{str(self.maxSteps)}</maxSteps>'
                   f'    <maxLength>{self.maxLength}</maxLength>'
                   f'    <accuracyControl>{"true" if self.accuracyControl else "false"}</accuracyControl>'
                   f'    <tolerance>{self.tolerance}</tolerance>'
                   f'    <streamlineType>{self.streamlineType.value}</streamlineType>'
                   f'    <lineWidth>{self.lineWidth}</lineWidth>'
                   f'    <displayItems/>'
                   f'</graphic>')

        element = etree.fromstring(string)

        scaffoldsElement = element.find('displayItems', namespaces=nsmap)

        for item in self.displayItems.values():
            scaffoldsElement.append(item.toElement())

        return element

    def xpath(self):
        return f'/graphic[uuid="{str(self.uuid)}"]'

    def saveToCoreDB(self):
        coredb.CoreDB().removeElement(self.GRAPHICS_PATH + self.xpath())
        coredb.CoreDB().addElement(self.GRAPHICS_PATH, self.toElement())

    async def _displayItemUpdated(self, scaffold: UUID):
        self.saveToCoreDB()

    async def notifyReportUpdated(self):
        self.saveToCoreDB()
        await self.instanceUpdated.emit(self.uuid)

    def getValueRange(self, useNodeValues: bool, relevantScaffoldsOnly: bool) -> tuple[float, float]:
        if len(self.displayItems) == 0:
            return 0, 1

        rMin = float('inf')
        rMax = float('-inf')

        for item in self.displayItems.values():
            if relevantScaffoldsOnly:
                if  not item.visibility or item.solidColor:
                    continue

            if self.field.type == FieldType.VECTOR:
                valueRange = item.getVectorRange(self.field, self.fieldComponent, useNodeValues)
            else:
                valueRange = item.getScalarRange(self.field, useNodeValues)

            rMin = min(rMin, valueRange[0])
            rMax = max(rMax, valueRange[1])

        if rMin == float('inf') or rMax == float('-inf'):
            return 0, 1

        return rMin, rMax

    async def updatePolyMesh(self):
        async with OpenFOAMReader() as reader:
            reader.setTimeValue(float(self.time))
            await reader.update()
            mBlock = reader.getOutput()

        coordsFieldName = getSolverFieldName(COORDINATE)
        self.polyMesh = await addCoordinateVector(mBlock, coordsFieldName)
        self.internalMesh = await collectInternalMesh(self.polyMesh)

        for item in self.displayItems.values():
            scaffold = ScaffoldsDB().getScaffold(item.scaffoldUuid)
            item.dataSet = await scaffold.getDataSet(self.polyMesh)

        self.rangeMin, self.rangeMax = self.getValueRange(self.useNodeValues, self.relevantScaffoldsOnly)

        await self.instanceUpdated.emit(self.uuid)

    def getDefaultFieldDisplayName(self) -> str:
        if self.field.type == FieldType.VECTOR:
            return f'{self.field.text} ({VECTOR_COMPONENT_TEXTS[self.fieldComponent]})'
        else:
            return self.field.text

    def hasScaffold(self, scaffoldUuid: UUID) -> bool:
        return scaffoldUuid in self.displayItems

    def getScaffolds(self) -> list[UUID]:
        return list(self.displayItems.keys())

    def getDisplayItem(self, scaffoldUuid: UUID) -> DisplayItem:
        return self.displayItems[scaffoldUuid]

    async def addDisplayItem(self, item: DisplayItem):
        self.displayItems[item.scaffoldUuid] = item
        item.instanceUpdated.asyncConnect(self._displayItemUpdated)
        await self.displayItemAdded.emit(item.scaffoldUuid)
        self.saveToCoreDB()

    async def removeDisplayItem(self, scaffoldUuid: UUID):
        await self.displayItemRemoving.emit(scaffoldUuid)
        del self.displayItems[scaffoldUuid]
        await self.displayItemRemoved.emit(scaffoldUuid)
        self.saveToCoreDB()
