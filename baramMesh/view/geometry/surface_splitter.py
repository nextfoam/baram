#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from vtkmodules.vtkCommonCore import vtkIdList
from vtkmodules.vtkFiltersCore import vtkCleanPolyData, vtkExtractCells
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter


def _computeCellNormals(polyData):
    pts = polyData.GetPoints()
    numCells = polyData.GetNumberOfCells()
    normals = []

    for i in range(numCells):
        cell = polyData.GetCell(i)
        if cell.GetNumberOfPoints() >= 3:
            p0 = np.array(pts.GetPoint(cell.GetPointId(0)))
            p1 = np.array(pts.GetPoint(cell.GetPointId(1)))
            p2 = np.array(pts.GetPoint(cell.GetPointId(2)))
            n = np.cross(p1 - p0, p2 - p0)
            length = np.linalg.norm(n)
            normals.append(n / length if length > 1e-15 else np.zeros(3))
        else:
            normals.append(np.zeros(3))

    return normals


def floodFillByAngle(polyData, startCellId, angleThresholdDegrees=30.0):
    if startCellId < 0 or polyData.GetNumberOfCells() == 0:
        return []

    normals = _computeCellNormals(polyData)

    cosThreshold = np.cos(np.radians(angleThresholdDegrees))

    polyData.BuildLinks()

    visited = {startCellId}
    queue = [startCellId]

    while queue:
        currentCellId = queue.pop(0)
        currentNormal = normals[currentCellId]

        cellPoints = vtkIdList()
        polyData.GetCellPoints(currentCellId, cellPoints)
        numPoints = cellPoints.GetNumberOfIds()

        for i in range(numPoints):
            edgePoints = vtkIdList()
            edgePoints.InsertNextId(cellPoints.GetId(i))
            edgePoints.InsertNextId(cellPoints.GetId((i + 1) % numPoints))

            neighbors = vtkIdList()
            polyData.GetCellNeighbors(currentCellId, edgePoints, neighbors)

            for j in range(neighbors.GetNumberOfIds()):
                neighborId = neighbors.GetId(j)
                if neighborId in visited:
                    continue

                neighborNormal = normals[neighborId]

                if (np.linalg.norm(currentNormal) < 1e-10
                        or np.linalg.norm(neighborNormal) < 1e-10):
                    continue

                dot = float(np.dot(currentNormal, neighborNormal))
                dot = max(-1.0, min(1.0, dot))

                if dot >= cosThreshold:
                    visited.add(neighborId)
                    queue.append(neighborId)

    return list(visited)


def splitPolyData(polyData, selectedCellIds):
    allCellIds = set(range(polyData.GetNumberOfCells()))
    selectedSet = set(selectedCellIds)
    remainingIds = allCellIds - selectedSet

    def _extract(cellIdSet):
        idList = vtkIdList()
        for cid in sorted(cellIdSet):
            idList.InsertNextId(cid)

        extractor = vtkExtractCells()
        extractor.SetInputData(polyData)
        extractor.SetCellList(idList)
        extractor.Update()

        geom = vtkGeometryFilter()
        geom.SetInputConnection(extractor.GetOutputPort())
        geom.Update()

        cleaner = vtkCleanPolyData()
        cleaner.SetInputConnection(geom.GetOutputPort())
        cleaner.Update()

        return cleaner.GetOutput()

    surface1 = _extract(remainingIds)
    surface2 = _extract(selectedSet)

    return surface1, surface2
