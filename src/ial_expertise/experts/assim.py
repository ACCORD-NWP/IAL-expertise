#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Assimilation tasks parsers."""
import re
import os

from footprints import FPDict
import arpifs_listings

from . import OutputExpert, TextOutputExpert
from .util import (difftree, comp_messages, ppp)
from .thresholds import (JOTABLES,
                         EPSILON,
                         OBSERVATIONS_NUMBER,
                         CANARISTATS_VALIDATION)


class JoTable(OutputExpert):

    _footprint = dict(
        info = 'Read and compare the Jo for each {obstype, sensor, parameter} in listing.',
        attr = dict(
            kind = dict(
                values = ['joTables',],
            ),
            output = dict(
                info = "Output listing file name to process.",
                optional = True,
                default = 'NODE.001_01',
            ),
            validation_thresholds = dict(
                info = "Thresholds on {Jo, Jo/n and n} for validation.",
                type = FPDict,
                optional = True,
                default = JOTABLES
            ),
        )
    )

    def _parse(self):
        """Parse file, read all norms."""
        self.listing = arpifs_listings.listings.OutputListing(self.output, 'Jo-tables')
        self.listing.parse_patterns(flush_after_reading=True)

    def summary(self):
        summary = self.listing.jo_tables.as_dict()
        for k in summary.keys():
            for o in list(summary[k].keys()):
                if summary[k][o][o]['n'] == 0:
                    summary[k].pop(o)
            for o in summary[k].keys():
                for t in summary[k][o].keys():
                    for p in summary[k][o][t].keys():
                        if isinstance(summary[k][o][t][p], dict) and 'jon' in summary[k][o][t][p]:
                            summary[k][o][t][p]['jo/n'] = summary[k][o][t][p].pop('jon')
                    if 'jon' in summary[k][o][t]:
                        summary[k][o][t]['jo/n'] = summary[k][o][t].pop('jon')
        return {'Jo-Tables':summary,
                'Number of Tables':len(summary),
                'Total Jo per Table':{table:self.listing.jo_tables[table].jo
                                      for table in self.listing.jo_tables.keys()}
                }

    def _compare(self, references):
        """Compare to a reference."""
        listings = [r for r in references if r.resource.kind == 'plisting']
        if len(listings) > 0:
            return self._compare_listings(references, validation_thresholds=self.validation_thresholds)
        else:
            raise NotImplementedError("Comparison need a reference output listing.")

    def _compare_2jotableset(self, test, ref,
                             validation_thresholds=JOTABLES,
                             epsilon=EPSILON):
        """
        Compare 2 Jo-Tables.

        :param validation_thresholds: validation will be considered OK if all
            maximal differences (diff/reldiff of n, jo, jo/n) are lower than
            associated threshold
        """
        if len(ref) > 0:
            if len(test) > 0:
                # if not the same number of JoTables
                if len(set(test.keys())) != len(set(ref.keys())):
                    # ignore the ones present in one side only
                    test_set = set(test.keys())
                    ref_set = set(ref.keys())
                    for k in test_set.difference(ref_set):
                        test._content.pop(k)
                    for k in ref_set.difference(test_set):
                        ref._content.pop(k)
                # compute diff
                diff = test.compute_diff(ref)
                maxdiff = test.maxdiff(ref)
                comp = {'All comparisons':diff,
                        'Maximum differences':maxdiff,
                        'Maximum Relative diff in Jo/n':ppp(maxdiff['jo/n']['reldiff']),
                        'Validated means':"Maximum errors lower than thresholds: {}".format(str(validation_thresholds)),
                        'Validated':all([all([abs(maxdiff[p]['diff']) <= validation_thresholds[p]['diff'] for p in maxdiff.keys()]),
                                         all([abs(maxdiff[p]['reldiff']) <= validation_thresholds[p]['reldiff'] for p in maxdiff.keys()])
                                         ]),
                        'Bit-reproducible':all([abs(maxdiff[p]['diff']) <= epsilon for p in maxdiff.keys()]),
                        'mainMetrics':'Maximum Relative diff in Jo/n'}
            else:
                comp = {'No Jo-Table available in':'test'}
        else:
            comp = {'No comparison':'No Jo-tables'}
        return comp

    def _compare_listings(self, references,
                          validation_thresholds=JOTABLES):
        """Get listing among references resources, parse it and compare."""
        ref_listing = self.filter_one_resource(references, rkind='plisting')
        ref_listing_in = arpifs_listings.listings.OutputListing(
            ref_listing.container.localpath(), 'Jo-tables')
        ref_listing_in.parse_patterns(flush_after_reading=True)
        return self._compare_2jotableset(self.listing.jo_tables, ref_listing_in.jo_tables,
                                         validation_thresholds=validation_thresholds)


