#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.constants import Directory
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramMesh.app import app
from baramMesh.db.configurations_schema import RegionType


class RegionProperties(DictionaryFile):
    def __init__(self, casePath):
        super().__init__(casePath, self.constantLocation(), Directory.REGION_PROPERTIES_FILE_NAME)

    def build(self):
        regions = app.db.getElements('region')

        if len(regions) > 1:
            fluids = []
            solids = []
            for region in regions.values():
                if region.value('type') == RegionType.SOLID.value:
                    solids.append(region.value('name'))
                else:
                    fluids.append(region.value('name'))

            self._data = {
                'regions': [
                    'fluid',
                    fluids,
                    'solid',
                    solids
                ]
            }

        return self
