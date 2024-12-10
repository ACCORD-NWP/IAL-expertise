#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup Experts.
"""
import re

from .util import EXTENDED_FLOAT_RE
from . import TextOutputExpert


class SetupExpert(TextOutputExpert):
    
    _footprint = dict(
        info = 'Read and compare the variables printed during the Setup.',
        attr = dict(
            kind = dict(
                values = ['setup',],
            ),
            output = dict(
                info = "Output listing file name to process.",
                optional = True,
                default = 'NODE.001_01',
            ),
            all_vars_in_summary = dict(
                info = "Get all parsed variables in summary (huge).",
                optional = True,
                default = False,
                type = bool,
            )
        )
    )

    side_expert = True
    active = False

    END_SIGNATURE = "------ END OF SETUPS at level 0 ---------------------------------------"

    KEY = r'\w+(%\w+)?\s*(\((\d*|:)(,\d+|:)?\))?'
    VAL = '(' + EXTENDED_FLOAT_RE + r'|T|F|\*+'+ ')'
    VALS = VAL + r'((\s|,)*' + VAL + ')*'
    REC_KV = re.compile(r'.*(\s|,|^)(?P<key>' + KEY + r')\s*=\s*(?P<val>' + VALS + r')(\s|,|$).*')
    REC_K_EQ_ENDLINE = re.compile(r'.*(\s|,|^)(?P<key>' + KEY + r')\s*=\s*$')
    REC_TABLE_ALONE = re.compile(r'^\s*' + VALS + '$')
    REC_VALS = re.compile(VALS)
    REC_VALS_SPACES = re.compile(VAL + r'(\s*' + VAL + ')*')
    REC_VALS_COMMAS = re.compile(VAL + '(,*' + VAL + ')*')

    def _parse(self):
        listing = self._read_txt_output()
        try:
            end_of_setup = listing.index(self.END_SIGNATURE)
        except Exception as e:
            pass
        else:
            self.parsedOut = listing[:end_of_setup]
            self._variables_parse()

    def _variables_parse(self):
        """Parse listing, looking for 'key = value' schemes."""
        variables = {}
        orphans = []
        for l, line in enumerate(self.parsedOut):
            rightmost = True
            while True:
                kv_match = self.REC_KV.match(line)
                if kv_match:
                    # key = <numerical or boolean value> found:
                    # decode the line backwards recursively
                    key = kv_match.group('key').strip()
                    val = kv_match.group('val').strip()
                    if self.REC_VALS.match(val):
                        val = self._split_tables(val)
                    if rightmost:  # try to find a continued table only if rightmost key/value on this line
                        table = self._table_on_next_lines(l)
                        if table:
                            if isinstance(val, str):
                                val = [val]
                            val.extend(table)
                        rightmost = False  # we just processed the rightmost
                    variables[key] = val
                    # cut the processed part on the right of the line
                    i = line.index(key)
                    line = line[:i]
                k_eq_end_match = self.REC_K_EQ_ENDLINE.match(line)
                if k_eq_end_match:
                    # key = <end of line> case
                    key = k_eq_end_match.group('key')
                    i = line.index(key)
                    line = line[:i]
                    # look for a table of values on the next line(s) 
                    table = self._table_on_next_lines(l)
                    if table:
                        variables[key] = table
                    else:
                        # no table next line: orphan key with no value
                        orphans.append(key)
                    rightmost = False  # we just processed the rightmost
                if k_eq_end_match is kv_match is None:  # Nothing to do on this line
                    break
        self.variables = variables
        self.orphans = orphans
        self.active = True

    @classmethod
    def _split_tables(cls, string):
        """Split a table of values in a string into a list."""
        string = string.strip()
        if cls.REC_VALS_SPACES.match(string):
            table = [s.strip() for s in string.split() if s != '']
        elif cls.REC_VALS_COMMAS.match(string):
            table = [s.strip() for s in string.split(',') if s != '']
        return table

    def _table_on_next_lines(self, l):
        """
        Is there a table of values on line(s) right after line *l*,
        and if so, parse it.
        """
        table = []
        k = 1
        t = True
        while t:
            t = self.REC_TABLE_ALONE.match(self.parsedOut[l+k])
            if t:  # yes, there are numbers
                try:
                    table.extend(self._split_tables(self.parsedOut[l+k]))
                except:
                    break
                else:
                    k += 1  # go on to the next line
        return table

    def summary(self):
        if self.active:
            summary = {'Orphan variables (not able to get values)':self.orphans,
                       'Number of parsed Variables':len(self.variables)}
            if self.all_vars_in_summary:
                summary['Variables'] = self.variables
        else:
            summary = {'Deactivated at runtime':'Regular Setups pattern did not match'}
        return summary
    
    def _compare(self, references):
        listings = [r for r in references if r.resource.kind == 'plisting']
        if len(listings) > 0:  # in priority, because summary may not contain all norms
            return self._compare_listings(references)
        else:
            raise NotImplementedError("Comparison need a reference output listing.")
            
    def _compare_listings(self, references):
        ref_listing = self.filter_one_resource(references, rkind='plisting')
        ref_setup_expert = SetupExpert(kind=self.kind,
                                       output=ref_listing.container.localpath())
        ref_setup_expert.parse()
        return self._comp(ref_setup_expert)
        
    
    def _comp(self, other):
        if other.active:
            if self.active:
                new_vars = {}
                lost_vars = {}
                modified_vars = {}
                for k in self.variables.keys():
                    if k not in other.variables:
                        new_vars[k] = self.variables[k]
                    elif self.variables[k] != other.variables[k]:
                        modified_vars[k] = {'ref':other.variables[k],
                                            'test':self.variables[k]}
                for k in other.variables.keys():
                    if k not in self.variables.keys():
                        lost_vars[k] = other.variables[k]
                comp = {'Identical':len(new_vars) + len(lost_vars) + len(modified_vars) == 0,
                        'Number of new variables':len(new_vars),
                        'Number of lost variables':len(lost_vars),
                        'Number of modified variables':len(modified_vars)}
                if len(new_vars) != 0:
                    comp['New variables'] = new_vars
                if len(lost_vars) != 0:
                    comp['Lost variables'] = lost_vars
                if len(modified_vars) != 0:
                    comp['Modified variables'] = modified_vars
            else:
                comp = {'No setup available in test':self.summary()['Deactivated at runtime']}
        else:
            comp = other.summary()
        return comp
