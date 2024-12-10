#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Profiling parsers."""
import re
import os
import subprocess
import numpy as np
import json
import io
import importlib.resources

from . import OutputExpert, ExpertError
from .util import ppp, EXTENDED_FLOAT_RE


class DrHook(OutputExpert):
    """
    Handles the DrHook profiling of a job.
    Must be instanciated in the actual directory of drhook files.
    """

    _footprint = dict(
        info = 'DrHook profiling parser.',
        attr = dict(
            kind = dict(
                info = "Two cases: 'drhook-max' merges drhook.by.proc by max walltime of routines; 'drhook-ave' by average.",
                values = ['drHookMax', 'drHookAve']
            ),
        )
    )

    side_expert = True

    _re_file1 = re.compile(r'drhook\.prof\.\d+')
    _re_file2 = re.compile(r'drhookprof\..+\.n\d+')
    _re_walltime = re.compile(r'Wall-times over all MPI-tasks \(secs\) : Min=(?P<min>\d+\.\d+), Max=(?P<max>\d+\.\d+), Avg=(?P<avg>\d+\.\d+), StDev=(?P<stdev>\d+\.\d+)')
    _re_mpi_tasks = re.compile(r'Number of MPI-tasks : (?P<mpi>\d+)')
    _re_openmp_threads = re.compile(r'Number of OpenMP-threads : (?P<openmp>\d+)')
    _header = "  Avg-%   Avg.time   Min.time   Max.time   St.dev  Imbal-%   # of calls : Name of the routine"

    def _parse(self):
        """Actual parsing."""
        self._find_drhookprof()
        if self.kind.endswith('Max'):
            self._merge_walltime_max()
        elif self.kind.endswith('Ave'):
            self._merge_walltime_ave()
        header_index = self.merged_drhook.index(self._header)
        self.general_info = self.merged_drhook[:header_index]
        self.rawprofile = self.merged_drhook[header_index:]
    
    @classmethod
    def parse_routines(cls, drhook_kind, profile):
        routine_profile = {}
        for line in profile[1:-1]:  # starts with header, ends with global info
            splitted, routine = line.split(' : ')
            splitted = splitted.split()
            if drhook_kind.endswith('Max'):
                routine_profile[routine] = float(splitted[3])  # 'Max.time'
            elif drhook_kind.endswith('Ave'):
                routine_profile[routine] = float(splitted[1])  # 'Avg.time'
        return routine_profile
    
    def summary(self):
        """Return a summary as a dict."""
        return {'Elapse time':self._get_walltime_max(),
                'MPI tasks':self._get_mpi_tasksnum(),
                'OpenMP threads':self._get_openmp_threads(),
                'General info':self.general_info,
                '_DrHookProfile':self.rawprofile}

    @classmethod
    def compare_2summaries(cls, test, ref, drhook_kind):
        """
        Compare 2 summaries: absolute and relative difference in Elapse time.
        """
        elapse_diff = test['Elapse time'] - ref['Elapse time']
        reldiff = elapse_diff / ref['Elapse time']
        comparison = {'Diff in Elapse time':elapse_diff,
                      'Relative diff in Elapse time':ppp(reldiff),
                      'mainMetrics':'Relative diff in Elapse time'}
        comparison.update(cls.compare_by_routine(test, ref, drhook_kind))
        return comparison

    def _compare(self, reference):
        """
        Compare to a reference summary: absolute and relative difference
        in Elapse time.
        """
        return self._compare_summaries(reference, drhook_kind=self.kind)

    # inner methods ############################################################
    def _find_drhookprof(self):
        """Look for DrHook files in directory."""
        workdir = os.getcwd()
        taskfiles = os.listdir(workdir)
        self.drhookfiles  = [f for f in taskfiles
                             if self._re_file1.match(f) or
                             self._re_file2.match(f)]
        if len(self.drhookfiles) == 0:
            raise ExpertError('No drhook files found.')

    def _merge_walltime(self, stat):
        script = importlib.resources.path("ial_expertise.drhook", 'drhook_merge_walltime_{}.pl'.format(stat))
        out = subprocess.check_output([script,] + self.drhookfiles)
        self.merged_drhook = out.decode('utf-8').split('\n')[:-1]  # to remove trailing empty line

    def _merge_walltime_ave(self):
        """Merge walltime of inner routines (self) by the average."""
        self._merge_walltime('ave')

    def _merge_walltime_max(self):
        """Merge walltime of inner routines (self) by the maximum."""
        self._merge_walltime('max')

    def _get_walltime_max(self):
        """Return the walltime over all MPI-tasks."""
        for l in self.merged_drhook:
            match = self._re_walltime.match(l)
            if match:
                return float(match.group('max'))

    def _get_mpi_tasksnum(self):
        """Return the number of MPI-tasks."""
        for l in self.merged_drhook:
            match = self._re_mpi_tasks.match(l)
            if match:
                return int(match.group('mpi'))

    def _get_openmp_threads(self):
        """Return the number of OpenMP threads."""
        for l in self.merged_drhook:
            match = self._re_openmp_threads.match(l)
            if match:
                return int(match.group('openmp'))

    @classmethod
    def compare_by_routine(cls, test_summary, ref_summary, drhook_kind):
        test_routine_profile = cls.parse_routines(drhook_kind, test_summary['_DrHookProfile'])
        ref_routine_profile = cls.parse_routines(drhook_kind, ref_summary['_DrHookProfile'])
        routines = set(test_routine_profile.keys()).intersection(set(ref_routine_profile.keys()))
        faster = ['None', 0.]
        slower = ['None', 0.]
        rel_faster = ['None', 0.]
        rel_slower = ['None', 0.]
        for r in routines:
            if ref_routine_profile[r] > 0.001:  # quicker routines don't matter
                diff = test_routine_profile[r] - ref_routine_profile[r]
                reldiff = diff / ref_routine_profile[r]
                if diff < 0. and diff <= faster[1]:
                    faster[1] = diff
                    faster[0] = r
                elif diff > 0. and diff >= slower[1]:
                    slower[1] = diff
                    slower[0] = r
                if reldiff < 0. and reldiff <= rel_faster[1]:
                    rel_faster[1] = reldiff
                    rel_faster[0] = r
                elif reldiff > 0. and reldiff >= rel_slower[1]:
                    rel_slower[1] = reldiff
                    rel_slower[0] = r
        def nicet(d,t,r):
            return '{:.3f} (ref:{}s => test:{}s)'.format(d,r,t)
        def nicep(d,t,r):
            return '{} (ref:{}s => test:{}s)'.format(d,r,t)
        return {'Highest slow-down - routine':slower[0],
                'Highest slow-down':nicet(slower[1],
                                          test_routine_profile[slower[0]],
                                          ref_routine_profile[slower[0]]),
                'Highest acceleration - routine':faster[0],
                'Highest acceleration':nicet(faster[1],
                                             test_routine_profile[faster[0]],
                                             ref_routine_profile[faster[0]]),
                'Highest relative acceleration - routine':rel_faster[0],
                'Highest relative acceleration':nicep(ppp(rel_faster[1]),
                                                      test_routine_profile[rel_faster[0]],
                                                      ref_routine_profile[rel_faster[0]]),
                'Highest relative slow-down - routine':rel_slower[0],
                'Highest relative slow-down':nicep(ppp(rel_slower[1]),
                                                   test_routine_profile[rel_slower[0]],
                                                   ref_routine_profile[rel_slower[0]]),
            }


