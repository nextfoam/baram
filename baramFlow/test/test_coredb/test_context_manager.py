import unittest

from baramFlow.coredb import coredb


class TestContextManager(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()
        self.db.addRegion('dummyRegion')
        self.pathFirst = './/runConditions/numberOfIterations'
        # turbulentIntensity should be in 0~100
        self.pathSecond = './/initialValues/turbulentIntensity'

    def tearDown(self) -> None:
        coredb.destroy()

    def testValidInteger(self):
        self.db.setValue(self.pathFirst, '10')
        with coredb.CoreDB() as db:
            db.setValue(self.pathFirst, '20')
            db.setValue(self.pathSecond, '101')  # this will get error return

        self.assertEqual('10', self.db.getValue(self.pathFirst))

    def testException(self):
        self.db.setValue(self.pathFirst, '10')
        with self.assertRaises(UserWarning):
            with coredb.CoreDB() as db:
                db.setValue(self.pathFirst, '20')
                raise UserWarning

        self.assertEqual('10', self.db.getValue(self.pathFirst))

    def testCancel(self):
        self.db.setValue(self.pathFirst, '10')
        with coredb.CoreDB() as db:
            db.setValue(self.pathFirst, '30')
            raise coredb.Cancel

        self.assertEqual('10', self.db.getValue(self.pathFirst))


if __name__ == '__main__':
    unittest.main()
