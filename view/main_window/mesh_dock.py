#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING

from dataclasses import dataclass
import asyncio
from pathlib import Path
from typing import Optional

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

from coredb import coredb
from openfoam.file_system import FileSystem
from .tabified_dock import TabifiedDock
if TYPE_CHECKING:
    from .main_window import MainWindow

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
            if ds.GetNumberOfCells() > 0:
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
def getVtkMesh(foamFilePath: Path, statusConfig: dict):
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


class MeshDock(TabifiedDock):
    reloadMesh = Signal()
    meshLoaded = Signal()

    def __init__(self, parent: Optional['MainWindow'] = None):
        super().__init__(parent)

        self._main_window = parent

        self.setWindowTitle(self.tr("Mesh"))
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self._widget = None
        self._renderer = None
        self._vtkMesh = None

        self.reloadMesh.connect(self.showOpenFoamMesh)

        self._main_window.windowClosed.connect(self._windowClosed)

    def vtkMesh(self):
        return self._vtkMesh

    def clear(self):
        if self._widget is not None:
            self._renderer.RemoveAllViewProps()
            self._widget.Render()

    def closeEvent(self, event):
        if self._widget is not None:
            self._widget.close()
            self._widget = None

    def _windowClosed(self, result):
        self.close()

    @qasync.asyncSlot()
    async def showOpenFoamMesh(self):
        self.clear()

        if self._widget is None:
            self._widget = QVTKRenderWindowInteractor(self)
            self._renderer = vtkRenderer()
            self._widget.GetRenderWindow().AddRenderer(self._renderer)
            self.setWidget(self._widget)

            self._widget.Initialize()
            self._widget.Start()

            self._setBackGroundColor()
            self._addAxes()

        statusConfig = self.buildPatchArrayStatus()

        self._vtkMesh = await asyncio.to_thread(getVtkMesh, FileSystem.foamFilePath(), statusConfig)

        for region in self._vtkMesh:
            if 'boundary' not in self._vtkMesh[region]:  # polyMesh folder in multi-region constant folder
                continue

            for boundary in self._vtkMesh[region]['boundary']:
                actorInfo = self._vtkMesh[region]['boundary'][boundary]
                self._renderer.AddActor(actorInfo.actor)

                actorInfo.actor.GetProperty().SetColor((0.8, 0.8, 0.8))
                actorInfo.actor.GetProperty().SetOpacity(0.9)
                actorInfo.actor.GetProperty().EdgeVisibilityOn()
                actorInfo.actor.GetProperty().SetEdgeColor(0.1, 0.0, 0.3)
                actorInfo.actor.GetProperty().SetLineWidth(1.0)

        self._renderer.ResetCamera()
        self._widget.Render()

        self.meshLoaded.emit()

    def buildPatchArrayStatus(self):
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

    def _setBackGroundColor(self):
        self._renderer.GradientBackgroundOn()
        self._renderer.SetBackground2(0.32, 0.34, 0.43)
        self._renderer.SetBackground(0.90, 0.91, 0.91)

    def _addAxes(self):
        self.actAxes = vtk.vtkAxesActor()

        self.actAxes.SetShaftTypeToCylinder()
        self.actAxes.SetCylinderResolution(4)
        self.actAxes.SetNormalizedShaftLength(0.9, 0.9, 0.9)
        self.actAxes.SetConeResolution(4)
        self.actAxes.SetNormalizedTipLength(0.3, 0.3, 0.3)

        actorAxesX = self.actAxes.GetXAxisCaptionActor2D()
        actorAxesY = self.actAxes.GetYAxisCaptionActor2D()
        actorAxesZ = self.actAxes.GetZAxisCaptionActor2D()

        actorTextAxesX = actorAxesX.GetTextActor()
        actorTextAxesY = actorAxesY.GetTextActor()
        actorTextAxesZ = actorAxesZ.GetTextActor()

        propAxesX = actorAxesX.GetCaptionTextProperty()
        propAxesY = actorAxesY.GetCaptionTextProperty()
        propAxesZ = actorAxesZ.GetCaptionTextProperty()

        actorTextAxesX.SetTextScaleModeToNone()
        actorTextAxesY.SetTextScaleModeToNone()
        actorTextAxesZ.SetTextScaleModeToNone()

        self.actAxes.SetXAxisLabelText('X')
        self.actAxes.SetYAxisLabelText('Y')
        self.actAxes.SetZAxisLabelText('Z')

        self.actAxes.SetNormalizedLabelPosition(1.2, 1.2, 1.2)

        propAxesX.SetFontSize(24)
        propAxesY.SetFontSize(24)
        propAxesZ.SetFontSize(24)

        propAxesX.SetColor(0.1, 0.1, 0.1)
        propAxesY.SetColor(0.1, 0.1, 0.1)
        propAxesZ.SetColor(0.1, 0.1, 0.1)

        self.axes = vtk.vtkOrientationMarkerWidget()
        self.axes.SetViewport(0.0, 0.0, 0.2, 0.2)
        self.axes.SetOrientationMarker(self.actAxes)
        self.axes.SetInteractor(self._widget)

        self.axes.EnabledOn()
        self.axes.InteractiveOn()

        self.actAxes.SetVisibility(True)
