#!/usr/bin/env python
# -*- coding: utf-8 -*-

from xml.etree.ElementTree import Element

from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict

from libbaram.openfoam.constants import Directory

from baramFlow.base.boundary.boundary_data import BoundaryData
from baramFlow.base.cell_zone.cell_zone import CellZoneData
from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.base.region.poly_mesh import PolyMeshRegion
from baramFlow.base.region.region_data import RegionModel, BoundaryModel, CellZoneModel
from baramFlow.coredb.boundary_db import GeometricalType, BoundaryType
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.libdb import E, nsmap
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.region_db import CELL_ZONE_NAME_FOR_REGION
from baramFlow.openfoam.file_system import FileSystem

REGIONS_XPATH = '/regions'


class Regions:
    initialPressure = '0'
    defaultMaterial = '1'

    def __init__(self):
        self._regions: dict[str, RegionModel] = {}
        self._boundaries: dict[str, BoundaryModel] = {}
        self._cellZones: dict[str, CellZoneModel] = {}

    @property
    def regions(self):
        return self._regions

    @property
    def boundaries(self):
        return self._boundaries

    @property
    def cellZones(self):
        return self._cellZones

    def load(self, e: Element):
        for r in e.findall('region', namespaces=nsmap):
            region = RegionModel.fromElement(r)
            self._regions[region.name] = region

            polyMeshBoundaries = ParsedBoundaryDict(FileSystem.polyMeshPath(region.name) / Directory.BOUNDARY_FILE_NAME,
                                                    treatBinaryAsASCII=True)

            for model in region.boundaries:
                model.startFace = polyMeshBoundaries[model.name]['startFace']
                self._boundaries[model.bcid] = model

            region.sortBoundaries()

            for model in region.cellZones:
                self._cellZones[model.czid] = model

    def clear(self):
        self._regions.clear()
        self._boundaries.clear()
        self._cellZones.clear()

    def replace(self, data: list[PolyMeshRegion]):
        self.clear()

        # Initial value of "0" for pressure in density-based solvers causes trouble by making density zero
        # because operating pressure is fixed to "0" for density-based solvers
        if GeneralDB.isDensityBased():
            self.initialPressure = '103125'

        self.defaultMaterial = MaterialDB.getMaterials()[0][0]

        for r in data:
            self._addRegion(r.rname)

            for name, bc in r.boundaries.items():
                boundary = BoundaryData(name=name,
                                        geometricalType=GeometricalType(bc['type']),
                                        bctype=BoundaryType(bc['bctype']))
                boundary.patchInteraction.type = DPMModelManager.getDefaultPatchInteractionType(boundary.bctype)

                self._addBoundary(BoundaryModel(boundary=boundary,
                                                startFace=bc['startFace'],
                                                rname=r.rname))

                if 'couple' in bc and 'bcid' in bc['couple']:
                    couple = self._boundaries[bc['couple']['bcid']]
                    boundary.coupledBoundary = couple.bcid
                    couple.boundary.coupledBoundary = boundary.bcid

                bc['bcid'] = boundary.bcid

            self._regions[r.rname].sortBoundaries()

            for name in r.cellZones:
                self._addCellZone(CellZoneModel(configurations=CellZoneData(name=name,
                                                                            rname=r.rname),
                                                rname=r.rname))

    def updatePolyMeshData(self, polyMeshBoundaries: dict):
        for region in self._regions.values():
            for model in region.boundaries:
                model.startFace = polyMeshBoundaries[region.name][model.name]['startFace']

            region.sortBoundaries()


    def toElement(self):
        element = E('regions')

        for region in self._regions.values():
            element.append(region.toElement())

        return element

    def _addRegion(self, rname):
        self._regions[rname] = RegionModel(name=rname, material=self.defaultMaterial)
        self._regions[rname].initialization.initialValues.pressure = self.initialPressure
        self._addCellZone(CellZoneModel(configurations=CellZoneData(name=CELL_ZONE_NAME_FOR_REGION,
                                                                    rname=rname),
                                        rname=rname))

    def _addBoundary(self, model: BoundaryModel):
        model.setID(str(len(self._boundaries) + 1))
        self._boundaries[model.bcid] = model
        self._regions[model.rname].addBoundary(model)

    def _addCellZone(self, model: CellZoneModel):
        model.setID(str(len(self._cellZones) + 1))
        self._cellZones[model.czid] = model
        self._regions[model.rname].addCellZone(model)
