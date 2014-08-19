#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import webapp
from google.appengine.api import users, memcache

from models import Tip, DisplaySession

from math import ceil
from datetime import datetime, timedelta

import string
import json
import constants

def calculate_event_score_result(backing_score, opposition_score):
    if backing_score is None or opposition_score is None:
        return 'R'
    elif float(backing_score) > float(opposition_score):
        return 'W'
    elif float(backing_score) < float(opposition_score):
        return 'L'
    else:
        return 'D'
    
def convert_to_decimal_odds(moneyline):
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
            
    if result == 'W':
        return bet_amount * fractional_line
    elif result == 'L':
        return bet_amount * -1.0
    elif result == 'H':
        return ((bet_amount / 2.0) * fractional_line) - (bet_amount / 2.0)
    
    return None

class TipDisplay(webapp.RequestHandler):
    def post(self):
        self.datastore = {}
        
        self.html = []
        self.cssheader = []
        self.styleheader = []
        self.jsheader = []
        self.scriptheader = []
        
        self.cssheader.append(
'''<link rel="stylesheet" href="/javascript/scatterplot/css/scatterplot.css" />''')
        self.jsheader.append(
'''<script src="//ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>
<script src="/javascript/scatterplot/js/scatterplot.min.js"></script>''')
        self.styleheader.append(
'''<style>
    .line_hour_interval {display: inline-block; vertical-align: top; width: 20%; margin: 1%; padding: 1%; border: 1px solid black;}
    .hour {text-decoration: underline; text-align: center;}
    .game_time-MST {width: 10%;}
    .upcoming_game {margin: 6px 0;}
    .upcoming_game > span {display: inline-block; margin-right: 12px; min-width: 50px;}
    .upcoming_game .participants {width: 22%; text-overflow: ellipsis;}
    .upcoming_game .tip-team {width: 13%; text-overflow: ellipsis;}
    .upcoming_game .tip-date {width: 10%;}
    .upcoming_game .tip-line-adjusted_win, .upcoming_game .tip-line-adjusted_loss {background: lightgrey; text-align: center;}
    .upcoming_game .today {font-weight: bold;}
    .upcoming_game .closing {color: red;}
    .upcoming_game .pending {color: green;}
    .teams, .totals, .over, .under, .none, .total_side .header {display: inline-block; width: 150px; text-align: right;}
    .tip_stake_result {margin: 3px 0;}
    .total_nos_result {margin: 12px 0;}
    .tip_stake_result .teams, .total_no_result .results > span, .total_side .header {margin-right: 18px;}
    .total_side {margin-left: 38px;}
    .total_no_result .total_no, .tip_stake_result .stake {display: inline-block; width: 28px;}
    .unit_change {margin: 0 0 0 6px ;}
    .point {margin-bottom: -4.5px; margin-left: -6.5px;}
    .point .data {display: none; background: lightblue; padding: 3px; margin-left: 12px; float: left; text-align: right; position: absolute; z-index: 1;}
    .intervals .interval {float: left; display: inline-block; width: 120px; height: 35px; opacity: 0.25; font-weight: bold; color: white; margin: -1px 1px 1px -1px;}
</style>''')
        self.html.append('<body>')
        
        session = DisplaySession.gql('WHERE user = :1', users.get_current_user()).get()
        
        if session is None:
            session = DisplaySession()
            session.user = users.get_current_user()
        
        visible_seasons = self.request.get_all('season-display-control')
        hidden_seasons = self.request.get_all('season-display-hidden-control')
        
        display_seasons = {}
        
        for season in visible_seasons:
            values = season.partition('&')
            if values[0] == season:
                continue
            
            season_league = values[0]
            season_dates = values[2]
            
            if not season_league in display_seasons:
                display_seasons[season_league] = {}
                
            display_seasons[season_league][season_dates] = True
            
        for season in hidden_seasons:
            values = season.partition('&')
            if values[0] == season:
                continue
            
            season_league = values[0]
            season_dates = values[2]
            
            if not season_league in display_seasons:
                display_seasons[season_league] = {}
                
            display_seasons[season_league][season_dates] = False
        
        ds_json_string = json.dumps(display_seasons)
