#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import subprocess
import sys

import qasync

from libbaram.openfoam.constants import Directory
from libbaram.openfoam.polymesh import removeVoidBoundaries
from libbaram.process import ProcessError
from libbaram.run import RunParallelUtility, RunUtility
from libbaram.utils import rmtree
from resources import resource
from widgets.progress_dialog import ProgressDialog

from baramMesh.app import app
from baramMesh.db.configurations_schema import CFDType
from baramMesh.openfoam.file_system import FileSystem
from baramMesh.openfoam.constant.region_properties import RegionProperties
from baramMesh.openfoam.redistribution_task import RedistributionTask
from baramMesh.openfoam.system.collapse_dict import CollapseDict
from baramMesh.openfoam.system.create_patch_dict import CreatePatchDict
from baramMesh.openfoam.system.extrude_mesh_dict import ExtrudeMeshDict
from baramMesh.openfoam.system.topo_set_dict import TopoSetDict
from baramMesh.openfoam.utility.restore_cyclic_patch_names import RestoreCyclicPatchNames
from baramMesh.view.step_page import StepPage
from .export_dialog import ExportDialog
from .export_2D_plane_dialog import Export2DPlaneDialog
from .export_2D_wedge_dialog import Export2DWedgeDialog


class ExportPage(StepPage):
    OUTPUT_TIME = 4

    def __init__(self, ui):
        super().__init__(ui, ui.exportPage)

        self._dialog = None

        self._connectSignalsSlots()

    def isNextStepAvailable(self):
        return False

    def _connectSignalsSlots(self):
        self._ui.export_.clicked.connect(self._openExport3DDialog)
        self._ui.export2DPlane.clicked.connect(self._openExport2DPlaneDialog)
        self._ui.export2DWedge.clicked.connect(self._openExport2DWedgeDialog)

    def _openExport3DDialog(self):
        self._openExportDialog(ExportDialog(self._widget))

    def _openExport2DPlaneDialog(self):
        self._openExportDialog(Export2DPlaneDialog(self._widget), True)

    def _openExport2DWedgeDialog(self):
        self._openExportDialog(Export2DWedgeDialog(self._widget), True)

    def _openExportDialog(self, dialog, to2d=False):
        self._dialog = dialog
        self._dialog.accepted.connect(lambda: self._export(to2d))
        self._dialog.rejected.connect(self._ui.menubar.repaint)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _export(self, to2d=False):
        path = self._dialog.projectPath()

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

                redistributionTask = RedistributionTask(baramSystem)
                redistributionTask.progress.connect(progressDialog.setLabelText)
                await redistributionTask.reconstruct()
            else:
                if len(regions) > 1:
                    for region in regions.values():
                        shutil.move(self._outputPath() / region.value('name'), baramSystem.constantPath())
                else:
                    shutil.move(self._outputPath() / Directory.POLY_MESH_DIRECTORY_NAME, baramSystem.polyMeshPath())

            # Reorder faces in conformal interfaces
            # (Faces in cyclic boundary pair should match in order)

            NumberOfConformalInterfaces = app.db.elementCount(
                'geometry', lambda i, e: e['cfdType'] == CFDType.INTERFACE.value and not e['interRegion'] and not e['nonConformal'])

            if NumberOfConformalInterfaces > 0:
                prefix = 'NFBRM_'
                CreatePatchDict(prefix, baramSystem).build().write()
                self._cm = RunParallelUtility('createPatch', '-allRegions', '-overwrite', '-case', baramSystem.caseRoot(),
                                              cwd=baramSystem.caseRoot())
                self._cm.output.connect(console.append)
                self._cm.errorOutput.connect(console.appendError)
                await self._cm.start()
                await self._cm.wait()

                rpn = RestoreCyclicPatchNames(prefix, baramSystem)
                rpn.restore()

            if to2d:
                progressDialog.setLabelText(self.tr('Extruding Mesh'))

                regionBoundaries, options = self._dialog.extrudeOptions()
                if len(regions) > 1:
                    for rname, p1, p2 in regionBoundaries:
                        await baramSystem.createRegionSystemDirectory(rname)
                        ExtrudeMeshDict(baramSystem).build(p1, p2, options).write()
                        cm = RunUtility('extrudeMesh', '-region', rname, '-dict', 'system/extrudeMeshDict',
                                                cwd=baramSystem.caseRoot())
                        cm.output.connect(console.append)
                        cm.errorOutput.connect(console.appendError)
                        await cm.start()
                        rc = await cm.wait()
                        if rc != 0:
                            raise ProcessError(rc)
                else:
                    ExtrudeMeshDict(baramSystem).build(regionBoundaries[0][1], regionBoundaries[0][2], options).write()
                    cm = RunUtility('extrudeMesh', cwd=baramSystem.caseRoot())
                    cm.output.connect(console.append)
                    cm.errorOutput.connect(console.appendError)
                    await cm.start()
                    rc = await cm.wait()
                    if rc != 0:
                        raise ProcessError(rc)

                    CollapseDict(baramSystem).create()
                    cm = RunUtility('collapseEdges', '-overwrite', cwd=baramSystem.caseRoot())
                    cm.output.connect(console.append)
                    cm.errorOutput.connect(console.appendError)
                    await cm.start()
                    rc = await cm.wait()
                    if rc != 0:
                        raise ProcessError(rc)

            rmtree(self._outputPath())

            rmtree(baramSystem.polyMeshPath() / 'sets')

            removeVoidBoundaries(baramSystem.caseRoot())

            if self._dialog.isRunBaramFlowChecked():
                progressDialog.close()
                subprocess.Popen([sys.executable, '-m', 'baramFlow.main', path])
            else:
                progressDialog.finish(self.tr('Export completed'))
        except ProcessError as e:
            self.clearResult()
            progressDialog.finish(self.tr('Export failed. [') + str(e.returncode) + ']')
        finally:
            self.unlock()
