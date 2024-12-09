#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Task: tools to analyse the outputs of a task and state about its validation.
"""
import json
import sys

from footprints import proxy as fpx
from bronx.fancies import loggers
from bronx.stdtypes import date

from .experts import ExpertError

logger = loggers.getLogger(__name__)


task_status = {'X':{'symbol':'X',
                    'short':'Crashed',
                    'text':'Crashed: the task ended abnormally, with associated exception'},
               'X=R':{'symbol':'X=R',
                      'short':'Crashed as Ref',
                      'text':'Crashed: AS IN REFERENCE, the task ended abnormally'},
               'X:R?':{'symbol':'X:R?',
                      'short':'Crashed : as Ref ?',
                      'text':'Crashed: the task ended abnormally, but REFERENCE might as well ?'},
               'E':{'symbol':'E',
                    'short':'Ended',
                    'text':'Ended: Task ended without crash.'},
               'I...':{'symbol':'(I...)',
                       'short':'(Inputs...)',
                       'text':'Waiting for task : Input step started, unknown status since ' +
                              '(possible reasons: fetch error, dependancy...)'},
               'C...':{'symbol':'(C...)',
                       'short':'(Compute...)',
                       'text':'Waiting for task : Compute step started, unknown status since ' +
                              '(possible reasons: cancellation, timeout...)'},
               'O...':{'symbol':'(O...)',
                       'short':'(Outputs...)',
                       'text':'Waiting for task : Output step started, unknown status since ' +
                              '(possible reasons: resource absence, ...)'},
               'F':{'symbol':'F',
                    'short':'Failed',
                    'text':'Failed: Task ended but the inner auto-test (i.e. the test auto-evaluates its results) has failed.'},
               }


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
        if isinstance(out, str):
            close = True
            out = open(out, 'w')
        else:
            close = False
        json.dump(self, out, indent=4, sort_keys=True)
        if close:
            out.close()

    def _load(self, filein):
        if isinstance(filein, str):
            close = True
            filein = open(filein, 'r')
        else:
            close = False
        asdict = json.load(filein)
        if close:
            filein.close()
        self.clear()
        self.update(asdict)


class ExpertBoard(object):

    def __init__(self, experts, lead_expert=None):
        """
        Arguments:

        :param experts: list of dicts, whose kwargs are used to get
            experts and parse output
        :param lead_expert: indicate whose Expert is to be selected from the experts panel for validation
        """
        if isinstance(lead_expert, dict):
            lead_expert = lead_expert.get('kind', None)
        self.lead_expert = lead_expert
        self.experts = list()
        for expert in experts:
            self.add_expert(expert)
        self.task_summary = TaskSummary()  # to contain summaries reported by each expert
        self.consistency = TaskSummary()  # contains consistency comparisons outputs
        self.continuity = TaskSummary()  # contains continuity comparisons outputs
        # ExpertBoard AlgoComponent is ran only if the task did not crash
        self.task_summary['Status'] = task_status['E']

    def process(self, consistency=None, continuity=None):
        """Process experts. Cf. :meth:`compare` for arguments."""
        logger.info("Expertise: parsing start.")
        self.parse()
        logger.info("Expertise: parsing end.")
        if consistency or continuity:  # at least one provided and not empty
            logger.info("Expertise: comparison start.")
            self.compare(consistency, continuity)
            logger.info("Expertise: comparison end.")
        else:
            logger.info('Expertise: no reference resource available => no comparison processed.')
            self._notify_no_ref_resource('consistency')
            self._notify_no_ref_resource('continuity')
        self.task_summary['Updated'] = date.utcnow().isoformat().split('.')[0]
        self.dump()
        logger.info("Expertise: dumped to file.")

    def add_expert(self, expert_kwargs):
        """Instanciate expert and register it to ExpertBoard."""
        expert = fpx.outputexpert(**expert_kwargs)
        if expert is not None:
            self.experts.append(expert)
        else:
            message = "No Expert was found for attributes: " + str(expert_kwargs)
            fatal = expert_kwargs.get('fatal_exceptions', True)
            if fatal:
                raise ExpertError(message)
            else:
                logger.warning(message)

    def parse(self):
        """
        Ask experts to parse whatever information they are supposed to,
        collecting information into self.task_summary.
        """
        for e in self.experts:
            logger.info("Start parsing with expert: {}...".format(type(e)))
            self.task_summary[e.kind] = e.parse()
            logger.info("... complete.")
            if self.task_summary[e.kind].get('Auto-test', None) == 'Failed':
                self.task_summary['Status'] = task_status['F']
        self.task_summary.dump('task_summary.json')

    def compare(self, consistency=None, continuity=None):
        """
        Ask experts to compare to references, collecting comparison
        information into self.against_summary.

        :param consistency: the list of consistency reference resource,
            as a list of dicts: {'rh': Vortex resource handler, 'ref_is': ...}
        :param continuity: the list of continuity reference resource,
            as a list of dicts: {'rh': Vortex resource handler, 'ref_is': ...}
        """
        if consistency:
            ref_task = [r['ref_is']['task'] for r in consistency]
            if len(set(ref_task)) > 1:
                raise ExpertError("Consistency reference resources must all come from the same 'task'.")
            else:
                self.consistency['referenceTask'] = ref_task[0]
        for e in self.experts:
            logger.info("Start comparison with expert: {}...".format(type(e)))
            if consistency:
                logger.info('(consistency)')
                self.consistency[e.kind] = e.compare([r['rh'] for r in consistency])
            if continuity:
                logger.info('(continuity)')
                self.continuity[e.kind] = e.compare([r['rh'] for r in continuity])
            logger.info("... complete.")

        for comp_summary in ('consistency', 'continuity'):
            self._status(comp_summary)

    def _status(self, which_summary):
        """State about the comparison to reference."""
        comp_summary = getattr(self, which_summary)
        if len(comp_summary) > 0:
            status_order = ['-', '0', '?', 'OK', 'KO', '!', '+']
            # by default, unknown status (e.g. if no expert has a Validated key)
            comp_summary['comparisonStatus'] = {'symbol':'-',
                                                'short':'- No expert -',
                                                'text':'No expert available'}
            for e in self.experts:
                if e.kind in comp_summary and comp_summary[e.kind].get('symbol') == '+':
                    # reference was crashed: empty comp_summary and keep that message
                    status = comp_summary[e.kind]
                    for e in self.experts:
                        comp_summary.pop(e.kind, None)
                elif e.side_expert:
                    continue  # these are not used to state about Validation/comparisonStatus
                elif e.kind in comp_summary and 'Validated' in comp_summary[e.kind]:
                    # if a 'Validated' key is found in an expert, interpret it and end research
                    if comp_summary[e.kind]['Validated'] is True:  # FIXME: actual comparison to True or False, because could contain something else ? (None?)
                        status = {'symbol':'OK',
                                  'short':'OK',
                                  'text':'Success: "{}"'.format(comp_summary[e.kind]['Validated means'])}
                    elif comp_summary[e.kind]['Validated'] is False:
                        status = {'symbol':'KO',
                                  'short':'KO',
                                  'text':'Fail: "{}" is False'.format(comp_summary[e.kind].get('Validated means', '(?)'))}
                elif e.kind in comp_summary and comp_summary[e.kind].get('Comparison') == 'Failed':
                    # else, if we found at least one comparison failure, raise it as status
                    status = {'symbol':'!',
                              'short':'! Comp Issue !',
                              'text':'To be checked: at least one technical problem occurred in comparison ({})'.format(e.kind)}
                elif e.kind in comp_summary and comp_summary[e.kind].get('comparisonStatus', {}).get('symbol') == '0':
                    status = comp_summary[e.kind].get('comparisonStatus')
                else:
                    # expert present but no Validated key available
                    status = {'symbol':'?',
                              'short':'? Unknown ?',
                              'text':'To be checked: expert has not stated about Validation'}
                # update status
                if status_order.index(status['symbol']) >= status_order.index(comp_summary['comparisonStatus']['symbol']):
                    # several OK or KO: gather
                    if status['symbol'] == comp_summary['comparisonStatus']['symbol'] and status['symbol'] in ('OK', 'KO'):
                        comp_summary['comparisonStatus']['text'] += ' | ' + status['text']
                    else:
                        comp_summary['comparisonStatus'] = status
            # identify leadExpert
            if self.lead_expert is None:
                potential_experts = [e.kind for e in self.experts if not e.side_expert]
                if len(potential_experts) == 1:
                    self.lead_expert = potential_experts[0]
            if self.lead_expert is not None:
                comp_summary['leadExpert'] = self.lead_expert
        else:
            # means no resources were available for this comparison summary
            self._notify_no_ref_resource(which_summary)

    def _notify_no_ref_resource(self, which_summary):
        """
        Write in comparison summary that no reference resource was provided to
        perform a comparison.
        """
        comp_summary = getattr(self, which_summary)
        comp_summary['comparisonStatus'] = {'symbol':'0',
                                            'short':'- No ref -',
                                            'text':'No reference to be compared to'}

    def remember_context(self, context_info):
        """Save info from context into task summary."""
        self.task_summary['Context'] = context_info

    def remember_listings(self, promises, continuity):  # TODO: consistency too !
        """Write paths to listings in cache/archive into summaries."""
        promises = [p.rh for p in promises if p.rh.resource.kind in ('listing', 'plisting')]
        if len(promises) > 1:
            raise ExpertError("More than one promised listing.")
        elif len(promises) == 1:
            test_listing = promises[0].locate().split(';')
        else:
            test_listing = []
        ref_listing = []
        if continuity:
            ref_listing = [r['rh'] for r in continuity
                           if r['rh'].resource.kind in ('listing', 'plisting')]
            if len(ref_listing) > 1:
                raise ExpertError("More than one continuity reference listing.")
            elif len(ref_listing) == 1:
                ref_listing = ref_listing[0].locate().split(';')
        # save
        if test_listing:
            self.task_summary['Listing'] = {'Task listing uri(s)':test_listing}
        if ref_listing:
            self.continuity['Listings'] = {'Compare listings at uri(s)':{'test':test_listing,
                                                                         'ref':ref_listing}}

    def dump(self):
        """Dump output."""
        self.task_summary.dump('task_summary.json')  # again, in case there has been some delayed parsing
        self.consistency.dump('task_consistency.json')
        self.continuity.dump('task_continuity.json')
