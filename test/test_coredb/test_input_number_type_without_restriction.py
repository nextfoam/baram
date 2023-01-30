import unittest

from coredb import coredb


class TestInputNumberTypeWithoutRestriction(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()
        self.db.addRegion('dummyRegion')
        self.path = './/initialValues/scaleOfVelocity'

    def testValidDecimalNotation(self):
        written = '10000'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual('10000', read)

    def testValidScientificNotation(self):
        written = '1.234e+5'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testUnalignedScientificNotation(self):
        written = '12.345e-6'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testBigEScientificNotation(self):
        written = '12.345E-6'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written.lower(), read)

    def testMalformedString(self):
        written = '10000.e'
        error = self.db.setValue(self.path, written)
        self.assertEqual(coredb.Error.FLOAT_ONLY, error)

    def testNotationChange(self):
        # 1. Write in Scientific Notation
        written = '1.234e23'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

        # 2. Write in Decimal Notation
        written = '787.654321'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

        # 3. Write in Scientific Notation again
        written = '5.678e-10'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def tearDown(self) -> None:
        coredb.destroy()


if __name__ == '__main__':
    unittest.main()
