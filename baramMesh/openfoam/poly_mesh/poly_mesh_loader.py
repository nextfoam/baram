#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import asyncio

from vtkmodules.vtkIOParallel import vtkPOpenFOAMReader
from vtkmodules.vtkFiltersCore import vtkFeatureEdges
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
from vtkmodules.vtkCommonDataModel import vtkCompositeDataSet
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper
from vtkmodules.vtkRenderingLOD import vtkQuadricLODActor
from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.util.vtkConstants import VTK_MULTIBLOCK_DATA_SET, VTK_UNSTRUCTURED_GRID, VTK_POLY_DATA
from PySide6.QtCore import QObject, Signal


logger = logging.getLogger(__name__)


def getActor(dataset):
    gFilter = vtkGeometryFilter()
    gFilter.SetInputData(dataset)
    gFilter.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(gFilter.GetOutput())

    actor = vtkQuadricLODActor()    # vtkActor()
    actor.SetMapper(mapper)

    return actor


def getFeatureActor(dataset):
    edges = vtkFeatureEdges()
    edges.SetInputData(dataset)
    edges.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(edges.GetOutput())
    mapper.ScalarVisibilityOff()

    actor = vtkActor()
    actor.SetMapper(mapper)

    return actor


def build(mBlock):
    vtkMesh = {}
    n = mBlock.GetNumberOfBlocks()
    for i in range(0, n):
        if mBlock.HasMetaData(i):
            name = mBlock.GetMetaData(i).Get(vtkCompositeDataSet.NAME())
        else:
            name = ''
        ds = mBlock.GetBlock(i)
        dsType = ds.GetDataObjectType()
        if dsType == VTK_MULTIBLOCK_DATA_SET:
            vtkMesh[name] = build(ds)
        elif dsType == VTK_UNSTRUCTURED_GRID:
            # if ds.GetNumberOfCells() > 0:
            #     # vtkMesh[name] = ActorInfo(getActor(ds))
            #     gFilter = vtkGeometryFilter()
            #     gFilter.SetInputData(ds)
            #     gFilter.Update()
            #
            #     vtkMesh[name] = gFilter.GetOutput()
            vtkMesh[name] = ds
        elif dsType == VTK_POLY_DATA:
            # vtkMesh[name] = ActorInfo(getActor(ds), getFeatureActor(ds))
            vtkMesh[name] = ds
        else:
            vtkMesh[name] = f'Type {dsType}'  # ds

    return vtkMesh


class PolyMeshLoader(QObject):
    progress = Signal(str)

    def __init__(self, foamFile):
        super().__init__()

        self._reader = vtkPOpenFOAMReader()
        self._processorPath = foamFile.parent / 'processor0'

        self._reader.SetFileName(foamFile)
        self._reader.EnableAllCellArrays()
        self._reader.EnableAllPointArrays()
        self._reader.EnableAllPatchArrays()
        self._reader.EnableAllLagrangianArrays()
        self._reader.CreateCellToPointOn()
        self._reader.CacheMeshOn()
        self._reader.ReadZonesOn()
        self._reader.SkipZeroTimeOff()

        self._progress_range = [0, 100]

        self._reader.AddObserver(vtkCommand.ProgressEvent, self._readerProgressed)

    async def loadMesh(self, time):
        if self._processorPath.is_dir():
            self._reader.SetCaseType(vtkPOpenFOAMReader.DECOMPOSED_CASE)
        else:
            self._reader.SetCaseType(vtkPOpenFOAMReader.RECONSTRUCTED_CASE)

        self._reader.UpdateInformation()
        self._reader.SetTimeValue(time)
        self._reader.Modified()

        self._progress_range = [0, 50]
        # Be careful!
        # This should  be protected by modal dialog to prohibit users from interacting with rendering window
        # Only one VTK can be allowed to keep integrity
        await asyncio.to_thread(self._reader.Update)
        self._progress_range = [50, 100]
        return await asyncio.to_thread(self._getVtkMesh, self._buildPatchArrayStatus())

    def _buildPatchArrayStatus(self):
        #
        # for i in range(self._reader.GetNumberOfCellArrays()):
        #     name = self._reader.GetCellArrayName(i)
        #     status = self._reader.GetCellArrayStatus(name)
        #     print(f'CellArray {name} : {status}')

        statusConfig = {}
        for i in range(self._reader.GetNumberOfPatchArrays()):
            name = self._reader.GetPatchArrayName(i)
            statusConfig[name] = 1

        statusConfig['internalMesh'] = 1

        return statusConfig

    def _getVtkMesh(self, statusConfig: dict):
        """
        VtkMesh dict
        {
            <region> : {
                "boundary" : {
                    <boundary> : <PolyData>
                    ...
                },
                "internalMesh" : <ActorInfo>,
                "zones" : {
                    "cellZones" : {
                        <cellZone> : <PolyData>,
                        ...
                    }
                }
            },
            ...
        }
        """

        if statusConfig:
            for patchName, status in statusConfig.items():
                self._reader.SetPatchArrayStatus(patchName, status)

        for i in range(self._reader.GetNumberOfCellArrays()):
            name = self._reader.GetCellArrayName(i)
            self._reader.SetCellArrayStatus(name, 1)

        for i in range(self._reader.GetNumberOfPointArrays()):
            name = self._reader.GetPointArrayName(i)
            self._reader.SetPointArrayStatus(name, 1)

        self._reader.Update()

        vtkMesh = build(self._reader.GetOutput())

        if 'boundary' in vtkMesh:  # single region mesh
            vtkMesh = {'': vtkMesh}

        return vtkMesh

    def _readerProgressed(self, caller: vtkPOpenFOAMReader, ev):
        self.progress.emit(self.tr('Loading Mesh : ')
                           + f'{int(self._progress_range[0] + (float(caller.GetProgress()) * (self._progress_range[1] - self._progress_range[0])))}%')
