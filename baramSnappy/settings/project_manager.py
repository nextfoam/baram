#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject

from baramSnappy.db.project import Project


class ProjectManager(QObject):
    def __init__(self):
        super().__init__()

    def createProject(self, path):
        path.mkdir()

        return self.openProject(path)

    def openProject(self, path):
        project = Project(path)

        project.open()

        return project
