#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from PySide6.QtGui import QIcon, QPixmap

from resources import resource

@dataclass
class AppProperties:
    name: str
    fullName: str
    iconResource: str
    logoResource: str
    projectSuffix: str = None

    def icon(self):
        return QIcon(str(resource.file(self.iconResource)))

    def logo(self):
        return QPixmap(str(resource.file(self.logoResource)))
