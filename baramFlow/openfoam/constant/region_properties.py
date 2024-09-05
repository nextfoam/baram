#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

from libbaram.openfoam.constants import Directory
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.material_schema import Phase
from baramFlow.openfoam.file_system import FileSystem, FileLoadingError
from libbaram.openfoam.polymesh import isPolyMesh


class RegionProperties(DictionaryFile):
    def __init__(self):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(), Directory.REGION_PROPERTIES_FILE_NAME)

        self._data = None

    @classmethod
    def loadRegions(cls, path):
        regions = []
        regionPropFile = path / Directory.REGION_PROPERTIES_FILE_NAME

        if regionPropFile.is_file():
            regionsDict = ParsedParameterFile(regionPropFile).content['regions']
            for i in range(1, len(regionsDict), 2):
                for region in regionsDict[i]:
                    if not path.joinpath(region).is_dir():
                        raise FileLoadingError(f'"{region}" directory not found.')
                    regions.append(region)

        if regions:
            for g in regions:
                if not isPolyMesh(path.joinpath(f'{g}/polyMesh')):
                    raise FileLoadingError(f'Cannot find polyMesh files,')

        return regions if regions else ['']

    def setRegions(self, fluids, solids):
        self._data = {
            'regions': [
                'fluid',
                fluids,
                'solid',
                solids
            ]
        }

        return self

    def build(self):
        fluids = []
        solids = []
        for rname in CoreDBReader().getRegions():
            if RegionDB.getPhase(rname) == Phase.SOLID:
                solids.append(rname)
            else:
                fluids.append(rname)

        return self.setRegions(fluids, solids)
