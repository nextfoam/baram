#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from resources import resource


APP_VERSION = '26.2.0'


@dataclass
class AppProperties:
    name: str
    fullName: str
    iconResource: str
    logoResource: str
    version: str            = APP_VERSION
    projectSuffix: str      = None
    analyticsEnabled: bool  = True  # OEM variants can disable analytics entirely

    def icon(self):
        return QIcon(str(resource.file(self.iconResource)))

    def logo(self):
        return QPixmap(str(resource.file(self.logoResource)))


flowAppProperties = AppProperties(
    name='BaramFlow',
    fullName=QApplication.translate('AppProperties', 'BaramFlow'),
    iconResource='baramFlow.ico',
    logoResource='baramFlow.ico',
    projectSuffix='.bf'
)


@dataclass
class MeshAppProperties(AppProperties):
    flowAppName: str    = flowAppProperties.fullName
    exportSuffix: str   = flowAppProperties.projectSuffix
    flowExecutable: str = flowAppProperties.name + '.exe'


meshAppProperties = MeshAppProperties(
    name='BaramMesh',
    fullName=QApplication.translate('AppProperties', 'BaramMesh'),
    iconResource='baramMesh.ico',
    logoResource='baramMesh.ico',
    projectSuffix='.bm',
    flowExecutable='baramFlow.exe'
)
