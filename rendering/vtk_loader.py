#!/usr/bin/env python
# -*- coding: utf-8 -*-

from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkDataSetMapper, vtkActor, vtkFollower
from vtkmodules.vtkIOLegacy import vtkPolyDataReader
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkHexahedron, vtkCellArray, vtkUnstructuredGrid, vtkPolygon, vtkPolyData
from vtkmodules.vtkCommonDataModel import vtkDataObject
from vtkmodules.vtkRenderingLOD import vtkQuadricLODActor
from vtkmodules.vtkFiltersSources import vtkLineSource, vtkSphereSource
from vtkmodules.vtkFiltersCore import vtkTubeFilter, vtkThreshold
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter
from vtkmodules.vtkIOGeometry import vtkSTLReader
from vtkmodules.vtkRenderingFreeType import vtkVectorText


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


# def loadSTL(path: Path):
#     reader = vtkSTLReader()
#     reader.SetFileName(str(path))
#     reader.Update()
#
#     mapper = vtkPolyDataMapper()
#     mapper.SetInputData(reader.GetOutput())
#     actor = vtkActor()
#     actor.SetMapper(mapper)
#     return actor


def loadSTL(path):
    reader: vtkSTLReader = vtkSTLReader()
    reader.SetFileName(str(path))
    reader.ScalarTagsOn()
    reader.Update()

    ds: vtkPolyData = reader.GetOutput()
    minSolid, maxSolid = ds.GetCellData().GetScalars('STLSolidLabeling').GetRange()
    if minSolid == maxSolid:
        return [ds]

    solids = []
    for solid in range(int(minSolid), int(maxSolid) + 1):
        threshold = vtkThreshold()
        threshold.SetInputData(ds)
        threshold.SetLowerThreshold(solid - 0.5)
        threshold.SetUpperThreshold(solid + 0.5)
        threshold.SetThresholdFunction(vtkThreshold.THRESHOLD_BETWEEN)
        threshold.SetInputArrayToProcess(0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_CELLS, 'STLSolidLabeling')
        threshold.Update()

        geometryFilter = vtkGeometryFilter()
        geometryFilter.SetInputData(threshold.GetOutput())
        geometryFilter.Update()
        solids.append(geometryFilter.GetOutput())

    return solids


def polyDataToActor(polyData):
    mapper = vtkPolyDataMapper()
    mapper.SetInputData(polyData)
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
    #
    # hexs = vtkCellArray()
    # hexs.InsertNextCell(hexahedron)

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


def polygonActor(points):
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

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(polygonPolyData)

    actor = vtkActor()
    actor.SetMapper(mapper)

    return actor
