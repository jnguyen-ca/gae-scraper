#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import webapp

import json
from datetime import datetime

import re
import models

# .teams, .totals, .over, .under, .none, .total_side .header {display: inline-block; width: 150px; text-align: right;}
# .tip_stake_result {margin: 3px 0;}
# .total_nos_result {margin: 12px 0;}
# .tip_stake_result .teams, .total_no_result .results > span, .total_side .header {margin-right: 18px;}
# .total_side {margin-left: 38px;}
# .total_no_result .total_no, .tip_stake_result .stake {display: inline-block; width: 28px;}
# .unit_change {margin: 0 0 0 6px ;}

BET_RESULT_WIN = 'Y'
BET_RESULT_LOSS = 'N'
BET_RESULT_NONE = 'R'
BET_RESULT_PUSH = 'PU'
BET_RESULT_SPLIT = 'H'
BET_RESULT_HALF_WIN = 'HW'
BET_RESULT_HALF_LOSS = 'HL'

def calculate_event_score_result(backing_score, opposition_score, **kwargs):
    if isinstance(backing_score, basestring):
        if '(' in backing_score:
            if (
                'regulation_only' in kwargs 
                and kwargs['regulation_only'] is True 
                ):
                backing_score = re.sub('.+\(', '', backing_score).rstrip(')')
                opposition_score = re.sub('.+\(', '', opposition_score).rstrip(')')
            else:
                backing_score = re.sub('\s+.*', '', backing_score)
                opposition_score = re.sub('\s+.*', '', opposition_score)
    
    backing_score = float(backing_score)
    opposition_score = float(opposition_score)
    
    if backing_score is None or opposition_score is None:
        return BET_RESULT_NONE
    
    if 'spread_modifier' in kwargs and kwargs['spread_modifier'] is not None:
        spread_modifier = float(kwargs['spread_modifier'])
        
        if spread_modifier % 0.5 == 0:
            if opposition_score < (backing_score + spread_modifier):
                return BET_RESULT_WIN
            elif opposition_score > (backing_score + spread_modifier):
                return BET_RESULT_LOSS
            else:
                return BET_RESULT_PUSH
        else:
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
        if 'draw_result' in kwargs and kwargs['draw_result'] is True:
            if backing_score == opposition_score:
                return BET_RESULT_WIN
            else:
                return BET_RESULT_LOSS
        else:
            if backing_score > opposition_score:
                return BET_RESULT_WIN
            elif backing_score < opposition_score:
                return BET_RESULT_LOSS
            else:
                if 'draw_lose' in kwargs and kwargs['draw_lose'] is True:
                    return BET_RESULT_LOSS
                else:
                    return BET_RESULT_PUSH
    
def convert_to_decimal_odds(moneyline):
    moneyline = float(moneyline)
    
    if moneyline < 0:
        return 100.0 / (moneyline * -1) + 1.0
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

