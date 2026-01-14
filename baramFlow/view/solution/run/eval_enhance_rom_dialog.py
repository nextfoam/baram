#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid
from typing import Any, Dict, List

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QCheckBox,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QDialogButtonBox,
)
from PySide6.QtGui import QDoubleValidator

from baramFlow.base.constants import VectorComponent
from baramFlow.base.field import Field
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.monitor_db import MonitorDB
from baramFlow.coredb.monitor_db import DirectionSpecificationMethod
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType
from baramFlow.view.widgets.post_field_selector import (
    loadFieldsComboBox,
    connectFieldsToComponents,
)
from baramFlow.view.widgets.region_objects_selector import BoundariesSelector
from baramFlow.view.widgets.vector_component_combo_box import VectorComponentComboBox
from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog
from .eval_enhance_rom_dialog_ui import Ui_EvalNEnhanceROMDialog


class ForceTargetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Force coefficients"))
        layout = QVBoxLayout(self)

        self._rname: str | None = None
        self._boundaries: list[int] = []

        form = QFormLayout()

        self._lblRegion = QLabel(self.tr("-"), self)
        self._lblBoundaries = QLabel(self.tr("Not selected"), self)
        self._lblBoundaries.setMinimumWidth(160)

        surfaceRow = QHBoxLayout()
        self._btnSelect = QPushButton(self.tr("Select..."), self)
        surfaceRow.addWidget(self._lblBoundaries, 1)
        surfaceRow.addWidget(self._btnSelect)

        form.addRow(self.tr("Region:"), self._lblRegion)
        form.addRow(self.tr("Boundaries:"), surfaceRow)

        self._methodCombo = QComboBox(self)
        self._methodCombo.addItem(
            self.tr("Direct"),
            DirectionSpecificationMethod.DIRECT,
        )
        self._methodCombo.addItem(
            self.tr("AOA and AOS"),
            DirectionSpecificationMethod.AOA_AOS,
        )
        form.addRow(self.tr("Direction spec.:"), self._methodCombo)

        validator = QDoubleValidator(self)

        self._dragDirXEdit = QLineEdit(self)
        self._dragDirYEdit = QLineEdit(self)
        self._dragDirZEdit = QLineEdit(self)
        self._dragDirXEdit.setText("1.0")
        self._dragDirYEdit.setText("0.0")
        self._dragDirZEdit.setText("0.0")
        for w in (self._dragDirXEdit, self._dragDirYEdit, self._dragDirZEdit):
            w.setValidator(validator)

        dragRowWidget = QWidget(self)
        dragRowLayout = QHBoxLayout(dragRowWidget)
        dragRowLayout.setContentsMargins(0, 0, 0, 0)
        dragRowLayout.addWidget(self._dragDirXEdit)
        dragRowLayout.addWidget(self._dragDirYEdit)
        dragRowLayout.addWidget(self._dragDirZEdit)
        form.addRow(self.tr("Drag dir. (x,y,z):"), dragRowWidget)

        self._liftDirXEdit = QLineEdit(self)
        self._liftDirYEdit = QLineEdit(self)
        self._liftDirZEdit = QLineEdit(self)
        self._liftDirXEdit.setText("0.0")
        self._liftDirYEdit.setText("1.0")
        self._liftDirZEdit.setText("0.0")
        for w in (self._liftDirXEdit, self._liftDirYEdit, self._liftDirZEdit):
            w.setValidator(validator)

        liftRowWidget = QWidget(self)
        liftRowLayout = QHBoxLayout(liftRowWidget)
        liftRowLayout.setContentsMargins(0, 0, 0, 0)
        liftRowLayout.addWidget(self._liftDirXEdit)
        liftRowLayout.addWidget(self._liftDirYEdit)
        liftRowLayout.addWidget(self._liftDirZEdit)
        form.addRow(self.tr("Lift dir. (x,y,z):"), liftRowWidget)

        self._lblAngles = QLabel(self.tr("AoA / AoS (deg):"), self)
        self._aoaEdit = QLineEdit(self)
        self._aosEdit = QLineEdit(self)
        for w in (self._aoaEdit, self._aosEdit):
            w.setValidator(validator)
            w.setText("0.0")

        anglesRowWidget = QWidget(self)
        anglesRowLayout = QHBoxLayout(anglesRowWidget)
        anglesRowLayout.setContentsMargins(0, 0, 0, 0)
        anglesRowLayout.addWidget(self._aoaEdit)
        anglesRowLayout.addWidget(self._aosEdit)

        form.addRow(self._lblAngles, anglesRowWidget)

        self._corXEdit = QLineEdit(self)
        self._corYEdit = QLineEdit(self)
        self._corZEdit = QLineEdit(self)
        for w in (self._corXEdit, self._corYEdit, self._corZEdit):
            w.setValidator(validator)
            w.setText("0.0")

        corRowWidget = QWidget(self)
        corRowLayout = QHBoxLayout(corRowWidget)
        corRowLayout.setContentsMargins(0, 0, 0, 0)
        corRowLayout.addWidget(self._corXEdit)
        corRowLayout.addWidget(self._corYEdit)
        corRowLayout.addWidget(self._corZEdit)
        form.addRow(self.tr("Center of rotation:"), corRowWidget)

        self._chkLift = QCheckBox(self.tr("Lift coefficient"), self)
        self._chkDrag = QCheckBox(self.tr("Drag coefficient"), self)
        self._chkMoment = QCheckBox(self.tr("Pitching moment"), self)

        self._chkLift.setChecked(True)
        self._chkDrag.setChecked(True)
        self._chkMoment.setChecked(False)

        qtyRowWidget = QWidget(self)
        qtyRowLayout = QHBoxLayout(qtyRowWidget)
        qtyRowLayout.setContentsMargins(0, 0, 0, 0)
        qtyRowLayout.addWidget(self._chkLift)
        qtyRowLayout.addWidget(self._chkDrag)
        qtyRowLayout.addWidget(self._chkMoment)

        form.addRow(self.tr("Quantities:"), qtyRowWidget)

        layout.addLayout(form)

        btnBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        btnBox.accepted.connect(self.accept)
        btnBox.rejected.connect(self.reject)
        layout.addWidget(btnBox)

        self._btnSelect.clicked.connect(self._selectBoundaries)
        self._methodCombo.currentIndexChanged.connect(self._specMethodChanged)

        self._specMethodChanged(self._methodCombo.currentIndex())

    def _selectBoundaries(self):
        dlg = BoundariesSelector(self, self._boundaries)
        dlg.accepted.connect(lambda: self._boundariesChanged(dlg))
        dlg.open()

    def _boundariesChanged(self, dlg: BoundariesSelector):
        self._rname = dlg.region()
        self._boundaries = dlg.selectedItems() or []

        if self._boundaries:
            if self._rname:
                self._lblRegion.setText(self._rname)
            else:
                self._lblRegion.setText("-")
            names = [BoundaryDB.getBoundaryText(bcid) for bcid in self._boundaries]
            self._lblBoundaries.setText(", ".join(names))
        else:
            self._lblRegion.setText("-")
            self._lblBoundaries.setText(self.tr("Not selected"))

    def _specMethodChanged(self, index: int):
        method = self._methodCombo.itemData(index)
        useAngles = method == DirectionSpecificationMethod.AOA_AOS

        self._lblAngles.setVisible(useAngles)
        self._aoaEdit.setVisible(useAngles)
        self._aosEdit.setVisible(useAngles)

    def accept(self):
        if not self._boundaries:
            AsyncMessageBox().warning(
                self,
                self.tr("No boundary selected"),
                self.tr("Please select at least one boundary."),
            )
            return
        super().accept()

    def config(self) -> Dict[str, Any]:
        dragDir = [
            float(self._dragDirXEdit.text()),
            float(self._dragDirYEdit.text()),
            float(self._dragDirZEdit.text()),
        ]
        liftDir = [
            float(self._liftDirXEdit.text()),
            float(self._liftDirYEdit.text()),
            float(self._liftDirZEdit.text()),
        ]
        cofr = [
            float(self._corXEdit.text()),
            float(self._corYEdit.text()),
            float(self._corZEdit.text()),
        ]

        method = self._methodCombo.currentData()

        aoa = float(self._aoaEdit.text())
        aos = float(self._aosEdit.text())

        boundaryNames = [
            BoundaryDB.getBoundaryName(bcid) for bcid in self._boundaries
        ]

        return {
            "region": self._rname,
            "boundaryIds": list(self._boundaries),
            "boundaries": boundaryNames,
            "directionMethod": method,
            "dragDirection": dragDir,
            "liftDirection": liftDir,
            "centerOfRotation": cofr,
            "AoA": aoa,
            "AoS": aos,
            "metrics": {
                "lift": self._chkLift.isChecked(),
                "drag": self._chkDrag.isChecked(),
                "moment": self._chkMoment.isChecked(),
            },
        }

    def summaryText(self) -> str:
        if self._boundaries:
            btxt = ", ".join(
                BoundaryDB.getBoundaryText(bcid) for bcid in self._boundaries
            )
        else:
            btxt = self.tr("No boundary")

        if self._rname:
            location = f"{self._rname}: {btxt}"
        else:
            location = btxt

        m = []
        if self._chkLift.isChecked():
            m.append("Cl")
        if self._chkDrag.isChecked():
            m.append("Cd")
        if self._chkMoment.isChecked():
            m.append("Cm")

        if m:
            mtxt = "/".join(m)
        else:
            mtxt = self.tr("none")

        return f"{location}  [{mtxt}]"


class PointTargetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Point value"))
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._xEdit = QLineEdit(self)
        self._yEdit = QLineEdit(self)
        self._zEdit = QLineEdit(self)

        validator = QDoubleValidator(self)

        for w in (self._xEdit, self._yEdit, self._zEdit):
            w.setValidator(validator)
            w.setText("0.0")

        self._fieldCombo = QComboBox(self)
        self._componentCombo = VectorComponentComboBox(self)

        loadFieldsComboBox(self._fieldCombo)
        connectFieldsToComponents(self._fieldCombo, self._componentCombo)

        self.TEXT_FOR_NONE_BOUNDARY = "None"
        self._snapOntoBoundary: int = None

        self._lblSnap = QLabel(self.TEXT_FOR_NONE_BOUNDARY, self)
        self._btnSelectSnap = QPushButton(self.tr("Select..."), self)
        self._btnSelectSnap.clicked.connect(self._selectSnapBoundary)

        self._snapRowWidget = QWidget(self)
        snapRowLayout = QHBoxLayout(self._snapRowWidget)
        snapRowLayout.setContentsMargins(0, 0, 0, 0)
        snapRowLayout.addWidget(self._lblSnap, 1)
        snapRowLayout.addWidget(self._btnSelectSnap)

        form.addRow("x:", self._xEdit)
        form.addRow("y:", self._yEdit)
        form.addRow("z:", self._zEdit)
        form.addRow("Field:", self._fieldCombo)
        form.addRow("Component:", self._componentCombo)
        form.addRow("Snap:", self._snapRowWidget)

        layout.addLayout(form)

        btnBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        btnBox.accepted.connect(self.accept)
        btnBox.rejected.connect(self.reject)
        layout.addWidget(btnBox)

    def _setSnapBoundary(self, bcid: int | None):
        self._snapOntoBoundary = bcid
        if bcid is None:
            self._lblSnap.setText(self.TEXT_FOR_NONE_BOUNDARY)
        else:
            self._lblSnap.setText(BoundaryDB.getBoundaryText(bcid))

    def _selectSnapBoundary(self):
        dlg = SelectorDialog(
            self,
            self.tr("Select Boundary"),
            self.tr("Select Boundary"),
            BoundaryDB.getBoundarySelectorItems(),
            self.TEXT_FOR_NONE_BOUNDARY,
        )
        dlg.accepted.connect(lambda: self._setSnapBoundary(dlg.selectedItem()))
        dlg.open()

    def config(self) -> Dict[str, Any]:
        coord = [
            float(self._xEdit.text()),
            float(self._yEdit.text()),
            float(self._zEdit.text()),
        ]

        field: Field = self._fieldCombo.currentData()
        fieldComponent: VectorComponent = self._componentCombo.currentData()

        return {
            "coordinate": coord,
            "field": field,
            "fieldComponent": fieldComponent,
            "snapOntoBoundary": self._snapOntoBoundary,
        }

    def summaryText(self) -> str:
        cfg = self.config()
        c = cfg["coordinate"]
        fieldLabel = self._fieldCombo.currentText() or "?"
        return f"{fieldLabel} @ ({c[0]:g}, {c[1]:g}, {c[2]:g})"


class SurfaceTargetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Surface field value"))
        layout = QVBoxLayout(self)

        self._surfaceId: int | None = None

        form = QFormLayout()

        surfaceRow = QHBoxLayout()
        self._surfaceEdit = QLineEdit(self)
        self._surfaceEdit.setReadOnly(True)
        self._btnSelectSurface = QPushButton(self.tr("Select..."), self)
        surfaceRow.addWidget(self._surfaceEdit, 1)
        surfaceRow.addWidget(self._btnSelectSurface)

        self._fieldCombo = QComboBox(self)
        self._reportTypeCombo = QComboBox(self)
        self._componentCombo = VectorComponentComboBox(self)

        loadFieldsComboBox(self._fieldCombo)
        connectFieldsToComponents(self._fieldCombo, self._componentCombo)

        for t in SurfaceReportType:
            text: str = MonitorDB.surfaceReportTypeToText(t) or ""
            self._reportTypeCombo.addItem(text, t)

        form.addRow(self.tr("Surface:"), surfaceRow)
        form.addRow(self.tr("Field:"), self._fieldCombo)
        form.addRow(self.tr("Report type:"), self._reportTypeCombo)
        form.addRow(self.tr("Component:"), self._componentCombo)

        layout.addLayout(form)

        btnBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        btnBox.accepted.connect(self.accept)
        btnBox.rejected.connect(self.reject)
        layout.addWidget(btnBox)

        self._btnSelectSurface.clicked.connect(self._selectSurface)

    def _selectSurface(self):
        dlg = SelectorDialog(
            self,
            self.tr("Select Boundary"),
            self.tr("Select Boundary"),
            BoundaryDB.getBoundarySelectorItems(),
        )
        dlg.accepted.connect(lambda: self._surfaceChanged(dlg))
        dlg.open()

    def _surfaceChanged(self, dlg: SelectorDialog):
        self._surfaceId = dlg.selectedItem()
        if self._surfaceId is not None:
            self._surfaceEdit.setText(BoundaryDB.getBoundaryText(self._surfaceId))
        else:
            self._surfaceEdit.clear()

    def accept(self):
        if self._surfaceId is None and not self._surfaceEdit.text().strip():
            AsyncMessageBox().warning(
                self,
                self.tr("No surface selected"),
                self.tr("Please select a surface."),
            )
            return
        super().accept()

    def config(self) -> Dict[str, Any]:
        field: Field = self._fieldCombo.currentData()
        fieldComponent: VectorComponent = self._componentCombo.currentData()
        reportType: SurfaceReportType = self._reportTypeCombo.currentData()

        surface = self._surfaceId

        return {
            "surface": surface,
            "reportType": reportType,
            "field": field,
            "fieldComponent": fieldComponent,
        }

    def summaryText(self) -> str:
        cfg = self.config()
        rtype = cfg["reportType"] or "?"
        f = cfg["field"] or "?"
        s = cfg["surface"] or "?"
        surfaceName = BoundaryDB.getBoundaryText(s)
        return f"{rtype} of {f} @ {surfaceName}"


class VolumeTargetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Volume field value"))
        layout = QVBoxLayout(self)

        self._volumeId: int | None = None

        form = QFormLayout()

        volumeRow = QHBoxLayout()
        self._volumeEdit = QLineEdit(self)
        self._volumeEdit.setReadOnly(True)
        self._btnSelectVolume = QPushButton(self.tr("Select..."), self)
        volumeRow.addWidget(self._volumeEdit, 1)
        volumeRow.addWidget(self._btnSelectVolume)

        self._fieldCombo = QComboBox(self)
        self._reportTypeCombo = QComboBox(self)
        self._componentCombo = VectorComponentComboBox(self)

        loadFieldsComboBox(self._fieldCombo)
        connectFieldsToComponents(self._fieldCombo, self._componentCombo)

        for t in VolumeReportType:
            text = MonitorDB.volumeReportTypeToText(t)
            self._reportTypeCombo.addItem(text, t)

        form.addRow(self.tr("Volume zone:"), volumeRow)
        form.addRow(self.tr("Field:"), self._fieldCombo)
        form.addRow(self.tr("Report type:"), self._reportTypeCombo)
        form.addRow(self.tr("Component:"), self._componentCombo)

        layout.addLayout(form)

        btnBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        btnBox.accepted.connect(self.accept)
        btnBox.rejected.connect(self.reject)
        layout.addWidget(btnBox)

        self._btnSelectVolume.clicked.connect(self._selectVolume)

    def _selectVolume(self):
        dlg = SelectorDialog(
            self,
            self.tr("Select Cell Zone"),
            self.tr("Select Cell Zone"),
            CellZoneDB.getCellZoneSelectorItems(),
        )
        dlg.accepted.connect(lambda: self._volumeChanged(dlg))
        dlg.open()

    def _volumeChanged(self, dlg: SelectorDialog):
        self._volumeId = dlg.selectedItem()
        if self._volumeId is not None:
            self._volumeEdit.setText(CellZoneDB.getCellZoneText(self._volumeId))
        else:
            self._volumeEdit.clear()

    def accept(self):
        if self._volumeId is None and not self._volumeEdit.text().strip():
            AsyncMessageBox().warning(
                self,
                self.tr("No volume selected"),
                self.tr("Please select a volume zone."),
            )
            return
        super().accept()

    def config(self) -> Dict[str, Any]:
        field: Field = self._fieldCombo.currentData()
        fieldComponent: VectorComponent = self._componentCombo.currentData()
        reportType: VolumeReportType = self._reportTypeCombo.currentData()

        return {
            "volume": self._volumeId,
            "reportType": reportType,
            "field": field,
            "fieldComponent": fieldComponent,
        }

    def summaryText(self) -> str:
        cfg = self.config()
        rtype = cfg["reportType"] or "?"
        f = cfg["field"] or "?"
        v = cfg["volume"] or "?"
        volumeName = CellZoneDB.getCellZoneText(v)
        return f"{rtype} of {f} @ {volumeName}"


