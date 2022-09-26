import unittest
import math

from coredb import coredb
from coredb.boundary_db import BoundaryDB
from coredb.models_db import ModelsDB
from coredb.cell_zone_db import RegionDB
from coredb.material_db import MaterialDB
from openfoam.boundary_conditions.epsilon import Epsilon

dimensions = '[0 2 -3 0 0 0 0]'
region = "testRegion_1"
boundary = "testBoundary_1"


class TestEpsilon(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()
        self._db.addRegion(region)
        bcid = self._db.addBoundaryCondition(region, boundary, 'wall')
        self._xpath = BoundaryDB.getXPath(bcid)

        p = float(self._db.getValue('.//initialization/initialValues/pressure')) \
            + float(self._db.getValue('.//operatingConditions/pressure'))  # Pressure
        t = float(self._db.getValue('.//initialization/initialValues/temperature'))  # Temperature
        v = float(self._db.getValue('.//initialization/initialValues/scaleOfVelocity'))  # Scale of Velocity
        i = float(self._db.getValue('.//initialization/initialValues/turbulentIntensity')) / 100.0  # Turbulent Intensity
        b = float(self._db.getValue('.//initialization/initialValues/turbulentViscosity'))  # Turbulent Viscosity

        mid = RegionDB.getMaterial(region)

        rho = MaterialDB.getDensity(mid, t, p)  # Density
        mu = MaterialDB.getViscosity(mid, t)  # Viscosity

        nu = mu / rho  # Kinetic Viscosity
        nut = b * nu

        k = 1.5 * math.sqrt(v*i)
        e = 0.09 * math.sqrt(k) / nut

        self._initialValue = e

        self._db.setValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/model', 'k-epsilon')

    def tearDown(self) -> None:
        coredb.destroy()

    # Velocity Inlet - kAndEpsilon
    def testVelocityInlet(self):
        self._db.setValue(self._xpath + '/turbulence/k-epsilon/specification', 'kAndEpsilon')
        self._db.setValue(self._xpath + '/physicalType', 'velocityInlet')
        content = Epsilon(region).build().asDict()
        self.assertEqual(dimensions, content['dimensions'])
        self.assertEqual(self._initialValue, content['internalField'][1])
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-epsilon/turbulentDissipationRate'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Flow Rate - intensityAndViscosityRatio
    def testFlowRateInletVolume(self):
        self._db.setValue(self._xpath + '/turbulence/k-epsilon/specification', 'intensityAndViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'flowRateInlet')
        content = Epsilon(region).build().asDict()
        self.assertEqual('viscosityRatioInletOutletTDR', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'),
                         content['boundaryField'][boundary]['viscosityRatio'])

    def testPressureInlet(self):
        self._db.setValue(self._xpath + '/turbulence/k-epsilon/specification', 'kAndEpsilon')
        self._db.setValue(self._xpath + '/physicalType', 'pressureInlet')
        content = Epsilon(region).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-epsilon/turbulentDissipationRate'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    # Pressure Outlet
    def testPressureOutletBackflow(self):
        self._db.setValue(self._xpath + '/turbulence/k-epsilon/specification', 'intensityAndViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'true')
        content = Epsilon(region).build().asDict()
        self.assertEqual('viscosityRatioInletOutletTDR', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'),
                         content['boundaryField'][boundary]['viscosityRatio'])

    # Pressure Outlet
    def testPressureOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'false')
        content = Epsilon(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testAblInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'ablInlet')
        content = Epsilon(region).build().asDict()
        self.assertEqual('atmBoundaryLayerInletEpsilon', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/flowDirection'),
                         content['boundaryField'][boundary]['flowDir'])
        self.assertEqual(self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/groundNormalDirection'),
                         content['boundaryField'][boundary]['zDir'])
        self.assertEqual(self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceFlowSpeed'),
                         content['boundaryField'][boundary]['Uref'])
        self.assertEqual(self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceHeight'),
                         content['boundaryField'][boundary]['Zref'])
        self.assertEqual(self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
                         content['boundaryField'][boundary]['z0'])
        self.assertEqual(self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate'),
                         content['boundaryField'][boundary]['d'])

    def testOpenChannelInlet(self):
        self._db.setValue(self._xpath + '/turbulence/k-epsilon/specification', 'kAndEpsilon')
        self._db.setValue(self._xpath + '/physicalType', 'openChannelInlet')
        content = Epsilon(region).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-epsilon/turbulentDissipationRate'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testOpenChannelOutlet(self):
        self._db.setValue(self._xpath + '/turbulence/k-epsilon/specification', 'intensityAndViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'openChannelOutlet')
        content = Epsilon(region).build().asDict()
        self.assertEqual('viscosityRatioInletOutletTDR', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'),
                         content['boundaryField'][boundary]['viscosityRatio'])

    def testOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'outflow')
        content = Epsilon(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    # Free Stream
    def testFreeStreamKAndEpsilon(self):
        self._db.setValue(self._xpath + '/turbulence/k-epsilon/specification', 'kAndEpsilon')
        self._db.setValue(self._xpath + '/physicalType', 'freeStream')
        content = Epsilon(region).build().asDict()
        self.assertEqual('freestream', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getVector(self._xpath + '/freeStream/streamVelocity'),
                         content['boundaryField'][boundary]['freestreamValue'][1])

    # Free Stream
    def testFreeStreamKEpsilonIntensityAndViscosityRatio(self):
        self._db.setValue(self._xpath + '/turbulence/k-epsilon/specification', 'intensityAndViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'freeStream')
        content = Epsilon(region).build().asDict()
        self.assertEqual('viscosityRatioInletOutletTDR', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'),
                         content['boundaryField'][boundary]['viscosityRatio'])

    def testFarFieldRiemann(self):
        self._db.setValue(self._xpath + '/turbulence/k-epsilon/specification', 'kAndEpsilon')
        self._db.setValue(self._xpath + '/physicalType', 'farFieldRiemann')
        content = Epsilon(region).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-epsilon/turbulentDissipationRate'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSubsonicInflow(self):
        self._db.setValue(self._xpath + '/turbulence/k-epsilon/specification', 'intensityAndViscosityRatio')
        self._db.setValue(self._xpath + '/physicalType', 'subsonicInflow')
        content = Epsilon(region).build().asDict()
        self.assertEqual('viscosityRatioInletOutletTDR', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'),
                         content['boundaryField'][boundary]['viscosityRatio'])

    def testSubsonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'subsonicOutflow')
        content = Epsilon(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testSupersonicInflow(self):
        self._db.setValue(self._xpath + '/turbulence/k-epsilon/specification', 'kAndEpsilon')
        self._db.setValue(self._xpath + '/physicalType', 'supersonicInflow')
        content = Epsilon(region).build().asDict()
        self.assertEqual('inletOutlet', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/turbulence/k-epsilon/turbulentDissipationRate'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSupersonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicOutflow')
        content = Epsilon(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        content = Epsilon(region).build().asDict()
        self.assertEqual('epsilonWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testThermoCoupledWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'thermoCoupledWall')
        content = Epsilon(region).build().asDict()
        self.assertEqual('epsilonWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testSymmetry(self):
        self._db.setValue(self._xpath + '/physicalType', 'symmetry')
        content = Epsilon(region).build().asDict()
        self.assertEqual('symmetry', content['boundaryField'][boundary]['type'])

    # Interface
    def testInternalInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'internalInterface')
        content = Epsilon(region).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRotationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'rotationalPeriodic')
        content = Epsilon(region).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testTranslationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'translationalPeriodic')
        content = Epsilon(region).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRegionInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'regionInterface')
        content = Epsilon(region).build().asDict()
        self.assertEqual('epsilonWallFunction', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._initialValue, content['boundaryField'][boundary]['value'][1])

    def testPorousJump(self):
        self._db.setValue(self._xpath + '/physicalType', 'porousJump')
        content = Epsilon(region).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testFan(self):
        self._db.setValue(self._xpath + '/physicalType', 'fan')
        content = Epsilon(region).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testEmpty(self):
        self._db.setValue(self._xpath + '/physicalType', 'empty')
        content = Epsilon(region).build().asDict()
        self.assertEqual('empty', content['boundaryField'][boundary]['type'])

    def testCyclic(self):
        self._db.setValue(self._xpath + '/physicalType', 'cyclic')
        content = Epsilon(region).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testWedge(self):
        self._db.setValue(self._xpath + '/physicalType', 'wedge')
        content = Epsilon(region).build().asDict()
        self.assertEqual('wedge', content['boundaryField'][boundary]['type'])


if __name__ == '__main__':
    unittest.main()
