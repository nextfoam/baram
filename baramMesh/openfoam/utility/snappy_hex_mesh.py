#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkCommonDataModel import vtkPlane
from vtkmodules.vtkFiltersCore import vtkFeatureEdges, vtkAppendPolyData, vtkTriangleFilter, vtkPolyDataPlaneCutter
from vtkmodules.vtkFiltersCore import vtkCleanPolyData
from vtkmodules.vtkIOGeometry import vtkSTLWriter, vtkOBJWriter

from libbaram.process import ProcessError
from libbaram.run import RunParallelUtility

from baramMesh.app import app
from baramMesh.db.configurations_schema import GeometryType, Shape, CFDType
from baramMesh.openfoam.file_system import makeDir
from baramMesh.openfoam.system.snappy_hex_mesh_dict import SnappyHexMeshDict
from baramMesh.openfoam.system.topo_set_dict import TopoSetDict
from libbaram.utils import copyOrLink


CASTELLATION_OUTPUT_TIME    = 1
SNAP_OUTPUT_TIME            = 2
BOUNDARY_LAYER_OUTPUT_TIME  = 3


def Plane(ox, oy, oz, nx, ny, nz):
    plane = vtkPlane()
    plane.SetOrigin(ox, oy, oz)
    plane.SetNormal(nx, ny, nz)

    return plane


def _writeFeatureFile(path: Path, pd):
    edges = vtkFeatureEdges()
    edges.SetInputData(pd)
    edges.SetNonManifoldEdges(app.db.getValue('castellation/vtkNonManifoldEdges'))
    edges.SetBoundaryEdges(app.db.getValue('castellation/vtkBoundaryEdges'))
    edges.SetFeatureAngle(float(app.db.getValue('castellation/resolveFeatureAngle')))
    edges.Update()

    features = vtkAppendPolyData()
    features.AddInputData(edges.GetOutput())

    _, geometry = app.window.geometryManager.getBoundingHex6()
    if geometry is not None:  # boundingHex6 is configured
        x1, y1, z1 = geometry.vector('point1')
        x2, y2, z2 = geometry.vector('point2')

        planes = [
            Plane(x1, 0, 0, -1, 0, 0),
            Plane(x2, 0, 0, 1, 0, 0),
            Plane(0, y1, 0, 0, -1, 0),
            Plane(0, y2, 0, 0, 1, 0),
            Plane(0, 0, z1, 0, 0, -1),
            Plane(0, 0, z2, 0, 0, 1)
        ]

        # vtkTriangleFilter is used to convert "Triangle Strips" to Triangles
        tf = vtkTriangleFilter()
        tf.SetInputData(pd)
        tf.Update()

        # "cutter" should be created in the loop
        # because its pointer is handed over to vtkAppendPolyData
        for p in planes:
            cutter = vtkPolyDataPlaneCutter()
            cutter.SetInputData(tf.GetOutput())
            cutter.SetPlane(p)
            cutter.Update()

            if cutter.GetOutput().GetNumberOfCells() > 0:
                features.AddInputData(cutter.GetOutput())

    features.Update()

    writer = vtkOBJWriter()
    writer.SetFileName(str(path))
    writer.SetInputData(features.GetOutput())
    writer.Write()