class TipAnalysis(webapp.RequestHandler):
    def get(self):
        pass
    
    def display_wettpoint_results(self, league):
        team_list = self.team_wettpoint_stake_result(league)
        total_list = self.total_wettpoint_stake_result(league)
        
        for tip_stake in sorted(team_list.iterkeys()):
            tip_team_results = team_list[tip_stake]
            tip_total_results = total_list[tip_stake]
            
            team_wins = tip_team_results[0]
            team_losses = tip_team_results[1]
            team_pushes = tip_team_results[2]
            team_unit_change = tip_team_results[3]
            total_wins = tip_total_results[0]
            total_losses = tip_total_results[1]
            total_pushes = tip_total_results[2]
            total_unit_change = tip_total_results[3]
            
            self.html.append("<div class='tip_stake_result'>")
            self.html.append("<span class='stake'><b>%(tip_stake)s</b></span> : " % locals())
            self.html.append("<span class='results'>")
            self.html.append("<span class='teams'>")
            self.html.append("<span class='wins'>%(team_wins)d</span> - " % locals())
            self.html.append("<span class='losses'>%(team_losses)d</span> - " % locals())
            self.html.append("<span class='pushes'>%(team_pushes)d</span>" % locals())
            self.html.append("<span class='unit_change'>(%(team_unit_change).2f)</span>" % locals())
            self.html.append("</span>")
            self.html.append("<span class='totals'>")
            self.html.append("<span class='wins'>%(total_wins)d</span> - " % locals())
            self.html.append("<span class='losses'>%(total_losses)d</span> - " % locals())
            self.html.append("<span class='pushes'>%(total_pushes)d</span>" % locals())
            self.html.append("<span class='unit_change'>(%(total_unit_change).2f)</span>" % locals())
            self.html.append("</span>")
            self.html.append("</span>")
            self.html.append("</div>")
    
    def total_wettpoint_stake_result(self, league):
        wettpoint_list = {}
        total_list = {}
        
        for tip_instance in self.datastore[league]:
            if tip_instance.game_team_away.split(' ')[0].lower() == 'away' and tip_instance.game_team_home.split(' ')[0].lower() == 'home':
                continue
            
            tip_stake = str(tip_instance.wettpoint_tip_stake)
            if not tip_stake in wettpoint_list:
                wettpoint_list[tip_stake] = [0, 0, 0, 0]
                
            if tip_instance.total_no:
                latest_date = False
                latest_no = False
                latest_line = 0
                for date, line in json.loads(tip_instance.total_no).iteritems():
                    date = datetime.strptime(date, '%d.%m.%Y %H:%M')
                    if not latest_date:
                        latest_date = date
                        latest_no = line
                    if date > latest_date:
                        latest_date = date
                        latest_no = line
                        
                if latest_date and tip_instance.total_lines:
                    lines = json.loads(tip_instance.total_lines)
                    latest_date = latest_date.strftime('%d.%m.%Y %H:%M')
                    if latest_date in lines:
                        latest_line = lines[latest_date]
                
                if not latest_no in total_list:
                    total_list[latest_no] = {'Over' : [0, 0, 0, 0], 'Under' : [0, 0, 0, 0], 'None' : [0, 0, 0, 0]}
                
                latest_no_float = float(latest_no)
                        
                if tip_instance.wettpoint_tip_total and tip_instance.wettpoint_tip_total == 'Over':
                    if tip_instance.score_away is None and tip_instance.score_home is None:
                        wettpoint_list[tip_stake][2] += 1
                        total_list[latest_no]['Over'][2] += 1
                    elif float(tip_instance.score_away) + float(tip_instance.score_home) > latest_no_float:
                        wettpoint_list[tip_stake][0] += 1
                        total_list[latest_no]['Over'][0] += 1
                        if float(latest_line) < 100:
                            wettpoint_list[tip_stake][3] += 1
                            total_list[latest_no]['Over'][3] += 1
                        else:
                            unit_change = float(latest_line) / 100.0
                            wettpoint_list[tip_stake][3] += unit_change
                            total_list[latest_no]['Over'][3] += unit_change
                    elif float(tip_instance.score_away) + float(tip_instance.score_home) < latest_no_float:
                        wettpoint_list[tip_stake][1] += 1
                        total_list[latest_no]['Over'][1] += 1
                        if float(latest_line) < 100:
                            unit_change = float(latest_line) / 100.0
                            wettpoint_list[tip_stake][3] += unit_change
                            total_list[latest_no]['Over'][3] += unit_change
                        else:
                            wettpoint_list[tip_stake][3] -= 1
                            total_list[latest_no]['Over'][3] -= 1
                    else:
                        wettpoint_list[tip_stake][2] += 1
                        total_list[latest_no]['Over'][2] += 1
                elif tip_instance.wettpoint_tip_total and tip_instance.wettpoint_tip_total == 'Under':
                    if tip_instance.score_away is None and tip_instance.score_home is None:
                        wettpoint_list[tip_stake][2] += 1
                        total_list[latest_no]['Under'][2] += 1
                    elif float(tip_instance.score_away) + float(tip_instance.score_home) < latest_no_float:
                        wettpoint_list[tip_stake][0] += 1
                        total_list[latest_no]['Under'][0] += 1
                        if float(latest_line) < 100:
                            wettpoint_list[tip_stake][3] += 1
                            total_list[latest_no]['Under'][3] += 1
                        else:
                            unit_change = float(latest_line) / 100.0
                            wettpoint_list[tip_stake][3] += unit_change
                            total_list[latest_no]['Under'][3] += unit_change
                    elif float(tip_instance.score_away) + float(tip_instance.score_home) > latest_no_float:
                        wettpoint_list[tip_stake][1] += 1
                        total_list[latest_no]['Under'][1] += 1
                        if float(latest_line) < 100:
                            unit_change = float(latest_line) / 100.0
                            wettpoint_list[tip_stake][3] += unit_change
                            total_list[latest_no]['Under'][3] += unit_change
                        else:
                            wettpoint_list[tip_stake][3] -= 1
                            total_list[latest_no]['Under'][3] -= 1
                    else:
                        wettpoint_list[tip_stake][2] += 1
                        total_list[latest_no]['Under'][2] += 1
                else:
                    if tip_instance.score_away is None and tip_instance.score_home is None:
                        wettpoint_list[tip_stake][2] += 1
                        total_list[latest_no]['None'][2] += 1
                    elif float(tip_instance.score_away) + float(tip_instance.score_home) < latest_no_float:
                        wettpoint_list[tip_stake][0] += 1
                        total_list[latest_no]['None'][0] += 1
                        if float(latest_line) < 100:
                            wettpoint_list[tip_stake][3] += 1
                            total_list[latest_no]['None'][3] += 1
                        else:
                            unit_change = float(latest_line) / 100.0
                            wettpoint_list[tip_stake][3] += unit_change
                            total_list[latest_no]['None'][3] += unit_change
                    elif float(tip_instance.score_away) + float(tip_instance.score_home) > latest_no_float:
                        wettpoint_list[tip_stake][1] += 1
                        total_list[latest_no]['None'][1] += 1
                        if float(latest_line) < 100:
                            unit_change = float(latest_line) / 100.0
                            wettpoint_list[tip_stake][3] += unit_change
                            total_list[latest_no]['None'][3] += unit_change
                        else:
                            wettpoint_list[tip_stake][3] -= 1
                            total_list[latest_no]['None'][3] -= 1
                    else:
                        wettpoint_list[tip_stake][2] += 1
                        total_list[latest_no]['None'][2] += 1
        
        self.html.append("<div class='total_nos_result'>")
        self.html.append("<div class='total_side'>")
        self.html.append("<span class='header'>Over</span>")
        self.html.append("<span class='header'>Under</span>")
        self.html.append("<span class='header'>None</span>")
        self.html.append("</div>")
        
        for total_no in sorted(total_list.iterkeys()):
            over_wins = total_list[total_no]['Over'][0]
            over_losses = total_list[total_no]['Over'][1]
            over_pushes = total_list[total_no]['Over'][2]
            under_wins = total_list[total_no]['Under'][0]
            under_losses = total_list[total_no]['Under'][1]
            under_pushes = total_list[total_no]['Under'][2]
            none_wins = total_list[total_no]['None'][0]
            none_losses = total_list[total_no]['None'][1]
            none_pushes = total_list[total_no]['None'][2]
            over_unit_change = total_list[total_no]['Over'][3]
            under_unit_change = total_list[total_no]['Under'][3]
            none_unit_change = total_list[total_no]['None'][3]
            
            self.html.append("<div class='total_no_result'>")
            self.html.append("<span class='total_no'><b>%(total_no)s</b></span> : " % locals())
            self.html.append("<span class='results'>")
            self.html.append("<span class='over'>")
            self.html.append("<span class='wins'>%(over_wins)d</span> - " % locals())
            self.html.append("<span class='losses'>%(over_losses)d</span> - " % locals())
            self.html.append("<span class='pushes'>%(over_pushes)d</span>" % locals())
            self.html.append("<span class='unit_change'>(%(over_unit_change).2f)</span>" % locals())
            self.html.append("</span>")
            self.html.append("<span class='under'>")
            self.html.append("<span class='wins'>%(under_wins)d</span> - " % locals())
            self.html.append("<span class='losses'>%(under_losses)d</span> - " % locals())
            self.html.append("<span class='pushes'>%(under_pushes)d</span>" % locals())
            self.html.append("<span class='unit_change'>(%(under_unit_change).2f)</span>" % locals())
            self.html.append("</span>")
            self.html.append("<span class='none'>")
            self.html.append("<span class='wins'>%(none_wins)d</span> - " % locals())
            self.html.append("<span class='losses'>%(none_losses)d</span> - " % locals())
            self.html.append("<span class='pushes'>%(none_pushes)d</span>" % locals())
            self.html.append("<span class='unit_change'>(%(none_unit_change).2f)</span>" % locals())
            self.html.append("</span>")
            self.html.append("</span>")
            self.html.append("</div>")
        
        self.html.append("</div>")
                                
        return wettpoint_list
    
    def team_wettpoint_stake_result(self, league):
        wettpoint_list = {}
        
        for tip_instance in self.datastore[league]:
            # ignore grand salami
            if tip_instance.game_team_away.split(' ')[0].lower() == 'away' and tip_instance.game_team_home.split(' ')[0].lower() == 'home':
                continue
            
            # keep a running total for each tip_stake
            tip_stake = str(tip_instance.wettpoint_tip_stake)
            if not tip_stake in wettpoint_list:
                # index order is: wins, losses, draws, unit change
                wettpoint_list[tip_stake] = [0, 0, 0, 0]
            
            # use the line right before a event starts to get most accurate results
            latest_date = False
            latest_line = False
            if tip_instance.team_lines:
                for date, line in json.loads(tip_instance.team_lines).iteritems():
                    date = datetime.strptime(date, '%d.%m.%Y %H:%M')
                    if not latest_date:
                        latest_date = date
                        latest_line = line
                    if date > latest_date:
                        latest_date = date
                        latest_line = line
            
            # single side bet
            if (
                tip_instance.wettpoint_tip_team == '1' 
                or tip_instance.wettpoint_tip_team == '2' 
                or tip_instance.wettpoint_tip_team == 'X'
                ):
                
                if tip_instance.wettpoint_tip_team == '1':
                    result = calculate_event_score_result(tip_instance.score_home, tip_instance.score_away)
                else:
                    result = calculate_event_score_result(tip_instance.score_away, tip_instance.score_home)
                    
                if result == 'R':
                    wettpoint_list[tip_stake][2] += 1
                elif (
                      result == BET_RESULT_WIN 
                      or (
                          tip_instance.wettpoint_tip_team == 'X' 
                          and result == 'D'
                          )
                      ):
                    wettpoint_list[tip_stake][0] += 1
                    wettpoint_list[tip_stake][3] += calculate_event_unit_change(BET_RESULT_WIN, float(latest_line), win=1)
                else:
                    wettpoint_list[tip_stake][1] += 1
                    wettpoint_list[tip_stake][3] += calculate_event_unit_change(BET_RESULT_LOSS, float(latest_line), win=1)
            elif tip_instance.wettpoint_tip_team == '12':
                pass
            elif tip_instance.wettpoint_tip_team == '1X':
                pass
            elif tip_instance.wettpoint_tip_team == 'X2':
                pass
            
