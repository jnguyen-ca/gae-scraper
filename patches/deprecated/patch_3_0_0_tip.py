#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('libs/GoogleAppEngineMapReduce-1.9.5.0')

from google.appengine.ext import ndb
from mapreduce import operation

from models import TipChange

import re

def patch_3_0_0_tip(tip_instance):
    if tip_instance.wettpoint_tip_team == tip_instance.game_team_home:
        tip_instance.wettpoint_tip_team = '1'
        yield operation.db.Put(tip_instance)
        yield operation.counters.Increment('Tip Home')
    elif tip_instance.wettpoint_tip_team == tip_instance.game_team_away:
        tip_instance.wettpoint_tip_team = '2'
        yield operation.db.Put(tip_instance)
        yield operation.counters.Increment('Tip Away')
        
    query = TipChange.gql('WHERE tip_key = :1', str(tip_instance.key.to_old_key()))
    if query.count() != 0:
        yield operation.counters.Increment('Tip Change')
        
        doubleheader_search = re.search('^G\d+\s+(.+)', tip_instance.game_team_away)
        if doubleheader_search:
            tip_game_team_away = doubleheader_search.group(1).strip()
            tip_game_team_home = re.search('^G\d+\s+(.+)', tip_instance.game_team_home).group(1).strip()
        else:
            tip_game_team_away = tip_instance.game_team_away
            tip_game_team_home = tip_instance.game_team_home
        
        tipchange_instance = query.get()
        
        old_key = tipchange_instance.tip_key
        if tip_instance.key.urlsafe() != tipchange_instance.tip_key:
            tipchange_instance.tip_key = tip_instance.key.urlsafe()
        
        if tipchange_instance.wettpoint_tip_team == tip_game_team_home:
            tipchange_instance.wettpoint_tip_team = '1'
            tipchange_instance.put()
            yield operation.counters.Increment('Tip Change Home')
        elif tipchange_instance.wettpoint_tip_team == tip_game_team_away:
            tipchange_instance.wettpoint_tip_team = '2'
            tipchange_instance.put()
            yield operation.counters.Increment('Tip Change Away')
        elif old_key != tipchange_instance.tip_key:
            tipchange_instance.put()
            yield operation.counters.Increment('Tip Change Key Update')