#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QGroupBox, QFormLayout, QLineEdit

from baramFlow.base.boundary.boundary import UserDefinedScalarValue
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from libbaram.pfloat import PFloat


class UserDefinedScalarsWidget(QGroupBox):
    def __init__(self, rname):
        super().__init__()

        self._rname = rname

        self._on = False
        self._layout = None
        self._scalars = {}

        self.setTitle(self.tr('User-defined Scalars'))

        db = coredb.CoreDB()
        if scalars := db.getUserDefinedScalarsInRegion(rname):
            self._on = True
            self._layout = QFormLayout(self)
            for scalarID, fieldName in scalars:
                editor = QLineEdit()
                self._layout.addRow(fieldName, editor)
                self._scalars[scalarID] = (fieldName, editor)

    def data(self):
        if not self._on:
            return None

        data = []
        for scalarID in self._scalars:
            fieldName, editor = self._scalars[scalarID]
            data.append(UserDefinedScalarValue(
                scalarID=scalarID,
                value=str(PFloat(editor.text(), self.tr('User Defined Scalars' + fieldName)))))

        return data

    def on(self):
        return self._on

    def load(self, xpath):
        if self._on:
            db = coredb.CoreDB()
            for scalarID in self._scalars:
                fieldName, editor = self._scalars[scalarID]
                editor.setText(db.getValue(f'{xpath}/scalar[scalarID="{scalarID}"]/value'))

    def appendToWriter(self, writer: CoreDBWriter, xpath):
        if self._on:
            for scalarID in self._scalars:
                fieldName, editor = self._scalars[scalarID]

                if editor.isModified():
                    writer.append(f'{xpath}/scalar[scalarID="{scalarID}"]/value', editor.text(), fieldName)

        return True
