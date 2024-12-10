#!/usr/bin/env python
import os
import json
import matplotlib.pyplot as plt
from ial_expertise.experts.profiling import plot_bator_profile
tests = os.path.abspath(os.path.dirname(__file__))
taskinfo = os.path.join(tests, 'data/taskinfo.expertise.continuity.json')
with open(taskinfo, 'r') as f:
    compdict = json.load(f)

fig = plot_bator_profile(compdict['bator_profile'])
plt.show()
