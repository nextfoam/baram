import unittest

from coredb import coredb
from coredb.boundary_db import BoundaryDB
from coredb.region_db import RegionDB
from openfoam.boundary_conditions.alpha import Alpha

dimensions = '[0 0 0 0 0 0 0]'
rname = "testRegion_1"
boundary = "testBoundary_1"
primaryMid = 1
material = "water-liquid"
initialValue = '0.1'


class TestAlpha(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()
        self._db.addRegion(rname)
        self._mid = str(self._db.addMaterial(material))
        self._bcid = self._db.addBoundaryCondition(rname, boundary, 'wall')
        self._db.updateRegionMaterials(rname, primaryMid, [self._mid])
        self._xpath = BoundaryDB.getXPath(self._bcid)
        self._db.setValue(
            f'{RegionDB.getXPath(rname)}/initialization/initialValues/volumeFractions/volumeFraction[material="{self._mid}"]/fraction',
            initialValue)

        self._db.setValue('.//models/multiphaseModels/model', 'volumeOfFluid')

        self._volumeFraction = self._db.getValue(f'{self._xpath}/volumeFractions/volumeFraction[material="{self._mid}"]/fraction')

    def tearDown(self) -> None:
        coredb.destroy()

    def testVelocityInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'velocityInlet')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual(dimensions, content['dimensions'])
        self.assertEqual(initialValue, content['internalField'][1])
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._volumeFraction, content['boundaryField'][boundary]['value'][1])

    def testFlowRateInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'flowRateInlet')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._volumeFraction, content['boundaryField'][boundary]['value'][1])

    def testPressureInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureInlet')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._volumeFraction, content['boundaryField'][boundary]['value'][1])

    # Pressure Outlet - turbulentViscosityRatio
    def testPressureOutletBackflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'true')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._volumeFraction, content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(initialValue, content['boundaryField'][boundary]['value'][1])

    # Pressure Outlet
    def testPressureOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'false')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testOpenChannelInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'openChannelInlet')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('variableHeightFlowRate', content['boundaryField'][boundary]['type'])
        self.assertEqual(0.0, content['boundaryField'][boundary]['lowerBound'])
        self.assertEqual(0.9, content['boundaryField'][boundary]['upperBound'])
        self.assertEqual(initialValue, content['boundaryField'][boundary]['value'][1])

    def testOpenChannelOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'openChannelOutlet')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('variableHeightFlowRate', content['boundaryField'][boundary]['type'])
        self.assertEqual(0.0, content['boundaryField'][boundary]['lowerBound'])
        self.assertEqual(0.9, content['boundaryField'][boundary]['upperBound'])
        self.assertEqual(initialValue, content['boundaryField'][boundary]['value'][1])

    def testOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'outflow')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    # Disable Wall Adhesion
    def testWallDisableAdhiesion(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/wallAdhesions/model', 'none')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    # Constant Wall Adhesion
    def testWallContantAdhesion(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/wallAdhesions/model', 'constantContactAngle')
        xpath = f'{self._xpath}/wall/wallAdhesions/wallAdhesion[mid="{self._mid}"][mid="{primaryMid}"]'
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('constantAlphaContactAngle', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(xpath + '/contactAngle'), content['boundaryField'][boundary]['theta0'])
        self.assertEqual(self._db.getValue(self._xpath + '/wall/wallAdhesions/limit'), content['boundaryField'][boundary]['limit'])
        self.assertEqual(initialValue, content['boundaryField'][boundary]['value'][1])

    # Dynamic Wall Adhesion
    def testWallDynamicAdhesion(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/wallAdhesions/model', 'dynamicContactAngle')
        xpath = f'{self._xpath}/wall/wallAdhesions/wallAdhesion[mid="{self._mid}"][mid="{primaryMid}"]'
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('dynamicAlphaContactAngle', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(xpath + '/contactAngle'), content['boundaryField'][boundary]['theta0'])
        self.assertEqual(self._db.getValue(xpath + '/characteristicVelocityScale'), content['boundaryField'][boundary]['uTheta'])
        self.assertEqual(self._db.getValue(xpath + '/advancingContactAngle'), content['boundaryField'][boundary]['thetaA'])
        self.assertEqual(self._db.getValue(xpath + '/recedingContactAngle'), content['boundaryField'][boundary]['thetaR'])
        self.assertEqual(self._db.getValue(self._xpath + '/wall/wallAdhesions/limit'), content['boundaryField'][boundary]['limit'])
        self.assertEqual(initialValue, content['boundaryField'][boundary]['value'][1])

    # Interface
    def testInternalInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'internalInterface')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    def testSymmetry(self):
        self._db.setValue(self._xpath + '/physicalType', 'symmetry')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('symmetry', content['boundaryField'][boundary]['type'])

    # Interface
    def testRotationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'rotationalPeriodic')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testTranslationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'translationalPeriodic')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    def testEmpty(self):
        self._db.setValue(self._xpath + '/physicalType', 'empty')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('empty', content['boundaryField'][boundary]['type'])

    def testWedge(self):
        self._db.setValue(self._xpath + '/physicalType', 'wedge')
        content = Alpha(RegionDB.getRegionProperties(rname), '0', None, self._mid).build().asDict()
        self.assertEqual('wedge', content['boundaryField'][boundary]['type'])


if __name__ == '__main__':
    unittest.main()
