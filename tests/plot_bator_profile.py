#!/usr/bin/env python
import json
import matplotlib.pyplot as plt
from ial_expertise.experts.profiling import plot_bator_profile
with open('data/taskinfo.expertise.continuity.json', 'r') as f:
    compdict = json.load(f)

fig = plot_bator_profile(compdict['bator_profile'])
plt.show()
