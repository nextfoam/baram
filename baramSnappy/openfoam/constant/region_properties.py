#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramSnappy.app import app
from baramSnappy.db.configurations_schema import RegionType
from baramSnappy.openfoam.dictionary_file import DictionaryFile


class RegionProperties(DictionaryFile):
    def __init__(self, fileSystem):
        super().__init__(fileSystem)
        self._setHeader(self.constantLocation(), fileSystem.REGION_PROPERTIES_FILE_NAME)

    def build(self):
        fluids = []
        solids = []
        for region in app.db.getElements('region').values():
            if region['type'] == RegionType.SOLID.value:
                solids.append(region['name'])
            else:
                fluids.append(region['name'])

        self._data = {
            'regions': [
                'fluid',
                fluids,
                'solid',
                solids
            ]
        }

        return self