class BatorObservationsCount(TextOutputExpert):

    _footprint = dict(
        info = 'Read and compare the numbers of observations archived by Bator in listings.',
        attr = dict(
            kind = dict(
                values = ['bator_obscount',],
            ),
            output = dict(
                info = "Ignored attribute: files to process are automatically found in current directory.",
                optional = True,
            ),
            validation_threshold = dict(
                info = "Maximum difference in observation counts for validation.",
                type = int,
                optional = True,
                default = OBSERVATIONS_NUMBER
            ),
        )
    )

    _start_pattern = "****** Donnees archivees ******"
    _end_pattern = re.compile(r"Nb total d'observations :\s*(?P<ntotobs>\d+)")
    _obstype_pattern = re.compile(r"observations :\s+(?P<obstype>\w+)\s+(?P<N_obstype>\d+)")
    _subobstype_pattern = re.compile(r"\s*(?P<subobstype>.+)\s+(?P<N_subobstype>\d+)")
    _nbpool_pattern = re.compile(r"\*\*\* INFO - BATOR : BATOR_NBPOOL is (?P<nbpool>\d+)")
    _loc_listing_name = re.compile(r'listing\.(?P<base>\w+)')

    def _find_listings(self):
        loc_files = os.listdir(os.getcwd())
        listings = [f for f in loc_files if self._loc_listing_name.match(f)]
        return listings

    @classmethod
    def _parse_text(cls, text):
        "Parse *text*, being a list of lines."
        obs_numbers = {}
        for line in text:
            nbpool = cls._nbpool_pattern.match(line)
            if nbpool:
                obs_numbers['Number of Pools'] = int(nbpool.group("nbpool"))
                break
        if cls._start_pattern in text:
            i0 = text.index(cls._start_pattern)
            obstats = text[i0:]
            for i, line in enumerate(obstats):
                end = cls._end_pattern.match(line)
                if end:
                    obs_numbers['Total'] = int(end.group('ntotobs'))
                    iend = i
                    break
            obstats = obstats[:iend]
            for line in obstats:
                ot = cls._obstype_pattern.match(line)
                if ot:
                    obstype_numbers = {'SubTotal': int(ot.group('N_obstype'))}
                    obstype = ot.group('obstype')
                    obs_numbers[obstype] = obstype_numbers
                sot = cls._subobstype_pattern.match(line)
                if sot:
                    obs_numbers[obstype][sot.group('subobstype').strip()] = int(sot.group('N_subobstype'))
        else:
            obs_numbers['Total'] = 0
        return obs_numbers

    def _parse(self):
        """Parse files."""
        obs_numbers = {}
        for listing in self._find_listings():
            base = self._loc_listing_name.match(listing).group('base')
            obs_numbers[base] = {}
            output_lines = self._read_txt_output(listing)
            obs_numbers[base] = self._parse_text(output_lines)
        self.parsedOut = obs_numbers

    def summary(self):
        return {'Observation counts':self.parsedOut}

    @classmethod
    def compare_2summaries(cls, test, ref,
                           validation_threshold=OBSERVATIONS_NUMBER):
        """Compare Obs Numbers."""
        test = test['Observation counts']
        ref = ref['Observation counts']
        diffs = {}
        validated = True
        bitrepro = True
        max_diff_in_number = 0
        for base in ref.keys():
            if base not in test:
                diffs[base] = comp_messages['missing']
                validated = False
                bitrepro = False
            else:
                diffs[base] = {}
                for ot in ref[base].keys():
                    if ot not in test[base]:
                        diffs[base][ot] = comp_messages['missing']
                        validated = False
                        bitrepro = False
                    else:
                        if isinstance(ref[base][ot], dict):
                            diffs[base][ot] = {}
                            for sot in ref[base][ot].keys():
                                if sot not in test[base][ot]:
                                    diffs[base][ot][sot] = comp_messages['missing']
                                    validated = False
                                    bitrepro = False
                                else:
                                    diffs[base][ot][sot] = test[base][ot][sot] - ref[base][ot][sot]
                                    if abs(diffs[base][ot][sot]) > validation_threshold:
                                        validated = False
                                    if diffs[base][ot][sot] != 0:
                                        bitrepro = False
                                    if abs(diffs[base][ot][sot]) > abs(max_diff_in_number):
                                        max_diff_in_number = diffs[base][ot][sot]
                        else:  # SubTotal
                            diffs[base][ot] = test[base][ot] - ref[base][ot]
        return {'Validated means':'Maximum difference in number of observations is lower or equal to {:g}'.format(
                validation_threshold),
                'Validated':validated,
                'Bit-reproducible':bitrepro,
                'Differences in obs counts':diffs,
                'Maximum difference in obs counts':max_diff_in_number,
                'mainMetrics':'Maximum difference in obs counts'}

    def _compare(self, references, *args, **kwargs):
        """Compare to a reference summary."""
        return self._compare_summaries(references, *args, **kwargs)