#             if tip_instance.wettpoint_tip_team == tip_instance.game_team_away:
#                 # a PPD/cancelled event, track as a draw
#                 if (
#                     tip_instance.score_away is None 
#                     and tip_instance.score_home is None
#                     ):
#                     wettpoint_list[tip_stake][2] += 1
#                 # a team away win
#                 elif float(tip_instance.score_away) > float(tip_instance.score_home):
#                     wettpoint_list[tip_stake][0] += 1
#                     if latest_line:
#                         # get unit change based on 1 unit (to-win) bets
#                         if float(latest_line) < 100:
#                             wettpoint_list[tip_stake][3] += 1
#                         else:
#                             unit_change = float(latest_line) / 100.0
#                             wettpoint_list[tip_stake][3] += unit_change
#                 # a team away loss
#                 elif float(tip_instance.score_away) < float(tip_instance.score_home):
#                     wettpoint_list[tip_stake][1] += 1
#                     if latest_line:
#                         # get unit change based on 1 unit (to-win) bets
#                         if float(latest_line) < 100:
#                             unit_change = float(latest_line) / 100.0
#                             wettpoint_list[tip_stake][3] += unit_change
#                         else:
#                             wettpoint_list[tip_stake][3] -= 1
#                 # a draw
#                 else:
#                     wettpoint_list[tip_stake][2] += 1
#             elif tip_instance.wettpoint_tip_team == tip_instance.game_team_home:
#                 # a PPD/cancelled event, track as a draw
#                 if (
#                     tip_instance.score_away is None 
#                     and tip_instance.score_home is None
#                     ):
#                     wettpoint_list[tip_stake][2] += 1
#                 # a team home win
#                 elif float(tip_instance.score_home) > float(tip_instance.score_away):
#                     wettpoint_list[tip_stake][0] += 1
#                     if latest_line:
#                         # get unit change based on 1 unit (to-win) bets
#                         if float(latest_line) < 100:
#                             wettpoint_list[tip_stake][3] += 1
#                         else:
#                             unit_change = float(latest_line) / 100.0
#                             wettpoint_list[tip_stake][3] += unit_change
#                 # a team home loss
#                 elif float(tip_instance.score_home) < float(tip_instance.score_away):
#                     wettpoint_list[tip_stake][1] += 1
#                     if latest_line:
#                         # get unit change based on 1 unit (to-win) bets
#                         if float(latest_line) < 100:
#                             unit_change = float(latest_line) / 100.0
#                             wettpoint_list[tip_stake][3] += unit_change
#                         else:
#                             wettpoint_list[tip_stake][3] -= 1
#                 # a draw
#                 else:
#                     wettpoint_list[tip_stake][2] += 1
                    
        return wettpoint_list