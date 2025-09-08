#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

import pandas as pd
import qasync
from PySide6.QtCore import QObject, Signal, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu, QMessageBox
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from baramFlow.base.graphic.graphics_db import GraphicsDB
from baramFlow.openfoam.openfoam_reader import OpenFOAMReader
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog

from baramFlow.case_manager import CaseManager, BatchCase
from baramFlow.coredb.filedb import FileDB
from baramFlow.coredb.project import Project
from baramFlow.solver_status import SolverStatus


class Column(IntEnum):
    LOADED_ICON = 0
    CASE_NAME = auto()
    CALCULATION = auto()
    RESULT = auto()

    PARAMETER_START = auto()


class StatusWidget(QWidget):
    def __init__(self):
        super().__init__()

        self._circle = QLabel()

        self._setup()

    def setStatus(self, status):
        if status == SolverStatus.ENDED:
            color = 'green'
        elif status == SolverStatus.ERROR:
            color = 'red'
        else:
            self.setVisible(False)
            return

        self.setVisible(True)
        self._circle.setStyleSheet(f'background-color: {color}; border: 1px solid LightGrey; border-radius: 8px;')

    def _setup(self):
        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(self._circle)
        layout.addStretch()
        layout.setContentsMargins(9, 1, 9, 1)
        self.setLayout(layout)
        self._circle.setMinimumSize(16, 16)
        self._circle.setMaximumSize(16, 16)


class CaseItem(QTreeWidgetItem):
    emptyIcon = QIcon()
    checkIcon = QIcon(':/icons/checkmark.svg')
    currentIcon = QIcon(':/icons/arrow-forward.svg')
    runningIcon = QIcon(':/icons/ellipsis-horizontal-circle.svg')
    doneIcon = QIcon(':/icons/checkmark-circle-outline.svg')
    errorIcon = QIcon(':/icons/alert-circle-outline.svg')

    def __init__(self, parent, name):
        super().__init__(parent)

        self._scheduled = False
        self._status = None
        self._loaded = False
        self._statusWidget = StatusWidget()

        self.setText(Column.CASE_NAME, name)
        parent.setItemWidget(self, Column.RESULT, self._statusWidget)

    def name(self):
        return self.text(Column.CASE_NAME)

    def isScheduled(self):
        return self._scheduled

    def status(self):
        return self._status

    def isLoaded(self):
        return self._loaded

    def setLoaded(self, loaded):
        self._loaded = loaded
        self.setIcon(Column.LOADED_ICON, self.currentIcon if loaded else self.emptyIcon)

    def scheduleCalculation(self):
        self._scheduled = True
        self.setIcon(Column.CALCULATION, self.checkIcon)

    def cancelSchedule(self):
        self._scheduled = False
        self.setIcon(Column.CALCULATION, self.emptyIcon)

    def setStatus(self, status):
        self._status = status
        self._statusWidget.setStatus(status)


class SnapshotCaseList(QObject):
    def __init__(self, parent, tree: QTreeWidget):
        super().__init__()

        self._parent = parent
        self._list = tree
        self._header = self._list.headerItem()
        self._cases = {}
        self._items = {}
        self._parameters = None
        self._currentCase = None
        self._project = Project.instance()

        self._hideColumns()

        self._connectSignalsSlots()

    def close(self):
        self._disconnectSignalsSlots()

    def _connectSignalsSlots(self):
        CaseManager().batchCleared.connect(self._clearStatuses)

    def _disconnectSignalsSlots(self):
        CaseManager().batchCleared.disconnect(self._clearStatuses)

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

        statuses = self._project.loadBatchStatuses()

        if self._parameters is None or self._parameters.empty:
            self._parameters = df.columns

            i = Column.PARAMETER_START
            for p in self._parameters:
                self._header.setText(i, p)
                self._list.header().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
                i += 1

        cases = df.to_dict(orient='index')
        for name, case in cases.items():
            status = None

            if statusName := statuses.get(name):
                status = SolverStatus[statusName]
                if status == SolverStatus.RUNNING:
                    status = SolverStatus.ENDED

            self._setCase(name, case, status)

        self._listChanged(False)
        self._hideColumns()

    def exportAsDataFrame(self):
        return pd.DataFrame.from_dict(self._cases, orient='index')

    def load(self):
        self.importFromDataFrame(self._project.fileDB().getDataFrame(FileDB.Key.SNAPSHOT_CASES.value))

    def setCurrentCase(self, name):
        if self._currentCase in self._items:
            self._items[self._currentCase].setLoaded(False)

        self._currentCase = name

        if self._currentCase:
            self._items[self._currentCase].setLoaded(True)

    def updateStatus(self, status, name):
        if name:
            self._items[name].setStatus(status)

    def _adjustSize(self):
        if self._cases:
            rowHeight = self._list.rowHeight(self._list.model().index(0, 0, self._list.rootIndex()))
            height = rowHeight * (len(self._items) + 1) + 10

            iconSize = rowHeight - 6
            self._list.setIconSize(QSize(iconSize, iconSize))
        else:
            height = 100

        width = sum([self._list.columnWidth(i) for i in range(self._list.columnCount())])
        self._list.setMinimumWidth(width)
        self._list.setMinimumHeight(height)
        self._list.setMaximumWidth(width)
        self._list.setMaximumHeight(height)

    def _setCase(self, name, case, status):
        if name not in self._items:
            self._items[name] = CaseItem(self._list, name)

        self._cases[name] = case

        i = Column.PARAMETER_START
        for p in self._parameters:
            self._items[name].setText(i, case[p])
            i += 1

        self._items[name].setStatus(status)

    @qasync.asyncSlot()
    async def _loadCase(self, item):
        progressDialog = ProgressDialog(self._parent, self.tr('Case Loading'))
        CaseManager().progress.connect(progressDialog.setLabelText)
        progressDialog.open()

        CaseManager().loadBatchCase(BatchCase(item.name(), self._cases[item.name()]))

        async with OpenFOAMReader() as reader:
            await reader.setupReader()

        await GraphicsDB().updatePolyMeshAll()

        CaseManager().progress.disconnect(progressDialog.setLabelText)
        progressDialog.close()

    def _scheduleCalculation(self, items):
        for i in items:
            i.scheduleCalculation()

    def _cancelSchedule(self, items):
        for i in items:
            i.cancelSchedule()

    @qasync.asyncSlot()
    async def _delete(self, items):
        confirm = await AsyncMessageBox().question(
            self._parent, self.tr('Delete Case'), self.tr('Are you sure you want to delete the selected cases?'))
        if confirm != QMessageBox.StandardButton.Yes:
            return

        if self._currentCase in [i.name() for i in items]:
            await CaseManager().loadLiveCase()

        for i in items:
            name = i.name()
            self._list.takeTopLevelItem(self._list.indexOfTopLevelItem(i))

            self._project.removeBatchStatus(name)
            del self._items[name]
            del self._cases[name]
            CaseManager().removeCase(name)

        self._listChanged()

    def _clearStatuses(self):
        for name, item in self._items.items():
            item.setStatus(SolverStatus.NONE)

    def _listChanged(self, save=True):
        self._adjustSize()
        if save:
            self._project.fileDB().putDataFrame(FileDB.Key.SNAPSHOT_CASES.value, self.exportAsDataFrame())

    def _hideColumns(self):
        for jCol in [0, 2, 3]:
            self._list.setColumnHidden(jCol, True)
            self._list.header().setSectionHidden(jCol, True)
