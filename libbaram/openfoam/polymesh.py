#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from vtkmodules.vtkCommonCore import VTK_MULTIBLOCK_DATA_SET, VTK_POLY_DATA, vtkDataArray, vtkFloatArray, vtkMath
from vtkmodules.vtkCommonDataModel import vtkCompositeDataIterator, vtkCompositeDataSet, vtkDataSet, vtkDataSetAttributes, vtkMultiBlockDataSet, vtkPolyData, vtkUnstructuredGrid
from vtkmodules.vtkFiltersCore import vtkAppendFilter, vtkAppendPolyData, vtkArrayCalculator, vtkPointDataToCellData

from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict, ParsedParameterFile

from libbaram.openfoam.constants import Directory
from libbaram.vtk_threads import vtk_run_in_thread


def _addArrayIfNotExists(dsa: vtkDataSetAttributes, name: str, numComponents: int):
    if dsa.HasArray(name):
        return

    numTuples = dsa.GetNumberOfTuples()

    # dataArray = vtkDoubleArray()
    dataArray = vtkFloatArray()
    dataArray.SetName(name)
    dataArray.SetNumberOfComponents(numComponents)
    dataArray.SetNumberOfTuples(numTuples)
    dataArray.Fill(vtkMath.Nan())

    dsa.AddArray(dataArray)


def _collectArrayFields(dsa: vtkDataSetAttributes) -> dict[str, int]:
    fields: dict[str, int] = {}
    for i in range(dsa.GetNumberOfArrays()):
        dataArray: vtkDataArray = dsa.GetArray(i)
        name = dataArray.GetName()
        fields[name] = dataArray.GetNumberOfComponents()

    return fields


def isPolyMesh(path: Path):
    if not path.is_dir():
        return False

    checkFiles = ['boundary', 'faces', 'neighbour', 'owner', 'points']
    for f in checkFiles:
        if path.joinpath(f).is_file() or path.joinpath(f'{f}.gz').is_file():
            continue
        else:
            return False

    return True


def loadRegions(constant: Path):
    regions = []
    regionPropFile = constant / Directory.REGION_PROPERTIES_FILE_NAME

    if regionPropFile.is_file():
        regionsDict = ParsedParameterFile(regionPropFile).content['regions']
        for i in range(1, len(regionsDict), 2):
            for rname in regionsDict[i]:
                if not constant.joinpath(rname).is_dir():
                    raise RuntimeError(f'"{rname}" directory not found.')
                if not isPolyMesh(constant / rname / 'polyMesh'):
                    raise RuntimeError(f'Cannot find polyMesh files,')

                regions.append(rname)

    return regions if regions else ['']


def removeVoidBoundaries(caseRoot: Path):
    """
    This only works on reconstructed case
    because decomposed cases generally have some boundaries that have nFaces==0
    :param caseRoot:
    :return:
    """
    constant = caseRoot / 'constant'
    regions = loadRegions(constant)
    for rname in regions:
        if not isPolyMesh(constant / rname / 'polyMesh'):
            continue
        boundaryPath = constant / rname / 'polyMesh' / 'boundary'
        boundaryDict = ParsedBoundaryDict(str(boundaryPath), treatBinaryAsASCII=True)
        boundaries = boundaryDict.content

        for b in list(boundaries.keys()):
            if boundaries[b]['nFaces'] == 0:
                del boundaries[b]

        boundaryDict.writeFile()


def findBlock(mBlock: vtkMultiBlockDataSet, name: str, type_: int):
    n = mBlock.GetNumberOfBlocks()
    for i in range(0, n):
        if not mBlock.HasMetaData(i):
            continue

        if name != mBlock.GetMetaData(i).Get(vtkCompositeDataSet.NAME()):
            continue

        ds: vtkDataSet = mBlock.GetBlock(i)
        dsType = ds.GetDataObjectType()

        if dsType != type_:
            continue

        if ds.GetNumberOfCells() == 0:
            continue

        return ds

    return None


