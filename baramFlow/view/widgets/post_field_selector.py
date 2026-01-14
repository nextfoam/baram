#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.base.constants import FieldType
from baramFlow.base.field import Field
from baramFlow.openfoam.solver_field import getAvailableFields


def loadFieldsComboBox(fieldComboBox, includeCoordinate=False):
    for field in getAvailableFields(includeCoordinate):
        fieldComboBox.addItem(field.text, field)


def connectFieldsToComponents(fieldComboBox, componentComboBox):
    def updateComponentComboBox():
        field: Field = fieldComboBox.currentData()
        if field and field.type == FieldType.VECTOR:
            componentComboBox.setEnabled(True)
            componentComboBox.setCurrentIndex(0)
        else:
            componentComboBox.setEnabled(False)

    fieldComboBox.currentIndexChanged.connect(updateComponentComboBox)
    updateComponentComboBox()