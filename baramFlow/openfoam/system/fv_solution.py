#!/usr/bin/env python
# -*- coding: utf-8 -*-
from baramFlow.coredb.region_db import RegionDB
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.numerical_db import NumericalDB, PressureVelocityCouplingScheme
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.reference_values_db import ReferenceValuesDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.openfoam.file_system import FileSystem


class FvSolution(DictionaryFile):
    def __init__(self, rname: str = None):
        """

        Args:
            rname: Region name. None for global fvSolution of multi region case, empty string for single region.
        """
        super().__init__(FileSystem.caseRoot(), self.systemLocation('' if rname is None else rname), 'fvSolution')

        self._db = CoreDBReader()

        self._region = None
        self._species = None

        if rname is not None:
            self._region = self._db.getRegionProperties(rname)
            self._species = MaterialDB.getSpecies(RegionDB.getMaterial(rname))

    def build(self):
        if self._data is not None:
            return self

        if self._region is None:
            # Global fvSolution in multi region case
            self._data = {
                'PIMPLE': {
                    'nOuterCorrectors':
                        self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/maxIterationsPerTimeStep'),
                }

            }

            return self

        underRelaxaitionFactorsXPath = NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/underRelaxationFactors'

        # If region name is empty string, the only fvSolution in single region case.
        # Otherwise, fvSolution of specified region.
        scheme = self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/pressureVelocityCouplingScheme')
        consistent = 'no'
        momentumPredictor = 'on'
        energyOn = ModelsDB.isEnergyModelOn()

        if scheme == PressureVelocityCouplingScheme.SIMPLEC.value and self._region.isFluid():
            consistent = 'yes'
        if self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/useMomentumPredictor') == 'false':
            momentumPredictor = 'off'

        solveFlow = self._boolToYN(self._db.getBool(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced/equations/flow'))
        solveEnergy = self._boolToYN(
            energyOn
            and self._db.getAttribute(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced/equations/energy', 'disabled') == 'false')

        solveSpecies = self._boolToYN(
            ModelsDB.isSpeciesModelOn()
            and self._db.getBool(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/advanced/equations/species'))

        scalarFields = [name for _, name in self._db.getUserDefinedScalars()]
        if len(scalarFields) > 0:
            scalarFieldNames = '|' + '|'.join(scalarFields)
        else:
            scalarFieldNames = ''

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
                'h': (h := self._constructSolversH()),
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
                f'"(U|k|epsilon|omega|nuTilda|scalar|Yi{scalarFieldNames})"': (others := {
                    'solver': 'PBiCGStab',
                    'preconditioner': 'DILU',
                    'tolerance': '1e-16',
                    'relTol': '0.1',
                    'minIter': '1',
                    'maxIter': '5',
                }),
                f'"(U|k|epsilon|omega|nuTilda|scalar|Yi{scalarFieldNames})Final"': others,
                'age': {  # no "ageFinal" because "age" supports only steady case
                    'solver': 'PBiCGStab',
                    'preconditioner': 'DILU',
                    'tolerance': '1e-16',
                    'relTol': '0.1',
                    'minIter': '1',
                    'maxIter': '5',
                },
            },
            'SIMPLE': {
                'consistent': consistent,
                'nNonOrthogonalCorrectors':
                    self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/numberOfNonOrthogonalCorrectors'),
                # only for fluid
                # 'pRefPoint': self._db.getVector(
                #     ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation'),
                'pRefCell': 0,
                # only for fluid
                'pRefValue': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'),
                'solveFlow': solveFlow,
                'solveEnergy': solveEnergy,  # NEXTfoam custom option
                'solveSpecies':  solveSpecies,
                'residualControl': {
                    'p': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/pressure/absolute'),
                    'p_rgh': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/pressure/absolute'),
                    'U': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/momentum/absolute'),
                    'h': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/energy/absolute'),
                    '"(k|epsilon|omega|nuTilda)"':
                        self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/turbulence/absolute'),
                    # For multiphase model
                    '"alpha.*"': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/volumeFraction/absolute'),
                    **{
                        specie: self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/species/absolute')
                        for specie in self._species.values()
                    }
                }
            },
            'PIMPLE': {
                'consistent': consistent,
                'momentumPredictor': momentumPredictor,
                # only for fluid
                'turbOnFinalIterOnly': 'false',
                'nNonOrthogonalCorrectors':
                    self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/numberOfNonOrthogonalCorrectors'),
                # only for fluid
                'nCorrectors': self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/numberOfCorrectors'),
                # only in single region case
                'nOuterCorrectors':
                    self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/maxIterationsPerTimeStep'),
                'nAlphaSpreadIter': 0,
                'nAlphaSweepIter': 0,
                'maxCo': self._db.getValue('/runCalculation/runConditions/maxCourantNumber'),
                'maxAlphaCo': self._db.getValue('/runCalculation/runConditions/VoFMaxCourantNumber'),
                'nonOrthogonalityThreshold': '80',
                'skewnessThreshold': '0.95',
                # only for fluid
                # 'pRefPoint': self._db.getVector(
                #     ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation'),
                'pRefCell': 0,
                # only for fluid
                'pRefValue': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'),
                'rDeltaTSmoothingCoeff': '0.5',
                'rDeltaTDampingCoeff': '0.5',
                'solveFlow': solveFlow,
                'solveEnergy': solveEnergy,  # NEXTfoam custom option
                'solveSpecies':  solveSpecies,
                'residualControl': {
                    'p': {
                        'tolerance': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/pressure/absolute'),
                        'relTol': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/pressure/relative'),
                    },
                    'p_rgh': {
                        'tolerance': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/pressure/absolute'),
                        'relTol': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/pressure/relative'),
                    },
                    'U': {
                        'tolerance': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/momentum/absolute'),
                        'relTol': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/momentum/relative'),
                    },
                    'h': {
                        'tolerance': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/energy/absolute'),
                        'relTol': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/energy/relative'),
                    },
                    '"(k|epsilon|omega|nuTilda)"': {
                        'tolerance': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/turbulence/absolute'),
                        'relTol': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/turbulence/relative'),
                    },
                    # For multiphase model
                    '"alpha.*"': {
                        'tolerance': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/volumeFraction/absolute'),
                        'relTol': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/volumeFraction/relative'),
                    },
                    **{
                        specie: {
                            'tolerance': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/species/absolute'),
                            'relTol': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/species/absolute')
                        }
                        for specie in self._species.values()
                    }
                }
            },
            'relaxationFactors': {
                'fields': {
                    'p': self._db.getValue(underRelaxaitionFactorsXPath + '/pressure'),
                    'pFinal': self._db.getValue(underRelaxaitionFactorsXPath + '/pressureFinal'),
                    'p_rgh': self._db.getValue(underRelaxaitionFactorsXPath + '/pressure'),
                    'p_rghFinal': self._db.getValue(underRelaxaitionFactorsXPath + '/pressureFinal'),
                    'rho': self._db.getValue(underRelaxaitionFactorsXPath + '/density'),
                    'rhoFinal': self._db.getValue(underRelaxaitionFactorsXPath + '/densityFinal'),
                },
                'equations': {
                    'U': self._db.getValue(underRelaxaitionFactorsXPath + '/momentum'),
                    'UFinal': self._db.getValue(underRelaxaitionFactorsXPath + '/momentumFinal'),
                    'h': 1 if self._region.isSolid() else self._db.getValue(underRelaxaitionFactorsXPath + '/energy'),
                    'hFinal':
                        1 if self._region.isSolid() else self._db.getValue(underRelaxaitionFactorsXPath + '/energyFinal'),
                    '"(k|epsilon|omega|nuTilda)"':
                        self._db.getValue(underRelaxaitionFactorsXPath + '/turbulence'),
                    '"(k|epsilon|omega|nuTilda)Final"':
                        self._db.getValue(underRelaxaitionFactorsXPath + '/turbulenceFinal'),
                    **{
                        specie: self._db.getValue(underRelaxaitionFactorsXPath + '/species')
                        for specie in self._species.values()
                    },
                    **{
                        f'{specie}Final': self._db.getValue(underRelaxaitionFactorsXPath + '/speciesFinal')
                        for specie in self._species.values()
                    }
                }
            },
            'LU-SGS': self._constructTransientSGS() if GeneralDB.isTimeTransient() else self._constructSteadySGS(),
            'Riemann': {
                'fluxScheme': self._db.getValue(
                    NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/densityBasedSolverParameters/fluxType'),
                'secondOrder':
                    'yes'
                    if self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/discretizationSchemes/momentum')
                       == 'secondOrderUpwind'
                    else 'no',
                'reconGradScheme': 'VKLimited Gauss linear 1',
                'roeFluxCoeffs': {
                    'epsilon': self._db.getValue(
                        NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/densityBasedSolverParameters/entropyFixCoefficient')
                },
                'AUSMplusUpFluxCoeffs': {
                    'MInf': self._db.getValue(
                        NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/densityBasedSolverParameters/cutOffMachNumber'),
                }
            },
            'fieldBounds': {
                'p': '1e-06 1e+10',
                'rho': '1e-06 1e+10',
                'h': '1e-06 1e+10',
                'e': '1e-06 1e+10',
                'rhoE': '1e-06 1e+10',
                'T': '1e-06 3e+4',
                'U': '3e+4',
            }
        }

        # For multiphase model
        for mid in self._region.secondaryMaterials:
            material = MaterialDB.getName(mid)
            self._data['relaxationFactors']['equations'][f'alpha.{material}'] = self._db.getValue(
                underRelaxaitionFactorsXPath + '/volumeFraction')
            self._data['relaxationFactors']['equations'][f'alpha.{material}Final'] = self._db.getValue(
                underRelaxaitionFactorsXPath + '/volumeFractionFinal')

        absolute = self._db.getValue(f'{NumericalDB.NUMERICAL_CONDITIONS_XPATH}/convergenceCriteria/scalar/absolute')
        relative = self._db.getValue(f'{NumericalDB.NUMERICAL_CONDITIONS_XPATH}/convergenceCriteria/scalar/relative')
        self._data['SIMPLE']['residualControl']['scalar'] = absolute
        self._data['PIMPLE']['residualControl']['scalar'] = {
            'tolerance': absolute,
            'relTol': relative
        }

        self._data['relaxationFactors']['equations']['scalar'] = self._db.getValue(
            underRelaxaitionFactorsXPath + '/scalar')
        self._data['relaxationFactors']['equations']['scalarFinal'] = self._db.getValue(
            underRelaxaitionFactorsXPath + '/scalarFinal')

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

    def _constructSolversH(self):
        if self._region.isSolid():
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

    def _constructTransientSGS(self):
        return {
            'residualControl': {
                'rho': {
                    'tolerance': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/density/absolute'),
                    'relTol': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/density/relative'),
                },
                'rhoU': {
                    'tolerance': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/momentum/absolute'),
                    'relTol': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/momentum/relative'),
                },
                'rhoE': {
                    'tolerance': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/energy/absolute'),
                    'relTol': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/energy/relative'),
                },
                '"(k|epsilon|omega|nuTilda)"': {
                    'tolerance': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/turbulence/absolute'),
                    'relTol': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/turbulence/relative'),
                }
            },
            'nPseudoTimeIterations': self._db.getValue(
                NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/maxIterationsPerTimeStep')
        }

    def _constructSteadySGS(self):
        return {
            'residualControl': {
                'rho': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/density/absolute'),
                'rhoU': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/momentum/absolute'),
                'rhoE': self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/energy/absolute'),
                '"(k|epsilon|omega|nuTilda)"':
                    self._db.getValue(NumericalDB.CONVERGENCE_CRITERIA_XPATH + '/turbulence/absolute'),
            }
        }
