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
from vtkmodules.vtkCommonCore import VTK_MULTIBLOCK_DATA_SET, VTK_UNSTRUCTURED_GRID, VTK_POLY_DATA, vtkCommand
from PySide6.QtCore import QObject, Signal

from rendering.actor_info import ActorInfo


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
            if ds.GetNumberOfCells() > 0:
                vtkMesh[name] = ActorInfo(getActor(ds))
        elif dsType == VTK_POLY_DATA:
            vtkMesh[name] = ActorInfo(getActor(ds), getFeatureActor(ds))
        else:
            vtkMesh[name] = f'Type {dsType}'  # ds

    return vtkMesh


class PolyMeshLoader(QObject):
    progress = Signal(str)

    def __init__(self, foamFile):
        super().__init__()

        self._reader = vtkPOpenFOAMReader()

        self._reader.SetCaseType(vtkPOpenFOAMReader.RECONSTRUCTED_CASE)
        self._reader.SetFileName(foamFile)

    async def loadMesh(self):
        vtkMesh = await self._loadVtkMesh(self._buildPatchArrayStatus())
        return vtkMesh

    async def _loadVtkMesh(self, statusConfig):
        return await asyncio.to_thread(self._getVtkMesh, statusConfig)

    def _buildPatchArrayStatus(self):
        self._reader.UpdateInformation()
        #
        # for i in range(self._reader.GetNumberOfCellArrays()):
        #     name = self._reader.GetCellArrayName(i)
        #     status = self._reader.GetCellArrayStatus(name)
        #     print(f'CellArray {name} : {status}')

        statusConfig = {}
        for i in range(self._reader.GetNumberOfPatchArrays()):
            name = self._reader.GetPatchArrayName(i)
            statusConfig[name] = 1

        statusConfig['internalMesh'] = 0

        return statusConfig

    def _getVtkMesh(self, statusConfig: dict):
        """
        VtkMesh dict
        {
            <region> : {
                "boundary" : {
                    <boundary> : <ActorInfo>
                    ...
                },
                "internalMesh" : <ActorInfo>,
                "zones" : {
                    "cellZones" : {
                        <cellZone> : <ActorInfo>,
                        ...
                    }
                }
            },
            ...
        }
        """
        def readerProgressEvent(caller: vtkPOpenFOAMReader, ev):
            self.progress.emit(self.tr('Loading Mesh : ') + f'{int(float(caller.GetProgress()) * 100)}%')

        self._reader.DecomposePolyhedraOn()
        self._reader.EnableAllCellArrays()
        self._reader.EnableAllPointArrays()
        self._reader.EnableAllPatchArrays()
        self._reader.EnableAllLagrangianArrays()
        self._reader.CreateCellToPointOn()
        self._reader.CacheMeshOn()
        self._reader.ReadZonesOn()

        self._reader.AddObserver(vtkCommand.ProgressEvent, readerProgressEvent)

        if statusConfig:
            for patchName, status in statusConfig.items():
                self._reader.SetPatchArrayStatus(patchName, status)

        self._reader.Update()

        vtkMesh = build(self._reader.GetOutput())

        if 'boundary' in vtkMesh:  # single region mesh
            vtkMesh = {'': vtkMesh}

        return vtkMesh
