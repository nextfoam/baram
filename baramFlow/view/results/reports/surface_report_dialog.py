#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
from pathlib import Path

import qasync
from PySide6.QtWidgets import QDialog

from libbaram import utils
from libbaram.natural_name_uuid import uuidToNnstr
from libbaram.run import runParallelUtility
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog
from widgets.selector_dialog import SelectorDialog

from baramFlow.base.constants import FieldType, VectorComponent, FieldCategory
from baramFlow.base.field import CollateralField, Field, SpecieField, UserScalarField, ALL_PHASES, ALL_SPECIES
from baramFlow.base.material.constants import MaterialType
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.monitor_db import MonitorDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.libbaram.collateral_fields import collateralFieldDict
from baramFlow.openfoam import parallel
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.function_objects import FoDict
from baramFlow.openfoam.function_objects.components import foComponentsReport
from baramFlow.openfoam.function_objects.mag import foMagReport
from baramFlow.openfoam.function_objects.material_fields import foComplementAlphaPhiReport
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType, foSurfaceFieldValueReport
from baramFlow.openfoam.post_processing.post_file_reader import readPostFile
from baramFlow.openfoam.solver import findSolver
from baramFlow.openfoam.solver_field import getSolverComponentName, getSolverFieldName
from baramFlow.services.material.material_service import MaterialService
from baramFlow.services.region.region_service import RegionService
from baramFlow.view.widgets.post_field_selector import loadFieldsComboBox, connectFieldsToComponents

from .surface_report_dialog_ui import Ui_SurfaceReportDialog


class SurfaceReportDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_SurfaceReportDialog()
        self._ui.setupUi(self)

        self._surface = None

        for t in SurfaceReportType:
            text: str = MonitorDB.surfaceReportTypeToText(t) or ''
            self._ui.reportType.addItem(text, t)

        loadFieldsComboBox(self._ui.field)

        self._ui.field.setCurrentIndex(0)

        if ModelsDB.isMultiphaseModelOn():
            self._ui.field.insertItem(0, self.tr('Fluid'), ALL_PHASES)
        else:
            self._ui.field.insertItem(0, self.tr('Fluid'), ALL_SPECIES)

        if self._ui.field.currentIndex() == 0:
            self._ui.field.setCurrentIndex(1)
        self._ui.field.view().setRowHidden(0, True)

        field: Field = self._ui.field.currentData()
        if field.type == FieldType.VECTOR:
            self._ui.fieldComponent.setEnabled(True)
            self._ui.fieldComponent.setCurrentIndex(0)
        else:
            self._ui.fieldComponent.setEnabled(False)

        self._connectSignalsSlots()

        self._load()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectSurface)
        self._ui.reportType.currentIndexChanged.connect(self._updateInputFields)
        self._ui.field.currentIndexChanged.connect(self._updateInputFields)
        self._ui.compute.clicked.connect(self._compute)
        self._ui.close.clicked.connect(self._accept)

        connectFieldsToComponents(self._ui.field, self._ui.fieldComponent)

    def _load(self):
        pass

    @qasync.asyncSlot()
    async def _accept(self):
        self.accept()

    @qasync.asyncSlot()
    async def _compute(self):
        self._ui.compute.setEnabled(False)

        reportType: SurfaceReportType = self._ui.reportType.currentData()

        field: Field = self._ui.field.currentData()
        fieldComponent: VectorComponent = self._ui.fieldComponent.currentData()

        if not self._surface:
            await AsyncMessageBox().information(self, self.tr("Input Error"), self.tr("Select Surface."))
            self._ui.compute.setEnabled(True)
            return

        rname = BoundaryDB.getBoundaryRegion(self._surface)

        seed = uuidToNnstr(uuid.uuid4())

        foName = f'delete_me_{seed}_surface'

        functions = {}

        if isinstance(field, SpecieField):
            if field != ALL_SPECIES:
                if reportType == SurfaceReportType.VOLUME_FLOW_RATE:
                    await AsyncMessageBox().information(
                        self, self.tr("Input Error"),
                        self.tr("Volume Flow Rate does not support individual species."))
                    self._ui.compute.setEnabled(True)
                    return

                region = RegionService.getRegion(rname)
                if (MaterialService.getMaterial(region.material).type != MaterialType.MIXTURE
                        or field.codeName not in MaterialService.getSpeciesInMixture(region.material)):
                    await AsyncMessageBox().information(
                        self, self.tr("Input Error"),
                        self.tr("The region where the material is configured does not contain selected surface."))
                    self._ui.compute.setEnabled(True)
                    return

        if reportType == SurfaceReportType.MASS_FLOW_RATE or reportType == SurfaceReportType.VOLUME_FLOW_RATE:
            solverFieldName = 'phi'

            if field.category == FieldCategory.PHASE:
                db = CoreDBReader()
                region = db.getRegionProperties(rname)
                primary = MaterialService.getMaterial(region.mid)
                secondary = MaterialService.getMaterial(region.secondaryMaterials[0])

                phase = None
                if field == ALL_PHASES:
                    if reportType == SurfaceReportType.MASS_FLOW_RATE:
                        solverFieldName = 'rhoPhi'
                elif findSolver() == 'interFoam' and field.codeName == primary.mid:
                    phase = primary
                    solverFieldName = f'alphaPhi0.{phase.name}'
                    functions[solverFieldName] = foComplementAlphaPhiReport(solverFieldName, secondary.name)
                else:
                    phase = MaterialService.getMaterial(field.codeName)
                    solverFieldName = f'alphaPhi0.{phase.name}'

                functions[foName] = foSurfaceFieldValueReport(BoundaryDB.getBoundaryName(self._surface), solverFieldName, reportType, rname)

                if reportType == SurfaceReportType.MASS_FLOW_RATE and field != ALL_PHASES:
                    functions[foName]['scaleFactor'] = db.getDensity([(phase.mid, 1)],
                                                              region.initialTemperature,
                                                              region.initialPressure)
            elif field.category == FieldCategory.SPECIE:
                functions[foName] = foSurfaceFieldValueReport(
                    BoundaryDB.getBoundaryName(self._surface), solverFieldName, reportType, rname)

                if reportType == SurfaceReportType.VOLUME_FLOW_RATE:
                    # field == ALL_SPECIES (Individual species are not supported)
                    functions[foName]['operation'] = 'weightedSum'
                    functions[foName]['weightField'] = 'faceRho'
                    functions[foName]['inverseWeight'] = 'true'
                elif field != ALL_SPECIES:
                    # reportType == SurfaceReportType.MASS_FLOW_RATE
                    functions[foName]['operation'] = 'weightedSum'
                    functions[foName]['weightField'] = MaterialService.getMaterial(field.codeName).name
        else:
            solverFieldName = getSolverFieldName(field)

            if isinstance(field, CollateralField):
                functions.update(collateralFieldDict([field]))  # FO for generating the collateral field

            elif isinstance(field, UserScalarField):
                if rname != UserDefinedScalarsDB.getRegion(field.codeName):
                    await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                        self.tr("The region where the scalar field is configured does not contain selected surface."))
                    self._ui.compute.setEnabled(True)
                    return

            if field.type == FieldType.SCALAR:
                functions[foName] = foSurfaceFieldValueReport(BoundaryDB.getBoundaryName(self._surface), solverFieldName, reportType, rname)

            else:  # FieldType.VECTOR
                if fieldComponent == VectorComponent.MAGNITUDE:
                    functions['mag1'] = foMagReport(solverFieldName, rname)
                else:
                    functions['components1'] = foComponentsReport(solverFieldName, rname)

                solverComponentName = getSolverComponentName(field, fieldComponent)
                functions[foName] = foSurfaceFieldValueReport(BoundaryDB.getBoundaryName(self._surface), solverComponentName, reportType, rname)

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
            await progressDialog.abort(self.tr('Computing failed 1'))
            self._ui.resultValue.setText('0')
            self._ui.compute.setEnabled(True)
            return

        foPath = FileSystem.postProcessingPath(rname) / foName

        foFiles:  list[Path] = list(foPath.glob('**/surfaceFieldValue.dat'))

        if len(foFiles) < 1:
            await progressDialog.abort(self.tr('Computing failed 2'))
            self._ui.resultValue.setText('0')
            self._ui.compute.setEnabled(True)
            return

        df = readPostFile(foFiles[0])

        self._ui.resultValue.setText(str(df.iloc[0, 0]))

        utils.rmtree(foPath)

        await progressDialog.abort(self.tr('Calculation Completed'))

        self._ui.compute.setEnabled(True)

    def _setSurface(self, surface):
        self._surface = surface
        self._ui.surface.setText(BoundaryDB.getBoundaryText(surface))

    def _selectSurface(self):
        self._dialog = SelectorDialog(self, self.tr("Select Boundary"), self.tr("Select Boundary"),
                                      BoundaryDB.getBoundarySelectorItems())
        self._dialog.accepted.connect(self._surfaceChanged)
        self._dialog.open()

    def _surfaceChanged(self):
        self._setSurface(self._dialog.selectedItem())

    def _updateInputFields(self):
        reportType: SurfaceReportType = self._ui.reportType.currentData()
        isFlowRateType = reportType in [SurfaceReportType.MASS_FLOW_RATE, SurfaceReportType.VOLUME_FLOW_RATE]
        hasMultiMaterials = ModelsDB.isMultiphaseModelOn() or ModelsDB.isSpeciesModelOn()

        # Field Category to keep without hiding
        category = None
        # Hide other category fields only if report type is MASS_FLOW_RATE or VOLUME_FLOW_RATE
        if isFlowRateType:
            if ModelsDB.isMultiphaseModelOn():
                category = FieldCategory.PHASE
            elif ModelsDB.isSpeciesModelOn():
                category = FieldCategory.SPECIE

        self._ui.field.view().setRowHidden(0, not isFlowRateType)   # ALL_PHASES or ALL_SPECIES
        for i in range(1, self._ui.field.count()):
            self._ui.field.view().setRowHidden(i,
                                               category is not None and self._ui.field.itemData(i).category != category)

        if isFlowRateType and not hasMultiMaterials:
            self._ui.field.setCurrentIndex(0)
        else:
            if self._ui.field.view().isRowHidden(self._ui.field.currentIndex()):
                if self._ui.field.currentIndex() == 0:
                    self._ui.field.setCurrentIndex(1)
                else:
                    self._ui.field.setCurrentIndex(0)

        self._ui.field.setEnabled(not isFlowRateType or hasMultiMaterials)

        field: Field = self._ui.field.currentData()
        if field.type == FieldType.VECTOR:
            self._ui.fieldComponent.setEnabled(True)
        else:
            self._ui.fieldComponent.setEnabled(False)
