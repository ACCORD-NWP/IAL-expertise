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

    env_catalog_variables = ('APPENV', 'APPENV_LAM', 'APPENV_GLOBAL',
                             'APPENV_CLIM', 'COMMONENV')

    def __init__(self, xpid):
        self._dict = {'xpid':xpid,
                      'initial_time_of_launch':date.utcnow().isoformat().split('.')[0],
                      'user':os.environ['USER'],
                      # absent-safe
                      'ref_xpid':os.environ.get('REF_XPID'),
                      'usecase':os.environ.get('USECASE'),
                      'git_branch':os.environ.get('GIT_BRANCH'),
                      'comment':os.environ.get('COMMENT'),
                      'pack':os.environ.get('PACK'),
                      }
        for k in self.env_catalog_variables:
            e = os.environ.get(k)
            if e:
                self.set(k.lower(), e)
        for k in ('INPUT_STORE', 'INPUT_STORE_LAM', 'INPUT_STORE_GLOBAL'):
            s = os.environ.get(k)
            if s:
                self.set(k.lower(), s)
    
    def set(self, k, v):
        self._dict[k] = v
    
    def get(self, k=None):
        if k is None:
            return copy.copy(self._dict)
        else:
            return self._dict[k]
    
    def which_env_catalog_details(self):
        return {k.lower():self._dict.get(k.lower())
                for k in self.env_catalog_variables
                if k.lower() in self._dict}
    
    def set_env_catalog_details(self, k, details):
        self._dict['{}_details'.format(k.lower())] = '<br>'.join(details)
    
    def write(self):
        with open('xpinfo.json', 'w') as out:
            json.dump(metadata, out, indent=4, sort_keys=True)

def XP_which_env_to_pull():
    """Return a list of genv/uenv to be pulled."""
    envs = {}
    for k in :
        e = os.environ.get(k)
        if e:
            envs[k] = e
    return envs


def XP_metadata_collect(metadata):
    """Collect a series of metadata from environment variables."""
    
    for k, e in XP_which_env_to_pull().items():
        metadata[k.lower()] = e
    return metadata

def XPinfo_write():
