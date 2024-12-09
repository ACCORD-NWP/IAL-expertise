#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse

from ..experts.fields import scatter_fields_process_summary


def main():
    """Get fields normalized errors expertise (and optionally plot)."""
    from vortex import toolbox
    import common  # @UnusedImport
    args = get_args()
    found = toolbox.rload(kind='taskinfo',
                          scope='continuity',
                          task='expertise',
                          namespace='vortex.multi.fr',
                          experiment=args.xpid,
                          vapp=args.vapp,
                          vconf=args.vconf,
                          block=args.block,
                          model=args.model,
                          cutoff=args.cutoff,
                          member=args.member,
                          date=args.date,
                          local='{}.expertise.json'.format(args.xpid))
    found[0].get()
    report = found[0].container.localpath()
    print('Report: {}'.format(report))
    if args.plot:
        scatter_fields_process_summary(report)


def get_args():
    parser = argparse.ArgumentParser(description='Get fields normalized errors expertise (and optionally plot).')
    parser.add_argument('xpid',
                        help="Grib comparison XPID")
    parser.add_argument('-d', '--date',
                        help="Vortex date",
                        required=True)
    parser.add_argument('-p', '--plot',
                        help="Activate plotting",
                        action='store_true',
                        default=False)
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
    parser.add_argument('--member',
                        help="Vortex member",
                        default=None)
    return parser.parse_args()

