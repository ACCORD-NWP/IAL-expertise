#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Useful functionalities for Experts.
"""
from __future__ import print_function, absolute_import, division, unicode_literals

FLOAT_RE = '(\+|\-)*((\d+(\.\d*)*)|(\.\d+))(E(\+|\-)\d+)*'


def difftree(test, ref, fatal_exceptions=False):
    """
    Walk a dict tree, and compute differences to a reference dict tree.
    When a branch is not found, the diff branch is replaced by an ad-hoc message.
    When an error is met in trying to compare, raise if **fatal_exceptions**
    or set an ad-hoc message.
    """
    diff = {}
    for k in ref.keys():
        if k not in test:
            diff[k] = comp_messages['missing']
        else:
            if isinstance(test[k], dict) and isinstance(ref[k], dict):
                diff[k] = difftree(test[k], ref[k])  # recursion !
            else:
                try:
                    diff[k] = test[k] - ref[k]
                except Exception:
                    if fatal_exceptions:
                        raise
                    else:
                        diff[k] = comp_messages['error']
    for k in test.keys():
        if k not in ref:
            diff[k] = comp_messages['new']
    return diff


def ppi(value):
    """
    Pretty Print for Integers.

    Examples:
    - if value=1 => '+1'
    - if value=-1 => '-1'
    - if value=0 => '0'
    """
    if int(value) == 0:
        sign = ''
    else:
        sign = '+'
    return ('{:' + sign + 'd}').format(value)


def ppp(value, threshold_exponent=2):
    """
    Pretty Print for Percentages, with a threshold.

    Examples:
    - if threshold_exponent=1, value=0.1 => '+10.0%'
    - if threshold_exponent=2, value=0.019 => '+1.90%'
    - if threshold_exponent=1, value=-0.001 => '-0.1%'
    - if threshold_exponent=1, value=-0.0005 => '-0.1%'
    - if threshold_exponent=1, value=-0.0004 => '0.0%'
    """
    if abs(value) < 0.5 * 10. ** (-threshold_exponent) / 100:
        sign = ''
        value = 0.
    else:
        sign = '+'
    return ('{:' + sign + '.' + str(threshold_exponent) + '%}').format(value)


#: Error messages in comparisons
comp_messages = {'missing':'!Missing in test!',
                 'error':'!ComparisonError!',
                 'new':'!New in test!'}

#: OOPS tests sample outputs
test_ad = '<Message file=".D[6]/test/base/TestSuiteOpObsTrajModel.h" line="153"><![CDATA[dx1.dx2 = -10551.185388577840058 dy1.dy2 = -10551.185388577810954 digits = 14.559351102071987683]]></Message>'
test_jo = '<Message file=".D[6]/test/base/TestSuiteOpObsTrajFile.h" line="106"><![CDATA[Jo = 543801527.59527683258]]></Message><Message file=".D[6]/test/base/TestSuiteVariationalFixture.h" line="250"><![CDATA[Expected result = 543801527 Digits: 8.9607214420661822629]]></Message> ALLOBS_OPER_MOD:OBS_OPER_DELETE instance=           0'
test_diff = '<Message file=".D[6]/test/base/TestSuiteModel.h" line="133"><![CDATA[||Mx-x|| = 43411459.225849807262||Mx|| = ]]></Message><Message file=".D[6]/test/base/TestSuiteVariationalFixture.h" line="250"><![CDATA[Expected result = 43411459 Digits: 8.2837846578541558529]]></Message></TestLog>'
test_diff2 = '<Message file=".D[6]/test/base/TestSuiteModel.h" line="98"><![CDATA[||Mx-x|| = 137534984.33869171143||Mx|| = ]]></Message><Message file=".D[6]/test/base/TestSuiteVariationalFixture.h" line="250"><![CDATA[Expected result = 9999 Digits: -4.1384250389422065908]]></Message></TestLog>'
