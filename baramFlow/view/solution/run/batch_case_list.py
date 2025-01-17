#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

import pandas as pd
import qasync
from PySide6.QtCore import QObject, Signal, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu, QMessageBox
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

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


class ContextMenu(QMenu):
    loadActionTriggered = Signal(CaseItem)
    scheduleActionTriggered = Signal(list)
    cancelScheduleActionTriggered = Signal(list)
    deleteActionTriggered = Signal(list)

    def __init__(self, parent):
        super().__init__(parent)

        self._targets = None

        self._loadAction = self.addAction(
            self.tr('Load'), lambda: self.loadActionTriggered.emit(self._targets[0]))
        self._scheduleAction = self.addAction(
            self.tr('Schedule Calculation'), lambda: self.scheduleActionTriggered.emit(self._targets))
        self._cancelScheduleAction = self.addAction(
            self.tr('Cancel Schedule'), lambda: self.cancelScheduleActionTriggered.emit(self._targets))
        self._deleteAction = self.addAction(
            self.tr('Delete'), lambda: self.deleteActionTriggered.emit(self._targets))

    def execute(self, pos, items):
        self._targets = items

        self._loadAction.setVisible(len(items) == 1)

        self.exec(pos)


class BatchCaseList(QObject):
    def __init__(self, parent, tree: QTreeWidget):
        super().__init__()

        self._parent = parent
        self._list = tree
        self._header = self._list.headerItem()
        self._cases = {}
        self._items = {}
        self._parameters = None
        self._menu = ContextMenu(self._list)
        self._currentCase = None
        self._project = Project.instance()

        self._list.setColumnWidth(Column.LOADED_ICON, 20)
        self._list.header().setSectionResizeMode(Column.CASE_NAME, QHeaderView.ResizeMode.ResizeToContents)
        self._list.header().setSectionResizeMode(Column.CALCULATION, QHeaderView.ResizeMode.ResizeToContents)
        self._list.header().setSectionResizeMode(Column.RESULT, QHeaderView.ResizeMode.ResizeToContents)

        self._connectSignalsSlots()

    def close(self):
        self._disconnectSignalsSlots()

    def _connectSignalsSlots(self):
        self._list.customContextMenuRequested.connect(self._showContextMenu)
        self._menu.loadActionTriggered.connect(self._loadCase)
        self._menu.scheduleActionTriggered.connect(self._scheduleCalculation)
        self._menu.cancelScheduleActionTriggered.connect(self._cancelSchedule)
        self._menu.deleteActionTriggered.connect(self._delete)

        CaseManager().batchCleared.connect(self._clearStatuses)

    def _disconnectSignalsSlots(self):
        print('Disconnecting signals in BatchCaseList')
        CaseManager().batchCleared.disconnect(self._clearStatuses)

    def parameters(self):
        return self._parameters

    def clear(self):
        self._list.clear()
        self._list.setColumnCount(3)
        self._parameters = None
        self._cases = {}
        self._items = {}

    def importFromDataFrame(self, df, loading=False):
        if df is None:
            return

        statuses = self._project.loadBatchStatuses() if loading else {}

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
            if not loading:
                CaseManager().removeCase(name)

        self._listChanged(not loading)

        self._project.updateBatchStatuses(
            {name: item.status().name for name, item in self._items.items() if item.status()})

        CaseManager().removeInvalidCases(list(self._cases.keys()))

    def exportAsDataFrame(self):
        return pd.DataFrame.from_dict(self._cases, orient='index')

    def load(self):
        self.importFromDataFrame(self._project.fileDB().getDataFrame(FileDB.Key.BATCH_CASES.value), True)

    def batchSchedule(self):
        return [(name, self._cases[name]) for name, item in self._items.items() if item.isScheduled()]

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

    def _showContextMenu(self, pos):
        items = self._list.selectedItems()

        if not items:
            return

        self._menu.execute(self._list.mapToGlobal(pos), items)

    @qasync.asyncSlot()
    async def _loadCase(self, item):
        progressDialog = ProgressDialog(self._parent, self.tr('Case Loading'))
        CaseManager().progress.connect(progressDialog.setLabelText)
        progressDialog.open()

        CaseManager().loadBatchCase(BatchCase(item.name(), self._cases[item.name()]))

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
            CaseManager().loadLiveCase()

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
            self._project.fileDB().putDataFrame(FileDB.Key.BATCH_CASES.value, self.exportAsDataFrame())

