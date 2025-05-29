#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from uuid import UUID

from lxml import etree

from vtkmodules.vtkCommonDataModel import vtkDataObject, vtkMultiBlockDataSet, vtkPlane, vtkPolyData, vtkSphere
from vtkmodules.vtkFiltersCore import vtkArrayCalculator, vtkContourFilter, vtkCutter

from baramFlow.coredb import coredb
from baramFlow.coredb.libdb import nsmap
from baramFlow.base.field import COORDINATE, Field, FieldCategory, FieldType, VectorComponent, getFieldInstance
from baramFlow.base.field import VELOCITY
from baramFlow.base.scaffold.scaffold import Scaffold
from baramFlow.openfoam.solver_field import getSolverFieldName
from libbaram.openfoam.polymesh import collectInternalMesh
from libbaram.vtk_threads import vtk_run_in_thread


@dataclass
class IsoSurface(Scaffold):
    field: Field = VELOCITY
    fieldComponent: VectorComponent = VectorComponent.MAGNITUDE
    isoValues: str = '0'
    surfacePerValue: int = 1
    spacing: str = '1'

    @classmethod
    def parseScaffolds(cls) -> dict[UUID, Scaffold]:
        scaffolds: dict[UUID, Scaffold] = {}

        for e in coredb.CoreDB().getElements(Scaffold.SCAFFOLDS_PATH + '/isoSurfaces/surface'):
            s = IsoSurface.fromElement(e)
            scaffolds[s.uuid] = s

        return scaffolds

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text
        fieldCategory = FieldCategory(e.find('fieldCategory', namespaces=nsmap).text)
        fieldCodeName = e.find('fieldCodeName', namespaces=nsmap).text
        field = getFieldInstance(fieldCategory, fieldCodeName)
        fieldComponent = VectorComponent(int(e.find('fieldComponent', namespaces=nsmap).text))
        isoValues = e.find('isoValues', namespaces=nsmap).text
        surfacePerValue = int(e.find('surfacesPerValue', namespaces=nsmap).text)
        spacing = e.find('spacing', namespaces=nsmap).text

        return IsoSurface(uuid=uuid,
                          name=name,
                          field=field,
                          fieldComponent=fieldComponent,
                          isoValues=isoValues,
                          surfacePerValue=surfacePerValue,
                          spacing=spacing)

    def toElement(self):
        string = ('<surface xmlns="http://www.baramcfd.org/baram">'
                 f'    <uuid>{str(self.uuid)}</uuid>'
                 f'    <name>{self.name}</name>'
                 f'    <fieldCategory>{self.field.category.value}</fieldCategory>'
                 f'    <fieldCodeName>{self.field.codeName}</fieldCodeName>'
                 f'    <fieldComponent>{self.fieldComponent.value}</fieldComponent>'
                 f'    <isoValues>{self.isoValues}</isoValues>'
                 f'    <surfacesPerValue>{self.surfacePerValue}</surfacesPerValue>'
                 f'    <spacing>{self.spacing}</spacing>'
                  '</surface>')
        return etree.fromstring(string)

    def xpath(self):
        return f'/surface[uuid="{str(self.uuid)}"]'

    def addElement(self):
        coredb.CoreDB().addElement(Scaffold.SCAFFOLDS_PATH + '/isoSurfaces', self.toElement())

    def removeElement(self):
        coredb.CoreDB().removeElement(Scaffold.SCAFFOLDS_PATH + '/isoSurfaces' + self.xpath())

    async def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        values = self._getValues()
        mesh = await collectInternalMesh(mBlock)

        solverFieldName = getSolverFieldName(self.field)
        contour = vtkContourFilter()
        contour.ComputeNormalsOn()
        contour.GenerateTrianglesOn()
        if self.field.type == FieldType.VECTOR:
            calc = vtkArrayCalculator()
            calc.ReplaceInvalidValuesOn()
            calc.SetReplacementValue(0.0)
            calc.SetInputData(mesh)
            calc.SetAttributeTypeToPointData()
            if self.fieldComponent == VectorComponent.MAGNITUDE:
                calc.AddVectorArrayName(solverFieldName)
                calc.SetFunction(f'mag({solverFieldName})')
            else:
                if self.fieldComponent == VectorComponent.X:
                    componentIndex = 0
                elif self.fieldComponent == VectorComponent.Y:
                    componentIndex = 1
                elif self.fieldComponent == VectorComponent.Z:
                    componentIndex = 2
                else:
                    componentIndex = 0
                calc.AddScalarVariable('component', solverFieldName, componentIndex)
                calc.SetFunction('component')

            calc.SetResultArrayName('isoScalar')
            contour.SetInputConnection(calc.GetOutputPort())
            contour.SetInputArrayToProcess(0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, 'isoScalar')
        else:  # FieldType.SCALAR
            contour.SetInputData(mesh)
            contour.SetInputArrayToProcess(0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, solverFieldName)

        for i, v in enumerate(values):
            contour.SetValue(i, v)

        await vtk_run_in_thread(contour.Update)

        return contour.GetOutput()

    def _getValues(self):
        values: list[float] = []

        for s in self.isoValues.split():
            v = float(s)
            for i in range(int(self.surfacePerValue)):
                values.append(v + i * float(self.spacing))

        return sorted(values)
