#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.base.region.regions_cache import regionCache


class CacheManager:
    @staticmethod
    def load():
        regionCache.load()