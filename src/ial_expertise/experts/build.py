#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build executables Experts.
"""
import io
import json

from . import OutputExpert


class GmkpackBuildExpert(OutputExpert):
    
    _footprint = dict(
        info = 'Check the build of executables within gmkpack',
        attr = dict(
            kind = dict(
                values = ['gmkpack_build',],
            ),
            output = dict(
                info = "Output listing file name to process.",
                optional = True,
                default = 'build_report.json',
            ),
        )
    )

    def _parse(self):
        with io.open(self.output, 'r') as f:
            self.parsedOut = json.load(f)

    def summary(self):
        summary = {'All OK':all([v['OK'] for v in self.parsedOut.values()]),
                   'Executables OK':sorted([k for k, v in self.parsedOut.items() if v['OK']]),
                   'Executables failed':sorted([k for k, v in self.parsedOut.items() if not v['OK']]),
            }
        for k, v in self.parsedOut.items():
            summary['_' + k] = v
        return summary
    
    def _compare(self, references, *args, **kwargs):
        return self._compare_summaries(references, *args, **kwargs)

    @classmethod
    def compare_2summaries(cls, test, ref):
        test_execs = set(test['Executables OK'] + test['Executables failed'])
        ref_execs = set(ref['Executables OK'] + ref['Executables failed'])
        common_executables = test_execs.intersection(ref_execs)
        test_failed = common_executables.intersection(test['Executables failed'])
        ref_failed = common_executables.intersection(ref['Executables failed'])
        return {'Validated means':'No executables is failed that was successful in reference.',
                'Validated':test_failed.issubset(ref_failed),
                'Newly missing executables':len(test_failed.difference(ref_failed)),
                'mainMetrics':'Newly missing executables'}
