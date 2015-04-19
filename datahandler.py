#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

class DataHandler(object):
    datastore_writes = 0
    datastore_reads = 0
    
    def __init__(self):
        pass
    
    def update_tips(self):
        pass

import logging
import constants

class DatastoreException(constants.ApplicationException):
    """Base exception for datastore operations"""
    def __init__(self, message):
        super(DatastoreException, self).__init__(message, constants.MAIL_TITLE_DATASTORE_ERROR)

def _game_details_string(tip_instance):
    return '%s : %s (%d) @ %s (%d) [%s / %s]' % (
                                               tip_instance.date.strftime(constants.DATETIME_ISO_8601_FORMAT),
                                               tip_instance.game_team_away,
                                               tip_instance.rot_away,
                                               tip_instance.game_team_home,
                                               tip_instance.rot_home,
                                               tip_instance.game_sport,
                                               tip_instance.game_league,
                                             )

import sys
sys.path.append('utils')
sys.path.append('libs/'+constants.LIB_DIR_PYTZ)

from google.appengine.ext import ndb

from datetime import datetime, timedelta
from utils import sys_util, memcache_util, appvar_util, requests_util

import re
import json
import pytz
import scraper
import teamconstants
import models

_WETTPOINT_DATETIME_FORMAT = '%d.%m.%Y %H:%M'

_TIME_CRON_SCHEDULE_MINUTES_APART = 30
_TIME_ERROR_MARGIN_MINUTES_BEFORE = -65
_TIME_ERROR_MARGIN_MINUTES_AFTER = 90
_TIME_ERROR_MARGIN_HOURS_GAME_MATCH = 12

