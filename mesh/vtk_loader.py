#!/usr/bin/env python
# -*- coding: utf-8 -*-
import vtk
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper
from vtkmodules.vtkIOLegacy import vtkPolyDataReader
from .mesh_model import ActorInfo


def loadVtkFile(file):
    if not file.exists():
        return None

    r = vtkPolyDataReader()
    r.SetFileName(file)
    r.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(r.GetOutput())

    actor = vtk.vtkQuadricLODActor()    # vtkActor()
    actor.SetMapper(mapper)

    actorInfo = ActorInfo(actor)
    actorInfo.visibility = False

    return actorInfo
