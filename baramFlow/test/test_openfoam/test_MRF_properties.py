#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from baramFlow.coredb import coredb
from baramFlow.openfoam.constant.MRF_properties import MRFProperties


class TestMRFProperties(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()

    def tearDown(self) -> None:
        coredb.destroy()

    def testBuild(self):
        rname = 'testRegion_1'
        zone = 'testZone_1'
        self.db.addRegion(rname)
        czid = self.db.addCellZone(rname, zone)
        boundaries = [self.db.addBoundaryCondition(rname, 'boundary1', 'wall'),
                      self.db.addBoundaryCondition(rname, 'boundary2', 'wall')]
        xpath = f'.//cellZones/cellZone[@czid="{czid}"]'
        self.db.setValue(xpath + '/zoneType', 'mrf')
        self.db.setValue(xpath + '/mrf/staticBoundaries', ' '.join([str(b) for b in boundaries]))
        self.db.setValue('.//general/flowType', 'compressible')

        content = MRFProperties(rname).build().asDict()
        patches = [self.db.getValue(f'.//regions/region[name="{rname}"]/boundaryConditions/boundaryCondition[@bcid="{bcid}"]/name')
                   for bcid in boundaries]

        self.assertEqual(patches, content['MRFCellZone_testZone_1']['nonRotatingPatches'])

        self.assertEqual([0.0, 0.0, 0.0], content[f'MRFCellZone_{zone}']['origin'])
        self.assertEqual([1.0, 0.0, 0.0], content[f'MRFCellZone_{zone}']['axis'])
        self.assertEqual(float(self.db.getValue(xpath + '/mrf/rotatingSpeed')) * 2 * 3.141592 / 60, content[f'MRFCellZone_{zone}']['omega'])

if __name__ == '__main__':
    unittest.main()
