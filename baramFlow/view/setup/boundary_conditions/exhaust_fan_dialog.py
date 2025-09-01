#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import UUID, uuid4
import qasync

from PySide6.QtCore import Qt
import pandas as pd

from baramFlow.coredb.libdb import ValueException, dbErrorToMessage
from libbaram.natural_name_uuid import uuidToNnstr
from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb.project import Project
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.view.widgets.piecewise_linear_dialog import PiecewiseLinearDialog
from baramFlow.view.widgets.resizable_dialog import ResizableDialog

from .exhaust_fan_dialog_ui import Ui_ExhaustFanDialog


class ExhaustFanDialog(ResizableDialog):
    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_ExhaustFanDialog()
        self._ui.setupUi(self)

        self._dialog: PiecewiseLinearDialog
        self._fanCurveName: UUID
        self._fanCurve: list[list[float]] = []

        self._xpath = BoundaryDB.getXPath(bcid)

        self._connectSignalsSlots()

        self._load()

    def closeEvent(self, event):
        self._ui.cancel.click()
        event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            event.ignore()
        else:
            super().keyPressEvent(event)

    @qasync.asyncSlot()
    async def _accept(self):
        df = pd.DataFrame(self._fanCurve)
        if df.empty:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Edit Fan Curve'))
            return

        try:
            with coredb.CoreDB() as db:
                db.setValue(self._xpath + '/pressure', self._ui.totalPressure.text(), self.tr("Total Pressure"))

                if self._fanCurveName.int == 0:
                    self._fanCurveName = uuid4()
                    db.setValue(self._xpath + '/fanCurveName', str(self._fanCurveName), self.tr("Fan Curve Name"))
        except ValueException as ve:
            await AsyncMessageBox().information(self, self.tr('Input Error'), dbErrorToMessage(ve))

        Project.instance().fileDB().putDataFrame(uuidToNnstr(self._fanCurveName), df)

        self.accept()

    @qasync.asyncSlot()
    async def _reject(self):
        if self._fanCurveName.int == 0:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Be sure to edit Fan Curve'))
        else:
            self.reject()

    def _load(self):
        db = coredb.CoreDB()
        self._ui.totalPressure.setText(db.getValue(self._xpath + '/pressure'))

        self._fanCurveName = UUID(db.getValue(self._xpath + '/fanCurveName'))
        if self._fanCurveName.int != 0:
            df = Project.instance().fileDB().getDataFrame(uuidToNnstr(self._fanCurveName))
            if df is not None:
                self._fanCurve = df.values.tolist()

    def _connectSignalsSlots(self):
        self._ui.editFanCurve.clicked.connect(self._editFanCurve)
        self._ui.ok.clicked.connect(self._accept)
        self._ui.cancel.clicked.connect(self._reject)

    def _editFanCurve(self):
        self._dialog = PiecewiseLinearDialog(self, self.tr('Fan Curve'), 'Q', 'm3/s', ['P'], 'Pa', self._fanCurve)
        self._dialog.accepted.connect(self._fanCurveAccepted)
        self._dialog.open()

    def _fanCurveAccepted(self):
        self._fanCurve = self._dialog.getData()
