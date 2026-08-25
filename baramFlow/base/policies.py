#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.services.monitor.monitor_policy import MonitorPolicy
from baramFlow.services.region.region_service import RegionService


def connectSignalsToPolicies():
    RegionService.materialsUpdateRequested.connect(MonitorPolicy.checkRegionMaterialUpdateRequest)