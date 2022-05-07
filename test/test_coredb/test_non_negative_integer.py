import unittest

from coredb import coredb


class TestNonNegativeInteger(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()
        self.path = './/runConditions/numberOfIterations'

    def testValidInteger(self):
        written = '10'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testValidBigInteger(self):
        written = '100000'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testZero(self):
        written = '0'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testNegativeValue(self):
        written = '-1'
        with self.assertRaises(ValueError) as context:
            self.db.setValue(self.path, written)

    def testMalformedString(self):
        written = '10E'
        with self.assertRaises(ValueError) as context:
            self.db.setValue(self.path, written)


if __name__ == '__main__':
    unittest.main()
