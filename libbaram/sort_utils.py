#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Natural sort utilities.
#
# Standard string sort compares character by character, so names with
# unpadded numbers sort incorrectly (e.g. "case_1, case_10, case_2, ...").
# naturalKey() splits a string into digit / non-digit chunks and compares
# the digit chunks as integers, so "case_1, case_2, ..., case_10" sorts
# in the expected numeric order.

import re


def naturalKey(text):
    """
    Returns a sort key that orders embedded numbers numerically rather
    than lexicographically (e.g. 'item2' before 'item10').
    """
    return [int(chunk) if chunk.isdigit() else chunk.lower()
            for chunk in re.split(r'(\d+)', text)]
