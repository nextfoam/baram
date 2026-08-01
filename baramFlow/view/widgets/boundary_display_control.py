#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import IntEnum, auto

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QLabel, QWidget, QHBoxLayout
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkRenderingCore import vtkActor

from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from baramFlow.mesh.mesh_model import ActorInfo, DisplayMode
from widgets.rendering.rendering_widget import RenderingWidget


def _defaultColor() -> QColor:
    return QColor.fromString('#FFFFFF')


def _applyWireframeMode(actor: vtkActor):
    actor.GetProperty().SetLineWidth(1.0)
    actor.GetProperty().SetRepresentationToWireframe()


def _applySurfaceMode(actor: vtkActor):
    actor.GetProperty().SetRepresentationToSurface()
    actor.GetProperty().EdgeVisibilityOff()


def _applySurfaceEdgeMode(actor: vtkActor):
    actor.GetProperty().SetRepresentationToSurface()
    actor.GetProperty().EdgeVisibilityOn()
    actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Gray'))
    actor.GetProperty().SetLineWidth(1.0)


def _applyFeatureMode(actor: vtkActor):
    actor.GetProperty().SetLineWidth(1.0)


class Column(IntEnum):
    REGION_COLUMN = 0
    NAME_COLUMN = auto()
    TYPE_COLUMN = auto()
    COLOR_COLUMN = auto()


