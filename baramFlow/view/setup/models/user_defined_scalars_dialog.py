#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

import qasync
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QTreeWidgetItem, QHeaderView

from baramFlow.coredb.coredb_writer import CoreDBWriter
from widgets.async_message_box import AsyncMessageBox
from widgets.flat_push_button import FlatPushButton

from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.scalar_model_db import ScalarSpecificationMethod, UserDefinedScalarsDB
from .user_defined_scalar_dialog import UserDefiendScalarDialog, ALL_MATERIALS_TEXT, SCALAR_SPECIFICATION_METHODS
from .user_defined_scalars_dialog_ui import Ui_UserDefinedScalarsDialog


class Column(IntEnum):
    FIELD_NAME = 0
    TARGET = auto()
    DIFFUSIVITY = auto()
    REMOVE = auto()


removeIcon = QIcon(':/icons/trash-outline.svg')


class UserDefinedScalarsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_UserDefinedScalarsDialog()
        self._ui.setupUi(self)

        self._dialog = None
        self._scalars = {}
        self._toDelete = []

        self._ui.scalars.setColumnWidth(Column.REMOVE, 20)
        self._ui.scalars.header().setSectionResizeMode(Column.FIELD_NAME, QHeaderView.ResizeMode.ResizeToContents)
        self._ui.scalars.header().setSectionResizeMode(Column.TARGET, QHeaderView.ResizeMode.ResizeToContents)
        self._ui.scalars.header().setSectionResizeMode(Column.DIFFUSIVITY, QHeaderView.ResizeMode.Stretch)
        self._ui.scalars.header().setStretchLastSection(False)

        if not ModelsDB.isMultiphaseModelOn():
            self._ui.scalars.headerItem().setText(Column.TARGET, self.tr('Region'))

        self._connectSignalsSlots()
        self._load()

    def fieldNameExists(self, fieldName):
        return fieldName in self._scalars

    def _connectSignalsSlots(self):
        self._ui.add.clicked.connect(self._openScalarDialog)
        self._ui.scalars.itemDoubleClicked.connect(self._showScalar)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        db = coredb.CoreDB()
        for scalarID, _ in db.getUserDefinedScalars():
            self._addScalar(UserDefinedScalarsDB.getUserDefinedScalar(scalarID))
            # xpath = ModelsDB.getUserDefinedScalarXPath(scalarID)
            #
            # target = ALL_MATERIALS_TEXT
            # if ModelsDB.isMultiphaseModelOn():
            #     if mid := int(db.getValue(xpath + '/material')):
            #         target = MaterialDB.getName(mid)
            # elif region := db.getValue(xpath + '/region'):
            #     target = region
            #
            # specificationMethod = ScalarSpecificationMethod(db.getValue(xpath + '/diffusivity/specificationMethod'))
            #
            # self._addScalar(scalarID, db.getValue(xpath + '/fieldName'), target,
            #                 (db.getValue(xpath + '/diffusivity/constant')
            #                  if specificationMethod == ScalarSpecificationMethod.CONSTANT
            #                  else SCALAR_SPECIFICATION_METHODS[specificationMethod]))

    def _openScalarDialog(self):
        self._dialog = UserDefiendScalarDialog(self, UserDefinedScalarsDB.getUserDefinedScalar(0))
        self._dialog.accepted.connect(lambda: self._addScalar(self._dialog.scalar()))
        self._dialog.open()

    def _addScalar(self,  scalar):
        target = ALL_MATERIALS_TEXT
        if ModelsDB.isMultiphaseModelOn() and int(scalar.material):
            target = MaterialDB.getName(scalar.material)
        elif scalar.region:
            target = scalar.region

        item = QTreeWidgetItem([scalar.fieldName,
                                target,
                                (scalar.constantDiffusivity
                                 if scalar.specificationMethod == ScalarSpecificationMethod.CONSTANT
                                 else SCALAR_SPECIFICATION_METHODS[scalar.specificationMethod])])
        self._scalars[scalar.fieldName] = scalar

        removeButton = FlatPushButton(removeIcon, '')
        removeButton.clicked.connect(lambda: self._removeScalar(item))

        self._ui.scalars.addTopLevelItem(item)
        self._ui.scalars.setItemWidget(item, Column.REMOVE, removeButton)

    @qasync.asyncSlot()
    async def _removeScalar(self, item):
        fieldName = item.text(Column.FIELD_NAME)
        scalar = self._scalars[fieldName]

        if UserDefinedScalarsDB.isReferenced(scalar.scalarID):
            await AsyncMessageBox().information(
                self, self.tr('Cannot Delete Selected Scalar'),
                self.tr('The selected scalar has been set as a monitoring field.'))
            return

        if not await AsyncMessageBox().confirm(
                self, self.tr('Delete Scalar'),
                self.tr('Are you sure you want to delete the scalar "{}"'.format(fieldName))):
            return

        if scalar.scalarID:
            self._toDelete.append(scalar.scalarID)

        self._scalars.pop(fieldName)
        self._ui.scalars.takeTopLevelItem(self._ui.scalars.indexOfTopLevelItem(item))

    def _showScalar(self, item):
        self._dialog = UserDefiendScalarDialog(self, self._scalars[item.text(Column.FIELD_NAME)])
        self._dialog.open()

    @qasync.asyncSlot()
    async def _accept(self):
        writer = CoreDBWriter()
        for scalarID in self._toDelete:
            writer.callFunction('removeUserDefinedScalar', [scalarID])

        for scalar in self._scalars.values():
            if scalar.scalarID == 0:
                writer.callFunction('addUserDefinedScalar', [scalar])

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().information(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self.accept()

