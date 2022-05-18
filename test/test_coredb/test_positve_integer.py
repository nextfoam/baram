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
        error = self.db.setValue(self.path, written)
        self.assertEqual(coredb.Error.OUT_OF_RANGE, error)

    def test_negativeValue(self):
        written = '-1'
        error = self.db.setValue(self.path, written)
        self.assertEqual(coredb.Error.OUT_OF_RANGE, error)

    def test_malformedString(self):
        written = '10E'
        error = self.db.setValue(self.path, written)
        self.assertEqual(coredb.Error.INTEGER_ONLY, error)

    def tearDown(self) -> None:
        del coredb.CoreDB._instance


if __name__ == '__main__':
    unittest.main()
