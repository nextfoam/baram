#!/usr/bin/env python
# -*- coding: utf-8 -*-
from baramFlow.base.numberical_condition.numberical_condition import NumericalConditions, NumericalAdvanced
from baramFlow.base.numberical_condition.update_models import NumericalUpdate
from baramFlow.base.project_data import projectData
from baramFlow.coredb.coredb import CoreDB


NUMERICAL_CONDITIONS_XPATH = '/numericalConditions'

class NumericalService:
    @staticmethod
    def getConditions():
        return projectData.numericalConditions

    @staticmethod
    def updateConditions(data: NumericalUpdate):
        new = NumericalConditions(pressureVelocityCouplingScheme=data.pressureVelocityCouplingScheme,
                                  densityBasedSolverParameters=data.densityBasedSolverParameters,
                                  useMomentumPredictor=data.useMomentumPredictor,
                                  discretizationSchemes=data.discretizationSchemes,
                                  underRelaxationFactors=data.underRelaxationFactors,
                                  highOrderTermRelaxation=data.highOrderTermRelaxation,
                                  maxIterationsPerTimeStep=data.maxIterationsPerTimeStep,
                                  numberOfCorrectors=data.numberOfCorrectors,
                                  numberOfNonOrthogonalCorrectors=data.numberOfNonOrthogonalCorrectors,
                                  multiphase=data.multiphase,
                                  convergenceCriteria=data.convergenceCriteria,
                                  advanced=projectData.numericalConditions.advanced)

        if new == projectData.numericalConditions:
            return

        projectData.numericalConditions = new

        db = CoreDB()
        db.replaceElement(NUMERICAL_CONDITIONS_XPATH, projectData.numericalConditions.toElement())

    @staticmethod
    def updateAdvanced(data: NumericalAdvanced):
        if data == projectData.numericalConditions.advanced:
            return

        projectData.numericalConditions.advanced = data

        db = CoreDB()
        db.replaceElement(NUMERICAL_CONDITIONS_XPATH + '/advanced',
                          projectData.numericalConditions.advanced.toElement())
