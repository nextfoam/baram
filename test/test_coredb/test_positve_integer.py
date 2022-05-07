import unittest

from coredb import coredb


class TestPositiveInteger(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()
        self.path = './/runConditions/reportIntervalSteps'

    def test_validInteger(self):
        written = '10'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(read, written)

    def test_validBigInteger(self):
        written = '100000'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(read, written)

    def test_zero(self):
        written = '0'
        with self.assertRaises(ValueError) as context:
            self.db.setValue(self.path, written)

    def test_negativeValue(self):
        written = '-1'
        with self.assertRaises(ValueError) as context:
            self.db.setValue(self.path, written)

    def test_malformedString(self):
        written = '10E'
        with self.assertRaises(ValueError) as context:
            self.db.setValue(self.path, written)

    #def test_turbulentIntensity(self):
        #db.getValue('.//runConditions/timeSteppingMethod')
        #db.getValue('.//runConditions/numberOfIterations') # non negative integer


if __name__ == '__main__':
    unittest.main()
