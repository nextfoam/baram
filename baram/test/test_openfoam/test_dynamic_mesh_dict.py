import unittest

from baram.coredb import coredb
from baram.openfoam.constant.dynamic_mesh_dict import DynamicMeshDict


class TestDynamicMeshDict(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()

    def tearDown(self) -> None:
        coredb.destroy()

    def testBuild(self):
        rname = 'testRegion_1'
        zone = 'testZone_1'
        origin = [1, 2, 3]
        axis = [4, 5, 6]
        rpm = 60

        self.db.addRegion(rname)
        czid = self.db.addCellZone(rname, zone)
        xpath = f'.//cellZones/cellZone[@czid="{czid}"]'
        self.db.setValue(xpath + '/zoneType', 'slidingMesh')
        self.db.setValue(xpath + '/slidingMesh/rotatingSpeed', str(rpm))  # in RPM
        self.db.setValue(xpath + '/slidingMesh/rotationAxisOrigin/x', str(origin[0]))
        self.db.setValue(xpath + '/slidingMesh/rotationAxisOrigin/y', str(origin[1]))
        self.db.setValue(xpath + '/slidingMesh/rotationAxisOrigin/z', str(origin[2]))
        self.db.setValue(xpath + '/slidingMesh/rotationAxisDirection/x', str(axis[0]))
        self.db.setValue(xpath + '/slidingMesh/rotationAxisDirection/y', str(axis[1]))
        self.db.setValue(xpath + '/slidingMesh/rotationAxisDirection/z', str(axis[2]))
        self.db.setValue('.//general/flowType', 'compressible')

        content = DynamicMeshDict(rname).build().asDict()

        self.assertEqual('dynamicMotionSolverListFvMesh', content['dynamicFvMesh'])
        self.assertIn('"libfvMotionSolvers.so"', content['motionSolverLibs'])
        self.assertEqual('fvMotionSolvers', content['motionSolver'])

        solver = content['solvers'][f'sliding_{zone}']

        self.assertEqual('solidBody', solver['solver'])
        self.assertEqual('rotatingMotion', solver['solidBodyMotionFunction'])
        self.assertEqual(zone, solver['cellZone'])

        coeffs = solver['rotatingMotionCoeffs']

        self.assertEqual(origin, coeffs['origin'])
        self.assertEqual(axis, coeffs['axis'])
        self.assertEqual(float(rpm) * 2 * 3.141592 / 60, coeffs['omega'])


if __name__ == '__main__':
    unittest.main()
