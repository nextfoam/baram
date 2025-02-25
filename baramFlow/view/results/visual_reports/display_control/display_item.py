#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum, IntEnum, auto

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTreeWidgetItem, QLabel, QWidget, QHBoxLayout
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkRenderingCore import vtkActor, vtkMapper, vtkPolyDataMapper

from libbaram.colormap import sequentialRedLut


class ColorMode(Enum):
    SOLID = auto()  # noqa: E221
    FIELD = auto()  # noqa: E221


class DisplayMode(Enum):
    WIREFRAME      = auto()  # noqa: E221
    SURFACE        = auto()  # noqa: E221
    SURFACE_EDGE   = auto()  # noqa: E221


@dataclass
class Properties:
    visibility: bool
    opacity: float
    color: QColor
    colorMode: ColorMode
    displayMode: DisplayMode
    highlighted: bool

    def merge(self, properties):
        self.visibility = properties.visibility if properties.visibility == self.visibility else None
        self.opacity = properties.opacity if properties.opacity == self.opacity else None
        self.color = properties.color if properties.color == self.color else None
        self.colorMode = properties.colorMode if properties.colorMode == self.colorMode else None
        self.displayMode = properties.displayMode if properties.displayMode == self.displayMode else None


class Column(IntEnum):
    NAME_COLUMN = 0
    TYPE_COLUMN = auto()
    COLOR_COLUMN = auto()
    # CUT_ICON_COLUMN = auto()
    # VISIBLE_ICON_COLUMN = auto()


