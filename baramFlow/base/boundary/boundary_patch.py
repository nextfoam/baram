#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from libbaram.pfloat import PFloat

from baramFlow.base.boundary.ABL_inlet import AtmosphericBoundaryLayer
from baramFlow.base.boundary.boundary import UserDefinedScalarValue, SpecieValue, updateUserDefinedScalarsInDB
from baramFlow.base.boundary.boundary import updateSpeciesInDB
from baramFlow.base.boundary.fan import Fan
from baramFlow.base.boundary.free_stream import FarFieldRiemann
from baramFlow.base.boundary.flow_rate_port import BoundaryFlowRate
from baramFlow.base.boundary.free_stream import FreeStream
from baramFlow.base.boundary.open_channel_port import OpenChannelOutlet, OpenChannelInlet
from baramFlow.base.boundary.pressure_port import PressureOutlet, PressureInlet
from baramFlow.base.boundary.subsonic_inle import SubsonicInlet
from baramFlow.base.boundary.supersonic_inflow import SupersonicInflow
from baramFlow.base.boundary.temperature import BoundaryTemperature
from baramFlow.base.boundary.turbulence import BoundaryTurbulencePatch
from baramFlow.base.boundary.velocity_inlet import VelocityInlet
from baramFlow.base.file_data_manager import TableDataForFileDB
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.coredb import _CoreDB
from baramFlow.coredb.libdb import nsmap


@dataclass
class VelocityInletPatch:
    velocityInet: VelocityInlet = None

    turbulence: BoundaryTurbulencePatch  = None
    temperature: BoundaryTemperature = None

    userDefinedScalars: list[UserDefinedScalarValue] = None
    species: list[SpecieValue] = None

    def applyToDB(self, db, bcid):
        self.velocityInet.applyToDB(db, bcid)

        if self.turbulence is not None:
            self.turbulence.applyToDB(db, bcid)

        if self.temperature is not None:
            self.temperature.applyToDB(db, bcid)

        updateUserDefinedScalarsInDB(db, bcid, self.userDefinedScalars)
        updateSpeciesInDB(db, bcid, self.species)



@dataclass
class FlowRateInletPatch:
    flowRate: BoundaryFlowRate

    turbulence: BoundaryTurbulencePatch = None

    def applyToDB(self, db: _CoreDB, bcid: str):
        self.flowRate.applyToDBByPath(db, BoundaryDB.getXPath(bcid) + '/flowRateInlet')

        if self.turbulence is not None:
            self.turbulence.applyToDB(db, bcid)


@dataclass
class FlowRateOutletPatch:
    flowRate: BoundaryFlowRate

    def applyToDB(self, db: _CoreDB, bcid: str):
        self.flowRate.applyToDBByPath(db, BoundaryDB.getXPath(bcid) + '/flowRateOutlet')


@dataclass
class PressureInletPatch:
    pressureInlet: PressureInlet

    turbulence: BoundaryTurbulencePatch = None

    def applyToDB(self, db: _CoreDB, bcid: str):
        self.pressureInlet.applyToDB(db, bcid)

        if self.turbulence is not None:
            self.turbulence.applyToDB(db, bcid)


@dataclass
class PressureOutletPatch:
    pressureOutlet: PressureOutlet

    turbulence: BoundaryTurbulencePatch = None

    def applyToDB(self, db: _CoreDB, bcid: str):
        element = db.getElement(BoundaryDB.getXPath(bcid))
        element.replace(element.find('pressureOutlet', namespaces=nsmap), self.pressureOutlet.toElement())

        if self.turbulence is not None:
            self.turbulence.applyToDB(db, bcid)
#
#
# @dataclass
# class PressureOutletPatch:


