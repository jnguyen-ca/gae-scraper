#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('utils')

import json
from datetime import datetime, timedelta
from utils import appvar_util

import models

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
        
        # query datastore for previous series events
        # a series can be determined by matching the same 2 teams who play against each other
        # uninterrupted by other teams, limited to a certain date range
        #TODO: analyze this, any better way to do this without having to make a query every single time?
        self.datastore_reads += 1
        query = models.Tip.gql('WHERE game_sport = :1 AND game_league = :2 AND date < :3 ORDER BY date DESC',
                                 tip_instance.game_sport,
                                 tip_instance.game_league,
                                 tip_instance.date,
                                 )
        
        max_day_limit = 3
        last_series_entry_date = tip_instance.date
        
        # continue searching until no longer a series between the 2 teams
        series_tips = []
        for previous_tip_instance in query:
            self.datastore_reads += 1
            # only interested in the previous Tip if it's an earlier game of the same series or if it's a game
            # that breaks the series for tip_instances, either way only care if 1 of the teams match
            if (
                previous_tip_instance.game_team_away in [tip_instance.game_team_away, tip_instance.game_team_home]
                or previous_tip_instance.game_team_home in [tip_instance.game_team_away, tip_instance.game_team_home]
            ):
                # both teams have to be the same to be part of the same series (away vs home can be switched, just same teams)
                # on first sign where 1 team is playing a different team then the series has been broken
                if (
                    (
                     previous_tip_instance.game_team_away == tip_instance.game_team_away
                     and previous_tip_instance.game_team_home == tip_instance.game_team_home
                     )
                    or
                    (
                     previous_tip_instance.game_team_home == tip_instance.game_team_away
                     and previous_tip_instance.game_team_away == tip_instance.game_team_home
                     )
                ):
                    # same series
                    series_tips.append(previous_tip_instance)
                    last_series_entry_date = previous_tip_instance.date
                else:
                    # 1 of the teams is playing a different team, series has been broken
                    break
                
            if (last_series_entry_date - timedelta(days = max_day_limit)) > previous_tip_instance.date:
                break
        
        # Tip was the first of its series (or there is no series)
        if len(series_tips) < 1:
            return None
        
        # only want to extend the first of the series wettpoint tips if none of the other Tips in the series
        # have wettpoint tips (which would mean the wettpoint tips are being updated throughout the series and
        # a 0.0 wettpoint tip is actually a 0.0 wettpoint tip and not just a blank)
        series_wettpoint_tip_team = str(tip_instance.wettpoint_tip_team)
        series_wettpoint_tip_total = str(tip_instance.wettpoint_tip_total)
        series_wettpoint_tip_stake = str(tip_instance.wettpoint_tip_stake)
        
        first_series_tip = series_tips.pop()
        
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
        
        for preceding_series_tip in series_tips:
            # series is being updated throughout
            if preceding_series_tip.wettpoint_tip_stake != 0.0 or preceding_series_tip.wettpoint_tip_total != None:
                return None
        
        return series_wettpoint_tip_team, series_wettpoint_tip_total, series_wettpoint_tip_stake