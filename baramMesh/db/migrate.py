#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .configurations_schema import CFDType, CURRENT_CONFIGURATIONS_VERSION, CONFIGURATIONS_VERSION_KEY


def migrate(data):
    version = int(data.get(CONFIGURATIONS_VERSION_KEY, 0))

    if version > CURRENT_CONFIGURATIONS_VERSION:
        assert 'Invalid data version.'

    if version < 1:
        print('Loaded data has no version information. It is assumes as version 1.')

    data[CONFIGURATIONS_VERSION_KEY] = CURRENT_CONFIGURATIONS_VERSION

    return data
