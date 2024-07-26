#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile


class CollapseDict(DictionaryFile):
    def __init__(self, fileSystem):
        super().__init__(fileSystem.caseRoot(), self.systemLocation(), 'collapseDict')

    def create(self):
        self.copyFromResource('openfoam/dictionaries/collapseDict')

        return self
