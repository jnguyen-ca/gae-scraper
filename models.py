#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import ndb

TIP_SELECTION_TEAM_AWAY = '2'
TIP_SELECTION_TEAM_HOME = '1'
TIP_SELECTION_TEAM_DRAW = 'X'

TIP_SELECTION_TOTAL_OVER = 'Over'
TIP_SELECTION_TOTAL_UNDER = 'Under'

TIP_SELECTION_LINE_SEPARATOR = '|'

TIP_HASH_DATETIME_FORMAT = '%d.%m.%Y %H:%M'

class DisplaySession(ndb.Model):
    user = ndb.UserProperty()
    last_login = ndb.DateTimeProperty()
    leagues = ndb.TextProperty()
    
class Tip(ndb.Model):
    """Single ndb object to hold all information regarding a single game tip
    """
    pinnacle_game_no = ndb.StringProperty()
    
    rot_away = ndb.IntegerProperty()
    rot_home = ndb.IntegerProperty()
    
    date = ndb.DateTimeProperty()
    
    game_sport = ndb.StringProperty()
    game_league = ndb.StringProperty()
    
    game_team_away = ndb.StringProperty()
    game_team_home = ndb.StringProperty()
    
    wettpoint_tip_team = ndb.StringProperty()
    wettpoint_tip_total = ndb.StringProperty()
    
    wettpoint_tip_stake = ndb.FloatProperty()
    
    team_lines = ndb.TextProperty()
    
    total_no = ndb.TextProperty()
    total_lines = ndb.TextProperty()
    
    spread_no = ndb.TextProperty()
    spread_lines = ndb.TextProperty()
    
    score_away = ndb.StringProperty()
    score_home = ndb.StringProperty()
    
    elapsed = ndb.BooleanProperty()
    archived = ndb.BooleanProperty()
    
class TipChange(ndb.Model):
    date = ndb.DateTimeProperty()
    
    tip_key = ndb.StringProperty()
    type = ndb.StringProperty()
    changes = ndb.IntegerProperty()
    
    wettpoint_tip_team = ndb.StringProperty()
    wettpoint_tip_total = ndb.StringProperty()
    
    wettpoint_tip_stake = ndb.FloatProperty()
    
    team_lines = ndb.TextProperty()
    
    total_no = ndb.TextProperty()
    total_lines = ndb.TextProperty()
    
    spread_no = ndb.TextProperty()
    spread_lines = ndb.TextProperty()