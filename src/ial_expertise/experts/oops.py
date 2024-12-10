#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OOPS parsers."""
import re
import numpy

from . import TextOutputExpert, ExpertError
from .util import ppp, ppi, FLOAT_RE, EXTENDED_FLOAT_RE
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
    _re_jo = r'.*\[CDATA\[Jo = (?P<jo>' + EXTENDED_FLOAT_RE + ')\]\].*'
    _re_test = re.compile(_re_jo)  # + _re_exp_jo)

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
    _re_test = re.compile(r'.*\[CDATA\[' +
                          r'dx1\.dx2 = (?P<dx1dx2>' + EXTENDED_FLOAT_RE + r')\s+' +
                          r'dy1\.dy2 = (?P<dy1dy2>' + EXTENDED_FLOAT_RE + r')\s+' +
                          r'(D|d)igits = (?P<digits>' + EXTENDED_FLOAT_RE + r')\s*\]\].*')

    def summary(self):
        return {'dx1.dx2':float(self.parsedOut['dx1dx2']),
                'dy1.dy2':float(self.parsedOut['dy1dy2']),
                'Digits':min(float(self.parsedOut['digits']), 16),
                'Auto-test':'Failed' if min(float(self.parsedOut['digits']), 16) < self.digits_validation_threshold else 'Passed'}

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


class OOPSJoTLExpert(OOPSTestExpert):

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

    _re_signature = r'WRITE_OBSVEC: CDNAME == obs_diags_1@update_(?P<nupdate>\d+) - write to ODB'
    _re_stats46 = re.compile(r'WRITE_OBSVEC: MIN,MAX,AVG=\s*' +
                             r'(?P<min>' + EXTENDED_FLOAT_RE + r')\s+' +
                             r'(?P<max>' + EXTENDED_FLOAT_RE + r')\s+' +
                             r'(?P<avg>' + EXTENDED_FLOAT_RE + r')\s*')
    _re_stats47 = re.compile(r'WRITE_OBSVEC: VALUES,NOT RMDI,MIN,MAX,AVG=\s*' +
                             r'(?P<values>\d+)\s+' +
                             r'(?P<not_rmdi>\d+)\s+' +
                             r'(?P<min>' + EXTENDED_FLOAT_RE + r')\s+' +
                             r'(?P<max>' + EXTENDED_FLOAT_RE + r')\s+' +
                             r'(?P<avg>' + EXTENDED_FLOAT_RE + r')\s*')
    
    def _parse(self):
        pass
    
    def __parse(self):
        """
        Parse listing, looking for OOPS WRITE_OBSVEC values.
        """
        txtdata = self._read_txt_output()
        test_status = {}
        n = 1
        for i, l in enumerate(txtdata):
            found = re.match(self._re_signature, l)
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
                    # test_status[found.group('nupdate')] = stats  # FIXME: 
                    test_status[str(n)] = stats
                    n += 1
                else:
                    continue
        if len(test_status) == 0:
            raise ExpertError('Regular expression research failed.')
        self.parsedOut = test_status
    
    def summary(self):
        return {'Deactivated':'Expertise to be developed reading ODB files'}
    
    def __summary(self):
        return {'WRITE_OBSVEC statistics at each update':self.parsedOut,
                'Number of updates':len(self.parsedOut)}
    
    @classmethod
    def compare_2summaries(cls, *args, **kwargs):
        return {'Deactivated':'Expertise to be developed reading ODB files'}
    
    @classmethod
    def __compare_2summaries(cls, test, ref,
                           validation_threshold=JO):
        """
        Compare two Jo-TL statistics using relative error.
        """
        test = test['WRITE_OBSVEC statistics at each update']
        ref = ref['WRITE_OBSVEC statistics at each update']
        new_u = sorted(set(test.keys()).difference(set(ref.keys())))
        lost_u = sorted(set(ref.keys()).difference(set(test.keys())))
        updates = sorted(set(test.keys()).intersection(set(ref.keys())))
        keys = sorted(set(test[updates[0]].keys()).intersection(set(ref[updates[0]].keys())))
        errors = {u:{k:test[u][k] - ref[u][k]
                     for k in keys if not numpy.isinf(ref[u][k])}
                  for u in updates}
        rel_errors = {u:{k:errors[u][k] / ref[u][k]
                         for k in keys if not numpy.isinf(ref[u][k])}
                      for u in updates}
        max_rel_err = max([max(update.values())
                           for update in rel_errors.values()
                           if len(update) > 0])
        max_abs_err = max([max(update.values())
                           for update in errors.values()
                           if len(update) > 0])
        comp = {'Validated means':'Absolute values of Relative errors in WRITE_OBSVEC statistics is lower or equal to {:g}%'.format(
                validation_threshold * 100),
                'Validated':abs(max_rel_err) <= validation_threshold,
                'Relative errors in WRITE_OBSVEC statistics':ppp(max_rel_err, 3),
                'Absolute errors in WRITE_OBSVEC statistics':'{:+g}'.format(max_abs_err),
                'mainMetrics':'Relative errors in WRITE_OBSVEC statistics'}
        if len(new_u) > 0:
            comp['New updates'] = new_u
        if len(lost_u) > 0:
            comp['Lost updates'] = lost_u
        return comp

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

    # Diff between 2 states
    _re_statediff = r'.*\[CDATA\[.*\|\|((Mx-x)|(x0-x2))\|\| = (?P<statediff>(\+|\-)*\d+(\.\d+)*).*'
    #_re_exp_statediff = '<Message file=".+" line="\d+"><!\[CDATA\[Expected result = (?P<exp_statediff>(\+|\-)*\d+\.?\d+) Digits: (?P<digits>(\+|\-)*\d+(\.\d+)*)\]\]></Message>'
    _re_test = re.compile(_re_statediff)  # + _re_exp_statediff)

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
    _re_var = r'.*\[CDATA\[variances = (?P<var>\d+\.\d+)\]\].*'
    _re_test = re.compile(_re_var)

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