class TipData(DataHandler):
    def __init__(self, bookieDict={}):
        self._not_previously_elapsed_tips = None
        self._not_previously_archived_tips = None
        self._sports_requiring_wettpoint_update = None
        self.utc_task_start = datetime.utcnow()
        self.new_or_updated_tips = []
        self.bookieDict = bookieDict
        
        for bookieObj in self.bookieDict.values():
            self.new_or_updated_tips += bookieObj.new_or_updated_tips
    
    @property
    def sports_requiring_wettpoint_update(self):
        if self._sports_requiring_wettpoint_update is None:
            self.update_properties()
        return self._sports_requiring_wettpoint_update
    
    @property
    def not_previously_elapsed_tips(self):
        if self._not_previously_elapsed_tips is None:
            self.update_properties()
        return self._not_previously_elapsed_tips
    
    @property
    def not_previously_archived_tips(self):
        if self._not_previously_archived_tips is None:
            self._not_previously_archived_tips = {}
            
            self.datastore_reads += 1
            query = models.Tip.gql('WHERE elapsed = True AND archived != True')
            for tip_instance in query:
                self.datastore_reads += 1
                
                sport_key = tip_instance.game_sport
                league_key = tip_instance.game_league
                
                if sport_key not in self._not_previously_archived_tips:
                    self._not_previously_archived_tips[sport_key] = {}
                if league_key not in self._not_previously_archived_tips[sport_key]:
                    self._not_previously_archived_tips[sport_key][league_key] = []
                    
                self._not_previously_archived_tips[sport_key][league_key].append(tip_instance)
                
        return self._not_previously_archived_tips
    
    def update_properties(self):
        self._not_previously_elapsed_tips = {}
        self._sports_requiring_wettpoint_update = {}
        
        wettpoint_tables_memcache = memcache_util.get(memcache_util.MEMCACHE_KEY_SCRAPER_WETTPOINT_TABLE)
        
        # want to check all non-elapsed tips in the datastore so that elapse statuses can be updated
        # this prevents a object from being possibly missed and staying unelapsed forever
        self.datastore_reads += 1
        query = models.Tip.gql('WHERE elapsed != True')
        for tip_instance in query:
            self.datastore_reads += 1
            
            sport_key = tip_instance.game_sport
            league_key = tip_instance.game_league
            
            # keep in a sorted dict so that functions requiring the tips have an easier time parsing
            if sport_key not in self._not_previously_elapsed_tips:
                self._not_previously_elapsed_tips[sport_key] = {}
            if league_key not in self._not_previously_elapsed_tips[sport_key]:
                self._not_previously_elapsed_tips[sport_key][league_key] = []
            
            # update elapse status
            minutes_until_start = divmod((tip_instance.date - self.utc_task_start).total_seconds(), 60)[0]
            if minutes_until_start < 0:
                tip_instance.elapsed = True
            
            #TODO: store updated tip instances in a seperate list so that only updated ones get committed (use less writes)
            # store updated tip in property (not yet committed to datastore)
            self._not_previously_elapsed_tips[sport_key][league_key].append(tip_instance)
            
            # determine which sports should make a wettpoint request to be updated
            
            # off the board tips do not require wettpoint scrapes
            if teamconstants.is_game_off_the_board(tip_instance):
                continue
                
            if tip_instance.key in self.new_or_updated_tips:
                if sport_key not in self._sports_requiring_wettpoint_update:
                    self._sports_requiring_wettpoint_update[sport_key] = 'Checking '+sport_key+' due to new tip'
            elif sport_key not in self._sports_requiring_wettpoint_update:
                if minutes_until_start <= 180:
                    self._sports_requiring_wettpoint_update[sport_key] = 'Checking '+sport_key+' starting within 3 hours'
                elif tip_instance.wettpoint_tip_stake is None:
                    if wettpoint_tables_memcache and sport_key in wettpoint_tables_memcache:
                        if wettpoint_tables_memcache[sport_key]['first_event_time'] is not False:
                            last_event_UTC_time = pytz.timezone(constants.TIMEZONE_WETTPOINT).localize(datetime.strptime(wettpoint_tables_memcache[sport_key]['first_event_time'], _WETTPOINT_DATETIME_FORMAT)).astimezone(pytz.utc)
                        
                            if ((last_event_UTC_time - timedelta(minutes=15)) - datetime.utcnow().replace(tzinfo=pytz.utc)).total_seconds() <= 0:
                                self._sports_requiring_wettpoint_update[sport_key] = 'Checking '+sport_key+' for updated table ('+last_event_UTC_time.strftime(_WETTPOINT_DATETIME_FORMAT)+')'
                    else:
                        self._sports_requiring_wettpoint_update[sport_key] = 'Checking '+sport_key+' due to missing memcache key'
                        
    def update_tips(self):
        # TODO: move Tip looping and general scraper functionality outside WettpointData
        # not completely necessary since WettpointData will only ever act on WettpointScraper info
        # but would like it to be consistent with how the score updating (further on) works
        
        # wettpoint stuff
        wettpointData = WettpointData(self)
        wettpointData.update_tips()
        
        self.datastore_reads += wettpointData.datastore_reads
        self.datastore_writes += wettpointData.datastore_writes
        
        # line stuff
        self._update_odds()
        
        # scores stuff
        try:
            self._update_scores()
        except requests_util.HTTP_EXCEPTION_TUPLE as request_error:
            logging.warning('scoreboard down')
            logging.warning(request_error)
        
        sys_util.send_all_mail()
        
        update_tips = []
        for sport_key in appvar_util.get_sport_names_appvar():
            for league_key in appvar_util.get_league_names_appvar()[sport_key]:
                if sport_key in self.not_previously_elapsed_tips and league_key in self.not_previously_elapsed_tips[sport_key]:
                    update_tips += self.not_previously_elapsed_tips[sport_key][league_key]
                if sport_key in self.not_previously_archived_tips and league_key in self.not_previously_archived_tips[sport_key]:
                    update_tips += self.not_previously_archived_tips[sport_key][league_key]
                
        self.datastore_writes += len(update_tips)
        ndb.put_multi(update_tips)
    
    @sys_util.function_timer()
    def _update_odds(self):
        for sport_key in appvar_util.get_sport_names_appvar():
            # don't need to update if there are no games to update
            if sport_key not in self.not_previously_elapsed_tips:
                continue
            for league_key in appvar_util.get_league_names_appvar()[sport_key]:
                if league_key not in self.not_previously_elapsed_tips[sport_key]:
                    continue
                for tip_instance_index, tip_instance in enumerate(self.not_previously_elapsed_tips[sport_key][league_key]):
                    # don't update odds if the game has already elapsed
                    if tip_instance.elapsed is True:
                        continue
                    
                    if (
                        tip_instance.wettpoint_tip_stake is None 
                        and tip_instance.wettpoint_tip_team is None 
                        and tip_instance.wettpoint_tip_total is None
                    ):
                        # tip stake hasn't been determined yet, move on
                        continue
                    
                    minutes_until_start = divmod((tip_instance.date - self.utc_task_start).total_seconds(), 60)[0]
                    
                    # games more than 24 hours from start, only fill lines 3 times daily
                    if minutes_until_start >= 1440:
                        if self.utc_task_start.hour % 9 != 0 or self.utc_task_start.minute >= 30:
                            continue
                    elif minutes_until_start > 720:
                        if self.utc_task_start.minute >= 30:
                            continue
                    
                    # if tip does not have corresponding event in any of the bookies then it may have been ppd
                    event_is_missing = True
                    bookies_are_down = True
                    for bookieKey, bookieObj in self.bookieDict.iteritems():
                        '@type bookieObj: BookieData'
                        if bookieObj.status == bookieObj.STATUS_ERROR:
                            # bookie scraper failed, move onto next bookie
                            continue
                        
                        bookies_are_down = False
                        
                        '@type eventData: scraper.BookieScrapeData'
                        eventData = bookieObj.get_event_from_key(tip_instance.key)
                        if eventData is None:
                            continue
                        
                        event_is_missing = False
                        
                        line_date = eventData.line_datetime
                        # round line_date to nearest minute for store
                        if line_date.second >= 30:
                            line_date += timedelta(minutes=1)
                        line_date = line_date.strftime(models.TIP_HASH_DATETIME_FORMAT)
                        
                        # TODO: add support for multiple bookie lines
                        ############# TOTALS (O/U) UPDATE #############
                        # get the correct total dict (i.e. either the over or the under)
                        if tip_instance.wettpoint_tip_total == models.TIP_SELECTION_TOTAL_OVER:
                            event_total = eventData.total_over
                        else:
                            event_total = eventData.total_under
                        
                        # add newest total points number
                        if event_total[eventData.LINE_KEY_POINTS] is not None:
                            if tip_instance.total_no:
                                hash1 = json.loads(tip_instance.total_no)
                            else:
                                hash1 = {}
                                
                            hash1[line_date] = event_total[eventData.LINE_KEY_POINTS]
                            tip_instance.total_no = json.dumps(hash1)
                        
                        # add newest total odds number
                        if event_total[eventData.LINE_KEY_ODDS] is not None:
                            if tip_instance.total_lines:
                                hash1 = json.loads(tip_instance.total_lines)
                            else:
                                hash1 = {}
                                
                            hash1[line_date] = event_total[eventData.LINE_KEY_ODDS]
                            tip_instance.total_lines = json.dumps(hash1)
                        
                        ############# MONEYLINE (1X2) UPDATE #############
                        if (
                            eventData.moneyline_away is not None
                            or eventData.moneyline_home is not None
                            or eventData.moneyline_draw is not None
                        ):
                            if tip_instance.team_lines:
                                hash1 = json.loads(tip_instance.team_lines)
                            else:
                                hash1 = {}
                            
                            # if a team has been specified by wettpoint, store that team's odds
                            # otherwise store the favourite's odds (which can then be used or thrown away depending on
                            # what the wettpoint team actually ends up being)
                            if tip_instance.wettpoint_tip_team is not None:
                                moneyline = ''
                                try:
                                    # go through the 1X2 string to get all the specified odds
                                    for i in tip_instance.wettpoint_tip_team:
                                        if i == models.TIP_SELECTION_TEAM_HOME:
                                            moneyline += eventData.moneyline_home + models.TIP_SELECTION_LINE_SEPARATOR
                                        elif i == models.TIP_SELECTION_TEAM_DRAW:
                                            moneyline += eventData.moneyline_draw + models.TIP_SELECTION_LINE_SEPARATOR
                                        elif i == models.TIP_SELECTION_TEAM_AWAY:
                                            moneyline += eventData.moneyline_away + models.TIP_SELECTION_LINE_SEPARATOR
                                except TypeError:
                                    raise DatastoreException('Type error occured when creating moneyline string (most likely a NoneType) for '+_game_details_string(tip_instance))
                                
                                # if sport has draws and draw odds are not specified in wettpoint team, attach the draw odds to the end
                                if (
                                    eventData.moneyline_draw 
                                    and len(tip_instance.wettpoint_tip_team) < 2
                                ):
                                    # in the rare case that the draw was the wettpoint team, add the home team odds
                                    if tip_instance.wettpoint_tip_team == models.TIP_SELECTION_TEAM_DRAW:
                                        moneyline += eventData.moneyline_home
                                    else:
                                        moneyline += eventData.moneyline_draw
                                
                                # strip the line separator at the end of the string
                                moneyline = moneyline.rstrip(models.TIP_SELECTION_LINE_SEPARATOR)
                                hash1[line_date] = moneyline
                            else:
                                moneyline = ''
                                # determine whether home or away is the favourite (in case of pick'em tie, home team)
                                if float(eventData.moneyline_away) < float(eventData.moneyline_home):
                                    tip_instance.wettpoint_tip_team = models.TIP_SELECTION_TEAM_AWAY
                                    moneyline = eventData.moneyline_away
                                else:
                                    tip_instance.wettpoint_tip_team = models.TIP_SELECTION_TEAM_HOME
                                    moneyline = eventData.moneyline_home
                                    
                                if eventData.moneyline_draw:
                                    moneyline += models.TIP_SELECTION_LINE_SEPARATOR+eventData.moneyline_draw
                                    
                                hash1[line_date] = moneyline
                                    
                            tip_instance.team_lines = json.dumps(hash1)
                            
                        ############# SPREAD UPDATE #############
                        event_spread_home_points = eventData.spread_home[eventData.LINE_KEY_POINTS]
                        event_spread_home_odds = eventData.spread_home[eventData.LINE_KEY_ODDS]
                        event_spread_away_points = eventData.spread_away[eventData.LINE_KEY_POINTS]
                        event_spread_away_odds = eventData.spread_away[eventData.LINE_KEY_ODDS]
                        
                        if (
                            event_spread_home_points is not None 
                            and event_spread_home_odds is not None
                            and event_spread_away_points is not None
                            and event_spread_away_odds is not None  
                        ):
                            if tip_instance.spread_no:
                                hash1 = json.loads(tip_instance.spread_no)
                            else:
                                hash1 = {}
                                
                            if tip_instance.spread_lines:
                                hash2 = json.loads(tip_instance.spread_lines)
                            else:
                                hash2 = {}
                                
                            if tip_instance.wettpoint_tip_team is not None:
                                # if team has home (1) or is draw use home spread
                                if tip_instance.wettpoint_tip_team.find(models.TIP_SELECTION_TEAM_HOME) != -1 or tip_instance.wettpoint_tip_team == models.TIP_SELECTION_TEAM_DRAW:
                                    hash1[line_date] = event_spread_home_points
                                    hash2[line_date] = event_spread_home_odds
                                elif tip_instance.wettpoint_tip_team.find(models.TIP_SELECTION_TEAM_AWAY) != -1:
                                    hash1[line_date] = event_spread_away_points
                                    hash2[line_date] = event_spread_away_odds
                            else:
                                # get the favourite by comparing spread points (if pick'em use odds with home being default)
                                if (
                                    float(event_spread_away_points) < float(event_spread_home_points) 
                                    or (
                                        float(event_spread_away_points) == float(event_spread_home_points) 
                                        and float(event_spread_away_odds) < float(event_spread_home_odds)
                                    )
                                ):
                                    tip_instance.wettpoint_tip_team = models.TIP_SELECTION_TEAM_AWAY
                                    hash1[line_date] = event_spread_away_points
                                    hash2[line_date] = event_spread_away_odds
                                elif (
                                      float(event_spread_away_points) > float(event_spread_home_points) 
                                      or (
                                          float(event_spread_away_points) == float(event_spread_home_points) 
                                          and float(event_spread_away_odds) >= float(event_spread_home_odds)
                                      )
                                ):
                                    tip_instance.wettpoint_tip_team = models.TIP_SELECTION_TEAM_HOME
                                    hash1[line_date] = event_spread_home_points
                                    hash2[line_date] = event_spread_home_odds
                                
                            tip_instance.spread_no = json.dumps(hash1)
                            tip_instance.spread_lines = json.dumps(hash2)
                    
                    if event_is_missing is not True:
                        self.not_previously_elapsed_tips[sport_key][league_key][tip_instance_index] = tip_instance
                    elif bookies_are_down is not True:
                        # either game was taken off the board (for any number of reasons) - could be temporary
                        # or game is a duplicate (something changed that i didn't account for)
                        mail_message = 'Missing from bookies: '+_game_details_string(tip_instance)+"\n"
                        sys_util.add_mail(constants.MAIL_TITLE_MISSING_EVENT, mail_message, logging='warning')
    
    @sys_util.function_timer()             
    def _update_scores(self):
        for sport_key, sport_leagues in appvar_util.get_league_names_appvar().iteritems():
            if sport_key not in self.not_previously_archived_tips:
                continue
            
            xscoreScraper = scraper.XscoresScraper(sport_key)
            
            for league_key in sport_leagues:
                if league_key not in self.not_previously_archived_tips[sport_key]:
                    continue
                
                scoresProScraper = scraper.ScoresProScraper(sport_key, league_key)
                
                for tip_instance_index, tip_instance in enumerate(self.not_previously_archived_tips[sport_key][league_key]):
                    if tip_instance.game_sport == 'Handball':
                        score_scraper = scoresProScraper
                    else:
                        score_scraper = xscoreScraper
                    
                    '@type score_row: scraper.ScoreRowData'
                    for score_row in score_scraper.scrape(tip_instance.date):
                        if not teamconstants.is_league_alias('scoreboard', tip_instance.game_sport, tip_instance.game_league, score_row.league):
                            continue
                        
                        # row should have same time (30 minute error window) and team names
                        time_difference = score_row.datetime - score_scraper.convert_utc_to_local(tip_instance.date)
                        time_difference_minutes = divmod(time_difference.total_seconds(), 60)[0]
                        
                        if (
                            _TIME_ERROR_MARGIN_MINUTES_BEFORE <= time_difference_minutes 
                            and _TIME_ERROR_MARGIN_MINUTES_AFTER >= time_difference_minutes
                        ):
                            home_team = teamconstants.get_team_datastore_name_and_id(tip_instance.game_sport, tip_instance.game_league, score_row.team_home)[0]
                            away_team = teamconstants.get_team_datastore_name_and_id(tip_instance.game_sport, tip_instance.game_league, score_row.team_away)[0]
                        
                            if (
                                tip_instance.game_team_away == away_team 
                                and tip_instance.game_team_home == home_team
                            ):
                                if not score_scraper.is_complete(score_row.status):
                                    break
                                
                                if score_row.final_score_home and score_row.final_score_away:
                                    tip_instance.score_home = score_row.final_score_home
                                    tip_instance.score_away = score_row.final_score_away
                                    if score_row.extra_time:
                                        tip_instance.score_home += ' ('+score_row.regulation_score_home+')'
                                        tip_instance.score_away += ' ('+score_row.regulation_score_away+')'
                                        
                                tip_instance.elapsed = True
                                tip_instance.archived = True
                                    
                                self.not_previously_archived_tips[sport_key][league_key][tip_instance_index] = tip_instance
                                break
                            elif tip_instance.game_team_home == home_team:
                                mail_message = ('Scoreboard table has matched a Tip date and home team.'
                                                ' Possible AWAY team name missing for '+_game_details_string(tip_instance)+
                                                ' Scoreboard table match is %s @ %s' % (str(away_team), str(home_team)))
                                sys_util.add_mail(constants.MAIL_TITLE_TEAM_ERROR, mail_message, logging='warning')
                            elif tip_instance.game_team_away == away_team:
                                mail_message = ('Scoreboard table has matched a Tip date and away team.'
                                                ' Possible HOME team name missing for '+_game_details_string(tip_instance)+
                                                ' Scoreboard table match is %s @ %s' % (str(away_team), str(home_team)))
                                sys_util.add_mail(constants.MAIL_TITLE_TEAM_ERROR, mail_message, logging='warning')
                                
                    if (
                        tip_instance.archived != True 
                        and (datetime.utcnow() - tip_instance.date).total_seconds() > 18000 # 5 hours
                    ):
                        mail_message = 'Game missing from scoreboard - '+_game_details_string(tip_instance)+"\n"
                        sys_util.add_mail(constants.MAIL_TITLE_TIP_WARNING, mail_message, logging='warning')

