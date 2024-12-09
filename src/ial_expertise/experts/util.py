#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Useful functionalities for Experts.
"""

FLOAT_RE = r'(\+|\-)*((\d+(\.\d*)*)|(\.\d+))((E|e)(\+|\-)\d+)*'
NAN_RE = '(NaN)|(nan)|(NAN)'
INFINITY_RE = r'(\+|\-)*((Infinity)|(inf)|(Inf))'
EXTENDED_FLOAT_RE = '({})'.format('|'.join(['({})'.format(expr)
                                            for expr in (FLOAT_RE,
                                                         NAN_RE,
                                                         INFINITY_RE)]))


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
test_ad2 = '<Message file=".D[83]/testsuite/TestSuiteOpObsTrajFile.h" line="175"><![CDATA[dx1.dx2 = -1.0476904596503497304e-05 dy1.dy2 = -1.0476904596503483751e-05 digits = 14.888212703032722928]]></Message> ALLOBS_OPER_MOD:OBS_OPER_DELETE instance=           1'
test_jo = '<Message file=".D[6]/test/base/TestSuiteOpObsTrajFile.h" line="106"><![CDATA[Jo = 543801527.59527683258]]></Message><Message file=".D[6]/test/base/TestSuiteVariationalFixture.h" line="250"><![CDATA[Expected result = 543801527 Digits: 8.9607214420661822629]]></Message> ALLOBS_OPER_MOD:OBS_OPER_DELETE instance=           0'
test_jo2 = '<Message file=".D[83]/testsuite/TestSuiteOpObsTrajFile.h" line="105"><![CDATA[Jo = 0]]></Message><Message file=".D[83]/testsuite/TestSuiteVariationalFixture.h" line="266"><![CDATA[Expected result = 9999 Digits: -0]]></Message> ALLOBS_OPER_MOD:OBS_OPER_DELETE instance=           1'
test_diff = '<Message file=".D[6]/test/base/TestSuiteModel.h" line="133"><![CDATA[||Mx-x|| = 43411459.225849807262||Mx|| = ]]></Message><Message file=".D[6]/test/base/TestSuiteVariationalFixture.h" line="250"><![CDATA[Expected result = 43411459 Digits: 8.2837846578541558529]]></Message></TestLog>'
test_diff2 = '<Message file=".D[6]/test/base/TestSuiteModel.h" line="98"><![CDATA[||Mx-x|| = 137534984.33869171143||Mx|| = ]]></Message><Message file=".D[6]/test/base/TestSuiteVariationalFixture.h" line="250"><![CDATA[Expected result = 9999 Digits: -4.1384250389422065908]]></Message></TestLog>'
test_variances = '<Message file=".D[83]/testsuite/TestSuiteEnsemble.h" line="98"><![CDATA[variances = 465160482.80360126495]]></Message><Message file=".D[83]/testsuite/TestSuiteVariationalFixture.h" line="264"><![CDATA[Expected result = 9999 Digits: -4.6676369086232849526]]></Message>'
test_interpol = '<Message file=".D[79]/testsuite/TestSuiteInterpolator.h" line="173"><![CDATA[ADJOINT TEST (DIRECT): x.Ft(y)= -12665440.848849847913 y.F(x)= -12665440.848849833012 digits = 14.929400198238932163]]></Message></TestLog>'
