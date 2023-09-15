#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from baram.coredb import coredb

from baram.openfoam.system.decomposePar_dict import DecomposeParDict

class TestDecomposeParDict(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()

        self.region1 = 'testRegion_1'
        self._db.addRegion(self.region1)

    def tearDown(self) -> None:
        coredb.destroy()

    def testNumberOfSubdomains(self):
        self._db.setValue('.//runCalculation/parallel/numberOfCores', '4')
        content = DecomposeParDict(self.region1).build().asDict()
        self.assertEqual('4', content['numberOfSubdomains'])

    def testMethod(self):
        content = DecomposeParDict(self.region1).build().asDict()
        self.assertEqual('scotch', content['method'])


if __name__ == '__main__':
    unittest.main()
