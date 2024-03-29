import unittest

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.openfoam.boundary_conditions.omega import Omega

dimensions = '[0 0 -1 0 0 0 0]'
rname = "testRegion_1"
boundary = "testBoundary_1"


class TestOmega(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()
        self._db.addRegion(rname)
        bcid = self._db.addBoundaryCondition(rname, boundary, 'wall')
        self._xpath = BoundaryDB.getXPath(bcid)

        p = float(self._db.getValue('.//initialization/initialValues/pressure')) \
            + float(self._db.getValue('.//operatingConditions/pressure'))  # Pressure
        t = float(self._db.getValue('.//initialization/initialValues/temperature'))  # Temperature
        v = float(self._db.getValue('.//initialization/initialValues/scaleOfVelocity'))  # Scale of Velocity
        i = float(self._db.getValue('.//initialization/initialValues/turbulentIntensity')) / 100.0  # Turbulent Intensity
        b = float(self._db.getValue('.//initialization/initialValues/turbulentViscosity'))  # Turbulent Viscosity

        mid = RegionDB.getMaterial(rname)

        rho = MaterialDB.getDensity(mid, t, p)  # Density
        mu = MaterialDB.getViscosity(mid, t)  # Viscosity

        nu = mu / rho  # Kinetic Viscosity
        nut = b * nu

        k = 1.5 * (v*i) ** 2
        w = k / nut

        self._initialValue = w

        self._db.setValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model', 'k-omega')

    def tearDown(self) -> None:
        coredb.destroy()

    # Velocity Inlet - kAndOmega
    def testVelocityInlet(self):
        self._db.setValue(self._xpath + '/turbulence/k-omega/specification', 'kAndOmega')
        self._db.setValue(self._xpath + '/physicalType', 'velocityInlet')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual(dimensions, content['dimensions'])
        self.assertEqual(self._initialValue, content['internalField'][1])
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-omega/specificDissipationRate'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Flow Rate - intensityAndViscosityRatio
    def testFlowRateInletVolume(self):
        self._db.setValue(self._xpath + '/turbulence/k-omega/specification', 'intensityAndViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'flowRateInlet')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('viscosityRatioInletOutletTDR', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-omega/turbulentViscosityRatio'),
                         content['boundaryField'][boundary]['viscosityRatio'][1])

    def testPressureInlet(self):
        self._db.setValue(self._xpath + '/turbulence/k-omega/specification', 'kAndOmega')
        self._db.setValue(self._xpath + '/physicalType', 'pressureInlet')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-omega/specificDissipationRate'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Pressure Outlet
    def testPressureOutletBackflow(self):
        self._db.setValue(self._xpath + '/turbulence/k-omega/specification', 'intensityAndViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'true')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('viscosityRatioInletOutletTDR', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-omega/turbulentViscosityRatio'),
                         content['boundaryField'][boundary]['viscosityRatio'][1])

    # Pressure Outlet
    def testPressureOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'false')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testAblInlet(self):
        self._db.setValue(self._xpath + '/turbulence/k-omega/specification', 'kAndOmega')
        self._db.setValue(self._xpath + '/physicalType', 'ablInlet')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-omega/specificDissipationRate'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testOpenChannelInlet(self):
        self._db.setValue(self._xpath + '/turbulence/k-omega/specification', 'intensityAndViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'openChannelInlet')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('viscosityRatioInletOutletTDR', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-omega/turbulentViscosityRatio'),
                         content['boundaryField'][boundary]['viscosityRatio'][1])

    def testOpenChannelOutlet(self):
        self._db.setValue(self._xpath + '/turbulence/k-omega/specification', 'kAndOmega')
        self._db.setValue(self._xpath + '/physicalType', 'openChannelOutlet')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-omega/specificDissipationRate'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'outflow')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    # Free Stream
    def testFreeStreamKAndOmega(self):
        self._db.setValue(self._xpath + '/turbulence/k-omega/specification', 'kAndOmega')
        self._db.setValue(self._xpath + '/physicalType', 'freeStream')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('freestream', content['boundaryField'][boundary]['type'])
        self.assertEqual(float(self._db.getValue(self._xpath + '/turbulence/k-omega/specificDissipationRate')),
                         content['boundaryField'][boundary]['freestreamValue'][1])

    # Free Stream
    def testFreeStreamKOmegaIntensityAndViscosityRatio(self):
        self._db.setValue(self._xpath + '/turbulence/k-omega/specification', 'intensityAndViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'freeStream')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('freestream', content['boundaryField'][boundary]['type'])
        self.assertEqual(
            Omega(RegionDB.getRegionProperties(rname), '0', None)._calculateFreeStreamKW(self._xpath, rname)[1],
            content['boundaryField'][boundary]['freestreamValue'][1])

    def testFarFieldRiemann(self):
        self._db.setValue(self._xpath + '/turbulence/k-omega/specification', 'kAndOmega')
        self._db.setValue(self._xpath + '/physicalType', 'farFieldRiemann')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-omega/specificDissipationRate'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSubsonicInflow(self):
        self._db.setValue(self._xpath + '/turbulence/k-omega/specification', 'intensityAndViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'subsonicInflow')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('viscosityRatioInletOutletTDR', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-omega/turbulentViscosityRatio'),
                         content['boundaryField'][boundary]['viscosityRatio'][1])

    def testSubsonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'subsonicOutflow')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testSupersonicInflow(self):
        self._db.setValue(self._xpath + '/turbulence/k-omega/specification', 'kAndOmega')
        self._db.setValue(self._xpath + '/physicalType', 'supersonicInflow')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-omega/specificDissipationRate'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSupersonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicOutflow')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    # Wall
    def testWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('omegaWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Wall
    def testAtmosphericWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/velocity/type', 'atmosphericWall')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('atmOmegaWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
                         content['boundaryField'][boundary]['z0'])
        self.assertEqual(self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate'),
                         content['boundaryField'][boundary]['d'])

    def testThermoCoupledWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'thermoCoupledWall')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('omegaWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSymmetry(self):
        self._db.setValue(self._xpath + '/physicalType', 'symmetry')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('symmetry', content['boundaryField'][boundary]['type'])

    # interface
    def testInternalInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'internalInterface')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # interface
    def testRotationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'rotationalPeriodic')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # interface
    def testTranslationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'translationalPeriodic')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # interface
    def testRegionInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'regionInterface')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('omegaWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testPorousJump(self):
        self._db.setValue(self._xpath + '/physicalType', 'porousJump')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testFan(self):
        self._db.setValue(self._xpath + '/physicalType', 'fan')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testEmpty(self):
        self._db.setValue(self._xpath + '/physicalType', 'empty')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('empty', content['boundaryField'][boundary]['type'])

    def testCyclic(self):
        self._db.setValue(self._xpath + '/physicalType', 'cyclic')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testWedge(self):
        self._db.setValue(self._xpath + '/physicalType', 'wedge')
        content = Omega(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('wedge', content['boundaryField'][boundary]['type'])


if __name__ == '__main__':
    unittest.main()
