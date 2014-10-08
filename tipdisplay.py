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
import teamconstants

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
                
#                 if not league_key in self.datastore:
#                     continue
                        
                self.list_next_games(league_key)
#                 self.display_wettpoint_results(league_key)
        
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
            team_away_aliases, team_away_id = teamconstants.get_team_aliases(tip_instance.game_sport, league, team_away)
            team_home = tip_instance.game_team_home
            team_home_aliases, team_home_id = teamconstants.get_team_aliases(tip_instance.game_sport, league, team_home)
            
            wettpoint_h2h_link = 'http://'+constants.SPORTS[tip_instance.game_sport]['wettpoint']+'.'+constants.WETTPOINT_FEED+'/h2h/'+team_home_id+'-'+team_away_id+'.html'
            
            wettpoint_stake = tip_instance.wettpoint_tip_stake
            wettpoint_team = tip_instance.wettpoint_tip_team
            wettpoint_total = tip_instance.wettpoint_tip_total
            
#             line_hour_track = [0,0,0]
#             adjust_count = 0
            
            latest_date = False
            latest_line = False
            if tip_instance.team_lines:
                sorted_team_line_dates = sorted(tip_instance.team_lines, key=lambda x: datetime.strptime(x, '%d.%m.%Y %H:%M'))
                latest_date = datetime.strptime(sorted_team_line_dates[-1], '%d.%m.%Y %H:%M')
                latest_line = tip_instance.team_lines[sorted_team_line_dates[-1]]
#                 for date, line in json.loads(tip_instance.team_lines).iteritems():
#                     date = datetime.strptime(date, '%d.%m.%Y %H:%M')
#                     if not latest_date:
#                         latest_date = date
#                         latest_line = line
#                         
#                     if date > latest_date:
#                         latest_date = date
#                         latest_line = line
#                         
# #                     if date.time().hour in hour_intervals:
# #                         if line in hour_intervals[date.time().hour]:
# #                             line_hour_track[0] += hour_intervals[date.time().hour][line][0]
# #                             line_hour_track[1] += hour_intervals[date.time().hour][line][1]
# #                             line_hour_track[2] += hour_intervals[date.time().hour][line][2]
#                             
# #                             adjust_count += 1
            
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
            self.html.append('<span class="h2h-link"><a href="%(wettpoint_h2h_link)s">H2H</a></span>' % locals())
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
