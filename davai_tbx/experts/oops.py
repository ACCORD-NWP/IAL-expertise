#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OOPS parsers."""
from __future__ import print_function, absolute_import, division, unicode_literals

import re
import numpy

from . import TextOutputExpert, ExpertError
from .util import ppp, ppi, FLOAT_RE
from .thresholds import (JO,
                         JOAD_DIGITS,
                         STATESDIFF,
                         VARIANCES,
                         EXPECTED_RESULT_TOLERANCE_FACTOR)


class OOPSTestExpert(TextOutputExpert):

    _abstract = True
    _footprint = dict(
        info = 'OOPS Test OutputExpert.',
        attr = dict(
            output = dict(
                optional = True,
                default = 'stdeo.0',
            ),
        )
    )

    def _parse(self):
        """
        Parse listing, looking for OOPS Test check and result comparison to
        expected.
        """
        txtdata = self._read_txt_output()
        test_status = None
        for l in txtdata:
            found = self._re_test.match(l)
            if found:
                test_status = found.groupdict()
                test_status = {k:float(v) for k,v in test_status.items()}
                break
        if test_status is None:
            raise ExpertError('Regular expression research failed.')
        self.parsedOut = test_status

    def _compare(self, references, *args, **kwargs):
        """Compare to a reference summary."""
        return self._compare_summaries(references, *args, **kwargs)


class OOPSJoExpert(OOPSTestExpert):

    _footprint = dict(
        info = 'Read and compare *Jo* written by OOPS-test:test_hop_with_jo in standard output file.',
        attr = dict(
            kind = dict(
                values = ['oops:op_obs_file/test_hop_with_jo',
                          'oops:op_obs_model/test_hop_with_jo',],
            ),
            jo_validation_threshold = dict(
                info = "Maximum value for the Jo relative error",
                type = float,
                optional = True,
                default = JO,
            ),
        )
    )

    # Jo & expected Jo
    _re_jo = '<Message file=".+" line="\d+"><!\[CDATA\[Jo = (?P<jo>\d+\.\d+)\]\]></Message>'
    _re_exp_jo = '<Message file=".+" line="\d+"><!\[CDATA\[Expected result = (?P<exp_jo>\d+\.?\d+) Digits: (?P<digits>(\+|\-)*\d+\.\d+)\]\]></Message>'
    _re_test = re.compile(_re_jo + _re_exp_jo)

    def as_EXPECTED_RESULT(self, tolerance_factor=EXPECTED_RESULT_TOLERANCE_FACTOR):  # TODO: CLEANME
        """From the parsed result, prepare a new EXPECTED_RESULT variable for OOPS."""
        jo = float(self.parsedOut['jo'])
        digits = max(int(numpy.ceil(numpy.log10(jo) * tolerance_factor)), 1)
        return {"expected_Jo": str(int(jo)),  # empirical: rounded
                "significant_digits":str(int(digits))}

    def summary(self):
        return {'Jo':float(self.parsedOut['jo'])}

    @classmethod
    def compare_2summaries(cls, test, ref,
                           validation_threshold=JO):
        """
        Compare two Jo using relative error.
        Relative error makes sense because Jo is definite positive.
        """
        err = test['Jo'] - ref['Jo']
        rel_err = err / ref['Jo']
        return {'Validated means':'Absolute value of Relative error in Jo is lower or equal to {:g}%'.format(
                validation_threshold * 100),
                'Validated':abs(rel_err) <= validation_threshold,
                'Relative error in Jo':ppp(rel_err, 3),
                'Absolute error in Jo':'{:+g}'.format(err),
                'mainMetrics':'Relative error in Jo'}

    def _compare(self, references):
        """Compare to a reference summary: relative error in Jo."""
        return super(OOPSJoExpert, self)._compare(references,
                                                  validation_threshold=self.jo_validation_threshold)


class OOPSJoADExpert(OOPSTestExpert):

    _footprint = dict(
        info = 'Read and compare *adjoint-test result* written by obs operator OOPS-test:test_adjoint in standard output file.',
        attr = dict(
            kind = dict(
                values = ['oops:op_obs_file/test_adjoint',
                          'oops:op_obs_model/test_adjoint',],
            ),
            digits_validation_threshold = dict(
                info = "Minimum value for the number of common digits in the JoAD-test.",
                type = int,
                optional = True,
                default = JOAD_DIGITS,
            ),
        )
    )

    # Adjoint test  # CLEANME: le (D|d) est une scorie
    _re_ad = '<Message file=".+" line="\d+"><!\[CDATA\[dx1\.dx2 = (?P<dx1dx2>-?\d+\.\d+(e(\+|-)\d+)?) dy1\.dy2 = (?P<dy1dy2>-?\d+\.\d+(e(\+|-)\d+)?) (D|d)igits = (?P<digits>-?\d+\.\d+|inf)\]\]></Message>'
    _re_test = re.compile(_re_ad)

    def as_EXPECTED_RESULT(self):  # TODO: CLEANME
        """From the parsed result, prepare a new EXPECTED_RESULT variable for OOPS."""
        digits = min(float(self.parsedOut['digits']), 16)
        return {"significant_digits":str(int(digits))}

    def summary(self):
        return {'dx1.dx2':float(self.parsedOut['dx1dx2']),
                'dy1.dy2':float(self.parsedOut['dy1dy2']),
                'Digits':min(float(self.parsedOut['digits']), 16)}

    @classmethod
    def compare_2summaries(cls, test, ref, validation_threshold=JOAD_DIGITS):
        """Compare two AD tests."""
        digits_diff = test['Digits'] - ref['Digits']
        return {'Validated means':'Enough digits common between dx1.dx2 and dy1.dy2 (scalar products); enough == as many as reference or > {}'.format(validation_threshold),
                'Validated':int(round(digits_diff)) >= 0 or test['Digits'] >= validation_threshold,
                'Common digits in AD-test >= reference ()'.format(ref['Digits']):int(round(digits_diff)) >= 0,
                'Common digits in AD-test >= {}'.format(validation_threshold):test['Digits'] >= validation_threshold,
                'Diff in common digits':ppi(int(round(digits_diff))),
                'Float diff in common digits':digits_diff,
                'mainMetrics':'Diff in common digits'}


