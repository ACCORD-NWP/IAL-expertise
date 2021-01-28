#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex import toolbox
from vortex.layout.jobs import JobAssistantPlugin


class DavaiJobAssistantPlugin(JobAssistantPlugin):
    """JobAssistant plugin for Davai."""
    _footprint = dict(
        info = 'Davai JobAssistant Plugin',
        attr = dict(
            kind = dict(
                values = ['davai', ]
            ),
        ),
    )

    def plugable_env_setup(self, t, **kw):  # @UnusedVariable
        t.env.DAVAI_SERVER = 'http://intra.cnrm.meteo.fr/gws/davai'
        #FIXME: t.env.DAVAI_SERVER = t.conf.DAVAI_SERVER


class IncludesTaskPlugin(object):
    """Provide a method to input usual tools, known as 'Task Includes' in Olive."""

    def _load_usual_tools(self):
        if 'early-fetch' in self.steps:
            self.sh.title('Toolbox usual-tools tb_ut01')
            tb_ut01 = toolbox.input(
                role           = 'LFIScripts',
                format         = 'unknown',
                genv           = self.conf.commonenv,
                kind           = 'lfiscripts',
                local          = 'usualtools/tools.lfi.tgz',
            )
            print(self.ticket.prompt, 'tb_ut01 =', tb_ut01)
            print()
            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox usual-tools tb_ut02')
            tb_ut02 = toolbox.input(
                role           = 'IOPoll',
                format         = 'unknown',
                genv           = self.conf.commonenv,
                kind           = 'iopoll',
                language       = 'perl',
                local          = 'usualtools/io_poll',
            )
            print(self.ticket.prompt, 'tb_ut02 =', tb_ut02)
            print()
            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox usual-tools tb_ut03')
            tb_ut03 = toolbox.input(
                role           = 'LFITOOLS',
                format         = 'gmap',
                genv           = 'bullx',
                kind           = 'lfitools',
                local          = 'usualtools/lfitools',
                remote         = '{0:s}/bin'.format(self.conf.pack),
                setcontent     = 'binaries',
            )
            print(self.ticket.prompt, 'tb_ut03 =', tb_ut03)
            print()
            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox usual-tools tb_ut04')
            tb_ut04 = toolbox.input(
                role           = 'AdditionalGribAPIDefinitions',
                format         = 'unknown',
                genv           = self.conf.commonenv,
                kind           = 'gribapiconf',
                local          = 'extra_grib_defs/gribdef.tgz',
                target         = 'definitions',
            )
            print(self.ticket.prompt, 'tb_ut04 =', tb_ut04)
            print()
        return tb_ut01, tb_ut02, tb_ut03, tb_ut04


class IA4HTaskPlugin(object):
    pass
# TODO: plugin for usual IA4H outputs: listing (and as promise), DrHookprof, stdeo...


class DavaiTaskPlugin(object):
    """Provide useful methods for Davai IOs."""
    experts = []
    lead_expert = None

    def _promised_expertise(self):
        if 'early-fetch' in self.steps:
            self.sh.title('Toolbox expertise promise tb_expt_p01')
            tb_expt_p01 = toolbox.promise(
                role           = 'TaskSummary',
                block          = self.tag,
                experiment     = self.conf.xpid,
                format         = 'json',
                hook_train     = ('davai.hooks.take_the_DAVAI_train', self.conf.expertise_fatal_exceptions),
                kind           = 'taskinfo',
                local          = 'task_summary.[format]',
                namespace      = self.conf.namespace,
                nativefmt      = '[format]',
                scope          = 'itself',
                task           = 'expertise',
            )
            print(self.ticket.prompt, 'tb_expt_p01 =', tb_expt_p01)
            print()
        return tb_expt_p01

    def _reference_continuity_expertise(self):
        if 'early-fetch' in self.steps:
            self.sh.title('Toolbox reference continuity expertise tb_ref01')
            tb_ref01 = toolbox.input(
                role           = 'Reference',
                namespace      = self.conf.ref_namespace,
                experiment     = self.conf.ref_xpid,
                block          = self.tag,
                fatal          = False,
                format         = 'json',
                kind           = 'taskinfo',
                local          = 'ref_summary.[format]',
                nativefmt      = '[format]',
                scope          = 'itself',
                task           = 'expertise',
            )
            print(self.ticket.prompt, 'tb_ref01 =', tb_ref01)
            print()
        return tb_ref01

    def _reference_consistency_expertise(self):
        if 'early-fetch' in self.steps or 'fetch' in self.steps:  # probably produced in the same job
            self.sh.title('Toolbox reference consistency expertise tb_ref_s01')
            tb_ref_s01 = toolbox.input(
                role           = 'Reference',
                experiment     = self.conf.xpid,
                block          = self.conf.consistency_ref_block,
                fatal          = False,
                format         = 'json',
                kind           = 'taskinfo',
                local          = 'ref_summary.[format]',
                nativefmt      = '[format]',
                scope          = 'itself',
                task           = 'expertise',
            )
            print(self.ticket.prompt, 'tb_ref_s01 =', tb_ref_s01)
            print()
        return tb_ref_s01

    def _expertise(self):
        if 'compute' in self.steps:
            self.sh.title('Toolbox algo tbexpertise')
            tbexpertise = toolbox.algo(
                block          = self.tag,
                engine         = 'algo',
                experiment     = self.conf.xpid,
                experts        = self.experts,
                lead_expert    = self.lead_expert,
                fatal_exceptions = self.conf.expertise_fatal_exceptions,
                ignore_reference = self.conf.ignore_reference,
                kind           = 'expertise',
            )
            print(self.ticket.prompt, 'tbexpertise =', tbexpertise)
            print()
        return tbexpertise

    def _output_expertise(self):
        if 'late-backup' in self.steps:
            self.sh.title('Toolbox expertise output tb_expt01')
            tb_expt01 = toolbox.output(
                role           = 'TaskSummary',
                kind           = 'taskinfo',
                block          = self.tag,
                experiment     = self.conf.xpid,
                hook_train     = ('davai.hooks.take_the_DAVAI_train', self.conf.expertise_fatal_exceptions),
                format         = 'json',
                local          = 'task_summary.[format]',
                namespace      = self.conf.namespace,
                nativefmt      = '[format]',
                promised       = True,
                scope          = 'itself',
                task           = 'expertise',
            )
            print(self.ticket.prompt, 'tb_expt01 =', tb_expt01)
            print()
        return tb_expt01

    def _output_comparison_expertise(self):
        if 'late-backup' in self.steps:
            self.sh.title('Toolbox expertise output tb_expt02')
            tb_expt02 = toolbox.output(
                role           = 'TaskAgainstRef',
                kind           = 'taskinfo',
                block          = self.tag,
                experiment     = self.conf.xpid,
                hook_train     = ('davai.hooks.take_the_DAVAI_train', self.conf.expertise_fatal_exceptions),
                format         = 'json',
                local          = 'task_[scope].[format]',
                namespace      = self.conf.namespace,
                nativefmt      = '[format]',
                scope          = 'continuity,consistency',
                task           = 'expertise',                
            )
            print(self.ticket.prompt, 'tb_expt02 =', tb_expt02)
            print()
        return tb_expt02

