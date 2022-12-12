#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

from coredb import coredb
from openfoam.dictionary_file import DictionaryFile
from openfoam.file_system import FileSystem, FileLoadingError
from coredb.region_db import RegionDB
from coredb.material_db import Phase


class RegionProperties(DictionaryFile):
    def __init__(self):
        super().__init__(self.constantLocation(), FileSystem.REGION_PROPERTIES_FILE_NAME)

        self._data = None

    @classmethod
    def loadRegions(cls, path):
        regions = []
        regionPropFile = path / FileSystem.REGION_PROPERTIES_FILE_NAME

        if regionPropFile.is_file():
            regionsDict = ParsedParameterFile(str(regionPropFile)).content['regions']
            for i in range(1, len(regionsDict), 2):
                for region in regionsDict[i]:
                    if not path.joinpath(region).is_dir():
                        raise FileLoadingError(f'"{region}" directory not found.')
                    regions.append(region)

        if regions:
            for g in regions:
                if not FileSystem.isPolyMesh(path.joinpath(f'{g}/polyMesh')):
                    raise FileLoadingError(f'Cannot find polyMesh files,')

        return regions if regions else ['']

    def build(self):
        fluids = []
        solids = []
        for rname in coredb.CoreDB().getRegions():
            if RegionDB.getPhase(rname) == Phase.SOLID:
                solids.append(rname)
            else:
                fluids.append(rname)

        self._data = {
            'regions': [
                'fluid',
                fluids,
                'solid',
                solids
            ]
        }

        return self
