#!/usr/bin/env python
# -*- coding: utf-8 -*-


from vtkmodules.vtkCommonCore import vtkDataArray, vtkMath
from vtkmodules.vtkCommonDataModel import vtkDataSet
from vtkmodules.vtkFiltersCore import vtkArrayCalculator

from baramFlow.base.constants import VectorComponent
from baramFlow.base.field import Field
from baramFlow.openfoam.solver_field import getSolverFieldName


def getVectorRange(dataSet: vtkDataSet, field: Field, vectorComponent: VectorComponent, useNodeValues: bool) -> tuple[float, float]:
    solverFieldName = getSolverFieldName(field)
    if useNodeValues:
        vectors: vtkDataArray = dataSet.GetPointData().GetVectors(solverFieldName)
    else:
        vectors: vtkDataArray = dataSet.GetCellData().GetVectors(solverFieldName)

    if not vectors:
        return vtkMath.Nan(), vtkMath.Nan()

    if vectorComponent == VectorComponent.MAGNITUDE:
        calculator = vtkArrayCalculator()
        calculator.ReplaceInvalidValuesOn()
        calculator.SetReplacementValue(0.0)
        calculator.SetInputData(dataSet)
        if useNodeValues:
            calculator.SetAttributeTypeToPointData()
        else:
            calculator.SetAttributeTypeToCellData()
        calculator.AddVectorArrayName(solverFieldName)
        calculator.SetFunction(f'mag({solverFieldName})')
        RESULT_ARRAY_NAME = 'magnitude'
        calculator.SetResultArrayName(RESULT_ARRAY_NAME)
        calculator.Update()
        if useNodeValues:
            scalars: vtkDataArray = calculator.GetOutput().GetPointData().GetScalars(RESULT_ARRAY_NAME)
        else:
            scalars: vtkDataArray = calculator.GetOutput().GetCellData().GetScalars(RESULT_ARRAY_NAME)

        if scalars:
            return scalars.GetRange()
        else:
            return vtkMath.Nan(), vtkMath.Nan()

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
        return vtkMath.Nan(), vtkMath.Nan()

