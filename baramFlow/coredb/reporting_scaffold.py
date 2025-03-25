#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import ClassVar

from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkCommonCore import vtkDataArray
from vtkmodules.vtkCommonDataModel import vtkDataSet
from vtkmodules.vtkFiltersCore import vtkArrayCalculator
from baramFlow.coredb.libdb import nsmap

from PySide6.QtGui import QColor
from lxml import etree


from dataclasses import dataclass
from uuid import UUID

from baramFlow.coredb.post_field import Field, VectorComponent
from baramFlow.coredb.scaffolds_db import ScaffoldsDB
from baramFlow.openfoam.solver_field import getSolverFieldName


@dataclass
class ReportingScaffold(QObject):
    instanceUpdated: ClassVar[Signal] = Signal(UUID)

    scaffoldUuid: UUID  = UUID(int = 0)
    dataSet: vtkDataSet = None

    visibility: bool = True
    opacity: float = 0.9
    solidColor: bool = False
    color: QColor = QColor.fromString('#FFFFFF')
    edges: bool = False
    faces: bool = True
    showVectors: bool = False
    showStreamlines: bool = False
    maxNumberOfSamplePoints: int = 100
    streamlinesIntegrateForward: bool = True
    streamlinesIntegrateBackward: bool = False

    def __post_init__(self):
        super().__init__()

    @classmethod
    def fromElement(cls, e):
        scaffoldUuid = UUID(e.find('scaffoldUuid', namespaces=nsmap).text)
        visibility = (e.find('visibility', namespaces=nsmap).text == 'true')
        opacity = float(e.find('opacity', namespaces=nsmap).text)
        solidColor = (e.find('solidColor', namespaces=nsmap).text == 'true')
        color = QColor.fromString(e.find('color', namespaces=nsmap).text)
        edges = (e.find('edges', namespaces=nsmap).text == 'true')
        faces = (e.find('faces', namespaces=nsmap).text == 'true')
        showVectors = (e.find('showVectors', namespaces=nsmap).text == 'true')
        showStreamlines = (e.find('showStreamlines', namespaces=nsmap).text == 'true')
        maxNumberOfSamplePoints = int(e.find('maxNumberOfSamplePoints', namespaces=nsmap).text)
        streamlinesIntegrateForward = True if e.find('streamlinesIntegrateForward', namespaces=nsmap).text == 'true' else False
        streamlinesIntegrateBackward = True if e.find('streamlinesIntegrateBackward', namespaces=nsmap).text == 'true' else False


        return ReportingScaffold(scaffoldUuid=scaffoldUuid,
                          visibility=visibility,
                          opacity=opacity,
                          solidColor=solidColor,
                          color=color,
                          edges=edges,
                          faces=faces,
                          showVectors=showVectors,
                          showStreamlines=showStreamlines,
                          maxNumberOfSamplePoints=maxNumberOfSamplePoints,
                          streamlinesIntegrateForward=streamlinesIntegrateForward,
                          streamlinesIntegrateBackward=streamlinesIntegrateBackward)

    def toElement(self):
        string = (f'<scaffold xmlns="http://www.baramcfd.org/baram">'
                  f'    <scaffoldUuid>{str(self.scaffoldUuid)}</scaffoldUuid>'
                  f'    <visibility>{"true" if self.visibility else "false"}</visibility>'
                  f'    <opacity>{str(self.opacity)}</opacity>'
                  f'    <solidColor>{"true" if self.solidColor else "false"}</solidColor>'
                  f'    <color>{self.color.name()}</color>'
                  f'    <edges>{"true" if self.edges else "false"}</edges>'
                  f'    <faces>{"true" if self.faces else "false"}</faces>'
                  f'    <showVectors>{"true" if self.showVectors else "false"}</showVectors>'
                  f'    <showStreamlines>{"true" if self.showStreamlines else "false"}</showStreamlines>'
                  f'    <maxNumberOfSamplePoints>{str(self.maxNumberOfSamplePoints)}</maxNumberOfSamplePoints>'
                  f'    <streamlinesIntegrateForward>{"true" if self.streamlinesIntegrateForward else "false"}</streamlinesIntegrateForward>'
                  f'    <streamlinesIntegrateBackward>{"true" if self.streamlinesIntegrateBackward else "false"}</streamlinesIntegrateBackward>'
                  f'</scaffold>')

        return etree.fromstring(string)

    def markUpdated(self):
        self.instanceUpdated.emit(self.scaffoldUuid)

    @property
    def name(self):
        scaffold = ScaffoldsDB().getScaffold(self.scaffoldUuid)
        return scaffold.name

    def getScalarRange(self, field: Field, useNodeValues: bool) -> tuple[float, float]:
        solverFieldName = getSolverFieldName(field)
        if useNodeValues:
            scalars: vtkDataArray = self.dataSet.GetPointData().GetScalars(solverFieldName)
        else:
            scalars: vtkDataArray = self.dataSet.GetCellData().GetScalars(solverFieldName)

        if scalars:
            return scalars.GetRange()
        else:
            return (0, 1)

    def getVectorRange(self, field: Field, vectorComponent: VectorComponent, useNodeValues: bool) -> tuple[float, float]:
        solverFieldName = getSolverFieldName(field)
        if useNodeValues:
            vectors: vtkDataArray = self.dataSet.GetPointData().GetVectors(solverFieldName)
        else:
            vectors: vtkDataArray = self.dataSet.GetCellData().GetVectors(solverFieldName)

        if not vectors:
            return (0, 1)

        if vectorComponent == VectorComponent.MAGNITUDE:
            filter = vtkArrayCalculator()
            filter.SetInputData(self.dataSet)
            if useNodeValues:
                filter.SetAttributeTypeToPointData()
            else:
                filter.SetAttributeTypeToCellData()
            filter.AddVectorArrayName(solverFieldName)
            filter.SetFunction(f'mag({solverFieldName})')
            RESULT_ARRAY_NAME = 'magnitude'
            filter.SetResultArrayName(RESULT_ARRAY_NAME)
            filter.Update()
            if useNodeValues:
                scalars: vtkDataArray = filter.GetOutput().GetPointData().GetScalars(RESULT_ARRAY_NAME)
            else:
                scalars: vtkDataArray = filter.GetOutput().GetCellData().GetScalars(RESULT_ARRAY_NAME)

            if scalars:
                return scalars.GetRange()
            else:
                return (0, 1)

        elif vectorComponent == VectorComponent.X:
            return vectors.GetRange(0)
        elif vectorComponent == VectorComponent.Y:
            return vectors.GetRange(1)
        elif vectorComponent == VectorComponent.Z:
            return vectors.GetRange(2)
