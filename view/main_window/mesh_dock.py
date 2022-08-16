#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
import asyncio
from pathlib import Path

import qasync

from PySide6.QtCore import Qt, Signal
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer
from vtkmodules.vtkIOGeometry import vtkOpenFOAMReader
from vtkmodules.vtkFiltersGeometry import  vtkGeometryFilter
from vtkmodules.vtkCommonDataModel import vtkCompositeDataSet
# load implementations for rendering and interaction factory classes
import vtkmodules.vtkRenderingOpenGL2
import vtkmodules.vtkInteractionStyle

from openfoam.file_system import FileSystem
from .tabified_dock import TabifiedDock

import vtk


@dataclass
class ActorInfo:
    # It is not clear if the references of these two values should be kept
    #    dataset: vtk.vtkDataObject
    #    gFilter: vtk.vtkGeometryFilter
    mapper: vtkPolyDataMapper
    actor: vtkActor


def getActorInfo(dataset) -> ActorInfo:
    gFilter = vtkGeometryFilter()
    gFilter.SetInputData(dataset)
    gFilter.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(gFilter.GetOutput())

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(255, 255, 255)

    # return ActorInfo(dataset, gFilter, mapper, actor)
    return ActorInfo(mapper, actor)


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
            vtkMesh[name] = getActorInfo(ds)
        elif dsType == vtk.VTK_POLY_DATA:
            vtkMesh[name] = getActorInfo(ds)
        else:
            vtkMesh[name] = f'Type {dsType}'  # ds

    return vtkMesh


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
def getVtkMesh(foamFilePath: Path):
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
    r.Update()

    numberOfPatchArrays = r.GetNumberOfPatchArrays()
    for i in range(0, numberOfPatchArrays):
        name = r.GetPatchArrayName(i)
        if name.endswith('internalMesh'):
            r.SetPatchArrayStatus(name, 0)
        else:
            r.SetPatchArrayStatus(name, 1)

    r.Update()

    vtkMesh = build(r.GetOutput())

    if 'boundary' in vtkMesh:  # single region mesh
        vtkMesh = {'': vtkMesh}

    return vtkMesh


class MeshDock(TabifiedDock):
    reloadMesh = Signal()
    meshLoaded = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Mesh"))
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self._widget = QVTKRenderWindowInteractor(self)
        self._renderer = vtkRenderer()
        self._widget.GetRenderWindow().AddRenderer(self._renderer)
        self.setWidget(self._widget)

        self._widget.Initialize()
        self._widget.Start()

        self._vtkMesh = None

        self.reloadMesh.connect(self.showOpenFoamMesh)

    def vtkMesh(self):
        return self._vtkMesh

    @qasync.asyncSlot()
    async def showOpenFoamMesh(self):
        self._vtkMesh = await asyncio.to_thread(getVtkMesh, FileSystem.foamFilePath())

        for region in self._vtkMesh:
            for boundary in self._vtkMesh[region]['boundary']:
                actorInfo = self._vtkMesh[region]['boundary'][boundary]
                self._renderer.AddActor(actorInfo.actor)

        self._widget.Render()

        self.meshLoaded.emit()
