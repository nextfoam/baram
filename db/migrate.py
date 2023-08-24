#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .configurations_schema import CFDType


def migrate(data):
    cfdTypes = [e.value for e in CFDType]
    for geometry in data['geometry'].values():
        if geometry['cfdType'] not in cfdTypes:
            geometry['cfdType'] = CFDType.INTERFACE.value

    return data