#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A collection of Experts.

Experts are meant to parse the result of a task, and eventually compare it
to a reference.
"""
import io
import json

import footprints


class ExpertError(Exception):
    pass


class OutputExpert(footprints.FootprintBase):

    _abstract = True
    _collector = ('outputexpert',)
    _footprint = dict(
        info = 'Abstract OutputExpert.',
        attr = dict(
            kind = dict(
                info = "Defines what is to be expertised.",
            ),
            fatal_exceptions = dict(
                info = "Raise parsing/summary/compare errors.",
                type = bool,
                optional = True,
                default = False,
            ),
        )
    )

    #: If the expert measures about execution rather than result of an Algo (e.g. profiling experts).
    side_expert = False

    def _parse(self):
        """Abstract method."""
        raise NotImplementedError('Abstract method')

    def parse(self):
        """Parse Output and return summary."""
        try:
            self._parse()
        except Exception as e:
            if self.fatal_exceptions:
                raise
            else:
                summary = {"Parsing":"Failed",
                           "Exception":str(e)}  # TODO: add traceback ?
        else:
            try:
                summary = self.summary()
            except Exception as e:
                if self.fatal_exceptions:
                    raise
                else:
                    summary = {"Summary":"Failed",
                               "Exception":str(e)}
        return summary

    def compare(self, references, *args, **kwargs):
        """
        Compare to references.

        :param references: the list of reference resource handlers
        """
        try:
            comp = self._compare(references, *args, **kwargs)
        except Exception as e:
            if self.fatal_exceptions:
                raise
            else:
                comp = {'Comparison':'Failed',
                        'Exception':str(e)}
        return comp

    def _compare(self, references, *args, **kwargs):
        """
        Actual comparison method, to be implemented by each expert.

        :param references: the list of reference resource handlers
        """
        raise NotImplementedError('This is an abstract method. Must be implemented in actual expert.')

    @classmethod
    def filter_one_resource(cls, references, rkind):
        """Get kind=rkind resource, only one."""
        if isinstance(rkind, str):
            rkind = (rkind,)
        references = [r for r in references if r.resource.kind in rkind]
        if len(references) > 1:
            raise ExpertError("Too many resources of kind '{}' provided".format(rkind))
        elif len(references) < 1:
            raise ExpertError("No resource of kind '{}' provided".format(rkind))
        else:
            return references[0]

    def _compare_summaries(self, references, *args, **kwargs):
        """
        Compare to a reference summary.
        """
        ref_summary = self.filter_one_resource(references, rkind=('taskinfo', 'statictaskinfo'))
        with io.open(ref_summary.container.localpath(), 'r') as _ref:
            ref_summary_in = json.load(_ref)
        try:
            ref_summary_in = ref_summary_in[self.kind]
        except KeyError:
            if 'Crashed' in ref_summary_in['Status']['short']:
                comp = {'symbol':'+',
                        'short':'+ Alive again +',
                        'text':'Task Ended, whereas reference was Crashed ! (so no comparison available)'}
            else:
                raise KeyError("The reference summary does not contain key for this expert kind: {}".format(self.kind))
        else:
            comp = self.compare_2summaries(self.summary(), ref_summary_in,
                                           *args, **kwargs)
        return comp


class TextOutputExpert(OutputExpert):

    _abstract = True
    _footprint = dict(
        info = 'Provide a reading method.',
        attr = dict(
            output = dict(
                info = "The text output file to parse.",
            ),
        )
    )

    def _read_txt_output(self, filename=None):
        if filename is None:
            filename = self.output
        with io.open(filename, 'r') as _file:
            return [l.strip() for l in _file.readlines()]


from . import thresholds
from . import oops, profiling, fields, assim, setup, build