#         self.response.set_cookie('DisplaySessionCookie', ds_json_string, expires=(datetime.now() + timedelta(days=1)), overwrite=True)
        memcache.set('DisplaySessionCookie', ds_json_string)
        session.leagues = ds_json_string
        
        for sport, leagues in constants.LEAGUES.iteritems():
            for league_key, league_specifiers in leagues.iteritems():
                if not league_key in display_seasons.keys():
                    continue
                
                self.html.append("<div class='league_key'><b>%(league_key)s</b></div>" % locals())
                
                dateRanges = {}
                for dateRange, checked in display_seasons[league_key].iteritems():
                    if checked:
                        dateValues = dateRange.partition('-')
                        fromDate = datetime.strptime(dateValues[0] + ' 00:00:00','%m.%d.%Y %H:%M:%S') + timedelta(hours = 4)
                        toDate = datetime.strptime(dateValues[2] + ' 23:59:59','%m.%d.%Y %H:%M:%S') + timedelta(hours = 4)
                        
                        if fromDate in dateRanges:
                            if dateRanges[fromDate] > toDate:
                                continue
                            
                        dateRanges[fromDate] = toDate
                
                self.html.append("<span class='league-dates'>")
                
                for fromDate in sorted(dateRanges):
                    self.html.append("<span class='league-date'><span class='from-date'>"+fromDate.strftime('%m.%d.%Y')+"</span>-<span class='to-date'>"+dateRanges[fromDate].strftime('%m.%d.%Y')+"</span></span>")
                    
                    query = Tip.gql('WHERE date >= :1 AND date <= :2 AND archived = True AND game_league = :3 ORDER BY date ASC', fromDate, dateRanges[fromDate], league_key)
                    
                    for tip_instance in query:
                        if not league_key in self.datastore:
                            self.datastore[league_key] = []
                            
                        self.datastore[league_key].append(tip_instance)
                
                self.html.append("</span>")
                
                if not league_key in self.datastore:
                    continue
                        
                self.list_next_games(league_key)
                #self.line_by_time_scatterplot(league_key)      
                self.display_wettpoint_results(league_key)
                #self.line_movement_scatterplot(league_key)  
                #self.display_line_by_time(league_key)
        
        self.html.append('</body></html>')    
            
        html = []
        html.append('''<html><head>''')
        html.append("".join(self.cssheader))
        html.append("".join(self.jsheader))
        html.append("".join(self.scriptheader))
        html.append("".join(self.styleheader))
        html.append('</head>')
        html.append("".join(self.html))
        self.response.out.write("".join(html))
        
        session.last_login = datetime.utcnow()
        session.put()
        
    def list_next_games(self, league):
        query = Tip.gql('WHERE archived != True AND game_league = :1 ORDER BY archived ASC, date ASC', league)
        
        #hour_intervals = self.line_by_time(league)
        
        game_count = 0
        self.html.append('<div class="upcoming_games">')
        for tip_instance in query:
            current_time = datetime.utcnow() - timedelta(hours = 6)
            game_time = tip_instance.date - timedelta(hours = 6)
            
            date_class = 'game_time-MST'
            if current_time.date().day == game_time.date().day:
                date_class += ' today'
            elif (game_time.date() - current_time.date()).days == 1:
                date_class += ' tomorrow'
            if game_time - current_time < timedelta(hours=2):
                date_class += ' closing'
            if tip_instance.elapsed == True:
                date_class += ' pending'
            
            game_time = game_time.strftime('%B-%d %I:%M%p')
            
            team_away = tip_instance.game_team_away
            team_home = tip_instance.game_team_home
            
            wettpoint_stake = tip_instance.wettpoint_tip_stake
            wettpoint_team = tip_instance.wettpoint_tip_team
            wettpoint_total = tip_instance.wettpoint_tip_total
            
#             line_hour_track = [0,0,0]
#             adjust_count = 0
            
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
                        
#                     if date.time().hour in hour_intervals:
#                         if line in hour_intervals[date.time().hour]:
#                             line_hour_track[0] += hour_intervals[date.time().hour][line][0]
#                             line_hour_track[1] += hour_intervals[date.time().hour][line][1]
#                             line_hour_track[2] += hour_intervals[date.time().hour][line][2]
                            
#                             adjust_count += 1
            
            total_no = False
            if tip_instance.total_no:
                latest_date_string = latest_date.strftime('%d.%m.%Y %H:%M')
                totals = json.loads(tip_instance.total_no)
                if latest_date_string in totals:
                    total_no = totals[latest_date_string]
            
            if latest_date:
                latest_date = latest_date - timedelta(hours = 6)
                latest_date = latest_date.strftime('%Y/%m/%d %I:%M%p')
                
