#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtCore import Signal, QCoreApplication, QEvent, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QColorDialog
from PySide6QtAds import CDockWidget
from vtkmodules.vtkRenderingCore import vtkActor

from widgets.rendering.rotation_center_widget import RotationCenterWidget
from widgets.rendering.ruler_widget import RulerWidget

from .rendering_view_ui import Ui_RenderingView
from .control_panel import ControlPanel


class DisplayMode(Enum):
    DISPLAY_MODE_FEATURE        = 0
    DISPLAY_MODE_POINTS         = auto()
    DISPLAY_MODE_SURFACE        = auto()
    DISPLAY_MODE_SURFACE_EDGE   = auto()
    DISPLAY_MODE_WIREFRAME      = auto()


class RenderingView(QWidget):
    actorPicked = Signal(vtkActor, bool)
    viewClosed = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._ui = Ui_RenderingView()
        self._ui.setupUi(self)

        self._controlPanel = ControlPanel(self)

        self._view = self._ui.view

        self._rotationCenter = None

        self._dialog = None

        self._updateBGButtonStyle(self._ui.bg1, QColor.fromRgbF(*self._view.background1()))
        self._updateBGButtonStyle(self._ui.bg2, QColor.fromRgbF(*self._view.background2()))

        self._connectSignalsSlots()

    def view(self):
        return self._view

    def close(self):
        self._view.close()
        return super().close()

    def resizeEvent(self, ev):
        super(RenderingView, self).resizeEvent(ev)
        self._controlPanel.updateGeometry()
   
    def showEvent(self, ev):
        self._controlPanel.updateGeometry()
        return super(RenderingView, self).showEvent(ev)

    def addActor(self, actor: vtkActor):
        self._view.addActor(actor)

    def removeActor(self, actor):
        self._view.removeActor(actor)

    def refresh(self):
        self._view.refresh()

    def fitCamera(self):
        self._view.fitCamera()

    def _connectSignalsSlots(self):
        self._ui.axis.toggled.connect(self._view.setAxisVisible)
        self._ui.cubeAxis.toggled.connect(self._view.setCubeAxisVisible)
        self._ui.ruler.toggled.connect(self._setRulerVisible)
        self._ui.fit.clicked.connect(self._view.fitCamera)
        self._ui.perspective.toggled.connect(self._view.setParallelProjection)
        self._ui.alignAxis.clicked.connect(self._view.alignCamera)
        self._ui.rotate.clicked.connect(self._view.rollCamera)
        self._ui.rotationCenter.clicked.connect(self._toggleRotationCenter)
        self._ui.bg1.clicked.connect(self._pickBackground1)
        self._ui.bg2.clicked.connect(self._pickBackground2)

        self._view.actorPicked.connect(self.actorPicked)
        self._view.viewClosed.connect(self.viewClosed)

        self._controlPanel.collapsed.connect(self._controlPanelCollapsed)

    def _setRulerVisible(self, checked):
        if checked:
            self._ruler = RulerWidget(self._view.interactor(), self._view.renderer())
            self._ruler.on()
        else:
            self._ruler.off()
            self._ruler = None

    def _paraviewFileSelected(self, file):
        print('paraview selected')

    def _toggleRotationCenter(self, checked):
        if checked:
            self._rotationCenter = self._rotationCenter or RotationCenterWidget(self._view)
            self._rotationCenter.on()
        else:
            self._rotationCenter.off()

    def _pickBackground1(self):
        self._dialog = self._newBGColorDialog()
        self._dialog.colorSelected.connect(self._setBackground1)
        self._dialog.open()

    def _pickBackground2(self):
        self._dialog = self._newBGColorDialog()
        self._dialog.colorSelected.connect(self._setBackground2)
        self._dialog.open()

    def _newBGColorDialog(self):
        dialog = QColorDialog(self)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setCustomColor(0, QColor(56, 61, 84))
        dialog.setCustomColor(1, QColor(209, 209, 209))

        return dialog

    def _setBackground1(self, color):
        r, g, b, a = color.getRgbF()
        self._view.setBackground1(r, g, b)
        self._updateBGButtonStyle(self._ui.bg1, color)

    def _setBackground2(self, color):
        r, g, b, a = color.getRgbF()
        self._view.setBackground2(r, g, b)
        self._updateBGButtonStyle(self._ui.bg2, color)

    def _updateBGButtonStyle(self, button, color):
        r, g, b, a = color.getRgb()
        button.setStyleSheet(
            f'background: rgb({r}, {g}, {b}); border-style: solid; border-color:black; border-width: 1')

    def _controlPanelCollapsed(self, collapsed: bool):
        if collapsed:
            self._ui.frame.setEnabled(True)
        else:
            self._ui.frame.setEnabled(False)

class RenderingDock(CDockWidget):
    def __init__(self):
        super().__init__(self._title())

        self._widget = RenderingView()
        self.setWidget(self._widget)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.setWindowTitle(self._title())

        super().changeEvent(event)

    def _title(self):
        return QCoreApplication.translate('RenderingDock', 'Mesh')
