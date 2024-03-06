#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path

CASE_DIRECTORY_NAME = 'case'
FOAM_FILE_NAME = 'case.foam'


class Directory:
    CONSTANT_DIRECTORY_NAME = 'constant'
    BOUNDARY_CONDITIONS_DIRECTORY_NAME = '0'
    SYSTEM_DIRECTORY_NAME = 'system'
    POLY_MESH_DIRECTORY_NAME = 'polyMesh'
    BOUNDARY_DATA_DIRECTORY_NAME = 'boundaryData'
    REGION_PROPERTIES_FILE_NAME = 'regionProperties'
    POST_PROCESSING_DIRECTORY_NAME = 'postProcessing'
    TRI_SURFACE_DIRECTORY_NAME = 'triSurface'
    BOUNDARY_FILE_NAME = 'boundary'


def isBaramProject(path: Path):
    # ToDo: For compatibility. Remove this code block after 20251231
    # Migration from previous name of "baram.foam"
    # Begin
    oldFile = path / CASE_DIRECTORY_NAME / 'baram.foam'
    if oldFile.is_file():
        return True
    # End

    foamFile = path / CASE_DIRECTORY_NAME / FOAM_FILE_NAME

    return foamFile.is_file()
