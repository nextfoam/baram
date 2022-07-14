import unittest

from coredb import coredb
from coredb.boundary_db import BoundaryDB
from coredb.cell_zone_db import CellZoneDB
from openfoam.boundary_conditions.p import P

dimensions = '[1 -1 -2 0 0 0 0]'
region = "testRegion_1"
boundary = "testBoundary_1"


class TestP(unittest.TestCase):
    def setUp(self):
        self._db = coredb.CoreDB()
        self._db.addRegion(region)
        bcid = self._db.addBoundaryCondition(region, boundary, 'wall')
        self.xpath = BoundaryDB.getXPath(bcid)
        self._initialValue = self._db.getValue('.//initialization/initialValues/pressure')
        operatingValue = self._db.getValue(CellZoneDB.OPERATING_CONDITIONS_XPATH + '/pressure')
        self._calculatedValue = float(self._initialValue) + float(operatingValue)

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

    def testCalculated(self):
        content = P(region, 'p', True).build().asDict()
        self.assertEqual(dimensions, content['dimensions'])
        self.assertEqual(self._initialValue, content['internalField'][1])
        self.assertEqual('calculated', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._calculatedValue, content['boundaryField'][boundary]['value'][1])

    def testVelocityInlet(self):
        self._db.setValue(self.xpath + '/physicalType', 'velocityInlet')
        content = P(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testFlowRateInlet(self):
        self._db.setValue(self.xpath + '/physicalType', 'flowRateInlet')
        content = P(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testPressureInlet(self):
        self._db.setValue(self.xpath + '/physicalType', 'pressureInlet')
        content = P(region).build().asDict()
        self.assertEqual('totalPressure', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self.xpath + '/pressureInlet/pressure'),
                         content['boundaryField'][boundary]['p0'][1])

    def testPressureOutlet(self):
        self._db.setValue(self.xpath + '/physicalType', 'pressureOutlet')
        content = P(region).build().asDict()
        self.assertEqual('totalPressure', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self.xpath + '/pressureOutlet/totalPressure'),
                         content['boundaryField'][boundary]['p0'][1])

    def testAblInlet(self):
        self._db.setValue(self.xpath + '/physicalType', 'ablInlet')
        content = P(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testOpenChannelInlet(self):
        self._db.setValue(self.xpath + '/physicalType', 'openChannelInlet')
        content = P(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testOpenChannelOutlet(self):
        self._db.setValue(self.xpath + '/physicalType', 'openChannelOutlet')
        content = P(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testOutflow(self):
        self._db.setValue(self.xpath + '/physicalType', 'outflow')
        content = P(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testFreeStream(self):
        self._db.setValue(self.xpath + '/physicalType', 'freeStream')
        content = P(region).build().asDict()
        self.assertEqual('freestreamPressure', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self.xpath + '/freeStream/pressure'),
                         content['boundaryField'][boundary]['freestreamValue'])

    def testFarFieldRiemann(self):
        self._db.setValue(self.xpath + '/physicalType', 'farFieldRiemann')
        content = P(region).build().asDict()
        self.assertEqual('farfieldRiemann', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getVector(self.xpath + '/farFieldRiemann/flowDirection'),
                         content['boundaryField'][boundary]['flowDir'])
        self.assertEqual(self._db.getValue(self.xpath + '/farFieldRiemann/machNumber'),
                         content['boundaryField'][boundary]['MInf'])
        self.assertEqual(self._db.getValue(self.xpath + '/farFieldRiemann/staticPressure'),
                         content['boundaryField'][boundary]['pInf'])
        self.assertEqual(self._db.getValue(self.xpath + '/farFieldRiemann/staticTemperature'),
                         content['boundaryField'][boundary]['TInf'])

    def testSubsonicInflow(self):
        self._db.setValue(self.xpath + '/physicalType', 'subsonicInflow')
        content = P(region).build().asDict()
        self.assertEqual('subsonicInflow', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getVector(self.xpath + '/subsonicInflow/flowDirection'),
                         content['boundaryField'][boundary]['flowDir'])
        self.assertEqual(self._db.getValue(self.xpath + '/subsonicInflow/totalPressure'),
                         content['boundaryField'][boundary]['p0'])
        self.assertEqual(self._db.getValue(self.xpath + '/subsonicInflow/totalTemperature'),
                         content['boundaryField'][boundary]['T0'])

    def testSubsonicOutflow(self):
        self._db.setValue(self.xpath + '/physicalType', 'subsonicOutflow')
        content = P(region).build().asDict()
        self.assertEqual('subsonicOutflow', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self.xpath + '/subsonicOutflow/staticPressure'),
                         content['boundaryField'][boundary]['pExit'])

    def testSupersonicInflow(self):
        self._db.setValue(self.xpath + '/physicalType', 'supersonicInflow')
        content = P(region).build().asDict()
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self.xpath + '/supersonicInflow/staticPressure'),
                         content['boundaryField'][boundary]['value'][1])

    def testSupersonicOutflow(self):
        self._db.setValue(self.xpath + '/physicalType', 'supersonicOutflow')
        content = P(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testWall(self):
        self._db.setValue(self.xpath + '/physicalType', 'wall')
        content = P(region).build().asDict()
        self.assertEqual('fixedFluxPressure', content['boundaryField'][boundary]['type'])

    def testThermoCoupledWall(self):
        self._db.setValue(self.xpath + '/physicalType', 'thermoCoupledWall')
        content = P(region).build().asDict()
        self.assertEqual('fixedFluxPressure', content['boundaryField'][boundary]['type'])

    def testSymmetry(self):
        self._db.setValue(self.xpath + '/physicalType', 'symmetry')
        content = P(region).build().asDict()
        self.assertEqual('symmetry', content['boundaryField'][boundary]['type'])

    # Interface
    def testInternalInterface(self):
        self._db.setValue(self.xpath + '/physicalType', 'interface')
        self._db.setValue(self.xpath + '/interface/mode', 'internalInterface')
        content = P(region).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRotationalPeriodic(self):
        self._db.setValue(self.xpath + '/physicalType', 'interface')
        self._db.setValue(self.xpath + '/interface/mode', 'rotationalPeriodic')
        content = P(region).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testTranslationalPeriodic(self):
        self._db.setValue(self.xpath + '/physicalType', 'interface')
        self._db.setValue(self.xpath + '/interface/mode', 'translationalPeriodic')
        content = P(region).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRegionInterface(self):
        self._db.setValue(self.xpath + '/physicalType', 'interface')
        self._db.setValue(self.xpath + '/interface/mode', 'regionInterface')
        content = P(region).build().asDict()
        self.assertEqual('fixedFluxPressure', content['boundaryField'][boundary]['type'])

    def testPorousJump(self):
        self._db.setValue(self.xpath + '/physicalType', 'porousJump')
        content = P(region).build().asDict()
        self.assertEqual('porousBafflePressure', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self.xpath + '/porousJump/darcyCoefficient'),
                         content['boundaryField'][boundary]['D'])
        self.assertEqual(self._db.getValue(self.xpath + '/porousJump/inertialCoefficient'),
                         content['boundaryField'][boundary]['I'])
        self.assertEqual(self._db.getValue(self.xpath + '/porousJump/porousMediaThickness'),
                         content['boundaryField'][boundary]['length'])

    def testFan(self):
        self._db.setValue(self.xpath + '/physicalType', 'fan')
        content = P(region).build().asDict()
        self.assertEqual('fanPressureJump', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self.xpath + '/fan/fanCurveFile'), content['boundaryField'][boundary]['file'])
        self.assertEqual(self._db.getValue(self.xpath + '/fan/reverseDirection'),
                         content['boundaryField'][boundary]['reverse'])

    def testEmpty(self):
        self._db.setValue(self.xpath + '/physicalType', 'empty')
        content = P(region).build().asDict()
        self.assertEqual('empty', content['boundaryField'][boundary]['type'])

    def testCyclic(self):
        self._db.setValue(self.xpath + '/physicalType', 'cyclic')
        content = P(region).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testWedge(self):
        self._db.setValue(self.xpath + '/physicalType', 'wedge')
        content = P(region).build().asDict()
        self.assertEqual('wedge', content['boundaryField'][boundary]['type'])


if __name__ == '__main__':
    unittest.main()
