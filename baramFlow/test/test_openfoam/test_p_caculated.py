import unittest

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.openfoam.boundary_conditions.p import P

dimensions = '[1 -1 -2 0 0 0 0]'
rname = "testRegion_1"
boundary = "testBoundary_1"


class TestPCalculated(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()
        self._db.addRegion(rname)
        bcid = self._db.addBoundaryCondition(rname, boundary, 'wall')
        self._xpath = BoundaryDB.getXPath(bcid)
        self._initialValue = float(self._db.getValue('.//initialization/initialValues/pressure'))
        self._operatingValue = float(self._db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))
        self._calculatedValue = self._initialValue + self._operatingValue

        self._db.setAttribute(GeneralDB.OPERATING_CONDITIONS_XPATH + '/gravity', 'disabled', 'true')

    def tearDown(self) -> None:
        coredb.destroy()

    def testVelocityInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'velocityInlet')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual(dimensions, content['dimensions'])
        self.assertEqual(self._calculatedValue, content['internalField'][1])
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testFlowRateInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'flowRateInlet')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testPressureInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureInlet')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testPressureOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testAblInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'ablInlet')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testOpenChannelInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'openChannelInlet')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testOpenChannelOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'openChannelOutlet')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'outflow')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testFreeStream(self):
        self._db.setValue(self._xpath + '/physicalType', 'freeStream')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testFarFieldRiemann(self):
        self._db.setValue(self._xpath + '/physicalType', 'farFieldRiemann')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testSubsonicInflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'subsonicInflow')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testSubsonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'subsonicOutflow')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testSupersonicInflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicInflow')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testSupersonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicOutflow')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testThermoCoupledWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'thermoCoupledWall')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testSymmetry(self):
        self._db.setValue(self._xpath + '/physicalType', 'symmetry')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('symmetry', content['boundaryField'][boundary]['type'])

    # Interface
    def testInternalInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'internalInterface')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRotationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'rotationalPeriodic')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testTranslationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'translationalPeriodic')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRegionInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'regionInterface')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testPorousJump(self):
        self._db.setValue(self._xpath + '/physicalType', 'porousJump')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testFan(self):
        self._db.setValue(self._xpath + '/physicalType', 'fan')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testEmpty(self):
        self._db.setValue(self._xpath + '/physicalType', 'empty')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('empty', content['boundaryField'][boundary]['type'])

    def testCyclic(self):
        self._db.setValue(self._xpath + '/physicalType', 'cyclic')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testWedge(self):
        self._db.setValue(self._xpath + '/physicalType', 'wedge')
        content = P(RegionDB.getRegionProperties(rname), '0', None, 'p').build().asDict()
        self.assertEqual('wedge', content['boundaryField'][boundary]['type'])


if __name__ == '__main__':
    unittest.main()
