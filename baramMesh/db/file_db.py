#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

import h5py
from vtkmodules.vtkIOXML import vtkXMLPolyDataWriter, vtkXMLPolyDataReader

CONFIGURATIONS_KEY = 'configurations'

POLYDATA_PREFIX = 'polyData'


class FileGroup(Enum):
    GEOMETRY_POLY_DATA = 'geometry'


def newFiles():
    return {
        FileGroup.GEOMETRY_POLY_DATA.value: {}
    }


def writeConfigurations(path, configurations, files):
    with h5py.File(path, 'w') as f:
        f[CONFIGURATIONS_KEY] = configurations

        geometryPolyData = f.create_group(FileGroup.GEOMETRY_POLY_DATA.value)
        polyData = files[FileGroup.GEOMETRY_POLY_DATA.value]
        for key in polyData:
            if polyData[key]:
                writer = vtkXMLPolyDataWriter()
                writer.SetInputData(polyData[key])
                writer.WriteToOutputStringOn()
                writer.Update()

                geometryPolyData[key] = writer.GetOutputString()


def readConfigurations(path):
    with h5py.File(path, 'r') as f:
        configurations = f[CONFIGURATIONS_KEY][()]

        files = {}
        maxIds = {}

        geometryPolyData = f[FileGroup.GEOMETRY_POLY_DATA.value]
        polyData = {}
        maxIndex = 0
        prefixLen = len(POLYDATA_PREFIX)
        for key in geometryPolyData.keys():
            reader = vtkXMLPolyDataReader()
            reader.ReadFromInputStringOn()
            reader.SetInputString(geometryPolyData[key][()])
            reader.Update()
            polyData[key] = reader.GetOutput()

            index = int(key[prefixLen:])
            if index > maxIndex:
                maxIndex = index

        files[FileGroup.GEOMETRY_POLY_DATA.value] = polyData
        maxIds[FileGroup.GEOMETRY_POLY_DATA.value] = maxIndex

        return configurations, files, maxIds
