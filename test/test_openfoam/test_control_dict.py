import unittest

from coredb import coredb

from openfoam.system.control_dict import ControlDict


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


if __name__ == '__main__':
    unittest.main()
