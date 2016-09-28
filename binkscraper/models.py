#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import ndb
from datetime import datetime

APPVAR_KEY_SCOREBOARD = 'scoreboard'
APPVAR_KEY_WETTPOINT = 'wettpoint'
APPVAR_KEY_PINNACLE = 'pinnacle'

TIP_SELECTION_TEAM_AWAY = '2'
TIP_SELECTION_TEAM_HOME = '1'
TIP_SELECTION_TEAM_DRAW = 'X'

TIP_SELECTION_TOTAL_OVER = 'Over'
TIP_SELECTION_TOTAL_UNDER = 'Under'

TIP_SELECTION_LINE_SEPARATOR = '|'

TIP_STAKE_TEAM_TOTAL_DISAGREE = 1
TIP_STAKE_TEAM_TOTAL_NONE = 2
TIP_STAKE_TEAM_DISAGREE_TOTAL_NONE = 3
TIP_STAKE_TOTAL_DISAGREE_TEAM_NONE = 4
TIP_STAKE_TEAM_DISAGREE = 5
TIP_STAKE_TOTAL_DISAGREE = 6
TIP_STAKE_TEAM_NONE = 7
TIP_STAKE_TOTAL_NONE = 8

TIP_HASH_DATETIME_FORMAT = '%d.%m.%Y %H:%M'

TIPLINE_KEY_POINTS = 'points'
TIPLINE_KEY_ODDS = 'odds'

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
    
    score_away = ndb.StringProperty()
    score_home = ndb.StringProperty()
    
    elapsed = ndb.BooleanProperty()
    archived = ndb.BooleanProperty()
    
class TipLine(ndb.Model):
    '''Line information for a Tip stored as json properties.
    Each TipLine should have a single parent Tip (one-to-one relation, not enforced)
    
    It should be noted that not all Tips will have a TipLine. If an event has no odds
    '''
    spread_away = ndb.JsonProperty(indexed=False,compressed=True)
    spread_home = ndb.JsonProperty(indexed=False,compressed=True)
    
    money_away = ndb.JsonProperty(indexed=False,compressed=True)
    money_home = ndb.JsonProperty(indexed=False,compressed=True)
    money_draw = ndb.JsonProperty(indexed=False,compressed=True)
    
    total_over = ndb.JsonProperty(indexed=False,compressed=True)
    total_under = ndb.JsonProperty(indexed=False,compressed=True)

