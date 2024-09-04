#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.openfoam.file_system import FileSystem


class CellZonesToRegions(DictionaryFile):
    def __init__(self):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(), 'cellZonesToRegions')

    def loadCellZones(self):
        return ParsedParameterFile(self.fullPath()).content['fluentCellZones']

    def setCellZoneRegions(self, cellZones, regions):
        self._data = {
            'fluentCellZones': cellZones,
            'regions': regions
        }

        return self

    def setSingleCellZone(self, cellZone):
        self._data = {
            'fluentCellZones': {
                cellZone: 'fluid'
            },
            'regions': {
                'region': {
                    'cellZones': [cellZone],
                    'type': 'fluid'
                }
            }
        }

        return self
