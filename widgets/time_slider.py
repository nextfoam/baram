#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QLabel, QSlider

class TimeSlider(QObject):
    currentTimeChanged = Signal(str)
    lastTimeChanged = Signal(str)

    def __init__(self, uiSlider: QSlider, uiCurrentTime: QLabel, uiLastTime: QLabel):
        super().__init__()

        self._timeValues = ['0']

        self._uiCurrentTIme = uiCurrentTime
        self._uiLastTIme = uiLastTime
        self._slider = uiSlider

        self._uiCurrentTIme.setText('0')
        self._uiLastTIme.setText('0')

        self._slider.setRange(0, 0)
        self._slider.setTracking(False)

        self._slider.sliderMoved.connect(self._sliderMoved)
        self._slider.valueChanged.connect(self._sliderValueChanged)

    def setDisable(self):
        self._slider.setEnabled(False)

    def setEnable(self):
        self._slider.setEnabled(True)

    def getCurrentTime(self) -> str:
        return self._timeValues[self._slider.value()]

    def setCurrentTime(self, time: str):
        if time in self._timeValues:
            index = self._timeValues.index(time)
            self._slider.setValue(index)
            self._uiCurrentTIme.setText(self._timeValues[index])

    def updateTimeValues(self, timeValues: list[str]):
        if (len(self._timeValues) == len(timeValues)
            and self._timeValues[-1] == timeValues[-1]):
            return

        currentTime = self._timeValues[self._slider.value()]
        if currentTime in timeValues:
            self._slider.setValue(timeValues.index(currentTime))
        else:
            self._slider.setValue(0)
            self.currentTimeChanged.emit('0')

        self._slider.setMaximum(len(timeValues)-1)

        if self._timeValues[-1] != timeValues[-1]:
            self._uiLastTIme.setText(timeValues[-1])
            self.lastTimeChanged.emit(timeValues[-1])

        self._timeValues = timeValues

    def _sliderMoved(self, index):
        self._uiCurrentTIme.setText(self._timeValues[index])

    def _sliderValueChanged(self, index):
        self._uiCurrentTIme.setText(self._timeValues[index])
        self.currentTimeChanged.emit(self._timeValues[index])
