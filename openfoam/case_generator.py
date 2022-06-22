#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import os

from coredb import coredb
from .operating_conditions import OperatingConditions
from .MRF_properties import MRFProperties


class CaseGenerator:
    def __init__(self, path):
        self._path = path
        self._db = coredb.CoreDB()

    def generateFiles(self):
        # shutil.rmtree(self._path)
        constantPath = self._path + '/constant'
        if not os.path.exists(constantPath):
            os.mkdir(constantPath)

        regions = self._db.getRegions()
        for rname in regions:
            rpath = f'{constantPath}/{rname}'
            if not os.path.exists(rpath):
                os.mkdir(rpath)

            with open(f'{rpath}/operatingConditions', "w") as f:
                f.write(str(OperatingConditions(rname)))

            properties = str(MRFProperties(rname))
            if properties:
                with open(f'{rpath}/MRFProperties', "w") as f:
                    f.write(properties)

