#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Useful objects/functions.
"""

from __future__ import print_function, absolute_import, division, unicode_literals
import six

import json
import sys
import os

from bronx.stdtypes import date

from . import __version__


class TaskSummary(dict):
    """
    A summary of a task contains info about the job, according to a series of
    Experts.

    Each Expert is a key of the TaskSummary.
    """

    def __init__(self, from_file=None):
        if from_file is not None:
            self._load(from_file)

    def dump(self, out=sys.stdout):
        """Dump the TaskSummary into a JSON file."""
        if isinstance(out, six.string_types):
            close = True
            out = open(out, 'w')
        else:
            close = False
        json.dump(self, out, indent=4, sort_keys=True)
        if close:
            out.close()

    def _load(self, filein):
        if isinstance(filein, six.string_types):
            close = True
            filein = open(filein, 'r')
        else:
            close = False
        asdict = json.load(filein)
        if close:
            filein.close()
        self.clear()
        self.update(asdict)


def write_xpinfo(user, xpid, ref_xpid, usecase, commonenv, commonenv_details,
                 appenv=None, input_store=None, appenv_details=None,  # DEPRECATED
                 appenv_lam=None, appenv_global=None, appenv_clim=None,
                 appenv_lam_details=None, appenv_global_details=None,
                 input_store_lam=None, input_store_global=None):
    """Write info about experiment in 'xpinfo.json'."""
    metadata = {'initial_time_of_launch':date.utcnow().isoformat().split('.')[0],
                'user':user,
                'xpid':xpid,
                'ref_xpid':ref_xpid,
                'commonenv':commonenv,
                'usecase':usecase,
                'commonenv_details':'<br>'.join(commonenv_details),
                # optional
                'git_branch':os.environ.get('GIT_BRANCH'),
                'comment':os.environ.get('COMMENT'),
                'pack':os.environ.get('PACK'),
                }
    # DEPRECATED
    if appenv:
        metadata['appenv'] = appenv
    if input_store:
        metadata['input_store'] = input_store
    if appenv_details:
        metadata['appenv_details'] = '<br>'.join(appenv_details)
    # NEW
    if appenv_lam:
        metadata['appenv_lam'] = appenv_lam
    if appenv_global:
        metadata['appenv_global'] = appenv_global
    if appenv_clim:
        metadata['appenv_clim'] = appenv_clim
    if input_store_lam:
        metadata['input_store_lam'] = input_store_lam
    if input_store_global:
        metadata['input_store_global'] = input_store_global
    if appenv_lam_details:
        metadata['appenv_lam_details'] = '<br>'.join(appenv_lam_details)
    if appenv_global_details:
        metadata['appenv_global_details'] = '<br>'.join(appenv_global_details)
    # write
    with open('xpinfo.json', 'w') as out:
        json.dump(metadata, out, indent=4, sort_keys=True)


class XPMetadata(object):
    """Collect metadata about XP and save it."""
    env_catalog_variables = ('APPENV', 'APPENV_LAM', 'APPENV_GLOBAL',
                             'APPENV_CLIM', 'COMMONENV')

    def __init__(self, xpid):
        ref_xpid = os.environ.get('REF_XPID')
        if ref_xpid == xpid:
            ref_xpid = None
        self._dict = {'xpid':xpid,
                      'initial_time_of_launch':date.utcnow().isoformat().split('.')[0],
                      'davai_tbx':__version__,
                      'user':os.environ['USER'],
                      # absent-safe
                      'ref_xpid':ref_xpid,
                      'usecase':os.environ.get('USECASE'),
                      'git_branch':os.environ.get('IA4H_GITREF'),  # CLEANME: to be pruned at some point
                      'IA4H_gitref':os.environ.get('IA4H_GITREF'),
                      'comment':os.environ.get('COMMENT'),
                      }
        self._dict.update(self._gmkpack_info())
        for k in self.env_catalog_variables:
            e = os.environ.get(k)
            if e:
                self.set(k.lower(), e)
        for k in ('INPUT_STORE', 'INPUT_STORE_LAM', 'INPUT_STORE_GLOBAL'):
            s = os.environ.get(k)
            if s:
                self.set(k.lower(), s)
        self._set_details()

    def _gmkpack_info(self):
        from ia4h_scm.algos import guess_packname
        pack = guess_packname(os.environ.get('IA4H_GITREF', os.environ.get('IAL_GIT_REF')),
                              os.environ.get('GMKPACK_COMPILER_LABEL'),
                              os.environ.get('GMKPACK_PACKTYPE'),
                              os.environ.get('GMKPACK_COMPILER_FLAG'))
        return {'gmkpack_packname':pack,
                'homepack':os.environ.get('HOMEPACK'),
                'rootpack':os.environ.get('ROOTPACK'),
                'GMKPACK_COMPILER_LABEL':os.environ.get('GMKPACK_COMPILER_LABEL'),
                'GMKPACK_COMPILER_FLAG':os.environ.get('GMKPACK_COMPILER_FLAG'),
                'pack':pack,  # CLEANME: to be pruned at some point
                }

    def set(self, k, v):
        self._dict[k] = v

    def get(self, k=None):
        if k is None:
            return copy.copy(self._dict)
        else:
            return self._dict[k]

    @property
    def _which_env_catalog_details(self):
        """Get keys and values of necessary env-catalogs to be detailed."""
        return {k.lower():self._dict.get(k.lower())
                for k in self.env_catalog_variables
                if k.lower() in self._dict}

    @classmethod
    def _get_env_catalog_details(cls, env):
        from gco.tools import uenv, genv
        if any([env.startswith(scheme) for scheme in ('uget:', 'uenv:')]):
            # uenv
            details = uenv.nicedump(env,
                                    scheme='uget',
                                    netloc='uget.multi.fr')
        else:
            # genv
            details = ['%s="%s"' % (k, v)
                       for (k, v) in genv.autofill(env).items()]
        return details

    def _set_details(self):
        for k, env in self._which_env_catalog_details.items():
            details = self._get_env_catalog_details(env)
            self._dict['{}_details'.format(k.lower())] = '<br>'.join(details)

    def write(self):
        """Dump in file (xpinfo.json)."""
        with open('xpinfo.json', 'w') as out:
            json.dump(self._dict, out, indent=4, sort_keys=True)


def context_info_for_task_summary(context):
    """Get some infos from context for task summary."""
    session = {'rundir':context.rundir}
    for k in ('MTOOL_STEP_ABORT', 'MTOOL_STEP_DEPOT'):
        v = context.env.get(k, None)
        if v:
            session[k] = v
    return session

