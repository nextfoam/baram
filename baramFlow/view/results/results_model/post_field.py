#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QCoreApplication

from baramFlow.coredb import post_field


FIELD_TEXTS = {
    post_field.X_COORDINATE: QCoreApplication.translate('PostField', 'X-Coordinate'),
    post_field.Y_COORDINATE: QCoreApplication.translate('PostField', 'Y-Coordinate'),
    post_field.Z_COORDINATE: QCoreApplication.translate('PostField', 'Z-Coordinate'),
    post_field.PRESSURE: QCoreApplication.translate('PostField', 'Pressure'),
    post_field.SPEED: QCoreApplication.translate('PostField', 'Speed'),
    post_field.X_VELOCITY: QCoreApplication.translate('PostField', 'X-Velocity'),
    post_field.Y_VELOCITY: QCoreApplication.translate('PostField', 'Y-Velocity'),
    post_field.Z_VELOCITY: QCoreApplication.translate('PostField', 'Z-Velocity'),
    post_field.TURBULENT_KINETIC_ENERGY: QCoreApplication.translate('PostField', 'Turbulent Kinetic Energy'),
    post_field.TURBULENT_DISSIPATION_RATE: QCoreApplication.translate('PostField', 'Turbulent Dissipation Rate'),
    post_field.SPECIFIC_DISSIPATION_RATE: QCoreApplication.translate('PostField', 'Specific Dissipation Rate'),
    post_field.MODIFIED_TURBULENT_VISCOSITY: QCoreApplication.translate('PostField', 'Modified Turbulent Viscosity'),
    post_field.TEMPERATURE: QCoreApplication.translate('PostField', 'Temperature'),
    post_field.DENSITY: QCoreApplication.translate('PostField', 'Density'),
    post_field.AGE: QCoreApplication.translate('PostField', 'Age'),
    post_field.HEAT_TRANSFER_COEFF: QCoreApplication.translate('PostField', 'Heat Transfer Coefficient'),
    post_field.MACH_NUMBER: QCoreApplication.translate('PostField', 'Mach Number'),
    post_field.Q: QCoreApplication.translate('PostField', 'Q'),
    post_field.TOTAL_PRESSURE: QCoreApplication.translate('PostField', 'Total Pressure'),
    post_field.VORTICITY: QCoreApplication.translate('PostField', 'Vorticity'),
    post_field.WALL_HEAT_FLUX: QCoreApplication.translate('PostField', 'Wall Heat Flux'),
    post_field.WALL_SHEAR_STRESS: QCoreApplication.translate('PostField', 'Wall Shear Stress'),
    post_field.WALL_Y_PLUS: QCoreApplication.translate('PostField', 'Wall Y Plus'),

}