@dataclass(kw_only=True)
class IntakeFanPatch:
    turbulence: BoundaryTurbulencePatch = None
    pressure: PFloat
    fanCurve: TableDataForFileDB        = None

    def applyToDB(self, db: _CoreDB, bcid: str):
        if self.turbulence is not None:
            self.turbulence.applyToDB(db, bcid)

        db.setValue(BoundaryDB.getXPath(bcid) + '/pressure', str(self.pressure))

        if self.fanCurve is not None:
            self.fanCurve.applyToDB(db, bcid)



@dataclass
class OpenChannelInletPatch:
    openChannelInlet: OpenChannelInlet

    turbulence: BoundaryTurbulencePatch = None

    def applyToDB(self, db: _CoreDB, bcid: str):
        self.openChannelInlet.applyToDB(db, bcid)

        if self.turbulence is not None:
            self.turbulence.applyToDB(db, bcid)


@dataclass
class OpenChannelOutletPatch:
    openChannelOutlet: OpenChannelOutlet

    turbulence: BoundaryTurbulencePatch = None

    def applyToDB(self, db: _CoreDB, bcid: str):
        self.openChannelOutlet.applyToDB(db, bcid)

        if self.turbulence is not None:
            self.turbulence.applyToDB(db, bcid)


@dataclass
class FreeStreamPatch:
    freeStream: FreeStream

    turbulence: BoundaryTurbulencePatch = None

    def applyToDB(self, db: _CoreDB, bcid: str):
        self.freeStream.applyToDB(db, bcid)

        if self.turbulence is not None:
            self.turbulence.applyToDB(db, bcid)


@dataclass
class FarFieldRiemannPatch:
    farFieldRiemann: FarFieldRiemann

    turbulence: BoundaryTurbulencePatch = None

    def applyToDB(self, db: _CoreDB, bcid: str):
        self.farFieldRiemann.applyToDB(db, bcid)

        if self.turbulence is not None:
            self.turbulence.applyToDB(db, bcid)


@dataclass
class SubsonicInletPatch:
    subsonicInlet: SubsonicInlet

    turbulence: BoundaryTurbulencePatch = None

    def applyToDB(self, db: _CoreDB, bcid: str):
        element = db.getElement(BoundaryDB.getXPath(bcid))
        element.replace(element.find('subsonicInlet', namespaces=nsmap), self.subsonicInlet.toElement())

        if self.turbulence is not None:
            self.turbulence.applyToDB(db, bcid)
#
#
# @dataclass
# class SubsonicOutflowPatch:


@dataclass
class SupersonicInflowPatch:
    supersonicInflow: SupersonicInflow

    turbulence: BoundaryTurbulencePatch = None

    def applyToDB(self, db: _CoreDB, bcid: str):
        element = db.getElement(BoundaryDB.getXPath(bcid))
        element.replace(element.find('supersonicInflow', namespaces=nsmap), self.supersonicInflow.toElement())

        if self.turbulence is not None:
            self.turbulence.applyToDB(db, bcid)
#
#
# @dataclass
# class WallPatch:
#
#
# @dataclass
# class ThermoCoupledWallPatch:
#
#
# @dataclass
# class InterfacePatch:
#
#
# @dataclass
# class PorousJumpPatch:


@dataclass
class FanPatch:
    fan: Fan    = None
    coupledBoundary: str = None

    def applyToDB(self, db, bcid):
        self.fan.applyToDB(db, bcid)
        self.fan.applyCoupleConditionToDB(db, self.coupledBoundary)

        db.setValue(BoundaryDB.getXPath(bcid) + '/coupledBoundary', self.coupledBoundary)


@dataclass
class ABLInletPatch:
    abl: AtmosphericBoundaryLayer = None

    userDefinedScalars: list[UserDefinedScalarValue] = None
    species: list[SpecieValue] = None

    def applyToDB(self, db, bcid):
        self.abl.applyToDB(db)

        updateUserDefinedScalarsInDB(db, bcid, self.userDefinedScalars)
        updateSpeciesInDB(db, bcid, self.species)