class DisplayItem(QTreeWidgetItem):

    sourceChanged = Signal(str)
    nameChanged = Signal(str)


    def __init__(self, did, name, dataSet):

        super().__init__()

        self._dataSet = dataSet
        self._did = did
        self._name = name

        self._mapper: vtkMapper = vtkPolyDataMapper()
        self._mapper.SetInputData(dataSet)
        self._mapper.ScalarVisibilityOff()
        self._mapper.SetScalarModeToUsePointData()
        self._mapper.SetColorModeToMapScalars()
        self._mapper.SetLookupTable(sequentialRedLut)
        self._mapper.SelectColorArray('T')

        self._actor = vtkActor()
        self._actor.SetMapper(self._mapper)
        self._actor.GetProperty().SetDiffuse(0.3)
        self._actor.GetProperty().SetOpacity(0.9)
        self._actor.GetProperty().SetAmbient(0.3)
        self._actor.SetObjectName(str(self._did))
        print(f'{self._did} added')
        prop = self._actor.GetProperty()
        self._properties = Properties(bool(self._actor.GetVisibility()),
                                      prop.GetOpacity(),
                                      QColor.fromRgbF(*prop.GetColor()),
                                      ColorMode.SOLID,
                                      DisplayMode.SURFACE,
                                      False)

        self._displayModeApplicator = {
            DisplayMode.WIREFRAME: self._applyWireframeMode,
            DisplayMode.SURFACE: self._applySurfaceMode,
            DisplayMode.SURFACE_EDGE: self._applySurfaceEdgeMode
        }

        self._colorWidget = QLabel()

        self.setText(Column.NAME_COLUMN, name)
        self.setText(Column.TYPE_COLUMN, name)
        self._updateColorColumn()
        # self._updateCutIcon()
        # self._updateVisibleIcon()

        self._connectSignalsSlots()

    def setDataSet(self, dataSet):
        self._dataSet = dataSet

        self._mapper.Update()

        self.sourceChanged.emit(self._id)

    def properties(self):
        return self._properties

    def actor(self):
        return self._actor

    def did(self):
        return self._did

    def isVisible(self):
        return self._properties.visibility

    def color(self):
        return self._properties.color

    def setVisible(self, visibility):
        self._properties.visibility = visibility
        self._actor.SetVisibility(visibility)

    def setupColorWidget(self, parent):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(9, 1, 9, 1)
        layout.addWidget(self._colorWidget)
        # self._colorWidget.setFrameShape(QFrame.Shape.Box)
        self._colorWidget.setMinimumSize(16, 16)
        parent.setItemWidget(self, Column.COLOR_COLUMN, widget)

    def setActorVisible(self, visibility):
        self._properties.visibility = visibility
        self._actor.SetVisibility(visibility)
        self._updateColorColumn()

    def setDisplayMode(self, mode: DisplayMode):
        self._properties.displayMode = mode
        self._displayModeApplicator[mode]()

    def setOpacity(self, opacity):
        self._properties.opacity = opacity
        self._actor.GetProperty().SetOpacity(opacity)

    def setActorColor(self, color: QColor):
        self._properties.color = color
        self._actor.GetProperty().SetColor(color.redF(), color.greenF(), color.blueF())
        self._updateColorColumn()

    def setColorMode(self, mode: ColorMode):
        self._properties.colorMode = mode
        if mode == ColorMode.SOLID:
            self._mapper.ScalarVisibilityOff()
        elif mode == ColorMode.FIELD:
            self._mapper.ScalarVisibilityOn()
        else:
            raise AssertionError

        self._updateColorColumn()

    def setHighlighted(self, highlighted):
        if self._properties.highlighted != highlighted:
            self._properties.highlighted = highlighted
            if highlighted:
                self._highlightOn()
            else:
                self._highlightOff()

    def _highlightOn(self):
        self._applySurfaceEdgeMode()
        self._actor.GetProperty().SetDiffuse(0.6)
        self._actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Magenta'))
        self._actor.GetProperty().SetLineWidth(2)

    def _highlightOff(self):
        self._displayModeApplicator[self._properties.displayMode]()
        self._actor.GetProperty().SetDiffuse(0.3)
        self._actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Gray'))
        self._actor.GetProperty().SetLineWidth(1)

    def colorWidget(self):
        return self._colorWidget

    def _applyWireframeMode(self):
        if not self._properties.highlighted:
            self._actor.GetProperty().SetRepresentationToWireframe()

    def _applySurfaceMode(self):
        if not self._properties.highlighted:
            self._actor.GetProperty().SetRepresentationToSurface()
            self._actor.GetProperty().EdgeVisibilityOff()

    def _applySurfaceEdgeMode(self):
        self._actor.GetProperty().SetRepresentationToSurface()
        self._actor.GetProperty().EdgeVisibilityOn()
        self._actor.GetProperty().SetLineWidth(1.0)

    def _updateColorColumn(self):
        if self.isVisible():
            if self._properties.colorMode == ColorMode.SOLID:
                color = self.color()
                self._colorWidget.setStyleSheet(
                    f'background-color: rgb({color.red()}, {color.green()}, {color.blue()});'
                    'border: 1px solid LightGrey; border-radius: 3px;')
            elif self._properties.colorMode == ColorMode.FIELD:
                self._colorWidget.setStyleSheet(
                    'background-color: qlineargradient(x1: 0, y1: 0,x2: 1, y2: 1, stop: 0 #ff0000, stop: 0.33 #ffff00, stop: 0.66 #00c0ff, stop: 1 #c000ff);'
                    'border: 1px solid LightGrey; border-radius: 3px;')
            else:
                raise AssertionError
        else:
            self._colorWidget.setStyleSheet('')

    def _updateName(self, name):
        self.setText(Column.NAME_COLUMN, name)
    #
    # def _updateCutIcon(self):
    #     if self._actorInfo.isCutEnabled():
    #         self._colorWidget.clear()
    #     else:
    #         icon = QPixmap(':/icons/lock-closed.svg')
    #         self._colorWidget.setPixmap(icon.scaled(18, 18))
    #
    # def _updateVisibleIcon(self):
    #     if self._actorInfo.isVisible():
    #         self.setIcon(Column.VISIBLE_ICON_COLUMN, self._bulbOnIcon)
    #     else:
    #         self.setIcon(Column.VISIBLE_ICON_COLUMN, self._bulbOffIcon)

    def _connectSignalsSlots(self):
        pass
