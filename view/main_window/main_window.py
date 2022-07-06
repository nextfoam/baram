#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil

from PySide6.QtWidgets import QMainWindow, QWidget, QFileDialog
from PySide6.QtCore import Qt

from view.case_wizard.case_wizard import CaseWizard
from openfoam.case_generator import CaseGenerator
from .content_view import ContentView
from .main_window_ui import Ui_MainWindow
from .menu_view import MenuView
from .mesh_dock import MeshDock
from .console_dock import ConsoleDock



class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
        self._wizard = None
        self._menuView = MenuView(self._ui.menuView)
        self._contentView = ContentView(self._ui.formView, self._ui)

        self._emptyDock = self._ui.emptyDock
        self._emptyDock.setTitleBarWidget(QWidget())
        self._meshDock = MeshDock(self)
        self._consoleDock = ConsoleDock(self)

        self._addDockTabified(self._consoleDock)
        self._addDockTabified(self._meshDock)

        self._connectSignalsSlots()

    def tabifyDock(self, dock):
        self.tabifyDockWidget(self._emptyDock, dock)

    def _connectSignalsSlots(self):
        self._ui.actionExit.triggered.connect(self.close)
        self._ui.actionNew.triggered.connect(self._openWizard)
        self._ui.actionSave.triggered.connect(self._save)
        self._ui.actionLoad_Mesh.triggered.connect(self._loadMesh)
        self._menuView.connectCurrentItemChanged(self._changeForm)

    def _openWizard(self, signal):
        self._wizard = CaseWizard()

        self._wizard.exec()

    def _save(self):
        dirName = QFileDialog.getExistingDirectory(self)
        if dirName:
            CaseGenerator(dirName).generateFiles()

    def _loadMesh(self):
        selectedPath = QFileDialog.getExistingDirectory(self, self.tr("Select constant"))
        if selectedPath:
            print(selectedPath)

            # Check path (polyMesh dir)


            # Copy
            # shutil.copy(selectPath, casePath)

            # Show
            self._meshDock.showMesh(selectedPath)

        # fileName = QFileDialog.getOpenFileName(self, self.tr("Open Mesh"), "", self.tr("OpenFOAM Mesh (*.foam)"))
        # if fileName[0]:
        #     self._meshDock.showMesh(fileName[0])


    def _changeForm(self, current):
        currentPane = self._menuView.currentPane()
        if currentPane.index < 0:
            newPage = currentPane.createPage()
            currentPane.index = self._contentView.addPage(newPage)

        self._contentView.changePane(currentPane.index)

    def _addDockTabified(self, dock):
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.tabifyDock(dock)
        self._ui.menuView_2.addAction(dock.toggleViewAction())
