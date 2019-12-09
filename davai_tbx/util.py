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


def write_xpinfo(user, xpid, ref_xpid, appenv, commonenv, input_store, usecase,
                 appenv_details, commonenv_details):
    """Write info about experiment in 'xpinfo.json'."""
    metadata = {'initial_time_of_launch':date.utcnow().isoformat().split('.')[0], # + ' Z',
                'user':user,
                'xpid':xpid,
                'ref_xpid':ref_xpid,
                'appenv':appenv,
                'commonenv':commonenv,
                'input_store':input_store,
                'usecase':usecase,
                'appenv_details':'<br>'.join(appenv_details),
                'commonenv_details':'<br>'.join(commonenv_details),
                # optional
                'git_branch':os.environ.get('GIT_BRANCH'),
                'comment':os.environ.get('COMMENT'),
                'pack':os.environ.get('PACK'),
                }
    with open('xpinfo.json', 'w') as out:
        json.dump(metadata, out, indent=4, sort_keys=True)
