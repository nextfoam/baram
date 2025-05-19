#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum


class TimeSteppingMethod(Enum):
    FIXED = "fixed"
    ADAPTIVE = "adaptive"


class DataWriteFormat(Enum):
    BINARY = "binary"
    ASCII = "ascii"


class RunCalculationDB:
    RUN_CALCULATION_XPATH = '/runCalculation'