class WettpointData(DataHandler):
    wettpoint_timezone = pytz.timezone(constants.TIMEZONE_WETTPOINT)
    _WETTPOINT_TABLE_MINUTES_BEFORE_EVENT_EXPIRE = 15
    _TIME_CRON_SCHEDULE_MINUTES_APART = 30
    
    def __init__(self, tipData):
        self.tipData = tipData
        self.wettpoint_tables_memcache = memcache_util.get(memcache_util.MEMCACHE_KEY_SCRAPER_WETTPOINT_TABLE)
        self.valid_sports = None
        self.set_valid_sports(tipData.sports_requiring_wettpoint_update)
        
    def set_valid_sports(self, valid_sports):
        # first add all sports that need to be checked
        # any sports that are missing from the memcache will automatically be checked
        if self.wettpoint_tables_memcache:
            for sport_key in appvar_util.get_sport_names_appvar():
                if sport_key not in valid_sports and sport_key in self.wettpoint_tables_memcache:
                    sport_wettpoint_memcache = self.wettpoint_tables_memcache[sport_key]
                    
                    sport_updated = sport_wettpoint_memcache['time_updated']
                    sport_minutes_between_checks = sport_wettpoint_memcache['minutes_between_checks']
                    
                    # check a sport if it meets any of the following conditions:
                    # - any wettpoint data got changed during the previous run
                    if sport_wettpoint_memcache['tip_changed'] is True:
                        valid_sports[sport_key] = 'Checking '+sport_key+' due to last change'
                    # - wettpoint scrapes were interuppted due to limit being reach during previous run
                    elif sport_wettpoint_memcache['h2h_limit_reached'] is True:
                        valid_sports[sport_key] = 'Checking '+sport_key+' due to H2H limit reached'
                    # - the last scrape is older than the specified minutes_between_checks
                    elif divmod((datetime.utcnow() - datetime.strptime(sport_updated, _WETTPOINT_DATETIME_FORMAT)).total_seconds(), 60)[0] > sport_minutes_between_checks:
                        valid_sports[sport_key] = 'Checking '+sport_key+' due to expiration ('+str(round(sport_minutes_between_checks))+'min since '+sport_updated+')'
                elif sport_key not in self.wettpoint_tables_memcache:
                    valid_sports[sport_key] = 'Checking '+sport_key+' due to missing memcache key'
        else:
            self.wettpoint_tables_memcache = {}
            logging.debug('Checking all sports due to memcache expiration')
            for sport_key in appvar_util.get_sport_names_appvar():
                valid_sports[sport_key] = None
        
        # only want to do a wettpoint request if there actually exists a tip for the sport
        empty_sports_to_remove = []
        for sport_key, debug_message in valid_sports.iteritems():
            if sport_key not in self.tipData.not_previously_elapsed_tips:
                empty_sports_to_remove.append(sport_key)
            elif debug_message:
                logging.debug(debug_message)
        
        for sport_key in empty_sports_to_remove:
            valid_sports.pop(sport_key, None)
        
        self.valid_sports = valid_sports
        return self.valid_sports
    
    @sys_util.function_timer()
    def update_tips(self):
        # go through all our sports
        for sport_key in appvar_util.get_sport_names_appvar():
            # if no tips to update in this sport or sport is not up to be updated, move on
            if sport_key not in self.tipData.not_previously_elapsed_tips or sport_key not in self.valid_sports:
                continue
            
            # get the sport table
            wettpointScraper = scraper.WettpointScraper(sport_key)
            try:
                sport_wettpoint_table = wettpointScraper.sport_table
                # get the time immediately after a scrape for converting the table times
                wettpoint_current_time = datetime.utcnow()
                wettpoint_current_date = wettpoint_current_time.replace(tzinfo=pytz.utc).astimezone(self.wettpoint_timezone).strftime('%d.%m.%Y')
            except requests_util.HTTP_EXCEPTION_TUPLE as request_error:
                logging.warning('wettpoint tables down')
                logging.warning(request_error)
                return
            
            # get the last event time so next scrape can possibly occur when all current events have expired (i.e. table completely refreshes)
            if not sport_wettpoint_table:
                last_event_time = False
            else:
                last_event_time = re.sub('[^0-9\.\s:]', '', sport_wettpoint_table[-1].time_string)
                
            # format the tip time to a standard
            if last_event_time is not False and not re.match('\d{2}\.\d{2}\.\d{4}', last_event_time):
                last_event_time = wettpoint_current_date + ' ' + last_event_time
            
            # update or set the memcache entry, will be updated as we go through the tips
            self.wettpoint_tables_memcache[sport_key] = {
                                                    'first_event_time' : last_event_time,
                                                    'time_updated' : wettpoint_current_time.strftime(_WETTPOINT_DATETIME_FORMAT),
                                                    'tip_changed' : False,
                                                    'minutes_between_checks' : 120,
                                                    'h2h_limit_reached' : False,
                                                    }
            
            # sometimes the H2H site can be down, don't want to continuously request it if it is
            H2H_sport_issue = False
            for league_key in appvar_util.get_league_names_appvar()[sport_key]:
                if league_key not in self.tipData.not_previously_elapsed_tips[sport_key]:
                    # no pending games in this league, move on
                    continue
                
                possible_earlier_games = []
                if sport_key in self.tipData.not_previously_archived_tips and league_key in self.tipData.not_previously_archived_tips[sport_key]:
                    possible_earlier_games += self.tipData.not_previously_archived_tips[sport_key][league_key]
                possible_earlier_games += self.tipData.not_previously_elapsed_tips[sport_key][league_key]
                
                # finally go through each tip (by league) to update wettpoint info
                for tip_instance_index, tip_instance in enumerate(self.tipData.not_previously_elapsed_tips[sport_key][league_key]):
                    tip_stake_changed = False
                    minutes_until_start = divmod((tip_instance.date - wettpoint_current_time).total_seconds(), 60)[0]
                    
                    if (
                        tip_instance.wettpoint_tip_stake is not None 
                        and tip_instance.wettpoint_tip_stake >= 1.0
                    ):
                        # don't want to change it if it's already elapsed
                        if tip_instance.elapsed is True:
                            continue
                    
                    # determine if the data for the teams have likely been updated (i.e. this is the next game and current games are finished)
                    matchup_finalized = self._matchup_data_finalized(tip_instance.game_sport, [tip_instance.game_team_away, tip_instance.game_team_home], tip_instance.date, possible_earlier_games)
                    
                    # has the wettpoint tip been changed
                    tip_change_created = False
                    tip_change_object = None
                    
                    # empty table (either failed to retrieve or no tips listed)
                    if not sport_wettpoint_table:
                        if tip_instance.wettpoint_tip_stake is None:
                            tip_stake_changed = True
                            tip_instance.wettpoint_tip_stake = 0.0
                        
                    # go through the events listed
                    '@type tip_row: scraper.WettpointRowData'
                    for tip_row in sport_wettpoint_table:
                        # standard information to determine if tip is of interest
                        league_name = tip_row.league
                        
                        # format the tip time to a standard
                        game_time = re.sub('[^0-9\.\s:]', '', tip_row.time_string)
                        if not re.match('\d{2}\.\d{2}\.\d{4}', game_time):
                            game_time = wettpoint_current_date + ' ' + game_time
                        
                        # set game time to UTC    
                        game_time = self.wettpoint_timezone.localize(datetime.strptime(game_time, _WETTPOINT_DATETIME_FORMAT)).astimezone(pytz.utc)
                        row_minutes_past_start = divmod((game_time - tip_instance.date.replace(tzinfo=pytz.utc)).total_seconds(), 60)[0]
                        
                        # is it a league we're interested in and does the game time match the tip's game time?
                        correct_league = teamconstants.is_league_alias('wettpoint', tip_instance.game_sport, tip_instance.game_league, league_name)
                            
                        # if the league is correct then does the time match (30 minute error window)    
                        if (
                            correct_league is True 
                            and (
                                 _TIME_ERROR_MARGIN_MINUTES_BEFORE <= row_minutes_past_start 
                                 and _TIME_ERROR_MARGIN_MINUTES_AFTER >= row_minutes_past_start
                             )
                        ):
                            home_team = teamconstants.get_team_datastore_name_and_id(tip_instance.game_sport, tip_instance.game_league, tip_row.team_home)[0]
                            away_team = teamconstants.get_team_datastore_name_and_id(tip_instance.game_sport, tip_instance.game_league, tip_row.team_away)[0]
                            
                            # finally, are the teams correct?
                            if (
                                tip_instance.game_team_away == away_team 
                                and tip_instance.game_team_home == home_team
                            ):
                                # so now we know that this wettpoint tip (probably) refers to this tip object... yay!
                                tip_team = tip_row.tip_team
                                tip_total = tip_row.tip_total
                                tip_stake = tip_row.tip_stake
                                tip_stake = float(tip_stake[0:tip_stake.find('/')])
                                
                                # team tip changed
                                if (
                                    tip_instance.wettpoint_tip_team is not None 
                                    and tip_instance.wettpoint_tip_team != tip_team
                                ):
                                    self._create_tip_change_object(tip_instance, tip_change_object, 'team', 'team_general', not tip_change_created, new_team_selection=tip_team)
                                    tip_change_created = True
                                
                                tip_instance.wettpoint_tip_team = tip_team
    
                                # tip is over
                                if tip_total.lower().find('over') != -1:
                                    # total tip changed
                                    if (
                                        tip_instance.total_lines is not None 
                                        and tip_instance.wettpoint_tip_total != models.TIP_SELECTION_TOTAL_OVER
                                    ):
                                        self._create_tip_change_object(tip_instance, tip_change_object, 'total', 'total_over', not tip_change_created, new_total_selection=models.TIP_SELECTION_TOTAL_OVER)
                                        tip_change_created = True
                                    
                                    tip_instance.wettpoint_tip_total = models.TIP_SELECTION_TOTAL_OVER
                                # tip is under
                                elif tip_total.lower().find('under') != -1:
                                    # total tip changed
                                    if (
                                        tip_instance.wettpoint_tip_total is not None 
                                        and tip_instance.wettpoint_tip_total != models.TIP_SELECTION_TOTAL_UNDER
                                    ):
                                        self._create_tip_change_object(tip_instance, tip_change_object, 'total', 'total_under', not tip_change_created, new_total_selection=models.TIP_SELECTION_TOTAL_UNDER)
                                        tip_change_created = True
                                    
                                    tip_instance.wettpoint_tip_total = models.TIP_SELECTION_TOTAL_UNDER
                                
                                initial_negative_tip_stake = None
                                if (
                                    tip_instance.wettpoint_tip_stake is not None 
                                    and tip_instance.wettpoint_tip_stake < 0
                                ):
                                    initial_negative_tip_stake = tip_instance.wettpoint_tip_stake
                                
                                # stake tip changed
                                if (
                                    tip_instance.wettpoint_tip_stake is not None 
                                    and tip_instance.wettpoint_tip_stake >= 0.0 
                                    and tip_instance.wettpoint_tip_stake != tip_stake 
                                    and int(tip_instance.wettpoint_tip_stake) != int(round(tip_stake))
                                ):
                                    self._create_tip_change_object(tip_instance, tip_change_object, 'stake', 'stake_chart', not tip_change_created)
                                    tip_change_created = True
                                    
                                    tip_stake_changed = True
                                    tip_instance.wettpoint_tip_stake = tip_stake
                                elif tip_instance.wettpoint_tip_stake is None or tip_instance.wettpoint_tip_stake < 0.0:
                                    tip_stake_changed = True
                                    tip_instance.wettpoint_tip_stake = tip_stake
                                
                                if (
                                    tip_instance.game_sport not in appvar_util.get_h2h_excluded_sports_appvar() 
                                    and tip_instance.wettpoint_tip_stake % 1 == 0 
                                    and matchup_finalized 
                                    and H2H_sport_issue is not True
                                ):
                                    tip_stake_changed = True
                                    try:
                                        if sys_util.is_local() and tip_instance.elapsed is True:
                                            h2h_details = None
                                        else:
                                            h2h_details = wettpointScraper.get_wettpoint_h2h(league_key, tip_instance.game_team_home, tip_instance.game_team_away)
                                    except requests_util.HTTP_EXCEPTION_TUPLE as request_error:
                                        logging.warning('Error adding wettpoint H2H details. Skipping future [%s] fetches for this execution (1).' % (tip_instance.game_sport))
                                        logging.warning(request_error)
                                        H2H_sport_issue = True
                                    else:
                                        if h2h_details is None:
                                            self.wettpoint_tables_memcache[sport_key]['h2h_limit_reached'] = True
                                        else:
                                            self._add_wettpoint_h2h_details(tip_instance, h2h_details)
                                        
                                if (
                                    H2H_sport_issue is True 
                                    and initial_negative_tip_stake is not None 
                                    and tip_instance.wettpoint_tip_stake >= 0.0
                                ):
                                    logging.warning('[%s] fetches are being skipped, but Tip has appeared in table.'
                                                    ' Making H2H temporary (?) assumption for ' % (tip_instance.game_sport) + _game_details_string(tip_instance))
                                    tip_instance.wettpoint_tip_stake = tip_instance.wettpoint_tip_stake + (initial_negative_tip_stake * -0.1)
                                
                                break
                            # one of the team names matches but the other doesn't, send admin mail to check team names
                            # could either be 1) team name missing or 2) wettpoint has wrong game listed
                            elif tip_instance.game_team_home == home_team:
                                mail_message = ('Wettpoint table has matched a Tip date and home team.'
                                                ' Possible AWAY team name missing for '+_game_details_string(tip_instance)+
                                                ' Wettpoint table match is %s @ %s' % (str(away_team), str(home_team)))
                                sys_util.add_mail(constants.MAIL_TITLE_TEAM_ERROR, mail_message, logging='warning')
                            elif tip_instance.game_team_away == away_team:
                                mail_message = ('Wettpoint table has matched a Tip date and away team.'
                                                ' Possible HOME team name missing for '+_game_details_string(tip_instance)+
                                                ' Wettpoint table match is %s @ %s' % (str(away_team), str(home_team)))
                                sys_util.add_mail(constants.MAIL_TITLE_TEAM_ERROR, mail_message, logging='warning')
                        # tip has passed this object (i.e. no tip upcoming for this event therefore tip stake = 0)
                        elif _TIME_ERROR_MARGIN_MINUTES_AFTER < row_minutes_past_start:
                            if (
                                tip_instance.wettpoint_tip_stake is not None 
                                and tip_instance.wettpoint_tip_stake >= 1.0
                            ):
                                if minutes_until_start <= (abs(_TIME_ERROR_MARGIN_MINUTES_BEFORE) + self._WETTPOINT_TABLE_MINUTES_BEFORE_EVENT_EXPIRE):
                                    # tip has already been filled out and table updated past tip time, move on to next to avoid resetting tip to 0
                                    break
                                self._create_tip_change_object(tip_instance, tip_change_object, 'stake', 'stake_all', not tip_change_created)
                                tip_change_created = True
                            
                            if tip_instance.wettpoint_tip_stake is None or tip_instance.wettpoint_tip_stake >= 1.0:
                                tip_stake_changed = True
                                tip_instance.wettpoint_tip_stake = 0.0
                                
                            break
                    
                    if tip_instance.game_sport not in appvar_util.get_h2h_excluded_sports_appvar() and H2H_sport_issue is not True:
                        if tip_instance.wettpoint_tip_stake == 0.0 and tip_stake_changed is True:
                            if not matchup_finalized:
                                tip_instance.wettpoint_tip_stake = None
                                tip_stake_changed = False
                        
                        last_window_minutes = (abs(self._TIME_CRON_SCHEDULE_MINUTES_APART) * 1.5) + 5
                        if ((
                            tip_instance.wettpoint_tip_stake is None 
                            and (
                                 minutes_until_start <= last_window_minutes 
                                 or (
                                     matchup_finalized 
                                     and tip_instance.wettpoint_tip_team is None 
                                     and tip_instance.wettpoint_tip_total is None
                                     )
                                 )
                            ) or
                            (
                             tip_instance.wettpoint_tip_stake == 0.0 
                             and tip_stake_changed is True 
                            )
                        ):
                            nolimit = False
                            if minutes_until_start <= last_window_minutes:
                                nolimit = True
                                
                            h2h_total = h2h_team = h2h_risk = False
                            try:
                                if sys_util.is_local() and tip_instance.elapsed is True:
                                    h2h_details = None
                                else:
                                    h2h_details = wettpointScraper.get_wettpoint_h2h(league_key, tip_instance.game_team_home, tip_instance.game_team_away, nolimit=nolimit)
                            except requests_util.HTTP_EXCEPTION_TUPLE as request_error:
                                logging.warning('Error getting wettpoint H2H details. Skipping future [%s] fetches for this execution (2).' % (tip_instance.game_sport))
                                logging.warning(request_error)
                                H2H_sport_issue = True
                                tip_instance.wettpoint_tip_stake = None
                            else:
                                if h2h_details is None:
                                    self.wettpoint_tables_memcache[sport_key]['h2h_limit_reached'] = True
                                else:
                                    h2h_total = h2h_details['total']
                                    h2h_team = h2h_details['team']
                                    h2h_risk = h2h_details['risk']
                                
                            if h2h_total is not False:
                                if (
                                    tip_instance.wettpoint_tip_total is not None 
                                    and tip_instance.wettpoint_tip_total != h2h_total
                                    ):
                                    tip_instance.total_no = None
                                    tip_instance.total_lines = None
                                tip_instance.wettpoint_tip_total = h2h_total
                                
                            if h2h_team is not False:
                                if (
                                    tip_instance.wettpoint_tip_team is not None 
                                    and tip_instance.wettpoint_tip_team != h2h_team
                                    ):
                                    tip_instance.team_lines = None
                                    tip_instance.spread_no = None
                                    tip_instance.spread_lines = None
                                tip_instance.wettpoint_tip_team = h2h_team
                           
                            if h2h_risk is not False:
                                if h2h_team is not False:
                                    tip_instance.wettpoint_tip_stake = (10.0 - h2h_risk) * -1
                                elif tip_instance.wettpoint_tip_stake == 0.0 or minutes_until_start <= last_window_minutes:
                                    h2h_stake = (10.0 - h2h_risk) / 10.0
                                    tip_instance.wettpoint_tip_stake = 0.0 + h2h_stake
                            elif minutes_until_start <= last_window_minutes:
                                tip_instance.wettpoint_tip_stake = 0.0
                            elif self.wettpoint_tables_memcache[sport_key]['h2h_limit_reached'] is True and tip_instance.wettpoint_tip_stake == 0.0:
                                tip_instance.wettpoint_tip_stake = None
                            
                    # change object created, put in datastore
                    if tip_change_object is not None:
                        self.datastore_writes += 1
                        tip_change_object.put()
                        tip_change_object = None
                    
                    minutes_for_next_check = minutes_until_start / 3
                    if minutes_for_next_check < self.wettpoint_tables_memcache[sport_key]['minutes_between_checks']:
                        if minutes_for_next_check < 120:
                            self.wettpoint_tables_memcache[sport_key]['minutes_between_checks'] = 120
                        else:
                            self.wettpoint_tables_memcache[sport_key]['minutes_between_checks'] = minutes_for_next_check
                    elif (
                          minutes_for_next_check >= self.wettpoint_tables_memcache[sport_key]['minutes_between_checks'] 
                          and self.wettpoint_tables_memcache[sport_key]['minutes_between_checks'] == 120
                          ):
                        self.wettpoint_tables_memcache[sport_key]['minutes_between_checks'] = minutes_for_next_check
                    
                    if tip_stake_changed is True:
                        self.wettpoint_tables_memcache[sport_key]['tip_changed'] = True
                    
                    self.tipData.not_previously_elapsed_tips[sport_key][league_key][tip_instance_index] = tip_instance
        
        memcache_util.set(memcache_util.MEMCACHE_KEY_SCRAPER_WETTPOINT_TABLE, self.wettpoint_tables_memcache)
    
    def _matchup_data_finalized(self, sport_key, team_list, matchup_date, possible_earlier_games):
        for check_tip_instance in possible_earlier_games:
            if (
                (
                 sport_key not in appvar_util.get_weekly_sports_appvar() 
                 and check_tip_instance.date < (matchup_date - timedelta(hours = _TIME_ERROR_MARGIN_HOURS_GAME_MATCH)) 
                 )
                or
                (
                 check_tip_instance.date < matchup_date 
                 and (
                      check_tip_instance.game_team_away in team_list 
                      or check_tip_instance.game_team_home in team_list
                     )
                 )
                ):
                return False
            
        return True
    
    def _add_wettpoint_h2h_details(self, tip_instance, h2h_details):
        h2h_total = h2h_details['total']
        h2h_team = h2h_details['team']
        h2h_risk = h2h_details['risk']
        
        new_wettpoint_stake = tip_instance.wettpoint_tip_stake
        
        if h2h_risk is not False:
            h2h_stake = (10.0 - h2h_risk) / 10.0
        else:
            h2h_stake = 0.0
            
        if (
            h2h_team is False 
            and h2h_total is False
        ):
            h2h_stake += models.TIP_STAKE_TEAM_TOTAL_NONE / 1000.0
        elif (
              h2h_team is not False 
              and h2h_total is not False 
        ):
            if (
                h2h_team != tip_instance.wettpoint_tip_team 
                and h2h_total != tip_instance.wettpoint_tip_total
            ):
                h2h_stake += models.TIP_STAKE_TEAM_TOTAL_DISAGREE / 1000.0
            elif h2h_team != tip_instance.wettpoint_tip_team:
                h2h_stake += models.TIP_STAKE_TEAM_DISAGREE / 1000.0
            elif h2h_total != tip_instance.wettpoint_tip_total:
                h2h_stake += models.TIP_STAKE_TOTAL_DISAGREE / 1000.0
        elif h2h_team is not False:
            if h2h_team != tip_instance.wettpoint_tip_team:
                h2h_stake += models.TIP_STAKE_TEAM_DISAGREE_TOTAL_NONE / 1000.0
            else:
                h2h_stake += models.TIP_STAKE_TOTAL_NONE / 1000.0
        elif h2h_total is not False:
            if h2h_total != tip_instance.wettpoint_tip_total:
                h2h_stake += models.TIP_STAKE_TOTAL_DISAGREE_TEAM_NONE / 1000.0
            else:
                h2h_stake += models.TIP_STAKE_TEAM_NONE / 1000.0
            
        new_wettpoint_stake += h2h_stake
        tip_instance.wettpoint_tip_stake = new_wettpoint_stake
    
    #TODO: remove in TipLine update
    def _create_tip_change_object(self, tip_instance, tip_change_object, ctype, line, create_mail, new_team_selection=None, new_total_selection=None):
        if create_mail is True:
            mail_message = "\n"+(tip_instance.date.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(constants.TIMEZONE_LOCAL))).strftime('%B-%d %I:%M%p') + " " + tip_instance.game_team_away + " @ " + tip_instance.game_team_home + "\n"
            mail_message += str(tip_instance.wettpoint_tip_stake) + " " + str(tip_instance.wettpoint_tip_team) + " " + str(tip_instance.wettpoint_tip_total) + "\n"
            mail_message += ctype + " (" + line + ")\n"
            sys_util.add_mail('Tip Change Notice', mail_message)
        else:
            mail_message = ctype + " (" + line + ")\n"
            sys_util.add_mail('Tip Change Notice', mail_message)
        
        key_string = unicode(tip_instance.key.urlsafe())
        
        self.datastore_reads += 1
        query = models.TipChange.gql('WHERE tip_key = :1', key_string)
        query_count = query.count(limit=1)
        
        if query_count == 0 and not tip_change_object:
            self.datastore_writes += 1
            tip_change_object = models.TipChange()
            tip_change_object.changes = 1
            tip_change_object.type = ctype
        else:
            if query_count != 0:
                self.datastore_reads += 2
                tip_change_object = query.get()
            tip_change_object.changes += 1
            tip_change_object.type = tip_change_object.type + ctype
            
        tip_change_object.date = datetime.utcnow()
        tip_change_object.tip_key = key_string
            
        tip_change_object.wettpoint_tip_stake = tip_instance.wettpoint_tip_stake
        
        if ctype == 'team':
            if (
                tip_instance.wettpoint_tip_stake is not None 
                and tip_instance.wettpoint_tip_stake >= 1.0 
            ):
                tip_instance.wettpoint_tip_stake = float(int(tip_instance.wettpoint_tip_stake))
            
            if (
                new_team_selection is not None 
                and tip_change_object.wettpoint_tip_team == new_team_selection
            ):
                logging.info('Transferring team lines from existing TipChange object to Tip for %s @ %s' % (tip_instance.game_team_away, tip_instance.game_team_home))
                original_lines = tip_change_object.team_lines
            else:
                original_lines = None
                
            tip_change_object.team_lines = tip_instance.team_lines
            tip_instance.team_lines = original_lines
            
            if (
                new_team_selection is not None 
                and tip_change_object.wettpoint_tip_team == new_team_selection
            ):
                original_lines = tip_change_object.spread_no
            else:
                original_lines = None
            
            tip_change_object.spread_no = tip_instance.spread_no
            tip_instance.spread_no = original_lines
            
            if (
                new_team_selection is not None 
                and tip_change_object.wettpoint_tip_team == new_team_selection
            ):
                original_lines = tip_change_object.spread_lines
            else:
                original_lines = None
            
            tip_change_object.spread_lines = tip_instance.spread_lines
            tip_instance.spread_lines = original_lines
            
            tip_change_object.wettpoint_tip_team = tip_instance.wettpoint_tip_team
            tip_instance.wettpoint_tip_team = None
        elif ctype == 'total':
            if (
                tip_instance.wettpoint_tip_stake is not None 
                and tip_instance.wettpoint_tip_stake >= 1.0 
            ):
                tip_instance.wettpoint_tip_stake = float(int(tip_instance.wettpoint_tip_stake))
            
            if (
                new_total_selection is not None 
                and tip_change_object.wettpoint_tip_total == new_total_selection
            ):
                logging.info('Transferring total lines from existing TipChange object to Tip for %s @ %s' % (tip_instance.game_team_away, tip_instance.game_team_home))
                original_lines = tip_change_object.total_no
            else:
                original_lines = None
            
            tip_change_object.total_no = tip_instance.total_no
            tip_instance.total_no = original_lines
            
            if (
                new_total_selection is not None 
                and tip_change_object.wettpoint_tip_total == new_total_selection
            ):
                original_lines = tip_change_object.total_lines
            else:
                original_lines = None
            
            tip_change_object.total_lines = tip_instance.total_lines
            tip_instance.total_lines = original_lines
            
            tip_change_object.wettpoint_tip_total = tip_instance.wettpoint_tip_total
            tip_instance.wettpoint_tip_total = None