class OOPSInterpolExpert(OOPSTestExpert):

    _footprint = dict(
        info = 'Read and compare *adjoint-test result* written by oops:interpol/two_geos_test.',
        attr = dict(
            kind = dict(
                values = ['oops:interpol/two_geos_test',],
            ),
            digits_validation_threshold = dict(
                info = "Minimum value for the number of common digits in the AD-test.",
                type = int,
                optional = True,
                default = JOAD_DIGITS,
            ),
        )
    )

    _re_test = re.compile(r'.*\[CDATA\[ADJOINT TEST \(DIRECT\):\s*' +
                          r'x\.Ft\(y\)\s*=\s*(?P<xFty>' + EXTENDED_FLOAT_RE + r')\s+' +
                          r'y\.F\(x\)\s*=\s*(?P<yFx>' + EXTENDED_FLOAT_RE + r')\s+' +
                          r'(D|d)igits\s*=\s*(?P<digits>' + EXTENDED_FLOAT_RE + r')\s*\]\].*')

    def summary(self):
        return {'x.Ft(y)':float(self.parsedOut['xFty']),
                'y.F(x)':float(self.parsedOut['yFx']),
                'Digits':min(float(self.parsedOut['digits']), 16)}

    @classmethod
    def compare_2summaries(cls, test, ref, validation_threshold=JOAD_DIGITS):
        """Compare two AD tests."""
        digits_diff = test['Digits'] - ref['Digits']
        return {'Validated means':'Enough digits common between x.Ft(y) and y.F(x) (scalar products); enough == as many as reference or > {}'.format(validation_threshold),
                'Validated':int(round(digits_diff)) >= 0 or test['Digits'] >= validation_threshold,
                'Common digits in AD-test >= reference ()'.format(ref['Digits']):int(round(digits_diff)) >= 0,
                'Common digits in AD-test >= {}'.format(validation_threshold):test['Digits'] >= validation_threshold,
                'Diff in common digits':ppi(int(round(digits_diff))),
                'Float diff in common digits':digits_diff,
                'mainMetrics':'Diff in common digits'}


class OOPSmodelADExpert(OOPSTestExpert):

    _footprint = dict(
        info = 'Read and compare *adjoint-test result* written by OOPS-test:mix/test_adjoint in standard output file.',
        attr = dict(
            kind = dict(
                values = ['oops:mix/test_adjoint',],
            ),
            digits_validation_threshold = dict(
                info = "Minimum value for the number of common digits in the AD-test.",
                type = int,
                optional = True,
                default = JOAD_DIGITS,
            ),
        )
    )

    _re_test = re.compile(r'.*\[CDATA\[' +
                          r'<dx1,Mtdx2> = (?P<dx1Mtdx2>' + EXTENDED_FLOAT_RE + r')\s+' +
                          r'<Mdx1,dx2> = (?P<Mdx1dx2>' + EXTENDED_FLOAT_RE + r')\s+' +
                          r'digits = (?P<digits>' + EXTENDED_FLOAT_RE + r')\s*\]\].*')

    def summary(self):
        return {'dx1,Mtdx2':float(self.parsedOut['dx1Mtdx2']),
                'Mdx1,dx2':float(self.parsedOut['Mdx1dx2']),
                'Digits':min(float(self.parsedOut['digits']), 16),
                'Auto-test':'Failed' if min(float(self.parsedOut['digits']), 16) < self.digits_validation_threshold else 'Passed'}

    @classmethod
    def compare_2summaries(cls, test, ref, validation_threshold=JOAD_DIGITS):
        """Compare two AD tests."""
        digits_diff = test['Digits'] - ref['Digits']
        return {'Validated means':'Enough digits common between <dx1,Mtdx2> and <Mdx1,dx2> (scalar products); enough == as many as reference or > {}'.format(validation_threshold),
                'Validated':int(round(digits_diff)) >= 0 or test['Digits'] >= validation_threshold,
                'Common digits in AD-test >= reference ()'.format(ref['Digits']):int(round(digits_diff)) >= 0,
                'Common digits in AD-test >= {}'.format(validation_threshold):test['Digits'] >= validation_threshold,
                'Diff in common digits':ppi(int(round(digits_diff))),
                'Float diff in common digits':digits_diff,
                'mainMetrics':'Diff in common digits'}
