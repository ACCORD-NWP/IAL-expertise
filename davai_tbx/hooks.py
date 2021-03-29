#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division


def hook_temporary_OOPS_3DVar_fix(t, rh, NDVar):
    """
    Temporary hook for model namelist, until OOPS better handles time in 3DVar case
    (and to avoid to duplicate model namelists in for 3D/4DVar versions)
    """
    if NDVar == '3DVar':
        # 3DVar case
        if 'NAMRIP' in rh.contents:
            print("Set ['NAMRIP']['CSTOP'] = 'h0'")
            rh.contents['NAMRIP']['CSTOP'] = 'h0'
    rh.save()


def hook_adjust_DFI(t, rh, NDVar):
    """
    Runtime tuning of DFI in Screening:

    - unplug DFI in 3DVar case
    - or tune number of steps to timestep
    """
    if NDVar == '3DVar':
        # because no DFI in 3DVar screening (and avoiding to duplicate model namelists)
        print("Unplug DFI")
        if 'NAMINI' in rh.contents:
            rh.contents['NAMINI']['LDFI'] = False
            rh.contents['NAMINI'].delvar('NEINI')
        if 'NAMDFI' in rh.contents:
            rh.contents['NAMDFI'].delvar('NEDFI')
            rh.contents['NAMDFI'].delvar('NTPDFI')
            rh.contents['NAMDFI'].delvar('TAUS')
        if 'NAMRIP' in rh.contents:
            rh.contents['NAMRIP']['CSTOP'] = 'h0'
    else:
        # Because timestep is not that of the operational screening
        print("Adjust NSTDFI to timestep")
        rh.contents['NAMDFI']['NSTDFI'] = 6
    rh.save()


def hook_gnam(t, rh, gnam_as_dict):
    """Gnam a namelist based on a dict(BLOCK={KEY:VALUE, ...}, ...)"""
    from bronx.datagrip.namelist import NamelistSet
    gnam = NamelistSet()
    for blockname, block in gnam_as_dict.items():
        for key, value in block.items():
            print("Gnam setting: {}:{} = {}".format(blockname, key, value))
            if blockname not in gnam:
                gnam.newblock(blockname)
            gnam[blockname][key] = value
    rh.contents.merge(gnam)
    rh.save()


def hook_OOPS_2_CNT0(t, rh):
    """Hook to turn OOPS namelist into CNT0 namelist."""
    gnam = {'NAMARG': {'CNMEXP':'MINI'},
            'NAMCT0': {'L_OOPS':False}}
    hook_gnam(t, rh, gnam)
    #print("Set ['NAMARG']['CNMEXP'] = 'MINI'")
    #rh.contents['NAMARG']['CNMEXP'] = 'MINI'
    #print("Set ['NAMCT0']['L_OOPS'] = .FALSE.")
    #rh.contents['NAMCT0']['L_OOPS'] = False
    #rh.save()

