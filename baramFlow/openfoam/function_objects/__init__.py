#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.openfoam.file_system import FileSystem
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile


class FoDict(DictionaryFile):
    def __init__(self, objectName: str):
        super().__init__(FileSystem.caseRoot(), self.systemLocation(), objectName)

    def build(self, data):
        self._data = data
        return self