class SnappyHexMesh(QObject):
    snappyStarted = Signal()
    snappyStopped = Signal()

    def __init__(self):
        super().__init__()
        self._cm = None

    async def castellation(self):
        time = CASTELLATION_OUTPUT_TIME

        try:
            self._writeGeometryFiles()

            snapDict = SnappyHexMeshDict(castellationMesh=True).build()
            if app.db.elementCount('region') > 1:
                snapDict.write()
            else:
                snapDict.updateForCellZoneInterfacesSnap().write()

            console = app.consoleView

            self._cm = RunParallelUtility('snappyHexMesh', cwd=app.fileSystem.caseRoot(),
                                          parallel=app.project.parallelEnvironment())
            self._cm.output.connect(console.append)
            self._cm.errorOutput.connect(console.appendError)
            await self._cm.start()
            rc = await self._cm.wait()
            if rc != 0:
                raise ProcessError(rc)

            self._cm = RunParallelUtility('checkMesh',
                                          '-allRegions',
                                          '-writeFields', '(cellAspectRatio cellVolume nonOrthoAngle skewness)',
                                          '-time', str(time),
                                          '-case', app.fileSystem.caseRoot(),
                                          cwd=app.fileSystem.caseRoot(), parallel=app.project.parallelEnvironment())
            self._cm.output.connect(console.append)
            self._cm.errorOutput.connect(console.appendError)
            await self._cm.start()
            await self._cm.wait()
        except Exception as e:
            raise e
        finally:
            self._cm = None

    async def snap(self):
        time = SNAP_OUTPUT_TIME

        try:
            parallel = app.project.parallelEnvironment()

            snapDict = SnappyHexMeshDict(snap=True).build()
            if app.db.elementCount('region') > 1:
                snapDict.write()
            else:
                snapDict.updateForCellZoneInterfacesSnap().write()

            console = app.consoleView

            self._cm = RunParallelUtility('snappyHexMesh', cwd=app.fileSystem.caseRoot(), parallel=parallel)
            self._cm.output.connect(console.append)
            self._cm.errorOutput.connect(console.appendError)
            await self._cm.start()
            rc = await self._cm.wait()
            if rc != 0:
                raise ProcessError(rc)

            if app.db.elementCount('region') > 1:
                TopoSetDict().build(TopoSetDict.Mode.CREATE_REGIONS).write()

                self._cm = RunParallelUtility('topoSet', cwd=app.fileSystem.caseRoot(), parallel=parallel)
                self._cm.output.connect(console.append)
                self._cm.errorOutput.connect(console.appendError)
                await self._cm.start()
                rc = await self._cm.wait()
                if rc != 0:
                    raise ProcessError(rc)

                if app.db.elementCount('geometry', lambda i, e: e['cfdType'] == CFDType.CELL_ZONE.value):
                    snapDict.updateForCellZoneInterfacesSnap().removeBufferLayers().write()

                    self._cm = RunParallelUtility('snappyHexMesh', '-overwrite', cwd=app.fileSystem.caseRoot(),
                                                  parallel=parallel)
                    self._cm.output.connect(console.append)
                    self._cm.errorOutput.connect(console.appendError)
                    await self._cm.start()
                    rc = await self._cm.wait()
                    if rc != 0:
                        raise ProcessError(rc)

            self._cm = RunParallelUtility('checkMesh',
                                          '-allRegions',
                                          '-writeFields', '(cellAspectRatio cellVolume nonOrthoAngle skewness)',
                                          '-time', str(time),
                                          '-case', app.fileSystem.caseRoot(),
                                          cwd=app.fileSystem.caseRoot(), parallel=app.project.parallelEnvironment())
            self._cm.output.connect(console.append)
            self._cm.errorOutput.connect(console.appendError)
            await self._cm.start()
            await self._cm.wait()
        except Exception as e:
            raise e
        finally:
            self._cm = None

    async def addLayers(self):
        time = BOUNDARY_LAYER_OUTPUT_TIME

        try:
            console = app.consoleView

            #
            #  Add Boundary Layers
            #

            boundaryLayersAdded = False

            if app.db.getElements('addLayers/layers').items():
                SnappyHexMeshDict(addLayers=True).build().write()

                self._cm = RunParallelUtility('snappyHexMesh', cwd=app.fileSystem.caseRoot(),
                                              parallel=app.project.parallelEnvironment())
                self._cm.output.connect(console.append)
                self._cm.errorOutput.connect(console.appendError)
                await self._cm.start()
                rc = await self._cm.wait()
                if rc != 0:
                    raise ProcessError(rc)

                boundaryLayersAdded = True

            else:
                self._createOutputPath(time)

            if boundaryLayersAdded:
                self._cm = RunParallelUtility('checkMesh',
                                              '-allRegions',
                                              '-writeFields', '(cellAspectRatio cellVolume nonOrthoAngle skewness)',
                                              '-time', str(time),
                                              '-case', app.fileSystem.caseRoot(),
                                              cwd=app.fileSystem.caseRoot(), parallel=app.project.parallelEnvironment())
                self._cm.output.connect(console.append)
                self._cm.errorOutput.connect(console.appendError)
                await self._cm.start()
                await self._cm.wait()
            else:  # Mesh Quality information should be in this time folder
                nProcFolders = app.fileSystem.numberOfProcessorFolders()
                if nProcFolders == 0:
                    source = app.fileSystem.timePath(time - 1)
                    target = app.fileSystem.timePath(time)
                    copyOrLink(source / 'cellAspectRatio', target / 'cellAspectRatio')
                    copyOrLink(source / 'cellVolume', target / 'cellVolume')
                    copyOrLink(source / 'nonOrthoAngle', target / 'nonOrthoAngle')
                    copyOrLink(source / 'skewness', target / 'skewness')
                else:
                    for processorNo in range(nProcFolders):
                        source = app.fileSystem.timePath(time - 1, processorNo)
                        target = app.fileSystem.timePath(time, processorNo)
                        copyOrLink(source / 'cellAspectRatio', target / 'cellAspectRatio')
                        copyOrLink(source / 'cellVolume', target / 'cellVolume')
                        copyOrLink(source / 'nonOrthoAngle', target / 'nonOrthoAngle')
                        copyOrLink(source / 'skewness', target / 'skewness')
        except Exception as e:
            raise e
        finally:
            self._cm = None

    def _writeGeometryFiles(self):
        def writeGeometryFile(path: Path, pd):
            writer = vtkSTLWriter()
            writer.SetFileName(str(path))
            writer.SetInputData(pd)
            writer.Write()

        filePath = app.fileSystem.triSurfacePath()
        geometryManager = app.window.geometryManager
        geometries = app.db.getElements('geometry')

        for gId, geometry in geometries.items():
            if geometryManager.isBoundingHex6(gId):
                continue

            if geometry.value('gType') == GeometryType.SURFACE.value:
                polyData = geometryManager.polyData(gId)
                _writeFeatureFile(filePath / f"{geometry.value('name')}.obj", polyData)

                if geometry.value('shape') == Shape.TRI_SURFACE_MESH.value:
                    volume = geometries[geometry.value('volume')] if geometry.value('volume') else None
                    if (geometry.value('cfdType') != CFDType.NONE.value
                            or geometry.value('castellationGroup')
                            or (volume is not None and volume.value('cfdType') != CFDType.NONE.value)):
                        writeGeometryFile(filePath / f"{geometry.value('name')}.stl", polyData)

            else:  # geometry['gType'] == GeometryType.VOLUME.value
                if geometry.value('shape') == Shape.TRI_SURFACE_MESH.value and (
                        geometry.value('cfdType') != CFDType.NONE.value or geometry.value('castellationGroup')):
                    appendFilter = vtkAppendPolyData()
                    for surfaceId in geometryManager.subSurfaces(gId):
                        appendFilter.AddInputData(geometryManager.polyData(surfaceId))

                    cleanFilter = vtkCleanPolyData()
                    cleanFilter.SetInputConnection(appendFilter.GetOutputPort())
                    cleanFilter.Update()

                    writeGeometryFile(filePath / f"{geometry.value('name')}.stl", cleanFilter.GetOutput())

    def isRunning(self):
        return self._cm is not None

    def cancel(self):
        if self._cm:
            self._cm.cancel()

    def _createOutputPath(self, time):
        output = str(time)

        if app.project.parallelCores() > 1:
            folders = app.fileSystem.processorFolders()
            if folders:
                for f in folders:
                    makeDir(f, output, True)

                return

        makeDir(app.fileSystem.caseRoot(), output, True)


snappyHexMesh = SnappyHexMesh()