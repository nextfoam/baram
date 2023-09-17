#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio

import qasync
from PySide6.QtWidgets import QMessageBox

from baramSnappy.app import app
from baramSnappy.openfoam.system.topo_set_dict import TopoSetDict
from baramSnappy.openfoam.system.refine_mesh_dict import RefineMeshDict
from baramSnappy.libbaram.run import runUtility
from baramSnappy.libbaram.process import Processor, ProcessError
from baramSnappy.view.step_page import StepPage
from baramSnappy.view.widgets.progress_dialog_simple import ProgressDialogSimple
from .mesh_translate_dialog import MeshTranslateDialog
from .mesh_rotate_dialog import MeshRotateDialog
from .mesh_scale_dialog import MeshScaleDialog
from .volume_refine_dialog import VolumeRefineDialog


class RefinementPage(StepPage):
    OUTPUT_TIME = 4

    def __init__(self, ui):
        super().__init__(ui, ui.refinementPage)

        self._ui = ui
        self._dialog = None
        self._progressDialog = None

        self._connectSignalsSlots()

    def open(self):
        self._reset()

    def _connectSignalsSlots(self):
        self._ui.translate.clicked.connect(self._openTranslateDialog)
        self._ui.rotate_.clicked.connect(self._openRotateDialog)
        self._ui.scale.clicked.connect(self._openScaleDialog)
        self._ui.volumeRefine.clicked.connect(self._openVolumeRefine)
        self._ui.refinementReset.clicked.connect(self._reset)
        self._ui.checkQuality.clicked.connect(self._checkQuality)

    def _openTranslateDialog(self):
        self._dialog = MeshTranslateDialog(self._widget)
        self._dialog.open()
        self._dialog.accepted.connect(self._translate)

    def _openRotateDialog(self):
        self._dialog = MeshRotateDialog(self._widget)
        self._dialog.open()
        self._dialog.accepted.connect(self._rotate)

    def _openScaleDialog(self):
        self._dialog = MeshScaleDialog(self._widget)
        self._dialog.open()
        self._dialog.accepted.connect(self._scale)

    def _openVolumeRefine(self):
        self._dialog = VolumeRefineDialog(self._widget)
        self._dialog.open()
        self._dialog.accepted.connect(self._volumeRefine)

    @qasync.asyncSlot()
    async def _reset(self):
        self.clearResult()

        dialog = ProgressDialogSimple(self._widget, self.tr('Copy Mesh Files for Refinement'))
        dialog.setLabelText(self.tr('Copying Files.'))
        dialog.open()
        await app.fileSystem.copyTimeDrectory(self.OUTPUT_TIME - 1, self.OUTPUT_TIME)
        dialog.close()

    @qasync.asyncSlot()
    async def _checkQuality(self):
        try:
            self.lock()

            console = app.consoleView
            console.clear()

            proc = await runUtility('checkMesh', '-writeAllFields', '-writeAllSurfaceFields',
                                    cwd=app.fileSystem.caseRoot(),
                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            processor = Processor(proc)
            processor.outputLogged.connect(console.append)
            processor.errorLogged.connect(console.appendError)
            await processor.run()
        except ProcessError as e:
            QMessageBox.information(self._widget, self.tr('Error'),
                                    self.tr('Failed to check quality. [') + str(e.returncode) + ']')
        finally:
            self.unlock()

    @qasync.asyncSlot()
    async def _translate(self):
        self._progressDialog = ProgressDialogSimple(self._widget, self.tr('Mesh Translation'))
        self._progressDialog.open()
        self._progressDialog.setLabelText(self.tr('Translating the mesh.'))

        x, y, z = self._dialog.data()
        proc = await runUtility('transformPoints', '-allRegions', '-translate', f'({x} {y} {z})',
                                '-case', app.fileSystem.caseRoot(), cwd=app.fileSystem.caseRoot())

        if returncode := await self._transform(proc):
            self._progressDialog.finish(self.tr('Mesh translation failed. [' + str(returncode) + ']'))
            return

        self._progressDialog.close()

    @qasync.asyncSlot()
    async def _rotate(self):
        self._progressDialog = ProgressDialogSimple(self._widget, self.tr('Mesh Rotation'))
        self._progressDialog.open()
        self._progressDialog.setLabelText(self.tr('Rotating the mesh.'))

        origin, axis, angle = self._dialog.data()
        proc = await runUtility('transformPoints', '-allRegions',
                                '-origin', f'({" ".join(origin)})',
                                '-rotate-angle', f'(({" ".join(axis)}) {angle})',
                                '-case', app.fileSystem.caseRoot(), cwd=app.fileSystem.caseRoot())

        if returncode := await self._transform(proc):
            self._progressDialog.finish(self.tr('Mesh rotation failed. [' + str(returncode) + ']'))
            return

        self._progressDialog.close()

    @qasync.asyncSlot()
    async def _scale(self):
        self._progressDialog = ProgressDialogSimple(self._widget, self.tr('Mesh Scaling'))
        self._progressDialog.open()
        self._progressDialog.setLabelText(self.tr('Scaling the mesh.'))

        x, y, z = self._dialog.data()
        proc = await runUtility('transformPoints', '-allRegions', '-scale', f'({x} {y} {z})',
                                '-case', app.fileSystem.caseRoot(), cwd=app.fileSystem.caseRoot())

        if returncode := await self._transform(proc):
            self._progressDialog.finish(self.tr('Mesh rotation failed. [' + str(returncode) + ']'))
            return

        self._progressDialog.close()

    @qasync.asyncSlot()
    async def _volumeRefine(self):
        try:
            self.lock()

            setName = 'refine'
            source = self._dialog.data()
            source.setName(setName)
            TopoSetDict(source).build().write()
            RefineMeshDict().build(setName).write()

            console = app.consoleView
            console.clear()

            proc = await runUtility('toposet', cwd=app.fileSystem.caseRoot(),
                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            processor = Processor(proc)
            processor.outputLogged.connect(console.append)
            processor.errorLogged.connect(console.appendError)
            await processor.run()

            proc = await runUtility('refineMesh', '-overwrite', cwd=app.fileSystem.caseRoot(),
                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            processor = Processor(proc)
            processor.outputLogged.connect(console.append)
            processor.errorLogged.connect(console.appendError)
            await processor.run()

            progressDialog = ProgressDialogSimple(self._widget, self.tr('Loading Mesh'), False)
            progressDialog.setLabelText(self.tr('Loading Mesh'))
            progressDialog.open()

            meshManager = app.window.meshManager
            meshManager.clear()
            meshManager.progress.connect(progressDialog.setLabelText)
            await meshManager.load()

            progressDialog.close()
        except ProcessError as e:
            await self._reset()
            QMessageBox.information(self._widget, self.tr('Error'),
                                    self.tr('Failed to create cellSet. [') + str(e.returncode) + ']')
        finally:
            self.unlock()

    async def _transform(self, proc):
        if returncode := await proc.wait():
            return returncode

        self._progressDialog.setLabelText(self.tr('Loading Mesh'))

        meshManager = app.window.meshManager
        meshManager.clear()
        meshManager.progress.connect(self._progressDialog.setLabelText)
        await meshManager.load()

        return 0