class BoundaryDisplayControl(QTreeWidgetItem):
    def __init__(self, parent, bcid: int, rname: str, bcname: str, bctype: BoundaryType,
                 actorInfo: ActorInfo, view: RenderingWidget):
        super().__init__(parent)

        self._bcid = bcid
        self._rname = rname
        self._actorInfo = actorInfo
        self._view = view

        self._opacity = 1.0
        self._color = _defaultColor()
        self._visibility = True
        self._displayMode = DisplayMode.DISPLAY_MODE_SURFACE
        self._frontFaceCulling = False
        self._highlighted = False

        self._colorWidget = QLabel()

        self.setText(Column.REGION_COLUMN, rname)
        self.setText(Column.NAME_COLUMN, bcname)
        self.setText(Column.TYPE_COLUMN, BoundaryDB.dbBoundaryTypeToText(bctype))

        self._actorInfo.face.SetObjectName(str(bcid))
        self._actorInfo.face.GetProperty().SetDiffuse(0.3)
        self._actorInfo.face.GetProperty().SetAmbient(0.3)
        self._view.addActor(self._actorInfo.face)

        if self._actorInfo.feature is not None:
            self._actorInfo.feature.SetObjectName(str(bcid))
            self._actorInfo.feature.GetProperty().SetDiffuse(0.3)
            self._actorInfo.feature.GetProperty().SetAmbient(0.3)
            self._view.addActor(self._actorInfo.feature)

        self._applyRepresentation()
        self._applyColor()
        self._applyCulling()
        self._applyVisibility()

        self._updateColorColumn()

    def did(self) -> int:
        return self._bcid

    @property
    def hasFeature(self) -> bool:
        return self._actorInfo.feature is not None

    @property
    def opacity(self) -> float:
        return self._opacity

    @property
    def color(self) -> QColor:
        return self._color

    @property
    def visibility(self) -> bool:
        return self._visibility

    @property
    def displayMode(self) -> DisplayMode:
        return self._displayMode

    @property
    def frontFaceCulling(self) -> bool:
        return self._frontFaceCulling

    def _currentActor(self) -> vtkActor:
        if self._displayMode == DisplayMode.DISPLAY_MODE_FEATURE and self._actorInfo.feature is not None:
            return self._actorInfo.feature

        return self._actorInfo.face

    def setupColorWidget(self, treeWidget: QTreeWidget):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(9, 1, 9, 1)
        layout.addWidget(self._colorWidget)
        self._colorWidget.setMinimumSize(16, 16)
        treeWidget.setItemWidget(self, Column.COLOR_COLUMN, widget)

    def setActorVisible(self, visibility: bool):
        self._visibility = visibility
        self._actorInfo.visibility = visibility

        self._applyVisibility()

        self._updateColorColumn()

    def setDisplayMode(self, mode: DisplayMode):
        self._displayMode = mode

        self._applyVisibility()

        if not self._highlighted:
            self._applyRepresentation()

    def setOpacity(self, opacity: float):
        self._opacity = opacity

        self._applyColor()

    def setActorColor(self, color: QColor):
        self._color = color

        self._applyColor()

        self._updateColorColumn()

    def cullFrontFace(self):
        self._frontFaceCulling = True

        self._applyCulling()

    def revealFrontFace(self):
        self._frontFaceCulling = False

        self._applyCulling()

    def setHighlighted(self, highlighted: bool):
        if self._highlighted != highlighted:
            self._highlighted = highlighted
            if highlighted:
                self._highlightOn()
            else:
                self._highlightOff()

    def _highlightOn(self):
        actor = self._currentActor()

        if self._displayMode == DisplayMode.DISPLAY_MODE_FEATURE and self._actorInfo.feature is not None:
            # The feature-edges actor renders lines only: EdgeColor/diffuse have no
            # visible effect on it, so the highlight has to recolor the line itself.
            actor.GetProperty().SetColor(vtkNamedColors().GetColor3d('Magenta'))
        else:
            actor.GetProperty().SetRepresentationToSurface()
            actor.GetProperty().EdgeVisibilityOn()
            actor.GetProperty().SetDiffuse(0.6)
            actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Magenta'))

        actor.GetProperty().SetLineWidth(2)

    def _highlightOff(self):
        self._applyRepresentation()
        self._applyColor()

        actor = self._currentActor()
        actor.GetProperty().SetDiffuse(0.3)
        actor.GetProperty().SetEdgeColor(vtkNamedColors().GetColor3d('Gray'))
        actor.GetProperty().SetLineWidth(1)

    def _applyVisibility(self):
        current = self._currentActor()

        self._actorInfo.face.SetVisibility(self._visibility and current is self._actorInfo.face)
        if self._actorInfo.feature is not None:
            self._actorInfo.feature.SetVisibility(self._visibility and current is self._actorInfo.feature)

    def _applyRepresentation(self):
        actor = self._currentActor()

        if self._displayMode == DisplayMode.DISPLAY_MODE_FEATURE and self._actorInfo.feature is not None:
            _applyFeatureMode(actor)
        elif self._displayMode == DisplayMode.DISPLAY_MODE_WIREFRAME:
            _applyWireframeMode(actor)
        elif self._displayMode == DisplayMode.DISPLAY_MODE_SURFACE:
            _applySurfaceMode(actor)
        else:
            _applySurfaceEdgeMode(actor)

    def _applyColor(self):
        r, g, b = self._color.redF(), self._color.greenF(), self._color.blueF()

        self._actorInfo.face.GetProperty().SetColor(r, g, b)
        self._actorInfo.face.GetProperty().SetOpacity(self._opacity)

        if self._actorInfo.feature is not None:
            self._actorInfo.feature.GetProperty().SetColor(r, g, b)
            self._actorInfo.feature.GetProperty().SetOpacity(self._opacity)

    def _applyCulling(self):
        actors = [self._actorInfo.face]
        if self._actorInfo.feature is not None:
            actors.append(self._actorInfo.feature)

        for actor in actors:
            if self._frontFaceCulling:
                actor.GetProperty().FrontfaceCullingOn()
            else:
                actor.GetProperty().FrontfaceCullingOff()

    def _updateColorColumn(self):
        if self._visibility:
            color = self._color
            self._colorWidget.setStyleSheet(
                f'background-color: rgb({color.red()}, {color.green()}, {color.blue()});'
                'border: 1px solid LightGrey; border-radius: 3px;')
        else:
            self._colorWidget.setStyleSheet('')

    def close(self):
        self._view.removeActor(self._actorInfo.face)
        if self._actorInfo.feature is not None:
            self._view.removeActor(self._actorInfo.feature)
