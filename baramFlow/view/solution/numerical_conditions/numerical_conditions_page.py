#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.numerical_db import PressureVelocityCouplingScheme
from baramFlow.coredb.numerical_db import ImplicitDiscretizationScheme, UpwindDiscretizationScheme, InterpolationScheme
from baramFlow.coredb.numerical_db import NumericalDB
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel
import baramFlow.openfoam.solver
from baramFlow.view.widgets.content_page import ContentPage
from .numerical_conditions_page_ui import Ui_NumericalConditionsPage
from .advanced_dialog import AdvancedDialog


class NumericalConditionsPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_NumericalConditionsPage()
        self._ui.setupUi(self)

        upwindDiscretizationSchemes = {
            UpwindDiscretizationScheme.FIRST_ORDER_UPWIND: self.tr('First Order Upwind'),
            UpwindDiscretizationScheme.SECOND_ORDER_UPWIND: self.tr('Second Order Upwind'),
        }

        self._ui.pressureVelocityCouplingScheme.addItems({
            PressureVelocityCouplingScheme.SIMPLE: self.tr('SIMPLE'),
            PressureVelocityCouplingScheme.SIMPLEC: self.tr('SIMPLEC'),
        })
        self._ui.discretizationSchemeTime.addItems({
            ImplicitDiscretizationScheme.FIRST_ORDER_IMPLICIT: self.tr('First Order Implicit'),
            ImplicitDiscretizationScheme.SECOND_ORDER_IMPLICIT: self.tr('Second Order Implicit'),
        })
        self._ui.discretizationSchemeMomentum.addItems(upwindDiscretizationSchemes)
        self._ui.discretizationSchemeEnergy.addItems(upwindDiscretizationSchemes)
        self._ui.discretizationSchemeTurbulence.addItems(upwindDiscretizationSchemes)
        self._ui.discretizationSchemeVolumeFraction.addItems(upwindDiscretizationSchemes)
        self._ui.discretizationSchemePressure.addItems({
            InterpolationScheme.LINEAR: self.tr('Linear'),
            InterpolationScheme.MOMENTUM_WEIGHTED_RECONSTRUC: self.tr('Momentum Weighted Reconstruct'),
            InterpolationScheme.MOMENTUM_WEIGHTED: self.tr('Momentum Weighted'),
        })

        self._xpath = NumericalDB.NUMERICAL_CONDITIONS_XPATH
        self._dialog = None

        self._connectSignalsSlots()

    def _load(self):
        timeIsTransient = GeneralDB.isTimeTransient()
        energyOn = ModelsDB.isEnergyModelOn()
        turbulenceOn = ModelsDB.getTurbulenceModel() not in (TurbulenceModel.INVISCID, TurbulenceModel.LAMINAR)
        multiphaseOn = ModelsDB.isMultiphaseModelOn()

        solvers = baramFlow.openfoam.solver.findSolvers()
        if len(solvers) == 0:  # No matching solver found
            raise RuntimeError
        solverCapability = baramFlow.openfoam.solver.getSolverCapability(solvers[0])
        allRoundSolver: bool = solverCapability['timeTransient'] and solverCapability['timeSteady']  # this solver is able to solve both steady and transient

        self._ui.useMomentumPredictor.setVisible(timeIsTransient or allRoundSolver)

        self._ui.discretizationSchemeTime.setEnabled(timeIsTransient)
        self._ui.discretizationSchemeEnergy.setEnabled(energyOn)
        self._ui.discretizationSchemeTurbulence.setEnabled(turbulenceOn)
        self._ui.discretizationSchemeVolumeFraction.setEnabled(multiphaseOn)

        self._ui.underRelaxationFactorPressureFinal.setEnabled(timeIsTransient or allRoundSolver)
        self._ui.underRelaxationFactorMomentumFinal.setEnabled(timeIsTransient or allRoundSolver)
        self._ui.underRelaxationFactorEnergy.setEnabled(energyOn)
        self._ui.underRelaxationFactorEnergyFinal.setEnabled((timeIsTransient or allRoundSolver) and energyOn)
        self._ui.underRelaxationFactorTurbulence.setEnabled(turbulenceOn)
        self._ui.underRelaxationFactorTurbulenceFinal.setEnabled((timeIsTransient or allRoundSolver) and turbulenceOn)
        self._ui.underRelaxationFactorDensityFinal.setEnabled(timeIsTransient or allRoundSolver)
        self._ui.underRelaxationFactorVolumeFraction.setEnabled(multiphaseOn)
        self._ui.underRelaxationFactorVolumeFractionFinal.setEnabled(multiphaseOn)

        self._ui.maxIterationsPerTimeStep.setEnabled(timeIsTransient or allRoundSolver)
        self._ui.numberOfCorrectors.setEnabled(timeIsTransient or allRoundSolver)

        if multiphaseOn:
            self._ui.multiphaseMaxIterationsPerTimeStep.setEnabled(True)
            self._ui.multiphaseNumberOfCorrectors.setEnabled(True)
        else:
            self._ui.multiphase.setEnabled(False)

        self._ui.relativePressure.setEnabled(timeIsTransient or allRoundSolver)
        self._ui.relativeMomentum.setEnabled(timeIsTransient or allRoundSolver)
        self._ui.absoluteEnergy.setEnabled(energyOn)
        self._ui.relativeEnergy.setEnabled((timeIsTransient or allRoundSolver) and energyOn)
        self._ui.absoluteTurbulence.setEnabled(turbulenceOn)
        self._ui.relativeTurbulence.setEnabled((timeIsTransient or allRoundSolver) and turbulenceOn)
        self._ui.absoluteVolumeFraction.setEnabled(multiphaseOn)
        self._ui.relativeVolumeFraction.setEnabled(multiphaseOn)

        db = coredb.CoreDB()

        self._ui.pressureVelocityCouplingScheme.setCurrentData(
            PressureVelocityCouplingScheme(db.getValue(self._xpath + '/pressureVelocityCouplingScheme')))
        self._ui.useMomentumPredictor.setChecked(db.getValue(self._xpath + '/useMomentumPredictor') == 'true')
        self._ui.discretizationSchemeTime.setCurrentData(
            ImplicitDiscretizationScheme(db.getValue(self._xpath + '/discretizationSchemes/time')))
        self._ui.discretizationSchemeMomentum.setCurrentData(
            UpwindDiscretizationScheme(db.getValue(self._xpath + '/discretizationSchemes/momentum')))
        self._ui.discretizationSchemeEnergy.setCurrentData(
            UpwindDiscretizationScheme(db.getValue(self._xpath + '/discretizationSchemes/energy')))
        self._ui.discretizationSchemeTurbulence.setCurrentData(
            UpwindDiscretizationScheme(db.getValue(self._xpath + '/discretizationSchemes/turbulentKineticEnergy')))
        self._ui.discretizationSchemeVolumeFraction.setCurrentData(
            UpwindDiscretizationScheme(db.getValue(self._xpath + '/discretizationSchemes/volumeFraction')))
        self._ui.discretizationSchemePressure.setCurrentData(
            InterpolationScheme(db.getValue(self._xpath + '/discretizationSchemes/pressure')))

        self._ui.underRelaxationFactorPressure.setText(
            db.getValue(self._xpath + '/underRelaxationFactors/pressure'))
        self._ui.underRelaxationFactorPressureFinal.setText(
            db.getValue(self._xpath + '/underRelaxationFactors/pressureFinal'))
        self._ui.underRelaxationFactorMomentum.setText(
            db.getValue(self._xpath + '/underRelaxationFactors/momentum'))
        self._ui.underRelaxationFactorMomentumFinal.setText(
            db.getValue(self._xpath + '/underRelaxationFactors/momentumFinal'))
        self._ui.underRelaxationFactorEnergy.setText(db.getValue(self._xpath + '/underRelaxationFactors/energy'))
        self._ui.underRelaxationFactorEnergyFinal.setText(
            db.getValue(self._xpath + '/underRelaxationFactors/energyFinal'))
        self._ui.underRelaxationFactorTurbulence.setText(
            db.getValue(self._xpath + '/underRelaxationFactors/turbulence'))
        self._ui.underRelaxationFactorTurbulenceFinal.setText(
            db.getValue(self._xpath + '/underRelaxationFactors/turbulenceFinal'))
        self._ui.underRelaxationFactorDensity.setText(
            db.getValue(self._xpath + '/underRelaxationFactors/density'))
        self._ui.underRelaxationFactorDensityFinal.setText(
            db.getValue(self._xpath + '/underRelaxationFactors/densityFinal'))
        self._ui.underRelaxationFactorVolumeFraction.setText(
            db.getValue(self._xpath + '/underRelaxationFactors/volumeFraction'))
        self._ui.underRelaxationFactorVolumeFractionFinal.setText(
            db.getValue(self._xpath + '/underRelaxationFactors/volumeFractionFinal'))

        self._ui.limitingFactor.setText(db.getValue(self._xpath + '/highOrderTermRelaxation/relaxationFactor'))
        self._ui.improveStablitiy.setChecked(
            db.getAttribute(self._xpath + '/highOrderTermRelaxation', 'disabled') == 'false')

        self._ui.maxIterationsPerTimeStep.setText(db.getValue(self._xpath + '/maxIterationsPerTimeStep'))
        self._ui.numberOfCorrectors.setText(db.getValue(self._xpath + '/numberOfCorrectors'))

        self._ui.multiphaseMaxIterationsPerTimeStep.setText(
            db.getValue(self._xpath + '/multiphase/maxIterationsPerTimeStep'))
        self._ui.multiphaseNumberOfCorrectors.setText(
            db.getValue(self._xpath + '/multiphase/numberOfCorrectors'))
        if db.getValue(self._xpath + '/multiphase/useSemiImplicitMules') == 'true':
            self._ui.mulesSemiImplicit.setChecked(True)
        else:
            self._ui.mullesExplicit.setChecked(True)
        self._ui.phaseInterfaceCompressionFactor.setText(
            db.getValue(self._xpath + '/multiphase/phaseInterfaceCompressionFactor'))
        self._ui.numberOfMulesIterations.setText(
            db.getValue(self._xpath + '/multiphase/numberOfMulesIterations'))

        self._ui.absolutePressure.setText(db.getValue(self._xpath + '/convergenceCriteria/pressure/absolute'))
        self._ui.relativePressure.setText(db.getValue(self._xpath + '/convergenceCriteria/pressure/relative'))
        self._ui.absoluteMomentum.setText(db.getValue(self._xpath + '/convergenceCriteria/momentum/absolute'))
        self._ui.relativeMomentum.setText(db.getValue(self._xpath + '/convergenceCriteria/momentum/relative'))
        self._ui.absoluteEnergy.setText(db.getValue(self._xpath + '/convergenceCriteria/energy/absolute'))
        self._ui.relativeEnergy.setText(db.getValue(self._xpath + '/convergenceCriteria/energy/relative'))
        self._ui.absoluteTurbulence.setText(db.getValue(self._xpath + '/convergenceCriteria/turbulence/absolute'))
        self._ui.relativeTurbulence.setText(db.getValue(self._xpath + '/convergenceCriteria/turbulence/relative'))
        self._ui.absoluteVolumeFraction.setText(
            db.getValue(self._xpath + '/convergenceCriteria/volumeFraction/absolute'))
        self._ui.relativeVolumeFraction.setText(
            db.getValue(self._xpath + '/convergenceCriteria/volumeFraction/relative'))

    def save(self):
        writer = CoreDBWriter()
        writer.append(self._xpath + '/pressureVelocityCouplingScheme',
                      self._ui.pressureVelocityCouplingScheme.currentValue(), None)
        writer.append(self._xpath + '/useMomentumPredictor',
                      'true' if self._ui.useMomentumPredictor.isChecked() else 'false', None)

        writer.append(self._xpath + '/discretizationSchemes/time',
                      self._ui.discretizationSchemeTime.currentValue(), None)
        writer.append(self._xpath + '/discretizationSchemes/momentum',
                      self._ui.discretizationSchemeMomentum.currentValue(), None)
        writer.append(self._xpath + '/discretizationSchemes/energy',
                      self._ui.discretizationSchemeEnergy.currentValue(), None)
        writer.append(self._xpath + '/discretizationSchemes/turbulentKineticEnergy',
                      self._ui.discretizationSchemeTurbulence.currentValue(), None)
        writer.append(self._xpath + '/discretizationSchemes/volumeFraction',
                      self._ui.discretizationSchemeVolumeFraction.currentValue(), None)
        writer.append(self._xpath + '/discretizationSchemes/pressure',
                      self._ui.discretizationSchemePressure.currentValue(), None)

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

    def _advancedSetup(self):
        self._dialog = AdvancedDialog()
        self._dialog.open()

    def _setupCombo(self, combo, items):
        for value, text in items.items():
            combo.addItem(text, value)
