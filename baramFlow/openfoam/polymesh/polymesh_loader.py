#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import asyncio
import re
from pathlib import Path

from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict
from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkIOParallel import vtkPOpenFOAMReader
from vtkmodules.vtkCommonDataModel import vtkCompositeDataSet
from vtkmodules.vtkCommonCore import VTK_MULTIBLOCK_DATA_SET, VTK_UNSTRUCTURED_GRID, VTK_POLY_DATA, vtkCommand

from libbaram.openfoam.constants import Directory

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryType, GeometricalType, BoundaryDB
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.region_db import RegionDB, DEFAULT_REGION_NAME
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.constant.region_properties import RegionProperties
from baramFlow.mesh.mesh_model import ActorInfo, MeshModel


logger = logging.getLogger(__name__)


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
                vtkMesh[name] = ActorInfo(ds)
        elif dsType == VTK_POLY_DATA:
            vtkMesh[name] = ActorInfo(ds)
        else:
            vtkMesh[name] = f'Type {dsType}'  # ds

    return vtkMesh


inMatchPattern = re.compile('in([^a-zA-Z]|$)', re.IGNORECASE)
inletSearchPattern = re.compile('([^a-zA-Z]|^)inlet', re.IGNORECASE)
outMatchPattern = re.compile('out([^a-zA-Z]|$)', re.IGNORECASE)
outletSearchPattern = re.compile('([^a-zA-Z]|^)outlet', re.IGNORECASE)

emptyBoundaryName ='frontAndBackPlanes'


def defaultBoundaryType(name, geometricalType):
    if name == emptyBoundaryName:
        return BoundaryType.EMPTY

    if geometricalType == GeometricalType.PATCH or geometricalType == GeometricalType.WALL:
        if inMatchPattern.match(name) or inletSearchPattern.search(name):
            return BoundaryType.VELOCITY_INLET

        if outMatchPattern.match(name) or outletSearchPattern.search(name):
            return BoundaryType.PRESSURE_OUTLET

        return BoundaryType.WALL

    if geometricalType == GeometricalType.CYCLIC:
        return BoundaryType.CYCLIC

    if geometricalType == GeometricalType.CYCLIC_AMI:
        return BoundaryType.INTERFACE

    if geometricalType == GeometricalType.MAPPED_WALL:
        return BoundaryType.THERMO_COUPLED_WALL

    if geometricalType == GeometricalType.SYMMETRY:
        return BoundaryType.SYMMETRY

    if geometricalType == GeometricalType.EMPTY:
        return BoundaryType.EMPTY

    if geometricalType == GeometricalType.WEDGE:
        return BoundaryType.WEDGE

    return BoundaryType.WALL


