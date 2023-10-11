import unittest

from baramFlow.coredb import coredb
from baramFlow.openfoam.boundary_conditions.alphat import Alphat
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB

dimensions = '[1 -1 -1  0 0 0 0]'
rname = "testRegion_1"
boundary = "testBoundary_1"


class TestAlphat(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()
        self._db.addRegion(rname)
        bcid = self._db.addBoundaryCondition(rname, boundary, 'wall')
        self._xpath = BoundaryDB.getXPath(bcid)
        # ToDo: set initial value
        self._initialValue = 0

        self._db.setValue(ModelsDB.ENERGY_MODELS_XPATH, 'on')

    def tearDown(self) -> None:
        coredb.destroy()

    def testVelocityInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'velocityInlet')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual(dimensions, content['dimensions'])
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    def testFlowRateInletVolume(self):
        self._db.setValue(self._xpath + '/physicalType', 'flowRateInlet')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    def testPressureInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureInlet')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    def testPressureOutletBackflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'true')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    def testPressureOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'false')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testOpenChannelInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'openChannelInlet')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    def testOpenChannelOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'openChannelOutlet')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    def testOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'outflow')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testFreeStream(self):
        self._db.setValue(self._xpath + '/physicalType', 'freeStream')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    def testFarFieldRiemann(self):
        self._db.setValue(self._xpath + '/physicalType', 'farFieldRiemann')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    def testSubsonicInflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'subsonicInflow')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    def testSubsonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'subsonicOutflow')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    def testSupersonicInflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicInflow')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    def testSupersonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicOutflow')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    # Wall
    def testWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('compressible::alphatWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/wallPrandtlNumber'),
                         content['boundaryField'][boundary]['Prt'])

    # Wall
    def testAtmosphericWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/velocity/type', 'atmosphericWall')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])

    def testThermoCoupledWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'thermoCoupledWall')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('compressible::alphatJayatillekeWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/wallPrandtlNumber'),
                         content['boundaryField'][boundary]['Prt'])

    def testSymmetry(self):
        self._db.setValue(self._xpath + '/physicalType', 'symmetry')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('symmetry', content['boundaryField'][boundary]['type'])

    # Interface
    def testInternalInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'internalInterface')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRotationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'rotationalPeriodic')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testTranslationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'translationalPeriodic')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRegionInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'regionInterface')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('compressible::alphatJayatillekeWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/wallPrandtlNumber'),
                         content['boundaryField'][boundary]['Prt'])

    def testPorousJump(self):
        self._db.setValue(self._xpath + '/physicalType', 'porousJump')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testFan(self):
        self._db.setValue(self._xpath + '/physicalType', 'fan')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testEmpty(self):
        self._db.setValue(self._xpath + '/physicalType', 'empty')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('empty', content['boundaryField'][boundary]['type'])

    def testCyclic(self):
        self._db.setValue(self._xpath + '/physicalType', 'cyclic')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testWedge(self):
        self._db.setValue(self._xpath + '/physicalType', 'wedge')
        content = Alphat(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('wedge', content['boundaryField'][boundary]['type'])


if __name__ == '__main__':
    unittest.main()
