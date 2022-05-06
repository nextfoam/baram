import unittest

from coredb import coredb


class MyTestCase(unittest.TestCase):
    def test_something(self):
        db = coredb.CoreDB()
        #db.getValue('.//materials/material/name')
        db.getValue('.//materials/material/phase')
        #db.getValue('.//runConditions/timeSteppingMethod')
        #db.getValue('.//initialValues/turbulentIntensity')
        #db.getValue('.//initialValues/scaleOfVelocity')

        self.assertEqual(True, False)  # add assertion here


if __name__ == '__main__':
    unittest.main()
