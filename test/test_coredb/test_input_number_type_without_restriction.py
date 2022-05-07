import unittest

from coredb import coredb


class TestInputNumberTypeWithoutRestriction(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()
        self.path = './/initialValues/scaleOfVelocity'

    def testValidDecimalNotation(self):
        written = '10000'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual('10000.0', read)

    def testValidScientificNotation(self):
        written = '1.234E+5'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testUnalignedScientificNotation(self):
        written = '12.345E-6'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

    def testMalformedString(self):
        written = '10000.E'
        with self.assertRaises(ValueError) as context:
            self.db.setValue(self.path, written)

    def testNotationChange(self):
        # 1. Write in Scientific Notation
        written = '1.234E23'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

        # 2. Write in Decimal Notation
        written = '787.654321'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)

        # 3. Write in Scientific Notation again
        written = '5.678E-10'
        self.db.setValue(self.path, written)
        read = self.db.getValue(self.path)
        self.assertEqual(written, read)


if __name__ == '__main__':
    unittest.main()
