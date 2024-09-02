#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
from pathlib import Path
from typing import Optional

import qasync
from PySide6.QtWidgets import QDialog

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import MaterialType
from baramFlow.coredb.monitor_db import FieldHelper, Field
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.mesh.vtk_loader import isPointInDataSet
from baramFlow.openfoam import parallel
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.function_objects import FoDict
from baramFlow.openfoam.function_objects.components import foComponentsReport
from baramFlow.openfoam.function_objects.mag import foMagReport
from baramFlow.openfoam.function_objects.patch_probes import foPatchProbesReport
from baramFlow.openfoam.function_objects.probes import foProbesReport
from baramFlow.openfoam.post_processing.post_file_reader import readPostFile
from baramFlow.openfoam.solver import findSolver

from libbaram import utils
from libbaram.mesh import Bounds
from libbaram.run import runParallelUtility

from widgets.async_message_box import AsyncMessageBox
from widgets.rendering.point_widget import PointWidget
from widgets.selector_dialog import SelectorDialog

from .point_report_dialog_ui import Ui_PointReportDialog


def _getRegionForPoint(coordinate: [float, float, float]) -> Optional[str]:
    for rname in coredb.CoreDB().getRegions():
        if isPointInDataSet(coordinate, app.internalMeshActor(rname).dataSet):
            return rname

    return None


class PointReportDialog(QDialog):
    TEXT_FOR_NONE_BOUNDARY = 'None'

    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_PointReportDialog()
        self._ui.setupUi(self)

        self._snapOntoBoundary = None

        self._renderingView = app.renderingView.view()
        self._bounds = Bounds(*self._renderingView.getBounds())
        self._pointWidget = PointWidget(self._renderingView)

        self._setupFieldCombo(FieldHelper.getAvailableFields())

        self._pointWidget.outlineOff()
        self._pointWidget.setBounds(self._bounds)

        self._connectSignalsSlots()

        self._load()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectSnapOntoBoundary)
        self._ui.coordinateX.editingFinished.connect(self._movePointWidget)
        self._ui.coordinateY.editingFinished.connect(self._movePointWidget)
        self._ui.coordinateZ.editingFinished.connect(self._movePointWidget)
        self._ui.compute.clicked.connect(self._compute)
        self._ui.close.clicked.connect(self._accept)

    def _load(self):
        self._ui.coordinateX.setText('0')
        self._ui.coordinateY.setText('0')
        self._ui.coordinateZ.setText('0')

        self._setSnapOntoBoundary(None)

        self._movePointWidget()
        self._pointWidget.on()

    @qasync.asyncSlot()
    async def _accept(self):
        self._pointWidget.off()

        self.accept()

    def _setSnapOntoBoundary(self, bcid):
        self._snapOntoBoundary = bcid
        if bcid is None:
            self._ui.snapOntoBoundary.setText(self.TEXT_FOR_NONE_BOUNDARY)
        else:
            self._ui.snapOntoBoundary.setText(BoundaryDB.getBoundaryText(bcid))

    def _selectSnapOntoBoundary(self):
        self._dialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                      BoundaryDB.getBoundarySelectorItems(), self.TEXT_FOR_NONE_BOUNDARY)
        self._dialog.accepted.connect(self._snapOntoBoundaryChanged)
        self._dialog.open()

    def _snapOntoBoundaryChanged(self):
        self._setSnapOntoBoundary(self._dialog.selectedItem())

    def _setupFieldCombo(self, fields):
        for f in fields:
            self._ui.field.addItem(f.text, f.key)

    def _movePointWidget(self):
        try:
            point = (
                float(self._ui.coordinateX.text()),
                float(self._ui.coordinateY.text()),
                float(self._ui.coordinateZ.text())
            )

            if self._bounds.includes(point):
                self._pointWidget.setPosition(*point)
                self._pointWidget.on()
            else:
                self._pointWidget.off()

        except Exception:
            self._pointWidget.off()

    @qasync.asyncSlot()
    async def _compute(self):
        coordinate = [float(self._ui.coordinateX.text()),
                      float(self._ui.coordinateY.text()),
                      float(self._ui.coordinateZ.text())]

        rname = _getRegionForPoint(coordinate)
        if rname is None:
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('The point is not in the mesh.'))
            return

        fieldKey: FieldHelper.FieldItem.DBFieldKey = self._ui.field.currentData()
        fieldType = fieldKey.field
        fieldID = fieldKey.id

        if fieldType == Field.SCALAR and rname != UserDefinedScalarsDB.getRegion(fieldID):
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('The region where the scalar field is configured does not contain selected Point.'))
            return

        primary = RegionDB.getMaterial(rname)
        if fieldType == Field.MATERIAL:
            mid = fieldID
            if MaterialDB.getType(mid) == MaterialType.SPECIE:
                if mid not in MaterialDB.getSpecies(primary):
                    await AsyncMessageBox().information(
                        self, self.tr('Input Error'),
                        self.tr('The region where the specie is configured does not contain selected Point.'))
                    return
            elif mid != primary and mid not in RegionDB.getSecondaryMaterials(rname):
                await AsyncMessageBox().information(
                    self, self.tr('Input Error'),
                    self.tr('The region where the material is configured does not contain selected Point.'))
                return

        field = FieldHelper.DBFieldKeyToField(fieldType, fieldID)

        self._ui.compute.setEnabled(False)

        self._ui.resultValue.setText('Calculating...')

        seed = str(uuid.uuid4())

        foName = f'delete_me_{seed}_point'

        functions = {}

        if field == 'mag(U)':
            functions['mag1'] = foMagReport('U')
        elif field in ('Ux', 'Uy', 'Uz'):
            functions['components1'] = foComponentsReport('U')

        if self._snapOntoBoundary:
            boundary = BoundaryDB.getBoundaryName(self._snapOntoBoundary)
            functions[foName] = foPatchProbesReport(boundary, field, coordinate, rname)
        else:
            functions[foName] = foProbesReport(field, coordinate, rname)

        data = {
            'functions': functions
        }

        foDict = FoDict(f'delete_me_{seed}').build(data)
        foDict.write()

        caseRoot = FileSystem.caseRoot()
        solver = findSolver()
        dictRelativePath = Path(os.path.relpath(foDict.fullPath(), caseRoot)).as_posix()  # "as_posix()": OpenFOAM cannot handle double backward slash separators in parallel processing
        proc = await runParallelUtility(solver, '-postProcess', '-latestTime', '-dict', str(dictRelativePath), parallel=parallel.getEnvironment(), cwd=caseRoot)

        rc = await proc.wait()

        foDict.fullPath().unlink()

        if rc != 0:
            await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Computing failed'))
            self._ui.resultValue.setText('0')
            self._ui.compute.setEnabled(True)
            return

        foPath = FileSystem.postProcessingPath(rname) / foName

        foFiles:  list[Path] = list(foPath.glob(f'**/{field}'))

        if len(foFiles) < 1:
            await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Computing failed'))
            self._ui.resultValue.setText('0')
            self._ui.compute.setEnabled(True)

            return

        df = readPostFile(foFiles[0])

        self._ui.resultValue.setText(str(df.iloc[0, 0]))

        utils.rmtree(foPath)

        self._ui.compute.setEnabled(True)