async def collectInternalMesh(mBlock: vtkMultiBlockDataSet) -> vtkUnstructuredGrid:
    dataSetList: list[vtkDataSet] = []

    # Collect Fields to make union Field list
    cellFields: dict[str, int] = {}   # FieldName, NumberOfComponent
    pointFields: dict[str, int] = {}  # FieldName, NumberOfComponent

    iterator: vtkCompositeDataIterator = mBlock.NewIterator()
    while not iterator.IsDoneWithTraversal():
        if not iterator.HasCurrentMetaData():
            iterator.GoToNextItem()
            continue

        name = iterator.GetCurrentMetaData().Get(vtkCompositeDataSet.NAME())
        if name != 'internalMesh':
            iterator.GoToNextItem()
            continue

        dataSet: vtkDataSet = iterator.GetCurrentDataObject()
        if dataSet is not None:
            fields = _collectArrayFields(dataSet.GetCellData())
            cellFields.update(fields)

            fields = _collectArrayFields(dataSet.GetPointData())
            pointFields.update(fields)

            dataSetList.append(dataSet)

        iterator.GoToNextItem()

    appendFilter = vtkAppendFilter()

    for dataSet in dataSetList:
        cellData = dataSet.GetCellData()
        for name, numComponents in cellFields.items():
            _addArrayIfNotExists(cellData, name, numComponents)

        pointData = dataSet.GetPointData()
        for name, numComponents in pointFields.items():
            _addArrayIfNotExists(pointData, name, numComponents)

        appendFilter.AddInputData(dataSet)

    await vtk_run_in_thread(appendFilter.Update)

    collectedMesh: vtkUnstructuredGrid = appendFilter.GetOutput()

    collectedMesh.GetCellData().SetActiveVectors('U')
    collectedMesh.GetPointData().SetActiveVectors('U')

    return collectedMesh


async def collectBoundaryMesh(mBlock: vtkMultiBlockDataSet, boundaries: list[tuple[str, str]]) -> vtkPolyData:
    """Returns merged vtkPolyData

    Returns a vtkPolyData that includes all the boundaries in the list

    Args:
        mBlock: Output of vtkOpenFOAMReader()
        boundaries: List of tuples consist of rname and bcname

    Returns:
        vtkPolyData that includes all the boundaries in the list
    """

    dataSetList: list[vtkPolyData] = []

    # Collect Fields to make union Field list
    cellFields: dict[str, int] = {}   # FieldName, NumberOfComponent
    pointFields: dict[str, int] = {}  # FieldName, NumberOfComponent

    for rname, bcname in boundaries:
        if rname != '':  # multi-region
            block = findBlock(mBlock, rname, VTK_MULTIBLOCK_DATA_SET)
            if block is None:
                raise AssertionError('Corrupted Case: Region not exists')
        else:
            block = mBlock

        block = findBlock(block, 'boundary', VTK_MULTIBLOCK_DATA_SET)
        if block is None:
            raise AssertionError('Corrupted Case: boundary group not exists')

        dataSet = findBlock(block, bcname, VTK_POLY_DATA)
        if dataSet is None:
            raise AssertionError('Corrupted Case: boundary not exists')

        dataSetList.append(dataSet)

        fields = _collectArrayFields(dataSet.GetCellData())
        cellFields.update(fields)

        fields = _collectArrayFields(dataSet.GetPointData())
        pointFields.update(fields)

    appendFilter = vtkAppendPolyData()

    for dataSet in dataSetList:
        cellData = dataSet.GetCellData()
        for name, numComponents in cellFields.items():
            _addArrayIfNotExists(cellData, name, numComponents)

        pointData = dataSet.GetPointData()
        for name, numComponents in pointFields.items():
            _addArrayIfNotExists(pointData, name, numComponents)

        appendFilter.AddInputData(dataSet)

    await vtk_run_in_thread(appendFilter.Update)

    return appendFilter.GetOutput()


async def addCoordinateVector(mBlock: vtkMultiBlockDataSet, name: str) -> vtkMultiBlockDataSet:
    calculator = vtkArrayCalculator()
    calculator.SetAttributeTypeToPointData()
    calculator.AddCoordinateVectorVariable( "pCoords",  0, 1, 2)
    calculator.SetFunction('pCoords')

    calculator.SetInputData(mBlock)
    calculator.SetResultArrayName(name)

    await vtk_run_in_thread(calculator.Update)

    return await pointDataToCellData(calculator.GetOutput(), [name])


async def pointDataToCellData(mBlock: vtkMultiBlockDataSet, arrayNames: list[str]) -> vtkMultiBlockDataSet:
    n = mBlock.GetNumberOfBlocks()

    for i in range(n):
        block = mBlock.GetBlock(i)

        if isinstance(block, vtkDataSet):
            conv = vtkPointDataToCellData()
            conv.PassPointDataOn()
            conv.SetInputData(block)
            for name in arrayNames:
                conv.AddPointDataArray(name)
            await vtk_run_in_thread(conv.Update)
            newBlock = conv.GetOutput()
            mBlock.SetBlock(i, newBlock)
        elif isinstance(block, vtkMultiBlockDataSet):
            newBlock = await pointDataToCellData(block, arrayNames)
            mBlock.SetBlock(i, newBlock)

    return mBlock

