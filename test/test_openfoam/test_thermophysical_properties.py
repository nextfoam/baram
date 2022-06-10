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

    def testBasicGeneration(self):
        region = 'testRegion_1'
        zone = 'testZone_1'
        self.db.addRegion(region)
        self.db.addCellZone(region, zone)
        content = str(ThermophysicalProperties(region))
        self.assertEqual(_DEF_CONTENT, content)

    def testPolynomialViscosity(self):
        region = 'testRegion_1'
        zone = 'testZone_1'
        viscosityCoeffs = '1.1 2.2 3.3 4.4 5.5'
        conductivityCcoeffs = '6.6 7.7 8.8 9.9'
        self.db.addRegion(region)
        self.db.addCellZone(region, zone)
        self.db.setValue('.//material[name="air"]/thermalConductivity/specification', 'polynomial')
        self.db.setValue('.//material[name="air"]/thermalConductivity/polynomial', conductivityCcoeffs)

        self.db.setValue('.//material[name="air"]/viscosity/specification', 'polynomial')
        self.db.setValue('.//material[name="air"]/viscosity/polynomial', viscosityCoeffs)

        content = ThermophysicalProperties(region).asdict()
        self.assertEqual('polynomial', content['thermoType']['transport'])
        self.assertEqual(viscosityCoeffs, content['mixture']['transport']['muCoeffs'])
        self.assertEqual(conductivityCcoeffs, content['mixture']['transport']['kappaCoeffs'])

    def testSutherlandViscosity(self):
        region = 'testRegion_1'
        zone = 'testZone_1'
        As = '1.1'
        Ts = '2.2'
        self.db.addRegion(region)
        self.db.addCellZone(region, zone)

        self.db.setValue('.//material[name="air"]/viscosity/specification', 'sutherland')
        self.db.setValue('.//material[name="air"]/viscosity/sutherland/coefficient', As)
        self.db.setValue('.//material[name="air"]/viscosity/sutherland/temperature', Ts)

        content = ThermophysicalProperties(region).asdict()
        self.assertEqual('sutherland', content['thermoType']['transport'])
        self.assertEqual(As, content['mixture']['transport']['As'])
        self.assertEqual(Ts, content['mixture']['transport']['Ts'])


if __name__ == '__main__':
    unittest.main()
