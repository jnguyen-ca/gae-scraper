#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import webapp

class SuperAdmin(webapp.RequestHandler):
    def get(self):
        print_simple_mlb_list(self.response.out)
#         patcher = RunPatch()
#         patcher.run_patch()

import sys
sys.path.append('patches')

from patches import patch_4_0_1_spread_fix

class RunPatch(object):
    def __init__(self):
        pass
        
    def run_patch(self):
        patch_4_0_1_spread_fix.patch()

import models
import tipanalysis
import datetime
import constants
sys.path.append('libs/'+constants.LIB_DIR_PYTZ)
import pytz
def print_simple_mlb_list(output):
    query = models.Tip.gql("WHERE date >= :1 AND game_league = 'MLB' AND archived = True ORDER BY date ASC", 
                           datetime.datetime.strptime('04-01-2015', '%m-%d-%Y'))
    
    html = ''
    for tip_instance in query:
        wettpoint_tip = int(tip_instance.wettpoint_tip_stake)
        if wettpoint_tip == 0:
            wettpoint_tip = 'ZERO'
        else:
            wettpoint_tip = str(wettpoint_tip)
            
        if tip_instance.wettpoint_tip_team == models.TIP_SELECTION_TEAM_AWAY:
            result = tipanalysis.calculate_event_score_result(tip_instance.game_league, tip_instance.score_away, tip_instance.score_home)
        else:
            result = tipanalysis.calculate_event_score_result(tip_instance.game_league, tip_instance.score_home, tip_instance.score_away)
        
        line = tipanalysis.get_line(tip_instance.team_lines)[0]
        
        html += '''
        <div>
            %s %s %s %s %s %s %s
        </div>
        ''' % (
               tip_instance.date.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(constants.TIMEZONE_LOCAL)).strftime('%m/%d/%y'),
               wettpoint_tip,
               line,
               result,
               tip_instance.game_team_away,
               tip_instance.game_team_home,
               tip_instance.wettpoint_tip_team,
               )
        
    output.write(html)