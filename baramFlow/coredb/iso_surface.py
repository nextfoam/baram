#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from uuid import UUID

from lxml import etree

from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkPlane, vtkPolyData, vtkSphere
from vtkmodules.vtkFiltersCore import vtkArrayCalculator, vtkContourFilter, vtkCutter

from baramFlow.coredb import coredb
from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.post_field import COORDINATE, Field, FieldType, VectorComponent, getFieldInstance
from baramFlow.coredb.post_field import VELOCITY
from baramFlow.coredb.scaffold import Scaffold
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
        fieldCategory = e.find('fieldCategory', namespaces=nsmap).text
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
                 f'    <fieldCategory>{self.field.category}</fieldCategory>'
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
        mesh = collectInternalMesh(mBlock)

        if self.field == COORDINATE:
            if self.fieldComponent == VectorComponent.MAGNITUDE:
                cutFunction = vtkSphere()
                cutFunction.SetCenter(0, 0, 0)
                cutFunction.SetRadius(0)
            else:
                cutFunction = vtkPlane()
                cutFunction.SetOrigin(0, 0, 0)
                if self.fieldComponent == VectorComponent.X:
                    cutFunction.SetNormal(1, 0, 0)
                elif self.fieldComponent == VectorComponent.Y:
                    cutFunction.SetNormal(0, 1, 0)
                elif self.fieldComponent == VectorComponent.Z:
                    cutFunction.SetNormal(0, 0, 1)
                else:  # ToDo: jake, How to handle this? Magnitude? Is it necessary?
                    cutFunction.SetNormal(1, 0, 0)

            filter = vtkCutter()
            filter.SetInputData(mesh)
            filter.SetCutFunction(cutFunction)
        else:
            solverFieldName = getSolverFieldName(self.field)
            filter = vtkContourFilter()

            if self.field.type == FieldType.VECTOR:
                mesh.GetPointData().SetActiveVectors(solverFieldName)
                calc = vtkArrayCalculator()
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
                filter.SetInputConnection(calc.GetOutputPort())
            else:  # FieldType.SCALAR
                mesh.GetPointData().SetActiveScalars(solverFieldName)
                filter.SetInputData(mesh)

        for i, v in enumerate(values):
            filter.SetValue(i, v)

        await vtk_run_in_thread(filter.Update)

        return filter.GetOutput()

    def _getValues(self):
        values: list[float] = []

        for s in self.isoValues.split():
            v = float(s)
            for i in range(int(self.surfacePerValue)):
                values.append(v + i * float(self.spacing))

        return sorted(values)