class OOPSJoTLExpert(OOPSTestExpert):  # FIXME: works ?

    _footprint = dict(
        info = 'Read and compare *TL-test result* written by obs operator OOPS-test:test_tl in standard output file.',
        attr = dict(
            kind = dict(
                values = ['oops:op_obs_file/test_tl',
                          'oops:op_obs_model/test_tl',],
            ),
            output = dict(
                info = "Output listing file name to process",
                optional = True,
                default = 'NODE.001_01',
            ),
            jo_validation_threshold = dict(
                info = "Maximum value for the Jo relative error.",
                type = float,
                optional = True,
                default = JO,
            ),
        )
    )

    _re_signature = 'WRITE_OBSVEC: CDNAME == obs_diags_1@update_(?P<nupdate>\d+) - write to ODB'
    _re_stats46 = re.compile('WRITE_OBSVEC: MIN,MAX,AVG=\s*' +
                             '(?P<min>' + FLOAT_RE + ')\s+' +
                             '(?P<max>' + FLOAT_RE + ')\s+' +
                             '(?P<avg>' + FLOAT_RE + ')\s*')
    _re_stats47 = re.compile('WRITE_OBSVEC: VALUES,NOT RMDI,MIN,MAX,AVG=\s*' +
                             '(?P<values>\d+)\s+' +
                             '(?P<not_rmdi>\d+)\s+' +
                             '(?P<min>' + FLOAT_RE + ')\s+' +
                             '(?P<max>' + FLOAT_RE + ')\s+' +
                             '(?P<avg>' + FLOAT_RE + ')\s*')

    def _parse(self):
        """
        Parse listing, looking for OOPS WRITE_OBSVEC values.
        """
        txtdata = self._read_txt_output()
        test_status = {}
        for i, l in enumerate(txtdata):
            found = re.match(self._re_signature, l)
            print("am:signature found")
            if found:
                stats = ' '.join([txtdata[i - 2], txtdata[i - 1]])
                stats_ok = self._re_stats47.match(stats)
                if not stats_ok:
                    stats_ok = self._re_stats46.match(stats)
                if stats_ok:
                    stats = stats_ok.groupdict()
                    # convert to floats/ints
                    for k, v in stats.items():
                        if k in ('min', 'max', 'avg'):
                            stats[k] = float(v)
                        elif k in ('values', 'not_rmdi'):
                            stats[k] = int(v)
                    test_status[found.group('nupdate')] = stats
                else:
                    continue
        if len(test_status) == 0:
            raise ExpertError('Regular expression research failed.')
        self.parsedOut = test_status

    def summary(self):
        return {'WRITE_OBSVEC statistics at each update':self.parsedOut,
                'Number of updates':len(self.parsedOut)}

    @classmethod
    def compare_2summaries(cls, test, ref,
                           validation_threshold=JO):
        """
        Compare two Jo-TL statistics using relative error.
        """
        test = test['WRITE_OBSVEC statistics at each update']
        ref = ref['WRITE_OBSVEC statistics at each update']
        errors = {u:{k:test[u][k] - ref[u][k]
                     for k in test[u].keys()}
                  for u in test.keys()}
        rel_errors = {u:{k:(test[u][k] - ref[u][k]) / ref[u][k]
                         for k in test[u].keys()}
                      for u in test.keys()}
        max_rel_err = max([max(update.values()) for update in rel_errors.values()])
        max_abs_err = max([max(update.values()) for update in errors.values()])
        return {'Validated means':'Absolute values of Relative errors in WRITE_OBSVEC statistics is lower or equal to {:g}%'.format(
                validation_threshold * 100),
                'Validated':abs(max_rel_err) <= validation_threshold,
                'Relative errors in WRITE_OBSVEC statistics':ppp(max_rel_err, 3),
                'Absolute errors in WRITE_OBSVEC statistics':'{:+g}'.format(max_abs_err),
                'mainMetrics':'Relative errors in WRITE_OBSVEC statistics'}

    def _compare(self, references):
        """Compare to a reference summary: relative error in JoTL."""
        return super(OOPSJoTLExpert, self)._compare(references,
                                                    validation_threshold=self.jo_validation_threshold)


