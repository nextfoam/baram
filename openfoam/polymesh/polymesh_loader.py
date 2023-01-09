#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import asyncio
from pathlib import Path

import vtk
from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict
from vtkmodules.vtkIOGeometry import vtkOpenFOAMReader
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
from vtkmodules.vtkCommonDataModel import vtkCompositeDataSet
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper

from app import app
from coredb import coredb
from coredb.project import Project
from openfoam.file_system import FileSystem, FileLoadingError
from openfoam.constant.region_properties import RegionProperties
from mesh.vtk_loader import ActorInfo
from mesh.mesh_model import MeshModel


logger = logging.getLogger(__name__)


def getActor(dataset):
    gFilter = vtkGeometryFilter()
    gFilter.SetInputData(dataset)
    gFilter.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(gFilter.GetOutput())

    actor = vtk.vtkQuadricLODActor()    # vtkActor()
    actor.SetMapper(mapper)

    return actor


def getFeatureActor(dataset):
    edges = vtk.vtkFeatureEdges()
    edges.SetInputData(dataset)
    edges.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(edges.GetOutput())
    mapper.ScalarVisibilityOff()

    actor = vtk.vtkActor()
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
        if dsType == vtk.VTK_MULTIBLOCK_DATA_SET:
            vtkMesh[name] = build(ds)
        elif dsType == vtk.VTK_UNSTRUCTURED_GRID:
            if ds.GetNumberOfCells() > 0:
                vtkMesh[name] = ActorInfo(getActor(ds))
        elif dsType == vtk.VTK_POLY_DATA:
            vtkMesh[name] = ActorInfo(getActor(ds), getFeatureActor(ds))
        else:
            vtkMesh[name] = f'Type {dsType}'  # ds

    return vtkMesh


def getVtkMesh(foamFilePath: Path, statusConfig: dict):
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
    r = vtkOpenFOAMReader()
    r.SetFileName(str(foamFilePath))
    r.DecomposePolyhedraOn()
    r.EnableAllCellArrays()
    r.EnableAllPointArrays()
    r.EnableAllPatchArrays()
    r.EnableAllLagrangianArrays()
    r.CreateCellToPointOn()
    r.CacheMeshOn()
    r.ReadZonesOn()

    for patchName, status in statusConfig.items():
        r.SetPatchArrayStatus(patchName, status)

    r.Update()

    vtkMesh = build(r.GetOutput())

    if 'boundary' in vtkMesh:  # single region mesh
        vtkMesh = {'': vtkMesh}

    return vtkMesh


class PolyMeshLoader:
    @classmethod
    def loadBoundaryDict(cls, path, listLengthUnparsed=None):
        return ParsedBoundaryDict(path, listLengthUnparsed=listLengthUnparsed, treatBinaryAsASCII=True)

    async def loadMesh(self, srcPath=None):
        boundaries = await self._loadBoundaries(srcPath)
        vtkMesh = await self._loadVtkMesh(self._buildPatchArrayStatus(boundaries))
        updated = self._updateDB(vtkMesh, boundaries)
        self._updateVtkMesh(vtkMesh)
        Project.instance().setMeshLoaded(True, updated)

    async def loadVtk(self):
        vtkMesh = await self._loadVtkMesh(self._buildPatchArrayStatusFromDB())
        self._updateVtkMesh(vtkMesh)

    async def _loadBoundaries(self, srcPath):
        boundaries = {}

        path = srcPath
        if not path:
            path = FileSystem.constantPath()

        regions = RegionProperties.loadRegions(path)
        if regions[0] == '':
            if not FileSystem.isPolyMesh(path.joinpath('polyMesh')):
                path = path.parent
                if not FileSystem.isPolyMesh(path.joinpath('polyMesh')):
                    raise FileLoadingError(f'PolyMesh files not found.')

            # single region
            if not FileSystem.isPolyMesh(path):
                path = path / FileSystem.POLY_MESH_DIRECTORY_NAME
                if not FileSystem.isPolyMesh(path):
                    raise FileLoadingError('Mesh directory not found.')

            boundaryDict = self.loadBoundaryDict(path / 'boundary')
            boundaries[''] = {bname: boundary['type'] for bname, boundary in boundaryDict.content.items()}
        else:
            # multi region
            for rname in regions:
                boundaryDict = self.loadBoundaryDict(path / rname / FileSystem.POLY_MESH_DIRECTORY_NAME / 'boundary')
                boundaries[rname] = {bname: boundary['type'] for bname, boundary in boundaryDict.content.items()}

        if srcPath:
            await FileSystem.copyMeshFrom(path, regions)

        return boundaries

    async def _loadVtkMesh(self, statusConfig):
        return await asyncio.to_thread(getVtkMesh, FileSystem.foamFilePath(), statusConfig)

    def _buildPatchArrayStatusFromDB(self):
        statusConfig = {'internalMesh': 0}

        db = coredb.CoreDB()
        regions = db.getRegions()

        if len(regions) == 1:  # single region
            for _, b, _ in db.getBoundaryConditions(regions[0]):
                statusConfig[f'patch/{b}'] = 1

            return statusConfig

        else:  # multi-region
            for r in regions:
                statusConfig[f'/{r}/internalMesh'] = 0
                for _, b, _ in db.getBoundaryConditions(r):
                    statusConfig[f'/{r}/patch/{b}'] = 1

            return statusConfig

    def _buildPatchArrayStatus(self, boundaries):
        statusConfig = {'internalMesh': 0}

        r = ''
        for region in boundaries:
            if region:
                r = f'/{region}/'
                statusConfig[f'{r}internalMesh'] = 0

            for b in boundaries[region]:
                statusConfig[f'{r}patch/{b}'] = 1

        return statusConfig

    def _updateDB(self, vtkMesh, boundaries):
        def oldBoundaries(region):
            return set(bcname for _, bcname, _ in db.getBoundaryConditions(region))

        def newBoundareis(region):
            return set(vtkMesh[region]['boundary'].keys())

        def oldCellZones(region):
            return set(czname for _, czname in db.getCellZones(region) if czname != 'All')

        def newCellZones(region):
            return set(vtkMesh[region]['zones']['cellZones'].keys()) \
                if 'zones' in vtkMesh[region] and 'cellZones' in vtkMesh[region]['zones'] \
                else set()

        db = coredb.CoreDB()
        if set(db.getRegions()) == set(r for r in vtkMesh if 'boundary' in vtkMesh[r]) and \
                all(oldBoundaries(rname) == newBoundareis(rname) and oldCellZones(rname) == newCellZones(rname)
                    for rname in boundaries):
            return False

        db.clearRegions()
        db.clearMonitors()

        for rname in boundaries:
            db.addRegion(rname)

            for bcname in vtkMesh[rname]['boundary']:
                db.addBoundaryCondition(rname, bcname, boundaries[rname][bcname])

            if 'zones' in vtkMesh[rname] and 'cellZones' in vtkMesh[rname]['zones']:
                for czname in vtkMesh[rname]['zones']['cellZones']:
                    db.addCellZone(rname, czname)

        return True

    def _updateVtkMesh(self, vtkMesh):
        db = coredb.CoreDB()

        viewModel = MeshModel()
        for rname in db.getRegions():
            for bcid, bcname, _ in db.getBoundaryConditions(rname):
                viewModel.setActorInfo(bcid, vtkMesh[rname]['boundary'][bcname])

        app.updateVtkMesh(viewModel)
