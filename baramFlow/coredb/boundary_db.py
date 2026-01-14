#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import QCoreApplication

import baramFlow.coredb.libdb as xml
from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import IMaterialObserver
from baramFlow.coredb.region_db import IRegionMaterialObserver, RegionDB, REGION_XPATH
from baramFlow.coredb.scalar_model_db import IUserDefinedScalarObserver
from baramFlow.view.widgets.multi_selector_dialog import SelectorItem


BOUNDARY_CONDITION_XPATH = REGION_XPATH + '/boundaryConditions/boundaryCondition'


class BoundaryType(Enum):
    # Inlet
    VELOCITY_INLET	    = 'velocityInlet'
    FLOW_RATE_INLET	    = 'flowRateInlet'
    PRESSURE_INLET	    = 'pressureInlet'
    INTAKE_FAN          = 'intakeFan'
    ABL_INLET	        = 'ablInlet'
    OPEN_CHANNEL_INLET  = 'openChannelInlet'
    FREE_STREAM	        = 'freeStream'
    FAR_FIELD_RIEMANN	= 'farFieldRiemann'
    SUBSONIC_INLET	    = 'subsonicInlet'
    SUPERSONIC_INFLOW	= 'supersonicInflow'
    # Outlet
    FLOW_RATE_OUTLET    = 'flowRateOutlet'
    PRESSURE_OUTLET	    = 'pressureOutlet'
    EXHAUST_FAN         = 'exhaustFan'
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


TYPE_MAP = {
    BoundaryType.VELOCITY_INLET       : GeometricalType.PATCH,
    BoundaryType.FLOW_RATE_INLET      : GeometricalType.PATCH,
    BoundaryType.PRESSURE_INLET       : GeometricalType.PATCH,
    BoundaryType.INTAKE_FAN           : GeometricalType.PATCH,
    BoundaryType.ABL_INLET            : GeometricalType.PATCH,
    BoundaryType.OPEN_CHANNEL_INLET   : GeometricalType.PATCH,
    BoundaryType.FREE_STREAM          : GeometricalType.PATCH,
    BoundaryType.FAR_FIELD_RIEMANN    : GeometricalType.PATCH,
    BoundaryType.SUBSONIC_INLET       : GeometricalType.PATCH,
    BoundaryType.SUPERSONIC_INFLOW    : GeometricalType.PATCH,
    BoundaryType.FLOW_RATE_OUTLET     : GeometricalType.PATCH,
    BoundaryType.PRESSURE_OUTLET      : GeometricalType.PATCH,
    BoundaryType.EXHAUST_FAN          : GeometricalType.PATCH,
    BoundaryType.OPEN_CHANNEL_OUTLET  : GeometricalType.PATCH,
    BoundaryType.OUTFLOW              : GeometricalType.PATCH,
    BoundaryType.SUBSONIC_OUTFLOW     : GeometricalType.PATCH,
    BoundaryType.SUPERSONIC_OUTFLOW   : GeometricalType.PATCH,
    BoundaryType.WALL                 : GeometricalType.WALL,
    BoundaryType.THERMO_COUPLED_WALL  : GeometricalType.MAPPED_WALL,
    BoundaryType.POROUS_JUMP          : GeometricalType.CYCLIC,
    BoundaryType.FAN                  : GeometricalType.CYCLIC,
    BoundaryType.SYMMETRY             : GeometricalType.SYMMETRY,
    BoundaryType.INTERFACE            : GeometricalType.CYCLIC_AMI,
    BoundaryType.EMPTY                : GeometricalType.EMPTY,
    BoundaryType.CYCLIC               : GeometricalType.CYCLIC,
    BoundaryType.WEDGE                : GeometricalType.WEDGE,
}


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


class WallMotion(Enum):
    STATIONARY_WALL = 'stationaryWall'
    MOVING_WALL = 'movingWall'


class MovingWallMotion(Enum):
    TRANSLATIONAL_MOTION = 'translationalMotion'
    ROTATIONAL_MOTION = 'rotationalMotion'
    MESH_MOTION = 'meshMotion'


class ShearCondition(Enum):
    NO_SLIP = 'noSlip'
    SLIP = 'slip'


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


class FlowDirectionSpecificationMethod(Enum):
    DIRECT = 'direct'
    SURFACE_NORMAL = 'surfaceNormal'


DirectionSpecificationMethodTexts = {
    DirectionSpecificationMethod.DIRECT:    QCoreApplication.translate('BoundaryDB', 'Direct'),
    DirectionSpecificationMethod.AOA_AOS:   QCoreApplication.translate('BoundaryDB', 'AOA and AOS')
}


