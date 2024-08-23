#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import QCoreApplication

import baramFlow.coredb.libdb as xml
from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import IMaterialObserver
from baramFlow.coredb.region_db import IRegionMaterialObserver, RegionDB, REGION_XPATH
from baramFlow.view.widgets.multi_selector_dialog import SelectorItem


BOUNDARY_CONDITION_XPATH = REGION_XPATH + '/boundaryConditions/boundaryCondition'


class BoundaryType(Enum):
    # Inlet
    VELOCITY_INLET	    = 'velocityInlet'
    FLOW_RATE_INLET	    = 'flowRateInlet'
    PRESSURE_INLET	    = 'pressureInlet'
    ABL_INLET	        = 'ablInlet'
    OPEN_CHANNEL_INLET  = 'openChannelInlet'
    FREE_STREAM	        = 'freeStream'
    FAR_FIELD_RIEMANN	= 'farFieldRiemann'
    SUBSONIC_INLET	    = 'subsonicInlet'
    SUPERSONIC_INFLOW	= 'supersonicInflow'
    # Outlet
    PRESSURE_OUTLET	    = 'pressureOutlet'
    OPEN_CHANNEL_OUTLET = 'openChannelOutlet'
    OUTFLOW	            = 'outflow'
    SUBSONIC_OUTFLOW	= 'subsonicOutflow'
    SUPERSONIC_OUTFLOW	= 'supersonicOutflow'
    # Wall
    WALL	            = 'wall'
    THERMO_COUPLED_WALL	= 'thermoCoupledWall'
    POROUS_JUMP	        = 'porousJump'
    FAN	                = 'fan'
    # Internal
    SYMMETRY	        = 'symmetry'
    INTERFACE	        = 'interface'
    EMPTY	            = 'empty'
    CYCLIC	            = 'cyclic'
    WEDGE	            = 'wedge'


class GeometricalType(Enum):
    PATCH       = 'patch'
    WALL        = 'wall'
    MAPPED_WALL = 'mappedWall'
    CYCLIC      = 'cyclic'
    CYCLIC_AMI  = 'cyclicAMI'
    SYMMETRY    = 'symmetry'
    EMPTY       = 'empty'
    WEDGE       = 'wedge'


class VelocitySpecification(Enum):
    COMPONENT = 'component'
    MAGNITUDE = 'magnitudeNormal'


class VelocityProfile(Enum):
    CONSTANT = 'constant'
    SPATIAL_DISTRIBUTION = 'spatialDistribution'
    TEMPORAL_DISTRIBUTION = 'temporalDistribution'


class FlowRateInletSpecification(Enum):
    VOLUME_FLOW_RATE = 'volumeFlowRate'
    MASS_FLOW_RATE = 'massFlowRate'


class WallVelocityCondition(Enum):
    NO_SLIP = 'noSlip'
    SLIP = 'slip'
    MOVING_WALL = 'movingWall'
    ATMOSPHERIC_WALL = 'atmosphericWall'
    TRANSLATIONAL_MOVING_WALL = 'translationalMovingWall'
    ROTATIONAL_MOVING_WALL = 'rotationalMovingWall'


class WallTemperature(Enum):
    ADIABATIC = 'adiabatic'
    CONSTANT_TEMPERATURE = 'constantTemperature'
    CONSTANT_HEAT_FLUX = 'constantHeatFlux'
    CONVECTION = 'convection'


class InterfaceMode(Enum):
    INTERNAL_INTERFACE = 'internalInterface'
    ROTATIONAL_PERIODIC = 'rotationalPeriodic'
    TRANSLATIONAL_PERIODIC = 'translationalPeriodic'
    REGION_INTERFACE = 'regionInterface'


class SpalartAllmarasSpecification(Enum):
    MODIFIED_TURBULENT_VISCOSITY = 'modifiedTurbulentViscosity'
    TURBULENT_VISCOSITY_RATIO = 'turbulentViscosityRatio'


class KEpsilonSpecification(Enum):
    K_AND_EPSILON = 'kAndEpsilon'
    INTENSITY_AND_VISCOSITY_RATIO = 'intensityAndViscosityRatio'


class KOmegaSpecification(Enum):
    K_AND_OMEGA = 'kAndOmega'
    INTENSITY_AND_VISCOSITY_RATIO = 'intensityAndViscosityRatio'


class TemperatureProfile(Enum):
    CONSTANT = 'constant'
    SPATIAL_DISTRIBUTION = 'spatialDistribution'
    TEMPORAL_DISTRIBUTION = 'temporalDistribution'


class TemperatureTemporalDistribution(Enum):
    PIECEWISE_LINEAR = 'piecewiseLinear'
    POLYNOMIAL = 'polynomial'


class ContactAngleModel(Enum):
    DISABLE = 'none'
    CONSTANT = 'constantContactAngle'
    DYNAMIC = 'dynamicContactAngle'