class CanariStats(TextOutputExpert):

    _footprint = dict(
        info = 'Read and compare the canari increments from CANCER in listing.',
        attr = dict(
            kind = dict(
                values = ['canari_stats',],
            ),
            output = dict(
                info = "Output listing file name to process.",
                optional = True,
                default = 'NODE.001_01',
            ),
            innovation_validation_threshold = dict(
                info = "Maximum value for the relative error in OBS-MOD",
                type = float,
                optional = True,
                default = CANARISTATS_VALIDATION,
            ),
            obscount_validation_threshold = dict(
                info = "Maximum difference in observation number",
                type = int,
                optional = True,
                default = OBSERVATIONS_NUMBER
            ),
        )
    )

    _start = 'Statistiques supplementaires'
    _end = "Fin de l'impression des statistiques supplementaires de CANCER"
    _re_type = re.compile(r"Type d'observations numero\s+(?P<obstypenum>\d+)")
    _re_param = re.compile(r"(?P<param>.*)OBS-MOD =\s*(?P<param_value>-?\d+\.\d{3}) SIGMA =\s*(?P<sigma>\d+\.\d{3}) \((?P<param_num>\d+)\)")

    @classmethod
    def _parse_text(cls, text):
        "Parse *text*, being a list of lines."
        extract = {}
        first = (text.index(cls._start), text.index(cls._end))
        extract['Beginning'] = text[first[0]:first[1]]
        text = text[first[1] + 1:]
        last = (text.index(cls._start), text.index(cls._end))
        extract['End'] = text[last[0]:last[1]]
        parsedOut = {step:{} for step in extract.keys()}
        for step, lines in extract.items():
            for line in lines:
                typematch = cls._re_type.match(line)
                if typematch:
                    t = int(typematch.group('obstypenum').strip())
                    t = 'Obstype: {}'.format(t)
                    parsedOut[step][t] = {}
                else:
                    paramatch = cls._re_param.match(line)
                    if paramatch:
                        p = paramatch.group('param').strip()
                        parsedOut[step][t][p] = {'OBS-MOD':float(paramatch.group('param_value')),
                                                 'SIGMA':float(paramatch.group('sigma')),
                                                 'NUMBER':int(paramatch.group('param_num'))}
        return parsedOut

    def _parse(self):
        """
        Parse listing, looking for OOPS Test check and result comparison to
        expected.
        """
        txtdata = self._read_txt_output()
        self.parsedOut = self._parse_text(txtdata)

    def summary(self):
        return {'OI residuals':self.parsedOut}

    @classmethod
    def compare_2summaries(cls, test, ref,
                           innovation_validation_threshold=CANARISTATS_VALIDATION,
                           obscount_validation_threshold=OBSERVATIONS_NUMBER):
        """
        Compare absolute error and obs numbers.
        """
        # FIXME: all parameters are mixed in the threshold...
        test = test['OI residuals']
        ref = ref['OI residuals']
        diffs = difftree(test, ref)
        max_err = 0.
        max_errnum = 0
        ok = True
        for step in diffs.keys():
            if isinstance(diffs[step], dict):
                for obstype in diffs[step].keys():
                    if isinstance(diffs[step][obstype], dict):
                        for param in diffs[step][obstype].keys():
                            if isinstance(diffs[step][obstype][param], dict):
                                if isinstance(diffs[step][obstype][param]['OBS-MOD'], float):
                                    max_err = max(max_err, abs(diffs[step][obstype][param]['OBS-MOD']))
                                else:
                                    ok = False
                                if isinstance(diffs[step][obstype][param]['NUMBER'], int):
                                    max_errnum = max(max_errnum, abs(diffs[step][obstype][param]['NUMBER']))
                                else:
                                    ok = False
                            else:
                                ok = False
                    else:
                        ok = False
            else:
                ok = False
        validated = (ok and max_err <= innovation_validation_threshold and
                     max_errnum <= obscount_validation_threshold)
        bitrepro = ok and max_err == 0.
        return {'Differences in residuals':diffs,
                'Validated means':'Maximum absolute value of error in OBS-MOD is lower or equal to {:g}'.format(innovation_validation_threshold),
                'Bit-reproducible':bitrepro,
                'Validated':validated,
                'Maximum absolute error on OBS-MOD':max_err,
                'Maximum absolute error on Observations number':max_errnum,
                'mainMetrics':'Maximum absolute error on OBS-MOD'}

    def _compare(self, references):
        """Compare to a reference summary."""
        return self._compare_summaries(references,
                                       innovation_validation_threshold=self.innovation_validation_threshold,
                                       obscount_validation_threshold=self.obscount_validation_threshold)
