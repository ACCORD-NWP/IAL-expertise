#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Météo France (2014-)
# This software is governed by the CeCILL-C license under French law.
# http://www.cecill.info

from __future__ import print_function, absolute_import, unicode_literals, division

import os
import sys
import argparse

from vortex import toolbox
import common  # @UnusedImport

# Automatically set the python path
package_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, package_path)

from davai_tbx.experts.fields import scatter_fields_process_summary


def main(xpid, vapp, vconf,
         block, model, cutoff, date):
    """Get comparison and plot."""
    found = toolbox.rload(kind='taskinfo',
                          scope='continuity',
                          task='expertise',
                          namespace='vortex.multi.fr',
                          experiment=xpid,
                          vapp=vapp,
                          vconf=vconf,
                          block=block,
                          model=model,
                          cutoff=cutoff,
                          date=date,
                          local='{}.expertise.json'.format(xpid))
    found[0].get()
    report = found[0].container.localpath()
    print('Report: {}'.format(report))
    scatter_fields_process_summary(report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Plot normalized errors comparison from fields_in_file Expert.')
    parser.add_argument('xpid',
                        help="Grib comparison XPID")
    parser.add_argument('--vapp',
                        help="Vortex App",
                        default='arpege')
    parser.add_argument('--vconf',
                        help="Vortex Conf",
                        default='4dvarfr')
    parser.add_argument('--block',
                        help="Vortex block",
                        default='forecast')
    parser.add_argument('--model',
                        help="Vortex model",
                        default='arpege')
    parser.add_argument('--cutoff',
                        help="Vortex cutoff",
                        default='prod')
    parser.add_argument('-d', '--date',
                        help="Vortex date",
                        required=True)

    args = parser.parse_args()

    main(**vars(args))
