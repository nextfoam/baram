#!/usr/bin/env python
# -*- coding:, # utf-8 -*-

from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.openfoam.constant.cloud_properties import CloudProperties


class KinematicCloudProperties(CloudProperties):
    def __init__(self, rname: str):
        super().__init__(rname, 'cloudProperties')

    def build(self):
        if self._data is not None:
            return self

        self._buildBaseCloudProperties(DPMModelManager.properties())

        return self
