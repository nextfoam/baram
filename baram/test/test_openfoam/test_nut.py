import unittest

from baram.coredb import coredb
from baram.openfoam.boundary_conditions.nut import Nut
from baram.coredb.boundary_db import BoundaryDB
from baram.coredb.models_db import ModelsDB
from baram.coredb.region_db import RegionDB
from baram.coredb.material_db import MaterialDB

dimensions = '[0 2 -1 0 0 0 0]'
rname = "testRegion_1"
boundary = "testBoundary_1"


class TestNut(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()
        self._db.setValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model', 'k-epsilon')
        self._db.addRegion(rname)
        bcid = self._db.addBoundaryCondition(rname, boundary, 'wall')
        self._xpath = BoundaryDB.getXPath(bcid)

        p = float(self._db.getValue('.//initialization/initialValues/pressure')) \
            + float(self._db.getValue('.//operatingConditions/pressure'))  # Pressure
        t = float(self._db.getValue('.//initialization/initialValues/temperature'))  # Temperature
        b = float(self._db.getValue('.//initialization/initialValues/turbulentViscosity'))  # Turbulent Viscosity

        mid = RegionDB.getMaterial(rname)

        rho = MaterialDB.getDensity(mid, t, p)  # Density
        mu = MaterialDB.getViscosity(mid, t)  # Viscosity

        nu = mu / rho  # Kinetic Viscosity
        nut = b * nu

        self._initialValue = nut

        self._db.setValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model', 'k-epsilon')

    def tearDown(self) -> None:
        coredb.destroy()

    def testVelocityInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'velocityInlet')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual(dimensions, content['dimensions'])
        self.assertEqual(self._initialValue, content['internalField'][1])
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testFlowRateInletVolume(self):
        self._db.setValue(self._xpath + '/physicalType', 'flowRateInlet')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testPressureInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureInlet')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Pressure Outlet
    def testPressureOutletBackflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'true')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Pressure Outlet
    def testPressureOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'false')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testAblInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'ablInlet')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testOpenChannelInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'openChannelInlet')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testOpenChannelOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'openChannelOutlet')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'outflow')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testFreeStreamKAndNut(self):
        self._db.setValue(self._xpath + '/physicalType', 'freeStream')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testFarFieldRiemann(self):
        self._db.setValue(self._xpath + '/physicalType', 'farFieldRiemann')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSubsonicInflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'subsonicInflow')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSubsonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'subsonicOutflow')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSupersonicInflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicInflow')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSupersonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicOutflow')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Wall
    def testNoSlip(self):
        self._db.setValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model', 'k-epsilon')
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/velocity/type', 'noSlip')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('nutkWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Wall
    def testSlip(self):
        self._db.setValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model', 'k-omega')
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/velocity/type', 'slip')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('nutUSpaldingWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Wall
    def testMovingWall(self):
        self._db.setValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model', 'k-epsilon')
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/velocity/type', 'movingWall')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('nutkWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Wall
    def testAtmosphericWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/velocity/type', 'atmosphericWall')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('atmNutkWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
                         content['boundaryField'][boundary]['z0'])

    # Wall
    def testTranslationalMovingWall(self):
        self._db.setValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model', 'k-omega')
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/velocity/type', 'translationalMovingWall')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('nutUSpaldingWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Wall
    def testWallRotationalMovingWall(self):
        self._db.setValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model', 'k-epsilon')
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/velocity/type', 'rotationalMovingWall')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('nutkWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testThermoCoupledWall(self):
        self._db.setValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model', 'k-omega')
        self._db.setValue(self._xpath + '/physicalType', 'thermoCoupledWall')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('nutUSpaldingWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSymmetry(self):
        self._db.setValue(self._xpath + '/physicalType', 'symmetry')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('symmetry', content['boundaryField'][boundary]['type'])

    # Interface
    def testInternalInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'internalInterface')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRotationalPeriodicInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'rotationalPeriodic')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testTranslationalPeriodicInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'translationalPeriodic')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRegionInterface(self):
        self._db.setValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model', 'k-epsilon')
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'regionInterface')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('nutkWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testPorousJump(self):
        self._db.setValue(self._xpath + '/physicalType', 'porousJump')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testFan(self):
        self._db.setValue(self._xpath + '/physicalType', 'fan')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testEmpty(self):
        self._db.setValue(self._xpath + '/physicalType', 'empty')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('empty', content['boundaryField'][boundary]['type'])

    def testCyclic(self):
        self._db.setValue(self._xpath + '/physicalType', 'cyclic')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testWedge(self):
        self._db.setValue(self._xpath + '/physicalType', 'wedge')
        content = Nut(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('wedge', content['boundaryField'][boundary]['type'])


if __name__ == '__main__':
    unittest.main()
