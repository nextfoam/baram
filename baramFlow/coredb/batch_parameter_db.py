#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb import coredb


BATCH_PARAMETER_PATTERN = '[A-Z_][A-Z0-9_]*'
BATCH_ARGUMENT_PATTERN = f'\${BATCH_PARAMETER_PATTERN}'

BATCH_PARAMETER_EXPRESSION = f'^{BATCH_PARAMETER_PATTERN}$'
BATCH_ARGUMENT_EXPRESSION = f'^{BATCH_ARGUMENT_PATTERN}$'


class BatchParametersDB:
    BATCH_PARAMETERS_XPATH = '/runCalculation/batch/parameters'

    @classmethod
    def batchParameterXPath(cls, name):
        return f'/runCalculation/batch/parameters/parameter[name="{name}"]'

    @classmethod
    def defaultValue(cls, name):
        return coredb.CoreDB().getElement(cls.batchParameterXPath(name) + '/value').text

