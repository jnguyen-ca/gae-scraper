#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from datetime import datetime

import constants
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
            if league_key in constants.LEAGUES_OT_INCLUDED:
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