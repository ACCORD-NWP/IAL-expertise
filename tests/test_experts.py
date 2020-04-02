#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Météo France (2014-)
# This software is governed by the CeCILL-C license under French law.
# http://www.cecill.info

from __future__ import print_function, absolute_import, division, unicode_literals

from unittest import main, TestCase
import io
import time

import epygram
from epygram import epylog

from davai_tbx.experts import oops, util

timing = False

epygram.init_env()
epylog.setLevel('WARNING')


class Test_oops(TestCase):

    def setUp(self):
        if timing:
            self.startTime = time.time()

    def tearDown(self):
        if timing:
            t = time.time() - self.startTime
            with io.open('timings.txt', 'a') as out:
                out.write("%s: %.3f" % (self.id(), t) + '\n')

    def test_re_jo(self):
        self.assertTrue(oops.OOPSJoExpert._re_test.match(util.test_jo) and
                        oops.OOPSJoExpert._re_test.match(util.test_jo2))
        
    def test_re_ad(self):
        self.assertTrue(oops.OOPSJoADExpert._re_test.match(util.test_ad) and
                        oops.OOPSJoADExpert._re_test.match(util.test_ad2))
        
    def test_re_diff(self):
        self.assertTrue(oops.OOPSStateDiffExpert._re_test.match(util.test_diff) and
                        oops.OOPSStateDiffExpert._re_test.match(util.test_diff2))
    
    def test_re_var(self):
        self.assertTrue(oops.OOPSVariancesExpert._re_test.match(util.test_variances))
    
    def test_interpol(self):
        self.assertTrue(oops.OOPSInterpolExpert._re_test.match(util.test_interpol))

if __name__ == '__main__':
    main(verbosity=2)
