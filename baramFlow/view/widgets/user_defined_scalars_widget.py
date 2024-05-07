#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QGroupBox, QFormLayout, QLineEdit

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter

DEFAULT_VALUE = '0'


class ScalarEdit(QLineEdit):
    def __init__(self):
        super().__init__()

        self._loaded = False

    def setValue(self, value):
        if value is None:
            self._loaded = False
            self.setText(DEFAULT_VALUE)
        else:
            self._loaded = True
            self.setText(value)

    def isLoaded(self):
        return self._loaded


class UserDefinedScalarsWidget(QGroupBox):
    def __init__(self, rname):
        super().__init__()

        self._db = coredb.CoreDB()
        self._rname = rname

        self._on = False
        self._layout = None
        self._scalars = {}

        self.setTitle(self.tr('User-defined Scalars'))

        if scalars := self._db.getUserDefinedScalarsInRegion(rname):
            self._on = True
            self._layout = QFormLayout(self)
            for scalarID, fieldName in scalars:
                editor = QLineEdit()
                self._layout.addRow(fieldName, editor)
                self._scalars[scalarID] = (fieldName, editor)

    def on(self):
        return self._on

    def load(self, xpath):
        if self._on:
            for scalarID in self._scalars:
                fieldName, editor = self._scalars[scalarID]
                editor.setText(self._db.getValue(f'{xpath}/scalar[scalarID="{scalarID}"]/value'))

    def appendToWriter(self, writer: CoreDBWriter, xpath):
        if self._on:
            for scalarID in self._scalars:
                fieldName, editor = self._scalars[scalarID]

                if editor.isModified():
                    writer.append(f'{xpath}/scalar[scalarID="{scalarID}"]/value', editor.text(), fieldName)

        return True