class RSS(OutputExpert):
    """
    Assumes that the binary has been launched wrapped within
    /home/gmap/mrpa/meunierlf/SAVE/getrusage/rss.x
    """

    _footprint = dict(
        info = 'RSS (memory) expert.',
        attr = dict(
            kind = dict(
                values = ['rss',]
            ),
            ntasks_per_node = dict(
                info = "Number of MPI tasks per node. If not present, misses some statistics.",
                type = int,
                optional = True,
                default = None,
            ),
        )
    )

    side_expert = True

    _re_file1 = re.compile(r'stdeo\.(?P<n>\d+)')
    _re_file2 = re.compile(r'listing\..+\.stdeo\.(?P<n>\d+)')
    _re_rss = re.compile(r'.*RSS=(\d+)k$')

    def _parse(self):
        """Actual parsing."""
        self._find_stdeos()
        self.tasks_RSS = []
        for f in self.stdeos:
            self.tasks_RSS.append(self._get_RSS(f))
        if self.ntasks_per_node:
            self._RSS_per_node()

    def summary(self):
        """Return a summary as a dict."""
        summary = {'RSSmax':self.pprint_RSS(self.RSSmax),
                   'RSStotal':self.pprint_RSS(self.RSStotal),
                   'imbalance':self.imbalance,
                   'MPI tasks':self.ntasks}
        if self.ntasks_per_node:
            summary['NodeRSSmax'] = self.pprint_RSS(self.NodeRSSmax)
            summary['Tasks per node'] = self.ntasks_per_node
        return summary

    @classmethod
    def compare_2summaries(cls, test, ref):
        """
        Compare to a reference summary: absolute and relative difference
        in RSSmax and RSStotal, and evolution of imbalance.
        """
        def str2float(mem):
            return float(mem.strip('Gb').strip('%'))
        RSSmax_diff = str2float(test['RSSmax']) - str2float(ref['RSSmax'])
        RSSmax_reldiff = RSSmax_diff / str2float(ref['RSSmax'])
        RSStotal_diff = str2float(test['RSStotal']) - str2float(ref['RSStotal'])
        RSStotal_reldiff = RSStotal_diff / str2float(ref['RSStotal'])
        imbalance_diff = str2float(test['imbalance']) - str2float(ref['imbalance'])
        return {'Absolute RSSmax diff':cls.pprint_RSS(RSSmax_diff, sign=True),
                'Relative RSSmax diff':ppp(RSSmax_reldiff),
                'Absolute RSStotal diff':cls.pprint_RSS(RSStotal_diff, sign=True),
                'Relative RSStotal diff':ppp(RSStotal_reldiff),
                'Imbalance evolution':ppp(imbalance_diff / 100),  # already expressed as a percentage
                'mainMetrics':'Relative RSStotal diff'}

    def _compare(self, references):
        """
        Compare to a reference summary: absolute and relative difference
        in Elapse time.
        """
        return self._compare_summaries(references)

    @property
    def ntasks(self):
        return len(self.stdeos)

    @property
    def RSSmax(self):
        """Maximum RSS among tasks."""
        return max(self.tasks_RSS)

    @property
    def NodeRSSmax(self):
        """Total RSS of the node which has the maximum RSS."""
        if self.ntasks_per_node:
            return self.NodesRSS.max()
        else:
            return None

    @property
    def RSStotal(self):
        """Total RSS over all nodes and tasks."""
        return sum(self.tasks_RSS)

    @property
    def imbalance(self):
        """
        imbalance = 0.0% : all tasks have the same consumption
        imbalance = 100% : very unbalanced consumption among tasks
        """
        imbalance = (max(self.tasks_RSS) - min(self.tasks_RSS)) / max(self.tasks_RSS) * 100
        return '{:.1f}%'.format(imbalance)

    @classmethod
    def pprint_RSS(cls, rss_in_k, sign=False):
        """Return a formatted str for a RSS."""
        if rss_in_k is not None:
            if sign:
                return '{:+.1f}Gb'.format(float(rss_in_k) / 1024. / 1024.)
            else:
                return '{:.1f}Gb'.format(float(rss_in_k) / 1024. / 1024.)

    def pprint_NodesRSS(self):
        """Return a formatted str for NodesRSS."""
        line = ' | '.join([self.pprint_RSS(rss) for rss in self.NodesRSS])
        return line

    def _find_stdeos(self):
        """Look for stdeo files in directory."""
        workdir = os.getcwd()
        taskfiles = os.listdir(workdir)
        self.stdeos = []
        for f in taskfiles:
            match = self._re_file1.match(f)
            if not match:
                match = self._re_file2.match(f)
            if match:
                self.stdeos.append((match.group('n'), f))
        self.stdeos  = [f[1] for f in sorted(self.stdeos)]
        if len(self.stdeos) == 0:
            raise IOError('No stdeo.? files found.')

    def _get_RSS(self, filename):
        """Get RSS of the task, in stdeo file."""
        with open(filename, 'r') as fh:
            for fhline in fh:
                m_rss = self._re_rss.match(fhline)
                if m_rss:
                    return int(m_rss.group(1))

    def _RSS_per_node(self):
        """Compute total RSS per node."""
        self.NodesRSS = np.empty((int(self.ntasks / self.ntasks_per_node),),
                                 dtype=np.float64)
        for i in range(0, self.ntasks, self.ntasks_per_node):
            rss_node = np.array([self.tasks_RSS[n]
                                 for n in range(i, i + self.ntasks_per_node)],
                                dtype=np.int64)
            self.NodesRSS[i // self.ntasks_per_node] = rss_node.sum()


class ParallelBatorProfile(OutputExpert):
    """
    Designed to parse and compare Parallel Bator synthesis
    (parallel_exec_synthesis.json).
    """

    _footprint = dict(
        info = 'Analyses parallel_exec_synthesis.json produced by Bator.',
        attr = dict(
            kind = dict(
                values = ['bator_profile',]
            ),
            synthesis = dict(
                info = "File name to process.",
                optional = True,
                default = 'parallel_exec_synthesis.json'
            ),
            graphics = dict(
                info = "Plot relative differences",
                optional = True,
                default = False,
                type = bool
            )
        )
    )

    side_expert = True

    def _parse(self):
        """Actual parsing."""
        with open(self.synthesis, 'r') as f:
            self.dict_obs_prof = json.load(f)

    def summary(self):
        """Return a summary as a dict."""
        summary = {'Elapse time per obstype':{obstype:self.dict_obs_prof[obstype]['time_real']
                                              for obstype in self.dict_obs_prof.keys()},
                   'Memory per obstype':{obstype:self.dict_obs_prof[obstype]['mem_real']
                                         for obstype in self.dict_obs_prof.keys()},
                   'Total elapse time':sum([self.dict_obs_prof[obstype]['time_real']
                                            for obstype in self.dict_obs_prof.keys()]),
                   'Total memory':sum([self.dict_obs_prof[obstype]['mem_real']
                                       for obstype in self.dict_obs_prof.keys()])}
        return summary

    @classmethod
    def compare_2summaries(cls, test, ref, graphics=False):
        """
        Compare to a reference summary: absolute and relative difference
        in RSSmax and RSStotal, and evolution of imbalance.
        """
        elapsediff = {o:test['Elapse time per obstype'][o] -
                        ref['Elapse time per obstype'][o]
                      for o in ref['Elapse time per obstype'].keys()}
        relelapsediff = {o:elapsediff[o] / ref['Elapse time per obstype'][o]
                         for o in ref['Elapse time per obstype'].keys()}
        memdiff = {o:test['Memory per obstype'][o] -
                     ref['Memory per obstype'][o]
                   for o in ref['Memory per obstype'].keys()}
        relmemdiff = {o:memdiff[o] / ref['Memory per obstype'][o]
                      for o in ref['Memory per obstype'].keys()}
        total_elapsediff = test['Total elapse time'] - ref['Total elapse time']
        total_memdiff = test['Total memory'] - ref['Total memory']
        comp = {'Absolute diff in elapse time per obstype':elapsediff,
                'Absolute diff in memory per obstype':memdiff,
                'Relative diff in elapse time per obstype':relelapsediff,
                'Relative diff in memory per obstype':relmemdiff,
                'Max relative diff in elapse time':ppp(max(relelapsediff.values())),
                'Max relative diff in memory':ppp(max(memdiff.values())),
                'Absolute diff in total elapse time':total_elapsediff,
                'Relative diff in total elapse time':ppp(total_elapsediff /
                                                         ref['Total elapse time']),
                'Absolute diff in total memory':total_memdiff,
                'Relative diff in total memory':ppp(total_memdiff /
                                                    ref['Total memory']),
                'mainMetrics':'Max relative diff in elapse time'}
        if graphics:
            svg = io.StringIO()
            fig = plot_bator_profile(comp)
            fig.savefig(svg, format='svg')
            svg.seek(0)
            comp['Relative diff (SVG)'] = svg.read()
        return comp

    def _compare(self, references):
        """
        Compare to a reference summary: absolute and relative difference
        in Elapse time and Memory.
        """
        return self._compare_summaries(references, graphics=self.graphics)


def plot_bator_profile(compdict):
    import matplotlib.pyplot as plt
    obstypes = sorted(compdict['Relative diff in elapse time per obstype'].keys())
    x = np.arange(len(obstypes))
    mem = [compdict['Relative diff in memory per obstype'][o] * 100
           for o in obstypes]
    elapse = [compdict['Relative diff in elapse time per obstype'][o] * 100
              for o in obstypes]
    width = 0.4
    fig, (ax_e, ax_m) = plt.subplots(2, 1, figsize=(10, 8))
    ax_e.bar(x - width / 2, elapse, width,
                label='Elapse Time',
                color='orange')
    ax_e.set_ylabel("Relative diff in elapse time (%)")
    ax_m.bar( x - width / 2, mem, width,
                 label='Memory',
                 color='blue')
    ax_m.set_ylabel("Relative diff in memory (%)")
    for ax in (ax_e, ax_m):
        ax.set_xlim([min(x) - width, max(x) + width])
        ax.set_xticks(x)
        ax.set_xticklabels(obstypes)
        ax.axhline(0, color='k')

    def autolabel(ax, data):
        """Attach a text label above each bar in *rects*, displaying its height."""
        for i in range(len(data)):
            ax.annotate('{:+.2f}'.format(data[i]),
                        xy=(x[i], data[i]),
                        xytext=(0, 2 if data[i] >= 0 else -3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom' if data[i] >= 0 else 'top')
    autolabel(ax_e, elapse)
    autolabel(ax_m, mem)
    return fig
