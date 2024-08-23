#!/usr/bin/env python
# -*- coding: utf-8 -*-

class ConfigurationException(Exception):
    def __init__(self, msg: str = None):
        super().__init__(msg)
