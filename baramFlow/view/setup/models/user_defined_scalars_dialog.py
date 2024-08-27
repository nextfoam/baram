#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

import qasync
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QTreeWidgetItem, QHeaderView

from baramFlow.coredb.configuraitions import ConfigurationException
from widgets.async_message_box import AsyncMessageBox
from widgets.flat_push_button import FlatPushButton

from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.scalar_model_db import ScalarSpecificationMethod, UserDefinedScalarsDB, UserDefinedScalar
from .user_defined_scalar_dialog import UserDefiendScalarDialog, ALL_MATERIALS_TEXT, SCALAR_SPECIFICATION_METHODS
from .user_defined_scalars_dialog_ui import Ui_UserDefinedScalarsDialog


class Column(IntEnum):
    FIELD_NAME = 0
    TARGET = auto()
    DIFFUSIVITY = auto()
    REMOVE = auto()


removeIcon = QIcon(':/icons/trash-outline.svg')


class ScalarItem(QTreeWidgetItem):
    def __init__(self, scalar):
        super().__init__()

        self._scalar = None
        self._modified = False

        self.setScalar(scalar, False)

    def scalar(self):
        return self._scalar

    def isModified(self):
        return self._modified

    def setScalar(self, scalar, modified=True):
        target = ALL_MATERIALS_TEXT
        if ModelsDB.isMultiphaseModelOn() and scalar.material != '0':
            target = MaterialDB.getName(scalar.material)
        elif scalar.rname:
            target = scalar.rname

        self.setText(Column.FIELD_NAME, scalar.fieldName)
        self.setText(Column.TARGET, target)
        self.setText(Column.DIFFUSIVITY, (scalar.constantDiffusivity
                                          if scalar.specificationMethod == ScalarSpecificationMethod.CONSTANT
                                          else SCALAR_SPECIFICATION_METHODS[scalar.specificationMethod]))

        self._scalar = scalar
        self._modified = modified


class UserDefinedScalarsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_UserDefinedScalarsDialog()
        self._ui.setupUi(self)

        self._dialog = None
        self._scalars: set = set()

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
        self._ui.add.clicked.connect(self._openScalarAddDialog)
        self._ui.scalars.itemDoubleClicked.connect(self._openScalarEditDialog)
        self._ui.ok.clicked.connect(self._accept)

    def _load(self):
        db = coredb.CoreDB()
        for scalarID, _ in db.getUserDefinedScalars():
            self._addScalar(UserDefinedScalarsDB.getUserDefinedScalar(scalarID))

    def _openScalarAddDialog(self):
        self._dialog = UserDefiendScalarDialog(self, UserDefinedScalarsDB.getUserDefinedScalar(0))
        self._dialog.accepted.connect(lambda: self._addScalar(self._dialog.scalar()))
        self._dialog.open()

    def _addScalar(self,  scalar: UserDefinedScalar):
        item = ScalarItem(scalar)
        removeButton = FlatPushButton(removeIcon, '')
        removeButton.clicked.connect(lambda: self._removeScalar(item))
        self._ui.scalars.addTopLevelItem(item)
        self._ui.scalars.setItemWidget(item, Column.REMOVE, removeButton)

        self._scalars.add(scalar.fieldName)

    @qasync.asyncSlot()
    async def _removeScalar(self, item):
        fieldName = item.text(Column.FIELD_NAME)

        if UserDefinedScalarsDB.isReferenced(item.scalar().scalarID):
            await AsyncMessageBox().information(
                self, self.tr('Cannot Delete Selected Scalar'),
                self.tr('The selected scalar has been set as a monitoring field.'))
            return

        if not await AsyncMessageBox().confirm(
                self, self.tr('Delete Scalar'),
                self.tr('Are you sure you want to delete the scalar "{}"'.format(fieldName))):
            return

        item.setHidden(True)
        self._scalars.remove(fieldName)
        # self._ui.scalars.takeTopLevelItem(self._ui.scalars.indexOfTopLevelItem(item))

    def _openScalarEditDialog(self, item):
        self._dialog = UserDefiendScalarDialog(self, item.scalar())
        self._dialog.accepted.connect(lambda: self._updateScalar(item))
        self._dialog.open()

    def _updateScalar(self,  item):
        item.setScalar(self._dialog.scalar())

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            with coredb.CoreDB() as db:
                for i in range(self._ui.scalars.topLevelItemCount()):
                    item = self._ui.scalars.topLevelItem(i)
                    scalar = item.scalar()

                    if scalar.scalarID > 0:
                        if item.isHidden():
                            UserDefinedScalarsDB.removeUserDefinedScalar(db, scalar.scalarID)
                        elif item.isModified():
                            xpath = UserDefinedScalarsDB.getXPath(scalar.scalarID)
                            db.setValue(xpath + '/region', scalar.rname)
                            db.setValue(xpath + '/material', scalar.material)
                            db.setValue(xpath + '/diffusivity/specificationMethod', scalar.specificationMethod.value)
                            if scalar.specificationMethod == ScalarSpecificationMethod.CONSTANT:
                                db.setValue(xpath + '/diffusivity/constant', scalar.constantDiffusivity)
                            else:
                                db.setValue(xpath + '/diffusivity/laminarAndTurbulentViscosity/laminarViscosityCoefficient',
                                            scalar.laminarViscosityCoefficient)
                                db.setValue(xpath + '/diffusivity/laminarAndTurbulentViscosity/turbulentViscosityCoefficient',
                                            scalar.turbulentViscosityCoefficient)

                    elif not item.isHidden():
                        UserDefinedScalarsDB.addUserDefinedScalar(db, scalar)

            self.accept()
        except ConfigurationException as ex:
            await AsyncMessageBox().information(self, self.tr('Model Change Failed'), str(ex))
