import unittest

from coredb import coredb
from openfoam.constant.MRF_properties import MRFProperties


class TestMRFProperties(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

    def testBuild(self):
        region = 'testRegion_1'
        zone = 'testZone_1'
        pressure = '0'
        self.db.addRegion(region)
        czid = self.db.addCellZone(region, zone)
        boundaries = [self.db.addBoundaryCondition(region, 'boundary1', 'wall'),
                      self.db.addBoundaryCondition(region, 'boundary2', 'wall')]
        xpath = f'.//cellZones/cellZone[@czid="{czid}"]'
        self.db.setValue(xpath + '/zoneType', 'mrf')
        self.db.setValue(xpath + '/mrf/staticBoundaries', ' '.join([str(b) for b in boundaries]))
        self.db.setValue('.//general/flowType', 'compressible')

        content = MRFProperties(region).build().asDict()
        patches = [self.db.getValue(f'.//regions/region[name="{region}"]/boundaryConditions/boundaryCondition[@bcid="{bcid}"]/name')
                   for bcid in boundaries]

        self.assertEqual(patches, content['MRFCellZone_testZone_1']['nonRotatingPatches'])


if __name__ == '__main__':
    unittest.main()