#             line_hour_total = line_hour_track[0] + line_hour_track[1]
#             line_hour_percentage = False
#             adjusted_win_percentage = False
#             adjusted_loss_percentage = False
#             adjusted_total_count = line_hour_total + adjust_count
#             if line_hour_total > 0:
#                 line_hour_percentage = line_hour_track[0] / float(line_hour_total)
#                 adjusted_win_percentage = (line_hour_track[0] + adjust_count) / float(adjusted_total_count)
#                 adjusted_loss_percentage = line_hour_track[0] / float(adjusted_total_count)
                
            game_count += 1
            self.html.append('<div class="upcoming_game">')
            self.html.append('<span class="game-count" style="min-width: 16px;">%(game_count)d</span>' % locals())
            self.html.append('<span class="%(date_class)s">%(game_time)s</span>' % locals())
            self.html.append('<span class="participants"><span class="away">%(team_away)s</span> - <span class="home">%(team_home)s</span></span>' % locals())
            self.html.append('<span class="tip-stake">%(wettpoint_stake)s</span>' % locals())
            self.html.append('<span class="tip-team">%(wettpoint_team)s</span>' % locals())
            self.html.append('<span class="tip-line">%(latest_line)s</span>' % locals())
            self.html.append('<span class="tip-date">%(latest_date)s</span>' % locals())
            self.html.append('<span class="tip-total">%(wettpoint_total)s</span>' % locals())
            self.html.append('<span class="tip-total_no">%(total_no)s</span>' % locals())
#             self.html.append('<span class="tip-line-past">%(line_hour_percentage).2f</span>' % locals())
#             self.html.append('<span class="tip-line-past-count">%(line_hour_total)d</span>' % locals())
#             self.html.append('<span class="tip-line-adjusted_win">%(adjusted_win_percentage).2f</span>' % locals())
#             self.html.append('<span class="tip-line-adjusted_loss">%(adjusted_loss_percentage).2f</span>' % locals())
#             self.html.append('<span class="tip-line-adjusted_count">%(adjusted_total_count)d</span>' % locals())
            self.html.append('</div>')
        
        self.html.append('</div>')
        
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
                      result == 'W' 
                      or (
                          tip_instance.wettpoint_tip_team == 'X' 
                          and result == 'D'
                          )
                      ):
                    wettpoint_list[tip_stake][0] += 1
                    wettpoint_list[tip_stake][3] += calculate_event_unit_change('W', float(latest_line), win=1)
                else:
                    wettpoint_list[tip_stake][1] += 1
                    wettpoint_list[tip_stake][3] += calculate_event_unit_change('L', float(latest_line), win=1)
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
    
