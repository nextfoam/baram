import unittest
import os
import shutil
from pathlib import Path

from coredb import coredb
from coredb.project import Project, _Project
from coredb.filedb import FileDB, BcFileRole
from coredb.boundary_db import BoundaryDB
from coredb.general_db import GeneralDB
from coredb.models_db import ModelsDB
from coredb.region_db import RegionDB
from openfoam.boundary_conditions.p import P
from openfoam.file_system import FileSystem

dimensions = '[1 -1 -2 0 0 0 0]'
region = "testRegion_1"
boundary = "testBoundary_1"


class TestP(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()
        self._db.addRegion(region)
        self._bcid = self._db.addBoundaryCondition(region, boundary, 'wall')
        self._xpath = BoundaryDB.getXPath(self._bcid)
        self._initialValue = float(self._db.getValue('.//initialization/initialValues/pressure'))
        self._operatingValue = float(self._db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))
        self._calculatedValue = self._initialValue + self._operatingValue

        self._db.setAttribute(GeneralDB.OPERATING_CONDITIONS_XPATH + '/gravity', 'disabled', 'true')
        self._db.setValue(ModelsDB.ENERGY_MODELS_XPATH, 'on')
        self._db.setValue(ModelsDB.SPECIES_MODELS_XPATH, 'on')

    def tearDown(self) -> None:
        coredb.destroy()

    def testVelocityInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'velocityInlet')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual(dimensions, content['dimensions'])
        self.assertEqual(self._calculatedValue, content['internalField'][1])
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testFlowRateInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'flowRateInlet')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testPressureInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureInlet')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('totalPressure', content['boundaryField'][boundary]['type'])
        self.assertEqual(float(self._db.getValue(self._xpath + '/pressureInlet/pressure'))+self._operatingValue,
                         content['boundaryField'][boundary]['p0'][1])

    def testPressureOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('totalPressure', content['boundaryField'][boundary]['type'])
        self.assertEqual(float(self._db.getValue(self._xpath + '/pressureOutlet/totalPressure'))+self._operatingValue,
                         content['boundaryField'][boundary]['p0'][1])

    def testAblInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'ablInlet')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testOpenChannelInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'openChannelInlet')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testOpenChannelOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'openChannelOutlet')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'outflow')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testFreeStream(self):
        self._db.setValue(self._xpath + '/physicalType', 'freeStream')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('freestreamPressure', content['boundaryField'][boundary]['type'])
        self.assertEqual(float(self._db.getValue(self._xpath + '/freeStream/pressure'))+self._operatingValue,
                         content['boundaryField'][boundary]['freestreamValue'][1])

    def testFarFieldRiemann(self):
        self._db.setValue(self._xpath + '/physicalType', 'farFieldRiemann')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('farfieldRiemann', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getVector(self._xpath + '/farFieldRiemann/flowDirection'),
                         content['boundaryField'][boundary]['flowDir'])
        self.assertEqual(self._db.getValue(self._xpath + '/farFieldRiemann/machNumber'),
                         content['boundaryField'][boundary]['MInf'])
        self.assertEqual(self._db.getValue(self._xpath + '/farFieldRiemann/staticPressure'),
                         content['boundaryField'][boundary]['pInf'])
        self.assertEqual(self._db.getValue(self._xpath + '/farFieldRiemann/staticTemperature'),
                         content['boundaryField'][boundary]['TInf'])

    def testSubsonicInflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'subsonicInflow')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('subsonicInflow', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getVector(self._xpath + '/subsonicInflow/flowDirection'),
                         content['boundaryField'][boundary]['flowDir'])
        self.assertEqual(self._db.getValue(self._xpath + '/subsonicInflow/totalPressure'),
                         content['boundaryField'][boundary]['p0'])
        self.assertEqual(self._db.getValue(self._xpath + '/subsonicInflow/totalTemperature'),
                         content['boundaryField'][boundary]['T0'])

    def testSubsonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'subsonicOutflow')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('subsonicOutflow', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/subsonicOutflow/staticPressure'),
                         content['boundaryField'][boundary]['pExit'])

    def testSupersonicInflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicInflow')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(float(self._db.getValue(self._xpath + '/supersonicInflow/staticPressure'))+self._operatingValue,
                         content['boundaryField'][boundary]['value'][1])

    def testSupersonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicOutflow')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('fixedFluxPressure', content['boundaryField'][boundary]['type'])

    def testThermoCoupledWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'thermoCoupledWall')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('fixedFluxPressure', content['boundaryField'][boundary]['type'])

    def testSymmetry(self):
        self._db.setValue(self._xpath + '/physicalType', 'symmetry')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('symmetry', content['boundaryField'][boundary]['type'])

    # Interface
    def testInternalInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'internalInterface')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRotationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'rotationalPeriodic')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testTranslationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'translationalPeriodic')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRegionInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'regionInterface')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('fixedFluxPressure', content['boundaryField'][boundary]['type'])

    def testPorousJump(self):
        self._db.setValue(self._xpath + '/physicalType', 'porousJump')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('porousBafflePressure', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/porousJump/darcyCoefficient'),
                         content['boundaryField'][boundary]['D'])
        self.assertEqual(self._db.getValue(self._xpath + '/porousJump/inertialCoefficient'),
                         content['boundaryField'][boundary]['I'])
        self.assertEqual(self._db.getValue(self._xpath + '/porousJump/porousMediaThickness'),
                         content['boundaryField'][boundary]['length'])

    def testFan(self):
        testDir = Path('testPFanCurve')
        csvFile = Path('testPFanCurve/testFanCurve.csv')

        os.makedirs(testDir, exist_ok=True)             # 사용자가 Working Directory 선택할 때 이미 존재하는 디렉토리
        project = _Project()
        Project._instance = project                     # MainWindow 생성 전에 Project 객체 생성
        project._fileDB = FileDB(testDir)               # Project.open에서 fileDB 생성
        FileSystem._casePath = FileSystem.makeDir(testDir, FileSystem.CASE_DIRECTORY_NAME)
        FileSystem._constantPath = FileSystem.makeDir(FileSystem.caseRoot(), FileSystem.CONSTANT_DIRECTORY_NAME)
        with open(csvFile, 'w') as f:
            f.write('0,0,0,1\n0,0,1,2\n')

        curveFileName = f'UvsPressure{self._bcid}'
        curveFilePath = FileSystem._constantPath / curveFileName

        self._db.setValue(self._xpath + '/physicalType', 'fan')
        self._db.setValue(self._xpath + '/fan/fanCurveFile',
                          project.fileDB().putBcFile(self._bcid, BcFileRole.BC_FAN_CURVE, csvFile))
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('fan', content['boundaryField'][boundary]['type'])
        self.assertEqual(f'<constant>/{curveFileName}',
                         content['boundaryField'][boundary]['jumpTableCoeffs']['file'])
        self.assertTrue(curveFilePath.is_file())

        shutil.rmtree(testDir)                          # 테스트 디렉토리 삭제

    def testEmpty(self):
        self._db.setValue(self._xpath + '/physicalType', 'empty')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('empty', content['boundaryField'][boundary]['type'])

    def testCyclic(self):
        self._db.setValue(self._xpath + '/physicalType', 'cyclic')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testWedge(self):
        self._db.setValue(self._xpath + '/physicalType', 'wedge')
        content = P(RegionDB.getRegionProperties(region)).build().asDict()
        self.assertEqual('wedge', content['boundaryField'][boundary]['type'])


if __name__ == '__main__':
    unittest.main()
