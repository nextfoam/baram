#!/usr/bin/env python
# -*- coding: utf-8 -*-

from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor, vtkFollower
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkHexahedron, vtkCellArray, vtkUnstructuredGrid, vtkPolygon, vtkPolyData
from vtkmodules.vtkFiltersSources import vtkLineSource, vtkSphereSource
from vtkmodules.vtkFiltersCore import vtkTubeFilter, vtkFeatureEdges
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
from vtkmodules.vtkRenderingFreeType import vtkVectorText


def polyDataToActor(polyData):
    mapper = vtkPolyDataMapper()
    mapper.SetInputData(polyData)
    mapper.ScalarVisibilityOff()
    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetAmbient(0.2)
    actor.GetProperty().SetDiffuse(0.3)

    return actor


def polyDataToFeatureActor(polyData):
    edges = vtkFeatureEdges()
    edges.SetInputData(polyData)
    edges.Update()

    return polyDataToActor(edges.GetOutput())


def hexPolyData(point1, point2):
    xMin, yMin, zMin = point1
    xMax, yMax, zMax = point2

    pointCoordinates = list()
    pointCoordinates.append([xMin, yMin, zMin])
    pointCoordinates.append([xMax, yMin, zMin])
    pointCoordinates.append([xMax, yMax, zMin])
    pointCoordinates.append([xMin, yMax, zMin])
    pointCoordinates.append([xMin, yMin, zMax])
    pointCoordinates.append([xMax, yMin, zMax])
    pointCoordinates.append([xMax, yMax, zMax])
    pointCoordinates.append([xMin, yMax, zMax])

    points = vtkPoints()

    hexahedron = vtkHexahedron()

    for i in range(0, len(pointCoordinates)):
        points.InsertNextPoint(pointCoordinates[i])
        hexahedron.GetPointIds().SetId(i, i)
    #
    # hexs = vtkCellArray()
    # hexs.InsertNextCell(hexahedron)

    uGrid = vtkUnstructuredGrid()
    uGrid.SetPoints(points)
    uGrid.InsertNextCell(hexahedron.GetCellType(), hexahedron.GetPointIds())

    geometryFilter = vtkGeometryFilter()
    geometryFilter.SetInputData(uGrid)
    geometryFilter.Update()
    #
    # mapper = vtkDataSetMapper()
    # mapper.SetInputData(geometryFilter.GetOutput())
    #
    # actor = vtkActor()
    # actor.SetMapper(mapper)
    # actor.GetProperty().SetColor(0.8, 0.8, 0.8)

    return geometryFilter.GetOutput()


def cylinderPolyData(point1, point2, radius):
    line = vtkLineSource()
    line.SetPoint1(*point1)
    line.SetPoint2(*point2)

    cyl = vtkTubeFilter()
    cyl.SetInputConnection(line.GetOutputPort())
    cyl.SetRadius(float(radius))
    cyl.SetNumberOfSides(64)
    cyl.CappingOn()

    geometryFilter = vtkGeometryFilter()
    geometryFilter.SetInputConnection(cyl.GetOutputPort())
    geometryFilter.Update()

    return geometryFilter.GetOutput()


def spherePolyData(point, radius):
    sphere = vtkSphereSource()
    sphere.SetCenter(*point)
    sphere.SetRadius(radius)
    sphere.SetPhiResolution(100)
    sphere.SetThetaResolution(100)
    sphere.Update()
    #
    # mapper = vtkDataSetMapper()
    # mapper.SetInputConnection(sphere.GetOutputPort())
    #
    # geometryFilter = vtkGeometryFilter()
    # geometryFilter.SetInputConnection(mapper.GetOutputPort())
    # geometryFilter.Update()

    return sphere.GetOutput()


def polygonPolyData(points):
    vPoints = vtkPoints()
    for p in points:
        vPoints.InsertNextPoint(*p)

    polygon = vtkPolygon()
    polygon.GetPointIds().SetNumberOfIds(len(points))
    for i in range(len(points)):
        polygon.GetPointIds().SetId(i, i)

    polygons = vtkCellArray()
    polygons.InsertNextCell(polygon)

    polygonPolyData = vtkPolyData()
    polygonPolyData.SetPoints(vPoints)
    polygonPolyData.SetPolys(polygons)
    #
    # mapper = vtkPolyDataMapper()
    # mapper.SetInputData(polygonPolyData)
    #
    # actor = vtkActor()
    # actor.SetMapper(mapper)

    return polygonPolyData


def lineActor(point1, point2):
    lineSource = vtkLineSource()
    lineSource.SetPoint1(point1)
    lineSource.SetPoint2(point2)

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(lineSource.GetOutputPort())

    actor = vtkActor()
    actor.SetMapper(mapper)

    return actor


def labelActor(text):
    label = vtkVectorText()
    label.SetText(text)

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(label.GetOutputPort())

    actor = vtkFollower()
    actor.SetMapper(mapper)

    return actor
