#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

import qasync
from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QIcon, QRegularExpressionValidator
from PySide6.QtWidgets import QDialog, QTreeWidgetItem, QLineEdit, QHeaderView

from widgets.async_message_box import AsyncMessageBox
from widgets.flat_push_button import FlatPushButton

from baramFlow.coredb.batch_parameter_db import BATCH_PARAMETER_PATTERN
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.run_calculation_db import RunCalculationDB
from .user_parameters_dialog_ui import Ui_UserParametersDialog


class Column(IntEnum):
    NAME = 0
    VALUE = auto()
    REMOVE = auto()


class ItemMode(IntEnum):
    ADD = auto()
    EDIT = auto()


class UserParametersDialog(QDialog):
    XPATH = RunCalculationDB.RUN_CALCULATION_XPATH + '/batch/parameters'

    def __init__(self, parent, parameters):
        super().__init__(parent)
        self._ui = Ui_UserParametersDialog()
        self._ui.setupUi(self)

        self._parameters = parameters

        self._ui.parameters.setColumnWidth(Column.REMOVE, 20)
        self._ui.parameters.header().setSectionResizeMode(Column.NAME, QHeaderView.ResizeMode.Stretch)

        self._connectSignalsSlots()

        for name, data in self._parameters.items():
            self._addItem(name, data['value'], data['usages'] == 0)

    @qasync.asyncSlot()
    async def _accept(self):
        parameters = {}
        for i in range(self._ui.parameters.topLevelItemCount()):
            item = self._ui.parameters.topLevelItem(i)
            value = self._ui.parameters.itemWidget(item, Column.VALUE).text().strip()

            if item.type() == ItemMode.ADD:
                name = self._ui.parameters.itemWidget(item, Column.NAME).text().strip()
                if not name:
                    await AsyncMessageBox().information(
                        self, self.tr('Input Error'),
                        self.tr('Parameter name cannot be empty at line {}').format(i + 1))
                    return

                if parameters.get(name):
                    await AsyncMessageBox().information(
                        self, self.tr('Input Error'), self.tr('Duplicate parameter name - ') + name)
                    return

                parameters[name] = value
            else:
                name = item.text(Column.NAME)
                if name not in parameters:
                    parameters[name] = None if item.isHidden() else value

            try:
                if value is not None:
                    float(value)
            except ValueError:
                await AsyncMessageBox().information(
                    self, self.tr('Input Error'), self.tr('Value must be a float - ') + name)
                return

        writer = CoreDBWriter()
        for name, value in parameters.items():
            if value is None:
                if name in self._parameters:
                    writer.removeElement(f'{self.XPATH}/parameter[name="{name}"]')
            elif name not in self._parameters:
                writer.addElement(self.XPATH,
                                  f'''
                                <parameter xmlns="http://www.baramcfd.org/baram">
                                    <name>{name}</name>
                                    <value>{value}</value>
                                </parameter>
                              ''')
            elif value != self._parameters[name]['value']:
                writer.append(f'{self.XPATH}/parameter[name="{name}"]/value', value, None)

        CoreDBReader().setParameters(parameters)

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().information(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self.accept()

    def _connectSignalsSlots(self):
        self._ui.add.clicked.connect(lambda: self._addItem())
        self._ui.ok.clicked.connect(self._accept)
        self._ui.cancel.clicked.connect(self.close)

    def _addItem(self, name=None, value='0', removable=True):
        mode = ItemMode.ADD if name is None else ItemMode.EDIT

        item = QTreeWidgetItem(self._ui.parameters, mode)
        if mode == ItemMode.ADD:
            nameEdit = QLineEdit()
            nameEdit.setValidator(QRegularExpressionValidator(QRegularExpression(BATCH_PARAMETER_PATTERN)))
            self._ui.parameters.setItemWidget(item, Column.NAME, nameEdit)
            nameEdit.setFocus()
        else:
            item.setText(Column.NAME, name)

        self._ui.parameters.setItemWidget(item, Column.VALUE, QLineEdit(value))

        if removable:
            removeButton = FlatPushButton(QIcon(':/icons/trash-outline.svg'), '')
            removeButton.clicked.connect(lambda: self._removeItem(item))
            self._ui.parameters.setItemWidget(item, Column.REMOVE, removeButton)

    def _removeItem(self, item):
        if item.type() == ItemMode.ADD:
            self._ui.parameters.takeTopLevelItem(self._ui.parameters.indexOfTopLevelItem(item))
        else:
            item.setHidden(True)