#     def line_by_time_scatterplot(self, league):
#         hour_intervals = self.line_by_time(league)
#         
#         current_time = datetime.utcnow() - timedelta(hours = 6)
#         
#         maxp = 0
#         points = []
#         for tip_instance in self.datastore[league]:
#             game_time = tip_instance.date - timedelta(hours = 6)
#             
#             line_hour_track = [0,0,0]
#             game_count = {}
#             if tip_instance.team_lines:
#                 latest_date = False
#                 latest_line = False
#                 
#                 for date, line in json.loads(tip_instance.team_lines).iteritems():
#                     date = datetime.strptime(date, '%d.%m.%Y %H:%M')
#                     if not latest_date:
#                         latest_date = date
#                         latest_line = int(line)
#                     if date > latest_date:
#                         latest_date = date
#                         latest_line = int(line)
#                     
#                     if date.time().hour in hour_intervals:
#                         if line in hour_intervals[date.time().hour]:
#                             line_hour_track[0] += hour_intervals[date.time().hour][line][0]
#                             line_hour_track[1] += hour_intervals[date.time().hour][line][1]
#                             line_hour_track[2] += hour_intervals[date.time().hour][line][2]
#                             
#                             if date.time().hour in game_count:
#                                 if line in game_count[date.time().hour]:
#                                     game_count[date.time().hour][line][0] += 1
#                                 else:
#                                     game_count[date.time().hour][line] = [1, hour_intervals[date.time().hour][line][0], hour_intervals[date.time().hour][line][1]]
#                             else:
#                                 game_count[date.time().hour] = {}
#                                 game_count[date.time().hour][line] = [1, hour_intervals[date.time().hour][line][0], hour_intervals[date.time().hour][line][1]]
#                             
#             color = False
#             result = False
#             if tip_instance.score_away is None and tip_instance.score_home is None:
#                 continue
#             elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) > float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) < float(tip_instance.score_home)):
#                 if (current_time.date() - game_time.date()).days == 0:
#                     color = 'yellow'
#                 elif (current_time.date() - game_time.date()).days == 1:
#                     color = 'darkgreen'
#                 elif tip_instance.wettpoint_tip_stake > 0:
#                     color = 'grey'
#                 else:
#                     color = 'black'
#                 
#                 for i in game_count.itervalues():
#                     for j in i.itervalues():
#                         line_hour_track[0] -= (j[0] * j[0])
#                 result = 'W'
#             elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) < float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) > float(tip_instance.score_home)):
#                 if (current_time.date() - game_time.date()).days == 0:
#                     color = 'orange'
#                 elif (current_time.date() - game_time.date()).days == 1:
#                     color = 'purple'
#                 elif tip_instance.wettpoint_tip_stake > 0:
#                     color = 'red'
#                 else:
#                     color = 'darkred'
#                     
#                 for i in game_count.itervalues():
#                     for j in i.itervalues():
#                         line_hour_track[1] -= (j[0] * j[0])
#                 result = 'L'
#             else:
#                 continue
#             
#             line_hour_total = line_hour_track[0] + line_hour_track[1]
#             if line_hour_total <= 0:
#                 continue
#             elif line_hour_total > maxp:
#                 maxp = line_hour_total
#             
#             line_hour_percentage = (line_hour_track[0] / float(line_hour_total)) * 100.00
#             
#             points.append([line_hour_total, line_hour_percentage, color, tip_instance.wettpoint_tip_stake, latest_line, result])
#         
#         self.draw_scatterplot('line_hour_interval_scatterplot', points, int(ceil(maxp / 1000.0) * 1000))
#         
#         self.scriptheader.append(
# '''<script>
# jQuery(document).ready(function() {
# ''')
#         self.scriptheader.append('var maxp = '+str(maxp)+';')
#         self.scriptheader.append(
# '''
#     jQuery('.upcoming_game .today').each(function() {
#         var game = jQuery(this).parent();
#         var position_x = String.fromCharCode(65 + Math.floor(game.find('.tip-line-past-count').text() / 2000.0 * 10))
#         var position_y = Math.floor(game.find('.tip-line-past').text() * 100 / 5 + 1)
#     
#         game.append('<span class="upcoming_interval" style="min-width: 30px;">'+position_x+position_y+'</span>')
#         
#         if (position_y != 21 && position_x != 'J')
#         {
#             var unit_count = jQuery.data(jQuery('.scatterplot #'+position_x+position_y)[0], 'unit_count');
#             var bet_amount = Math.round(Math.abs(((0.65 - jQuery('.scatterplot #'+position_x+position_y).css('opacity')) * 10) - 5));
#             if (typeof unit_count == 'undefined' || unit_count >= 0)
#             {
#                 game.append('<span class="upcoming_tail" style="background-color: lightgreen; text-align: center;">'+bet_amount+'</span>')
#             }
#             else
#             {
#                 game.append('<span class="upcoming_fade" style="background-color: pink; text-align: center;">'+bet_amount+'</span>')
#             }
#         }
#         
# //        game.find('.tip-line-adjusted_win, .tip-line-adjusted_loss').hover(function() {
# //            var a_position_x = String.fromCharCode(65 + Math.floor(game.find('.tip-line-adjusted_count').text() / maxp * 10))
# //            var a_position_y = Math.floor(jQuery(this).text() * 100 / 5 + 1)
#             
# //            game.find('.upcoming_interval').css('color', 'red').text(a_position_x+a_position_y)
# //        }, function() {game.find('.upcoming_interval').css('color', '').text(position_x+position_y)})
#     });
#     
#     jQuery('<input>')
#         .attr('id', 'line_hour_interval-simplify')
#         .attr('type', 'checkbox')
#         .attr('style', 'margin-left: 1270px; margin-top: -750px; position: absolute;')
#         .insertAfter('#line_hour_interval_scatterplot')
#         .on('change', function() {
#             var $this = jQuery(this);
#         
#             jQuery('#line_hour_interval_scatterplot .point:not(".today-point")').each(function() {
#                 if ($this.is(':checked'))
#                 {
#                     jQuery.data(this, 'original-color', jQuery(this).find('.data .color').text())
#                     if (jQuery(this).find('.data .result').text() == 'W')
#                     {
#                         jQuery(this).css('background-color', 'black');
#                     }
#                     else
#                     {
#                         jQuery(this).css('background-color', 'darkred');
#                     }
#                 }
#                 else
#                 {
#                     jQuery(this).css('background-color', jQuery.data(this, 'original-color'));
#                 }
#             });
#         });
#     
#     jQuery('<input>')
#         .attr('id', 'line_hour_interval-today')
#         .attr('type', 'checkbox')
#         .attr('style', 'margin-left: 1270px; margin-top: -700px; position: absolute;')
#         .insertAfter('#line_hour_interval_scatterplot')
#         .on('change', function() {
#             if (jQuery(this).is(':checked'))
#             {
#                 if (jQuery('#line_hour_interval_scatterplot .today-point').length == 0)
#                 {
#                     var today_games = jQuery('.upcoming_game .today');
#                     if (today_games.length == 0)
#                     {
#                         today_games = jQuery('.upcoming_game .tomorrow')
#                     }
#                 
#                     today_games.each(function() {
#                         var game = jQuery(this).parent();
#                         var left = (game.find('.tip-line-past-count').text() / 2000.0) * jQuery('#line_hour_interval_scatterplot').width()
#                         var bottom = game.find('.tip-line-past').text() * jQuery('#line_hour_interval_scatterplot').height()
#                         
#                         var today_point = jQuery('#line_hour_interval_scatterplot .point')
#                             .first()
#                             .clone(true)
#                             .css('background-color', 'lightblue')
#                             .css('bottom', bottom)
#                             .css('left', left)
#                             .addClass('today-point')
#                             .appendTo('#line_hour_interval_scatterplot');
#                             
#                         today_point.find('.data')
#                             .css('width', '115px')
#                             .empty()
#                             .append('<div class="game-data">'+game.find('.game-count').text()+'. '+game.find('.game_time-MST').text()+'<br/>'+game.find('.participants .away').text()+' @ '+game.find('.participants .home').text()+'</div>');
#                         
#                         var style = today_point.attr('style');
# /*                        
#                         jQuery('<span></span>')
#                             .addClass('adjustment')
#                             .addClass('win-adjust')
#                             .attr('style', style)
#                             .css('left', (game.find('.tip-line-adjusted_count').text() / maxp) * jQuery('#line_hour_interval_scatterplot').width() - left)
#                             .css('bottom', game.find('.tip-line-adjusted_win').text() * jQuery('#line_hour_interval_scatterplot').height() - bottom)
#                             .css('background-color', 'darkblue')
#                             .css('position', 'absolute')
#                             .css('z-index', 1)
#                             .appendTo(today_point)
#                             .hide();
#                             
#                         jQuery('<span></span>')
#                             .addClass('adjustment')
#                             .addClass('loss-adjust')
#                             .attr('style', style)
#                             .css('left', (game.find('.tip-line-adjusted_count').text() / maxp) * jQuery('#line_hour_interval_scatterplot').width() - left)
#                             .css('bottom', game.find('.tip-line-adjusted_loss').text() * jQuery('#line_hour_interval_scatterplot').height() - bottom)
#                             .css('background-color', 'darkblue')
#                             .css('position', 'absolute')
#                             .css('z-index', 1)
#                             .appendTo(today_point)
#                             .hide();
#                             
#                         today_point.hover(function() {jQuery(this).find('.adjustment').show()}, function() {jQuery(this).find('.adjustment').hide()});
# */
#                     });
#                 }
#                 else
#                 {
#                     jQuery('#line_hour_interval_scatterplot .today-point').show()
#                 }
#             }
#             else
#             {
#                 jQuery('#line_hour_interval_scatterplot .today-point').hide()
#             }
#         });
# });
# </script>''')
        
