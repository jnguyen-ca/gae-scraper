#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('utils')

import json
from datetime import datetime, timedelta
from utils import appvar_util, sys_util

import models
import constants

BET_RESULT_WIN = 'Y'
BET_RESULT_LOSS = 'N'
BET_RESULT_NONE = 'R'
BET_RESULT_PUSH = 'PU'
BET_RESULT_SPLIT = 'H'
BET_RESULT_HALF_WIN = 'HW'
BET_RESULT_HALF_LOSS = 'HL'

def strip_score(league_key, score_string):
    if isinstance(score_string, basestring):
        if '(' in score_string:
            if league_key in appvar_util.get_leagues_ot_included_appvar():
                return score_string.split('(', 1)[0].strip()
            else:
                return score_string.split('(', 1)[1].rstrip(')')
    
    return score_string

def calculate_event_score_result(league_key, backing_score, opposition_score, draw=BET_RESULT_PUSH, spread_modifier=None):
    if backing_score is None or opposition_score is None:
        return BET_RESULT_NONE
    
    backing_score = float(strip_score(league_key, backing_score))
    opposition_score = float(strip_score(league_key, opposition_score))
    
    if spread_modifier is not None:
        # spread
        spread_modifier = float(spread_modifier)
        
        if spread_modifier % 0.5 == 0:
            if opposition_score < (backing_score + spread_modifier):
                return BET_RESULT_WIN
            elif opposition_score > (backing_score + spread_modifier):
                return BET_RESULT_LOSS
            else:
                return BET_RESULT_PUSH
        else:
            # asian handicap modifier
            backing_score_low_modifier = backing_score + spread_modifier - 0.25
            backing_score_high_modifier = backing_score + spread_modifier + 0.25
            
            if backing_score_low_modifier > opposition_score:
                return BET_RESULT_WIN
            elif backing_score_high_modifier < opposition_score:
                return BET_RESULT_LOSS
            elif backing_score_low_modifier == opposition_score:
                return BET_RESULT_HALF_WIN
            elif backing_score_high_modifier == opposition_score:
                return BET_RESULT_HALF_LOSS
    else:
        # money line or total
        if draw == BET_RESULT_WIN:
            # betting for a draw, every other result loses
            if backing_score == opposition_score:
                return BET_RESULT_WIN
            else:
                return BET_RESULT_LOSS
        else:
            # backing one team over the other
            if backing_score > opposition_score:
                return BET_RESULT_WIN
            elif backing_score < opposition_score:
                return BET_RESULT_LOSS
            else:
                # draw may result in a loss (e.g. 1X2 money line) or a push (e.g. totals)
                if draw == BET_RESULT_LOSS:
                    return BET_RESULT_LOSS
                else:
                    return BET_RESULT_PUSH
    
def convert_to_decimal_odds(moneyline):
    moneyline = float(moneyline)
    
    # already decimal (probably)
    if moneyline > 1.0 and moneyline < 10.0:
        return moneyline
    # favourite
    elif moneyline < 0:
        return 100.0 / (moneyline * -1) + 1.0
    # underdog
    else:
        return moneyline / 100.0 + 1.0
    
def calculate_event_unit_change(result, moneyline, **kwargs):
    decimal_line = convert_to_decimal_odds(moneyline)
    fractional_line = decimal_line - 1
    
    if 'risk' in kwargs:
        bet_amount = float(kwargs['risk'])
    elif 'win' in kwargs:
        bet_amount = float(kwargs['win']) / fractional_line
    else:
        bet_amount = 1.0
            
    if result == BET_RESULT_WIN:
        return bet_amount * fractional_line
    elif result == BET_RESULT_LOSS:
        return bet_amount * -1.0
    elif result == 'H':
        return ((bet_amount / 2.0) * fractional_line) - (bet_amount / 2.0)
    
    return None

def get_line(line_dates, **kwargs):
    if line_dates is None:
        return None, None
    elif isinstance(line_dates, basestring):
        line_dates = json.loads(line_dates)
    
    date = line = None
    if 'date' in kwargs and isinstance(kwargs['date'], datetime):
        specified_date = kwargs['date'].replace(tzinfo=None)
        
        closest_date_string = min(line_dates, key=lambda x: abs(specified_date - datetime.strptime(x, models.TIP_HASH_DATETIME_FORMAT)))
        date = datetime.strptime(closest_date_string, models.TIP_HASH_DATETIME_FORMAT)
        line = line_dates[closest_date_string]
    else:
        sorted_line_dates = sorted(line_dates, key=lambda x: datetime.strptime(x, models.TIP_HASH_DATETIME_FORMAT))
        latest_date_string = sorted_line_dates[-1]
        date = datetime.strptime(latest_date_string, models.TIP_HASH_DATETIME_FORMAT)
        line = line_dates[latest_date_string]
        
    return line, date

