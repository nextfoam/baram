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
        error = self.db.setValue(self.path, written)
        self.assertEqual(coredb.Error.OUT_OF_RANGE, error)

    def testMalformedString(self):
        written = '10E'
        error = self.db.setValue(self.path, written)
        self.assertEqual(coredb.Error.INTEGER_ONLY, error)

    def tearDown(self) -> None:
        del coredb.CoreDB._instance


if __name__ == '__main__':
    unittest.main()
