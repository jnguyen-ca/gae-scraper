#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('libs/pytz-2014.7')
sys.path.append('utils')

from google.appengine.ext import webapp
# from google.appengine.api import users, memcache

from datetime import datetime, timedelta
from utils import appvar_util

# import json
import logging
import constants
import teamconstants
import pytz
import models
import frontpage
import tipanalysis

RESULTS_DATETIME_INPUT_NAME = 'results-UTC-datetime'

class TipDisplay(webapp.RequestHandler):
    def post(self):
        self.DATASTORE_PUTS = 0
        self.DATASTORE_READS = 0
        self.datastore = {}
        
        self.html = []
        self.cssheader = []
        self.styleheader = []
        self.jsheader = []
        self.scriptheader = []
        
        self.styleheader.append('<style>')
        
#         self.jsheader.append(
# '''<script src="//ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>''')
        self.styleheader.append(
'''
.league_key {margin: 0 6px 0 0;}
.league_result_totals > span {margin: 0 6px; text-decoration: underline;}
.game_time-MST {width: 12%;}
.game_row {margin: 6px 0;}
.game_row > span {display: inline-block; margin-right: 12px; min-width: 60px;}
.game_row .participants {width: 22%; text-overflow: ellipsis;}
.game_row .scores {width: 9%;}
.game_row .tip-team {text-overflow: ellipsis;}
.game_row .tip-date {width: 10%;}
.game_row .tip-line-adjusted_win, .upcoming_game .tip-line-adjusted_loss {background: lightgrey; text-align: center;}
.game_row .today {font-weight: bold;}
.game_row .closing {color: red;}
.game_row .pending {color: green;}
''')
        self.html.append('<body>')
        
        #TODO: move to tipanalysis