#     def line_movement_scatterplot(self, league):
#         hour_intervals = self.line_movement_by_hour(league)
#         remaining_intervals = self.line_movement_by_remaining(league)
#         
#         max_hour = 0
#         max_remaining = 0
#         points_hour = []
#         points_remaining = []
#         for tip_instance in self.datastore[league]:
#             line_hour_track = [0,0,0]
#             line_remaining_track = [0,0,0]
#             if tip_instance.team_lines:
#                 team_lines = json.loads(tip_instance.team_lines)
#                 date_list = sorted(team_lines, key=lambda x: datetime.strptime(x, '%d.%m.%Y %H:%M'))
#                 
#                 line = None
#                 previous_line = None
#                 for date in date_list:
#                     if line is not None:
#                         previous_line = line
#                     
#                     line = team_lines[date]
#                     date = datetime.strptime(date, '%d.%m.%Y %H:%M')
#                     remaining_hour = (tip_instance.date - date).total_seconds() / 60 / 60
#                     
#                     if previous_line is not None:
#                         if int(line) >= 100 and int(previous_line) < 100:
#                             movement = (int(line) - 100) +  (abs(int(previous_line)) - 100)
#                         elif int(line) < 100 and int(previous_line) >= 100:
#                             movement = (int(line) + 100) - (int(previous_line) - 100)
#                         else:
#                             movement = int(line) - int(previous_line)
#                     else:
#                         continue
#                     
#                     if date.time().hour in hour_intervals:
#                         if str(movement) in hour_intervals[date.time().hour]:
#                             line_hour_track[0] += hour_intervals[date.time().hour][str(movement)][0]
#                             line_hour_track[1] += hour_intervals[date.time().hour][str(movement)][1]
#                             line_hour_track[2] += hour_intervals[date.time().hour][str(movement)][2]
#                     if remaining_hour in remaining_intervals:
#                         if str(movement) in remaining_intervals[remaining_hour]:
#                             line_remaining_track[0] += remaining_intervals[remaining_hour][str(movement)][0]
#                             line_remaining_track[1] += remaining_intervals[remaining_hour][str(movement)][1]
#                             line_remaining_track[2] += remaining_intervals[remaining_hour][str(movement)][2]
#                             
#             line_hour_total = line_hour_track[0] + line_hour_track[1]
#             line_remaining_total = line_remaining_track[0] + line_remaining_track[1]
#             if line_hour_total > 0:
#                 line_hour_percentage = (line_hour_track[0] / float(line_hour_total)) * 100.00
#                 if line_hour_total > max_hour:
#                     max_hour = line_hour_total
#             if line_remaining_total > 0:
#                 line_remaining_percentage = (line_remaining_track[0] / float(line_remaining_total)) * 100.00
#                 if line_remaining_total > max_remaining:
#                     max_remaining = line_remaining_total
#             
#             color = False
#             if tip_instance.score_away is None and tip_instance.score_home is None:
#                 continue
#             elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) > float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) < float(tip_instance.score_home)):
#                 if tip_instance.wettpoint_tip_stake > 0:
#                     color = 'grey'
#                 else:
#                     color = 'black'
#             elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) < float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) > float(tip_instance.score_home)):
#                 if tip_instance.wettpoint_tip_stake > 0:
#                     color = 'red'
#                 else:
#                     color = 'darkred'
#             else:
#                 continue
#             
#             if line_hour_total > 0:
#                 points_hour.append([line_hour_total, line_hour_percentage, color])
#             if line_remaining_total > 0:
#                 points_remaining.append([line_remaining_total, line_remaining_percentage, color])
#                 
#         self.draw_scatterplot('line_movement_hour_scatterplot', points_hour, max_hour)
#         self.draw_scatterplot('line_movement_remaining_scatterplot', points_remaining, max_remaining)
                
