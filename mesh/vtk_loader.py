#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkDataSetMapper, vtkActor
from vtkmodules.vtkIOLegacy import vtkPolyDataReader
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkHexahedron, vtkCellArray, vtkUnstructuredGrid
from vtkmodules.vtkRenderingLOD import vtkQuadricLODActor
from vtkmodules.vtkFiltersSources import vtkLineSource, vtkSphereSource
from vtkmodules.vtkFiltersCore import vtkTubeFilter
from vtkmodules.vtkIOGeometry import vtkSTLReader


def loadVtkFile(file):
    if not file.exists():
        return None

    r = vtkPolyDataReader()
    r.SetFileName(file)
    r.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(r.GetOutput())

    actor = vtkQuadricLODActor()    # vtkActor()
    actor.SetMapper(mapper)

    return actor


def loadSTL(path: Path):
    reader = vtkSTLReader()
    reader.SetFileName(str(path))
    reader.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(reader.GetOutput())
    actor = vtkActor()
    actor.SetMapper(mapper)
    return actor


def hexActor(point1, point2):
    minX, minY, minZ = point1
    maxX, maxY, maxZ = point2

    pointCoordinates = list()
    pointCoordinates.append([minX, minY, minZ])
    pointCoordinates.append([maxX, minY, minZ])
    pointCoordinates.append([maxX, maxY, minZ])
    pointCoordinates.append([minX, maxY, minZ])
    pointCoordinates.append([minX, minY, maxZ])
    pointCoordinates.append([maxX, minY, maxZ])
    pointCoordinates.append([maxX, maxY, maxZ])
    pointCoordinates.append([minX, maxY, maxZ])

    points = vtkPoints()

    hexahedron = vtkHexahedron()

    for i in range(0, len(pointCoordinates)):
        points.InsertNextPoint(pointCoordinates[i])
        hexahedron.GetPointIds().SetId(i, i)

    hexs = vtkCellArray()
    hexs.InsertNextCell(hexahedron)

    uGrid = vtkUnstructuredGrid()
    uGrid.SetPoints(points)
    uGrid.InsertNextCell(hexahedron.GetCellType(), hexahedron.GetPointIds())

    mapper = vtkDataSetMapper()
    mapper.SetInputData(uGrid)

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(0.8, 0.8, 0.8)

    return actor


def cylinderActor(point1, point2, radius):
    line = vtkLineSource()
    line.SetPoint1(*point1)
    line.SetPoint2(*point2)

    cyl = vtkTubeFilter()
    cyl.SetInputConnection(line.GetOutputPort())
    cyl.SetRadius(float(radius))
    cyl.SetNumberOfSides(32)
    cyl.CappingOn()

    mapper = vtkDataSetMapper()
    mapper.SetInputConnection(cyl.GetOutputPort())

    actor = vtkQuadricLODActor()
    actor.SetMapper(mapper)

    return actor


def sphereActor(point, radius):
    sphere = vtkSphereSource()
    sphere.SetCenter(*point)
    sphere.SetRadius(radius)
    sphere.SetPhiResolution(100)
    sphere.SetThetaResolution(100)

    mapper = vtkDataSetMapper()
    mapper.SetInputConnection(sphere.GetOutputPort())

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(0.8, 0.8, 0.8)

    return actor
