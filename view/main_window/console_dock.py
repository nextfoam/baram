#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional
import asyncio
import qasync

from PySide6.QtWidgets import QVBoxLayout, QWidget, QPlainTextEdit, QCheckBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase

from .tabified_dock import TabifiedDock
from coredb.project import Project, SolverStatus
from openfoam.file_system import FileSystem


class ConsoleDock(TabifiedDock):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._main_window = parent

        self.stopReading = False
        self.readTask: Optional[asyncio.Task] = None

        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self._widget = QWidget()
        self.setWidget(self._widget)

        layout = QVBoxLayout(self._widget)

        self._textView = QPlainTextEdit()
        self._textView.setReadOnly(True)
        # small case may print 2,000 lines per second
        self._textView.setMaximumBlockCount(100000)
        self._textView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._textView.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._textView.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._textView.verticalScrollBar().setTracking(True)
        charFormat = self._textView.currentCharFormat()
        fixedFont = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        charFormat.setFont(fixedFont)
        self._textView.setCurrentCharFormat(charFormat)

        layout.addWidget(self._textView)

        self._lineWrap = QCheckBox()
        self._lineWrap.setChecked(False)
        self._lineWrap.stateChanged.connect(self._lineWrapStateChanged)

        layout.addWidget(self._lineWrap)

        self._project = Project.instance()
        self._project.projectOpened.connect(self._projectOpened)
        self._project.projectClosed.connect(self._projectClosed)
        self._project.solverStatusChanged.connect(self._solverStatusChanged)

        self._translate()

    def startCollecting(self):
        if self.readTask is None:
            self.stopReading = False
            self.readTask = asyncio.create_task(self.readLogForever())

    def stopCollecting(self):
        self.stopReading = True

    def _translate(self):
        self.setWindowTitle(self.tr("Console"))
        self._lineWrap.setText(self.tr('Line-Wrap'))

    def _lineWrapStateChanged(self):
        if self._lineWrap.isChecked():
            self._textView.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        else:
            self._textView.setLineWrapMode(QPlainTextEdit.NoWrap)

    async def readLogForever(self):
        root = FileSystem.caseRoot()
        try:
            stdout = open(root/'stdout.log', 'r')
            stderr = open(root/'stderr.log', 'r')

            idleCount = 0
            while True:
                hasOutput = False
                while lines := stdout.readlines():
                    self._textView.appendPlainText(''.join(lines).rstrip())
                    hasOutput = True
                while lines := stderr.readlines():
                    self._textView.appendPlainText(''.join(lines).rstrip())
                    hasOutput = True
                if hasOutput:
                    await asyncio.sleep(0.1)
                    idleCount = 0
                    continue
                else:
                    await asyncio.sleep(0.5)
                    idleCount += 1
                    # Last message from the solver can be flushed late
                    if idleCount > 4 and self.stopReading:
                        break

        except asyncio.CancelledError:
            print('cancel console reading')
        finally:
            stdout.close()
            stderr.close()
            self.readTask = None

    @qasync.asyncSlot()
    async def _projectOpened(self):
        if self._project.isSolverRunning():
            self.startCollecting()
        elif self._project.hasSolved():
            await self._readAllLog()

    def _projectClosed(self):
        if self.readTask is not None:
            self.readTask.cancel()

    def _solverStatusChanged(self, status):
        if status == SolverStatus.NONE:
            self._textView.clear()
        elif status == SolverStatus.RUNNING:
            self.startCollecting()
        else:
            self.stopCollecting()

    async def _readAllLog(self):
        async def _readLog(path):
            if path.is_file():
                with path.open() as file:
                    self._textView.appendPlainText(file.read())
                    self._textView.verticalScrollBar().setValue(self._textView.verticalScrollBar().maximum())

        root = FileSystem.caseRoot()
        await _readLog(root / 'stdout.log')
        await _readLog(root / 'stderr.log')
