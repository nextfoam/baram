#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import numpy as np


def rotationMatrix(axis, theta):
    """
    Return the rotation matrix associated with counterclockwise rotation about
    the given axis by theta radians.
    From StackOverflow, https://stackoverflow.com/a/6802723
    """
    axis = np.asarray(axis)
    axis = axis / math.sqrt(np.dot(axis, axis))
    a = math.cos(theta / 2.0)
    b, c, d = -axis * math.sin(theta / 2.0)
    aa, bb, cc, dd = a * a, b * b, c * c, d * d
    bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
    return np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                     [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                     [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])


def unitVector(v):
    return v / math.sqrt(np.dot(v, v))


def calucateDirectionsByRotation(drag, lift, aoa, aos):
    pitchAxis = np.cross(drag, lift)

    rotationAoA = rotationMatrix(pitchAxis, math.radians(aoa))
    rotationAoS = rotationMatrix(lift, (-1) * math.radians(aos))

    # Order of rotation is important

    # 1st. Apply Angle of Attack
    drag = np.dot(rotationAoA, drag)
    lift = np.dot(rotationAoA, lift)

    # 2nd. Apply Angle of AoS
    drag = np.dot(rotationAoS, drag)
    lift = np.dot(rotationAoS, lift)

    drag = unitVector(drag)
    lift = unitVector(lift)

    return list(drag), list(lift)
