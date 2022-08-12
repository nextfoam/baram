import unittest
import os
import shutil
from pathlib import Path

from coredb import coredb
from coredb.filedb import FileDB, BcFileRole
from coredb.boundary_db import BoundaryDB
from coredb.cell_zone_db import RegionDB
from coredb.material_db import Phase
from coredb.project import Project, _Project
from coredb.models_db import ModelsDB
from openfoam.boundary_conditions.t import T
from openfoam.file_system import FileSystem

dimensions = '[0 0 0 1 0 0 0]'
region = "testRegion_1"
boundary = "testBoundary_1"


class TestT(unittest.TestCase):
    def setUp(self):
        self._db = coredb.CoreDB()
        self._db.addRegion(region)
        self._bcid = self._db.addBoundaryCondition(region, boundary, 'wall')
        self._xpath = BoundaryDB.getXPath(self._bcid)
        self._initialValue = self._db.getValue('.//initialization/initialValues/temperature')

        self._db.setValue(ModelsDB.ENERGY_MODELS_XPATH, 'on')

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

    # Temperature Profile is constant
    def testVelocityInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'velocityInlet')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual(dimensions, content['dimensions'])
        self.assertEqual(self._initialValue, content['internalField'][1])
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/temperature/constant'),
                         content['boundaryField'][boundary]['value'][1])

    # Flow Rate Inlet
    def testFlowRateInletVolume(self):
        self._db.setValue(self._xpath + '/physicalType', 'flowRateInlet')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        self._db.setValue(self._xpath + '/flowRateInlet/flowRate/specification', 'volumeFlowRate')
        content = T(region).build().asDict()
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/temperature/constant'),
                         content['boundaryField'][boundary]['value'][1])

    # Flow Rate Inlet
    def testFlowRateInletMass(self):
        self._db.setValue(self._xpath + '/physicalType', 'flowRateInlet')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        self._db.setValue(self._xpath + '/flowRateInlet/flowRate/specification', 'massFlowRate')
        content = T(region).build().asDict()
        self.assertEqual('inletOutletTotalTemperature', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/temperature/constant'),
                         content['boundaryField'][boundary]['T0'][1])
        self.assertEqual(self._db.getValue(self._xpath + '/temperature/constant'),
                         content['boundaryField'][boundary]['T0'][1])

    def testPressureInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureInlet')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('inletOutletTotalTemperature', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/temperature/constant'),
                         content['boundaryField'][boundary]['T0'][1])
        self.assertEqual(self._db.getValue(self._xpath + '/temperature/constant'),
                         content['boundaryField'][boundary]['T0'][1])

    # Pressure Outlet
    def testPressureOutletBackflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'true')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('inletOutletTotalTemperature', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/temperature/constant'),
                         content['boundaryField'][boundary]['inletValue'][1])
        self.assertEqual(self._db.getValue(self._xpath + '/temperature/constant'),
                         content['boundaryField'][boundary]['T0'][1])

    # Pressure Outlet
    def testPressureOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'false')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'outflow')
        content = T(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testFreeStream(self):
        self._db.setValue(self._xpath + '/physicalType', 'freeStream')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('freestream', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getVector(self._xpath + '/freeStream/streamVelocity'),
                         content['boundaryField'][boundary]['freestreamValue'][1])

    def testFarFieldRiemann(self):
        self._db.setValue(self._xpath + '/physicalType', 'farFieldRiemann')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
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
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('subsonicInflow', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getVector(self._xpath + '/subsonicInflow/flowDirection'),
                         content['boundaryField'][boundary]['flowDir'])
        self.assertEqual(self._db.getValue(self._xpath + '/subsonicInflow/totalPressure'),
                         content['boundaryField'][boundary]['p0'])
        self.assertEqual(self._db.getValue(self._xpath + '/subsonicInflow/totalTemperature'),
                         content['boundaryField'][boundary]['T0'])

    def testSubsonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'subsonicOutflow')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('subsonicOutflow', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/subsonicOutflow/staticPressure'),
                         content['boundaryField'][boundary]['pExit'])

    def testSupersonicInflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicInflow')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/temperature/constant'),
                         content['boundaryField'][boundary]['value'][1])

    def testSupersonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicOutflow')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/velocity/type', 'noSlip')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testThermoCoupledWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'thermoCoupledWall')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('turbulentTemperatureCoupledBaffleMixed', content['boundaryField'][boundary]['type'])
        self.assertEqual('solidThermo' if RegionDB.getPhase(region) == Phase.SOLID else 'fluidThermo',
                         content['boundaryField'][boundary]['kappaMethod'])

    def testSymmetry(self):
        self._db.setValue(self._xpath + '/physicalType', 'symmetry')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('symmetry', content['boundaryField'][boundary]['type'])

    # Interface
    def testInternalInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'internalInterface')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRotationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'rotationalPeriodic')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testTranslationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'translationalPeriodic')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRegionInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'regionInterface')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('turbulentTemperatureCoupledBaffleMixed', content['boundaryField'][boundary]['type'])
        self.assertEqual('solidThermo' if RegionDB.getPhase(region) == Phase.SOLID else 'fluidThermo',
                         content['boundaryField'][boundary]['kappaMethod'])

    def testPorousJump(self):
        self._db.setValue(self._xpath + '/physicalType', 'porousJump')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('porousBafflePressure', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/porousJump/darcyCoefficient'),
                         content['boundaryField'][boundary]['D'])
        self.assertEqual(self._db.getValue(self._xpath + '/porousJump/inertialCoefficient'),
                         content['boundaryField'][boundary]['I'])
        self.assertEqual(self._db.getValue(self._xpath + '/porousJump/porousMediaThickness'),
                         content['boundaryField'][boundary]['length'])

    def testFan(self):
        self._db.setValue(self._xpath + '/physicalType', 'fan')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testEmpty(self):
        self._db.setValue(self._xpath + '/physicalType', 'empty')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('empty', content['boundaryField'][boundary]['type'])

    def testCyclic(self):
        self._db.setValue(self._xpath + '/physicalType', 'cyclic')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testWedge(self):
        self._db.setValue(self._xpath + '/physicalType', 'wedge')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(region).build().asDict()
        self.assertEqual('wedge', content['boundaryField'][boundary]['type'])

    # Temperature Profile is spatial distribution
    def testTemperatureSpatialDistribution(self):
        testDir = Path('testTSpatialDistribution')
        csvFile = Path('testTSpatialDistribution/testTSpatial.csv')
        # ToDo: Settings 처리 정리 후 재작성
        os.makedirs(testDir, exist_ok=True)             # 사용자가 Working Directory 선택할 때 이미 존재하는 디렉토리
        project = _Project()
        Project._instance = project               # MainWindow 생성 전에 Project 객체 생성
        project._fileDB = FileDB(testDir)               # Project.open에서 fileDB 생성
        FileSystem._casePath = FileSystem.makeDir(testDir, FileSystem.CASE_DIRECTORY_NAME)
        FileSystem._constantPath = FileSystem.makeDir(FileSystem.caseRoot(), FileSystem.CONSTANT_DIRECTORY_NAME)
                                                        # 사용자가 선택한 mesh directory 복사해 올 때 생성됨
        FileSystem.initCaseDir()                        # CaseGenerator애서 호출
        FileSystem.initRegionDirs(region)               # CaseGenerator에서 호출
        with open(csvFile, 'w') as f:
            f.write('0,0,0,1\n0,0,1,2\n')

        self._db.setValue(self._xpath + '/temperature/profile', 'spatialDistribution')
        project.fileDB().putBcFile(self._bcid, BcFileRole.BC_TEMPERATURE, csvFile)
        content = T(region).build().asDict()
        self.assertEqual('timeVaryingMappedFixedValue', content['boundaryField'][boundary]['type'])

        shutil.rmtree(testDir)                          # 테스트 디렉토리 삭제

    # Temperature Profile is temporalDistribution
    def testTemperaturePiecewiseLinear(self):
        self._db.setValue(self._xpath + '/temperature/profile', 'temporalDistribution')
        self._db.setValue(self._xpath + '/temperature/temporalDistribution/specification', 'piecewiseLinear')
        content = T(region).build().asDict()
        t = self._db.getValue(self._xpath + '/temperature/temporalDistribution/piecewiseLinear/t').split()
        v = self._db.getValue(self._xpath + '/temperature/temporalDistribution/piecewiseLinear/v').split()
        self.assertEqual('uniformFixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual([[t[i], v[i]] for i in range(len(t))], content['boundaryField'][boundary]['uniformValue'][1])

    # Temperature Profile is temporalDistribution
    def testTemperaturePolynomial(self):
        self._db.setValue(self._xpath + '/temperature/profile', 'temporalDistribution')
        self._db.setValue(self._xpath + '/temperature/temporalDistribution/specification', 'polynomial')
        content = T(region).build().asDict()
        t = self._db.getValue(self._xpath + '/temperature/temporalDistribution/piecewiseLinear/t').split()
        v = self._db.getValue(self._xpath + '/temperature/temporalDistribution/piecewiseLinear/v').split()
        self.assertEqual('uniformFixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual([[v[i], i] for i in range(len(v))],
                         content['boundaryField'][boundary]['uniformValue'][1])


if __name__ == '__main__':
    unittest.main()
