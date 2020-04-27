#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fields parsers."""

from __future__ import print_function, absolute_import, division, unicode_literals

import io
import numpy
import os
import re

from footprints import FPList
import arpifs_listings
from bronx.fancies import loggers

from . import OutputExpert, ExpertError
from .thresholds import (NORMSDIGITS_BITREPRO,
                         NORMALIZED_FIELDS_DIFF,
                         EPSILON)

logger = loggers.getLogger(__name__)


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
            plot_spectral = dict(
                info = "Plot evolution of spectral norms difference (number of # digits) to SVG.",
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
            for k in norms.keys():
                if len(norms[k]) == 0:
                    norms.pop(k)
        return summary

    @classmethod
    def compare_2summaries(cls, test, ref,
                           plot_spectral=False,
                           mode='last_spectral',
                           validation_threshold=NORMSDIGITS_BITREPRO):
        """
        Compare 2 sets of norms in summary.

        :param plot_spectral: plot evolution of spectral norms difference
            (number of # digits)
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
                                      plot_spectral=plot_spectral,
                                      validation_threshold=validation_threshold)

    @classmethod
    def _compare_2normsets(cls, testset, refset,
                           plot_spectral=False,
                           validation_threshold=NORMSDIGITS_BITREPRO):
        """
        Compare 2 sets of norms.

        :param plot_spectral: plot evolution of spectral norms difference
            (number of # digits)
        :param validation_threshold: validation will be considered OK if the
            maximal number of different digits is lower or equal to threshold
        """
        comp = io.StringIO()
        arpifs_listings.norms.compare_normsets(testset, refset, mode='text',
                                               which='all',
                                               out=comp,
                                               onlymaxdiff=False)
        comp.seek(0)
        worst_digit = arpifs_listings.norms.compare_normsets(testset, refset, mode='get_worst',
                                                             which='all',
                                                             onlymaxdiff=True)
        summary = {'Maximum different digits':worst_digit,
                   'Validated means':'Maximum number of different digits in norms is lower or equal to {}'.format(validation_threshold),
                   'Validated':worst_digit <= validation_threshold,
                   'Bit-reproducible':worst_digit <= NORMSDIGITS_BITREPRO,
                   'mainMetrics':'Maximum different digits'}
        if not summary['Validated']:
            summary['_Norms Compared (all)'] = comp.read().split('\n')
        if plot_spectral:
            svg = 'spnorms.svg'
            arpifs_listings.norms.compare_normsets(testset, refset, mode='plot',
                                                   which='all',
                                                   plot_out=svg)
            with io.open(svg, 'r') as s:
                svg = s.readlines()
            summary['Graph: Spectral norms evolution (SVG)'] = ''.join([l.strip() for l in svg])  # condensed
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
                                       plot_spectral=self.plot_spectral,
                                       validation_threshold=validation_threshold)


class FieldsInFileExpert(OutputExpert):

    _footprint = dict(
        info = 'Read and compare the fields present in files.',
        attr = dict(
            kind = dict(
                values = ['fields_in_file',],
            ),
            filenames = dict(
                info = "Filenames to process. If absent, will be determined " +
                       "according to reference resources and/or regular expressions on filenames.",
                type=FPList,
                optional = True,
                default=FPList([]),
            ),
            normalized_validation_threshold = dict(
                info = "Threshold on normalized distance for validation. " +
                       "Normalized distance is computed as normalized(test, ref) - normalized(ref, ref) " +
                       "where " +
                       "normalized(test, ref) == (test-ref.min()) / (ref.max()-ref.min())",
                type = float,
                optional = True,
                default = NORMALIZED_FIELDS_DIFF,
            ),
            ignore_meta = dict(
                info = "Ignore fields metadata in comparison.",
                type = bool,
                optional = True,
                default = False
            ),
            ignore_orphan_fields = dict(
                info = "Ignore fields that are present in only one of the resources.",
                type = bool,
                optional = True,
                default = False
            ),
            hide_bit_repro_fields = dict(
                info = "Do not show bit-reproducible fields in comparison summary.",
                type = bool,
                optional = True,
                default = True,
            ),
            compute_stats = dict(
                info = "Compute (min, avg, max) when parsing fields.",
                type = bool,
                optional = True,
                default = False
            ),
        )
    )

    _re_files = [re.compile(p)
                 for p in (
                     # historic of post-processed files
                     '(?P<prefix>(ICMSH)|(PF)|(GRIBPF))(?P<cnmexp>\w{4})(?P<area>.+)?\+(?P<term_h>\d+)(\:(?P<term_m>\d{2}))?(?P<sfx>\.sfx)?$',
                     # coupling files
                     '(?P<prefix>CPLOUT)\+(?P<term_h>\d+)(\:(?P<term_m>\d{2}))?$',
                     # pgd files
                     '(?P<prefix>PGD)\.fa',
                     # prep files
                     '(?P<prefix>PREP1_interpolated)\.fa')
                 ]
    # accepted_kinds
    filekinds = ('historic', 'gridpoint', 'pgdfa', 'initial_condition')
    # reference prefixes
    ref_prefix = 'ref.'
    cnty_prefix = 'continuity.'
    csty_prefix = 'consistency.'

    def __init__(self, *args, **kwargs):
        super(FieldsInFileExpert, self).__init__(*args, **kwargs)

    def _find_files_to_parse(self):
        self.files = {}
        if len(self.filenames) > 0:
            for f in self.filenames:
                if f not in os.listdir(os.getcwd()):
                    message = "Output file not found: {}".format(f)
                    if self.fatal_exceptions:
                        raise IOError(message)
                    else:
                        logger.warning(' '.join([message," => ignored in comparison."]))
                else:
                    self.files[f] = {}
        else:
            # find files in working directory
            filenames = os.listdir(os.getcwd())
            for f in filenames:
                for reg in self._re_files:
                    if reg.match(f):
                        self.files[f] = {}
                        break

    def _parse(self):
        """Parse file, list fields."""
        import epygram
        epygram.init_env()
        self._find_files_to_parse()
        for filename in self.files:
            r = epygram.formats.resource(filename, 'r')
            self.files[filename] = {f:{} for f in r.listfields()}
            if self.compute_stats:
                for f in self.files[filename]:
                    fld = r.readfield(f)
                    self.files[filename][f]['min'] = fld.min()
                    self.files[filename][f]['avg'] = fld.mean()
                    self.files[filename][f]['max'] = fld.max()

    def summary(self):
        summary = {'Number of files':len(self.files),
                   'Files':{f:{'Number of fields':len(self.files[f]),}
                            for f in self.files}
                   }
        if self.compute_stats:
            for f in self.files:
                summary['Files'][f]['Stats'] = self.files[f]
        return summary

    def _make_pairs(self, references):
        ref_handlers = [r for r in references
                        if r.resource.kind in self.filekinds]
        ref_filenames = [r.container.localpath() for r in ref_handlers]
        if len(self.filenames) == 0:
            pairs = self._make_pairs_from_references(ref_filenames)
        else:
            pairs = self._make_pairs_from_attribute(ref_filenames)
        return pairs

    def _make_pairs_from_references(self, ref_filenames):
        pairs = []
        # find local files matching references
        for ref in ref_filenames:
            if ref not in os.listdir(os.getcwd()):
                message = "Reference file: '{}' not found'.".format(ref)
                if self.fatal_exceptions:
                    raise ExpertError(message)
                else:
                    logger.warning(' '.join([message," => ignored in comparison."]))
                    continue
            f = ref.lstrip(self.ref_prefix).lstrip(self.cnty_prefix).lstrip(self.csty_prefix)
            if f not in os.listdir(os.getcwd()):
                message = "Reference file: '{}' has no local output equivalent '{}'.".format(ref, f)
                if self.fatal_exceptions:
                    raise ExpertError(message)
                else:
                    logger.warning(' '.join([message," => ignored in comparison."]))
            else:
                pairs.append((f, ref))
        return pairs

    def _make_pairs_from_attribute(self, ref_filenames):
        pairs = []
        # start from list of asked files
        for f in self.filenames:
            if f not in os.listdir(os.getcwd()):
                message = "Output file not found: {}".format(f)
                if self.fatal_exceptions:
                    raise ExpertError(message)
                else:
                    logger.warning(' '.join([message," => ignored in comparison."]))
                    continue
            ref = None
            for p in (self.ref_prefix, self.cnty_prefix, self.csty_prefix):
                if p + f in ref_filenames:
                    ref = p + f
                    break
            if ref is None:
                message = "Reference file: '{}' not found.".format(ref)
                if self.fatal_exceptions:
                    raise ExpertError(message)
                else:
                    logger.warning(' '.join([message," => ignored in comparison."]))
            else:
                pairs.append((f, ref))
        return pairs

    def _compare(self, references):
        """
        Compare to a reference.

        :param references: the list of reference resource handlers
        """
        pairs = self._make_pairs(references)
        comp = {}
        if len(pairs) > 0:
            for (test, ref) in pairs:
                logger.info('{} // {}'.format(test, ref))
                comp[test] = compare_2_files(test, ref,
                                             ignore_meta=self.ignore_meta,
                                             ignore_orphan_fields=self.ignore_orphan_fields,
                                             hide_bit_repro_fields=self.hide_bit_repro_fields,
                                             normalized_validation_threshold=self.normalized_validation_threshold,
                                             fatal_exceptions=self.fatal_exceptions)
            overall = {}
            overall['Validated'] = all([c.get('Validated') for c in comp.values()])
            overall['Bit-reproducible'] = all([c.get('Bit-reproducible') for c in comp.values()])
            overall['Validated means'] = comp[pairs[0][0]].get('Validated means')
            overall['mainMetrics'] = comp[pairs[0][0]].get('mainMetrics')
            overall['Max normalized diff'] = '{:%}'.format(
                max([float(c.get('Max normalized diff').strip('%')) / 100.
                     for c in comp.values()]))
            comp.update(overall)
        else:
            msg = "No kind={} reference resources provided".format(str(self.filekinds))
            if self.fatal_exceptions:
                raise ExpertError(msg)
            else:
                logger.warning(' '.join([msg," => ignored in comparison."]))
                comp['comparisonStatus'] = {'symbol':'0',
                                            'short':'- No ref -',
                                            'text':'No adequate reference available (kind={})'.format(str(self.filekinds))}
        return comp


def compare_2_files(test, ref,
                    ignore_meta=False,
                    ignore_orphan_fields=False,
                    hide_bit_repro_fields=True,
                    normalized_validation_threshold=NORMALIZED_FIELDS_DIFF,
                    fatal_exceptions=True):
    """
    Compare 2 files containing fields.

    Normalized distance is computed as normalized(test, ref) - normalized(ref, ref)
    where
    normalized(test, ref) == (test-ref.min()) / (ref.max()-ref.min())

    :param ignore_meta: Ignore metadata in comparison.
    :param ignore_orphan_fields: Ignore fields present in only one of the resources.
    :param hide_bit_repro_fields: Do not show bit-reproducible fields in comparison.
    :param normalized_validation_threshold: Threshold on normalized distance for validation.
    :param fatal_exceptions: Raise comparing errors.
    """
    import epygram
    epygram.init_env()
    t = epygram.formats.resource(test, 'r')
    r = epygram.formats.resource(ref, 'r')
    comp = {}
    # list fields
    test_list = set(t.listfields())
    ref_list = set(r.listfields())
    # new and lost
    new_fields = sorted(test_list.difference(ref_list))
    lost_fields = sorted(ref_list.difference(test_list))
    # common fields: comparison
    intersection = test_list.intersection(ref_list)
    fields_status = {}
    max_normalized_diff = 0.
    for f in sorted(intersection):
        try:
            (status,
             max_normalized_diff,
             ignore_meta) = compare_2_fields(t, r, f, max_normalized_diff,
                                             ignore_meta=ignore_meta,
                                             normalized_validation_threshold=normalized_validation_threshold)
        except Exception as e:
            if fatal_exceptions:
                raise
            status = {'Error during comparison':str(e)}
        if not status.get('Validated', False) or not hide_bit_repro_fields:
            fields_status[f] = status

    # status over all fields
    comp['Validated'] = all([status.get('Validated', False) for status in fields_status.values()])
    comp['Validated means'] = 'All fields have identical shape/mask than reference, and normalized errors lower than {}'.format(normalized_validation_threshold)
    if not ignore_orphan_fields:  # check that there is no orphan
        if len(new_fields + lost_fields) > 0:
            comp['Validated'] = False
        comp['Validated means'] += ', and no field is orphan on one or the other side.'
    # bit-repro status
    comp['Bit-reproducible'] = all([(status.get('Data bit-repro', False) and
                                     status.get('Validity diff', None) is None and
                                     status.get('Geometry diff', None) is None)
                                    for status in fields_status.values()])
    if t.format == 'GRIB':
        comp['Common fields differences'] = []
        for f in sorted(intersection):
            fields_status[f]['fid'] = f
            comp['Common fields differences'].append(fields_status[f]['fid'])
    else:
        comp['Common fields differences'] = fields_status
    comp['Max normalized diff'] = '{:%}'.format(max_normalized_diff)
    comp['mainMetrics'] = 'Max normalized diff'
    comp['New fields'] = new_fields if len(new_fields) > 0 else None
    comp['Lost fields'] = lost_fields if len(lost_fields) > 0 else None
    return comp


def compare_2_fields(test_resource, ref_resource, fid,
                     max_normalized_diff=0.,
                     ignore_meta=False,
                     normalized_validation_threshold=NORMALIZED_FIELDS_DIFF):
    """
    Compare two same fields from different resources.

    Normalized distance is computed as normalized(test, ref) - normalized(ref, ref)
    where
    normalized(test, ref) == (test-ref.min()) / (ref.max()-ref.min())

    :param max_normalized_diff: maximum normalized difference to be updated
    :param ignore_meta: Ignore metadata in comparison.
    :param normalized_validation_threshold: Threshold on normalized distance for validation.
    """
    import epygram
    status = {}
    tfld = test_resource.readfield(fid)
    rfld = ref_resource.readfield(fid)
    if not isinstance(tfld, epygram.fields.MiscField):
        for fld in (tfld, rfld):  # would not be sure of the meaning of errors in spectral space
            if fld.spectral:
                fld.sp2gp
    # metadata
    if not isinstance(tfld, epygram.fields.MiscField) and not ignore_meta:
        status['Validity diff'] = tfld.validity.recursive_diff(rfld.validity)
        status['Geometry diff'] = tfld.geometry.recursive_diff(rfld.geometry)
        if test_resource.format == 'FA':  # after the first one, in case of FA resources, skip metadata comparison
            ignore_meta = True
    # data
    if tfld.data.shape != rfld.data.shape:
        status['Data diff'] = 'Comparison not possible: dimensions differ'
        validated = False
        status['Data bit-repro'] = False
    else:
        if isinstance(tfld.data.dtype, (int, float)):
            status['Data bit-repro'] = bool(numpy.all(tfld.data - rfld.data <= EPSILON))
        else:
            status['Data bit-repro'] = bool(numpy.all(tfld.data == rfld.data))
        if not status['Data bit-repro']:
            data_diff, common_mask = tfld.normalized_comparison(rfld)
            status['Data diff'] = data_diff
            loc_max = max([abs(v) for v in data_diff.values()])
            if loc_max > max_normalized_diff:
                max_normalized_diff = loc_max
    # conclude about field validation
    if any([status.get('Validity diff', None),
            status.get('Geometry diff', None)]):
        validated = False
    if status['Data bit-repro']:
        validated = True
    else:
        if not common_mask:
            validated = False
        elif any([abs(v) >= normalized_validation_threshold
                  for v in data_diff.values()]):
            validated = False
        else:
            validated = True
    status['Validated'] = validated
    return status, max_normalized_diff, ignore_meta
