#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
from pathlib import Path

import qasync

from baramMesh.openfoam.system.collapse_dict import CollapseDict
from baramMesh.openfoam.system.extrude_mesh_dict import ExtrudeMeshDict
from baramMesh.view.export.export_2D_plane_dialog import Export2DPlaneDialog
from baramMesh.view.export.export_2D_wedge_dialog import Export2DWedgeDialog
from libbaram.openfoam.constants import Directory
from libbaram.openfoam.polymesh import removeVoidBoundaries
from libbaram.process import ProcessError
from libbaram.run import RunParallelUtility
from libbaram.utils import rmtree
from resources import resource
from widgets.new_project_dialog import NewProjectDialog
from widgets.progress_dialog import ProgressDialog

from baramMesh.app import app
from baramMesh.openfoam.file_system import FileSystem
from baramMesh.openfoam.constant.region_properties import RegionProperties
from baramMesh.openfoam.redistribution_task import RedistributionTask
from baramMesh.openfoam.system.topo_set_dict import TopoSetDict
from baramMesh.view.step_page import StepPage


class ExportPage(StepPage):
    OUTPUT_TIME = 4

    def __init__(self, ui):
        super().__init__(ui, ui.exportPage)

        self._dialog = None

        self._connectSignalsSlots()

    def isNextStepAvailable(self):
        return False

    def _connectSignalsSlots(self):
        self._ui.export_.clicked.connect(self._openFileDialog)
        self._ui.export2DPlane.clicked.connect(self._openExport2DPlaneDialog)
        self._ui.export2DWedge.clicked.connect(self._openExport2DWedgeDialog)

    @qasync.asyncSlot()
    async def _openFileDialog(self):
        self._dialog = NewProjectDialog(self._widget, self.tr('Export Baram Project'))
        self._dialog.accepted.connect(self._export)
        self._dialog.rejected.connect(self._ui.menubar.repaint)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _openExport2DPlaneDialog(self):
        self._dialog = Export2DPlaneDialog(self._widget)
        self._dialog.accepted.connect(self._export2D)
        self._dialog.rejected.connect(self._ui.menubar.repaint)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _openExport2DWedgeDialog(self):
        self._dialog = Export2DWedgeDialog(self._widget)
        self._dialog.accepted.connect(self._export2D)
        self._dialog.rejected.connect(self._ui.menubar.repaint)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _export(self, to2d=False):
        path = Path(self._dialog.projectLocation())

        progressDialog = ProgressDialog(self._widget, self.tr('Mesh Exporting'))
        progressDialog.setLabelText(self.tr('Preparing'))
        progressDialog.open()

        try:
            self.lock()

            self.clearResult()

            console = app.consoleView
            console.clear()

            fileSystem = app.fileSystem
            parallel = app.project.parallelEnvironment()

            if app.db.elementCount('region') > 1:
                progressDialog.setLabelText(self.tr('Splitting Mesh Regions'))

                cm = RunParallelUtility('splitMeshRegions', '-cellZonesOnly', cwd=fileSystem.caseRoot(), parallel=parallel)
                cm.output.connect(console.append)
                cm.errorOutput.connect(console.appendError)
                await cm.start()
                rc = await cm.wait()
                if rc != 0:
                    raise ProcessError(rc)

            else:  # Single Region. "4" folder was not created by "splitMeshRegions"
                progressDialog.setLabelText(self.tr('Copying Files'))

                lastMeshTime = self.OUTPUT_TIME - 1  # Boundary Layer step
                if not fileSystem.hasPolyMesh(lastMeshTime, parallel.isParallelOn()):
                    lastMeshTime = self.OUTPUT_TIME - 2  # Snap step

                if parallel.isParallelOn():
                    for n in range(parallel.np()):
                        await fileSystem.copyTimeDirectory(lastMeshTime, self.OUTPUT_TIME, n)
                else:
                    await fileSystem.copyTimeDirectory(lastMeshTime, self.OUTPUT_TIME)

            topoSetDict = TopoSetDict().build(TopoSetDict.Mode.CREATE_CELL_ZONES)
            regions = app.db.getElements('region')
            if topoSetDict.isBuilt():
                progressDialog.setLabelText(self.tr('Processing Cell Zones'))
                if len(regions) == 1:
                    topoSetDict.write()

                    cm = RunParallelUtility('topoSet', cwd=fileSystem.caseRoot(), parallel=parallel)
                    cm.output.connect(console.append)
                    cm.errorOutput.connect(console.appendError)
                    await cm.start()
                    rc = await cm.wait()
                    if rc != 0:
                        raise ProcessError(rc)

                else:
                    for region in regions.values():
                        rname = region.value('name')
                        topoSetDict.setRegion(rname).write()

                        cm = RunParallelUtility('topoSet', '-region', rname, cwd=fileSystem.caseRoot(), parallel=parallel)
                        cm.output.connect(console.append)
                        cm.errorOutput.connect(console.appendError)
                        await cm.start()
                        rc = await cm.wait()
                        if rc != 0:
                            raise ProcessError(rc)
            path.mkdir(parents=True, exist_ok=True)
            baramSystem = FileSystem(path)
            baramSystem.createCase(resource.file('openfoam/case'))

            if len(regions) > 1:
                RegionProperties(baramSystem.caseRoot()).build().write()

            progressDialog.setLabelText(self.tr('Exporting Files'))

            if parallel.isParallelOn():
                for n in range(parallel.np()):
                    p = baramSystem.processorPath(n, False)
                    p.mkdir()
                    shutil.move(fileSystem.timePath(self.OUTPUT_TIME, n), p / Directory.CONSTANT_DIRECTORY_NAME)
                #
                # redistributionTask = RedistributionTask(baramSystem)
                # redistributionTask.progress.connect(progressDialog.setLabelText)
                # await redistributionTask.reconstruct()
            else:
                if len(regions) > 1:
                    for region in regions.values():
                        shutil.move(self._outputPath() / region.value('name'), baramSystem.constantPath())
                else:
                    shutil.move(self._outputPath() / Directory.POLY_MESH_DIRECTORY_NAME, baramSystem.polyMeshPath())

            if to2d:
                progressDialog.setLabelText(self.tr('Extruding Mesh'))

                ExtrudeMeshDict(baramSystem).build(self._dialog.extrudeOptions()).write()
                cm = RunParallelUtility('extrudeMesh', cwd=baramSystem.caseRoot(), parallel=parallel)
                cm.output.connect(console.append)
                cm.errorOutput.connect(console.appendError)
                await cm.start()
                rc = await cm.wait()
                if rc != 0:
                    raise ProcessError(rc)

                CollapseDict(baramSystem).create()
                cm = RunParallelUtility('collapseEdges', '-overwrite', cwd=baramSystem.caseRoot(), parallel=parallel)
                cm.output.connect(console.append)
                cm.errorOutput.connect(console.appendError)
                await cm.start()
                rc = await cm.wait()
                if rc != 0:
                    raise ProcessError(rc)

            if parallel.isParallelOn():
                redistributionTask = RedistributionTask(baramSystem)
                redistributionTask.progress.connect(progressDialog.setLabelText)
                await redistributionTask.reconstruct()

            rmtree(self._outputPath())

            rmtree(baramSystem.polyMeshPath() / 'sets')

            removeVoidBoundaries(baramSystem.caseRoot())

            progressDialog.finish(self.tr('Export completed'))
        except ProcessError as e:
            self.clearResult()
            progressDialog.finish(self.tr('Export failed. [') + str(e.returncode) + ']')
        finally:
            self.unlock()

    @qasync.asyncSlot()
    async def _export2D(self):
        await self._export(True)
