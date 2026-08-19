#!/usr/bin/env python
# -*- coding: utf-8 -*-

from widgets.async_message_box import AsyncMessageBox

import baramFlow.openfoam.solver
from baramFlow.base.numberical_condition.numberical_condition import ImplicitDiscretizationScheme, NumericalConditions
from baramFlow.base.numberical_condition.numberical_condition import DiscretizationSchemes, UnderRelaxationFactors
from baramFlow.base.numberical_condition.numberical_condition import HighOrderTermRelaxation, MultiPhase
from baramFlow.base.numberical_condition.numberical_condition import ConvergenceCriteria, ConvergenceCriteriaItem
from baramFlow.base.numberical_condition.numberical_condition import UpwindDiscretizationScheme, InterpolationScheme
from baramFlow.base.numberical_condition.numberical_condition import PressureVelocityCouplingScheme, Formulation
from baramFlow.base.numberical_condition.numberical_condition import FluxType, DensityBasedSolverParameters
from baramFlow.base.numberical_condition.update_models import NumericalUpdate
from baramFlow.case_manager import CaseManager
from baramFlow.coredb import coredb
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB, MultiphaseModel
from baramFlow.coredb.numerical_db import NumericalDB
from baramFlow.coredb.project import Project
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB
from baramFlow.services.numerical_condition.numberical_service import NumericalService
from baramFlow.view.widgets.content_page import ContentPage

from .advanced_dialog import AdvancedDialog
from .numerical_conditions_page_ui import Ui_NumericalConditionsPage


class NumericalConditionsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_NumericalConditionsPage()
        self._ui.setupUi(self)

        self._discretizationSchemesCount = self._ui.discretizationSchemes.layout().rowCount()
        self._underRelaxationFactorsCount = self._ui.underRelaxationFactors.layout().count()
        self._convergenceCriteriaCount = self._ui.convergenceCriteria.layout().count()

        self._xpath = NumericalDB.NUMERICAL_CONDITIONS_XPATH
        self._dialog = None

        self._ui.pressureVelocityCouplingScheme.addItem(self.tr('SIMPLE'),  PressureVelocityCouplingScheme.SIMPLE)
        self._ui.pressureVelocityCouplingScheme.addItem(self.tr('SIMPLEC'), PressureVelocityCouplingScheme.SIMPLEC)

        self._ui.formulation.addItem(self.tr('Implicit'),   Formulation.IMPLICIT)

        self._ui.fluxType.addItem(self.tr('Roe-FDS'),   FluxType.ROE_FDS)
        self._ui.fluxType.addItem(self.tr('ASUM'),      FluxType.AUSM)
        self._ui.fluxType.addItem(self.tr('ASUM-up'),   FluxType.AUSM_UP)

        self._ui.discretizationSchemeTime.addItem(self.tr('First Order Implicit'),
                                                  ImplicitDiscretizationScheme.FIRST_ORDER_IMPLICIT),
        self._ui.discretizationSchemeTime.addItem(self.tr('Second Order Implicit'),
                                                  ImplicitDiscretizationScheme.SECOND_ORDER_IMPLICIT),

        self._ui.discretizationSchemeMomentum.addItem(self.tr('First Order Upwind'),
                                                            UpwindDiscretizationScheme.FIRST_ORDER_UPWIND)
        self._ui.discretizationSchemeMomentum.addItem(self.tr('Second Order Upwind'),
                                                            UpwindDiscretizationScheme.SECOND_ORDER_UPWIND)

        self._ui.discretizationSchemeEnergy.addItem(self.tr('First Order Upwind'),
                                                      UpwindDiscretizationScheme.FIRST_ORDER_UPWIND)
        self._ui.discretizationSchemeEnergy.addItem(self.tr('Second Order Upwind'),
                                                      UpwindDiscretizationScheme.SECOND_ORDER_UPWIND)

        self._ui.discretizationSchemeTurbulence.addItem(self.tr('First Order Upwind'),
                                                      UpwindDiscretizationScheme.FIRST_ORDER_UPWIND)
        self._ui.discretizationSchemeTurbulence.addItem(self.tr('Second Order Upwind'),
                                                      UpwindDiscretizationScheme.SECOND_ORDER_UPWIND)

        self._ui.discretizationSchemeVolumeFraction.addItem(self.tr('First Order Upwind'),
                                                      UpwindDiscretizationScheme.FIRST_ORDER_UPWIND)
        self._ui.discretizationSchemeVolumeFraction.addItem(self.tr('Second Order Upwind'),
                                                      UpwindDiscretizationScheme.SECOND_ORDER_UPWIND)

        self._ui.discretizationSchemePressure.addItem(self.tr('Linear'),
                                                      InterpolationScheme.LINEAR)
        self._ui.discretizationSchemePressure.addItem(self.tr('Momentum Weighted Reconstruct'),
                                                      InterpolationScheme.MOMENTUM_WEIGHTED_RECONSTRUC)
        self._ui.discretizationSchemePressure.addItem(self.tr('Momentum Weighted'),
                                                      InterpolationScheme.MOMENTUM_WEIGHTED)


        self._ui.discretizationSchemeScalar.addItem(self.tr('First Order Upwind'),
                                                            UpwindDiscretizationScheme.FIRST_ORDER_UPWIND)
        self._ui.discretizationSchemeScalar.addItem(self.tr('Second Order Upwind'),
                                                            UpwindDiscretizationScheme.SECOND_ORDER_UPWIND)

        self._ui.discretizationSchemeSpecies.addItem(self.tr('First Order Upwind'),
                                                    UpwindDiscretizationScheme.FIRST_ORDER_UPWIND)
        self._ui.discretizationSchemeSpecies.addItem(self.tr('Second Order Upwind'),
                                                    UpwindDiscretizationScheme.SECOND_ORDER_UPWIND)

        self._ui.maxIterationsPerTimeStep.setValidationRule(self.tr('Max Iterations per Time Step'),
                                                            low=0, lowInclusive=False)
        self._ui.numberOfCorrectors.setValidationRule(self.tr('Number of Correctors'), low=0, lowInclusive=False)
        self._ui.multiphaseMaxIterationsPerTimeStep.setValidationRule(self.tr('Multiphase Max Iterations per Time Step'),
                                                                      low=0)
        self._ui.multiphaseNumberOfCorrectors.setValidationRule(self.tr('Multiphase Number of Correctors'),
                                                                low=0, lowInclusive=False)
        self._ui.numberOfMulesIterations.setValidationRule(self.tr('Number of MULES iterations over the limiter'),
                                                           low=0, lowInclusive=False)

        self._updateEnabled()
        self._connectSignalsSlots()

    def _load(self):
        data: NumericalConditions = NumericalService.getConditions()
        timeIsTransient = GeneralDB.isTimeTransient()
        energyOn = ModelsDB.isEnergyModelOn()
        turbulenceOn = TurbulenceModelsDB.getModel()not in (TurbulenceModel.INVISCID, TurbulenceModel.LAMINAR)
        multiphaseOn = ModelsDB.isMultiphaseModelOn()
        compressibleDensity = GeneralDB.isCompressibleDensity()

        allRoundSolver = baramFlow.openfoam.solver.allRoundSolver()  # this solver is able to solve both steady and transient

        self._ui.useMomentumPredictor.setVisible(timeIsTransient or allRoundSolver)

        self._ui.discretizationSchemeTime.setEnabled(timeIsTransient and not compressibleDensity)
        self._ui.discretizationSchemePressure.setEnabled(not compressibleDensity)
        self._ui.discretizationSchemeEnergy.setEnabled(energyOn and not compressibleDensity)
        self._ui.discretizationSchemeTurbulence.setEnabled(turbulenceOn)
        self._ui.discretizationSchemeVolumeFraction.setEnabled(multiphaseOn and not compressibleDensity)

        if ModelsDB.getMultiphaseModel() == MultiphaseModel.VOLUME_OF_FLUID:
            self._handleTimeDiscretizationSchemeChanged()
        else:
            self._ui.discretizationSchemes.layout().setRowVisible(self._ui.crankNicolsonBlendingFactor, False)

        self._ui.underRelaxationFactorPressure.setEnabled(not compressibleDensity)
        self._ui.underRelaxationFactorPressureFinal.setEnabled((timeIsTransient or allRoundSolver) and not compressibleDensity)
        self._ui.underRelaxationFactorMomentum.setEnabled(not compressibleDensity)
        self._ui.underRelaxationFactorMomentumFinal.setEnabled((timeIsTransient or allRoundSolver) and not compressibleDensity)
        self._ui.underRelaxationFactorEnergy.setEnabled(energyOn and not compressibleDensity)
        self._ui.underRelaxationFactorEnergyFinal.setEnabled((timeIsTransient or allRoundSolver) and energyOn and not compressibleDensity)
        self._ui.underRelaxationFactorTurbulence.setEnabled(turbulenceOn)
        self._ui.underRelaxationFactorTurbulenceFinal.setEnabled((timeIsTransient or allRoundSolver) and turbulenceOn)
        self._ui.underRelaxationFactorDensity.setEnabled(not compressibleDensity)
        self._ui.underRelaxationFactorDensityFinal.setEnabled((timeIsTransient or allRoundSolver) and not compressibleDensity)
        self._ui.underRelaxationFactorVolumeFraction.setEnabled(multiphaseOn and not compressibleDensity)
        self._ui.underRelaxationFactorVolumeFractionFinal.setEnabled(multiphaseOn and not compressibleDensity)

        self._ui.maxIterationsPerTimeStep.setEnabled(timeIsTransient or allRoundSolver)
        self._ui.numberOfCorrectors.setEnabled(timeIsTransient or allRoundSolver)
        if GeneralDB.isCompressibleDensity():
            self._ui.numberOfCorrectors.setEnabled(False)
            self._ui.numberOfNonOrthogonalCorrectors.setEnabled(False)

        if multiphaseOn:
            self._ui.multiphaseMaxIterationsPerTimeStep.setEnabled(True)
            self._ui.multiphaseNumberOfCorrectors.setEnabled(True)
        else:
            self._ui.multiphase.setEnabled(False)

        self._ui.absolutePressure.setEnabled(not compressibleDensity)
        self._ui.relativePressure.setEnabled((timeIsTransient or allRoundSolver) and not compressibleDensity)
        self._ui.absoluteDensity.setEnabled(compressibleDensity)
        self._ui.relativeDensity.setEnabled(compressibleDensity and timeIsTransient)
        self._ui.relativeMomentum.setEnabled(timeIsTransient or allRoundSolver)
        self._ui.absoluteEnergy.setEnabled(energyOn)
        self._ui.relativeEnergy.setEnabled((timeIsTransient or allRoundSolver) and energyOn)
        self._ui.absoluteTurbulence.setEnabled(turbulenceOn)
        self._ui.relativeTurbulence.setEnabled((timeIsTransient or allRoundSolver) and turbulenceOn)
        self._ui.absoluteVolumeFraction.setEnabled(multiphaseOn)
        self._ui.relativeVolumeFraction.setEnabled(multiphaseOn)

        if len(coredb.CoreDB().getUserDefinedScalars()):
            self._ui.discretizationSchemeScalar.setEnabled(True)
            self._ui.underRelaxationFactorScalar.setEnabled(True)
            self._ui.underRelaxationFactorScalarFinal.setEnabled(timeIsTransient or allRoundSolver)
        else:
            self._ui.discretizationSchemeScalar.setEnabled(False)
            self._ui.underRelaxationFactorScalar.setEnabled(False)
            self._ui.underRelaxationFactorScalarFinal.setEnabled(False)

        if ModelsDB.isSpeciesModelOn():
            self._ui.discretizationSchemeSpecies.setEnabled(True)
            self._ui.underRelaxationFactorSpecies.setEnabled(True)
            self._ui.underRelaxationFactorSpeciesFinal.setEnabled(True)
            self._ui.absoluteSpecies.setEnabled(True)
            self._ui.relativeSpecies.setEnabled(True)
        else:
            self._ui.discretizationSchemeSpecies.setEnabled(False)
            self._ui.underRelaxationFactorSpecies.setEnabled(False)
            self._ui.underRelaxationFactorSpeciesFinal.setEnabled(False)
            self._ui.absoluteSpecies.setEnabled(False)
            self._ui.relativeSpecies.setEnabled(False)

        self._ui.pressureVelocityCouplingScheme.setCurrentIndex(
            self._ui.pressureVelocityCouplingScheme.findData(data.pressureVelocityCouplingScheme))

        self._ui.formulation.setCurrentIndex(
            self._ui.formulation.findData(data.densityBasedSolverParameters.formulation))
        self._ui.fluxType.setCurrentIndex(self._ui.fluxType.findData(data.densityBasedSolverParameters.fluxType))
        self._ui.entropyFixCoefficient.setPFloat(data.densityBasedSolverParameters.entropyFixCoefficient)
        self._ui.cutOffMachNumber.setPFloat(data.densityBasedSolverParameters.cutOffMachNumber)

        if compressibleDensity:
            self._ui.pressureVelocity.hide()
            self._ui.discretizationSchemesMomentumLabel.setPFloat(self.tr('Flow'))
            discretizationSchemeTime = (ImplicitDiscretizationScheme.SECOND_ORDER_IMPLICIT if timeIsTransient 
                                        else ImplicitDiscretizationScheme.FIRST_ORDER_IMPLICIT)
        else:
            self._ui.densityBasedSolverParameters.hide()
            discretizationSchemeTime = data.discretizationSchemes.time

        self._ui.useMomentumPredictor.setChecked(data.useMomentumPredictor)
        self._ui.discretizationSchemeTime.setCurrentIndex(
            self._ui.discretizationSchemeTime.findData(discretizationSchemeTime))
        self._ui.crankNicolsonBlendingFactor.setPFloat(data.discretizationSchemes.crankNicolsonBlendingFactor)
        self._ui.discretizationSchemePressure.setCurrentIndex(
            self._ui.discretizationSchemePressure.findData(data.discretizationSchemes.pressure))
        self._ui.discretizationSchemeMomentum.setCurrentIndex(
            self._ui.discretizationSchemeMomentum.findData(data.discretizationSchemes.momentum))

        self._ui.discretizationSchemeEnergy.setCurrentIndex(
            self._ui.discretizationSchemeEnergy.findData(data.discretizationSchemes.energy))
        self._ui.discretizationSchemeTurbulence.setCurrentIndex(
            self._ui.discretizationSchemeTurbulence.findData(data.discretizationSchemes.turbulentKineticEnergy))
        self._ui.discretizationSchemeVolumeFraction.setCurrentIndex(
            self._ui.discretizationSchemeVolumeFraction.findData(data.discretizationSchemes.volumeFraction))
        self._ui.discretizationSchemeScalar.setCurrentIndex(
            self._ui.discretizationSchemeScalar.findData(data.discretizationSchemes.scalar))
        self._ui.discretizationSchemeSpecies.setCurrentIndex(
            self._ui.discretizationSchemeSpecies.findData(data.discretizationSchemes.species))

        self._ui.underRelaxationFactorPressure.setPFloat(data.underRelaxationFactors.pressure)
        self._ui.underRelaxationFactorPressureFinal.setPFloat(data.underRelaxationFactors.pressureFinal)
        self._ui.underRelaxationFactorMomentum.setPFloat(data.underRelaxationFactors.momentum)
        self._ui.underRelaxationFactorMomentumFinal.setPFloat(data.underRelaxationFactors.momentumFinal)
        self._ui.underRelaxationFactorEnergy.setPFloat(data.underRelaxationFactors.energy)
        self._ui.underRelaxationFactorEnergyFinal.setPFloat(data.underRelaxationFactors.energyFinal)
        self._ui.underRelaxationFactorTurbulence.setPFloat(data.underRelaxationFactors.turbulence)
        self._ui.underRelaxationFactorTurbulenceFinal.setPFloat(data.underRelaxationFactors.turbulenceFinal)
        self._ui.underRelaxationFactorDensity.setPFloat(data.underRelaxationFactors.density)
        self._ui.underRelaxationFactorDensityFinal.setPFloat(data.underRelaxationFactors.densityFinal)
        self._ui.underRelaxationFactorVolumeFraction.setPFloat(data.underRelaxationFactors.volumeFraction)
        self._ui.underRelaxationFactorVolumeFractionFinal.setPFloat(data.underRelaxationFactors.volumeFractionFinal)
        self._ui.underRelaxationFactorScalar.setPFloat(data.underRelaxationFactors.scalar)
        self._ui.underRelaxationFactorScalarFinal.setPFloat(data.underRelaxationFactors.scalarFinal)
        self._ui.underRelaxationFactorSpecies.setPFloat(data.underRelaxationFactors.species)
        self._ui.underRelaxationFactorSpeciesFinal.setPFloat(data.underRelaxationFactors.speciesFinal)

        self._ui.limitingFactor.setPFloat(data.highOrderTermRelaxation.relaxationFactor)
        self._ui.improveStablitiy.setChecked(not data.highOrderTermRelaxation.disabled)

        self._ui.maxIterationsPerTimeStep.setText(data.maxIterationsPerTimeStep)
        self._ui.numberOfCorrectors.setText(data.numberOfCorrectors)
        self._ui.numberOfNonOrthogonalCorrectors.setPFloat(data.numberOfNonOrthogonalCorrectors)

        self._ui.multiphaseMaxIterationsPerTimeStep.setText(data.multiphase.maxIterationsPerTimeStep)
        self._ui.multiphaseNumberOfCorrectors.setText(data.multiphase.numberOfCorrectors)
        if data.multiphase.useSemiImplicitMules:
            self._ui.mulesSemiImplicit.setChecked(True)
        else:
            self._ui.mullesExplicit.setChecked(True)
        self._ui.phaseInterfaceCompressionFactor.setPFloat(data.multiphase.phaseInterfaceCompressionFactor)
        self._ui.numberOfMulesIterations.setText(data.multiphase.numberOfMulesIterations)

        self._ui.absolutePressure.setPFloat(data.convergenceCriteria.pressure.absolute)
        self._ui.relativePressure.setPFloat(data.convergenceCriteria.pressure.relative)
        self._ui.absoluteDensity.setPFloat(data.convergenceCriteria.density.absolute)
        self._ui.relativeDensity.setPFloat(data.convergenceCriteria.density.relative)
        self._ui.absoluteMomentum.setPFloat(data.convergenceCriteria.momentum.absolute)
        self._ui.relativeMomentum.setPFloat(data.convergenceCriteria.momentum.relative)
        self._ui.absoluteEnergy.setPFloat(data.convergenceCriteria.energy.absolute)
        self._ui.relativeEnergy.setPFloat(data.convergenceCriteria.energy.relative)
        self._ui.absoluteTurbulence.setPFloat(data.convergenceCriteria.turbulence.absolute)
        self._ui.relativeTurbulence.setPFloat(data.convergenceCriteria.turbulence.relative)
        self._ui.absoluteVolumeFraction.setPFloat(data.convergenceCriteria.volumeFraction.absolute)
        self._ui.relativeVolumeFraction.setPFloat(data.convergenceCriteria.volumeFraction.relative)
        self._ui.absoluteScalar.setPFloat(data.convergenceCriteria.scalar.absolute)
        self._ui.relativeScalar.setPFloat(data.convergenceCriteria.scalar.relative)
        self._ui.absoluteSpecies.setPFloat(data.convergenceCriteria.species.absolute)
        self._ui.relativeSpecies.setPFloat(data.convergenceCriteria.species.relative)

        discretizationSchemeLayout = self._ui.discretizationSchemes.layout()
        underRelaxationFactorLayout = self._ui.underRelaxationFactors.layout()
        convergenceCriteriaLayout = self._ui.convergenceCriteria.layout()

        while discretizationSchemeLayout.rowCount() > self._discretizationSchemesCount:
            discretizationSchemeLayout.removeRow(self._discretizationSchemesCount)

        while underRelaxationFactorLayout.count() > self._underRelaxationFactorsCount:
            widget = underRelaxationFactorLayout.itemAt(self._underRelaxationFactorsCount).widget()
            underRelaxationFactorLayout.removeWidget(widget)
            widget.deleteLater()

        while convergenceCriteriaLayout.count() > self._convergenceCriteriaCount:
            widget = convergenceCriteriaLayout.itemAt(self._convergenceCriteriaCount).widget()
            convergenceCriteriaLayout.removeWidget(widget)
            widget.deleteLater()

        self._onFluxTypeChanged()

    async def save(self):
        loaded = NumericalService.getConditions()

        try:
            if self._ui.discretizationSchemeTime.currentData() == ImplicitDiscretizationScheme.SECOND_ORDER_IMPLICIT:
                crankNicolsonBlendingFactor = self._ui.crankNicolsonBlendingFactor.pFloat(
                    self.tr('Crank-Nicolson Blending Factor'), low=0, high=1)
            else:
                crankNicolsonBlendingFactor = loaded.discretizationSchemes.crankNicolsonBlendingFactor

            if self._ui.improveStablitiy.isChecked():
                highOrderTermRelaxation=HighOrderTermRelaxation(
                    disabled=False,
                    relaxationFactor=self._ui.limitingFactor.pFloat(self.tr('Limiting Factor'), low=0, high=1))
            else:
                highOrderTermRelaxation=HighOrderTermRelaxation(
                    disabled=True,
                    relaxationFactor=loaded.highOrderTermRelaxation.relaxationFactor)

            data = NumericalUpdate(
                pressureVelocityCouplingScheme=self._ui.pressureVelocityCouplingScheme.currentData(),
                densityBasedSolverParameters=DensityBasedSolverParameters(
                    formulation=self._ui.formulation.currentData(),
                    fluxType=self._ui.fluxType.currentData(),
                    entropyFixCoefficient=self._ui.entropyFixCoefficient.pFloat(
                        self.tr('Entropy Fix Coefficient'), low=0, high=1, lowInclusive=False, highInclusive=False),
                    cutOffMachNumber=self._ui.cutOffMachNumber.pFloat(
                        self.tr('Cut-off Mach Number'), low=0, high=10, lowInclusive=False, highInclusive=False)),
                useMomentumPredictor=self._ui.useMomentumPredictor.isChecked(),
                discretizationSchemes=DiscretizationSchemes(
                    time=self._ui.discretizationSchemeTime.currentData(),
                    crankNicolsonBlendingFactor=crankNicolsonBlendingFactor,
                    momentum=self._ui.discretizationSchemeMomentum.currentData(),
                    energy=self._ui.discretizationSchemeEnergy.currentData(),
                    turbulentKineticEnergy=self._ui.discretizationSchemeTurbulence.currentData(),
                    volumeFraction=self._ui.discretizationSchemeVolumeFraction.currentData(),
                    pressure=self._ui.discretizationSchemePressure.currentData(),
                    scalar=self._ui.discretizationSchemeScalar.currentData(),
                    species=self._ui.discretizationSchemeSpecies.currentData()
                ),
                underRelaxationFactors=UnderRelaxationFactors(
                    pressure=self._ui.underRelaxationFactorPressure.pFloat(self.tr('Under-Relaxation Factor Pressure'),
                                                                           low=0, high=1, lowInclusive=False),
                    pressureFinal=self._ui.underRelaxationFactorPressureFinal.pFloat(
                        self.tr('Under-Relaxation Factor Pressure Final'), low=0, high=1, lowInclusive=False),
                    momentum=self._ui.underRelaxationFactorMomentum.pFloat(self.tr('Under-Relaxation Factor Momentum'),
                                                                           low=0, high=1, lowInclusive=False),
                    momentumFinal=self._ui.underRelaxationFactorMomentumFinal.pFloat(
                        self.tr('Under-Relaxation Factor Momentum Final'), low=0, high=1, lowInclusive=False),
                    energy=self._ui.underRelaxationFactorEnergy.pFloat(self.tr('Under-Relaxation Factor Energy'),
                                                                       low=0, high=1, lowInclusive=False),
                    energyFinal=self._ui.underRelaxationFactorEnergyFinal.pFloat(
                        self.tr('Under-Relaxation Factor Energy Final'), low=0, high=1, lowInclusive=False),
                    turbulence=self._ui.underRelaxationFactorTurbulence.pFloat(
                        self.tr('Under-Relaxation Factor Turbulence'), low=0, high=1, lowInclusive=False),
                    turbulenceFinal=self._ui.underRelaxationFactorTurbulenceFinal.pFloat(
                        self.tr('Under-Relaxation Factor Turbulence Final'), low=0, high=1, lowInclusive=False),
                    density=self._ui.underRelaxationFactorDensity.pFloat(self.tr('Under-Relaxation Factor Density'),
                                                                         low=0, high=1, lowInclusive=False),
                    densityFinal=self._ui.underRelaxationFactorDensityFinal.pFloat(
                        self.tr('Under-Relaxation Factor Density Final'), low=0, high=1, lowInclusive=False),
                    volumeFraction=self._ui.underRelaxationFactorVolumeFraction.pFloat(
                        self.tr('Under-Relaxation Factor Volume Fraction'), low=0, high=1, lowInclusive=False),
                    volumeFractionFinal=self._ui.underRelaxationFactorVolumeFractionFinal.pFloat(
                        self.tr('Under-Relaxation Factor Volume Fraction Final'), low=0, high=1, lowInclusive=False),
                    scalar=self._ui.underRelaxationFactorScalar.pFloat(self.tr('Under-Relaxation Scalar'),
                                                                       low=0, high=1, lowInclusive=False),
                    scalarFinal=self._ui.underRelaxationFactorScalarFinal.pFloat(self.tr('Under-Relaxation Scalar Final'),
                                                                                 low=0, high=1, lowInclusive=False),
                    species=self._ui.underRelaxationFactorSpecies.pFloat(self.tr('Under-Relaxation Species'),
                                                                         low=0, high=1, lowInclusive=False),
                    speciesFinal=self._ui.underRelaxationFactorSpeciesFinal.pFloat(
                        self.tr('Under-Relaxation Species Final'), low=0, high=1, lowInclusive=False)),
                highOrderTermRelaxation=highOrderTermRelaxation,
                maxIterationsPerTimeStep=self._ui.maxIterationsPerTimeStep.text(),
                numberOfCorrectors=self._ui.numberOfCorrectors.text(),
                numberOfNonOrthogonalCorrectors=self._ui.numberOfNonOrthogonalCorrectors.pFloat(
                    self.tr('Number of Non-orthogonal Correctors'), low=0, high=10),
                multiphase=MultiPhase(
                    maxIterationsPerTimeStep=self._ui.multiphaseMaxIterationsPerTimeStep.text(),
                    numberOfCorrectors=self._ui.multiphaseNumberOfCorrectors.text(),
                    useSemiImplicitMules=self._ui.mulesSemiImplicit.isChecked(),
                    phaseInterfaceCompressionFactor=self._ui.phaseInterfaceCompressionFactor.pFloat(
                        self.tr('Phase Interface Compression Factor')),
                        numberOfMulesIterations=self._ui.numberOfMulesIterations.text()),
                convergenceCriteria=ConvergenceCriteria(
                    pressure=ConvergenceCriteriaItem(
                        absolute=self._ui.absolutePressure.pFloat(self.tr('Convergence Criteria Absolute Pressure'),
                                                                  low=0, high=1),
                        relative=self._ui.relativePressure.pFloat(self.tr('Convergence Criteria Relative Pressure'),
                                                                  low=0, high=1)),
                    density=ConvergenceCriteriaItem(
                        absolute=self._ui.absoluteDensity.pFloat(self.tr('Convergence Criteria Absolute Density'),
                                                                 low=0, high=1),
                        relative=self._ui.relativeDensity.pFloat(self.tr('Convergence Criteria Relative Density'),
                                                                 low=0, high=1)),
                    momentum=ConvergenceCriteriaItem(
                        absolute=self._ui.absoluteMomentum.pFloat(self.tr('Convergence Criteria Absolute Moment'),
                                                                  low=0, high=1),
                        relative=self._ui.relativeMomentum.pFloat(self.tr('Convergence Criteria Relative Moment'),
                                                                  low=0, high=1)),
                    energy=ConvergenceCriteriaItem(
                        absolute=self._ui.absoluteEnergy.pFloat(self.tr('Convergence Criteria Absolute Energy'),
                                                                low=0, high=1),
                        relative=self._ui.relativeEnergy.pFloat(self.tr('Convergence Criteria Relative Energy'),
                                                                low=0, high=1)),
                    turbulence=ConvergenceCriteriaItem(
                        absolute=self._ui.absoluteTurbulence.pFloat(self.tr('Convergence Criteria Absolute Turbulence'),
                                                                    low=0, high=1),
                        relative=self._ui.relativeTurbulence.pFloat(self.tr('Convergence Criteria Relative Turbulence'),
                                                                    low=0, high=1)),
                    volumeFraction=ConvergenceCriteriaItem(
                        absolute=self._ui.absoluteVolumeFraction.pFloat(
                            self.tr('Convergence Criteria Absolute Volume Fraction'), low=0, high=1),
                        relative=self._ui.relativeVolumeFraction.pFloat(
                            self.tr('Convergence Criteria Relative Volume Fraction'), low=0, high=1)),
                    scalar=ConvergenceCriteriaItem(
                        absolute=self._ui.absoluteScalar.pFloat(self.tr('Convergence Criteria Absolute Scalar'),
                                                                low=0, high=1),
                        relative= self._ui.relativeScalar.pFloat(self.tr('Convergence Criteria Relative Scalar'),
                                                                 low=0, high=1)),
                    species=ConvergenceCriteriaItem(
                        absolute=self._ui.absoluteSpecies.pFloat(self.tr('Convergence Criteria Absolute Species'),
                                                                 low=0, high=1),
                        relative=self._ui.relativeSpecies.pFloat(self.tr('Convergence Criteria Relative Species'),
                                                                 low=0, high=1))))

            NumericalService.updateConditions(data)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return False

        return True

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._load()

        return super().showEvent(ev)

    def _connectSignalsSlots(self):
        Project.instance().solverStatusChanged.connect(self._updateEnabled)

        self._ui.advanced.clicked.connect(self._advancedSetup)
        self._ui.fluxType.currentIndexChanged.connect(self._onFluxTypeChanged)

        if ModelsDB.getMultiphaseModel() == MultiphaseModel.VOLUME_OF_FLUID:
            self._ui.discretizationSchemeTime.currentIndexChanged.connect(self._handleTimeDiscretizationSchemeChanged)

    def _updateEnabled(self):
        caseManager = CaseManager()
        self._ui.scrollArea.setEnabled(not caseManager.isBatchRunning())
        self._ui.advanced.setEnabled(not caseManager.isBatchRunning())

    def _advancedSetup(self):
        self._dialog = AdvancedDialog(self)
        self._dialog.open()

    def _onFluxTypeChanged(self):
        fluxType = self._ui.fluxType.currentData()
        self._ui.densityBasedSolverParametersLayout.setRowVisible(
            self._ui.entropyFixCoefficient, fluxType == FluxType.ROE_FDS)
        self._ui.densityBasedSolverParametersLayout.setRowVisible(
            self._ui.cutOffMachNumber, fluxType == FluxType.AUSM_UP)

    def _handleTimeDiscretizationSchemeChanged(self):
        if self._ui.discretizationSchemeTime.currentData() == ImplicitDiscretizationScheme.SECOND_ORDER_IMPLICIT:
            self._ui.discretizationSchemes.layout().setRowVisible(self._ui.crankNicolsonBlendingFactor, True)
            self._ui.multiphaseSteps.layout().setRowVisible(self._ui.multiphaseMaxIterationsPerTimeStep, False)
        else:
            self._ui.discretizationSchemes.layout().setRowVisible(self._ui.crankNicolsonBlendingFactor, False)
            self._ui.multiphaseSteps.layout().setRowVisible(self._ui.multiphaseMaxIterationsPerTimeStep, True)