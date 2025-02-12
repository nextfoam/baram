#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from uuid import UUID

from lxml import etree

from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.post_field import X_VELOCITY, Field, getFieldInstance
from baramFlow.coredb.scaffold import Scaffold


@dataclass
class BoundaryScaffold(Scaffold):
    bcid: str = '0'

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text
        bcid = e.find('bcid', namespaces=nsmap).text

        return BoundaryScaffold(uuid=uuid,
                          name=name,
                          bcid=bcid)

    def toElement(self):
        string = ('<boundary xmlns="http://www.baramcfd.org/baram">'
                 f'    <uuid>{str(self.uuid)}</uuid>'
                 f'    <name>{self.name}</name>'
                 f'    <bcid>{self.bcid}</bcid>'
                  '</boundary>')

        return etree.fromstring(string)