class BoundaryDB:
    BOUNDARY_CONDITIONS_XPATH = '/regions/region/boundaryConditions'
    ABL_INLET_CONDITIONS_XPATH = '/general/atmosphericBoundaryLayer'

    _coupledBoundaryType = {
        BoundaryType.THERMO_COUPLED_WALL,
        BoundaryType.POROUS_JUMP,
        BoundaryType.FAN,
        BoundaryType.INTERFACE,
        BoundaryType.CYCLIC,
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
    def getGeometryType(cls, bctype: BoundaryType)->GeometricalType:
        return TYPE_MAP.get(bctype, GeometricalType.WALL)

    @classmethod
    def getBoundaryType(cls, bcid)->BoundaryType:
        return BoundaryType(coredb.CoreDB().getValue(cls.getXPath(bcid) + '/physicalType'))

    @classmethod
    def getBoundaryTypeByName(cls, rname, bcname):
        return coredb.CoreDB().getValue(
            f'/regions/region[name="{rname}"]/boundaryConditions/boundaryCondition[name="{bcname}"]/physicalType')

    @classmethod
    def needsCoupledBoundary(cls, bctype: BoundaryType):
        return bctype in cls._coupledBoundaryType

    @classmethod
    def getCoupledBoundary(cls, bcid: str):
        return coredb.CoreDB().getValue(cls.getXPath(bcid) + '/coupledBoundary')

    @classmethod
    def cyclingBoundaries(cls, rname: str)->list[tuple[str, str]]:
        boundaries: dict[str, tuple[str, str]] = {}
        db = coredb.CoreDB()
        for bcid, bcname, ptype in db.getBoundaryConditions(rname):
            if str(bcid) in boundaries:
                continue

            if BoundaryType(ptype) in [BoundaryType.POROUS_JUMP, BoundaryType.FAN, BoundaryType.INTERFACE, BoundaryType.CYCLIC]:
                cpid = cls.getCoupledBoundary(str(bcid))
                if cpid == '0':
                    continue

                cpname = cls.getBoundaryName(cpid)
                boundaries[cpid] = (bcname, cpname)

        return list(boundaries.values())

    @classmethod
    def dbBoundaryTypeToText(cls, bctype:BoundaryType):
        return {
            # Inlet
            BoundaryType.VELOCITY_INLET:     QCoreApplication.translate('BoundaryDB', 'Velocity Inlet'),
            BoundaryType.FLOW_RATE_INLET:    QCoreApplication.translate('BoundaryDB', 'Flow Rate Inlet'),
            BoundaryType.PRESSURE_INLET:     QCoreApplication.translate('BoundaryDB', 'Pressure Inlet'),
            BoundaryType.INTAKE_FAN:         QCoreApplication.translate('BoundaryDB', 'Intake Fan'),
            BoundaryType.ABL_INLET:          QCoreApplication.translate('BoundaryDB', 'ABL Inlet'),
            BoundaryType.OPEN_CHANNEL_INLET: QCoreApplication.translate('BoundaryDB', 'Open Channel Inlet'),
            BoundaryType.FREE_STREAM:        QCoreApplication.translate('BoundaryDB', 'Free Stream'),
            BoundaryType.FAR_FIELD_RIEMANN:  QCoreApplication.translate('BoundaryDB', 'Far-Field Riemann'),
            BoundaryType.SUBSONIC_INLET:     QCoreApplication.translate('BoundaryDB', 'Subsonic Inlet'),
            BoundaryType.SUPERSONIC_INFLOW:  QCoreApplication.translate('BoundaryDB', 'Supersonic Inflow'),
            # Outlet
            BoundaryType.FLOW_RATE_OUTLET:    QCoreApplication.translate('BoundaryDB', 'Flow Rate Outlet'),
            BoundaryType.PRESSURE_OUTLET:     QCoreApplication.translate('BoundaryDB', 'Pressure Outlet'),
            BoundaryType.EXHAUST_FAN:         QCoreApplication.translate('BoundaryDB', 'Exhaust Fan'),
            BoundaryType.OPEN_CHANNEL_OUTLET: QCoreApplication.translate('BoundaryDB', 'Open Channel Outlet'),
            BoundaryType.OUTFLOW:             QCoreApplication.translate('BoundaryDB', 'Outflow'),
            BoundaryType.SUBSONIC_OUTFLOW:    QCoreApplication.translate('BoundaryDB', 'Subsonic Outflow'),
            BoundaryType.SUPERSONIC_OUTFLOW:  QCoreApplication.translate('BoundaryDB', 'Supersonic Outflow'),
            # Wall
            BoundaryType.WALL:                QCoreApplication.translate('BoundaryDB', 'Wall'),
            BoundaryType.THERMO_COUPLED_WALL: QCoreApplication.translate('BoundaryDB', 'Thermo-Coupled Wall'),
            BoundaryType.POROUS_JUMP:         QCoreApplication.translate('BoundaryDB', 'Porous Jump'),
            BoundaryType.FAN:                 QCoreApplication.translate('BoundaryDB', 'FAN'),
            # Internal
            BoundaryType.SYMMETRY:  QCoreApplication.translate('BoundaryDB', 'Symmetry'),
            BoundaryType.INTERFACE: QCoreApplication.translate('BoundaryDB', 'Interface'),
            BoundaryType.EMPTY:     QCoreApplication.translate('BoundaryDB', 'Empty'),
            BoundaryType.CYCLIC:    QCoreApplication.translate('BoundaryDB', 'Cyclic'),
            BoundaryType.WEDGE:     QCoreApplication.translate('BoundaryDB', 'Wedge'),
        }.get(bctype, 'Unknown Type')

    @classmethod
    def getBoundarySelectorItems(cls, types=None) -> list[SelectorItem]:
        db = coredb.CoreDB()

        items = []
        for rname in db.getRegions():
            r = '' if rname == '' else rname + ':'
            for bcid, bcname, ptype in db.getBoundaryConditions(rname):
                if types is None or BoundaryType(ptype) in types:
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

    @classmethod
    def getBoundaryConditionsByType(cls, physicalType: BoundaryType, rname=None) -> list[tuple[int, str]]:
        """Returns list of boundary conditions in the region

        Returns list of boundary conditions for the type

        Args:
            physicalType: physical type
            rname: region name, None or '' for all regions

        Returns:
            List of boundary conditions in tuple, '(bcid, name)'
        """
        regionXPath = RegionDB.getXPath(rname) if rname else REGION_XPATH

        return [
            # (int(e.attrib['bcid']), e.find('name', namespaces=nsmap).text)
            (int(e.attrib['bcid']), xml.getText(e, 'name'))
            for e
            in coredb.CoreDB().getElements(
                f'{regionXPath}/boundaryConditions/boundaryCondition[physicalType="{physicalType.value}"]')]


def getBoundaryElements(rname):
    return coredb.CoreDB().getElements(f'{RegionDB.getXPath(rname)}/boundaryConditions/boundaryCondition')


class MaterialObserver(IMaterialObserver):
    def materialRemoving(self, db, mid: str):
        for wallAdhesion in db.getElements(
                f'{BOUNDARY_CONDITION_XPATH}/wall/wallAdhesions/wallAdhesion[mid="{mid}"]'):
            wallAdhesion.getparent().remove(wallAdhesion)

        for volumeFraction in db.getElements(
                f'{BOUNDARY_CONDITION_XPATH}/volumeFractions/volumeFraction[material="{mid}"]'):
            volumeFraction.getparent().remove(volumeFraction)

    def specieAdded(self, db, mid: str, mixtureID: str):
        for mixture in db.getElements(f'{BOUNDARY_CONDITION_XPATH}/species/mixture[mid="{mixtureID}"]'):
            mixture.append(xml.createElement('<specie xmlns="http://www.baramcfd.org/baram">'
                                             f' <mid>{mid}</mid><value>0</value>'
                                             '</specie>'))

    def specieRemoving(self, db, mid: str, primarySpecie):
        for boundaryCondition in db.getElements(BOUNDARY_CONDITION_XPATH):
            for specie in xml.getElements(boundaryCondition, f'species/mixture/specie[mid="{mid}"]'):
                self._removeSpecieInComposition(primarySpecie, specie)


class RegionMaterialObserver(IRegionMaterialObserver):
    def materialsUpdating(self, db, rname: str, primary: str, secondaries: list[str], species):
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


class ScalarObserver(IUserDefinedScalarObserver):
    def scalarAdded(self, db, scalarID):
        scalarXML = f'''<scalar xmlns="http://www.baramcfd.org/baram">
                            <scalarID>{scalarID}</scalarID>
                            <value>0</value>
                        </scalar>'''

        for scalars in db.getElements(BOUNDARY_CONDITION_XPATH + '/userDefinedScalars'):
            scalars.append(xml.createElement(scalarXML))

    def scalarRemoving(self, db, scalarID):
        for scalars in db.getElements(BOUNDARY_CONDITION_XPATH + '/userDefinedScalars'):
            xml.removeElement(scalars, f'scalar[scalarID="{scalarID}"]')
