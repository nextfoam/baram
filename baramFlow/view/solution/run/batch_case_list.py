#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

import pandas as pd
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView

from baramFlow.coredb.filedb import FileDB
from baramFlow.coredb.project import Project


class Column(IntEnum):
    CASE_NAME = 0
    CALCULATION = auto()
    RESULT = auto()

    PARAMETER_START = auto()


class BatchCaseList(QObject):
    def __init__(self, tree: QTreeWidget):
        super().__init__()

        self._list = tree
        self._header = self._list.headerItem()
        self._cases = {}
        self._items = {}
        self._parameters = None

        self._loaded = False

        self._list.header().setSectionResizeMode(Column.CASE_NAME, QHeaderView.ResizeMode.ResizeToContents)
        self._list.header().setSectionResizeMode(Column.CALCULATION, QHeaderView.ResizeMode.ResizeToContents)
        self._list.header().setSectionResizeMode(Column.RESULT, QHeaderView.ResizeMode.ResizeToContents)

    def parameters(self):
        return self._parameters

    def clear(self):
        self._list.clear()
        self._list.setColumnCount(3)
        self._parameters = None
        self._cases = {}
        self._items = {}

    def importFromDataFrame(self, df):
        if df is None:
            return

        if self._parameters is None:
            self._parameters = df.columns

            i = Column.PARAMETER_START
            for p in self._parameters:
                self._header.setText(i, p)
                self._list.header().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
                i += 1

        cases = df.to_dict(orient='index')
        for name, case in cases.items():
            self._setCase(name, case)

        if self._loaded:
            Project.instance().fileDB().putDataFrame(FileDB.Key.BATCH_CASES, self.exportAsDataFrame())
        else:
            self._loaded = True

        self._adjustSize()

    def exportAsDataFrame(self):
        return pd.DataFrame.from_dict(self._cases, orient='index')

    def load(self):
        self.importFromDataFrame(Project.instance().fileDB().getDataFrame(FileDB.Key.BATCH_CASES))

    def _adjustSize(self):
        if self._cases:
            height = self._list.rowHeight(self._list.model().index(0, 0, self._list.rootIndex())) * (len(self._items) + 1) + 10
        else:
            height = 100
        width = sum([self._list.columnWidth(i) for i in range(self._list.columnCount())])
        self._list.setMinimumWidth(width)
        self._list.setMinimumHeight(height)
        self._list.setMaximumWidth(width)
        self._list.setMaximumHeight(height)

    def _setCase(self, name, case):
        if name not in self._items:
            self._items[name] = QTreeWidgetItem(self._list, [name])

        self._cases[name] = case

        i = Column.PARAMETER_START
        for p in self._parameters:
            self._items[name].setText(i, case[p])
            i += 1
