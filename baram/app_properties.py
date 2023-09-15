#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtGui import QIcon, QPixmap

from resources import resource


class AppProperties:
    def __init__(self, properties):
        self._name = properties['name']
        self._fullName = properties['fullName']
        self._iconFile = str(resource.file(properties['iconResource']))
        self._logoFile = str(resource.file(properties['logoResource']))

    @property
    def name(self):
        return self._name

    @property
    def fullName(self):
        return self._fullName

    def icon(self):
        return QIcon(self._iconFile)

    def logo(self):
        return QPixmap(self._logoFile)
