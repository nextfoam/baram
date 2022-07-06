#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path

from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtCore import Qt

import pyvista
from pyvistaqt import QtInteractor
from pyvista import themes

from .tabified_dock import TabifiedDock


class MeshDock(TabifiedDock):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderView = None

        self.setWindowTitle(self.tr("Mesh"))
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self._dockWidgetContents = QWidget()
        self._layout = QVBoxLayout(self._dockWidgetContents)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Add PyVista
        pyvista.set_plot_theme(themes.ParaViewTheme())
        pyvista.global_theme.show_scalar_bar = False

        self.__plotter = QtInteractor(self)
        self.__plotter.show_axes()
        # self.__plotter.show_grid()
        # self.__plotter.show_bounds()
        self.__plotter.add_camera_orientation_widget()
        # self.__plotter.add_text('NEXTfoam BARAM', position='lower_right', color='blue', font="courier", shadow=True, font_size=16)

        self._layout.addWidget(self.__plotter.interactor)
        self.setWidget(self._dockWidgetContents)

        # Test
        testPath = ""   # 경로 마지막에 "/" 적으면 안됨
        # testPath = "/home/test/Desktop/TestCase/constant"
        # testPath = "/home/test/Desktop/TestCase/Test3/constant"
        testPath = "/home/test/Desktop/TestCase/Test0/constant"
        if os.path.exists(testPath):
            self.showMesh(testPath)


    def showMesh(self, casePath):
        foamReader = pyvista.OpenFOAMReader(casePath)
        mesh = foamReader.read()

        #
        setStyle = dict(
            style           = 'surface',
            show_edges      = True,
            edge_color      = [120, 120, 120],
            opacity         = 0.8,
            # lighting      = True,
            reset_camera    = True,
            show_scalar_bar = False,
            multi_colors    = True,
            ambient         = 0.2,
            # culling         = "front",
            rgb             = True,
            pickable        = True,
        )
        self.__plotter.add_mesh(mesh, **setStyle)

    def closeEvent(self, event):
        self.hide()
        event.ignore()
