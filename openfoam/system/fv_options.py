#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.cell_zone_db import CellZoneListIndex, CellZoneDB, ZoneType
from coredb.models_db import ModelsDB, TurbulenceModel
from openfoam.dictionary_file import DictionaryFile


class FvOptions(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(self.constantLocation(rname), 'fvOptions')

        self._rname = rname
        self._db = coredb.CoreDB()

    def build(self):
        if self._data is not None:
            return

        self._data = {}

        cellZones = self._db.getCellZones(self._rname)
        for c in cellZones:
            name = c[CellZoneListIndex.NAME.value]
            czid = c[CellZoneListIndex.ID.value]
            xpath = CellZoneDB.getXPath(czid)   # <name>All</name> 여기 상위까지 경로옴
            type_ = self._db.getValue(xpath + '/zoneType')
            # type_ = self._db.getVector(xpath + '/zoneType')
            model = ModelsDB.getTurbulenceModel()

            if type_ == ZoneType.POROUS.value:
                # self._data[name] = Porous(czid).buildDict()
                self._data[f'{name}_porous'] = self._constructPorous(name, xpath + '/porous')
            elif type_ == ZoneType.ACTUATOR_DISK.value:
                pass

            #mass
            #energy
            if model == TurbulenceModel.SPALART_ALLMARAS: #nutilda(modifiedTurbulentViscosity)
                pass
            elif model == TurbulenceModel.K_EPSILON: # k(turbulentKineticEnergy), epsilon(turbulentDissipationRate)
                pass
            elif model == TurbulenceModel.K_OMEGA: # k, omega(specificDissipationRate)
                pass

            #fixed

        return self

    def _constructPorous(self, name, xpath):
        if self._data is not None:
            return

        model = self._db.getValue(xpath + '/model')

        data = {
            'type': 'explicitPorositySource',
            'active': 'true',
            'explicitPorositySourceCoeffs': {
                'selectionMode': 'all/cellZone',
                # if not All
                'cellZone': name,
                'type': model,
                'active': 'yes',
            }
        }

        if model == PorousZoneModel.DARCY_FORCHHEIMER.value:
            data['DarcyForchheimerCoeffs'] = self._constructDarcyForchheimerCoeffs()
        else:
            data['powerLawCoeffs'] = self._constructPowerLawCoeffs()

        return data