#     def draw_scatterplot(self, id, points, maxy):
#         self.html.append("<div id='"+id+"'>")
#         
#         for point in points:
#             total_percentage = (float(point[0])/float(maxy))*100.00
#             self.html.append("<span class='point' style='width: 9px;")
#             self.html.append('background-color:'+point[2]+';')
#             self.html.append('left: '+str( total_percentage )+'%;')
#             self.html.append('bottom: '+str(point[1])+'%;')
#             self.html.append("'>")
#             self.html.append("<div class='data'>")
#             self.html.append("<div class='percentage'>"+"{0:.2f}".format(round(point[1], 2))+"%</div>")
#             self.html.append("<div class='total'>"+str( point[0] )+"</div>")
#             self.html.append("<div class='stake'>"+str( point[3] )+"</div>")
#             self.html.append("<div class='line'>"+str( point[4] )+"</div>")
#             self.html.append("<div class='color' style='display: none;'>"+str( point[2] )+"</div>")
#             self.html.append("<div class='result'>"+str( point[5] )+"</div>")
#             
#             position_x = string.uppercase[int(total_percentage / 10)]
#             position_y = int(point[1] / 5) + 1
#             
#             self.html.append("<div class='interval'>"+position_x + str( position_y )+"</div>")
#             
#             self.html.append("</div>")
#             self.html.append("</span>")
#             
#         self.html.append("</div>")
#         self.scriptheader.append(
# '''<script>
# jQuery(document).ready(function() {
# ''')
#         self.scriptheader.append("var id = '"+id+"';")
#         self.scriptheader.append("jQuery('#'+id).scatter({")
#         self.scriptheader.append(
# '''
#         width: 1200,
#         height: 700,
#         xLabel: 'Total',
#         yLabel: 'Percentage',
#         responsive: true,
# ''')
#         increments = float(maxy) / 5
#         self.scriptheader.append("xUnits: ['0', '"+str(increments)+"', '"+str((increments*2))+"', '"+str((increments*3))+"', '"+str((increments*4))+"', '"+str(maxy)+"'],")
#         self.scriptheader.append(
# '''
#         yUnits: ['0', '.1', '.2', '.3', '.4', '.5', '.6', '.7', '.8', '.9', '1'],
#         rows: 10,
#         columns: 5,
#         subsections: 2,
#     });
# ''')
#         self.scriptheader.append(
# '''
# jQuery('#'+id+' .point').plot();
# jQuery('#'+id+' .point').hover(function() {jQuery(this).find('.data').show()}, function() {jQuery(this).find('.data').hide()});
# 
# jQuery('#'+id).prepend('<div class="intervals"></div>');
# for (var i = 0; i < 200; i++) {
#     var position_x = String.fromCharCode(65 + (i % 10));
#     var position_y = 20 - Math.floor(i / 10);
#     jQuery('#'+id+' .intervals').append('<div id="'+position_x + position_y+'" class="interval"></div>');
# }
# 
# jQuery('#'+id).after('<span id="'+id+'-interval-unit-total" style="background: lightgrey; border: 1px solid black; margin-left: 1270px; margin-top: -300px; padding: 3px; position: absolute;"></span>');
# 
# var max_plus_count = 0;
# var max_neg_count = 0;
# jQuery('#'+id+' .interval').each(function() {
#     var interval = jQuery(this).attr('id')
#     var points = jQuery('#'+id+' .point .data .interval:contains("'+interval+'")')
#     
#     var unit_count = 0;
#     var wins = 0;
#     var losses = 0;
#     points.each(function() {
#         if (jQuery(this).html() != interval || jQuery(this).closest('.point').hasClass('today-point'))
#         {
#             return true;
#         }
#     
#         var result = jQuery(this).closest('.data').find('.result').html()
#         var line = jQuery(this).closest('.data').find('.line').html()
#         
#         if (result == 'W') {
#             wins += 1;
#         
#             if (line >= 100) {
#                 unit_count += line / 100
#             }
#             else {
#                 unit_count += 100 / (line * -1) 
#             }
#         }
#         else
#         {
#             losses += 1
#             unit_count -= 1;
#         }
#         
#         jQuery(this).closest('.point').hover(function() {jQuery('#'+interval).text(unit_count);jQuery('#'+id+'-interval-unit-total').text(interval+' : '+unit_count+' ('+wins+'-'+losses+')');}, function() {jQuery('#'+interval).text('')});
#     });
#     
#     jQuery.data(this, 'unit_count', unit_count)
#     
#     if (unit_count != 0) {
#         if (unit_count > 0) {
#             jQuery(this).css('background-color', 'green')
#             
#             if (unit_count > max_plus_count)
#             {
#                 max_plus_count = unit_count;
#             }
#         }
#         else if (unit_count < 0) {
#             jQuery(this).css('background-color', 'red')
#             
#             if (unit_count < max_neg_count)
#             {
#                 max_neg_count = unit_count;
#             }
#         }
#         
#         unit_count = Math.round(unit_count * 100) / 100
#         jQuery(this).hover(function() {jQuery(this).text(unit_count);jQuery('#'+id+'-interval-unit-total').text(interval+' : '+unit_count+' ('+wins+'-'+losses+')');}, function() {jQuery(this).text('')});
#     }
# });
# 
# var max_opacity = 0.65;
# jQuery('#'+id+' .interval').each(function() {
#     var unit_count = jQuery.data(this, 'unit_count')
#     
#     if (unit_count > 0)
#     {
#         var new_opacity = max_opacity - (Math.ceil((max_plus_count - unit_count) / (max_plus_count / 4)) * 0.1);
#         jQuery(this).css('opacity', new_opacity);
#     }
#     else if (unit_count < 0)
#     {
#         var new_opacity = max_opacity - (Math.ceil((Math.abs(max_neg_count) - Math.abs(unit_count)) / (Math.abs(max_neg_count) / 4)) * 0.1);
#         jQuery(this).css('opacity', new_opacity);
#     }
# });
# 
# jQuery('#'+id).mousemove(function(e) {
#     var relX = e.pageX - jQuery(this).offset().left;
#     var relY = e.pageY - jQuery(this).offset().top;
#     
#     if (relX > 0 && relX <= jQuery(this).width() && relY > 0 && relY <= jQuery(this).height())
#     {
#         var position_x = String.fromCharCode(65 + Math.floor(relX / jQuery(this).width() * 10));
#         var position_y = Math.floor((jQuery(this).height() - relY) / jQuery(this).height() * 100 / 5 + 1)
#     }
# });
# ''')
#         self.scriptheader.append(
# '''});
# </script>''')
        
