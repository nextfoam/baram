#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.numerical_db import PressureVelocityCouplingScheme, Formulation, FluxType
from baramFlow.coredb.numerical_db import ImplicitDiscretizationScheme, UpwindDiscretizationScheme, InterpolationScheme
from baramFlow.coredb.numerical_db import NumericalDB
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel
from baramFlow.openfoam.solver import findSolver, getSolverCapability
from baramFlow.view.widgets.content_page import ContentPage
from .numerical_conditions_page_ui import Ui_NumericalConditionsPage
from .advanced_dialog import AdvancedDialog


class NumericalConditionsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_NumericalConditionsPage()
        self._ui.setupUi(self)

        self._scalarUnderRelazationFactors = {}
        self._scalarConvergenceCriterias = {}

        self._xpath = NumericalDB.NUMERICAL_CONDITIONS_XPATH
        self._db = coredb.CoreDB()
        self._dialog = None

        upwindDiscretizationSchemes = {
            UpwindDiscretizationScheme.FIRST_ORDER_UPWIND: self.tr('First Order Upwind'),
            UpwindDiscretizationScheme.SECOND_ORDER_UPWIND: self.tr('Second Order Upwind'),
        }

        self._ui.pressureVelocityCouplingScheme.addEnumItems({
            PressureVelocityCouplingScheme.SIMPLE: self.tr('SIMPLE'),
            PressureVelocityCouplingScheme.SIMPLEC: self.tr('SIMPLEC'),
        })
        self._ui.formulation.addEnumItems({
            Formulation.IMPLICIT: self.tr('Implicit'),
            # Formulation.EXPLICIT: self.tr('Explicit'),
        })
        self._ui.fluxType.addEnumItems({
            FluxType.ROE_FDS: self.tr('Roe-FDS'),
            FluxType.AUSM: self.tr('ASUM'),
            FluxType.AUSM_UP: self.tr('ASUM-up'),
        })
        self._ui.discretizationSchemeTime.addEnumItems({
            ImplicitDiscretizationScheme.FIRST_ORDER_IMPLICIT: self.tr('First Order Implicit'),
            ImplicitDiscretizationScheme.SECOND_ORDER_IMPLICIT: self.tr('Second Order Implicit'),
        })
        self._ui.discretizationSchemeMomentum.addEnumItems(upwindDiscretizationSchemes)
        self._ui.discretizationSchemeEnergy.addEnumItems(upwindDiscretizationSchemes)
        self._ui.discretizationSchemeTurbulence.addEnumItems(upwindDiscretizationSchemes)
        self._ui.discretizationSchemeVolumeFraction.addEnumItems(upwindDiscretizationSchemes)
        self._ui.discretizationSchemePressure.addEnumItems({
            InterpolationScheme.LINEAR: self.tr('Linear'),
            InterpolationScheme.MOMENTUM_WEIGHTED_RECONSTRUC: self.tr('Momentum Weighted Reconstruct'),
            InterpolationScheme.MOMENTUM_WEIGHTED: self.tr('Momentum Weighted'),
        })

        self._ui.discretizationSchemeScalar.addEnumItems(upwindDiscretizationSchemes)
        #
        # for scalarID, fieldName in self._db.getUserDefinedScalars():
        #     xpath = f'{self._xpath}/underRelaxationFactors/userDefinedScalars/scalar[scalarID="{scalarID}"]'
        #     if not self._db.exists(xpath):
        #         NumericalDB.addScalarUnderRelaxationFactors(scalarID)
        #
        #     row = self._ui.underRelaxationFactorsLayout.rowCount()
        #     self._ui.underRelaxationFactorsLayout.addWidget(QLabel(fieldName), row, 0)
        #     self._ui.underRelaxationFactorsLayout.addWidget(QLineEdit(), row, 1)
        #     self._ui.underRelaxationFactorsLayout.addWidget(QLineEdit(), row, 2)
        #     self._scalarUnderRelazationFactors[scalarID] = row
        #
        #     xpath = f'{self._xpath}/convergenceCriteria/userDefinedScalars/scalar[scalarID="{scalarID}"]'
        #     if not self._db.exists(xpath):
        #         NumericalDB.addConvergenceCriteria(scalarID)
        #
        #     row = self._ui.convergenceCriteriaLyaout.rowCount()
        #     self._ui.convergenceCriteriaLyaout.addWidget(QLabel(fieldName), row, 0)
        #     self._ui.convergenceCriteriaLyaout.addWidget(QLineEdit(), row, 1)
        #     self._ui.convergenceCriteriaLyaout.addWidget(QLineEdit(), row, 2)
        #     self._scalarConvergenceCriterias[scalarID] = row

        self._connectSignalsSlots()

    def _load(self):
        timeIsTransient = GeneralDB.isTimeTransient()
        energyOn = ModelsDB.isEnergyModelOn()
        turbulenceOn = ModelsDB.getTurbulenceModel() not in (TurbulenceModel.INVISCID, TurbulenceModel.LAMINAR)
        multiphaseOn = ModelsDB.isMultiphaseModelOn()
        compressibleDensity = GeneralDB.isCompressibleDensity()

        solverCapability = getSolverCapability(findSolver())
        allRoundSolver: bool = solverCapability['timeTransient'] and solverCapability['timeSteady']  # this solver is able to solve both steady and transient

        self._ui.useMomentumPredictor.setVisible(timeIsTransient or allRoundSolver)

        if compressibleDensity:
            self._ui.pressureVelocity.hide()
            self._ui.discretizationSchemesMomentumLabel.setText(self.tr('Flow'))
        else:
            self._ui.densityBasedSolverParameters.hide()

        self._ui.discretizationSchemeTime.setEnabled(timeIsTransient)
        self._ui.discretizationSchemePressure.setEnabled(not compressibleDensity)
        self._ui.discretizationSchemeEnergy.setEnabled(energyOn and not compressibleDensity)
        self._ui.discretizationSchemeTurbulence.setEnabled(turbulenceOn)
        self._ui.discretizationSchemeVolumeFraction.setEnabled(multiphaseOn and not compressibleDensity)

        self._ui.underRelaxationFactorPressure.setEnabled(not compressibleDensity)
        self._ui.underRelaxationFactorPressureFinal.setEnabled((timeIsTransient or allRoundSolver) and not compressibleDensity)
        self._ui.underRelaxationFactorMomentum.setEnabled(not compressibleDensity)
        self._ui.underRelaxationFactorMomentumFinal.setEnabled((timeIsTransient or allRoundSolver) and not compressibleDensity)
        self._ui.underRelaxationFactorEnergy.setEnabled(energyOn and not compressibleDensity)
        self._ui.underRelaxationFactorEnergyFinal.setEnabled((timeIsTransient or allRoundSolver) and energyOn and not compressibleDensity)
        self._ui.underRelaxationFactorTurbulence.setEnabled(turbulenceOn)
        self._ui.underRelaxationFactorTurbulenceFinal.setEnabled((timeIsTransient or allRoundSolver) and turbulenceOn)
        self._ui.underRelaxationFactorDensity.setEnabled((timeIsTransient or allRoundSolver) and not compressibleDensity)
        self._ui.underRelaxationFactorDensityFinal.setEnabled(timeIsTransient or allRoundSolver)
        self._ui.underRelaxationFactorVolumeFraction.setEnabled(multiphaseOn and not compressibleDensity)
        self._ui.underRelaxationFactorVolumeFractionFinal.setEnabled(multiphaseOn and not compressibleDensity)

        self._ui.maxIterationsPerTimeStep.setEnabled(timeIsTransient or allRoundSolver)
        self._ui.numberOfCorrectors.setEnabled(timeIsTransient or allRoundSolver)

        if multiphaseOn:
            self._ui.multiphaseMaxIterationsPerTimeStep.setEnabled(True)
            self._ui.multiphaseNumberOfCorrectors.setEnabled(True)
        else:
            self._ui.multiphase.setEnabled(False)

        self._ui.absolutePressure.setEnabled(not compressibleDensity)
        self._ui.relativePressure.setEnabled((timeIsTransient or allRoundSolver) and not compressibleDensity)
        self._ui.absoluteDensity.setEnabled(compressibleDensity)
        self._ui.relativeDensity.setEnabled(False)
        self._ui.relativeMomentum.setEnabled(timeIsTransient or allRoundSolver)
        self._ui.absoluteEnergy.setEnabled(energyOn)
        self._ui.relativeEnergy.setEnabled((timeIsTransient or allRoundSolver) and energyOn)
        self._ui.absoluteTurbulence.setEnabled(turbulenceOn)
        self._ui.relativeTurbulence.setEnabled((timeIsTransient or allRoundSolver) and turbulenceOn)
        self._ui.absoluteVolumeFraction.setEnabled(multiphaseOn)
        self._ui.relativeVolumeFraction.setEnabled(multiphaseOn)

        if len(self._db.getUserDefinedScalars()):
            self._ui.discretizationSchemeScalar.setEnabled(True)
            self._ui.underRelaxationFactorScalar.setEnabled(True)
            self._ui.underRelaxationFactorScalarFinal.setEnabled(True)
            self._ui.absoluteScalar.setEnabled(True)
            self._ui.relativeScalar.setEnabled(True)
        else:
            self._ui.discretizationSchemeScalar.setEnabled(False)
            self._ui.underRelaxationFactorScalar.setEnabled(False)
            self._ui.underRelaxationFactorScalarFinal.setEnabled(False)
            self._ui.absoluteScalar.setEnabled(False)
            self._ui.relativeScalar.setEnabled(False)

        self._ui.pressureVelocityCouplingScheme.setCurrentData(
            PressureVelocityCouplingScheme(self._db.getValue(self._xpath + '/pressureVelocityCouplingScheme')))

        self._ui.formulation.setCurrentData(Formulation(
            self._db.getValue(self._xpath + '/densityBasedSolverParameters/formulation')))
        self._ui.fluxType.setCurrentData(FluxType(
            self._db.getValue(self._xpath + '/densityBasedSolverParameters/fluxType')))
        self._ui.entropyFixCoefficient.setText(self._db.getValue(
            self._xpath + '/densityBasedSolverParameters/entropyFixCoefficient'))
        self._ui.cutOffMachNumber.setText(
            self._db.getValue(self._xpath + '/densityBasedSolverParameters/cutOffMachNumber'))

        self._ui.useMomentumPredictor.setChecked(self._db.getValue(self._xpath + '/useMomentumPredictor') == 'true')
        self._ui.discretizationSchemeTime.setCurrentData(
            ImplicitDiscretizationScheme(self._db.getValue(self._xpath + '/discretizationSchemes/time')))
        self._ui.discretizationSchemePressure.setCurrentData(
            InterpolationScheme(self._db.getValue(self._xpath + '/discretizationSchemes/pressure')))
        self._ui.discretizationSchemeMomentum.setCurrentData(
            UpwindDiscretizationScheme(self._db.getValue(self._xpath + '/discretizationSchemes/momentum')))
        self._ui.discretizationSchemeEnergy.setCurrentData(
            UpwindDiscretizationScheme(self._db.getValue(self._xpath + '/discretizationSchemes/energy')))
        self._ui.discretizationSchemeTurbulence.setCurrentData(
            UpwindDiscretizationScheme(
                self._db.getValue(self._xpath + '/discretizationSchemes/turbulentKineticEnergy')))
        self._ui.discretizationSchemeVolumeFraction.setCurrentData(
            UpwindDiscretizationScheme(self._db.getValue(self._xpath + '/discretizationSchemes/volumeFraction')))
        self._ui.discretizationSchemeScalar.setCurrentData(
            UpwindDiscretizationScheme(self._db.getValue(self._xpath + '/discretizationSchemes/scalar')))

        self._ui.underRelaxationFactorPressure.setText(
            self._db.getValue(self._xpath + '/underRelaxationFactors/pressure'))
        self._ui.underRelaxationFactorPressureFinal.setText(
            self._db.getValue(self._xpath + '/underRelaxationFactors/pressureFinal'))
        self._ui.underRelaxationFactorMomentum.setText(
            self._db.getValue(self._xpath + '/underRelaxationFactors/momentum'))
        self._ui.underRelaxationFactorMomentumFinal.setText(
            self._db.getValue(self._xpath + '/underRelaxationFactors/momentumFinal'))
        self._ui.underRelaxationFactorEnergy.setText(self._db.getValue(self._xpath + '/underRelaxationFactors/energy'))
        self._ui.underRelaxationFactorEnergyFinal.setText(
            self._db.getValue(self._xpath + '/underRelaxationFactors/energyFinal'))
        self._ui.underRelaxationFactorTurbulence.setText(
            self._db.getValue(self._xpath + '/underRelaxationFactors/turbulence'))
        self._ui.underRelaxationFactorTurbulenceFinal.setText(
            self._db.getValue(self._xpath + '/underRelaxationFactors/turbulenceFinal'))
        self._ui.underRelaxationFactorDensity.setText(
            self._db.getValue(self._xpath + '/underRelaxationFactors/density'))
        self._ui.underRelaxationFactorDensityFinal.setText(
            self._db.getValue(self._xpath + '/underRelaxationFactors/densityFinal'))
        self._ui.underRelaxationFactorVolumeFraction.setText(
            self._db.getValue(self._xpath + '/underRelaxationFactors/volumeFraction'))
        self._ui.underRelaxationFactorVolumeFractionFinal.setText(
            self._db.getValue(self._xpath + '/underRelaxationFactors/volumeFractionFinal'))
        self._ui.underRelaxationFactorScalar.setText(self._db.getValue(self._xpath + '/underRelaxationFactors/scalar'))
        self._ui.underRelaxationFactorScalarFinal.setText(
            self._db.getValue(self._xpath + '/underRelaxationFactors/scalarFinal'))

        self._ui.limitingFactor.setText(self._db.getValue(self._xpath + '/highOrderTermRelaxation/relaxationFactor'))
        self._ui.improveStablitiy.setChecked(
            self._db.getAttribute(self._xpath + '/highOrderTermRelaxation', 'disabled') == 'false')

        self._ui.maxIterationsPerTimeStep.setText(self._db.getValue(self._xpath + '/maxIterationsPerTimeStep'))
        self._ui.numberOfCorrectors.setText(self._db.getValue(self._xpath + '/numberOfCorrectors'))

        self._ui.multiphaseMaxIterationsPerTimeStep.setText(
            self._db.getValue(self._xpath + '/multiphase/maxIterationsPerTimeStep'))
        self._ui.multiphaseNumberOfCorrectors.setText(
            self._db.getValue(self._xpath + '/multiphase/numberOfCorrectors'))
        if self._db.getValue(self._xpath + '/multiphase/useSemiImplicitMules') == 'true':
            self._ui.mulesSemiImplicit.setChecked(True)
        else:
            self._ui.mullesExplicit.setChecked(True)
        self._ui.phaseInterfaceCompressionFactor.setText(
            self._db.getValue(self._xpath + '/multiphase/phaseInterfaceCompressionFactor'))
        self._ui.numberOfMulesIterations.setText(
            self._db.getValue(self._xpath + '/multiphase/numberOfMulesIterations'))

        self._ui.absolutePressure.setText(self._db.getValue(self._xpath + '/convergenceCriteria/pressure/absolute'))
        self._ui.relativePressure.setText(self._db.getValue(self._xpath + '/convergenceCriteria/pressure/relative'))
        self._ui.absoluteDensity.setText(self._db.getValue(self._xpath + '/convergenceCriteria/density/absolute'))
        self._ui.relativeDensity.setText(self._db.getValue(self._xpath + '/convergenceCriteria/density/relative'))
        self._ui.absoluteMomentum.setText(self._db.getValue(self._xpath + '/convergenceCriteria/momentum/absolute'))
        self._ui.relativeMomentum.setText(self._db.getValue(self._xpath + '/convergenceCriteria/momentum/relative'))
        self._ui.absoluteEnergy.setText(self._db.getValue(self._xpath + '/convergenceCriteria/energy/absolute'))
        self._ui.relativeEnergy.setText(self._db.getValue(self._xpath + '/convergenceCriteria/energy/relative'))
        self._ui.absoluteTurbulence.setText(self._db.getValue(self._xpath + '/convergenceCriteria/turbulence/absolute'))
        self._ui.relativeTurbulence.setText(self._db.getValue(self._xpath + '/convergenceCriteria/turbulence/relative'))
        self._ui.absoluteVolumeFraction.setText(
            self._db.getValue(self._xpath + '/convergenceCriteria/volumeFraction/absolute'))
        self._ui.relativeVolumeFraction.setText(
            self._db.getValue(self._xpath + '/convergenceCriteria/volumeFraction/relative'))
        self._ui.absoluteScalar.setText(self._db.getValue(self._xpath + '/convergenceCriteria/scalar/absolute'))
        self._ui.relativeScalar.setText(self._db.getValue(self._xpath + '/convergenceCriteria/scalar/relative'))
        #
        # for scalarID, fieldName in self._db.getUserDefinedScalars():
        #     xpath = f'{self._xpath}/underRelaxationFactors/userDefinedScalars/scalar[scalarID="{scalarID}"]'
        #     self._ui.underRelaxationFactorsLayout.itemAtPosition(self._scalarUnderRelazationFactors[scalarID], 1).widget().setText(self._db.getValue(xpath + '/value'))
        #     self._ui.underRelaxationFactorsLayout.itemAtPosition(self._scalarUnderRelazationFactors[scalarID], 2).widget().setText(self._db.getValue(xpath + '/finalValue'))
        #
        #     xpath = f'{self._xpath}/convergenceCriteria/userDefinedScalars/scalar[scalarID="{scalarID}"]'
        #     self._ui.convergenceCriteriaLyaout.itemAtPosition(self._scalarConvergenceCriterias[scalarID], 1).widget().setText(self._db.getValue(xpath + '/absolute'))
        #     self._ui.convergenceCriteriaLyaout.itemAtPosition(self._scalarConvergenceCriterias[scalarID], 2).widget().setText(self._db.getValue(xpath + '/relative'))

    @qasync.asyncSlot()
    async def save(self):
        writer = CoreDBWriter()
        writer.append(self._xpath + '/pressureVelocityCouplingScheme',
                      self._ui.pressureVelocityCouplingScheme.currentValue(), None)

        writer.append(self._xpath + '/densityBasedSolverParameters/formulation',
                      self._ui.formulation.currentValue(), None)
        writer.append(self._xpath + '/densityBasedSolverParameters/fluxType', self._ui.fluxType.currentValue(), None)
        writer.append(self._xpath + '/densityBasedSolverParameters/entropyFixCoefficient',
                      self._ui.entropyFixCoefficient.text(), self.tr('Entropy Fix Coefficient'))
        writer.append(self._xpath + '/densityBasedSolverParameters/cutOffMachNumber',
                      self._ui.cutOffMachNumber.text(), self.tr('Cut-off Mach Number'))

        writer.append(self._xpath + '/useMomentumPredictor',
                      'true' if self._ui.useMomentumPredictor.isChecked() else 'false', None)

        writer.append(self._xpath + '/discretizationSchemes/time',
                      self._ui.discretizationSchemeTime.currentValue(), None)
        writer.append(self._xpath + '/discretizationSchemes/pressure',
                      self._ui.discretizationSchemePressure.currentValue(), None)
        writer.append(self._xpath + '/discretizationSchemes/momentum',
                      self._ui.discretizationSchemeMomentum.currentValue(), None)
        writer.append(self._xpath + '/discretizationSchemes/energy',
                      self._ui.discretizationSchemeEnergy.currentValue(), None)
        writer.append(self._xpath + '/discretizationSchemes/turbulentKineticEnergy',
                      self._ui.discretizationSchemeTurbulence.currentValue(), None)
        writer.append(self._xpath + '/discretizationSchemes/volumeFraction',
                      self._ui.discretizationSchemeVolumeFraction.currentValue(), None)
        writer.append(self._xpath + '/discretizationSchemes/scalar',
                      self._ui.discretizationSchemeScalar.currentValue(), None)

        writer.append(self._xpath + '/underRelaxationFactors/pressure',
                      self._ui.underRelaxationFactorPressure.text(), self.tr('Under-Relaxation Factor Pressure'))
        writer.append(self._xpath + '/underRelaxationFactors/pressureFinal',
                      self._ui.underRelaxationFactorPressureFinal.text(),
                      self.tr('Under-Relaxation Factor Pressure Final'))
        writer.append(self._xpath + '/underRelaxationFactors/momentum',
                      self._ui.underRelaxationFactorMomentum.text(), self.tr('Under-Relaxation Factor Momentum'))
        writer.append(self._xpath + '/underRelaxationFactors/momentumFinal',
                      self._ui.underRelaxationFactorMomentumFinal.text(),
                      self.tr('Under-Relaxation Factor Momentum Final'))
        writer.append(self._xpath + '/underRelaxationFactors/energy',
                      self._ui.underRelaxationFactorEnergy.text(), self.tr('Under-Relaxation Factor Energy'))
        writer.append(self._xpath + '/underRelaxationFactors/energyFinal',
                      self._ui.underRelaxationFactorEnergyFinal.text(), self.tr('Under-Relaxation Factor Energy Final'))
        writer.append(self._xpath + '/underRelaxationFactors/turbulence',
                      self._ui.underRelaxationFactorTurbulence.text(), self.tr('Under-Relaxation Factor Turbulence'))
        writer.append(self._xpath + '/underRelaxationFactors/turbulenceFinal',
                      self._ui.underRelaxationFactorTurbulenceFinal.text(),
                      self.tr('Under-Relaxation Factor Turbulence Final'))
        writer.append(self._xpath + '/underRelaxationFactors/density',
                      self._ui.underRelaxationFactorDensity.text(), self.tr('Under-Relaxation Factor Density'))
        writer.append(self._xpath + '/underRelaxationFactors/densityFinal',
                      self._ui.underRelaxationFactorDensityFinal.text(),
                      self.tr('Under-Relaxation Factor Density Final'))
        writer.append(self._xpath + '/underRelaxationFactors/volumeFraction',
                      self._ui.underRelaxationFactorVolumeFraction.text(),
                      self.tr('Under-Relaxation Factor Volume Fraction'))
        writer.append(self._xpath + '/underRelaxationFactors/volumeFractionFinal',
                      self._ui.underRelaxationFactorVolumeFractionFinal.text(),
                      self.tr('Under-Relaxation Factor Volume Fraction Final'))
        writer.append(self._xpath + '/underRelaxationFactors/scalar', self._ui.underRelaxationFactorScalar.text(),
                      self.tr('Under-Relaxation Scalar'))
        writer.append(self._xpath + '/underRelaxationFactors/scalarFinal',
                      self._ui.underRelaxationFactorScalarFinal.text(), self.tr('Under-Relaxation Scalar Final'))

        if self._ui.improveStablitiy.isChecked():
            writer.append(self._xpath + '/highOrderTermRelaxation/relaxationFactor',
                          self._ui.limitingFactor.text(), self.tr('Limiting Factor'))
            writer.setAttribute(self._xpath + '/highOrderTermRelaxation', 'disabled', 'false')
        else:
            writer.setAttribute(self._xpath + '/highOrderTermRelaxation', 'disabled', 'true')

        writer.append(self._xpath + '/maxIterationsPerTimeStep',
                      self._ui.maxIterationsPerTimeStep.text(), self.tr('Max Iterations per Time Step'))
        writer.append(self._xpath + '/numberOfCorrectors',
                      self._ui.numberOfCorrectors.text(), self.tr('Number of Correctors'))

        writer.append(self._xpath + '/multiphase/maxIterationsPerTimeStep',
                      self._ui.multiphaseMaxIterationsPerTimeStep.text(),
                      self.tr('Multiphase Max Iterations per Time Step'))
        writer.append(self._xpath + '/multiphase/numberOfCorrectors',
                      self._ui.multiphaseNumberOfCorrectors.text(), self.tr('Multiphase Number of Correctors'))
        writer.append(self._xpath + '/multiphase/useSemiImplicitMules',
                      'true' if self._ui.mulesSemiImplicit.isChecked() else 'false', None)
        writer.append(self._xpath + '/multiphase/phaseInterfaceCompressionFactor',
                      self._ui.phaseInterfaceCompressionFactor.text(), self.tr('Phase Interface Compression Factor'))
        writer.append(self._xpath + '/multiphase/numberOfMulesIterations',
                      self._ui.numberOfMulesIterations.text(), self.tr('Number of MULES iterations over the limiter'))

        writer.append(self._xpath + '/convergenceCriteria/pressure/absolute',
                      self._ui.absolutePressure.text(), self.tr('Convergence Criteria Absolute Pressure'))
        writer.append(self._xpath + '/convergenceCriteria/pressure/relative',
                      self._ui.relativePressure.text(), self.tr('Convergence Criteria Relative Pressure'))
        writer.append(self._xpath + '/convergenceCriteria/density/absolute',
                      self._ui.absoluteDensity.text(), self.tr('Convergence Criteria Absolute Density'))
        writer.append(self._xpath + '/convergenceCriteria/density/relative',
                      self._ui.relativeDensity.text(), self.tr('Convergence Criteria Relative Density'))
        writer.append(self._xpath + '/convergenceCriteria/momentum/absolute',
                      self._ui.absoluteMomentum.text(), self.tr('Convergence Criteria Absolute Moment'))
        writer.append(self._xpath + '/convergenceCriteria/momentum/relative',
                      self._ui.relativeMomentum.text(), self.tr('Convergence Criteria Relative Moment'))
        writer.append(self._xpath + '/convergenceCriteria/energy/absolute',
                      self._ui.absoluteEnergy.text(), self.tr('Convergence Criteria Absolute Energy'))
        writer.append(self._xpath + '/convergenceCriteria/energy/relative',
                      self._ui.relativeEnergy.text(), self.tr('Convergence Criteria Relative Energy'))
        writer.append(self._xpath + '/convergenceCriteria/turbulence/absolute',
                      self._ui.absoluteTurbulence.text(), self.tr('Convergence Criteria Absolute Turbulence'))
        writer.append(self._xpath + '/convergenceCriteria/turbulence/relative',
                      self._ui.relativeTurbulence.text(), self.tr('Convergence Criteria Relative Turbulence'))
        writer.append(self._xpath + '/convergenceCriteria/volumeFraction/absolute',
                      self._ui.absoluteVolumeFraction.text(), self.tr('Convergence Criteria Absolute Volume Fraction'))
        writer.append(self._xpath + '/convergenceCriteria/volumeFraction/relative',
                      self._ui.relativeVolumeFraction.text(), self.tr('Convergence Criteria Relative Volume Fraction'))
        writer.append(self._xpath + '/convergenceCriteria/scalar/absolute',
                      self._ui.absoluteScalar.text(), self.tr('Convergence Criteria Absolute Scalar'))
        writer.append(self._xpath + '/convergenceCriteria/scalar/relative',
                      self._ui.relativeScalar.text(), self.tr('Convergence Criteria Relative Scalar'))
        #
        # for scalarID, fieldName in self._db.getUserDefinedScalars():
        #     writer.append(
        #         f'{self._xpath}/underRelaxationFactors/userDefinedScalars/scalar[scalarID="{scalarID}"]/value',
        #         self._ui.underRelaxationFactorsLayout.itemAtPosition(self._scalarUnderRelazationFactors[scalarID], 1).widget().text(),
        #         self.tr('Under-Relaxation Factor ') + fieldName)
        #     writer.append(
        #         f'{self._xpath}/underRelaxationFactors/userDefinedScalars/scalar[scalarID="{scalarID}"]/finalValue',
        #         self._ui.underRelaxationFactorsLayout.itemAtPosition(self._scalarUnderRelazationFactors[scalarID], 2).widget().text(),
        #         self.tr('Under-Relaxation Factor {} Final').format(fieldName))
        #
        #     writer.append(
        #         f'{self._xpath}/convergenceCriteria/userDefinedScalars/scalar[scalarID="{scalarID}"]/absolute',
        #         self._ui.convergenceCriteriaLyaout.itemAtPosition(self._scalarConvergenceCriterias[scalarID], 1).widget().text(),
        #         self.tr('Convergence Criteria Absolute ') + fieldName)
        #     writer.append(
        #         f'{self._xpath}/convergenceCriteria/userDefinedScalars/scalar[scalarID="{scalarID}"]/relative',
        #         self._ui.convergenceCriteriaLyaout.itemAtPosition(self._scalarConvergenceCriterias[scalarID], 2).widget().text(),
        #         self.tr('Convergence Criteria Relative ') + fieldName)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr('Input Error'), writer.firstError().toMessage())
            return False

        return True

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._load()

        return super().showEvent(ev)

    def _connectSignalsSlots(self):
        self._ui.advanced.clicked.connect(self._advancedSetup)
        self._ui.fluxType.currentDataChanged.connect(self._fluxTypeChanged)

    def _advancedSetup(self):
        self._dialog = AdvancedDialog()
        self._dialog.open()

    def _fluxTypeChanged(self, fluxType):
        self._ui.densityBasedSolverParametersLayout.setRowVisible(
            self._ui.entropyFixCoefficient,fluxType == FluxType.ROE_FDS)
        self._ui.densityBasedSolverParametersLayout.setRowVisible(
            self._ui.cutOffMachNumber,fluxType == FluxType.AUSM_UP)