#         # get user to get league dates for tip analysis
#         self.DATASTORE_READS += 1
#         session = models.DisplaySession.gql('WHERE user = :1', users.get_current_user()).get()
#         
#         if session is None:
#             self.DATASTORE_PUTS += 1
#             session = models.DisplaySession()
#             session.user = users.get_current_user()
#         
#         visible_seasons = self.request.get_all('season-display-control')
#         hidden_seasons = self.request.get_all('season-display-hidden-control')
#         
#         display_seasons = {}
#         
#         # sort the given dates into visible vs hidden
#         for season in visible_seasons:
#             values = season.partition('&')
#             if values[0] == season:
#                 continue
#             
#             season_league = values[0]
#             season_dates = values[2]
#             
#             if not season_league in display_seasons:
#                 display_seasons[season_league] = {}
#                 
#             display_seasons[season_league][season_dates] = True
#             
#         for season in hidden_seasons:
#             values = season.partition('&')
#             if values[0] == season:
#                 continue
#             
#             season_league = values[0]
#             season_dates = values[2]
#             
#             if not season_league in display_seasons:
#                 display_seasons[season_league] = {}
#                 
#             display_seasons[season_league][season_dates] = False
#         
#         # update the dates (every time, regardless of change or not)
#         ds_json_string = json.dumps(display_seasons)
#         memcache.set('DisplaySessionCookie', ds_json_string)
#         session.leagues = ds_json_string
        
        # determine display type (list upcoming games vs display day's results)
        display_type = self.request.get(frontpage.INPUT_NAME_TIPDISPLAY_TYPE)
        
        self.DATASTORE_READS += 1
        if frontpage.DISPLAY_VALUE_UPCOMING == display_type:
            # get all games whose scores have not been filled out
            query = models.Tip.gql('WHERE archived != True')
        elif frontpage.DISPLAY_VALUE_RESULTS == display_type:
            results_datetime = self.request.get(RESULTS_DATETIME_INPUT_NAME)
            
            local_timezone = pytz.timezone(constants.TIMEZONE_LOCAL)
            try:
                results_UTC_datetime_start = datetime.strptime(results_datetime, constants.DATETIME_ISO_8601_FORMAT).replace(tzinfo=pytz.utc)
                
                results_datetime = results_UTC_datetime_start.astimezone(local_timezone)
                
                results_UTC_datetime_end = results_datetime.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(pytz.utc)
            except ValueError:
                # get all games from today from earliest to latest
                results_datetime = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(local_timezone)
            
                results_UTC_datetime_start = results_datetime.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
                results_UTC_datetime_end = results_datetime.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(pytz.utc)
            
            previous_results_UTC_datetime_start = results_UTC_datetime_start - timedelta(days=1)
            previous_results_UTC_datetime_end = results_UTC_datetime_end - timedelta(days=1)
            
            query = models.Tip.gql('WHERE date >= :1 AND date <= :2 ORDER BY date ASC', results_UTC_datetime_start, results_UTC_datetime_end)
            
            self.DATASTORE_READS += 1
            tip_instance = query.get()
            if tip_instance is None or tip_instance.archived is not True:
                # if there were no games today that have completed (i.e. no results) then get yesterday's games
                query = models.Tip.gql('WHERE date >= :1 AND date <= :2 ORDER BY date ASC', previous_results_UTC_datetime_start, previous_results_UTC_datetime_end)
                
                previous_results_UTC_datetime_start = previous_results_UTC_datetime_start - timedelta(days=1)
                previous_results_UTC_datetime_end = previous_results_UTC_datetime_end - timedelta(days=1)
                
            self.html.append('''
                <form action="/display" method="post">
                    <input type="hidden" value="%s" name="%s">
                    <button type="submit" value="%s" name="%s">Previous Day</button>
                </form>
                ''' % (
                       previous_results_UTC_datetime_start.strftime(constants.DATETIME_ISO_8601_FORMAT),
                       RESULTS_DATETIME_INPUT_NAME,
                       frontpage.DISPLAY_VALUE_RESULTS,
                       frontpage.INPUT_NAME_TIPDISPLAY_TYPE,
                )
             )
        else:
            logging.error('Unsupported display type: %s' % (display_type))
            raise Exception('Unsupported display type: %s' % (display_type))
        
        not_archived_tips_values_by_sport_league = {}
        unsorted_sport_league_date = []
        for tip_instance in query:
            self.DATASTORE_READS += 1
            
            # if displaying results, then only retrieve games which have completed
            if (
                frontpage.DISPLAY_VALUE_RESULTS == display_type 
                and tip_instance.archived is not True
            ):
                break
            
            # store tips by sport and league
            if tip_instance.game_sport not in not_archived_tips_values_by_sport_league:
                not_archived_tips_values_by_sport_league[tip_instance.game_sport] = {}
            if tip_instance.game_league not in not_archived_tips_values_by_sport_league[tip_instance.game_sport]:
                not_archived_tips_values_by_sport_league[tip_instance.game_sport][tip_instance.game_league] = []
            
            not_archived_tips_values_by_sport_league[tip_instance.game_sport][tip_instance.game_league].append(tip_instance)
            
            # create a list with the earliest event date by league for later sorting
            initialize = True
            for index, sport_league_date in enumerate(unsorted_sport_league_date):
                if sport_league_date[1] == tip_instance.game_league:
                    initialize = False
                    if tip_instance.date < sport_league_date[2]:
                        unsorted_sport_league_date[index][2] = tip_instance.date
            
            # first entry in list of earliest event date
            if initialize is True:
                unsorted_sport_league_date.append([tip_instance.game_sport, tip_instance.game_league, tip_instance.date])
        
        try:
            # sort leagues based on league's next game
            sorted_sport_league_date = sorted(unsorted_sport_league_date, key=lambda x: x[2])
        except IndexError:
            logging.info('Nothing to display')
            self.html.append('<h1>Oops, nothing to display!</h1>')
        else:
            # display tips in the order of league's first game date
            for sport_league_date in sorted_sport_league_date:
                sport_key = sport_league_date[0]
                league_key = sport_league_date[1]
                
                # sort all the league's tips
                tips_values = sorted(not_archived_tips_values_by_sport_league[sport_key][league_key], key=lambda x: x.date)
                
                wettpoint_table = 'http://www.forum.'+constants.WETTPOINT_FEED+'/fr_toptipsys.php?cat='+appvar_util.get_sport_names_appvar()[sport_key]['wettpoint']
                
                # display all non-archived tips
                self.html.append("<div class='league_header'><b class='league_key'>%s</b>" % (league_key))
                
                if frontpage.DISPLAY_VALUE_UPCOMING == display_type:
                    self.html.append("<a href='%s'>Table</a>" % (wettpoint_table))
                    self.list_next_games(tips_values)
                elif frontpage.DISPLAY_VALUE_RESULTS == display_type:
                    index = len(self.html)
                    moneyline_totals, spread_totals, total_totals = self.list_game_results(tips_values)
                    
                    league_result_totals = '<span class="money_line_result_totals">Money Line: %d-%d-%d</span>' % (moneyline_totals[0], moneyline_totals[1], moneyline_totals[2])
                    league_result_totals += '<span class="spread_result_totals">Spread: %d-%d-%d</span>' % (spread_totals[0], spread_totals[1], spread_totals[2])
                    league_result_totals += '<span class="total_result_totals">Total: %d-%d-%d</span>' % (total_totals[0], total_totals[1], total_totals[2])
                    
                    self.html.insert(index, '<span class="league_result_totals">%s</span>' % (league_result_totals))
                    
                self.html.append("</div>")
        
        self.html.append('</body></html>')    
        self.styleheader.append('</style>')
            
        html = []
        html.append('''<html><head>''')
        html.append("".join(self.cssheader))
        html.append("".join(self.jsheader))
        html.append("".join(self.scriptheader))
        html.append("".join(self.styleheader))
        html.append('</head>')
        html.append("".join(self.html))
        self.response.out.write("".join(html))
        