class EvalItemWidget(QWidget):
    removed = Signal(uuid.UUID)
    changed = Signal()

    def __init__(self, item_id: uuid.UUID, meta: dict, parent: QWidget | None = None):
        super().__init__(parent)

        self._id = item_id
        self._meta = meta
        self._config: Dict[str, Any] = {}

        self._buildUi()

    def _buildUi(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._chkEnabled = QCheckBox(self)
        self._chkEnabled.setChecked(True)

        self._lblName = QLabel(self._meta.get("label", ""), self)
        self._lblTarget = QLabel(self.tr("Not selected"), self)
        self._lblTarget.setMinimumWidth(160)

        self._btnSelect = QPushButton(self.tr("Modify..."), self)
        self._btnDelete = QPushButton(self.tr("Delete"), self)

        layout.addWidget(self._chkEnabled)
        layout.addWidget(self._lblName)
        layout.addWidget(self._lblTarget, 1)
        layout.addWidget(self._btnSelect)
        layout.addWidget(self._btnDelete)

        self._btnSelect.clicked.connect(self._onSelect)
        self._btnDelete.clicked.connect(self._onDelete)

    @property
    def itemId(self) -> uuid.UUID:
        return self._id

    def toDict(self) -> Dict[str, Any]:
        return {
            "id": str(self._id),
            "enabled": self._chkEnabled.isChecked(),
            "label": self._meta.get("label"),
            "category": self._meta.get("category"),
            "metric": self._meta.get("metric"),
            "config": self._config,
        }

    def _onDelete(self):
        self.removed.emit(self._id)

    def _onSelect(self):
        category = self._meta.get("category")

        if category == "forceCoeff":
            self._selectForce()
        elif category == "point":
            self._selectPoint()
        elif category == "surface":
            self._selectSurface()
        elif category == "volume":
            self._selectVolume()

    def _selectForce(self):
        dlg = ForceTargetDialog(self)

        hadConfig = bool(self._config)
        if hadConfig:
            rname = self._config.get("region")
            boundaryIds = self._config.get("boundaryIds") or []

            dlg._rname = rname
            dlg._boundaries = list(boundaryIds)

            if dlg._boundaries:
                if dlg._rname:
                    dlg._lblRegion.setText(dlg._rname)
                else:
                    dlg._lblRegion.setText("-")
                names = [
                    BoundaryDB.getBoundaryText(bcid)
                    for bcid in dlg._boundaries
                ]
                dlg._lblBoundaries.setText(", ".join(names))
            else:
                dlg._lblRegion.setText("-")
                dlg._lblBoundaries.setText(self.tr("Not selected"))

            method= self._config.get("directionMethod")
            if method:
                for i in range(dlg._methodCombo.count()):
                    m = dlg._methodCombo.itemData(i)
                    if m == method:
                        dlg._methodCombo.setCurrentIndex(i)
                        break

            dragDir = self._config.get("dragDirection") or [0.0, 0.0, 0.0]
            liftDir = self._config.get("liftDirection") or [0.0, 0.0, 0.0]
            cofr = self._config.get("centerOfRotation") or [0.0, 0.0, 0.0]

            dlg._dragDirXEdit.setText(str(dragDir[0]))
            dlg._dragDirYEdit.setText(str(dragDir[1]))
            dlg._dragDirZEdit.setText(str(dragDir[2]))

            dlg._liftDirXEdit.setText(str(liftDir[0]))
            dlg._liftDirYEdit.setText(str(liftDir[1]))
            dlg._liftDirZEdit.setText(str(liftDir[2]))

            dlg._corXEdit.setText(str(cofr[0]))
            dlg._corYEdit.setText(str(cofr[1]))
            dlg._corZEdit.setText(str(cofr[2]))

            aoa = self._config.get("AoA")
            aos = self._config.get("AoS")
            if aoa is not None:
                dlg._aoaEdit.setText(str(aoa))
            if aos is not None:
                dlg._aosEdit.setText(str(aos))

            metrics = self._config.get("metrics") or {}
            dlg._chkLift.setChecked(bool(metrics.get("lift", True)))
            dlg._chkDrag.setChecked(bool(metrics.get("drag", True)))
            dlg._chkMoment.setChecked(bool(metrics.get("moment", False)))

            dlg._specMethodChanged(dlg._methodCombo.currentIndex())

        if dlg.exec() == QDialog.Accepted:
            self._config = dlg.config()
            self._lblTarget.setText(dlg.summaryText())
            self.changed.emit()
        else:
            if not hadConfig:
                self.removed.emit(self._id)

    def _selectPoint(self):
        dlg = PointTargetDialog(self)

        hadConfig = bool(self._config)
        if hadConfig:
            coordinate = self._config.get("coordinate") or [0.0, 0.0, 0.0]
            field = self._config.get("field")
            fieldComponent = self._config.get("fieldComponent")
            snapOntoBoundary = self._config.get("snapOntoBoundary")

            dlg._xEdit.setText(str(coordinate[0]))
            dlg._yEdit.setText(str(coordinate[1]))
            dlg._zEdit.setText(str(coordinate[2]))

            if field:
                for i in range(dlg._fieldCombo.count()):
                    f: Field | None = dlg._fieldCombo.itemData(i)
                    if f == field:
                        dlg._fieldCombo.setCurrentIndex(i)
                        break

            if fieldComponent:
                for i in range(dlg._componentCombo.count()):
                    v = dlg._componentCombo.itemData(i)
                    if v == fieldComponent:
                        dlg._componentCombo.setCurrentIndex(i)
                        break

            dlg._setSnapBoundary(snapOntoBoundary)

        if dlg.exec() == QDialog.Accepted:
            self._config = dlg.config()
            self._lblTarget.setText(dlg.summaryText())
            self.changed.emit()
        else:
            if not hadConfig:
                self.removed.emit(self._id)

    def _selectSurface(self):
        dlg = SurfaceTargetDialog(self)

        hadConfig = bool(self._config)
        if hadConfig:
            field = self._config.get("field")
            reportType = self._config.get("reportType")
            fieldComponent = self._config.get("fieldComponent")
            surface = self._config.get("surface") or ""

            dlg._surfaceEdit.setText(BoundaryDB.getBoundaryText(surface))

            if field:
                for i in range(dlg._fieldCombo.count()):
                    f = dlg._fieldCombo.itemData(i)
                    if f == field:
                        dlg._fieldCombo.setCurrentIndex(i)
                        break

            if reportType:
                for i in range(dlg._reportTypeCombo.count()):
                    t = dlg._reportTypeCombo.itemData(i)
                    if t == reportType:
                        dlg._reportTypeCombo.setCurrentIndex(i)
                        break

            if fieldComponent:
                for i in range(dlg._componentCombo.count()):
                    v = dlg._componentCombo.itemData(i)
                    if v == fieldComponent:
                        dlg._componentCombo.setCurrentIndex(i)
                        break

        if dlg.exec() == QDialog.Accepted:
            self._config = dlg.config()
            self._lblTarget.setText(dlg.summaryText())
            self.changed.emit()
        else:
            if not hadConfig:
                self.removed.emit(self._id)

    def _selectVolume(self):
        dlg = VolumeTargetDialog(self)

        hadConfig = bool(self._config)
        if hadConfig:
            field = self._config.get("field")
            reportType = self._config.get("reportType")
            fieldComponent = self._config.get("fieldComponent")
            volume = self._config.get("volume") or ""

            dlg._volumeEdit.setText(CellZoneDB.getCellZoneText(volume))

            if field:
                for i in range(dlg._fieldCombo.count()):
                    f = dlg._fieldCombo.itemData(i)
                    if f == field:
                        dlg._fieldCombo.setCurrentIndex(i)
                        break

            if reportType:
                for i in range(dlg._reportTypeCombo.count()):
                    t = dlg._reportTypeCombo.itemData(i)
                    if t == reportType:
                        dlg._reportTypeCombo.setCurrentIndex(i)
                        break

            if fieldComponent:
                for i in range(dlg._componentCombo.count()):
                    v = dlg._componentCombo.itemData(i)
                    if v == fieldComponent:
                        dlg._componentCombo.setCurrentIndex(i)
                        break

        if dlg.exec() == QDialog.Accepted:
            self._config = dlg.config()
            self._lblTarget.setText(dlg.summaryText())
            self.changed.emit()
        else:
            if not hadConfig:
                self.removed.emit(self._id)


class EvalNEnhanceROMDialog(QDialog):
    settingsCompleted = Signal(int, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_EvalNEnhanceROMDialog()
        self._ui.setupUi(self)

        self._ui.spnNumEval.setMinimum(1)
        self._ui.spnNumEval.setMaximum(999)
        self._ui.spnNumEval.setValue(1)

        self._rows: Dict[uuid.UUID, EvalItemWidget] = {}

        self._buildDynamicArea()
        self._connectSignalsSlots()

    def _buildDynamicArea(self):
        self._cmbType = self._ui.cmbType
        self._rowsLayout = self._ui.layoutItems

        self._populateTypeCombo()

    def _populateTypeCombo(self):
        self._cmbType.addItem(self.tr("Select to add"), None)

        self._cmbType.addItem(
            self.tr("Force coefficients (Cl/Cd/Cm)"),
            {
                "category": "forceCoeff",
                "metric": None,
                "label": self.tr("Force coefficients"),
            },
        )

        self._cmbType.addItem(
            self.tr("Point value"),
            {
                "category": "point",
                "metric": None,
                "label": self.tr("Point value"),
            },
        )

        self._cmbType.addItem(
            self.tr("Surface field value"),
            {
                "category": "surface",
                "metric": None,
                "label": self.tr("Surface field value"),
            },
        )

        self._cmbType.addItem(
            self.tr("Volume field value"),
            {
                "category": "volume",
                "metric": None,
                "label": self.tr("Volume field value"),
            },
        )

        self._cmbType.setCurrentIndex(0)

    def _connectSignalsSlots(self):
        self._ui.buttonBox.accepted.connect(self.accept)
        self._ui.buttonBox.rejected.connect(self.reject)

        self._cmbType.currentIndexChanged.connect(self._onTypeChanged)

    def _onTypeChanged(self, index: int):
        meta = self._cmbType.itemData(index)
        if not meta:
            return

        self._addRow(meta)

        self._cmbType.blockSignals(True)
        self._cmbType.setCurrentIndex(0)
        self._cmbType.blockSignals(False)

    def _addRow(self, meta: dict):
        item_id = uuid.uuid4()
        row = EvalItemWidget(item_id, meta, self)

        row.removed.connect(self._removeRow)
        row.changed.connect(self._rowChanged)

        self._rows[item_id] = row
        self._rowsLayout.addWidget(row)

        row._onSelect()

    def _removeRow(self, item_id: uuid.UUID):
        row = self._rows.pop(item_id, None)
        if row is not None:
            row.setParent(None)
            row.deleteLater()

    def _rowChanged(self):
        pass

    def _collectSettings(self) -> dict:
        items: List[dict] = []

        for row in self._rows.values():
            items.append(row.toDict())

        return {
            "items": items,
        }

    def accept(self):
        num = self._ui.spnNumEval.value()
        settings = self._collectSettings()

        self.settingsCompleted.emit(num, settings)
        super().accept()
