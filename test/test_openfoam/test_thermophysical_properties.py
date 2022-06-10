import unittest

from coredb import coredb
from openfoam.thermophysical_properties import ThermophysicalProperties

_DEF_CONTENT = """FoamFile
{
 version 2.0;
 format ascii;
 class dictionary;
 location constant;
 object thermophysicalProperties;
}

thermoType
{
  type hePsiThermo;
  mixture pureMixture;
  transport const;
  thermo hConst;
  equationOfState rhoConst;
  specie specie;
  energy sensibleEnthalpy;
}
mixture
{
  equationOfState
  {
    rho 1.225;
  }
  thermodynamics
  {
    Cp 1006.0;
    Hf 0;
  }
  transport
  {
    mu 1.79e-05;
    Pr 0.7349959183673469;
  }
  specie
  {
    nMoles 1;
    molWeight 28.966;
  }
}
"""

class TestThermophysicalProperties(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()
        self.path = './/operatingConditions/gravity'

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

    def testGetAttribute(self):
        region = 'testRegion_1'
        zone = 'testZone_1'
        self.db.addRegion(region)
        self.db.addCellZone(region, zone)
        content = str(ThermophysicalProperties(region))
        self.assertEqual(_DEF_CONTENT, content)


if __name__ == '__main__':
    unittest.main()
