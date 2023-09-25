#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baram.coredb import coredb
from baram.coredb.numerical_db import NumericalDB, PressureVelocityCouplingScheme
from baram.coredb.general_db import GeneralDB
from baram.coredb.region_db import RegionDB
from baram.coredb.material_db import Phase
from baram.coredb.models_db import ModelsDB
from baram.coredb.reference_values_db import ReferenceValuesDB
from baram.coredb.material_db import MaterialDB
from baram.openfoam.file_system import FileSystem


class FvSolution(DictionaryFile):
    def __init__(self, rname: str = None):
        """

        Args:
            rname: Region name. None for global fvSolution of multi region case, empty string for single region.
        """
        super().__init__(FileSystem.caseRoot(), self.systemLocation('' if rname is None else rname), 'fvSolution')

        self._rname = rname
        self._db = coredb.CoreDB()

    def build(self):
        if self._data is not None:
            return self

        if self._rname is None:
            # Global fvSolution in multi region case
            self._data = {
                'PIMPLE': {
                    'nOuterCorrectors':
                        self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/maxIterationsPerTimeStep'),
                }

            }

            return self

        # If region name is empty string, the only fvSolution in single region case.
        # Otherwise, fvSolution of specified region.
        scheme = self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/pressureVelocityCouplingScheme')
        phase = RegionDB.getPhase(self._rname)
        consistent = 'no'
        momentumPredictor = 'on'
        energyOn = ModelsDB.isEnergyModelOn()

        if scheme == PressureVelocityCouplingScheme.SIMPLEC.value and phase != Phase.SOLID:
            consistent = 'yes'
        if self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/useMomentumPredictor') == 'false':
            momentumPredictor = 'off'

        self._data = {
            # For multiphase model
            'solvers': {
                '"alpha.*"': {
                    'nAlphaCorr':
                        self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/multiphase/numberOfCorrectors'),
                    'nAlphaSubCycles':
                        self._db.getValue(
                            NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/multiphase/maxIterationsPerTimeStep'),
                    'cAlpha':
                        self._db.getValue(
                            NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/multiphase/phaseInterfaceCompressionFactor'),
                    'icAlpha': 0,
                    'MULESCorr':
                        'yes' if self._db.getValue(
                            NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/multiphase/useSemiImplicitMules') == 'true'
                        else 'no',
                    'nLimiterIter':
                        self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/multiphase/numberOfMulesIterations'),
                    'alphaApplyPrevCorr': 'yes',
                    'solver': 'smoothSolver',
                    'smoother': 'symGaussSeidel',
                    'tolerance': '1e-8',
                    'relTol': 0,
                    'minIter': 1,
                    'maxIter': 10,
                },
                '"(p|pcorr)"': (p := self._constructSolversP()),
                '"(p|pcorr)Final"': p,
                'p_rgh': (p_rgh := {
                    'solver': 'PCG',
                    'preconditioner': {
                        'preconditioner': 'GAMG',
                        'smoother': 'DIC',
                        'tolerance': '1e-5',
                        'relTol': '0.1',
                    },
                    'tolerance': '1e-16',
                    'relTol': '0.1',
                    'minIter': '1',
                    'maxIter': '5',
                }),
                'p_rghFinal': p_rgh,
                'h': (h := self._constructSolversH(phase)),
                'hFinal': h,
                'rho': (rho := {
                    'solver': 'PCG',
                    'preconditioner': 'DIC',
                    'tolerance': '1e-16',
                    'relTol': '0.1',
                    'minIter': '1',
                    'maxIter': '5',
                }),
                'rhoFinal': rho,
                '"(U|k|epsilon|omega|nuTilda)"': (others := {
                    'solver': 'PBiCGStab',
                    'preconditioner': 'DILU',
                    'tolerance': '1e-16',
                    'relTol': '0.1',
                    'minIter': '1',
                    'maxIter': '5',
                }),
                '"(U|k|epsilon|omega|nuTilda)Final"': others
            },
            'SIMPLE': {
                'consistent': consistent,
                'nNonOrthogonalCorrectors': '0',
                # only for fluid
                'pRefPoint': self._db.getVector(
                    ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation'),
                # only for fluid
                'pRefValue': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'),
                'solveEnergy': 'yes' if energyOn else 'no',  # NEXTfoam custom option
                'residualControl': {
                    'p': self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                    'p_rgh': self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                    'U': self._db.getValue('.//convergenceCriteria/momentum/absolute'),
                    'h': self._db.getValue('.//convergenceCriteria/energy/absolute'),
                    '"(k|epsilon|omega|nuTilda)"': self._db.getValue('.//convergenceCriteria/turbulence/absolute'),
                    # For multiphase model
                    '"alpha.*"': self._db.getValue('.//convergenceCriteria/volumeFraction/absolute'),
                }
            },
            'PIMPLE': {
                'consistent': consistent,
                'momentumPredictor': momentumPredictor,
                # only for fluid
                'turbOnFinalIterOnly': 'false',
                'nNonOrthogonalCorrectors': '0',
                # only for fluid
                'nCorrectors': self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/numberOfCorrectors'),
                # only in single region case
                'nOuterCorrectors':
                    self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/maxIterationsPerTimeStep'),
                'maxCo': self._db.getValue('.//runConditions/maxCourantNumber'),
                'nonOrthogonalityThreshold': '80',
                'skewnessThreshold': '0.95',
                # only for fluid
                'pRefPoint': self._db.getVector(
                    ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation'),
                # only for fluid
                'pRefValue': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'),
                'rDeltaTSmoothingCoeff': '0.05',
                'rDeltaTDampingCoeff': '0.5',
                'solveEnergy': 'yes' if energyOn else 'no',  # NEXTfoam custom option
                'residualControl': {
                    'p': {
                        'tolerance': self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                        'relTol': self._db.getValue('.//convergenceCriteria/pressure/relative'),
                    },
                    'p_rgh': {
                        'tolerance': self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                        'relTol': self._db.getValue('.//convergenceCriteria/pressure/relative'),
                    },
                    'U': {
                        'tolerance': self._db.getValue('.//convergenceCriteria/momentum/absolute'),
                        'relTol': self._db.getValue('.//convergenceCriteria/momentum/relative'),
                    },
                    'h': {
                        'tolerance': self._db.getValue('.//convergenceCriteria/energy/absolute'),
                        'relTol': self._db.getValue('.//convergenceCriteria/energy/relative'),
                    },
                    '"(k|epsilon|omega|nuTilda)"': {
                        'tolerance': self._db.getValue('.//convergenceCriteria/turbulence/absolute'),
                        'relTol': self._db.getValue('.//convergenceCriteria/turbulence/relative'),
                    },
                    # For multiphase model
                    '"alpha.*"': {
                        'tolerance': self._db.getValue('.//convergenceCriteria/volumeFraction/absolute'),
                        'relTol': self._db.getValue('.//convergenceCriteria/volumeFraction/relative'),
                    },
                }
            },
            'relaxationFactors': {
                'fields': {
                    'p': self._db.getValue('.//underRelaxationFactors/pressure'),
                    'pFinal': self._db.getValue('.//underRelaxationFactors/pressureFinal'),
                    'p_rgh': self._db.getValue('.//underRelaxationFactors/pressure'),
                    'p_rghFinal': self._db.getValue('.//underRelaxationFactors/pressureFinal'),
                    'rho': self._db.getValue('.//underRelaxationFactors/density'),
                    'rhoFinal': self._db.getValue('.//underRelaxationFactors/densityFinal'),
                },
                'equations': {
                    'U': self._db.getValue('.//underRelaxationFactors/momentum'),
                    'UFinal': self._db.getValue('.//underRelaxationFactors/momentumFinal'),
                    'h': self._db.getValue('.//underRelaxationFactors/energy'),
                    'hFinal': self._db.getValue('.//underRelaxationFactors/energyFinal'),
                    '"(k|epsilon|omega|nuTilda)"': self._db.getValue('.//underRelaxationFactors/turbulence'),
                    '"(k|epsilon|omega|nuTilda)Final"': self._db.getValue('.//underRelaxationFactors/turbulenceFinal'),
                }
            }
        }

        # For multiphase model
        for mid in RegionDB.getSecondaryMaterials(self._rname):
            material = MaterialDB.getName(mid)
            self._data['relaxationFactors']['equations'][f'alpha.{material}'] = self._db.getValue(
                NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/underRelaxationFactors/volumeFraction')
            self._data['relaxationFactors']['equations'][f'alpha.{material}Final'] = self._db.getValue(
                NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/underRelaxationFactors/volumeFraction')

        return self

    def _constructSolversP(self):
        if GeneralDB.isCompressible():
            return {
                'solver': 'PBiCGStab',
                'preconditioner': 'DILU',
                'tolerance': '1e-16',
                'relTol': '0.1',
                'minIter': '1',
                'maxIter': '5',
            }
        else:
            return {
                'solver': 'PCG',
                'preconditioner': {
                    'preconditioner': 'GAMG',
                    'smoother': 'DIC',
                    'tolerance': '1e-5',
                    'relTol': '0.1',
                },
                'tolerance': '1e-16',
                'relTol': '0.1',
                'minIter': '1',
                'maxIter': '5',
            }

    def _constructSolversH(self, phase):
        if phase == Phase.SOLID:
            return {
                'solver': 'PBiCGStab',
                'preconditioner': {
                    'preconditioner': 'GAMG',
                    'smoother': 'DIC',
                    'tolerance': '1e-5',
                    'relTol': '0.1',
                },
                'tolerance': '1e-16',
                'relTol': '0.1',
                'minIter': '1',
                'maxIter': '5',
            }
        else:
            return {
                'solver': 'PBiCGStab',
                'preconditioner': {
                    'preconditioner': 'GAMG',
                    'smoother': 'DILU',
                    'tolerance': '1e-5',
                    'relTol': '0.1',
                },
                'tolerance': '1e-16',
                'relTol': '0.1',
                'minIter': '1',
                'maxIter': '5',
            }