class OOPSStateDiffExpert(OOPSTestExpert):

    _footprint = dict(
        info = 'Read and compare *state difference* written by OOPS-test in standard output file.',
        attr = dict(
            kind = dict(
                values = ['oops:mix/test_model_direct',
                          'oops:mix/test_external_dfi',
                          'oops:mix/test_fields_change_resolution'],
            ),
            statesdiff_validation_threshold = dict(
                info = "Maximum value for the 'States diff' relative error.",
                type = float,
                optional = True,
                default = STATESDIFF,
            ),
        )
    )

    # Diff between 2 states  # CLEANME: le .* est une scorie dans OOPS
    _re_statediff = '<Message file=".+" line="\d+"><!\[CDATA\[.*\|\|((Mx-x)|(x0-x2))\|\| = (?P<statediff>(\+|\-)*\d+(\.\d+)*).*\]\]></Message>'
    _re_exp_statediff = '<Message file=".+" line="\d+"><!\[CDATA\[Expected result = (?P<exp_statediff>(\+|\-)*\d+\.?\d+) Digits: (?P<digits>(\+|\-)*\d+(\.\d+)*)\]\]></Message>'
    _re_test = re.compile(_re_statediff + _re_exp_statediff)

    def as_EXPECTED_RESULT(self, tolerance_factor=EXPECTED_RESULT_TOLERANCE_FACTOR):  # TODO: CLEANME
        """From the parsed result, prepare a new EXPECTED_RESULT variable for OOPS."""
        diff = float(self.parsedOut['statediff'])
        digits = max(int(numpy.ceil(numpy.log10(abs(diff)) * tolerance_factor)), 1)
        return {"expected_diff": str(diff),
                "significant_digits":str(int(digits))}

    def summary(self):
        return {'States diff':float(self.parsedOut['statediff'])}

    @classmethod
    def compare_2summaries(cls, test, ref,
                           validation_threshold=STATESDIFF):
        """
        Compare two 'States diff' using relative error.
        """
        err = test['States diff'] - ref['States diff']
        rel_err = err / ref['States diff']  # FIXME: what to do when ref -> 0 ?
        return {'Validated means':"Absolute value of Relative error in 'States diff' is lower or equal to " + ppp(validation_threshold, 3),
                'Validated':abs(rel_err) <= validation_threshold,
                'Relative error in States diff':ppp(rel_err, 3),
                'Absolute error in States diff':'{:+g}'.format(err),
                'mainMetrics':'Relative error in States diff'}

    def _compare(self, references):
        """Compare to a reference summary."""
        return super(OOPSStateDiffExpert, self)._compare(references,
                                                         validation_threshold=self.statesdiff_validation_threshold)


class OOPSVariancesExpert(OOPSTestExpert):

    _footprint = dict(
        info = 'Read and compare *variances* written by OOPS-test in standard output file.',
        attr = dict(
            kind = dict(
                values = ['oops:ensemble/read',],
            ),
            variances_validation_threshold = dict(
                info = "Maximum value for the variances relative error.",
                type = float,
                optional = True,
                default = VARIANCES,
            ),
        )
    )

    # Jo & expected Jo
    _re_var = '<Message file=".+" line="\d+"><!\[CDATA\[variances = (?P<var>\d+\.\d+)\]\]></Message>'
    _re_exp_var = '<Message file=".+" line="\d+"><!\[CDATA\[Expected result = (?P<exp_var>\d+\.?\d+) Digits: (?P<digits>(\+|\-)*\d+\.\d+)\]\]></Message>'
    _re_test = re.compile(_re_var + _re_exp_var)

    def as_EXPECTED_RESULT(self, tolerance_factor=EXPECTED_RESULT_TOLERANCE_FACTOR):  # TODO: CLEANME
        """From the parsed result, prepare a new EXPECTED_RESULT variable for OOPS."""
        var = float(self.parsedOut['var'])
        digits = max(int(numpy.ceil(numpy.log10(var) * tolerance_factor)), 1)
        return {"expected_variances": str(int(var)),  # empirical: rounded
                "significant_digits":str(int(digits))}

    def summary(self):
        return {'Variances':float(self.parsedOut['var'])}

    @classmethod
    def compare_2summaries(cls, test, ref,
                           validation_threshold=VARIANCES):
        """
        Compare two Variances using relative error.
        """
        err = test['Variances'] - ref['Variances']
        rel_err = err / ref['Variances']
        return {'Validated means':'Absolute value of Relative error in Variances is lower or equal to {:g}%'.format(
                validation_threshold * 100),
                'Validated':abs(rel_err) <= validation_threshold,
                'Relative error in Variances':ppp(rel_err, 3),
                'Absolute error in Variances':'{:+g}'.format(err),
                'mainMetrics':'Relative error in Variances'}

    def _compare(self, references):
        """Compare to a reference summary: relative error in Variances."""
        return super(OOPSVariancesExpert, self)._compare(references,
                                                         validation_threshold=self.variances_validation_threshold)
