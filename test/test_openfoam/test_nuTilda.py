import unittest

from coredb import coredb
from openfoam.boundary_conditions.nuTilda import NuTilda
from coredb.boundary_db import BoundaryDB
from coredb.models_db import ModelsDB
from coredb.region_db import RegionDB
from coredb.material_db import MaterialDB

dimensions = '[0 2 -1 0 0 0 0]'
region = "testRegion_1"
boundary = "testBoundary_1"


class TestNuTilda(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()
        self._db.addRegion(region)
        bcid = self._db.addBoundaryCondition(region, boundary, 'wall')
        self._xpath = BoundaryDB.getXPath(bcid)

        p = float(self._db.getValue('.//initialization/initialValues/pressure')) \
            + float(self._db.getValue('.//operatingConditions/pressure'))  # Pressure
        t = float(self._db.getValue('.//initialization/initialValues/temperature'))  # Temperature
        b = float(self._db.getValue('.//initialization/initialValues/turbulentViscosity'))  # Turbulent Viscosity

        mid = RegionDB.getMaterial(region)

        rho = MaterialDB.getDensity(mid, t, p)  # Density
        mu = MaterialDB.getViscosity(mid, t)  # Viscosity

        nu = mu / rho  # Kinetic Viscosity
        nut = b * nu

        self._initialValue = nut  # nut can be used for the INITIAL value of nuTilda

        self._db.setValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model', 'spalartAllmaras')

    def tearDown(self) -> None:
        coredb.destroy()

    # Velocity Inlet - modifiedTurbulentViscosity
    def testVelocityInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'velocityInlet')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual(dimensions, content['dimensions'])
        self.assertEqual(self._initialValue, content['internalField'][1])
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/spalartAllmaras/modifiedTurbulentViscosity'),
                         content['boundaryField'][boundary]['value'][1])

    # Flow Rate - turbulentViscosityRatio
    def testFlowRateInletVolume(self):
        self._db.setValue(self._xpath + '/turbulence/spalartAllmaras/specification', 'turbulentViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'flowRateInlet')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        # ToDo: Setting according to boundary field spec
        self.assertEqual('', content['boundaryField'][boundary]['type'])

    def testPressureInlet(self):
        self._db.setValue(self._xpath + '/turbulence/spalartAllmaras/specification', 'modifiedTurbulentViscosity')
        self._db.setValue(self._xpath + '/physicalType', 'pressureInlet')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/spalartAllmaras/modifiedTurbulentViscosity'),
                         content['boundaryField'][boundary]['value'][1])

    # Pressure Outlet - turbulentViscosityRatio
    def testPressureOutletBackflow(self):
        self._db.setValue(self._xpath + '/turbulence/spalartAllmaras/specification', 'turbulentViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'true')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        # ToDo: Setting according to boundary field spec
        self.assertEqual('', content['boundaryField'][boundary]['type'])

    # Pressure Outlet
    def testPressureOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'false')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testOpenChannelInlet(self):
        self._db.setValue(self._xpath + '/turbulence/spalartAllmaras/specification', 'modifiedTurbulentViscosity')
        self._db.setValue(self._xpath + '/physicalType', 'openChannelInlet')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/spalartAllmaras/modifiedTurbulentViscosity'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Open Channel Inlet - intensityAndViscosityRatio
    def testOpenChannelOutlet(self):
        self._db.setValue(self._xpath + '/turbulence/spalartAllmaras/specification', 'turbulentViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'openChannelOutlet')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        # ToDo: Setting according to boundary field spec
        self.assertEqual('', content['boundaryField'][boundary]['type'])

    def testOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'outflow')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testFreeStream(self):
        self._db.setValue(self._xpath + '/physicalType', 'freeStream')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('freestream', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getVector(self._xpath + '/freeStream/streamVelocity'),
                         content['boundaryField'][boundary]['freestreamValue'][1])

    def testFarFieldRiemann(self):
        self._db.setValue(self._xpath + '/turbulence/spalartAllmaras/specification', 'modifiedTurbulentViscosity')
        self._db.setValue(self._xpath + '/physicalType', 'farFieldRiemann')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/spalartAllmaras/modifiedTurbulentViscosity'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSubsonicInflow(self):
        self._db.setValue(self._xpath + '/turbulence/spalartAllmaras/specification', 'turbulentViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'subsonicInflow')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        # ToDo: Setting according to boundary field spec
        self.assertEqual('', content['boundaryField'][boundary]['type'])

    def testSubsonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'subsonicOutflow')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testSupersonicInflow(self):
        self._db.setValue(self._xpath + '/turbulence/spalartAllmaras/specification', 'modifiedTurbulentViscosity')
        self._db.setValue(self._xpath + '/physicalType', 'supersonicInflow')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/spalartAllmaras/modifiedTurbulentViscosity'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSupersonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicOutflow')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testThermoCoupledWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'thermoCoupledWall')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testSymmetry(self):
        self._db.setValue(self._xpath + '/physicalType', 'symmetry')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('symmetry', content['boundaryField'][boundary]['type'])

    # Interface
    def testInternalInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'internalInterface')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRotationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'rotationalPeriodic')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testTranslationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'translationalPeriodic')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRegionInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'regionInterface')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testPorousJump(self):
        self._db.setValue(self._xpath + '/physicalType', 'porousJump')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testFan(self):
        self._db.setValue(self._xpath + '/physicalType', 'fan')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testEmpty(self):
        self._db.setValue(self._xpath + '/physicalType', 'empty')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('empty', content['boundaryField'][boundary]['type'])

    def testCyclic(self):
        self._db.setValue(self._xpath + '/physicalType', 'cyclic')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testWedge(self):
        self._db.setValue(self._xpath + '/physicalType', 'wedge')
        content = NuTilda(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('wedge', content['boundaryField'][boundary]['type'])


if __name__ == '__main__':
    unittest.main()
