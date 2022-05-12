import unittest

from coredb import coredb


class TestInputNumberListType(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()
        self.db.addMaterial('air')
        self.path = './/material[name="air"]/specificHeat/polynomial'

    def testSingleDecimalNotation(self):
        written = '10000.0'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testSingleScientificNotation(self):
        written = '1.234e23'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testMultipleMixedNotations(self):
        written = '2.345e21 1000.1 5.678e-10 0.001'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testInvalidNotation(self):
        written = '2.345 1.234e 4.567'
        with self.assertRaises(ValueError) as context:
            self.db.setValue(self.path, written)


if __name__ == '__main__':
    unittest.main()
