#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import constants

import sys
sys.path.append('libs/'+constants.LIB_DIR_PYTZ)
sys.path.append('utils')

from google.appengine.ext import webapp, ndb
# from google.appengine.api import users, memcache

from datetime import datetime, timedelta
from utils import appvar_util, sys_util

# import json
import logging
import teamconstants
import pytz
import models
import frontpage
import tipanalysis

RESULTS_DATETIME_INPUT_NAME = 'results-UTC-datetime'

class TipDisplay(webapp.RequestHandler):
    INPUT_NAME_REQUEST_TYPE = 'request-type'
    INPUT_NAME_TIP_KEY = 'tip-key'
    INPUT_NAME_GAME_COUNT = 'game-count'
    INPUT_NAME_ROT_AWAY = 'rot-away'
    INPUT_NAME_ROT_HOME = 'rot-home'
    INPUT_NAME_DATE = 'tip-datetime'
    INPUT_NAME_TEAM_AWAY = 'participant-away'
    INPUT_NAME_TEAM_HOME = 'participant-home'
    INPUT_NAME_SCORE_AWAY = 'score-away'
    INPUT_NAME_SCORE_HOME = 'score-home'
    INPUT_NAME_STATUS_ELAPSED = 'status-elapsed'
    INPUT_NAME_STATUS_ARCHIVED = 'status-archived'
    
    REQUEST_TYPE_EDIT_TIP = 'edit-tip'
    REQUEST_TYPE_DELETE_TIP = 'delete-tip'
    
    __ERROR_SEPARATOR = ';'
    
    def post(self):
        if sys_util.is_ajax(self.request):
            request_type = self.request.get(self.INPUT_NAME_REQUEST_TYPE)
            
            logging.debug('Request : (%s)' % (request_type))
            if request_type == self.REQUEST_TYPE_EDIT_TIP:
                self._handle_edit_tip_request()
            elif request_type == self.REQUEST_TYPE_DELETE_TIP:
                logging.info('Deleting tip: '+self.request.get(self.INPUT_NAME_DATE)+' '+self.request.get(self.INPUT_NAME_TEAM_AWAY)+' @ '+self.request.get(self.INPUT_NAME_TEAM_HOME))
                ndb.Key(urlsafe=self.request.get(self.INPUT_NAME_TIP_KEY)).delete()
            else:
                # invalid ajax request
                logging.warning('Invalid request made!')
                
            return
        
        self.DATASTORE_PUTS = 0
        self.DATASTORE_READS = 0
        self.datastore = {}
        
        self.html = []
        self.cssheader = []
        self.styleheader = []
        self.jsheader = []
        self.scriptheader = []
        
        self.styleheader.append('<style>')
        
        self.jsheader.append(
'''
<script src="//ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>
<script src="/javascript/modules/tipdisplay.js"></script>
''')
        
        self.styleheader.append(
'''
.updated-highlight {background: #FFFFBC;}
.error-highlight {outline: 2px inset red; background: #FFF9F9;}
.tip_controls-hover {background: #ECECEC;}
.styleless-button {background: none; border: none;}
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
.game_row .tip-controls {float:right;}
.game_row .today {font-weight: bold;}
.game_row .closing {color: red;}
.game_row .pending {color: green;}
.game_row .tip-key, .game_row .rot_num, .game_row .tip-status, .game_row .tip-datetime {display: none;}
.upcoming_game .scores {display: none;}
.game_result .tip-date, .game_result .h2h-link {display: none;}
''')
        self.html.append('<body>')
        
        self.html.append('''
            <div id="form_templates" class="hidden" style="display:none;">
                <form class="%s-form" style="display:none;">
                    <input type="hidden" name="%s" value="%s">
                    <input type="hidden" name="%s" value="" class="tip-data">
                    <input type="hidden" name="%s" value="" class="tip-data">
                    <input type="hidden" name="%s" value="" class="tip-data">
                    <input type="hidden" name="%s" value="" class="tip-data">
                    <input type="submit" value="Submit">
                </form>
                <form class="%s-form">
                    <input type="hidden" name="%s" value="%s">
                    <input type="hidden" name="%s" value="" class="tip-data">
                    <input type="hidden" name="%s" value="" class="tip-data">
                    <input type="hidden" name="%s" value="" class="tip-data editable datetime-data">
                    <input type="hidden" name="%s" value="" class="tip-data editable integer-data">
                    <input type="hidden" name="%s" value="" class="tip-data editable integer-data">
                    <input type="hidden" name="%s" value="" class="tip-data editable string-data">
                    <input type="hidden" name="%s" value="" class="tip-data editable string-data">
                    <input type="hidden" name="%s" value="" class="tip-data editable string-data">
                    <input type="hidden" name="%s" value="" class="tip-data editable string-data">
                    <input type="hidden" name="%s" value="" class="tip-data editable boolean-data">
                    <input type="hidden" name="%s" value="" class="tip-data editable boolean-data">
                    <input type="submit" value="Submit">
                </form>
            </div>
            ''' % (
                   self.REQUEST_TYPE_DELETE_TIP,
                   # delete form
                   self.INPUT_NAME_REQUEST_TYPE, self.REQUEST_TYPE_DELETE_TIP,
                   self.INPUT_NAME_TIP_KEY,
                   self.INPUT_NAME_DATE,
                   self.INPUT_NAME_TEAM_AWAY,
                   self.INPUT_NAME_TEAM_HOME,
                   # edit form
                   self.REQUEST_TYPE_EDIT_TIP,
                   self.INPUT_NAME_REQUEST_TYPE, self.REQUEST_TYPE_EDIT_TIP,
                   self.INPUT_NAME_TIP_KEY,
                   self.INPUT_NAME_GAME_COUNT,
                   self.INPUT_NAME_DATE,
                   self.INPUT_NAME_ROT_AWAY,
                   self.INPUT_NAME_ROT_HOME,
                   self.INPUT_NAME_TEAM_AWAY,
                   self.INPUT_NAME_TEAM_HOME,
                   self.INPUT_NAME_SCORE_AWAY,
                   self.INPUT_NAME_SCORE_HOME,
                   self.INPUT_NAME_STATUS_ELAPSED,
                   self.INPUT_NAME_STATUS_ARCHIVED,
            )
        )
        
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
                continue
            
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
                tips_values = sorted(not_archived_tips_values_by_sport_league[sport_key][league_key], key=lambda x: (x.date, x.rot_home))
                
                wettpoint_table = 'http://www.forum.'+constants.WETTPOINT_FEED+'/fr_toptipsys.php?cat='+appvar_util.get_sport_names_appvar()[sport_key][appvar_util.APPVAR_KEY_WETTPOINT]
                
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
        
        game_count = 0
        next_games_html.append('<div class="league_games upcoming_games">')
        for tip_instance in not_archived_tips:
            game_count += 1
            next_games_html.append(self.display_game_row(tip_instance, game_count))
        
        next_games_html.append('</div>')
        
        self.html.append("".join(next_games_html))
        
    def list_game_results(self, archived_tips):
        moneyline_win_loss_draw = [0,0,0]
        spread_win_loss_draw = [0,0,0]
        total_win_loss_draw = [0,0,0]
        
        game_count = 0
        self.html.append('<div class="league_games game_results">')
        for tip_instance in archived_tips:
            game_count += 1
            
            spread_no = tipanalysis.get_line(tip_instance.spread_no)[0]
            total_no = tipanalysis.get_line(tip_instance.total_no)[0]
            
            moneyline_result = self._get_tip_tipanalysis_result(
                                                                analysis_type='moneyline', 
                                                                selection=tip_instance.wettpoint_tip_team, 
                                                                league_key=tip_instance.game_league, 
                                                                score_home=tip_instance.score_home, 
                                                                score_away=tip_instance.score_away,
                                                                )
            
            if tipanalysis.BET_RESULT_WIN == moneyline_result:
                moneyline_win_loss_draw[0] += 1
            elif tipanalysis.BET_RESULT_LOSS == moneyline_result:
                moneyline_win_loss_draw[1] += 1
            else:
                moneyline_win_loss_draw[2] += 1
            
            spread_result = self._get_tip_tipanalysis_result(
                                                             analysis_type='spread', 
                                                             selection=tip_instance.wettpoint_tip_team, 
                                                             league_key=tip_instance.game_league, 
                                                             score_home=tip_instance.score_home, 
                                                             score_away=tip_instance.score_away, 
                                                             result_no=spread_no
                                                             )
            
            if tipanalysis.BET_RESULT_WIN == spread_result:
                spread_win_loss_draw[0] += 1
            elif tipanalysis.BET_RESULT_LOSS == spread_result:
                spread_win_loss_draw[1] += 1
            else:
                spread_win_loss_draw[2] += 1
            
            total_result = self._get_tip_tipanalysis_result(
                                                             analysis_type='total', 
                                                             selection=tip_instance.wettpoint_tip_total, 
                                                             league_key=tip_instance.game_league, 
                                                             score_home=tip_instance.score_home, 
                                                             score_away=tip_instance.score_away, 
                                                             result_no=total_no
                                                             )
                
            if tipanalysis.BET_RESULT_WIN == total_result:
                total_win_loss_draw[0] += 1
            elif tipanalysis.BET_RESULT_LOSS == total_result:
                total_win_loss_draw[1] += 1
            else:
                total_win_loss_draw[2] += 1
                
            self.html.append(self.display_game_row(tip_instance, game_count))
            
        self.html.append('</div>')
        
        return moneyline_win_loss_draw, spread_win_loss_draw, total_win_loss_draw
    
    def _handle_edit_tip_request(self):
        request_tip_key_string = self.request.get(self.INPUT_NAME_TIP_KEY)
        request_tip_game_count = self.request.get(self.INPUT_NAME_GAME_COUNT)
        request_tip_date = self.request.get(self.INPUT_NAME_DATE, None)
        request_tip_rot_away = self.request.get(self.INPUT_NAME_ROT_AWAY, None)
        request_tip_rot_home = self.request.get(self.INPUT_NAME_ROT_HOME, None)
        request_tip_team_away = self.request.get(self.INPUT_NAME_TEAM_AWAY, None)
        request_tip_team_home = self.request.get(self.INPUT_NAME_TEAM_HOME, None)
        request_tip_score_away = self.request.get(self.INPUT_NAME_SCORE_AWAY, None)
        request_tip_score_home = self.request.get(self.INPUT_NAME_SCORE_HOME, None)
        request_tip_status_elapsed = self.request.get(self.INPUT_NAME_STATUS_ELAPSED, None)
        request_tip_status_archived = self.request.get(self.INPUT_NAME_STATUS_ARCHIVED, None)
        
        error_encountered = False
        
        tip_instance = ndb.Key(urlsafe=request_tip_key_string).get()
        if tip_instance is None:
            logging.warning('Edit tip resulted in invalid tip key string!')
            self.response.set_status(400)
            return
        
        logging_string = 'Modified: %s %s (%i) @ %s (%i), %s-%s; Elapsed: %s, Archived: %s' % (
                                                                                                tip_instance.date.strftime(constants.DATETIME_ISO_8601_FORMAT),
                                                                                                tip_instance.game_team_away,
                                                                                                tip_instance.rot_away,
                                                                                                tip_instance.game_team_home,
                                                                                                tip_instance.rot_home,
                                                                                                tip_instance.score_away,
                                                                                                tip_instance.score_home,
                                                                                                tip_instance.elapsed,
                                                                                                tip_instance.archived,
                                                                                                )
                                                                                                
        if request_tip_date is not None:
            # convert to datetime and UTC
            local_timezone = pytz.timezone(constants.TIMEZONE_LOCAL)
            utc_request_datetime = local_timezone.localize(datetime.strptime(request_tip_date, '%m-%d-%Y %I:%M%p')).astimezone(pytz.utc).replace(tzinfo=None)
            
            logging_string += "\n"+'Datetime: '+utc_request_datetime.strftime(constants.DATETIME_ISO_8601_FORMAT)+' ('+request_tip_date+')'
            tip_instance.date = utc_request_datetime
        
        if request_tip_rot_away is not None:
            if not request_tip_rot_away:
                self.response.out.write(self.INPUT_NAME_ROT_AWAY+self.__ERROR_SEPARATOR)
                logging.debug('Error encountered: Rotation # Away being removed.')
                error_encountered = True
            else:
                logging_string += "\n"+'Rot# Away: '+str(request_tip_rot_away)
                tip_instance.rot_away = int(request_tip_rot_away)
        if request_tip_rot_home is not None:
            if not request_tip_rot_home:
                self.response.out.write(self.INPUT_NAME_ROT_HOME+self.__ERROR_SEPARATOR)
                logging.debug('Error encountered: Rotation # Home being removed.')
                error_encountered = True
            else:
                logging_string += "\n"+'Rot# Home: '+str(request_tip_rot_home)
                tip_instance.rot_home = int(request_tip_rot_home)
            
        if request_tip_team_away is not None:
            datastore_name = teamconstants.get_team_datastore_name_and_id(tip_instance.game_sport, tip_instance.game_league, request_tip_team_away)[0]
            if datastore_name is None:
                logging.warning('Invalid team name edited: '+request_tip_team_away)
            elif datastore_name != request_tip_team_away:
                logging.warning('Alias edited instead of key name: '+request_tip_team_away+' (Datastore: '+datastore_name)
                
            logging_string += "\n"+'Team away name: '+request_tip_team_away
            tip_instance.game_team_away = request_tip_team_away
        if request_tip_team_home is not None:
            datastore_name = teamconstants.get_team_datastore_name_and_id(tip_instance.game_sport, tip_instance.game_league, request_tip_team_home)[0]
            if datastore_name is None:
                logging.warning('Invalid team name edited: '+request_tip_team_home)
            elif datastore_name != request_tip_team_home:
                logging.warning('Alias edited instead of key name: '+request_tip_team_home+' (Datastore: '+datastore_name)
                
            logging_string += "\n"+'Team home name: '+request_tip_team_home
            tip_instance.game_team_home = request_tip_team_home
            
        if request_tip_score_away is not None:
            #TODO: add validators to models (see ndb properties)
            score_away = request_tip_score_away
            if not score_away:
                score_away = None
                
            logging_string += "\n"+'Score away: '+str(score_away)+' ('+request_tip_score_away+')'
            tip_instance.score_away = score_away
        if request_tip_score_home is not None:
            score_home = request_tip_score_home
            if not score_home:
                score_home = None
            
            logging_string += "\n"+'Score home: '+str(score_home)+' ('+request_tip_score_home+')'
            tip_instance.score_home = score_home
            
        if request_tip_status_elapsed is not None:
            # only accept valid values
            if request_tip_status_elapsed == 'true':
                status_elapsed = True
            elif request_tip_status_elapsed == 'false':
                status_elapsed = None
            else:
                logging.debug('Error encountered: Invalid elapsed status.')
                error_encountered = True
            
            # a tip that has not elapsed cannot be archived
            if not status_elapsed:
                # invalid if archived status is being set
                if request_tip_status_archived is not None and request_tip_status_archived != 'false':
                    logging.debug('Error encountered: Tip not elapsed but being set to archived.')
                    error_encountered = True
                # invalid if tip is already archived and not being changed
                elif tip_instance.archived and request_tip_status_archived != 'false':
                    logging.debug('Error encountered: Tip not elapsed but archived.')
                    error_encountered = True
                    
            if not error_encountered:
                logging_string += "\n"+'Elapsed status: '+str(status_elapsed)+' ('+request_tip_status_elapsed+')'
                tip_instance.elapsed = status_elapsed
        if request_tip_status_archived is not None:
            # only accept valid values
            if request_tip_status_archived == 'true':
                status_archived = True
            elif request_tip_status_archived == 'false':
                status_archived = None
            else:
                logging.debug('Error encountered: Invalid archived status.')
                error_encountered = True
            
            # a tip that has not elapsed cannot be archived
            if status_archived and not tip_instance.elapsed:
                # since this field is being changed after the elapsed field
                # we can simply check what the elapsed status is on the Tip itself since it would have already been changed
                logging.debug('Error encountered: Tip archived but not elapsed.')
                error_encountered = True
        
            if not error_encountered:
                logging_string += "\n"+'Archived status: '+str(status_archived)+' ('+request_tip_status_archived+')'
                tip_instance.archived = status_archived
        
        # special exception: if a Tip is archived it has to have a score and if it can't have a score unless it's archived
        if tip_instance.archived:
            if not tip_instance.score_away or not tip_instance.score_home:
                logging.debug('Error encountered: Tip archived but scores not set.')
                error_encountered = True
        else:
            if tip_instance.score_away or tip_instance.score_home:
                logging.debug('Error encountered: Scores set but Tip not archived.')
                error_encountered = True
        
        #TODO: validate on frontend before submit that scores are filled if archived or not if not, and elapsed/archived pair
        if error_encountered:
            self.response.set_status(400)
            return
        
        tip_instance.put()
        logging.info(logging_string)
        
        self.response.out.write(self.display_game_row(tip_instance, int(request_tip_game_count)))
        return
    
    def display_game_row(self, tip_instance, game_count, game_row_actions=['edit','delete']):
        scores_exist = False
        if tip_instance.score_away and tip_instance.score_home:
            scores_exist = True
        
        game_row_id = tip_instance.game_league.lower().replace(' ','_')+'-'+str(game_count)
        game_status = 'game_result' if tip_instance.archived else 'upcoming_game'
        game_row_html = '<div id="%s" class="game_row %s">' % (game_row_id, game_status)
        
        game_row_html += '<span class="%s">%s</span>' % (self.INPUT_NAME_TIP_KEY, tip_instance.key.urlsafe())
            
        game_row_html += '<span class="%s" style="min-width: 16px;">%d</span>' % (self.INPUT_NAME_GAME_COUNT, game_count)
        
        local_timezone = pytz.timezone(constants.TIMEZONE_LOCAL)
        current_datetime = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(local_timezone)
        tip_datetime = tip_instance.date.replace(tzinfo=pytz.utc).astimezone(local_timezone)
            
        datetime_class = 'game_time-MST'
        if tip_instance.archived is not True:
            if current_datetime.date().day == tip_datetime.date().day:
                datetime_class += ' today'
            elif (tip_datetime.date() - current_datetime.date()).days == 1:
                datetime_class += ' tomorrow'
            if tip_datetime - current_datetime < timedelta(hours=2):
                datetime_class += ' closing'
            if tip_instance.elapsed is True:
                datetime_class += ' pending'
        
        game_row_html += '<span class="%s">%s</span>' % (datetime_class, tip_datetime.strftime('%B-%d %I:%M%p'))
        game_row_html += '<span class="%s %s" name="Datetime">%s</span>' % (datetime_class, self.INPUT_NAME_DATE, tip_datetime.strftime('%m-%d-%Y %I:%M%p'))
                
        game_row_html += '<span class="participants">'
        game_row_html += '<span class="away %s" name="Away Team">%s</span>' % (self.INPUT_NAME_TEAM_AWAY, tip_instance.game_team_away)
        game_row_html += '<span class="rot_num %s" name="Away Rot #">%s</span>' % (self.INPUT_NAME_ROT_AWAY, tip_instance.rot_away)
        game_row_html += '<span class="team-separator"> @ </span>'
        game_row_html += '<span class="home %s" name="Home Team">%s</span>' % (self.INPUT_NAME_TEAM_HOME, tip_instance.game_team_home)
        game_row_html += '<span class="rot_num %s" name="Home Rot #">%s</span>' % (self.INPUT_NAME_ROT_HOME, tip_instance.rot_home)
        game_row_html += '</span>'
        
        score_away = score_home = ''
        if scores_exist is True:
            score_away = tip_instance.score_away
            score_home = tip_instance.score_home
        game_row_html += '<span class="scores">'
        game_row_html += '<span class="score_away %s" name="Score Away">%s</span>' % (self.INPUT_NAME_SCORE_AWAY, score_away)
        game_row_html += '<span class="team-separator"> @ </span>'
        game_row_html += '<span class="score_home %s" name="Score Home">%s</span>' % (self.INPUT_NAME_SCORE_HOME, score_home)
        game_row_html += '</span>'
        
        display_wettpoint_tip_team = tip_instance.wettpoint_tip_team
        display_wettpoint_tip_total = tip_instance.wettpoint_tip_total
        display_wettpoint_tip_stake = tip_instance.wettpoint_tip_stake
        
        #TODO: replace this list
        if tip_instance.game_sport in ['Baseball']:
            analysis_object = tipanalysis.TipAnalysis()
            series_wettpoint_tips = analysis_object.calculate_series_wettpoint_tips(tip_instance)
            if series_wettpoint_tips:
                display_wettpoint_tip_team = series_wettpoint_tips[0]
                display_wettpoint_tip_total = series_wettpoint_tips[1]
                display_wettpoint_tip_stake = series_wettpoint_tips[2]
            
            self.DATASTORE_READS += analysis_object.datastore_reads
        
        game_row_html += '<span class="tip-stake">%s</span>' % (display_wettpoint_tip_stake)
        game_row_html += '<span class="tip-team">%s</span>' % (display_wettpoint_tip_team)    
        
        latest_moneyline, latest_moneyline_datetime = tipanalysis.get_line(tip_instance.team_lines)
        latest_spread_no, latest_spread_datetime = tipanalysis.get_line(tip_instance.spread_no)
        latest_total_no, latest_total_datetime = tipanalysis.get_line(tip_instance.total_no)
        
        latest_odds_datetime = None
        if latest_moneyline is not None:
            latest_odds_datetime = latest_moneyline_datetime
        elif latest_spread_datetime is not None:
            latest_odds_datetime = latest_spread_datetime
        elif latest_total_datetime is not None:
            latest_odds_datetime = latest_total_datetime
            
        if latest_odds_datetime is not None:
            latest_odds_datetime = latest_odds_datetime.replace(tzinfo=pytz.utc).astimezone(local_timezone)
            latest_odds_datetime = latest_odds_datetime.strftime('%Y/%m/%d %I:%M%p')
        
        game_row_html += '<span class="tip-money_line">%s</span>' % (latest_moneyline)
        
        if scores_exist is True:
            moneyline_result = self._get_tip_tipanalysis_result(
                                                                analysis_type='moneyline', 
                                                                selection=tip_instance.wettpoint_tip_team, 
                                                                league_key=tip_instance.game_league, 
                                                                score_home=tip_instance.score_home, 
                                                                score_away=tip_instance.score_away,
                                                                )
            
            spread_result = self._get_tip_tipanalysis_result(
                                                             analysis_type='spread', 
                                                             selection=tip_instance.wettpoint_tip_team, 
                                                             league_key=tip_instance.game_league, 
                                                             score_home=tip_instance.score_home, 
                                                             score_away=tip_instance.score_away, 
                                                             result_no=latest_spread_no
                                                             )
            
            total_result = self._get_tip_tipanalysis_result(
                                                             analysis_type='total', 
                                                             selection=tip_instance.wettpoint_tip_total, 
                                                             league_key=tip_instance.game_league, 
                                                             score_home=tip_instance.score_home, 
                                                             score_away=tip_instance.score_away, 
                                                             result_no=latest_total_no
                                                             )
        
        if scores_exist is True:
            game_row_html += '<span class="result-money_line">%s</span>' % (moneyline_result)
            
        game_row_html += '<span class="tip-spread_no">%s</span>' % (latest_spread_no)
            
        if scores_exist is True:
            game_row_html += '<span class="result-spread">%s</span>' % (spread_result)
        
        game_row_html += '<span class="tip-date">%s</span>' % (latest_odds_datetime)
            
        game_row_html += '<span class="tip-total">%s</span>' % (display_wettpoint_tip_total)
            
        game_row_html += '<span class="tip-total_no">%s</span>' % (latest_total_no)
        
        if scores_exist is True:
            game_row_html += '<span class="result-total">%s</span>' % (total_result)
        
        team_away_id = teamconstants.get_team_datastore_name_and_id(tip_instance.game_sport, tip_instance.game_league, tip_instance.game_team_away)[1]
        team_home_id = teamconstants.get_team_datastore_name_and_id(tip_instance.game_sport, tip_instance.game_league, tip_instance.game_team_home)[1]
        
        wettpoint_h2h_link = None
        if (
            tip_instance.game_sport not in appvar_util.get_h2h_excluded_sports_appvar() 
            and team_away_id is not None 
            and team_home_id is not None
        ):
            wettpoint_h2h_link = 'http://'+appvar_util.get_sport_names_appvar()[tip_instance.game_sport][appvar_util.APPVAR_KEY_WETTPOINT]+'.'+constants.WETTPOINT_FEED+'/h2h/'+team_home_id+'-'+team_away_id+'.html'
            
        
        if wettpoint_h2h_link is not None:
            game_row_html += '<span class="h2h-link"><a href="%s">H2H</a></span>' % (wettpoint_h2h_link)
        
        if len(game_row_actions):
            game_row_html += '<span class="tip-controls">'
            if 'edit' in game_row_actions:
                game_row_html += '<input type="button" class="styleless-button" name="%s" value="Edit">' % (self.REQUEST_TYPE_EDIT_TIP)
            if 'delete' in game_row_actions:
                game_row_html += '<input type="button" class="styleless-button" name="%s" value="Delete">' % (self.REQUEST_TYPE_DELETE_TIP)
            game_row_html += '</span>'
            
        game_row_html += '<span class="tip-status %s" name="Elapsed Status">%s</span>' % (self.INPUT_NAME_STATUS_ELAPSED, 'true' if tip_instance.elapsed is True else 'false')
        game_row_html += '<span class="tip-status %s" name="Archived Status">%s</span>' % (self.INPUT_NAME_STATUS_ARCHIVED, 'true' if tip_instance.archived is True else 'false')
        
        game_row_html += '</div>'
        return game_row_html
    
    def _get_tip_tipanalysis_result(self, analysis_type, selection, league_key, score_home, score_away, result_no=None):
        result = None
        if analysis_type == 'moneyline':
            if selection is not None and len(selection) == 1:
                if models.TIP_SELECTION_TEAM_HOME == selection:
                    result = tipanalysis.calculate_event_score_result(league_key, score_home, score_away, draw=tipanalysis.BET_RESULT_LOSS)
                elif models.TIP_SELECTION_TEAM_AWAY == selection:
                    result = tipanalysis.calculate_event_score_result(league_key, score_away, score_home, draw=tipanalysis.BET_RESULT_LOSS)
                elif models.TIP_SELECTION_TEAM_DRAW == selection:
                    result = tipanalysis.calculate_event_score_result(league_key, score_away, score_home, draw=tipanalysis.BET_RESULT_WIN)
        elif analysis_type == 'spread':
            result = None
            if selection is not None:
                if models.TIP_SELECTION_TEAM_HOME in selection:
                    result = tipanalysis.calculate_event_score_result(league_key, score_home, score_away, spread_modifier=result_no)
                elif models.TIP_SELECTION_TEAM_AWAY in selection:
                    result = tipanalysis.calculate_event_score_result(league_key, score_away, score_home, spread_modifier=result_no)
        elif analysis_type == 'total':
            if score_away is None or score_home is None:
                total_score = None
            else:
                total_score = float(tipanalysis.strip_score(league_key, score_away)) + float(tipanalysis.strip_score(league_key, score_home))
                
            result = None
            if models.TIP_SELECTION_TOTAL_OVER == selection:
                result = tipanalysis.calculate_event_score_result(league_key, total_score, result_no)
            else:
                result = tipanalysis.calculate_event_score_result(league_key, result_no, total_score)
                
        return result