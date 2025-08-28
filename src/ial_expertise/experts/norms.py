#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Norms parsers."""

import arpifs_listings

from . import OutputExpert
from .thresholds import NORMSDIGITS_BITREPRO


class NormsChecker(OutputExpert):

    _footprint = dict(
        info = 'Read and compare the spectral/gridpoint norms of fields in listing.',
        attr = dict(
            kind = dict(
                values = ['norms',],
            ),
            output = dict(
                info = "Output listing file name to process.",
                optional = True,
                default = 'NODE.001_01',
            ),
            digits4validation = dict(
                info = "Maximum number of different digits in norms for validation.",
                type = int,
                optional = True,
                default = NORMSDIGITS_BITREPRO
            ),
            normstype = dict(
                info = "Select type of norms to be written in task summary.",
                values = ['spnorms', 'gpnorms', 'both'],
                optional = True,
                default = 'both',
            ),
            mode = dict(
                info = "Tunes what is to be written in task summary, among: " +
                       "'all': all norms | " +
                       "'last': only last step norms | " +
                       "'last_spectral': only the last step that contains spectral norms.",
                values = ['all', 'last', 'last_spectral'],
                optional = True,
                default = 'last_spectral',
            ),
            hide_equal_norms = dict(
                info = "Hide fields which norms are equal.",
                optional = True,
                type = bool,
                default = False,
            ),
        )
    )

    _modes = {'all':'_Norms at each step',
              'last':'Last step norms',
              'last_spectral':'Last step with spectral norms'}

    def _parse(self):
        """Parse file, read all norms."""
        self.listing = arpifs_listings.listings.OutputListing(self.output, 'norms')
        self.listing.parse_patterns(flush_after_reading=True)

    def summary(self):
        normset = [n.as_dict() for n in self.listing.normset.norms_at_each_step]
        summary = {'Number of steps':len(normset)}
        if self.normstype in ('spnorms', 'gpnorms'):
            normset = [{'step':n['step'], self.normstype:n[self.normstype]}
                       for n in normset if len(n[self.normstype]) != 0]
            key_suffix = ' ({} only)'.format(self.normstype)
        else:
            key_suffix = ''
        if self.mode == 'all':
            summary['_Norms at each step' + key_suffix] = normset
        elif self.mode == 'last':
            summary['Last step norms' + key_suffix] = normset[-1]
        elif self.mode == 'last_spectral':
            normset = [n for n in normset if len(n.get('spnorms', {})) > 0]
            summary['Last step with spectral norms' + key_suffix] = normset[-1]
        for norms in normset:
            for k in list(norms.keys()):
                if len(norms[k]) == 0:
                    norms.pop(k)
        return summary

    @classmethod
    def compare_2summaries(cls, test, ref,
                           mode='last_spectral',
                           validation_threshold=NORMSDIGITS_BITREPRO):
        """
        Compare 2 sets of norms in summary.

        :param validation_threshold: validation will be considered OK if the
            maximal number of different digits is lower or equal to threshold
        """
        if mode in ('last', 'last_spectral'):
            teststeps = [test[cls._modes[mode]],]
            refsteps = [ref[cls._modes[mode]],]
        else:
            teststeps = test[cls._modes[mode]]
            refsteps = ref[cls._modes[mode]]
        testnorms = [arpifs_listings.norms.Norms(n['step'], from_dict=n)
                     for n in teststeps]
        testset = arpifs_listings.norms.NormsSet(from_list=testnorms)
        refnorms = [arpifs_listings.norms.Norms(n['step'], from_dict=n)
                     for n in refsteps]
        refset = arpifs_listings.norms.NormsSet(from_list=refnorms)
        return cls._compare_2normsets(testset, refset,
                                      validation_threshold=validation_threshold)

    @classmethod
    def _compare_2normsets(cls, testset, refset,
                           hide_equal_norms=False,
                           validation_threshold=NORMSDIGITS_BITREPRO):
        """
        Compare 2 sets of norms.

        :param validation_threshold: validation will be considered OK if the
            maximal number of different digits is lower or equal to threshold
        """
        worst_digit = arpifs_listings.norms.compare_normsets(testset, refset, mode='get_worst',
                                                             which='all',
                                                             onlymaxdiff=True)
        summary = {'Maximum different digits':worst_digit,
                   'Validated means':'Maximum number of different digits in norms is lower or equal to {}'.format(validation_threshold),
                   'Validated':worst_digit <= validation_threshold,
                   'Bit-reproducible':worst_digit <= NORMSDIGITS_BITREPRO,
                   'mainMetrics':'Maximum different digits'}
        if not summary['Validated']:
            summary['Table of diverging digits'] = arpifs_listings.norms.compare_normsets_as_table(testset, refset,
               hide_equal_norms=hide_equal_norms)
        return summary

    def _compare(self, references):
        """Compare to a reference."""
        listings = [r for r in references if r.resource.kind == 'plisting']
        if len(listings) > 0:  # in priority, because summary may not contain all norms
            return self._compare_listings(references,
                                          validation_threshold=self.digits4validation)
        else:
            return self._compare_summaries(references,
                                           mode=self.mode,
                                           validation_threshold=self.digits4validation)

    def _compare_listings(self, references,
                          validation_threshold=NORMSDIGITS_BITREPRO):
        """Get listing among references resources, parse it and compare."""
        ref_listing = self.filter_one_resource(references, rkind='plisting')
        ref_listing_in = arpifs_listings.listings.OutputListing(
            ref_listing.container.localpath(), 'norms')
        ref_listing_in.parse_patterns(flush_after_reading=True)
        return self._compare_2normsets(self.listing.normset,
                                       ref_listing_in.normset,
                                       hide_equal_norms=self.hide_equal_norms,
                                       validation_threshold=validation_threshold)

