#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from uuid import UUID

from lxml import etree

from vtkmodules.vtkCommonDataModel import vtkDataObject, vtkMultiBlockDataSet, vtkPlane, vtkPolyData, vtkSphere
from vtkmodules.vtkFiltersCore import vtkAppendPolyData, vtkContourFilter, vtkCutter

from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.post_field import COORDINATE, Field, VectorComponent, getFieldInstance
from baramFlow.coredb.post_field import VELOCITY
from baramFlow.coredb.scaffold import Scaffold
from baramFlow.openfoam.solver_field import getSolverFieldName
from libbaram.openfoam.polymesh import collectInternalMesh
from libbaram.vtk_threads import holdRendering, resumeRendering, to_vtk_thread
from libbaram import vtk_threads


@dataclass
class IsoSurface(Scaffold):
    field: Field = VELOCITY
    vectorComponent: VectorComponent = VectorComponent.MAGNITUDE
    isoValues: str = '0'
    surfacePerValue: int = 1
    spacing: str = '1'

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text
        fieldCategory = e.find('fieldCategory', namespaces=nsmap).text
        fieldCodeName = e.find('fieldCodeName', namespaces=nsmap).text
        field = getFieldInstance(fieldCategory, fieldCodeName)
        vectorComponent = VectorComponent(int(e.find('vectorComponent', namespaces=nsmap).text))
        isoValues = e.find('isoValues', namespaces=nsmap).text
        surfacePerValue = int(e.find('surfacesPerValue', namespaces=nsmap).text)
        spacing = e.find('spacing', namespaces=nsmap).text

        return IsoSurface(uuid=uuid,
                          name=name,
                          field=field,
                          vectorComponent=vectorComponent,
                          isoValues=isoValues,
                          surfacePerValue=surfacePerValue,
                          spacing=spacing)

    def toElement(self):
        string = ('<surface xmlns="http://www.baramcfd.org/baram">'
                 f'    <uuid>{str(self.uuid)}</uuid>'
                 f'    <name>{self.name}</name>'
                 f'    <fieldCategory>{self.field.category}</fieldCategory>'
                 f'    <fieldCodeName>{self.field.codeName}</fieldCodeName>'
                 f'    <vectorComponent>{self.vectorComponent.value}</vectorComponent>'
                 f'    <isoValues>{self.isoValues}</isoValues>'
                 f'    <surfacesPerValue>{self.surfacePerValue}</surfacesPerValue>'
                 f'    <spacing>{self.spacing}</spacing>'
                  '</surface>')
        return etree.fromstring(string)

    def xpath(self):
        return f'/surface[uuid="{str(self.uuid)}"]'

    async def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        values = self._getValues()
        mesh = collectInternalMesh(mBlock)

        if self.field == COORDINATE:
            if self.vectorComponent == VectorComponent.MAGNITUDE:
                cutFunction = vtkSphere()
                cutFunction.SetCenter(0, 0, 0)
                cutFunction.SetRadius(0)
            else:
                cutFunction = vtkPlane()
                cutFunction.SetOrigin(0, 0, 0)
                if self.vectorComponent == VectorComponent.X:
                    cutFunction.SetNormal(1, 0, 0)
                elif self.vectorComponent == VectorComponent.Y:
                    cutFunction.SetNormal(0, 1, 0)
                elif self.vectorComponent == VectorComponent.Z:
                    cutFunction.SetNormal(0, 0, 1)
                else:  # ToDo: jake, How to handle this? Magnitude? Is it necessary?
                    cutFunction.SetNormal(1, 0, 0)

            filter = vtkCutter()
            filter.SetInputData(mesh)
            filter.SetCutFunction(cutFunction)
        else:
            filter = vtkContourFilter()
            filter.SetInputData(mesh)
            solverFieldName = getSolverFieldName(self.field)
            filter.SetInputArrayToProcess(0, 0, 0,
                                            vtkDataObject.FIELD_ASSOCIATION_POINTS,
                                            solverFieldName)

        for i, v in enumerate(values):
            filter.SetValue(i, v)

        async with vtk_threads.vtkThreadLock:
            holdRendering()
            await to_vtk_thread(filter.Update)
            resumeRendering()

        return filter.GetOutput()

    def _getValues(self):
        values: list[float] = []

        for s in self.isoValues.split():
            v = float(s)
            for i in range(int(self.surfacePerValue)):
                values.append(v + i * float(self.spacing))

        return sorted(values)
