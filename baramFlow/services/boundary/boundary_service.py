#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from baramFlow.app import app
from baramFlow.base.boundary.boundary import PatchInteraction
from baramFlow.base.boundary.boundary_data import BoundaryData
from baramFlow.base.boundary.wall import WallHeatTransfer
from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from baramFlow.coredb.coredb import CoreDB
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.libdb import ValueException, nsmap
from baramFlow.services.region.region_service import RegionService


@dataclass
class BoundaryTypeAndCouplePatch:
    bcid: str
    bctype: BoundaryType = None
    coupledBoundary: str = None

    def applyToDB(self, db):
        xpath = BoundaryDB.getXPath(self.bcid)

        if self.bctype is not None:
            db.setValue(xpath + '/physicalType', self.bctype.value)

        if self.coupledBoundary is not None:
            db.setValue(xpath + '/coupledBoundary', self.coupledBoundary)


class BoundaryService:
    @classmethod
    def updateBoundaryCondition(cls, bcid, condition, writer: CoreDBWriter = None):
        boundary = cls.getBoundary(bcid).boundary

        couplingAffected = None
        if BoundaryDB.needsCoupledBoundary(boundary.bctype):
            couplingAffected = cls.makePatchToUpdateCouple(boundary, cls.getBoundary(condition.coupledBoundary).boundary)

        try:
            with CoreDB() as db:
                condition.applyToDB(db, bcid)

                if writer is not None:
                    writer.updateInDB(db)

                if couplingAffected is not None:
                    for a in couplingAffected:
                        cls.updateTypeAndCoupleWithPatch(db, a)

                db.increaseConfigCount()
        except ValueError as e:
            raise e
        finally:
            if couplingAffected is None:
                RegionService.reloadBoundary(bcid)
            else:
                for a in couplingAffected:
                    RegionService.reloadBoundary(a.bcid)

    @staticmethod
    def updateTypeAndCoupleWithPatch(db, patch: BoundaryTypeAndCouplePatch):
        patch.applyToDB(db)
        if patch.bctype is not None:
            interactionType = DPMModelManager.getDefaultPatchInteractionType(patch.bctype)
            db.setValue(BoundaryDB.getXPath(patch.bcid) + '/patchInteraction/type', interactionType.value)

    @staticmethod
    def makePatchToUpdateCouple(boundary: BoundaryData, partner: BoundaryData):
        if boundary.coupledBoundary == partner.bcid:
            return None

        affected = [BoundaryTypeAndCouplePatch(bcid=boundary.bcid,
                                               coupledBoundary=partner.bcid),
                    BoundaryTypeAndCouplePatch(bcid=partner.bcid,
                                               coupledBoundary=boundary.bcid,
                                               bctype=boundary.bctype if boundary.bctype != partner.bctype else None)]

        if boundary.coupledBoundary != '0':
            affected.append(BoundaryTypeAndCouplePatch(bcid=boundary.coupledBoundary,
                                                       coupledBoundary='0'))
        if partner.coupledBoundary != '0':
            affected.append(BoundaryTypeAndCouplePatch(bcid=partner.coupledBoundary,
                                                       coupledBoundary='0'))

        return affected

    @staticmethod
    def updateBoundaryType(bcid: str, newType: BoundaryType):
        boundaryModel = BoundaryService.getBoundary(bcid)
        if boundaryModel.bctype == newType:
            return

        keepCouple= True
        if boundaryModel.boundary.coupledBoundary != '0':
            coupleModel = BoundaryService.getBoundary(boundaryModel.boundary.coupledBoundary)
            if (not BoundaryDB.needsCoupledBoundary(newType)
                    or (newType != BoundaryType.THERMO_COUPLED_WALL and boundaryModel.rname != coupleModel.rname)
                    or bcid != coupleModel.boundary.coupledBoundary):
                keepCouple = False

        boundaryPatch = BoundaryTypeAndCouplePatch(bcid=bcid,
                                                     bctype=newType)
        couplePatch = BoundaryTypeAndCouplePatch(bcid=boundaryModel.boundary.coupledBoundary)

        if keepCouple:
            couplePatch.bctype = newType
        else:
            boundaryPatch.coupledBoundary = '0'
            couplePatch.coupledBoundary = '0'

        with CoreDB() as db:
            BoundaryService.updateTypeAndCoupleWithPatch(db, boundaryPatch)
            if couplePatch.bcid != '0':
                BoundaryService.updateTypeAndCoupleWithPatch(db, couplePatch)

            RegionService.reloadBoundary(bcid)
            if couplePatch.bcid != '0':
                RegionService.reloadBoundary(couplePatch.bcid)

    @staticmethod
    def patchInteraction(bcid: str):
        return PatchInteraction.fromElement(CoreDB().getElement(BoundaryDB.getXPath(bcid) + '/patchInteraction'))

    @staticmethod
    def updatePatchInteractionInDB(db, bcid, patchInteraction):
        db.replaceElement(BoundaryDB.getXPath(bcid) + '/patchInteraction', patchInteraction.toElement())
        db.increaseConfigCount()

    @staticmethod
    def updateWallHeatTransferInDB(db, bcid, new: WallHeatTransfer):
        boundary = RegionService.getBoundary(bcid).boundary
        boundary.wall.heatTransfer.update(new)

        try:
            wall = db.getElement(BoundaryDB.getXPath(bcid) + '/wall')
            wall.replace(wall.find('heatTransfer', namespaces=nsmap), boundary.wall.heatTransfer.toElement())

            db.increaseConfigCount()
        except ValueException as e:
            raise ValueError(e)

    @staticmethod
    def getBoundary(bcid):
        return RegionService.getBoundary(bcid)

    @staticmethod
    def getBoundaries():
        return RegionService.getBoundaries()

    @staticmethod
    def getBoundariesIn(rname):
        return RegionService.getBoundariesIn(rname)

    @staticmethod
    def getZoneAverageDirectionForFan(bcid, bcidOfCouple):
        boundary = RegionService.getBoundary(bcid)
        couple = RegionService.getBoundary(bcidOfCouple)

        master = boundary if boundary.startFace < couple.startFace else couple
        if master.zoneAverageDirection is None:
            master.zoneAverageDirection = app.meshModel().actorInfo(int(master.bcid)).getZoneAverageDirection()

        return master.zoneAverageDirection

