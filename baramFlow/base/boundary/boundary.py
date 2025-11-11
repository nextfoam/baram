#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from enum import Enum
from xml.etree.ElementTree import Element

from lxml import etree

from baramFlow.base.base import BatchableNumber
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.libdb import nsmap


class WallInteractionType(Enum):
    NONE    = 'none'
    REFLECT = 'reflect'
    ESCAPE  = 'escape'
    TRAP    = 'trap'
    RECYCLE = 'recycle'


@dataclass
class CoefficientOfRestitution:
    normal: BatchableNumber
    tangential: BatchableNumber

    @staticmethod
    def fromElement(e):
        return CoefficientOfRestitution(normal=BatchableNumber.fromElement(e.find('normal', namespaces=nsmap)),
                                        tangential=BatchableNumber.fromElement(e.find('tangential', namespaces=nsmap)))


@dataclass
class RecycleProperties:
    recycleBoundary: str
    recycleFraction: BatchableNumber

    @staticmethod
    def fromElement(e):
        return RecycleProperties(
            recycleBoundary=e.find('recycleBoundary', namespaces=nsmap).text,
            recycleFraction=BatchableNumber.fromElement(e.find('recycleFraction', namespaces=nsmap)))


@dataclass
class WallInteraction:
    type: WallInteractionType
    reflect: CoefficientOfRestitution
    recycle: RecycleProperties

    @staticmethod
    def fromElement(e):
        return WallInteraction(
            type=WallInteractionType(e.find('type', namespaces=nsmap).text),
            reflect=CoefficientOfRestitution.fromElement(e.find('reflect/coefficientOfRestitution', namespaces=nsmap)),
            recycle=RecycleProperties.fromElement(e.find('recycle', namespaces=nsmap)))

    def toElement(self):
        return etree.fromstring(
            f'''
                <wallInteraction xmlns="http://www.baramcfd.org/baram">
                    <type>{self.type.value}</type>
                    <reflect>
                        <coefficientOfRestitution>
                            {self.reflect.normal.toXML('normal')}
                            {self.reflect.tangential.toXML('tangential')}
                        </coefficientOfRestitution>
                    </reflect>
                    <recycle>
                        <recycleBoundary>{self.recycle.recycleBoundary}</recycleBoundary>
                        {self.recycle.recycleFraction.toXML('recycleFraction')}
                    </recycle>
                </wallInteraction>
            '''
        )


class BoundaryManager:
    @staticmethod
    def wallInteraction(bcid):
        return WallInteraction.fromElement(coredb.CoreDB().getElement(BoundaryDB.getXPath(bcid) + '/wall/wallInteraction'))

    @staticmethod
    def updateWallInteraction(db, bcid, wallInteraction):
        wall = db.getElement(BoundaryDB.getXPath(bcid) + '/wall')

        new: Element = wallInteraction.toElement()

        for i, child in enumerate(wall):
            if child.tag == new.tag:
                wall.remove(child)
                wall.insert(i, new)
                break
        else:
            assert False

        db.increaseConfigCount()


