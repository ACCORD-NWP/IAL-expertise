#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IAL expertise package: expertise outputs of IAL tasks.
"""
from __future__ import print_function, absolute_import, division, unicode_literals

import os
import io

package_rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__path__[0])))  # realpath to resolve symlinks
__version__ = "1.2.0"

from . import experts, task
