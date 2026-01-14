#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from baramFlow.base.constants import FieldType, VectorComponent
from baramFlow.base.field import getFieldInstance, Field
from baramFlow.coredb.coredb import CoreDB, nsmap
from baramFlow.openfoam.solver_field import getSolverComponentName, getSolverFieldName



@dataclass
class MonitorField():
    field: Field
    component: VectorComponent

    def displayText(self):
        if self.field.type == FieldType.SCALAR:
            return self.field.text

        if self.component == VectorComponent.X:
            component = 'X'
        elif self.component == VectorComponent.Y:
            component = 'Y'
        elif self.component == VectorComponent.Z:
            component = 'Z'
        else:
            component = 'Magnitude'

        return f'{component}-{self.field.text}'

    def openfoamField(self):
        if self.field.type == FieldType.VECTOR:
            return getSolverComponentName(self.field, self.component)

        return getSolverFieldName(self.field)



def getMonitorField(xpath):
    element = CoreDB().getElement(xpath)

    return MonitorField(getFieldInstance(element.find('fieldCategory', namespaces=nsmap).text,
                                         element.find('fieldCodeName', namespaces=nsmap).text),
                        VectorComponent(int(element.find('fieldComponent', namespaces=nsmap).text)))
