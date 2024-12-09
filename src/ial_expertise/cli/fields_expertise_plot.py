#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse

from ..experts.fields import scatter_fields_process_summary


def main():
    """Plot fields normalized errors expertise."""
    args = get_args()
    scatter_fields_process_summary(args.expertise)


def get_args():
    parser = argparse.ArgumentParser(description='Plot fields normalized errors expertise.')
    parser.add_argument('expertise',
                        help="Fields expertise file (.json)")
    return parser.parse_args()