#     consensus_spread_home = ndb.JsonProperty(indexed=False,compressed=True)
#     consensus_money_home = ndb.JsonProperty(indexed=False,compressed=True)
#     consensus_total_under = ndb.JsonProperty(indexed=False,compressed=True)

    @staticmethod
    def get_line_date(line_entries, bookie=APPVAR_KEY_PINNACLE, desired_date='latest'):
        if line_entries is None or len(line_entries) < 1:
            return None, None
        
        if bookie in line_entries:
            line_dates = line_entries[bookie]
        else:
            return None, None
        
        if isinstance(desired_date, datetime):
            # if a date was specified then find the line closest to that date
            specified_date = desired_date.replace(tzinfo=None)
            
            date_string = min(line_dates, key=lambda x: abs(specified_date - datetime.strptime(x, TIP_HASH_DATETIME_FORMAT)))
        elif desired_date == 'earliest':
            sorted_line_dates = sorted(line_dates, key=lambda x: datetime.strptime(x, TIP_HASH_DATETIME_FORMAT))
            date_string = sorted_line_dates[0]
        elif desired_date == 'latest':
            sorted_line_dates = sorted(line_dates, key=lambda x: datetime.strptime(x, TIP_HASH_DATETIME_FORMAT))
            date_string = sorted_line_dates[-1]
        else:
            raise ValueError('Invalid desired date given: '+str(desired_date))
            
        line_date = datetime.strptime(date_string, TIP_HASH_DATETIME_FORMAT)
        line = line_dates[date_string]
        
        return line, line_date

    @classmethod
    def from_tip_instance_key(cls, tip_instance_key):
        if not isinstance(tip_instance_key, ndb.Key):
            tip_instance_key = ndb.Key(urlsafe=tip_instance_key)
        return cls.gql('WHERE ANCESTOR IS :1', tip_instance_key).get()

    def _modify_property_value(self, tipline_property, bookie_key, date_key, entry_value):
        '''General function for inserting an entry to any of TipLine's propertys
        '''
        if not entry_value:
            return tipline_property
        if not isinstance(bookie_key, basestring):
            raise ValueError('Entry bookie_key is not a string')
        if not isinstance(date_key, basestring):
            raise ValueError('Entry date_key is not a string')
        
        if not isinstance(entry_value, dict) and not isinstance(entry_value, basestring):
            raise ValueError('Entry value is neither a dict or a string')
        
        if not tipline_property:
            tipline_property = {}
            
        if bookie_key not in tipline_property:
            tipline_property[bookie_key] = {}
        
        tipline_property[bookie_key][date_key] = entry_value
        return tipline_property

    def _create_points_odds_entry(self, points, odds):
        return {TIPLINE_KEY_POINTS : points, TIPLINE_KEY_ODDS : odds}
    
    def insert_property_entry(self, entry_property=None, bookie_key=None, line_date=None, points_values=None, odds_values=None):
        tipline_property_value = getattr(self, entry_property)
        
        entry_value = odds_values
        if points_values is not None:
            entry_value = self._create_points_odds_entry(points_values, odds_values)
        
        property_value = self._modify_property_value(tipline_property_value, bookie_key, line_date, entry_value)
        if property_value:
            setattr(self, entry_property, property_value)
    
    def get_money_entries(self, team_selection):
        if team_selection is None:
            team_selection = self.get_opening_favourite()
            if team_selection is None:
                return None
            
        if team_selection == TIP_SELECTION_TEAM_HOME:
            return self.money_home
        elif team_selection == TIP_SELECTION_TEAM_AWAY:
            return self.money_away
        elif team_selection == TIP_SELECTION_TEAM_DRAW:
            return self.money_draw
        raise ValueError('Invalid tip team selection given.')
    
    def get_spread_entries(self, team_selection):
        if team_selection is None:
            team_selection = self.get_opening_favourite()
            if team_selection is None:
                return None
        
        if team_selection == TIP_SELECTION_TEAM_HOME:
            return self.spread_home
        elif team_selection == TIP_SELECTION_TEAM_AWAY:
            return self.spread_away
        raise ValueError('Invalid tip team selection given.')
    
    def get_total_entries(self, total_selection):
        if total_selection is None:
            total_selection = TIP_SELECTION_TOTAL_UNDER
        
        if total_selection == TIP_SELECTION_TOTAL_OVER:
            return self.total_over
        elif total_selection == TIP_SELECTION_TOTAL_UNDER:
            return self.total_under
        raise ValueError('Invalid tip total selection given.')
    
    def get_opening_favourite(self, bookie=APPVAR_KEY_PINNACLE, allow_draw=False):
        if allow_draw is True:
            earliest_opening_draw = TipLine.get_line_date(self.money_draw, bookie=bookie, desired_date='earliest')[0]
            if earliest_opening_draw is None:
                allow_draw = False
        
        # check the spread first since it's the easiest way to determine a favourite
        # unless draw is allowed then can't use spread
        earliest_opening_spread = TipLine.get_line_date(self.spread_home, bookie=bookie, desired_date='earliest')[0]
        if earliest_opening_spread is not None and allow_draw is False:
            if earliest_opening_spread < 0:
                return TIP_SELECTION_TEAM_HOME
            elif earliest_opening_spread > 0:
                return TIP_SELECTION_TEAM_AWAY
        
        earliest_opening_money_home = TipLine.get_line_date(self.money_home, bookie=bookie, desired_date='earliest')[0]
        earliest_opening_money_away = TipLine.get_line_date(self.money_away, bookie=bookie, desired_date='earliest')[0]
        if earliest_opening_money_home is not None and earliest_opening_money_away is not None:
            if allow_draw is False:
                # default to home team, so if they're equal return home selection
                if earliest_opening_money_home <= earliest_opening_money_away:
                    return TIP_SELECTION_TEAM_HOME
                elif earliest_opening_money_home > earliest_opening_money_away:
                    return TIP_SELECTION_TEAM_AWAY
                raise Exception("Shouldn't be able to get here")
            else:
                if earliest_opening_money_home <= earliest_opening_money_away:
                    if earliest_opening_money_home <= earliest_opening_draw:
                        return TIP_SELECTION_TEAM_HOME
                    return TIP_SELECTION_TEAM_DRAW
                elif earliest_opening_money_home > earliest_opening_money_away:
                    if earliest_opening_money_away < earliest_opening_draw:
                        return TIP_SELECTION_TEAM_AWAY
                    return TIP_SELECTION_TEAM_DRAW
                raise Exception("Shouldn't be able to get here")
        
        # no lines for this game has been gathered
        return None

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
    
class ApplicationVariables(ndb.Model):
    value = ndb.TextProperty()