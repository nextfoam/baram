#!/usr/bin/env python
# -*- coding: utf-8 -*-


from vtkmodules.vtkCommonCore import vtkDataArray
from vtkmodules.vtkCommonDataModel import vtkDataSet
from vtkmodules.vtkFiltersCore import vtkArrayCalculator

from baramFlow.coredb.post_field import Field, VectorComponent
from baramFlow.openfoam.solver_field import getSolverFieldName


def getVectorRange(dataSet: vtkDataSet, field: Field, vectorComponent: VectorComponent, useNodeValues: bool) -> tuple[float, float]:
    solverFieldName = getSolverFieldName(field)
    if useNodeValues:
        vectors: vtkDataArray = dataSet.GetPointData().GetVectors(solverFieldName)
    else:
        vectors: vtkDataArray = dataSet.GetCellData().GetVectors(solverFieldName)

    if not vectors:
        return (0, 1)

    if vectorComponent == VectorComponent.MAGNITUDE:
        filter = vtkArrayCalculator()
        filter.SetInputData(dataSet)
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


def getScalarRange(dataSet: vtkDataSet, field: Field, useNodeValues: bool) -> tuple[float, float]:
    solverFieldName = getSolverFieldName(field)
    if useNodeValues:
        scalars: vtkDataArray = dataSet.GetPointData().GetScalars(solverFieldName)
    else:
        scalars: vtkDataArray = dataSet.GetCellData().GetScalars(solverFieldName)

    if scalars:
        return scalars.GetRange()
    else:
        return (0, 1)

