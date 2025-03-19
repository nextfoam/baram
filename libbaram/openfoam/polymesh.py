#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from vtkmodules.vtkCommonDataModel import vtkCompositeDataIterator, vtkCompositeDataSet, vtkDataObject, vtkDataSet, vtkMultiBlockDataSet, vtkUnstructuredGrid
from vtkmodules.vtkFiltersCore import vtkAppendFilter

from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict, ParsedParameterFile

from libbaram.openfoam.constants import Directory


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


def collectInternalMesh(mBlock: vtkMultiBlockDataSet) -> list[vtkDataObject]:
    meshes = []
    iterator: vtkCompositeDataIterator = mBlock.NewIterator()
    while not iterator.IsDoneWithTraversal():
        if not iterator.HasCurrentMetaData():
            iterator.GoToNextItem()
            continue

        name = iterator.GetCurrentMetaData().Get(vtkCompositeDataSet.NAME())
        if name != 'internalMesh':
            iterator.GoToNextItem()
            continue

        dobj = iterator.GetCurrentDataObject()
        if dobj is not None:
            meshes.append(dobj)

        iterator.GoToNextItem()

    return meshes

def collectInternalMesh2(mBlock: vtkMultiBlockDataSet) -> vtkUnstructuredGrid:
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

        dobj = iterator.GetCurrentDataObject()
        if dobj is not None:
            combined.AddInputData(dobj)

        iterator.GoToNextItem()

    combined.Update()

    return combined.GetOutput()
