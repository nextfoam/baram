import unittest
import os
import shutil
from pathlib import Path

from baramFlow.coredb import coredb
from baramFlow.coredb.filedb import FileDB, BcFileRole
from baramFlow.coredb.project import Project, _Project
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.material_db import Phase
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.openfoam.boundary_conditions.t import T
from baramFlow.openfoam.file_system import FileSystem
from libbaram.openfoam.constants import Directory

dimensions = '[0 0 0 1 0 0 0]'
rname = "testRegion_1"
boundary = "testBoundary_1"


class TestT(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()
        self._db.addRegion(rname)
        self._bcid = self._db.addBoundaryCondition(rname, boundary, 'wall')
        self._xpath = BoundaryDB.getXPath(self._bcid)
        self._initialValue = float(self._db.getValue('.//initialization/initialValues/temperature'))

        self._db.setValue(ModelsDB.ENERGY_MODELS_XPATH, 'on')

    def tearDown(self) -> None:
        coredb.destroy()

    # Temperature Profile is constant
    def testVelocityInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'velocityInlet')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual(dimensions, content['dimensions'])
        self.assertEqual(self._initialValue, content['internalField'][1])
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(float(self._db.getValue(self._xpath + '/temperature/constant')),
                         content['boundaryField'][boundary]['value'][1])

    # Flow Rate Inlet
    def testFlowRateInletVolume(self):
        self._db.setValue(self._xpath + '/physicalType', 'flowRateInlet')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        self._db.setValue(self._xpath + '/flowRateInlet/flowRate/specification', 'volumeFlowRate')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(float(self._db.getValue(self._xpath + '/temperature/constant')),
                         content['boundaryField'][boundary]['value'][1])

    # Flow Rate Inlet
    def testFlowRateInletMass(self):
        self._db.setValue(self._xpath + '/physicalType', 'flowRateInlet')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        self._db.setValue(self._xpath + '/flowRateInlet/flowRate/specification', 'massFlowRate')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('inletOutletTotalTemperature', content['boundaryField'][boundary]['type'])
        self.assertEqual(float(self._db.getValue(self._xpath + '/temperature/constant')),
                         content['boundaryField'][boundary]['T0'][1])
        self.assertEqual(float(self._db.getValue(self._xpath + '/temperature/constant')),
                         content['boundaryField'][boundary]['T0'][1])

    def testPressureInlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureInlet')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('inletOutletTotalTemperature', content['boundaryField'][boundary]['type'])
        self.assertEqual(float(self._db.getValue(self._xpath + '/temperature/constant')),
                         content['boundaryField'][boundary]['T0'][1])
        self.assertEqual(float(self._db.getValue(self._xpath + '/temperature/constant')),
                         content['boundaryField'][boundary]['T0'][1])

    # Pressure Outlet
    def testPressureOutletBackflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'true')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('inletOutletTotalTemperature', content['boundaryField'][boundary]['type'])
        self.assertEqual(float(self._db.getValue(self._xpath + '/temperature/constant')),
                         float(content['boundaryField'][boundary]['inletValue'][1]))
        self.assertEqual(float(self._db.getValue(self._xpath + '/temperature/constant')),
                         float(content['boundaryField'][boundary]['T0'][1]))

    # Pressure Outlet
    def testPressureOutlet(self):
        self._db.setValue(self._xpath + '/physicalType', 'pressureOutlet')
        self._db.setValue(self._xpath + '/pressureOutlet/calculatedBackflow', 'false')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'outflow')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testFreeStream(self):
        self._db.setValue(self._xpath + '/physicalType', 'freeStream')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('freestream', content['boundaryField'][boundary]['type'])
        self.assertEqual(float(self._db.getValue(self._xpath + '/temperature/constant')),
                         content['boundaryField'][boundary]['freestreamValue'][1])

    def testFarFieldRiemann(self):
        self._db.setValue(self._xpath + '/physicalType', 'farFieldRiemann')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
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
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
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
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('subsonicOutflow', content['boundaryField'][boundary]['type'])
        self.assertEqual(self._db.getValue(self._xpath + '/subsonicOutflow/staticPressure'),
                         content['boundaryField'][boundary]['pExit'])

    def testSupersonicInflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicInflow')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(float(self._db.getValue(self._xpath + '/temperature/constant')),
                         content['boundaryField'][boundary]['value'][1])

    def testSupersonicOutflow(self):
        self._db.setValue(self._xpath + '/physicalType', 'supersonicOutflow')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testWallAdiabatic(self):
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/velocity/type', 'noSlip')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')

        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()

        self.assertEqual('zeroGradient', content['boundaryField'][boundary]['type'])

    def testWallConstantTemperature(self):
        t = 321.1
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/velocity/type', 'slip')
        self._db.setValue(self._xpath + '/wall/temperature/type', 'constantTemperature')
        self._db.setValue(self._xpath + '/wall/temperature/temperature', str(t))

        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()

        self.assertEqual('fixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual(t, float(content['boundaryField'][boundary]['value'][1]))

    def testWallConvection(self):
        h = 123.4
        ta = 321.1
        self._db.setValue(self._xpath + '/physicalType', 'wall')
        self._db.setValue(self._xpath + '/wall/velocity/type', 'movingWall')
        self._db.setValue(self._xpath + '/wall/temperature/type', 'convection')
        self._db.setValue(self._xpath + '/wall/temperature/heatTransferCoefficient', str(h))
        self._db.setValue(self._xpath + '/wall/temperature/freeStreamTemperature', str(ta))

        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()

        self.assertEqual('externalWallHeatFluxTemperature', content['boundaryField'][boundary]['type'])
        self.assertEqual('coefficient', content['boundaryField'][boundary]['mode'])
        self.assertEqual(h, float(content['boundaryField'][boundary]['h'][1]))
        self.assertEqual(ta, float(content['boundaryField'][boundary]['Ta'][1]))

    def testThermoCoupledWall(self):
        self._db.setValue(self._xpath + '/physicalType', 'thermoCoupledWall')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('compressible::turbulentTemperatureRadCoupledMixed', content['boundaryField'][boundary]['type'])
        self.assertEqual('solidThermo' if RegionDB.getPhase(rname) == Phase.SOLID else 'fluidThermo',
                         content['boundaryField'][boundary]['kappaMethod'])

    def testSymmetry(self):
        self._db.setValue(self._xpath + '/physicalType', 'symmetry')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('symmetry', content['boundaryField'][boundary]['type'])

    # Interface
    def testInternalInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'internalInterface')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRotationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'rotationalPeriodic')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testTranslationalPeriodic(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'translationalPeriodic')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclicAMI', content['boundaryField'][boundary]['type'])

    # Interface
    def testRegionInterface(self):
        self._db.setValue(self._xpath + '/physicalType', 'interface')
        self._db.setValue(self._xpath + '/interface/mode', 'regionInterface')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('compressible::turbulentTemperatureRadCoupledMixed', content['boundaryField'][boundary]['type'])
        self.assertEqual('solidThermo' if RegionDB.getPhase(rname) == Phase.SOLID else 'fluidThermo',
                         content['boundaryField'][boundary]['kappaMethod'])

    def testPorousJump(self):
        self._db.setValue(self._xpath + '/physicalType', 'porousJump')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testFan(self):
        self._db.setValue(self._xpath + '/physicalType', 'fan')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testEmpty(self):
        self._db.setValue(self._xpath + '/physicalType', 'empty')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('empty', content['boundaryField'][boundary]['type'])

    def testCyclic(self):
        self._db.setValue(self._xpath + '/physicalType', 'cyclic')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('cyclic', content['boundaryField'][boundary]['type'])

    def testWedge(self):
        self._db.setValue(self._xpath + '/physicalType', 'wedge')
        self._db.setValue(self._xpath + '/temperature/profile', 'constant')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('wedge', content['boundaryField'][boundary]['type'])

    # Temperature Profile is spatial distribution
    def testTemperatureSpatialDistribution(self):
        testDir = Path('testTSpatialDistribution')
        csvFile = Path('testTSpatialDistribution/testTSpatial.csv')
        # ToDo: Settings 처리 정리 후 재작성
        os.makedirs(testDir, exist_ok=True)             # 사용자가 Working Directory 선택할 때 이미 존재하는 디렉토리
        project = _Project()
        Project._instance = project                     # MainWindow 생성 전에 Project 객체 생성
        project._fileDB = FileDB(testDir)               # Project.open에서 fileDB 생성
        FileSystem._casePath = FileSystem.makeDir(testDir, FileSystem.CASE_DIRECTORY_NAME)
        FileSystem._constantPath = FileSystem.makeDir(FileSystem.caseRoot(), Directory.CONSTANT_DIRECTORY_NAME)
                                                        # 사용자가 선택한 mesh directory 복사해 올 때 생성됨
        FileSystem._boundaryConditionsPath = FileSystem.makeDir(
            FileSystem._casePath, Directory.BOUNDARY_CONDITIONS_DIRECTORY_NAME)
        FileSystem._systemPath = FileSystem.makeDir(FileSystem._casePath, Directory.SYSTEM_DIRECTORY_NAME)
        FileSystem.initRegionDirs(rname)               # CaseGenerator에서 호출
        with open(csvFile, 'w') as f:
            f.write('0,0,0,1\n0,0,1,2\n')

        pointsFilePath = FileSystem.constantPath(rname) / 'boundaryData' / boundary / 'points_T'
        fieldTableFilePath = FileSystem.constantPath(rname) / 'boundaryData' / boundary / '0/T'

        self._db.setValue(self._xpath + '/temperature/profile', 'spatialDistribution')
        self._db.setValue(self._xpath + '/temperature/spatialDistribution',
                          project.fileDB().putBcFile(self._bcid, BcFileRole.BC_TEMPERATURE, csvFile))
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        self.assertEqual('timeVaryingMappedFixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual('points_T', content['boundaryField'][boundary]['points'])
        self.assertTrue(pointsFilePath.is_file())
        self.assertTrue(fieldTableFilePath.is_file())

        shutil.rmtree(testDir)                          # 테스트 디렉토리 삭제

    # Temperature Profile is temporalDistribution
    def testTemperaturePiecewiseLinear(self):
        self._db.setValue(self._xpath + '/temperature/profile', 'temporalDistribution')
        self._db.setValue(self._xpath + '/temperature/temporalDistribution/specification', 'piecewiseLinear')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        t = self._db.getValue(self._xpath + '/temperature/temporalDistribution/piecewiseLinear/t').split()
        v = self._db.getValue(self._xpath + '/temperature/temporalDistribution/piecewiseLinear/v').split()
        self.assertEqual('uniformFixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual([[t[i], v[i]] for i in range(len(t))], content['boundaryField'][boundary]['uniformValue'][1])

    # Temperature Profile is temporalDistribution
    def testTemperaturePolynomial(self):
        self._db.setValue(self._xpath + '/temperature/profile', 'temporalDistribution')
        self._db.setValue(self._xpath + '/temperature/temporalDistribution/specification', 'polynomial')
        content = T(RegionDB.getRegionProperties(rname), '0', None).build().asDict()
        t = self._db.getValue(self._xpath + '/temperature/temporalDistribution/piecewiseLinear/t').split()
        v = self._db.getValue(self._xpath + '/temperature/temporalDistribution/piecewiseLinear/v').split()
        self.assertEqual('uniformFixedValue', content['boundaryField'][boundary]['type'])
        self.assertEqual([[v[i], i] for i in range(len(v))],
                         content['boundaryField'][boundary]['uniformValue'][1])


if __name__ == '__main__':
    unittest.main()
