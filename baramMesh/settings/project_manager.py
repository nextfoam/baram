#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject

from baramMesh.db.project import Project


class ProjectManager(QObject):
    def __init__(self):
        super().__init__()

    def createProject(self, path):
        path.mkdir()

        project = Project(path)
        project.new()

        return project

    def openProject(self, path):
        project = Project(path)
        project.open()

        return project