#     def display_line_by_time(self, league):
#         hour_intervals = self.line_by_time(league)
#         time = datetime.utcnow()
#         
#         limit = 24
#         while limit > 0:
#             add = 24 - limit
#             limit -= 1
#             
#             hour = time.time().hour
#             if hour in hour_intervals:
#                 self.html.append("<div class='line_hour_interval'>")
#                 self.html.append("<div class='hour'><b>%(hour)s</b> (Current Hour +%(add)d)</div>" % locals())
#                 
#                 for line in sorted(hour_intervals[hour].iterkeys()):
#                     results = hour_intervals[hour][line]
#                     
#                     wins = results[0]
#                     losses = results[1]
#                     pushes = results[2]
#                     
#                     self.html.append("<div class='lines'>")
#                     self.html.append("<span class='line'><b>%(line)s</b></span> : " % locals())
#                     self.html.append("<span class='results'>")
#                     self.html.append("<span class='wins'>%(wins)d</span> - " % locals())
#                     self.html.append("<span class='losses'>%(losses)d</span> - " % locals())
#                     self.html.append("<span class='pushes'>%(pushes)d</span>" % locals())
#                     self.html.append("</span>")
#                     self.html.append("</div>")
#                     
#                 self.html.append("</div>")
#                     
#             time = time + timedelta(hours = 1)
        
