#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.insert(0, 'libs')

from mapreduce import operation

from models import TipChange

def patch_3_0_0_tip(tip_instance):
    if tip_instance.wettpoint_tip_team == tip_instance.game_team_home:
        tip_instance.wettpoint_tip_team = '1'
        yield operation.db.Put(tip_instance)
        yield operation.counters.Increment('Tip Home')
    elif tip_instance.wettpoint_tip_team == tip_instance.game_team_away:
        tip_instance.wettpoint_tip_team = '2'
        yield operation.db.Put(tip_instance)
        yield operation.counters.Increment('Tip Away')
        
    query = TipChange.gql('WHERE tip_key = :1', str(tip_instance.key))
    if query.count() != 0:
        tipchange_instance = query.get()
        if tipchange_instance.wettpoint_tip_team == tip_instance.game_team_home:
            tipchange_instance.wettpoint_tip_team = '1'
            tipchange_instance.put()
            yield operation.counters.Increment('Tip Change')
        elif tipchange_instance.wettpoint_tip_team == tip_instance.game_team_away:
            tipchange_instance.wettpoint_tip_team = '2'
            tipchange_instance.put()
            yield operation.counters.Increment('Tip Change')