class BookieData(DataHandler):
    STATUS_INITIALIZED = 'initialized'
    STATUS_ERROR = 'error'
    STATUS_UPDATED = 'updated'
    
    def __init__(self, eventsDict):
        if eventsDict:
            self.eventsDict = eventsDict
            self.status = self.STATUS_INITIALIZED
        else:
            self.eventsDict = {}
            self.status = self.STATUS_ERROR
            
        # a DataHandler object is defined by its events dictionary
        self._tipkey_to_event = {}
        self.new_or_updated_tips = []
        
    def get_event_from_key(self, tipKey):
        return self._tipkey_to_event.get(tipKey)
        
    def is_key_new_or_updated(self, tipKey):
        if tipKey in self.new_or_updated_tips:
            return True
        return False
    
    def _set_status(func):
        def call_and_set_status(*args, **kwargs):
            try:
                func(*args, **kwargs)
                args[0].status = args[0].STATUS_UPDATED
            except DatastoreException as error:
                logging.warning(error)
                args[0].status = args[0].STATUS_ERROR
        return call_and_set_status
    
    @sys_util.function_timer()
    @_set_status
    def update_tips(self):
        '''Create a dictionary (stored on DataHandler attribute _tipkey_to_event) that stores a 1:1 link
        for a Tip key (keys) to a BookieScrapeData (values). If an BookieScrapeData has no corresponding Tip then create and 
        write a new Tip to the datastore. The BookieScrapeData can now be accessed and used to fill out their 
        corresponding Tip line data. Needs to be done before line update so that new Tips lines can also be updated
        on their initialization.
        '''
        for sport_key, events_by_leage in self.eventsDict.iteritems():
            if sport_key not in appvar_util.get_sport_names_appvar():
                raise DatastoreException('Scraper did not get correct sport datastore name for %s' % (sport_key))
            for league_key, league_events in events_by_leage.iteritems():
                if league_key not in appvar_util.get_league_names_appvar()[sport_key]:
                    raise DatastoreException('Scraper did not get correct league datastore name for [%s / %s]' % (league_key, sport_key))
                
                # go through all scraped events to either find existing or insert new Tip object
                '@type event: scraper.BookieScrapeData'
                for event in league_events:
                    # team names as they were scraped may not be the correct name stored in the datastore
                    # and so will need to be updated
                    team_name_away = event.team_away
                    team_name_home = event.team_home
                    
                    team_name_without_game_string_away = None
                    team_name_without_game_string_home = None
                    # if a team name does not exist (as an alias or otherwise) then we'll want to email the admin later
                    missing_team_name = []
                    # convert the scraped team names to the team names as they are stored in the datastore
                    for team_name in [team_name_away, team_name_home]:
                        datastore_team_name, datastore_team_name_without_game_string = self._get_team_datastore_name(sport_key, league_key, team_name)
                        
                        if datastore_team_name is None:
                            # will still add this event to the datastore but email the admins about the missing team names
                            missing_team_name.append(team_name)
                        else:
                            if datastore_team_name != team_name:
                                logging.info('Changing pinnacle name (%s) to datastore (%s)' % (
                                                                                                team_name,
                                                                                                datastore_team_name
                                                                                                ))
                                
                            if team_name == team_name_away:
                                team_name_without_game_string_home = datastore_team_name_without_game_string
                                team_name_away = datastore_team_name
                            elif team_name == team_name_home:
                                team_name_without_game_string_away = datastore_team_name_without_game_string
                                team_name_home = datastore_team_name

                    # determine whether Tip object for this event exists or not based on rotation #s
                    self.datastore_reads += 1
                    query = models.Tip.gql('WHERE game_sport = :1 AND game_league = :2 AND rot_away = :3 AND rot_home = :4 AND date >= :5 AND date <= :6', 
                                    sport_key,
                                    league_key,
                                    event.rot_away,
                                    event.rot_home,
                                    event.datetime - timedelta(hours=_TIME_ERROR_MARGIN_HOURS_GAME_MATCH),
                                    event.datetime + timedelta(hours=_TIME_ERROR_MARGIN_HOURS_GAME_MATCH),
                                )
                    
                    try:
                        tip_instance = self._get_tip_from_query(query)
                    except DatastoreException as error:
                        # a previous Tip could have had its rotation numbers changed so that now there are 2
                        # Tips that match this query, will have to ignore this exception since we're expecting
                        # it to fix itself with the softer match
                        tip_instance = None
                    
                    # only update the Tip (using a datastore write) if we need to
                    update_tip_instance = False
                    
                    if (
                        # either a event with no corresponding Tip or...
                        tip_instance is None
                        or (
                            # ...a possibility that rotation numbers within the league have been switched around
                            # for more confidence that the rot numbers simply changed from when the event first appeared
                            # make sure the team names don't match at all
                            tip_instance.game_team_away != team_name_away 
                            and tip_instance.game_team_home != team_name_home
                            and tip_instance.game_team_away != team_name_without_game_string_away 
                            and tip_instance.game_team_home != team_name_without_game_string_home
                        )
                    ):
                        # do a softer match on team names and datetime margin error
                        self.datastore_reads += 1
                        query = models.Tip.gql('WHERE game_sport = :1 AND game_league = :2 AND game_team_away = :3 AND game_team_home = :4 AND date >= :5 AND date <= :6',
                                                sport_key,
                                                league_key,
                                                team_name_away,
                                                team_name_home,
                                                event.datetime - timedelta(hours=_TIME_ERROR_MARGIN_HOURS_GAME_MATCH),
                                                event.datetime + timedelta(hours=_TIME_ERROR_MARGIN_HOURS_GAME_MATCH),
                                               )
                            
                        try:
                            tip_instance = self._get_or_create_tip_from_query(query)
                            # either new or needs updating
                            update_tip_instance = True
                            if tip_instance.game_sport is None:
                                # completely new Tip
                                # if the team names were missing their datastore constants, email the admin about it (only once when inserting)
                                if len(missing_team_name) > 0:
                                    mail_message = '%s for [%s / %s] does not exist!' % (' & '.join(missing_team_name), league_key, sport_key) + "\n"
                                    sys_util.add_mail(constants.MAIL_TITLE_TEAM_ERROR, mail_message, logging='warning')
                            else:
                                # otherwise a Tip whose rotation numbers are wrong
                                update_message = 'Updating game rotation numbers: %s %s (%d) @ %s (%d) to %s (%d) @ %s (%d) [%s / %s]' % (
                                                                                            tip_instance.date.strftime(constants.DATETIME_ISO_8601_FORMAT),
                                                                                            tip_instance.game_team_away,
                                                                                            tip_instance.rot_away,
                                                                                            tip_instance.game_team_home,
                                                                                            tip_instance.rot_home,
                                                                                            team_name_away,
                                                                                            event.rot_away,
                                                                                            team_name_home,
                                                                                            event.rot_home,
                                                                                            tip_instance.game_league,
                                                                                            tip_instance.game_sport,
                                                                                          )
                                sys_util.add_mail(constants.MAIL_TITLE_UPDATE_NOTIFICATION, update_message, logging='info')
                                logging.info(update_message)
                        except DatastoreException as error:
                            # raise exception to send mail but continue on without this event
                            logging.warning(error)
                            continue
                    
                    if tip_instance.game_sport is not None:
                        # only if Tip is not a new one
                        # determine if information is the same as it should be
                        # possibly need to update the date and/or team names (e.g. updated doubleheader)
                        
                        # check the team names (e.g. doubleheader added)
                        if (
                            tip_instance.game_team_away != team_name_away 
                            or tip_instance.game_team_home != team_name_home
                        ):
                            # Tip could have been inserted before doubleheader status
                            # then the team names should match the names without the game string
                            if (
                                tip_instance.game_team_away != team_name_without_game_string_away 
                                or tip_instance.game_team_home != team_name_without_game_string_home
                            ):
                                # possibilities for how it got here:
                                # 1) a team name in bookie was not in app var, new Tip for it is created, team name then changes on bookie
                                # 2) something is really wrong and we got the completely wrong Tip
                                try:
                                    error_message = '''
                                    Retrieved incorrect Tip! 
                                    Retrieved: %s %s (%d) @ %s (%d) [%s / %s]
                                    Expected: %s %s (%d) @ %s (%d) [%s / %s]
                                    ''' % (
                                           tip_instance.date.strftime(constants.DATETIME_ISO_8601_FORMAT),
                                           tip_instance.game_team_away,
                                           tip_instance.rot_away,
                                           tip_instance.game_team_home,
                                           tip_instance.rot_home,
                                           tip_instance.game_sport,
                                           tip_instance.game_league,
                                           event.datetime.strftime(constants.DATETIME_ISO_8601_FORMAT),
                                           team_name_away,
                                           event.rot_away,
                                           team_name_home,
                                           event.rot_home,
                                           sport_key,
                                           league_key
                                           )
                                    raise DatastoreException(error_message)
                                except DatastoreException as error:
                                    # raise exception to send mail but continue on without this event
                                    logging.warning(error)
                                    continue
                            
                            # team names matched names without game string so we'll want to update this Tip with the doubleheader info
                            update_message = 'Updating game team names: %s %s @ %s to %s @ %s [%s / %s]' % (
                                                                                            tip_instance.date.strftime(constants.DATETIME_ISO_8601_FORMAT),
                                                                                            tip_instance.game_team_away,
                                                                                            tip_instance.game_team_home,
                                                                                            event.team_away,
                                                                                            event.team_home,
                                                                                            tip_instance.game_league,
                                                                                            tip_instance.game_sport
                                                                                              )
                            sys_util.add_mail(constants.MAIL_TITLE_UPDATE_NOTIFICATION, update_message, logging='info')
                            logging.info(update_message)
                            update_tip_instance = True
                            
                        # second check the datetime (e.g. game could have been delayed)
                        # TODO: add margin of error (because different bookies might have slightly different times)
                        if tip_instance.date != event.datetime:
                            update_message = 'Updating game date: %s %s @ %s to %s [%s / %s]' % (
                                                                                   tip_instance.date.strftime(constants.DATETIME_ISO_8601_FORMAT),
                                                                                   tip_instance.game_team_away,
                                                                                   tip_instance.game_team_home,
                                                                                   event.datetime.strftime(constants.DATETIME_ISO_8601_FORMAT),
                                                                                   tip_instance.game_league,
                                                                                   tip_instance.game_sport
                                                                                   )
                            sys_util.add_mail(constants.MAIL_TITLE_UPDATE_NOTIFICATION, update_message, logging='info')
                            logging.info(update_message)
                            update_tip_instance = True
                            
                    if update_tip_instance is True:
                        # add / overwrite basic information to tip object
                        tip_instance.game_sport = sport_key
                        tip_instance.game_league = league_key
                        tip_instance.date = event.datetime
                        tip_instance.game_team_away = team_name_away
                        tip_instance.game_team_home = team_name_home
                        tip_instance.rot_away = event.rot_away
                        tip_instance.rot_home = event.rot_home
                        
                        self.datastore_writes += 1
                        tip_instance_key = tip_instance.put()
                        
                        self.new_or_updated_tips.append(tip_instance_key)
                    else:
                        tip_instance_key = tip_instance.key
                    
                    # Tips will get their lines updated so keep Tip associated with their BookieScrapeData for later use
                    self._tipkey_to_event[tip_instance_key] = event
                    
    def _get_team_datastore_name(self, sport_key, league_key, bookie_team_name):
        # if the game is a doubleheader then we'll need both the team name with the game string and without
        # since a doubleheader may be stored as a Tip with the team name as is (with the game string) or
        # it could be a game that was converted to a doubleheader (without game string)
        bookie_team_name_without_game_string, team_game_string = teamconstants.split_doubleheaders_team_names(bookie_team_name)
        try:
            datastore_name = teamconstants.get_team_datastore_name_and_id(sport_key, league_key, bookie_team_name_without_game_string)[0]
        except KeyError:
            # league does not have team names data set up (correctly)
            datastore_name = None

        # the datastore name for this team was either retrieved or it doesn't exist
        datastore_team_name_without_game_string = datastore_name
        
        if team_game_string is not None:
            datastore_team_name = team_game_string + datastore_name
        else:
            datastore_team_name = datastore_name
            
        return datastore_team_name, datastore_team_name_without_game_string
    
    def _get_tip_from_query(self, query):
        # count: 0 = insert new Tip, 1 = get existing Tip, 2 = something wrong
        query_count = query.count(limit=2)
        
        if query_count == 0:
            tip_instance = None
        else:
            self.datastore_reads += 2
            tip_instance = query.get()
              
            # should be only one result if it exists
            if query_count > 1:
                error_message = '''
                                Multiple matching datastore Tip instances: %s (%d) @ %s (%d) [%s / %s]
                                ''' % (
                                       tip_instance.game_team_away,
                                       tip_instance.rot_away,
                                       tip_instance.game_team_home,
                                       tip_instance.rot_home,
                                       tip_instance.game_sport,
                                       tip_instance.game_league
                                       )
                raise DatastoreException(error_message)
            
        return tip_instance
    
    def _get_or_create_tip_from_query(self, query):
        if query:
            tip_instance = self._get_tip_from_query(query)
        else:
            tip_instance = None
        
        if tip_instance is None:
            self.datastore_writes += 1
            tip_instance = models.Tip()
            
        return tip_instance