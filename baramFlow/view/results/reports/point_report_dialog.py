#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
from pathlib import Path
from typing import Optional

import qasync
from PySide6.QtWidgets import QDialog

from baramFlow.base.constants import VectorComponent, FieldType
from baramFlow.base.field import CollateralField, SpecieField, UserScalarField, Field
from baramFlow.libbaram.collateral_fields import collateralFieldDict
from baramFlow.openfoam.function_objects.read_fields import foReadFieldsReport
from baramFlow.openfoam.solver_field import getSolverFieldName, getSolverComponentName
from libbaram import utils
from libbaram.mesh import Bounds
from libbaram.run import runParallelUtility
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog
from widgets.rendering.point_widget import PointWidget
from widgets.selector_dialog import SelectorDialog

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
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
from baramFlow.view.widgets.post_field_selector import loadFieldsComboBox, connectFieldsToComponents
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

        loadFieldsComboBox(self._ui.field)

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

        connectFieldsToComponents(self._ui.field, self._ui.fieldComponent)

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
        self._ui.compute.setEnabled(False)

        field: Field = self._ui.field.currentData()
        fieldComponent: VectorComponent = self._ui.fieldComponent.currentData()

        coordinate = [float(self._ui.coordinateX.text()),
                      float(self._ui.coordinateY.text()),
                      float(self._ui.coordinateZ.text())]

        rname = _getRegionForPoint(coordinate)
        if rname is None:
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('The point is not in the mesh.'))
            return

        seed = str(uuid.uuid4())

        foName = f'delete_me_{seed}_point'

        functions = {}
        solverFieldName = getSolverFieldName(field)

        if isinstance(field, CollateralField):
            time = FileSystem.latestTime()
            if FileSystem.fieldExists(time, solverFieldName):
                functions[f'readField_{solverFieldName}'] = foReadFieldsReport([solverFieldName], rname)  # FO for reading the collateral field
            else:
                functions.update(collateralFieldDict([field]))  # FO for generating the collateral field

        elif isinstance(field, SpecieField):
            if field.codeName not in RegionDB.getSecondaryMaterials(rname):
                await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                    self.tr("The region where the material is configured does not contain selected surface."))
                self._ui.compute.setEnabled(True)
                return

        elif isinstance(field, UserScalarField):
            if rname != UserDefinedScalarsDB.getRegion(field.codeName):
                await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                    self.tr("The region where the scalar field is configured does not contain selected surface."))
                self._ui.compute.setEnabled(True)
                return

        if field.type == FieldType.SCALAR:
            reportFieldName = solverFieldName

        else:  # FieldType.VECTOR
            if fieldComponent == VectorComponent.MAGNITUDE:
                functions['mag1'] = foMagReport(solverFieldName, rname)
            else:
                functions['components1'] = foComponentsReport(solverFieldName, rname)

            reportFieldName = getSolverComponentName(field, fieldComponent)

        self._ui.resultValue.setText('Calculating...')

        if self._snapOntoBoundary:
            boundary = BoundaryDB.getBoundaryName(self._snapOntoBoundary)
            functions[foName] = foPatchProbesReport(boundary, reportFieldName, coordinate, rname)
        else:
            functions[foName] = foProbesReport(reportFieldName, coordinate, rname)

        data = {
            'functions': functions
        }

        progressDialog = ProgressDialog(self, self.tr('Surface Report'), openDelay=500)
        progressDialog.setLabelText(self.tr('Generating Report...'))
        progressDialog.open()

        foDict = FoDict(f'delete_me_{seed}').build(data)
        foDict.write()

        caseRoot = FileSystem.caseRoot()
        solver = findSolver()
        dictRelativePath = Path(os.path.relpath(foDict.fullPath(), caseRoot)).as_posix()  # "as_posix()": OpenFOAM cannot handle double backward slash separators in parallel processing
        proc = await runParallelUtility(solver, '-postProcess', '-latestTime', '-dict', str(dictRelativePath), parallel=parallel.getEnvironment(), cwd=caseRoot)

        rc = await proc.wait()

        foDict.fullPath().unlink()

        if rc != 0:
            progressDialog.abort(self.tr('Computing failed'))
            self._ui.resultValue.setText('0')
            self._ui.compute.setEnabled(True)
            return

        foPath = FileSystem.postProcessingPath(rname) / foName

        foFiles:  list[Path] = list(foPath.glob(f'**/{reportFieldName}'))

        if len(foFiles) < 1:
            progressDialog.abort(self.tr('Computing failed'))
            self._ui.resultValue.setText('0')
            self._ui.compute.setEnabled(True)

            return

        df = readPostFile(foFiles[0])

        self._ui.resultValue.setText(str(df.iloc[0, 0]))

        utils.rmtree(foPath)

        progressDialog.finish(self.tr('Calculation Completed'))

        self._ui.compute.setEnabled(True)