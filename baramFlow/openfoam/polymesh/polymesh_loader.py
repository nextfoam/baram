#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import asyncio
import re
import shutil
from pathlib import Path

from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict
from vtkmodules.vtkIOParallel import vtkPOpenFOAMReader
from vtkmodules.vtkFiltersCore import vtkFeatureEdges
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
from vtkmodules.vtkCommonDataModel import vtkCompositeDataSet
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper
from vtkmodules.vtkRenderingLOD import vtkQuadricLODActor
from vtkmodules.vtkCommonCore import VTK_MULTIBLOCK_DATA_SET, VTK_UNSTRUCTURED_GRID, VTK_POLY_DATA, vtkCommand
from PySide6.QtCore import QObject, Signal

from baramFlow.coredb.boundary_db import BoundaryType
from libbaram import utils
from libbaram.openfoam.constants import Directory, CASE_DIRECTORY_NAME

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.project import Project
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.openfoam.file_system import FileSystem, FileLoadingError
from baramFlow.openfoam.constant.region_properties import RegionProperties
from baramFlow.mesh.mesh_model import ActorInfo, MeshModel


logger = logging.getLogger(__name__)


def getActor(dataset):
    gFilter = vtkGeometryFilter()
    gFilter.SetInputData(dataset)
    gFilter.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(gFilter.GetOutput())
    mapper.ScalarVisibilityOff()

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


inMatchPattern = re.compile('in([^a-zA-Z]|$)', re.IGNORECASE)
inletSearchPattern = re.compile('([^a-zA-Z]|^)inlet', re.IGNORECASE)
outMatchPattern = re.compile('out([^a-zA-Z]|$)', re.IGNORECASE)
outletSearchPattern = re.compile('([^a-zA-Z]|^)outlet', re.IGNORECASE)


def defaultBoundaryType(name, geometricalType):
    if inMatchPattern.match(name) or inletSearchPattern.search(name):
        return BoundaryType.VELOCITY_INLET.value

    if outMatchPattern.match(name) or outletSearchPattern.search(name):
        return BoundaryType.PRESSURE_OUTLET.value

    return BoundaryType.WALL.value


