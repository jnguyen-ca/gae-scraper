#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.insert(0, 'libs')

from mapreduce import operation

from patch_3_1_0_doubleheader_tip import patch_3_1_0_doubleheader_tip

def run_patch(tip_instance):
    if tip_instance.game_league == 'MLB Regular Season':
        tip_instance.game_league = 'MLB'
        yield operation.db.Put(tip_instance)
        yield operation.counters.Increment('Updated')
        
    result = patch_3_1_0_doubleheader_tip(tip_instance)
    
    yield operation.counters.Increment(tip_instance.game_sport)
    
    size_team = size_total_no = size_total = size_spread_no = size_spread = 0
    
    if tip_instance.team_lines:
        size_team = len(tip_instance.team_lines)
    if tip_instance.total_no:
        size_total_no = len(tip_instance.total_no)
    if tip_instance.total_lines:
        size_total = len(tip_instance.total_lines)
    if tip_instance.spread_no:
        size_spread_no = len(tip_instance.spread_no)
    if tip_instance.spread_lines:
        size_spread = len(tip_instance.spread_lines)
    
    total_size = size_team + size_total_no + size_total + size_spread_no + size_spread
    
    yield operation.counters.Increment(tip_instance.game_sport + ' Text', total_size)
    
    if result:
        yield operation.counters.Increment(result)
    else:
        yield operation.counters.Increment('Pass')
