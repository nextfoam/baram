import unittest

from baramFlow.coredb import coredb
from baramFlow.coredb.monitor_db import MonitorDB, Field
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType
from baramFlow.openfoam.function_objects.surface_field_value import SurfaceReportType
from baramFlow.coredb.reference_values_db import ReferenceValuesDB
from baramFlow.openfoam.system.control_dict import ControlDict

rname = 'testRegion_1'
boundary = 'testBoundary_1'
cellZone = 'testCellZone_1'


class TestSolver(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()

    def tearDown(self) -> None:
        coredb.destroy()

    def testTransientFixedTimeStep(self):
        self._db.setValue('.//general/timeTransient', 'true')
        self._db.setValue('.//runConditions/timeSteppingMethod', 'fixed')

        content = ControlDict().build().asDict()

        self.assertEqual(self._db.getValue('.//runConditions/endTime'), content['endTime'])
        self.assertEqual(self._db.getValue('.//runConditions/timeStepSize'), content['deltaT'])
        self.assertEqual('runTime', content['writeControl'])
        self.assertEqual(self._db.getValue('.//runConditions/reportIntervalSeconds'), content['writeInterval'])
        self.assertEqual('no', content['adjustTimeStep'])
        self.assertEqual(self._db.getValue('.//runConditions/maxCourantNumber'), content['maxCo'])

    def testTransientAdaptiveTimeStep(self):
        self._db.setValue('.//general/timeTransient', 'true')
        self._db.setValue('.//runConditions/timeSteppingMethod', 'adaptive')

        content = ControlDict().build().asDict()

        self.assertEqual(self._db.getValue('.//runConditions/endTime'), content['endTime'])
        self.assertEqual(0.001, content['deltaT'])
        self.assertEqual('adjustableRunTime', content['writeControl'])
        self.assertEqual(self._db.getValue('.//runConditions/reportIntervalSeconds'), content['writeInterval'])
        self.assertEqual('yes', content['adjustTimeStep'])

    def testSteady(self):
        self._db.setValue('.//general/timeTransient', 'false')
        self._db.setValue('.//runConditions/retainOnlyTheMostRecentFiles', 'false')

        content = ControlDict().build().asDict()

        self.assertEqual(self._db.getValue('.//runConditions/numberOfIterations'), content['endTime'])
        self.assertEqual(1, content['deltaT'])
        self.assertEqual('runTime', content['writeControl'])
        self.assertEqual(self._db.getValue('.//runConditions/reportIntervalSteps'), content['writeInterval'])
        self.assertEqual(0, content['purgeWrite'])
        self.assertEqual(self._db.getValue('.//runConditions/dataWriteFormat'), content['writeFormat'])
        self.assertEqual(self._db.getValue('.//runConditions/dataWritePrecision'), content['writePrecision'])
        self.assertEqual(self._db.getValue('.//runConditions/timePrecision'), content['timePrecision'])

    def testPurgeWrite(self):
        self._db.setValue('.//runConditions/retainOnlyTheMostRecentFiles', 'true')

        content = ControlDict().build().asDict()

        self.assertEqual(self._db.getValue('.//runConditions/maximumNumberOfDataFiles'), content['purgeWrite'])

    def testForceMonitor(self):
        self._db.addRegion('')
        bcid = self._db.addBoundaryCondition('', boundary, 'wall')
        name = self._db.addForceMonitor()
        xpath = MonitorDB.getForceMonitorXPath(name)
        self._db.setValue(xpath + '/boundaries', str(bcid))
        self._db.setValue(xpath + '/region', '')

        content = ControlDict().build().asDict()
        forcesName = name + '_forces'

        self.assertEqual('forces', content['functions'][forcesName]['type'])
        self.assertEqual('"libforces.so"', content['functions'][forcesName]['libs'][0])
        self.assertEqual(boundary, content['functions'][forcesName]['patches'][0])
        self.assertEqual('timeStep', content['functions'][forcesName]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][forcesName]['writeInterval'])

        self.assertEqual('forceCoeffs', content['functions'][name]['type'])
        self.assertEqual('"libforces.so"', content['functions'][name]['libs'][0])
        self.assertEqual(boundary, content['functions'][name]['patches'][0])
        self.assertEqual('rhoInf', content['functions'][name]['rho'])
        self.assertEqual(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/area'),
                         content['functions'][name]['Aref'])
        self.assertEqual(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/length'),
                         content['functions'][name]['lRef'])
        self.assertEqual(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/velocity'),
                         content['functions'][name]['magUInf'])
        self.assertEqual(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/density'),
                         content['functions'][name]['rhoInf'])
        self.assertEqual(self._db.getVector(xpath + '/dragDirection'), content['functions'][name]['dragDir'])
        self.assertEqual(self._db.getVector(xpath + '/liftDirection'), content['functions'][name]['liftDir'])
        self.assertEqual(self._db.getVector(xpath + '/centerOfRotation'), content['functions'][name]['CofR'])
        self.assertEqual('timeStep', content['functions'][name]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][name]['writeInterval'])

    def testForceMonitorMultiRegion(self):
        self._db.addRegion(rname)
        bcid = self._db.addBoundaryCondition(rname, boundary, 'wall')
        name = self._db.addForceMonitor()
        xpath = MonitorDB.getForceMonitorXPath(name)
        self._db.setValue(xpath + '/boundaries', str(bcid))
        self._db.setValue(xpath + '/region', rname)

        content = ControlDict().build().asDict()
        forcesName = name + '_forces'

        self.assertEqual('forces', content['functions'][forcesName]['type'])
        self.assertEqual('"libforces.so"', content['functions'][forcesName]['libs'][0])
        self.assertEqual(boundary, content['functions'][forcesName]['patches'][0])
        self.assertEqual('timeStep', content['functions'][forcesName]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][forcesName]['writeInterval'])
        self.assertEqual(rname, content['functions'][forcesName]['region'])

        self.assertEqual('forceCoeffs', content['functions'][name]['type'])
        self.assertEqual('"libforces.so"', content['functions'][name]['libs'][0])
        self.assertEqual(boundary, content['functions'][name]['patches'][0])
        self.assertEqual('rhoInf', content['functions'][name]['rho'])
        self.assertEqual(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/area'),
                         content['functions'][name]['Aref'])
        self.assertEqual(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/length'),
                         content['functions'][name]['lRef'])
        self.assertEqual(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/velocity'),
                         content['functions'][name]['magUInf'])
        self.assertEqual(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/density'),
                         content['functions'][name]['rhoInf'])
        self.assertEqual(self._db.getVector(xpath + '/dragDirection'), content['functions'][name]['dragDir'])
        self.assertEqual(self._db.getVector(xpath + '/liftDirection'), content['functions'][name]['liftDir'])
        self.assertEqual(self._db.getVector(xpath + '/centerOfRotation'), content['functions'][name]['CofR'])
        self.assertEqual(rname, content['functions'][name]['region'])
        self.assertEqual('timeStep', content['functions'][name]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][name]['writeInterval'])

    def testPointMonitor(self):
        name = self._db.addPointMonitor()
        xpath = MonitorDB.getPointMonitorXPath(name)
        self._db.setValue(xpath + '/field/field', Field.PRESSURE.value)

        content = ControlDict().build().asDict()

        self.assertEqual('probes', content['functions'][name]['type'])
        self.assertEqual('"libsampling.so"', content['functions'][name]['libs'][0])
        self.assertEqual('p', content['functions'][name]['fields'][0])
        self.assertEqual(self._db.getVector(xpath + '/coordinate'), content['functions'][name]['probeLocations'][0])
        self.assertEqual('timeStep', content['functions'][name]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][name]['writeInterval'])

    def testPointMonitorSnapOntoBoundary(self):
        self._db.addRegion('')
        bcid = self._db.addBoundaryCondition('', boundary, 'wall')
        name = self._db.addPointMonitor()
        xpath = MonitorDB.getPointMonitorXPath(name)
        self._db.setValue(xpath + '/field/field', Field.SPEED.value)
        self._db.setValue(xpath + '/snapOntoBoundary', 'true')
        self._db.setValue(xpath + '/boundary', str(bcid))

        content = ControlDict().build().asDict()

        self.assertEqual('patchProbes', content['functions'][name]['type'])
        self.assertEqual('"libsampling.so"', content['functions'][name]['libs'][0])
        self.assertEqual(boundary, content['functions'][name]['patches'][0])
        self.assertEqual('mag(U)', content['functions'][name]['fields'][0])
        self.assertEqual(self._db.getVector(xpath + '/coordinate'), content['functions'][name]['probeLocations'][0])
        self.assertEqual('timeStep', content['functions'][name]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][name]['writeInterval'])

        self.assertEqual('mag', content['functions']['mag1']['type'])
        self.assertEqual('fieldFunctionObjects', content['functions']['mag1']['libs'][0])
        self.assertEqual('"U"', content['functions']['mag1']['field'])
        self.assertEqual('true', content['functions']['mag1']['enabled'])
        self.assertEqual('false', content['functions']['mag1']['log'])
        self.assertEqual('timeStep', content['functions']['mag1']['executeControl'])
        self.assertEqual(1, content['functions']['mag1']['executeInterval'])
        self.assertEqual('none', content['functions']['mag1']['writeControl'])

    def testPointMaterialMonitor(self):
        mid = self._db.addMaterial('water-liquid')
        name = self._db.addPointMonitor()
        xpath = MonitorDB.getPointMonitorXPath(name)
        self._db.setValue(xpath + '/field/field', Field.MATERIAL.value)
        self._db.setValue(xpath + '/field/mid', str(mid))

        self._db.setValue('.//models/multiphaseModels/model', 'volumeOfFluid')

        content = ControlDict().build().asDict()

        self.assertEqual('probes', content['functions'][name]['type'])
        self.assertEqual('"libsampling.so"', content['functions'][name]['libs'][0])
        self.assertEqual('alpha.water-liquid', content['functions'][name]['fields'][0])
        self.assertEqual(self._db.getVector(xpath + '/coordinate'), content['functions'][name]['probeLocations'][0])
        self.assertEqual('timeStep', content['functions'][name]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][name]['writeInterval'])

    def testSurfaceMonitor(self):
        self._db.addRegion(rname)
        bcid = self._db.addBoundaryCondition(rname, boundary, 'wall')
        name = self._db.addSurfaceMonitor()
        xpath = MonitorDB.getSurfaceMonitorXPath(name)
        self._db.setValue(xpath + '/reportType', SurfaceReportType.AREA_WEIGHTED_AVERAGE.value)
        self._db.setValue(xpath + '/field/field', Field.X_VELOCITY.value)
        self._db.setValue(xpath + '/surface', str(bcid))

        content = ControlDict().build().asDict()

        self.assertEqual('surfaceFieldValue', content['functions'][name]['type'])
        self.assertEqual('"libfieldFunctionObjects.so"', content['functions'][name]['libs'][0])
        self.assertEqual('patch', content['functions'][name]['regionType'])
        self.assertEqual(boundary, content['functions'][name]['name'])
        self.assertEqual('none', content['functions'][name]['surfaceFormat'])
        self.assertEqual('Ux', content['functions'][name]['fields'][0])
        self.assertEqual('areaAverage', content['functions'][name]['operation'])
        self.assertEqual(rname, content['functions'][name]['region'])
        self.assertEqual('false', content['functions'][name]['writeFields'])
        self.assertEqual('timeStep', content['functions'][name]['executeControl'])
        self.assertEqual(1, content['functions'][name]['executeInterval'])
        self.assertEqual('timeStep', content['functions'][name]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][name]['writeInterval'])

        self.assertEqual('components', content['functions']['components1']['type'])
        self.assertEqual('fieldFunctionObjects', content['functions']['components1']['libs'][0])
        self.assertEqual('"U"', content['functions']['components1']['field'])
        self.assertEqual('true', content['functions']['components1']['enabled'])
        self.assertEqual('false', content['functions']['components1']['log'])
        self.assertEqual('timeStep', content['functions']['components1']['executeControl'])
        self.assertEqual(1, content['functions']['components1']['executeInterval'])
        self.assertEqual('none', content['functions']['components1']['writeControl'])

    def testSurfaceMonitorMassWeightedAverage(self):
        self._db.addRegion('')
        bcid = self._db.addBoundaryCondition('', boundary, 'wall')
        name = self._db.addSurfaceMonitor()
        xpath = MonitorDB.getSurfaceMonitorXPath(name)
        self._db.setValue(xpath + '/reportType', SurfaceReportType.MASS_WEIGHTED_AVERAGE.value)
        self._db.setValue(xpath + '/field/field', Field.TURBULENT_KINETIC_ENERGY.value)
        self._db.setValue(xpath + '/surface', str(bcid))

        content = ControlDict().build().asDict()

        self.assertEqual('surfaceFieldValue', content['functions'][name]['type'])
        self.assertEqual('"libfieldFunctionObjects.so"', content['functions'][name]['libs'][0])
        self.assertEqual('patch', content['functions'][name]['regionType'])
        self.assertEqual(boundary, content['functions'][name]['name'])
        self.assertEqual('none', content['functions'][name]['surfaceFormat'])
        self.assertEqual('k', content['functions'][name]['fields'][0])
        self.assertEqual('average', content['functions'][name]['operation'])
        self.assertEqual('phi', content['functions'][name]['weightField'])
        self.assertEqual('false', content['functions'][name]['writeFields'])
        self.assertEqual('timeStep', content['functions'][name]['executeControl'])
        self.assertEqual(1, content['functions'][name]['executeInterval'])
        self.assertEqual('timeStep', content['functions'][name]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][name]['writeInterval'])

    def testSurfaceMonitorMassFlowRate(self):
        self._db.addRegion(rname)
        bcid = self._db.addBoundaryCondition(rname, boundary, 'wall')
        name = self._db.addSurfaceMonitor()
        xpath = MonitorDB.getSurfaceMonitorXPath(name)
        self._db.setValue(xpath + '/reportType', SurfaceReportType.MASS_FLOW_RATE.value)
        self._db.setValue(xpath + '/surface', str(bcid))

        content = ControlDict().build().asDict()

        self.assertEqual('surfaceFieldValue', content['functions'][name]['type'])
        self.assertEqual('"libfieldFunctionObjects.so"', content['functions'][name]['libs'][0])
        self.assertEqual('patch', content['functions'][name]['regionType'])
        self.assertEqual(boundary, content['functions'][name]['name'])
        self.assertEqual('none', content['functions'][name]['surfaceFormat'])
        self.assertEqual('phi', content['functions'][name]['fields'][0])
        self.assertEqual('sum', content['functions'][name]['operation'])
        self.assertEqual(rname, content['functions'][name]['region'])
        self.assertEqual('false', content['functions'][name]['writeFields'])
        self.assertEqual('timeStep', content['functions'][name]['executeControl'])
        self.assertEqual(1, content['functions'][name]['executeInterval'])
        self.assertEqual('timeStep', content['functions'][name]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][name]['writeInterval'])

    def testSurfaceMonitorVolumeFlowRate(self):
        self._db.addRegion('')
        bcid = self._db.addBoundaryCondition('', boundary, 'wall')
        name = self._db.addSurfaceMonitor()
        xpath = MonitorDB.getSurfaceMonitorXPath(name)
        self._db.setValue(xpath + '/reportType', SurfaceReportType.VOLUME_FLOW_RATE.value)
        self._db.setValue(xpath + '/surface', str(bcid))

        content = ControlDict().build().asDict()

        self.assertEqual('surfaceFieldValue', content['functions'][name]['type'])
        self.assertEqual('"libfieldFunctionObjects.so"', content['functions'][name]['libs'][0])
        self.assertEqual('patch', content['functions'][name]['regionType'])
        self.assertEqual(boundary, content['functions'][name]['name'])
        self.assertEqual('none', content['functions'][name]['surfaceFormat'])
        self.assertEqual('U', content['functions'][name]['fields'][0])
        self.assertEqual('areaNormalIntegrate', content['functions'][name]['operation'])
        self.assertEqual('false', content['functions'][name]['writeFields'])
        self.assertEqual('timeStep', content['functions'][name]['executeControl'])
        self.assertEqual(1, content['functions'][name]['executeInterval'])
        self.assertEqual('timeStep', content['functions'][name]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][name]['writeInterval'])

    def testVolumeMonitorAll(self):
        self._db.addRegion(rname)
        name = self._db.addVolumeMonitor()
        xpath = MonitorDB.getVolumeMonitorXPath(name)
        self._db.setValue(xpath + '/reportType', VolumeReportType.VOLUME_AVERAGE.value)
        self._db.setValue(xpath + '/field/field', Field.TURBULENT_DISSIPATION_RATE.value)
        self._db.setValue(xpath + '/volume', '1')     # 'All' of the first region

        content = ControlDict().build().asDict()

        self.assertEqual('volFieldValue', content['functions'][name]['type'])
        self.assertEqual('"libfieldFunctionObjects.so"', content['functions'][name]['libs'][0])
        self.assertEqual('epsilon', content['functions'][name]['fields'][0])
        self.assertEqual('volAverage', content['functions'][name]['operation'])
        self.assertEqual('all', content['functions'][name]['regionType'])
        self.assertEqual(rname, content['functions'][name]['region'])
        self.assertEqual('false', content['functions'][name]['writeFields'])
        self.assertEqual('timeStep', content['functions'][name]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][name]['writeInterval'])

    def testVolumeMonitorCellZone(self):
        self._db.addRegion('')
        czid = self._db.addCellZone('', cellZone)
        name = self._db.addVolumeMonitor()
        xpath = MonitorDB.getVolumeMonitorXPath(name)
        self._db.setValue(xpath + '/reportType', VolumeReportType.VOLUME_INTEGRAL.value)
        self._db.setValue(xpath + '/field/field', Field.SPECIFIC_DISSIPATION_RATE.value)
        self._db.setValue(xpath + '/volume', str(czid))

        content = ControlDict().build().asDict()

        self.assertEqual('volFieldValue', content['functions'][name]['type'])
        self.assertEqual('"libfieldFunctionObjects.so"', content['functions'][name]['libs'][0])
        self.assertEqual('omega', content['functions'][name]['fields'][0])
        self.assertEqual('volIntegrate', content['functions'][name]['operation'])
        self.assertEqual('cellZone', content['functions'][name]['regionType'])
        self.assertEqual(cellZone, content['functions'][name]['name'])
        self.assertEqual('false', content['functions'][name]['writeFields'])
        self.assertEqual('timeStep', content['functions'][name]['writeControl'])
        self.assertEqual(self._db.getValue(xpath + '/writeInterval'), content['functions'][name]['writeInterval'])


if __name__ == '__main__':
    unittest.main()
