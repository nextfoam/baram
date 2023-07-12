#!/usr/bin/env python
# -*- coding: utf-8 -*-
from vtkmodules.vtkFiltersModeling import vtkSelectEnclosedPoints
from vtkmodules.vtkFiltersCore import vtkAppendPolyData, vtkCleanPolyData

from app import app
from openfoam.system.surface_patch_dict import SurfacePatchDict, SurfacePatchData
from openfoam.run import runUtility, OpenFOAMError
from rendering.vtk_loader import loadSTL


import qasync

SURFACE_PATCH_SRC_FILE_NAME = 'geometry.stl'
SURFACE_PATCHED_FILE_NAME = 'geometry_patched.stl'


class STLFileLoader:
    def __init__(self):
        self._fileSystem = app.fileSystem
        self._triSurfacePath = self._fileSystem.triSurfacePath() / SURFACE_PATCHED_FILE_NAME

    @qasync.asyncSlot()
    async def load(self, path, featureAngle):
        volumes = []
        surfaces = []

        solids = None
        if featureAngle:
            patchSrcFile = await self._fileSystem.copyTriSurfaceFrom(path, SURFACE_PATCH_SRC_FILE_NAME)

            SurfacePatchDict().build(SurfacePatchData(SURFACE_PATCH_SRC_FILE_NAME, featureAngle)).write()

            patchedFile = self._fileSystem.triSurfacePath() / SURFACE_PATCHED_FILE_NAME
            patchedFile.unlink(missing_ok=True)

            proc = await runUtility('surfacePatch', cwd=self._fileSystem.caseRoot())
            await proc.wait()

            if proc.returncode:
                raise OpenFOAMError(proc.returncode, 'An error occurred while running surfacePatch.')

            if patchedFile.exists():
                solids = loadSTL(patchedFile)
                patchedFile.unlink()

            patchSrcFile.unlink()

        if solids is None:
            solids = loadSTL(path)

        appendFilter = vtkAppendPolyData()

        for solid in solids:
            if vtkSelectEnclosedPoints.IsSurfaceClosed(solid):
                if solid.GetNumberOfPoints() > 0:
                    volumes.append([solid])
            else:
                surfaces.append(solid)
                appendFilter.AddInputData(solid)

        if surfaces:
            cleanFilter = vtkCleanPolyData()
            cleanFilter.SetInputConnection(appendFilter.GetOutputPort())
            cleanFilter.Update()
            if vtkSelectEnclosedPoints.IsSurfaceClosed(cleanFilter.GetOutput()):
                volumes.append(surfaces)
                surfaces = []

        return volumes, surfaces

