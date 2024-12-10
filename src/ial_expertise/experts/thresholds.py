#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Thresholds for validation of various comparisons.
"""

#: Threshold in Jo relative difference for validation
JO = 1e-8
#: Threshold in Jo AD test number of equal digits to validate
JOAD_DIGITS = 10
#: Threshold in *States diff* relative difference for validation
STATESDIFF = 1e-6
#: Threshold in variances (OOPS ensembles) for validation
VARIANCES = 1e-8
#: Threshold for number of different digits in norms for Bit-Reproducibility
NORMSDIGITS_BITREPRO = 0
#: Threshold for number of different digits in norms for Suspicious result
NORMSDIGITS_SUSPICIOUS = 1
#: Thresholds for validation of Jo-Tables
JOTABLES = {'n':{'diff':1, 'reldiff':0.001},
            'jo':{'diff':0.1, 'reldiff':0.001},
            'jo/n':{'diff':0.01, 'reldiff':0.001},}
#: Threshold for number of observations
OBSERVATIONS_NUMBER = 1
#: Threshold for maximum error between 2 fields
FIELDS_MAX_DIFF = 1e-15
#: Threshold for maximum relative error between 2 fields
FIELDS_MAX_RELDIFF = 1e-6
#: Threshold for error on normalized fields diff
NORMALIZED_FIELDS_DIFF = 1e-12
#: Canari statistics (OBS-MOD & SIGMA) absolute error
CANARISTATS_VALIDATION = 1e-3


#: Threshold for bit-reproducibility
EPSILON = 1e-15
#: Tolerance factor to define *significant_digits* for a new EXPECTED_RESULT
EXPECTED_RESULT_TOLERANCE_FACTOR = 0.8
