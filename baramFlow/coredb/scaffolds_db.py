#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import Field, dataclass
from enum import Enum, auto
from os import name
from threading import Lock
from uuid import UUID, uuid4

from PySide6.QtCore import QCoreApplication
import qasync

from baramFlow.coredb import coredb
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.iso_surface import IsoSurface
from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import MaterialType, Phase
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.post_field import BasicField, CollateralField, PhaseField, SpecieField
from baramFlow.coredb.scaffold import Scaffold
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver import usePrgh
from baramFlow.solver_status import SolverStatus


ISO_SURFACE_NAME_PREFIX = 'iso-surface'


_mutex = Lock()



# def buildFieldTimeMapFromModel() -> list[Field]:
#     fields = []

#     # Always available fields
#     p_rgh = True
#     try:
#         p_rgh = usePrgh()
#     except RuntimeError:
#         pass

#     if p_rgh:
#         fields.append(BasicField('p_rgh', 'p_rgh', QCoreApplication.translate('PostField', 'Pressure')))
#     else:
#         fields.append(BasicField('p',     'p',     QCoreApplication.translate('PostField', 'Pressure')))

#     fields.append(BasicField('speed', 'U', QCoreApplication.translate('PostField', 'Speed')))
#     fields.append(BasicField('Ux',    'U', QCoreApplication.translate('PostField', 'X-Velocity')))
#     fields.append(BasicField('Uy',    'U', QCoreApplication.translate('PostField', 'Y-Velocity')))
#     fields.append(BasicField('Uz',    'U', QCoreApplication.translate('PostField', 'Z-Velocity')))

#     fields.append(CollateralField('Q',    'Q', QCoreApplication.translate('PostField', 'Q')))
#     fields.append(CollateralField('totalPressure',    'totalPressure', QCoreApplication.translate('PostField', 'Total Pressure')))
#     fields.append(CollateralField('vorticity',    'vorticity', QCoreApplication.translate('PostField', 'Vorticity')))
#     fields.append(CollateralField('wallHeatFlux',    'wallHeatFlux', QCoreApplication.translate('PostField', 'Wall Heat Flux')))
#     fields.append(CollateralField('wallShearStress',    'wallShearStress', QCoreApplication.translate('PostField', 'Wall Shear Stress')))
#     fields.append(CollateralField('wallYPlus',    'wallYPlus', QCoreApplication.translate('PostField', 'Wall Y plus')))

#     if not GeneralDB.isTimeTransient() and not GeneralDB.isDensityBased():
#         fields.append(CollateralField('age', 'age', QCoreApplication.translate('PostField', 'Age')))

#     # Fields depending on the turbulence model
#     turbulenceModel = TurbulenceModelsDB.getModel()
#     if turbulenceModel == TurbulenceModel.K_EPSILON:
#         fields.append(BasicField('k',       'k',       QCoreApplication.translate('PostField', 'Turbulent Kinetic Energy')))
#         fields.append(BasicField('epsilon', 'epsilon', QCoreApplication.translate('PostField', 'Turbulent Dissipation Rate')))
#     elif turbulenceModel == TurbulenceModel.K_OMEGA:
#         fields.append(BasicField('k',       'k',       QCoreApplication.translate('PostField', 'Turbulent Kinetic Energy')))
#         fields.append(BasicField('omega',   'omega',   QCoreApplication.translate('PostField', 'Specific Dissipation Rate')))
#     elif turbulenceModel == TurbulenceModel.SPALART_ALLMARAS:
#         fields.append(BasicField('nuTilda', 'nuTilda', QCoreApplication.translate('PostField', 'Modified Turbulent Viscosity')))

#     # Fields depending on the energy model
#     energyOn = ModelsDB.isEnergyModelOn()
#     if energyOn:
#         fields.append(BasicField('T',   QCoreApplication.translate('PostField', 'Temperature')))
#         fields.append(BasicField('rho', QCoreApplication.translate('PostField', 'Density')))
#         fields.append(CollateralField('heatTransferCoeff', 'heatTransferCoeff(T)', QCoreApplication.translate('PostField', 'Age')))
#         if not GeneralDB.isDensityBased():
#             fields.append(CollateralField('machNumber', 'machNumber', QCoreApplication.translate('PostField', 'Mach Number')))

#     # Material fields on multiphase model
#     if ModelsDB.isMultiphaseModelOn():
#         for _, name, _, phase in MaterialDB.getMaterials():
#             if phase != Phase.SOLID.value:
#                 fields.append(PhaseField(name, 'alpha.'+name, name))

#     elif ModelsDB.isSpeciesModelOn():
#         for mid, _, _, _ in MaterialDB.getMaterials(MaterialType.MIXTURE.value):
#             for _, name in MaterialDB.getSpecies(mid).items():
#                 fields.append(SpecieField(name, name, name))

