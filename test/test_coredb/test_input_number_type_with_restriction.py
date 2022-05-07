import unittest

from coredb import coredb


class TestInputNumberTypeWithRestriction(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()
        self.path = './/initialValues/turbulentIntensity'

    def testValidDecimalNotation(self):
        written = '10'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual('10.0', read)

    def testValidScientificNotation(self):
        written = '1.234E-5'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testUnalignedScientificNotation(self):
        written = '12.345E-6'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testLessThanMinimumValue(self):
        written = '-1'
        with self.assertRaises(ValueError) as context:
            self.db.setValue(self.path, written)

    def testBiggerThanMaximumValue(self):
        written = '101'
        with self.assertRaises(ValueError) as context:
            self.db.setValue(self.path, written)

    def testMalformedString(self):
        written = '10E'
        with self.assertRaises(ValueError) as context:
            self.db.setValue(self.path, written)

    def testNotationChange(self):
        # 1. Write in Scientific Notation
        written = '1.234E1'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

        # 2. Write in Decimal Notation
        written = '78.654321'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

        # 3. Write in Scientific Notation again
        written = '5.678E-1'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)


if __name__ == '__main__':
    unittest.main()
