#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from vtkmodules.vtkCommonCore import vtkDataArray, vtkFloatArray, vtkMath
from vtkmodules.vtkCommonDataModel import vtkCompositeDataIterator, vtkCompositeDataSet, vtkDataSet, vtkDataSetAttributes, vtkMultiBlockDataSet, vtkUnstructuredGrid
from vtkmodules.vtkFiltersCore import vtkAppendFilter

from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict, ParsedParameterFile

from libbaram.openfoam.constants import Directory


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


def collectInternalMeshMultiBlock(mBlock: vtkMultiBlockDataSet) -> vtkMultiBlockDataSet:
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

        dobj: vtkDataSet = iterator.GetCurrentDataObject()
        if dobj is not None:
            fields = _collectArrayFields(dobj.GetCellData())
            cellFields.update(fields)

            fields = _collectArrayFields(dobj.GetPointData())
            pointFields.update(fields)

        iterator.GoToNextItem()

    newBlock = vtkMultiBlockDataSet()
    blockNo = 0

    iterator: vtkCompositeDataIterator = mBlock.NewIterator()
    while not iterator.IsDoneWithTraversal():
        if not iterator.HasCurrentMetaData():
            iterator.GoToNextItem()
            continue

        name = iterator.GetCurrentMetaData().Get(vtkCompositeDataSet.NAME())
        if name != 'internalMesh':
            iterator.GoToNextItem()
            continue

        dobj: vtkDataSet = iterator.GetCurrentDataObject()
        if dobj is not None:
            cellData = dobj.GetCellData()
            for name, numComponents in cellFields.items():
                _addArrayIfNotExists(cellData, name, numComponents)
            cellData.SetActiveVectors('U')

            pointData = dobj.GetPointData()
            for name, numComponents in pointFields.items():
                _addArrayIfNotExists(pointData, name, numComponents)
            pointData.SetActiveVectors('U')

            newBlock.SetBlock(blockNo, dobj)
            blockNo += 1

        iterator.GoToNextItem()

    return newBlock

def collectInternalMeshUnstructuredGrid(mBlock: vtkMultiBlockDataSet) -> vtkUnstructuredGrid:
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

        dobj: vtkDataSet = iterator.GetCurrentDataObject()
        if dobj is not None:
            fields = _collectArrayFields(dobj.GetCellData())
            cellFields.update(fields)

            fields = _collectArrayFields(dobj.GetPointData())
            pointFields.update(fields)

        iterator.GoToNextItem()

    combined = vtkAppendFilter()

    iterator: vtkCompositeDataIterator = mBlock.NewIterator()
    while not iterator.IsDoneWithTraversal():
        if not iterator.HasCurrentMetaData():
            iterator.GoToNextItem()
            continue

        name = iterator.GetCurrentMetaData().Get(vtkCompositeDataSet.NAME())
        if name != 'internalMesh':
            iterator.GoToNextItem()
            continue

        dobj: vtkDataSet = iterator.GetCurrentDataObject()
        if dobj is not None:
            cellData = dobj.GetCellData()
            for name, numComponents in cellFields.items():
                _addArrayIfNotExists(cellData, name, numComponents)

            pointData = dobj.GetPointData()
            for name, numComponents in pointFields.items():
                _addArrayIfNotExists(pointData, name, numComponents)

            combined.AddInputData(dobj)

        iterator.GoToNextItem()

    combined.Update()
    dataSet: vtkUnstructuredGrid = combined.GetOutput()

    dataSet.GetCellData().SetActiveVectors('U')
    dataSet.GetPointData().SetActiveVectors('U')

    return dataSet

def collectInternalMesh(mBlock: vtkMultiBlockDataSet) -> vtkDataSet:
    return collectInternalMeshUnstructuredGrid(mBlock)
