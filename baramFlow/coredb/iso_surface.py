#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from uuid import UUID

from lxml import etree

from vtkmodules.vtkCommonDataModel import vtkDataObject, vtkMultiBlockDataSet, vtkPlane, vtkPolyData
from vtkmodules.vtkFiltersCore import vtkAppendPolyData, vtkContourFilter, vtkCutter

from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.post_field import Field, getFieldInstance
from baramFlow.coredb.post_field import X_VELOCITY, X_COORDINATE, Y_COORDINATE, Z_COORDINATE
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

    def xpath(self):
        return f'/surface[uuid="{str(self.uuid)}"]'

    def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        values = self._getValues()
        polyData = vtkAppendPolyData()
        meshes = self._collectInternalMesh(mBlock)

        for mesh in meshes:
            if self.field in [X_COORDINATE, Y_COORDINATE, Z_COORDINATE]:
                plane = vtkPlane()
                plane.SetOrigin(0, 0, 0)
                if self.field == X_COORDINATE:
                    plane.SetNormal(1, 0, 0)
                elif self.field == Y_COORDINATE:
                    plane.SetNormal(0, 1, 0)
                elif self.field == Z_COORDINATE:
                    plane.SetNormal(0, 0, 1)

                filter = vtkCutter()
                filter.SetInputData(mesh)
                filter.SetCutFunction(plane)
            else:
                filter = vtkContourFilter()
                filter.SetInputData(mesh)

                filter.SetInputArrayToProcess(0, 0, 0,
                                                vtkDataObject.FIELD_ASSOCIATION_POINTS,
                                                self.field.name)

            for i, v in enumerate(values):
                filter.SetValue(i, v)

            filter.Update()

            polyData.AddInputData(filter.GetOutput())

        polyData.Update()

        return polyData.GetOutput()

    def _getValues(self):
        values: list[float] = []

        for s in self.isoValues.split():
            v = float(s)
            for i in range(int(self.surfacePerValue)):
                values.append(v + i * float(self.spacing))

        return sorted(values)