#     def line_by_time(self, league):
#         if hasattr(self, 'hour_intervals'):
#             return self.hour_intervals
#         else:
#             self.hour_line_interval(league)
#             return self.hour_intervals
        
#     def line_movement_by_hour(self, league):
#         if hasattr(self, 'movement_hour'):
#             return self.movement_hour
#         else:
#             self.hour_line_interval(league)
#             return self.movement_hour
        
#     def line_movement_by_remaining(self, league):
#         if hasattr(self, 'movement_intervals'):
#             return self.movement_intervals
#         else:
#             self.hour_line_interval(league)
#             return self.movement_intervals
    
#     def hour_line_interval(self, league):
#         self.hour_intervals = {}
#         self.movement_hour = {}
#         self.movement_intervals = {}
#         
#         for tip_instance in self.datastore[league]:
#             if tip_instance.team_lines:
#                 team_lines = json.loads(tip_instance.team_lines)
#                 date_list = sorted(team_lines, key=lambda x: datetime.strptime(x, '%d.%m.%Y %H:%M'))
#                 
#                 line = None
#                 previous_line = None
#                 for date in date_list:
#                     if line is not None:
#                         previous_line = line
#                     
#                     line = team_lines[date]
#                     date = datetime.strptime(date, '%d.%m.%Y %H:%M')
#                     
#                     if previous_line is not None:
#                         if int(line) >= 100 and int(previous_line) < 100:
#                             movement = (int(line) - 100) +  (abs(int(previous_line)) - 100)
#                         elif int(line) < 100 and int(previous_line) >= 100:
#                             movement = (int(line) + 100) - (int(previous_line) - 100)
#                         else:
#                             movement = int(line) - int(previous_line)
#                             
#                         remaining_hour = (tip_instance.date - date).total_seconds() / 60 / 60
#                             
#                         if not date.time().hour in self.movement_hour:
#                             self.movement_hour[date.time().hour] = {}
#                         if not remaining_hour in self.movement_intervals:
#                             self.movement_intervals[remaining_hour] = {}
#                         
#                         if not str(movement) in self.movement_hour[date.time().hour]:
#                             self.movement_hour[date.time().hour][str(movement)] = [0, 0, 0]
#                         if not str(movement) in self.movement_intervals[remaining_hour]:
#                             self.movement_intervals[remaining_hour][str(movement)] = [0, 0, 0]
#                         
#                         if tip_instance.score_away is None and tip_instance.score_home is None:
#                             self.movement_hour[date.time().hour][str(movement)][2] += 1
#                         elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) > float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) < float(tip_instance.score_home)):
#                             self.movement_hour[date.time().hour][str(movement)][0] += 1
#                         elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) < float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) > float(tip_instance.score_home)):
#                             self.movement_hour[date.time().hour][str(movement)][1] += 1
#                         else:
#                             self.movement_hour[date.time().hour][str(movement)][2] += 1
#                         if tip_instance.score_away is None and tip_instance.score_home is None:
#                             self.movement_intervals[remaining_hour][str(movement)][2] += 1
#                         elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) > float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) < float(tip_instance.score_home)):
#                             self.movement_intervals[remaining_hour][str(movement)][0] += 1
#                         elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) < float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) > float(tip_instance.score_home)):
#                             self.movement_intervals[remaining_hour][str(movement)][1] += 1
#                         else:
#                             self.movement_intervals[remaining_hour][str(movement)][2] += 1
#                             
#                     if not date.time().hour in self.hour_intervals:
#                         self.hour_intervals[date.time().hour] = {}
#                         
#                     if not line in self.hour_intervals[date.time().hour]:
#                         self.hour_intervals[date.time().hour][line] = [0, 0, 0]
#                     
#                     if tip_instance.score_away is None and tip_instance.score_home is None:
#                         self.hour_intervals[date.time().hour][line][2] += 1
#                     elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) > float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) < float(tip_instance.score_home)):
#                         self.hour_intervals[date.time().hour][line][0] += 1
#                     elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) < float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) > float(tip_instance.score_home)):
#                         self.hour_intervals[date.time().hour][line][1] += 1
#                     else:
#                         self.hour_intervals[date.time().hour][line][2] += 1
