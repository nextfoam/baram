#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from libbaram.pfloat import PFloat

from baramFlow.base.boundary.turbulence import KOmegaSpecification, BoundaryKOmega, KOmega, BoundaryTransitionSST
from baramFlow.base.boundary.turbulence import TransitionSST
from baramFlow.coredb import coredb
from baramFlow.coredb.turbulence_model_db import TurbulenceModelsDB, TurbulenceModel
from .turbulence_k_omega_widget_ui import Ui_turbulenceKOmegaWidget


class TurbulenceKOmegaWidget(QWidget):
    RELATIVE_XPATH = '/turbulence'

    def __init__(self, xpath):
        super().__init__()
        self._ui = Ui_turbulenceKOmegaWidget()
        self._ui.setupUi(self)

        self._ui.specificationMethod.addItem(self.tr("K and Omega"),
                                             KOmegaSpecification.K_AND_OMEGA)
        self._ui.specificationMethod.addItem(self.tr("Intensity and Viscosity Ratio"),
                                             KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO)

        self._xpath = xpath

        self._connectSignalsSlots()

    def on(self):
        return True

    def load(self):
        db = coredb.CoreDB()
        xpath = self._xpath + self.RELATIVE_XPATH

        self._ui.specificationMethod.setCurrentIndex(
            self._ui.specificationMethod.findData(KOmegaSpecification(db.getValue(xpath + '/k-omega/specification'))))
        self._ui.turbulentKineticEnergy.setText(db.getValue(xpath + '/k-omega/turbulentKineticEnergy'))
        self._ui.specificDissipationRate.setText(db.getValue(xpath + '/k-omega/specificDissipationRate'))
        self._ui.turbulentIntensity.setText(db.getValue(xpath + '/k-omega/turbulentIntensity'))
        self._ui.turbulentViscosityRatio.setText(db.getValue(xpath + '/k-omega/turbulentViscosityRatio'))
        self._specificationMethodChanged()

        if TurbulenceModelsDB.getRASModel() == TurbulenceModel.TRANSITION_SST:
            self._ui.intermittency.setText(db.getValue(xpath + '/transitionSST/intermittency'))
            self._ui.momentumThicknessRe.setText(db.getValue(xpath + '/transitionSST/momentumThicknessRe'))
        else:
            self._ui.transitionSST.setVisible(False)

    def appendToWriter(self, writer):
        return True

    def data(self):
        specification = self._ui.specificationMethod.currentData()
        kOmega = KOmega(specification=specification)
        if specification == KOmegaSpecification.K_AND_OMEGA:
            kOmega.turbulentKineticEnergy = str(
                PFloat(self._ui.turbulentKineticEnergy.text(), self.tr("Turbulent Kinetic Energy")))
            kOmega.specificDissipationRate = str(
                PFloat(self._ui.specificDissipationRate.text(), self.tr("Specific Dissipation Rate")))
        elif specification == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO:
            kOmega.turbulentIntensity = str(
                PFloat(self._ui.turbulentIntensity.text(), self.tr("Turbulent Intensity")))
            kOmega.turbulentViscosityRatio = str(
                PFloat(self._ui.turbulentViscosityRatio.text(), self.tr("Turbulent Viscosity Ratio")))

        if TurbulenceModelsDB.getRASModel() == TurbulenceModel.TRANSITION_SST:
            return BoundaryTransitionSST(
                kOmega=kOmega,
                transitionSST=TransitionSST(
                    intermittency=str(PFloat(self._ui.intermittency.text(), self.tr("Intermittency"), low=0, high=1)),
                    momentumThicknessRe=str(
                        PFloat(self._ui.momentumThicknessRe.text(), self.tr("Transition onset momentum-thickness Re"),
                               low=0))))
        else:
            return BoundaryKOmega(kOmega=kOmega)

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentIndexChanged.connect(self._specificationMethodChanged)

    def _specificationMethodChanged(self):
        specification = self._ui.specificationMethod.currentData()
        self._ui.kAndOmega.setVisible(specification == KOmegaSpecification.K_AND_OMEGA)
        self._ui.intensityAndViscocityRatio.setVisible(
            specification == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO)
