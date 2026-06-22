#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random

from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkFiltersModeling import vtkSelectEnclosedPoints
from vtkmodules.vtkFiltersCore import vtkAppendPolyData, vtkCleanPolyData

from baramMesh.app import app


def getVolumePolyData(volumeId, geometryManager, geometries):
    surfaces = {
        gId: g for gId, g in geometries.items()
        if g.value('volume') == volumeId
    }
    if not surfaces:
        return None

    appendFilter = vtkAppendPolyData()
    for surfaceId in surfaces:
        polyData = geometryManager.polyData(surfaceId)
        if polyData:
            appendFilter.AddInputData(polyData)
    appendFilter.Update()

    cleanFilter = vtkCleanPolyData()
    cleanFilter.SetInputData(appendFilter.GetOutput())
    cleanFilter.Update()

    return cleanFilter.GetOutput()


def findInteriorPoint(targetPolyData, exclusionPolyDatas=None):
    bounds = targetPolyData.GetBounds()
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    dx, dy, dz = xmax - xmin, ymax - ymin, zmax - zmin
    if dx <= 0 or dy <= 0 or dz <= 0:
        return None

    def _g6(v):
        return float('{:.6g}'.format(v))

    candidates = [(_g6((xmin + xmax) / 2.0), _g6((ymin + ymax) / 2.0), _g6((zmin + zmax) / 2.0))]

    for div in [3, 5, 7, 9]:
        sx, sy, sz = dx / (div + 1), dy / (div + 1), dz / (div + 1)
        for i in range(1, div + 1):
            for j in range(1, div + 1):
                for k in range(1, div + 1):
                    candidates.append((_g6(xmin + i * sx), _g6(ymin + j * sy), _g6(zmin + k * sz)))

    random.seed(42)
    for _ in range(100):
        candidates.append((_g6(xmin + random.random() * dx),
                           _g6(ymin + random.random() * dy),
                           _g6(zmin + random.random() * dz)))

    pts = vtkPoints()
    for p in candidates:
        pts.InsertNextPoint(p)
    pointsPoly = vtkPolyData()
    pointsPoly.SetPoints(pts)

    tol = 1e-8 * max(dx, dy, dz)

    targetSel = vtkSelectEnclosedPoints()
    targetSel.SetInputData(pointsPoly)
    targetSel.SetSurfaceData(targetPolyData)
    targetSel.SetTolerance(tol)
    targetSel.Update()

    exclusionSels = []
    for exPoly in (exclusionPolyDatas or []):
        exB = exPoly.GetBounds()
        exMax = max(exB[1] - exB[0], exB[3] - exB[2], exB[5] - exB[4])
        exTol = 1e-8 * exMax if exMax > 0 else tol
        sel = vtkSelectEnclosedPoints()
        sel.SetInputData(pointsPoly)
        sel.SetSurfaceData(exPoly)
        sel.SetTolerance(exTol)
        sel.Update()
        exclusionSels.append(sel)

    for i, p in enumerate(candidates):
        if targetSel.IsInside(i) != 1:
            continue
        if any(sel.IsInside(i) == 1 for sel in exclusionSels):
            continue
        return p

    return None
