#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import asyncio

from coredb.project import Project


class FileSystem:
    CASE_DIRECTORY_NAME = 'case'
    CONSTANT_DIRECTORY_NAME = 'constant'
    BOUNDARY_CONDITIONS_DIRECTORY_NAME = '0'
    SYSTEM_DIRECTORY_NAME = 'system'
    POLY_MESH_DIRECTORY_NAME = 'polyMesh'
    BOUNDARY_DATA_DIRECTORY_NAME = 'boundaryData'

    _casePath = None
    _constantPath = None
    _boundaryConditionsPath = None
    _systemPath = None

    @classmethod
    def setup(cls):
        cls._casePath = cls.makeDir(Project.instance().path, cls.CASE_DIRECTORY_NAME)
        cls._constantPath = os.path.join(cls._casePath, cls.CONSTANT_DIRECTORY_NAME)

    @classmethod
    def initCaseDir(cls):
        cls._boundaryConditionsPath = cls.makeDir(cls._casePath, cls.BOUNDARY_CONDITIONS_DIRECTORY_NAME)
        cls._systemPath = cls.makeDir(cls._casePath, cls.SYSTEM_DIRECTORY_NAME)

    @classmethod
    def initRegionDirs(cls, rname):
        cls.makeDir(cls._boundaryConditionsPath, rname)
        cls.makeDir(cls._constantPath, rname)
        cls.makeDir(cls._systemPath, rname)

    @classmethod
    def caseRoot(cls):
        return cls._casePath

    @classmethod
    def constantPath(cls, rname=None):
        return os.path.join(cls._constantPath, rname) if rname else cls._constantPath

    @classmethod
    def boundaryConditionsPath(cls, rname=None):
        return os.path.join(cls._boundaryConditionsPath, rname) if rname else cls._boundaryConditionsPath

    @classmethod
    def systemPath(cls, rname=None):
        return os.path.join(cls._systemPath, rname) if rname else cls._systemPath

    @classmethod
    def boundaryFilePath(cls, rname):
        return os.path.join(cls.constantPath(rname), cls.POLY_MESH_DIRECTORY_NAME, 'boundary')

    @classmethod
    def cellZonesFilePath(cls, rname):
        return os.path.join(cls.constantPath(rname), cls.POLY_MESH_DIRECTORY_NAME, 'cellZones')

    @classmethod
    def boundaryDataPath(cls, rname):
        return os.path.join(cls.constantPath(rname), rname, cls.BOUNDARY_DATA_DIRECTORY_NAME)

    @classmethod
    def foamFilePath(cls):
        return os.path.join(cls._casePath, 'baram.foam')

    @classmethod
    def _copyMeshFromInternal(cls, directory):
        if os.path.exists(cls._constantPath):
            shutil.rmtree(cls._constantPath)

        shutil.copytree(directory, cls._constantPath)

        with open(cls.foamFilePath(), 'a'):
            pass

    @classmethod
    async def copyMeshFrom(cls, directory):
        await asyncio.to_thread(cls._copyMeshFromInternal, directory)

    @classmethod
    def makeDir(cls, parent, directory):
        path = os.path.join(parent, directory)
        if not os.path.exists(path):
            os.mkdir(path)

        return path