class PolyMeshLoader(QObject):
    progress = Signal(str)

    @classmethod
    def loadBoundaryDict(cls, path, listLengthUnparsed=None, longListOutputThreshold=None):
        return ParsedBoundaryDict(path, listLengthUnparsed=listLengthUnparsed, treatBinaryAsASCII=True, longListOutputThreshold=longListOutputThreshold)

    async def loadMesh(self, srcPath=None):
        if srcPath is not None:
            path = self._checkAndCorrectMeshFolderSelection(srcPath)
            await self.copyMeshFrom(path)
        else:
            path = FileSystem.constantPath()

        boundaries = self._loadBoundaries(path)

        vtkMesh = await self._loadVtkMesh()
        self._updateDB(vtkMesh, boundaries)
        self._updateVtkMesh(vtkMesh)
        Project.instance().setMeshLoaded(True)

    async def loadVtk(self):
        self.progress.emit(self.tr("Loading Mesh..."))
        vtkMesh = await self._loadVtkMesh()
        self._updateVtkMesh(vtkMesh)

    def _loadBoundaries(self, path: Path):
        boundaries = {}

        regionPropFile = path / Directory.REGION_PROPERTIES_FILE_NAME
        if regionPropFile.is_file():
            regions = RegionProperties.loadRegions(path)
            for rname in regions:
                boundaryDict = self.loadBoundaryDict(path / rname / Directory.POLY_MESH_DIRECTORY_NAME / 'boundary')
                boundaries[rname] = {bname: boundary['type'] for bname, boundary in boundaryDict.content.items()}
        else:
            boundaryDict = self.loadBoundaryDict(path / 'polyMesh' / 'boundary')
            boundaries[''] = {bname: boundary['type'] for bname, boundary in boundaryDict.content.items()}

        return boundaries

    def _checkAndCorrectMeshFolderSelection(self, path: Path) -> Path:
        """Check if "path" has correct polyMesh

        Check if "path" has correct polyMesh
        "path" can point "polyMesh" or "constant" for single region mesh
        "path" should point "constant" for multi-region mesh

        Args:
            path: path for "constant" or "polyMesh"

        Returns:
            path for "constant" folder

        Raises:
            FileLoadingError: "path" does not have correct polyMesh
        """
        if FileSystem.isPolyMesh(path):
            return path.parent

        if FileSystem.isPolyMesh(path / 'polyMesh'):
            return path

        regionPropFile = path / Directory.REGION_PROPERTIES_FILE_NAME
        if not regionPropFile.is_file():
            raise FileLoadingError(f'PolyMesh not found.')

        regions = RegionProperties.loadRegions(path)
        for rname in regions:
            if not FileSystem.isPolyMesh(path / rname / 'polyMesh'):
                raise FileLoadingError(f'Corrupted Multi-Region PolyMesh')

        return path

    async def _loadVtkMesh(self):
        return await asyncio.to_thread(self._getVtkMesh, FileSystem.foamFilePath())

    def _getVtkMesh(self, foamFilePath: Path):
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

        r = vtkPOpenFOAMReader()
        r.SetCaseType(
            vtkPOpenFOAMReader.DECOMPOSED_CASE if FileSystem.processorPath(0) else vtkPOpenFOAMReader.RECONSTRUCTED_CASE)
        r.SetFileName(str(foamFilePath))
        r.EnableAllCellArrays()
        r.EnableAllPointArrays()
        r.EnableAllPatchArrays()
        r.EnableAllLagrangianArrays()
        r.CreateCellToPointOn()
        r.CacheMeshOn()
        r.ReadZonesOn()

        r.UpdateInformation()

        for i in range(r.GetNumberOfPatchArrays()):
            name = r.GetPatchArrayName(i)
            m = re.search(r'patch/', name)
            if m is not None:
                r.SetPatchArrayStatus(name, 1)

        r.AddObserver(vtkCommand.ProgressEvent, readerProgressEvent)

        r.Update()

        vtkMesh = build(r.GetOutput())

        if 'boundary' in vtkMesh:  # single region mesh
            vtkMesh = {'': vtkMesh}

        return vtkMesh

    def _updateDB(self, vtkMesh, boundaries):
        def oldBoundaries(region):
            return set(bcname for _, bcname, _ in db.getBoundaryConditions(region))

        def newBoundareis(region):
            return set(vtkMesh[region]['boundary'].keys())

        def oldCellZones(region):
            return set(czname for _, czname in db.getCellZones(region) if czname != CellZoneDB.NAME_FOR_REGION)

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
                geometricalType = boundaries[rname][bcname]
                db.addBoundaryCondition(rname, bcname, geometricalType, defaultBoundaryType(bcname, geometricalType))

            if 'zones' in vtkMesh[rname] and 'cellZones' in vtkMesh[rname]['zones']:
                for czname in vtkMesh[rname]['zones']['cellZones']:
                    db.addCellZone(rname, czname)

        return True

    def _updateVtkMesh(self, vtkMesh):
        db = coredb.CoreDB()

        viewModel = MeshModel()
        cellZones = {}
        for rname in db.getRegions():
            for bcid, bcname, _ in db.getBoundaryConditions(rname):
                viewModel.setActorInfo(bcid, vtkMesh[rname]['boundary'][bcname])

            for czid, czname in db.getCellZones(rname):
                if not CellZoneDB.isRegion(czname):
                    cellZones[czid] = vtkMesh[rname]['zones']['cellZones'][czname]

        app.updateVtkMesh(viewModel, cellZones)

    async def copyMeshFrom(self, source):
        await asyncio.to_thread(self._copyMeshFromInternal, source)

    def _copyMeshFromInternal(self, source):
        target = Project.instance().path / CASE_DIRECTORY_NAME / Directory.CONSTANT_DIRECTORY_NAME  # Constant Path for Live Case
        if target.exists():
            utils.rmtree(target)

        target.mkdir(exist_ok=True)

        regionPropFile = source / Directory.REGION_PROPERTIES_FILE_NAME
        if regionPropFile.is_file():
            shutil.copyfile(regionPropFile, target / Directory.REGION_PROPERTIES_FILE_NAME)
            regions = RegionProperties.loadRegions(source)
            for rname in regions:
                s = source / rname / Directory.POLY_MESH_DIRECTORY_NAME
                t = target / rname / Directory.POLY_MESH_DIRECTORY_NAME
                shutil.copytree(s, t, copy_function=shutil.copyfile)
        else:
            s = source / Directory.POLY_MESH_DIRECTORY_NAME
            t = target / Directory.POLY_MESH_DIRECTORY_NAME
            shutil.copytree(s, t, copy_function=shutil.copyfile)

