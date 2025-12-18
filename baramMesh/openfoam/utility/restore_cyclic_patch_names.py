#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PyFoam.Basics.DataStructures import DictProxy
from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict

from baramMesh.app import app
from baramMesh.db.configurations_schema import CFDType


class RestoreCyclicPatchNames:
    def __init__(self, prefix: str, fileSystem):
        self._prefix = prefix
        self._fileSystem = fileSystem

    def restore(self):
        self._updateCyclicPatchNames(self._fileSystem.boundaryFilePath())

    def _updateCyclicPatchNames(self, path: Path):
        boundaryDict: ParsedBoundaryDict = ParsedBoundaryDict(str(path), treatBinaryAsASCII=True)
        boundaries = boundaryDict.content.keys()  # To save the order of boundaries
        for interface in app.db.getElements(
                'geometry', lambda i, e: e['cfdType'] == CFDType.INTERFACE.value and not e['interRegion'] and not e['nonConformal']).values():
            master = interface.value('name')
            slave = master + '_slave'
            oldMaster = self._prefix + master
            oldSlave = self._prefix + slave

            if oldMaster not in boundaryDict.content:
                continue

            assert oldSlave in boundaryDict.content

            assert boundaryDict.content[oldMaster]['type'] == 'cyclic'
            assert boundaryDict.content[oldSlave]['type'] == 'cyclic'

            boundaryDict.content[oldMaster]['type'] = 'patch'
            boundaryDict.content[oldSlave]['type'] = 'patch'

            # xx[newKey] = xx.pop(oldKey) cannot be used here
            # because boundaryDict is not a python dict but a PyFoam.Basics.DataStructures.DictProxy
            boundaryDict.content[master] = boundaryDict.content[oldMaster]
            boundaryDict.content[slave] = boundaryDict.content[oldSlave]
            del boundaryDict.content[oldMaster]
            del boundaryDict.content[oldSlave]

            self._removeEntry(boundaryDict, master, 'inGroups')
            self._removeEntry(boundaryDict, slave,  'inGroups')
            self._removeEntry(boundaryDict, master, 'matchTolerance')
            self._removeEntry(boundaryDict, slave,  'matchTolerance')
            self._removeEntry(boundaryDict, master, 'transform')
            self._removeEntry(boundaryDict, slave,  'transform')
            self._removeEntry(boundaryDict, master, 'neighbourPatch')
            self._removeEntry(boundaryDict, slave,  'neighbourPatch')


        #
        #  Restore the original boundary order
        #
        oldContent = boundaryDict.content
        boundaryDict.content = DictProxy()
        for oldName in boundaries:
            bName = oldName[len(self._prefix):] if oldName.startswith(self._prefix) else oldName
            boundaryDict.content[bName] = oldContent[bName]

        boundaryDict.writeFile()

    @staticmethod
    def _removeEntry(bDict, bName, keyword):
        if keyword in bDict.content[bName]:
            del bDict.content[bName][keyword]

