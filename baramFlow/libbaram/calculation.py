#!/usr/bin/env python
# -*- coding: utf-8 -*-


class AverageCalculator:
    def __init__(self):
        self._totalValue = 0
        self._totalRatio = 0

    def add(self, value, ratio):
        self._totalValue += value * ratio
        self._totalRatio += ratio

    def average(self):
        if self._totalRatio == 0:
            return 0

        return self._totalValue / self._totalRatio