class PolyMeshLoader(QObject):
    progress = Signal(str)

    @classmethod
    def loadBoundaryDict(cls, path, listLengthUnparsed=None, longListOutputThreshold=None):
        return ParsedBoundaryDict(path, listLengthUnparsed=listLengthUnparsed, treatBinaryAsASCII=True, longListOutputThreshold=longListOutputThreshold)

    async def loadMesh(self):
        self.progress.emit(self.tr("Loading Mesh..."))
        boundaries = self._loadBoundaries()

        vtkMesh = await self._loadVtkMesh()
        updated = self._updateDB(vtkMesh, boundaries)
        self._updateVtkMesh(vtkMesh)
        if updated:
            app.updateMesh()

    async def loadVtk(self):
        self.progress.emit(self.tr("Loading Mesh..."))
        vtkMesh = await self._loadVtkMesh()
        self._updateVtkMesh(vtkMesh)

    def _loadBoundaries(self):
        boundaries = {}

        path = FileSystem.constantPath()
        regionPropFile = path / Directory.REGION_PROPERTIES_FILE_NAME
        if regionPropFile.is_file():
            regions = RegionProperties.loadRegions(path)
            for rname in regions:
                boundaryDict = self.loadBoundaryDict(path / rname / Directory.POLY_MESH_DIRECTORY_NAME / 'boundary')
                boundaries[rname] = boundaryDict.content
        else:
            boundaryDict = self.loadBoundaryDict(path / 'polyMesh' / 'boundary')
            boundaries[''] = boundaryDict.content

        return boundaries

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
            return set(czname for _, czname in db.getCellZones(region) if not CellZoneDB.isRegion(czname))

        def newCellZones(region):
            return set(vtkMesh[region]['zones']['cellZones'].keys()) \
                if 'zones' in vtkMesh[region] and 'cellZones' in vtkMesh[region]['zones'] \
                else set()

        def getSamplePatch(rname, bcname):
            region = None
            patch = None

            if rname == DEFAULT_REGION_NAME:
                rname = ''

            if rname in boundaries and bcname in boundaries[rname]:
                b = boundaries[rname][bcname]
                if 'samplePatch' in b:
                    patch = b['samplePatch']
                    region = b['sampleRegion'] if 'sampleRegion' in b else rname

            if region == DEFAULT_REGION_NAME:
                region = ''

            return region, patch

        def getNeighbourPatch(rname, bcname):
            b = boundaries[rname][bcname]
            if 'neighbourPatch' in b:
                return b['neighbourPatch']

            return None

        db = coredb.CoreDB()
        if set(db.getRegions()) == set(r for r in vtkMesh if 'boundary' in vtkMesh[r]) and \
                all(oldBoundaries(rname) == newBoundareis(rname) and oldCellZones(rname) == newCellZones(rname)
                    for rname in boundaries):
            return False

        UserDefinedScalarsDB.clearUserDefinedScalars(db)
        db.clearRegions()
        db.clearMonitors()

        for rname in boundaries:
            RegionDB.addRegion(rname)

            # Initial value of "0" for pressure in density-based solvers causes trouble by making density zero
            # because operating pressure is fixed to "0" for density-based solvers
            if GeneralDB.isDensityBased():
                pressurePath = f'.//regions/region[name="{rname}"]/initialization/initialValues/pressure'
                db.setValue(pressurePath, '101325')

            for bcname in vtkMesh[rname]['boundary']:
                boundary = boundaries[rname][bcname]
                geometricalType = GeometricalType(boundary['type'])
                boundaryType = defaultBoundaryType(bcname, geometricalType)
                boundary['bcid'] = str(db.addBoundaryCondition(rname, bcname, boundary['type'], boundaryType.value))

                if BoundaryDB.needsCoupledBoundary(boundaryType.value):
                    coupledBoundary = None
                    if geometricalType == GeometricalType.MAPPED_WALL and 'samplePatch' in boundary:
                        sampleRegion, samplePatch = getSamplePatch(rname, bcname)
                        if samplePatch and getSamplePatch(sampleRegion, samplePatch) == (rname, bcname):
                            coupledBoundary = boundaries[sampleRegion][samplePatch]
                    elif 'neighbourPatch' in boundary:
                        neighbourPatch = getNeighbourPatch(rname, bcname)
                        if neighbourPatch and getNeighbourPatch(rname, neighbourPatch) == bcname:
                            coupledBoundary = boundaries[rname][neighbourPatch]

                    if coupledBoundary and 'bcid' in coupledBoundary:
                        db.setValue(BoundaryDB.getXPath(boundary['bcid']) + '/coupledBoundary', coupledBoundary['bcid'])
                        db.setValue(BoundaryDB.getXPath(coupledBoundary['bcid']) + '/coupledBoundary', boundary['bcid'])

            if 'zones' in vtkMesh[rname] and 'cellZones' in vtkMesh[rname]['zones']:
                for czname in vtkMesh[rname]['zones']['cellZones']:
                    db.addCellZone(rname, czname)

        return True

    def _updateVtkMesh(self, vtkMesh):
        db = coredb.CoreDB()

        viewModel = MeshModel()
        cellZones = {}
        internalMeshes = {}
        for rname in db.getRegions():
            for bcid, bcname, _ in db.getBoundaryConditions(rname):
                viewModel.setActorInfo(bcid, vtkMesh[rname]['boundary'][bcname])

            for czid, czname in db.getCellZones(rname):
                if not CellZoneDB.isRegion(czname):
                    cellZones[czid] = vtkMesh[rname]['zones']['cellZones'][czname]

            internalMeshes[rname] = vtkMesh[rname]['internalMesh']

        app.updateVtk(viewModel, cellZones, internalMeshes)
