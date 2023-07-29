#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from app import app
from libbaram.utils import rmtree
from view.geometry.geometry_page import GeometryPage
from view.base_grid.base_grid_page import BaseGridPage
from view.castellation.castellation_page import CastellationPage
from .actor_manager import ActorGroup


def removeTimeDirectory(time):
    path = app.fileSystem.timePath(time)
    if path.exists():
        rmtree(path)

    for path in app.fileSystem.caseRoot().glob(f'processor*/{time}'):
        rmtree(path)


class Step:
    def __init__(self):
        self._page = None

    def page(self):
        return self._page

    def createPage(self):
        self._page = self._createPage()
        
        return self._page

    def _createPage(self):
        return QWidget()


class GeometryStep(Step):
    def isNextStepAvailable(self):
        return not app.window.geometryManager.isEmpty()

    def clearResult(self):
        return

    def _createPage(self):
        return GeometryPage()


class BaseGridStep(Step):
    def isNextStepAvailable(self):
        return app.fileSystem.boundaryFilePath().exists()

    def clearResult(self):
        path = app.fileSystem.polyMeshPath()
        if path.exists():
            rmtree(path)

    def _createPage(self):
        return BaseGridPage()


class CastellationStep(Step):
    _renderingGroups = {
        ActorGroup.GEOMETRY: True,
        ActorGroup.MESH: False
    }

    def isNextStepAvailable(self):
        return False

    def clearResult(self):
        removeTimeDirectory(CastellationPage.OUTPUT_TIME)

    def _createPage(self):
        return CastellationPage()