class TipAnalysis(object):
    '''Analysis of Tips that require querying the datastore
    '''
    datastore_writes = 0
    datastore_reads = 0
    
    def __init__(self):
        pass

    @sys_util.function_timer()
    def calculate_series_wettpoint_tips(self, tip_instance):
        '''For a series of events, wettpoint tips will usually only be applied to the first
        game of the series. Since having the rest of the series being treated as 0 tips is not
        conducive to tip analysis (e.g. there is no way to separate actual 0 tips from tips
        which are not the first of their series) it would be better instead to extend the 
        tips from the first game to the rest of the game in the same series.
        '''
        # if a Tip has it's own wettpoint tips set then we don't want to extends series wettpoint tips
        if tip_instance.wettpoint_tip_stake != 0.0 or tip_instance.wettpoint_tip_total != None:
            return None
        
        # get the previous match ups of the away team
        self.datastore_reads += 1
        sides_match_query = models.Tip.gql('WHERE game_sport = :1 AND game_league = :2 AND '
                               +'game_team_away = :3 AND date < :4 ORDER BY date DESC',
                                 tip_instance.game_sport,
                                 tip_instance.game_league,
                                 tip_instance.game_team_away,
                                 tip_instance.date,
                                 )
        
        self.datastore_reads += 1
        sides_switch_query = models.Tip.gql('WHERE game_sport = :1 AND game_league = :2 AND '
                               +'game_team_home = :3 AND date < :4 ORDER BY date DESC',
                                 tip_instance.game_sport,
                                 tip_instance.game_league,
                                 tip_instance.game_team_away,
                                 tip_instance.date,
                                 )
        
        #TODO: unchecked scenario
        # The away team (A) has a matchup against the home team (B)
        # To find series we query A's matchups and search for non-interrupted matchups against B within 2 days of each other
        # However, if A has matchup against B on day 1, then takes day 2 off while B faces off against C, and then on
        # day 3 A matches up against B again, the matchup on day 1 will be considered the start of the series because
        # we do not check B's matchups and do not see that B faced C on day 2 while A was resting
        sorted_date_series_tips = [tip_instance]
        self._fill_series(sorted_date_series_tips, sides_match_query, sides_switch_query)
        
        # Tip was the first of its series (or there is no series)
        if len(sorted_date_series_tips) < 2:
            return None
        
        # only want to extend the first of the series wettpoint tips if none of the other Tips in the series
        # have wettpoint tips (which would mean the wettpoint tips are being updated throughout the series and
        # a 0.0 wettpoint tip is actually a 0.0 wettpoint tip and not just a blank)
        series_wettpoint_tip_team = str(tip_instance.wettpoint_tip_team)
        series_wettpoint_tip_total = str(tip_instance.wettpoint_tip_total)
        series_wettpoint_tip_stake = str(tip_instance.wettpoint_tip_stake)
        
        first_series_tip = sorted_date_series_tips.pop(0)
        
        series_wettpoint_tip_total += ' ('+str(first_series_tip.wettpoint_tip_total)+')'
        series_wettpoint_tip_stake += ' ('+str(first_series_tip.wettpoint_tip_stake)+')'
        
        # for the wettpoint tip team, want to convert it so that it corresponds to the tip_instance's sides
        # i.e. first_series_tip wettpoint tip team was home team (aka '1') but tip_instance is a split series
        # so now the home team in first_series_tip is the away team then we want to convert it as such (i.e. to '2')
        if first_series_tip.game_team_away == tip_instance.game_team_away:
            series_wettpoint_tip_team += ' ('+str(first_series_tip.wettpoint_tip_team)+')'
        else:
            if first_series_tip.wettpoint_tip_team == models.TIP_SELECTION_TEAM_AWAY:
                series_wettpoint_tip_team += ' ('+models.TIP_SELECTION_TEAM_HOME+')'
            else:
                series_wettpoint_tip_team += ' ('+models.TIP_SELECTION_TEAM_AWAY+')'
        
        for preceding_series_tip in sorted_date_series_tips:
            # series is being updated throughout
            if preceding_series_tip.wettpoint_tip_stake != 0.0 or preceding_series_tip.wettpoint_tip_total != None:
                return None
        
        return series_wettpoint_tip_team, series_wettpoint_tip_total, series_wettpoint_tip_stake
    
    @sys_util.function_timer()
    def _fill_series(self, sorted_date_series, sides_match_query, sides_switch_query, max_day_limit=2):
        earliest_series_tip = sorted_date_series[0]
        current_series_tip = sorted_date_series[-1]
        
        # initialization
        if not isinstance(sides_match_query, dict):
            sides_match_query = {'query' : sides_match_query, 'last_tip' : None, 'offset' : 0}
        if not isinstance(sides_switch_query, dict):
            sides_switch_query = {'query' : sides_switch_query, 'last_tip' : None, 'offset' : 0}
        
        previous_match_tip_instance = previous_switch_tip_instance = None
        
        if sides_match_query['last_tip'] is None and sides_match_query['query'] is not None:
            # either initialization or last tip in series was from match query
            # get the team's last matchup where they were the away team
            self.datastore_reads += 1
            previous_match_tip_instance = sides_match_query['query'].get(offset=sides_match_query['offset'])
            if previous_match_tip_instance is None:
                sides_match_query['query'] = None
            sides_match_query['last_tip'] = previous_match_tip_instance
        elif sides_match_query['last_tip'] is not None:
            # last matchup added to the series was a matchup where team was a home team
            # while the last matchup where the team was the away team occurred before that and is still the same as before
            previous_match_tip_instance = sides_match_query['last_tip']
            
        if sides_switch_query['last_tip'] is None and sides_switch_query['query'] is not None:
            # either initialization or last tip in series was from switch query
            # get the team's last matchup where they were the home team
            self.datastore_reads += 1
            previous_switch_tip_instance = sides_switch_query['query'].get(offset=sides_switch_query['offset'])
            if previous_switch_tip_instance is None:
                sides_switch_query['query'] = None
            sides_switch_query['last_tip'] = previous_switch_tip_instance
        elif sides_switch_query['last_tip'] is not None:
            # last matchup added to the series was a matchup where team was a away team
            # while the last matchup where the team was the home team occurred before that and is still the same as before
            previous_switch_tip_instance = sides_switch_query['last_tip']
        
        # reached the start of team's initialization into the datastore, no games before this (rare occurrence)
        if previous_match_tip_instance is None and previous_switch_tip_instance is None:
            sys_util.add_mail(constants.MAIL_TITLE_GENERIC_WARNING, 
                              'Reached all the way to '+current_series_tip.game_team_away+' initialization while trying to find series!',
                              logging='debug')
            return
        
        if (
            previous_switch_tip_instance is None 
            or (
                previous_match_tip_instance is not None
                and previous_match_tip_instance.date > previous_switch_tip_instance.date
            )
        ):
            # last matchup was where team is away team
            if current_series_tip.game_team_home !=  previous_match_tip_instance.game_team_home:
                # if facing different opponent then series has ended
                return
            
            if (earliest_series_tip.date - timedelta(days = max_day_limit)) > previous_match_tip_instance.date:
                # if matchup occurred over max_day_limit days ago then series has ended
                return
            
            # this matchup is part of the series, continue searching for earliest matchup in series
            sides_match_query['last_tip'] = None
            sides_match_query['offset'] += 1
            sorted_date_series.insert(0, previous_match_tip_instance)
            self._fill_series(sorted_date_series, sides_match_query, sides_switch_query, max_day_limit)
        else:
            # last matchup was where team is home team
            if current_series_tip.game_team_home !=  previous_switch_tip_instance.game_team_away:
                # if facing different opponent then series has ended
                return
                
            if (earliest_series_tip.date - timedelta(days = max_day_limit)) > previous_switch_tip_instance.date:
                # if matchup occurred over max_day_limit days ago then series has ended
                return
            
            # this matchup is part of the series, continue searching for earliest matchup in series
            sides_switch_query['last_tip'] = None
            sides_switch_query['offset'] += 1
            sorted_date_series.insert(0, previous_switch_tip_instance)
            self._fill_series(sorted_date_series, sides_match_query, sides_switch_query, max_day_limit)
        
        # got all the matchups in the series, all done
        return