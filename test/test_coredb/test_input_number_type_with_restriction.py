import unittest

from coredb import coredb


class TestInputNumberTypeWithRestriction(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()
        self.db.addRegion('dummyRegion')
        self.path = './/initialValues/turbulentIntensity'

    def testValidDecimalNotation(self):
        written = '10'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual('10', read)

    def testValidScientificNotation(self):
        written = '1.234e-5'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testUnalignedScientificNotation(self):
        written = '12.345e-6'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testLessThanMinimumValue(self):
        written = '-1'
        error = self.db.setValue(self.path, written)
        self.assertEqual(coredb.Error.OUT_OF_RANGE, error)

    def testBiggerThanMaximumValue(self):
        written = '101'
        error = self.db.setValue(self.path, written)
        self.assertEqual(coredb.Error.OUT_OF_RANGE, error)

    def testBigEScientificNotation(self):
        written = '12.345E-6'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written.lower(), read)

    def testMalformedString(self):
        written = '10E'
        error = self.db.setValue(self.path, written)
        self.assertEqual(coredb.Error.FLOAT_ONLY, error)

    def testNotationChange(self):
        # 1. Write in Scientific Notation
        written = '1.234e1'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

        # 2. Write in Decimal Notation
        written = '78.654321'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

        # 3. Write in Scientific Notation again
        written = '5.678e-1'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def tearDown(self) -> None:
        coredb.destroy()


if __name__ == '__main__':
    unittest.main()