class ContactAngleLimit(Enum):
    NONE = 'none'
    GRADIENT = 'gradient'
    ZERO_GRADIENT = 'zeroGradient'
    ALPHA = 'alpha'


class DirectionSpecificationMethod(Enum):
    DIRECT = 'direct'
    AOA_AOS = 'AoA_AoS'


class BoundaryDB:
    BOUNDARY_CONDITIONS_XPATH = './/boundaryConditions'
    ABL_INLET_CONDITIONS_XPATH = './/atmosphericBoundaryLayer'

    _coupledBoundaryType = {
        BoundaryType.THERMO_COUPLED_WALL.value,
        BoundaryType.POROUS_JUMP.value,
        BoundaryType.FAN.value,
        BoundaryType.INTERFACE.value,
        BoundaryType.CYCLIC.value,
    }

    @classmethod
    def getXPath(cls, bcid):
        return f'{BOUNDARY_CONDITION_XPATH}[@bcid="{bcid}"]'

    @classmethod
    def getXPathByName(cls, rname, bcname):
        return f'{REGION_XPATH}[name="{rname}"]/boundaryConditions/boundaryCondition[name="{bcname}"]'

    @classmethod
    def getBoundaryName(cls, bcid):
        return coredb.CoreDB().getValue(cls.getXPath(bcid) + '/name')

    @classmethod
    def getBoundaryRegion(cls, bcid):
        return coredb.CoreDB().getValue(cls.getXPath(bcid) + '/../../name')

    @classmethod
    def getBoundaryText(cls, bcid):
        rname = cls.getBoundaryRegion(bcid)
        r = '' if rname == '' else rname + ':'
        return f'{r}{cls.getBoundaryName(bcid)}' if bcid else ''

    @classmethod
    def getBoundaryType(cls, bcid):
        return coredb.CoreDB().getValue(cls.getXPath(bcid) + '/physicalType')

    @classmethod
    def getBoundaryTypeByName(cls, rname, bcname):
        return coredb.CoreDB().getValue(
            f'.//region[name="{rname}"]/boundaryConditions/boundaryCondition[name="{bcname}"]/physicalType')

    @classmethod
    def needsCoupledBoundary(cls, bctype):
        return bctype in cls._coupledBoundaryType

    @classmethod
    def dbBoundaryTypeToText(cls, dbText):
        return {
            # Inlet
            BoundaryType.VELOCITY_INLET.value: QCoreApplication.translate('BoundaryDB', 'Velocity Inlet'),
            BoundaryType.FLOW_RATE_INLET.value: QCoreApplication.translate('BoundaryDB', 'Flow Rate Inlet'),
            BoundaryType.PRESSURE_INLET.value: QCoreApplication.translate('BoundaryDB', 'Pressure Inlet'),
            BoundaryType.ABL_INLET.value: QCoreApplication.translate('BoundaryDB', 'ABL Inlet'),
            BoundaryType.OPEN_CHANNEL_INLET.value: QCoreApplication.translate('BoundaryDB', 'Open Channel Inlet'),
            BoundaryType.FREE_STREAM.value: QCoreApplication.translate('BoundaryDB', 'Free Stream'),
            BoundaryType.FAR_FIELD_RIEMANN.value: QCoreApplication.translate('BoundaryDB', 'Far-Field Riemann'),
            BoundaryType.SUBSONIC_INLET.value: QCoreApplication.translate('BoundaryDB', 'Subsonic Inlet'),
            BoundaryType.SUPERSONIC_INFLOW.value: QCoreApplication.translate('BoundaryDB', 'Supersonic Inflow'),
            # Outlet
            BoundaryType.PRESSURE_OUTLET.value: QCoreApplication.translate('BoundaryDB', 'Pressure Outlet'),
            BoundaryType.OPEN_CHANNEL_OUTLET.value: QCoreApplication.translate('BoundaryDB', 'Open Channel Outlet'),
            BoundaryType.OUTFLOW.value: QCoreApplication.translate('BoundaryDB', 'Outflow'),
            BoundaryType.SUBSONIC_OUTFLOW.value: QCoreApplication.translate('BoundaryDB', 'Subsonic Outflow'),
            BoundaryType.SUPERSONIC_OUTFLOW.value: QCoreApplication.translate('BoundaryDB', 'Supersonic Outflow'),
            # Wall
            BoundaryType.WALL.value: QCoreApplication.translate('BoundaryDB', 'Wall'),
            BoundaryType.THERMO_COUPLED_WALL.value: QCoreApplication.translate('BoundaryDB', 'Thermo-Coupled Wall'),
            BoundaryType.POROUS_JUMP.value: QCoreApplication.translate('BoundaryDB', 'Porous Jump'),
            BoundaryType.FAN.value: QCoreApplication.translate('BoundaryDB', 'FAN'),
            # Internal
            BoundaryType.SYMMETRY.value: QCoreApplication.translate('BoundaryDB', 'Symmetry'),
            BoundaryType.INTERFACE.value: QCoreApplication.translate('BoundaryDB', 'Interface'),
            BoundaryType.EMPTY.value: QCoreApplication.translate('BoundaryDB', 'Empty'),
            BoundaryType.CYCLIC.value: QCoreApplication.translate('BoundaryDB', 'Cyclic'),
            BoundaryType.WEDGE.value: QCoreApplication.translate('BoundaryDB', 'Wedge'),
        }.get(dbText)

    @classmethod
    def getBoundarySelectorItems(cls):
        db = coredb.CoreDB()

        items = []
        for rname in db.getRegions():
            r = '' if rname == '' else rname + ':'
            for bcid, bcname, ptype in db.getBoundaryConditions(rname):
                items.append(SelectorItem(f'{r}{bcname}', bcname, str(bcid)))

        return items

    @classmethod
    def getBoundarySelectorItemsForCoupling(cls, coupleBcid, inRegion=True):
        db = coredb.CoreDB()

        items = []
        regions = [cls.getBoundaryRegion(coupleBcid)] if inRegion else db.getRegions()
        for rname in regions:
            r = '' if rname == '' or inRegion else rname + ':'
            for id_, bcname, ptype in db.getBoundaryConditions(rname):
                bcid = str(id_)
                if bcid != coupleBcid:
                    items.append(SelectorItem(f'{r}{bcname}', bcname, bcid))

        return items


