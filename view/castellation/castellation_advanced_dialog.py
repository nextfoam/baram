#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from app import app
from db.simple_schema import DBError
from .refinement_item import RefinementItem, Column
from .castellation_advanced_dialog_ui import Ui_CastellationAdvancedDialog

DEFAULT_FEATURE_LEVEL = '1'


class CastellationAdvancedDialog(QDialog):
    def __init__(self, parent, features):
        super().__init__(parent)
        self._ui = Ui_CastellationAdvancedDialog()
        self._ui.setupUi(self)

        self._features = features
        self._accepted = False

        self._db = app.db.checkout('castellation')

        self._connectSignalsSlots()
        self._load()

    def isAccepted(self):
        return self._accepted

    def accept(self):
        try:
            self._db.setValue('maxGlobalCells', self._ui.maxGlobalCells.text(), self.tr('Max. Global Cell Count'))
            self._db.setValue('maxLocalCells', self._ui.maxLocalCells.text(), self.tr('Max. Local Cell Count'))
            self._db.setValue('minRefinementCells', self._ui.minRefinementCells.text(),
                              self.tr('Min. Refinement Cell Count'))
            self._db.setValue('maxLoadUnbalance', self._ui.maxLoadUnbalance.text(), self.tr('Msx. Load Unbalance'))
            self._db.setValue('allowFreeStandingZoneFaces', self._ui.allowFreeStandingZoneFaces.isChecked())

            self._db.removeAllElements('features')
            for i in range(self._ui.refinements.topLevelItemCount()):
                item = self._ui.refinements.topLevelItem(i)
                e = self._db.newElement('features')
                e.setValue('level', item.level(), item.name() + self.tr(' Refinement Level'))
                self._db.addElement('features', e, item.type())

            app.db.commit(self._db)

            self._accepted = True

            super().accept()
        except DBError as e:
            QMessageBox.information(self, self.tr("Input Error"), e.toMessage())

    def _connectSignalsSlots(self):
        self._ui.refinements.itemClicked.connect(self._refinementItemClicked)

    def _load(self):
        self._ui.maxGlobalCells.setText(self._db.getValue('maxGlobalCells'))
        self._ui.maxLocalCells.setText(self._db.getValue('maxLocalCells'))
        self._ui.minRefinementCells.setText(self._db.getValue('minRefinementCells'))
        self._ui.maxLoadUnbalance.setText(self._db.getValue('maxLoadUnbalance'))
        self._ui.allowFreeStandingZoneFaces.setChecked(self._db.getValue('allowFreeStandingZoneFaces'))

        features = self._db.getElements('features')

        for geometry in self._features:
            item = RefinementItem(
                geometry['gId'], geometry['name'],
                features[geometry['gId']]['level'] if geometry['gId'] in features else DEFAULT_FEATURE_LEVEL)
            item.addAsTopLevel(self._ui.refinements)

    def _refinementItemClicked(self, item, column):
        if column == Column.LEVEL_COLUMN.value:
            self._ui.refinements.editItem(item, column)