#         session.last_login = datetime.utcnow()
#         self.DATASTORE_PUTS += 1
#         session.put()
        
        logging.debug('Total Reads: '+str(self.DATASTORE_READS)+', Total Writes: '+str(self.DATASTORE_PUTS))
        
    def list_next_games(self, not_archived_tips):
        next_games_html = []
        
        local_timezone = pytz.timezone(constants.TIMEZONE_LOCAL)
        current_datetime = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(local_timezone)
        
        game_count = 0
        next_games_html.append('<div class="league_games upcoming_games">')
        for tip_instance in not_archived_tips:
            game_count += 1
            game_row_id = tip_instance.game_league.lower().replace(' ','_')+'-'+str(game_count)
            
            game_time = tip_instance.date.replace(tzinfo=pytz.utc).astimezone(local_timezone)
            
            date_class = 'game_time-MST'
            if current_datetime.date().day == game_time.date().day:
                date_class += ' today'
            elif (game_time.date() - current_datetime.date()).days == 1:
                date_class += ' tomorrow'
            if game_time - current_datetime < timedelta(hours=2):
                date_class += ' closing'
            if tip_instance.elapsed == True:
                date_class += ' pending'
            
            game_time = game_time.strftime('%B-%d %I:%M%p')
            
            team_away, team_away_id = teamconstants.get_team_datastore_name_and_id(tip_instance.game_sport, tip_instance.game_league, tip_instance.game_team_away)
            team_home, team_home_id = teamconstants.get_team_datastore_name_and_id(tip_instance.game_sport, tip_instance.game_league, tip_instance.game_team_home)
            
            team_away = tip_instance.game_team_away
            team_home = tip_instance.game_team_home
            
            wettpoint_h2h_link = None
            if (
                tip_instance.game_sport not in appvar_util.get_h2h_excluded_sports_appvar() 
                and team_away_id is not None 
                and team_home_id is not None
            ):
                wettpoint_h2h_link = 'http://'+appvar_util.get_sport_names_appvar()[tip_instance.game_sport]['wettpoint']+'.'+constants.WETTPOINT_FEED+'/h2h/'+team_home_id+'-'+team_away_id+'.html'
            
            wettpoint_stake = tip_instance.wettpoint_tip_stake
            wettpoint_team = tip_instance.wettpoint_tip_team
            wettpoint_total = tip_instance.wettpoint_tip_total
            
            latest_line, latest_team_date = tipanalysis.get_line(tip_instance.team_lines)
            spread_no, latest_spread_date = tipanalysis.get_line(tip_instance.spread_no)
            total_no, latest_total_date = tipanalysis.get_line(tip_instance.total_no)
            
            latest_date = None
            if latest_team_date is not None:
                latest_date = latest_team_date
            elif latest_spread_date is not None:
                latest_date = latest_spread_date
            elif latest_total_date is not None:
                latest_date = latest_total_date
                
            if latest_date is not None:
                latest_date = latest_date.replace(tzinfo=pytz.utc).astimezone(local_timezone)
                latest_date = latest_date.strftime('%Y/%m/%d %I:%M%p')
            else:
                if ' ' in date_class:
                    self.styleheader.append('#%(game_row_id) {background-color: yellow;}')
                    
            next_games_html.append('<div id="%(game_row_id)s" class="game_row upcoming_game">' % locals())
            next_games_html.append('<span class="game-count" style="min-width: 16px;">%(game_count)d</span>' % locals())
            next_games_html.append('<span class="%(date_class)s">%(game_time)s</span>' % locals())
            next_games_html.append('<span class="participants"><span class="away">%(team_away)s</span><span class="team-separator"> @ </span><span class="home">%(team_home)s</span></span>' % locals())
            next_games_html.append('<span class="tip-stake">%(wettpoint_stake)s</span>' % locals())
            next_games_html.append('<span class="tip-team">%(wettpoint_team)s</span>' % locals())
            next_games_html.append('<span class="tip-money_line">%(latest_line)s</span>' % locals())
            next_games_html.append('<span class="tip-spread_no">%(spread_no)s</span>' % locals())
            next_games_html.append('<span class="tip-date">%(latest_date)s</span>' % locals())
            next_games_html.append('<span class="tip-total">%(wettpoint_total)s</span>' % locals())
            next_games_html.append('<span class="tip-total_no">%(total_no)s</span>' % locals())
            if wettpoint_h2h_link is not None:
                next_games_html.append('<span class="h2h-link"><a href="%(wettpoint_h2h_link)s">H2H</a></span>' % locals())
            next_games_html.append('</div>')
        
        next_games_html.append('</div>')
        
        self.html.append("".join(next_games_html))
        
    def list_game_results(self, archived_tips):
        local_timezone = pytz.timezone(constants.TIMEZONE_LOCAL)
        
        moneyline_win_loss_draw = [0,0,0]
        spread_win_loss_draw = [0,0,0]
        total_win_loss_draw = [0,0,0]
        
        game_count = 0
        self.html.append('<div class="league_games game_results">')
        for tip_instance in archived_tips:
            league_key = tip_instance.game_league
            
            game_count += 1
            game_row_id = league_key.lower().replace(' ','_')+'-'+str(game_count)
            
            game_time = tip_instance.date.replace(tzinfo=pytz.utc).astimezone(local_timezone).strftime('%B-%d %I:%M%p')
            team_away = tip_instance.game_team_away
            team_home = tip_instance.game_team_home
            
            wettpoint_stake = tip_instance.wettpoint_tip_stake
            wettpoint_team = tip_instance.wettpoint_tip_team
            wettpoint_total = tip_instance.wettpoint_tip_total
            
            latest_line = tipanalysis.get_line(tip_instance.team_lines)[0]
            spread_no = tipanalysis.get_line(tip_instance.spread_no)[0]
            total_no = tipanalysis.get_line(tip_instance.total_no)[0]
            
            score_home = tip_instance.score_home
            score_away = tip_instance.score_away
            
            moneyline_result = None
            if wettpoint_team is not None and len(wettpoint_team) == 1:
                if models.TIP_SELECTION_TEAM_HOME == wettpoint_team:
                    moneyline_result = tipanalysis.calculate_event_score_result(league_key, score_home, score_away, draw=tipanalysis.BET_RESULT_LOSS)
                elif models.TIP_SELECTION_TEAM_AWAY == wettpoint_team:
                    moneyline_result = tipanalysis.calculate_event_score_result(league_key, score_away, score_home, draw=tipanalysis.BET_RESULT_LOSS)
                elif models.TIP_SELECTION_TEAM_DRAW == wettpoint_team:
                    moneyline_result = tipanalysis.calculate_event_score_result(league_key, score_away, score_home, draw=tipanalysis.BET_RESULT_WIN)
            
            if tipanalysis.BET_RESULT_WIN == moneyline_result:
                moneyline_win_loss_draw[0] += 1
            elif tipanalysis.BET_RESULT_LOSS == moneyline_result:
                moneyline_win_loss_draw[1] += 1
            else:
                moneyline_win_loss_draw[2] += 1
            
            spread_result = None
            if wettpoint_team is not None:
                if models.TIP_SELECTION_TEAM_HOME in wettpoint_team:
                    spread_result = tipanalysis.calculate_event_score_result(league_key, score_home, score_away, spread_modifier=spread_no)
                elif models.TIP_SELECTION_TEAM_AWAY in wettpoint_team:
                    spread_result = tipanalysis.calculate_event_score_result(league_key, score_away, score_home, spread_modifier=spread_no)
            
            if tipanalysis.BET_RESULT_WIN == spread_result:
                spread_win_loss_draw[0] += 1
            elif tipanalysis.BET_RESULT_LOSS == spread_result:
                spread_win_loss_draw[1] += 1
            else:
                spread_win_loss_draw[2] += 1
            
            if score_away is None or score_home is None:
                total_score = None
            else:
                total_score = float(tipanalysis.strip_score(league_key, score_away)) + float(tipanalysis.strip_score(league_key, score_home))
                
            total_result = None
            if models.TIP_SELECTION_TOTAL_OVER == wettpoint_total:
                total_result = tipanalysis.calculate_event_score_result(league_key, total_score, total_no)
            else:
                total_result = tipanalysis.calculate_event_score_result(league_key, total_no, total_score)
                
            if tipanalysis.BET_RESULT_WIN == total_result:
                total_win_loss_draw[0] += 1
            elif tipanalysis.BET_RESULT_LOSS == total_result:
                total_win_loss_draw[1] += 1
            else:
                total_win_loss_draw[2] += 1
                
            self.html.append('<div id="%(game_row_id)s" class="game_row game_result">' % locals())
            self.html.append('<span class="game-count" style="min-width: 16px;">%(game_count)d</span>' % locals())
            self.html.append('<span class="game_time-MST">%(game_time)s</span>' % locals())
            self.html.append('<span class="participants"><span class="away">%(team_away)s</span><span class="team-separator"> @ </span><span class="home">%(team_home)s</span></span>' % locals())
            self.html.append('<span class="scores"><span class="score_away">%(score_away)s</span><span class="team-separator"> @ </span><span class="score_home">%(score_home)s</span></span>' % locals())
            self.html.append('<span class="tip-stake">%(wettpoint_stake)s</span>' % locals())
            self.html.append('<span class="tip-team">%(wettpoint_team)s</span>' % locals())
            self.html.append('<span class="tip-money_line">%(latest_line)s</span>' % locals())
            self.html.append('<span class="result-money_line">%(moneyline_result)s</span>' % locals())
            self.html.append('<span class="tip-spread_no">%(spread_no)s</span>' % locals())
            self.html.append('<span class="result-spread">%(spread_result)s</span>' % locals())
            self.html.append('<span class="tip-total">%(wettpoint_total)s</span>' % locals())
            self.html.append('<span class="tip-total_no">%(total_no)s</span>' % locals())
            self.html.append('<span class="result-total">%(total_result)s</span>' % locals())
            self.html.append('</div>')
            
        self.html.append('</div>')
        
        return moneyline_win_loss_draw, spread_win_loss_draw, total_win_loss_draw
