import unittest

from coredb import coredb


class TestContextManager(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()
        self.pathFirst = './/runConditions/numberOfIterations'
        # turbulentIntensity sould be in 0~100
        self.pathSecond = './/initialValues/turbulentIntensity'

    def testValidInteger(self):
        self.db.setValue(self.pathFirst, '10')
        with coredb.CoreDB() as db:
            db.setValue(self.pathFirst, '20')
            db.setValue(self.pathSecond, '101')  # this will get error return

        self.assertEqual('10', self.db.getValue(self.pathFirst))

    def tearDown(self) -> None:
        del coredb.CoreDB._instance


if __name__ == '__main__':
    unittest.main()