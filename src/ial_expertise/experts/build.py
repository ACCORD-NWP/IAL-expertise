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

class CodingNormsExpert(OutputExpert):
    """" expert to check coding norms during IALGitRef2Pack """

    _footprint = dict(
        info = 'Check coding norms violations',
        attr = dict(
            kind = dict(
                values = ['codingnorms',],
            ),
            output = dict(
                info = "Coding norms for local files.",
                optional = True,
                default = 'coding_norms.json',
            ),
        )
    )

    def _parse(self):
        with io.open(self.output, 'r') as f:
            self.parsedInput = json.load(f)

    def summary(self):

        summary = {}

        if 'local' in self.parsedInput:

            sourcefiles_improved = []
            sourcefiles_degraded = []
            sourcefiles_neutral = []
            
            if 'main' in self.parsedInput:
                # possible to make comparison

                for sourcefile in self.parsedInput['local']:
                    # total number of violations
                    localcount = sum([self.parsedInput['local'][sourcefile][violatedNorm]
                                      for violatedNorm in self.parsedInput['local'][sourcefile]])
                    if sourcefile in self.parsedInput['main']:
                        maincount = sum([self.parsedInput['main'][sourcefile][violatedNorm]
                                         for violatedNorm in self.parsedInput['main'][sourcefile]])
                    else:
                        maincount = 0
                    # add file to appropriate list
                    if localcount < maincount:
                        sourcefiles_improved.append(sourcefile)
                    elif localcount == maincount:
                        sourcefiles_neutral.append(sourcefile)
                    else:
                        sourcefiles_degraded.append(sourcefile)
                
                # add lists of files to summary
                summary['sourcefiles improved'] = sourcefiles_improved
                summary['sourcefiles degraded'] = sourcefiles_degraded
                summary['sourcefiles neutral'] = sourcefiles_neutral

                # add background info
                summary['_main'] = self.parsedInput['main']

                # main validation metric
                summary['Auto-test'] = 'Failed' if len(sourcefiles_degraded) > 0 else 'Passed'

            # add background info
            summary['_local'] = self.parsedInput['local']

        return summary
    
    def _compare(self, references, *args, **kwargs):
        return self._compare_summaries(references, *args, **kwargs)

    @classmethod
    def compare_2summaries(cls, test, ref):
        if '_local' in test and '_main' in test:
            comparison = {
                'Validated means':'No source files have degraded in terms of coding norms.',
                'Validated':len(test['sourcefiles_degraded']) == 0,
                'Number of files degraded':len(test['sourcefiles_degraded']),
                'mainMetrics':'Number of files degraded',
                'Source files improved':test['sourcefiles_improved'],
                'Source files degraded':test['sourcefiles_degraded'],
                'Source files neutral':test['sourcefiles_neutral'],
            }
        else:
            comparison = {
                'Validated means':'Coding norms not checked; unable to validate',
                'Validated':True,
                'Number of files degraded':0,
                'mainMetrics':'Number of files degraded',
            }