def getBoundaryElements(rname):
    return coredb.CoreDB().getElements(f'{RegionDB.getXPath(rname)}/boundaryConditions/boundaryCondition')


class MaterialObserver(IMaterialObserver):
    def specieAdded(self, db, mid, mixtureID):
        for mixture in db.getElements(f'{BOUNDARY_CONDITION_XPATH}/species/mixture[mid="{mixtureID}"]'):
            mixture.append(xml.createElement('<specie xmlns="http://www.baramcfd.org/baram">'
                                             f' <mid>{mid}</mid><value>0</value>'
                                             '</specie>'))

    def materialRemoving(self, db, mid: int):
        for wallAdhesion in db.getElements(
                f'{BOUNDARY_CONDITION_XPATH}/wall/wallAdhesions/wallAdhesion[mid="{mid}"]'):
            wallAdhesion.getparent().remove(wallAdhesion)

        for volumeFraction in db.getElements(
                f'{BOUNDARY_CONDITION_XPATH}/volumeFractions/volumeFraction[material="{mid}"]'):
            volumeFraction.getparent().remove(volumeFraction)

    def specieRemoving(self, db, mid, primarySpecie):
        for boundaryCondition in db.getElements(BOUNDARY_CONDITION_XPATH):
            for specie in xml.getElements(boundaryCondition, f'species/mixture/specie[mid="{mid}"]'):
                self._removeSpecieInComposition(primarySpecie, specie)


class RegionMaterialObserver(IRegionMaterialObserver):
    def materialsUpdating(self, db, rname, primary, secondaries, species):
        def addWallAdhesion(parent, mid1, mid2):
            if xml.getElement(parent, f'wallAdhesion[mid="{mid1}"][mid="{mid2}"]') is None:
                parent.append(xml.createElement('<wallAdhesion xmlns="http://www.baramcfd.org/baram"> '
                                                f'  <mid>{mid1}</mid>'
                                                f'  <mid>{mid2}</mid>'
                                                '   <contactAngle>90</contactAngle>'
                                                '   <advancingContactAngle>90</advancingContactAngle>'
                                                '   <recedingContactAngle>90</recedingContactAngle>'
                                                '   <characteristicVelocityScale>0.001</characteristicVelocityScale>'
                                                '</wallAdhesion>'))

        speicesXML = f'''<mixture xmlns="http://www.baramcfd.org/baram">
                            <mid>{primary}</mid>{self._specieRatiosXML(species)}
                         </mixture>'''

        for boundaryCondtion in getBoundaryElements(rname):
            wallAdhesions = xml.getElement(boundaryCondtion, 'wall/wallAdhesions')
            volumeFractions = xml.getElement(boundaryCondtion, 'volumeFractions')
            # wallAdhesions.clear()
            # volumeFractions.clear()

            for i in range(len(secondaries)):
                addWallAdhesion(wallAdhesions, primary, secondaries[i])
                for j in range(i + 1, len(secondaries)):
                    addWallAdhesion(wallAdhesions, secondaries[i], secondaries[j])

                if xml.getElement(volumeFractions, f'volumeFraction[material="{secondaries[i]}"]') is None:
                    volumeFractions.append(xml.createElement('<volumeFraction xmlns="http://www.baramcfd.org/baram">'
                                                             f' <material>{secondaries[i]}</material>'
                                                             f' <fraction>0</fraction>'
                                                             '</volumeFraction>'))

            speciesElement = xml.getElement(boundaryCondtion, 'species')
            speciesElement.clear()
            if species:
                speciesElement.append(xml.createElement(speicesXML))