#     for _, name in coredb.CoreDB().getUserDefinedScalars():
#         fields.append(SpecieField(name, name, name))

#     return fields


class ScaffoldsDB():
    SCAFFOLD_PATH = '/scaffolds'
    def __new__(cls, *args, **kwargs):
        with _mutex:
            if not hasattr(cls, '_instance'):
                cls._instance = super(ScaffoldsDB, cls).__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self):
        with _mutex:
            if hasattr(self, '_initialized'):
                return
            else:
                self._initialized = True

        super().__init__()

        self._fieldMap: list[Field] = {}

        self._scaffolds: dict[UUID, Scaffold] = {}


    def load(self):
        self._scaffolds = self._parseScaffolds()

    def _updateCoreDB(self):
        element = coredb.CoreDB().getElement(self.SCAFFOLD_PATH)

        isoSurfaces = element.find('isoSurface', namespaces=nsmap)
        isoSurfaces.clear()

        for v in self._scaffolds.values():
            if isinstance(v, IsoSurface):
                isoSurfaces.append(v.toElement())

    def _parseScaffolds(self) -> dict[UUID, Scaffold]:
        scaffolds = {}
        element = coredb.CoreDB().getElement(self.SCAFFOLD_PATH)

        isoSurfaces = element.find('isoSurfaces', namespaces=nsmap)
        for e in isoSurfaces.findall('surface', namespaces=nsmap):
            s = IsoSurface.fromElement(e)
            scaffolds[s.uuid] = s

        return scaffolds

    def getScaffolds(self):
        return self._scaffolds

    def addScaffold(self, scaffold: Scaffold):
        if scaffold.uuid in self._scaffolds:
            raise AssertionError

        if isinstance(scaffold, IsoSurface):
            tag = 'isoSurfaces'
        else:
            raise AssertionError

        element = coredb.CoreDB().getElement(self.SCAFFOLD_PATH)
        parent = element.find(tag, namespaces=nsmap)

        e = scaffold.toElement()
        parent.append(e)

        self._scaffolds[scaffold.uuid] = scaffold

    def removeScaffold(self, scaffold: Scaffold):
        if scaffold.uuid not in self._scaffolds:
            raise AssertionError

        if isinstance(scaffold, IsoSurface):
            tag = 'isoSurfaces'
        else:
            raise AssertionError

        element = coredb.CoreDB().getElement(self.SCAFFOLD_PATH)
        parent = element.find(tag, namespaces=nsmap)

        e = parent.find(f'./surface[uuid="{str(scaffold.uuid)}"]', namespaces=nsmap)
        parent.remove(e)

        del self._scaffolds[scaffold.uuid]

    def updateScaffold(self, scaffold: Scaffold):
        if scaffold.uuid not in self._scaffolds:
            raise AssertionError

        if isinstance(scaffold, IsoSurface):
            tag = 'isoSurfaces'
        else:
            raise AssertionError

        element = coredb.CoreDB().getElement(self.SCAFFOLD_PATH)
        parent = element.find(tag, namespaces=nsmap)

        e = parent.find(f'./surface[uuid="{str(scaffold.uuid)}"]', namespaces=nsmap)
        parent.remove(e)

        e = scaffold.toElement()
        parent.append(e)

    def getFieldMap(self) -> list[Field]:
        return self._fieldMap

    def nameDuplicates(self, uuid: UUID, name: str) -> bool:
        for v in self._scaffolds.values():
            if v.name == name and v.uuid != uuid:
                return True

        return False

    def getNewIsoSurfaceName(self) -> str:
        return self._getNewScaffoldName(ISO_SURFACE_NAME_PREFIX)

    def _getNewScaffoldName(self, prefix: str) -> str:
        suffixes = [v.name[len(prefix):] for v in self._scaffolds.values() if v.name.startswith(prefix)]
        for i in range(1, 1000):
            if f'-{i}' not in suffixes:
                return f'{prefix}-{i}'
        return f'{prefix}-{uuid4()}'

    # def _buildAvailableFieldTimeMap(self):
    #     fieldMap = buildFieldTimeMapFromModel()
    #     fieldMapFiles = self._buildFieldTimeMapFromFiles()
    #     for field in fieldMap:
    #         if field.fileName in fieldMapFiles:
    #             field.times = fieldMapFiles[field.fileName]

    #     self._fieldMap = fieldMap

    # def _buildFieldTimeMapFromFiles(self) -> dict[str, list[str]]:
    #     fieldTimeMap: dict[str, list[str]] = {}
    #     for time, fields in FileSystem.fieldsInTimeFolders().items():
    #         for f in fields:
    #             if f not in fieldTimeMap:
    #                 fieldTimeMap[f] = []

    #             fieldTimeMap[f].append(time)

    #     return fieldTimeMap


