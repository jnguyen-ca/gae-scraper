#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import constants

class ScrapeException(constants.ApplicationException):
    """Base exception for site traversal"""
    
class Scraper(object):
    def scrape(self):
        pass
    
class BookieScraper(Scraper):
    BOOKIE_KEY = None
    
class ScoreboardScraper(Scraper):
    _timezone = None
    
    def convert_utc_to_local(self, dataDatetime):
        raise NotImplementedError('must be overridden')
    
    def is_complete(self, status):
        raise NotImplementedError('must be overridden')
    
    def is_live(self, status):
        raise NotImplementedError('must be overridden')
    
class EventScrapeData(object):
    def __init__(self):
        self.sport = None
        self.league = None
        self.team_away = None
        self.team_home = None

# TODO: there should be an intermediate class between BookieScrapeDate and EventScrapeData
# that specifies that BookieScrapeData has valid datastore values (e.g. team names)
# while other classes that inherit from EventScrapeData do not (i.e. they're scraped data in their raw form) 
class BookieScrapeData(EventScrapeData):
    LINE_KEY_POINTS = 'points'
    LINE_KEY_ODDS = 'odds'
    
    def __init__(self):
        super(BookieScrapeData, self).__init__()
        self.line_datetime = None
        self.datetime = None
        self.rot_away = None
        self.rot_home = None
        self.spread_away = None
        self.spread_home = None
        self.moneyline_away = None
        self.moneyline_home = None
        self.moneyline_draw = None
        self.total_over = None
        self.total_under = None
        
class ScoreRowData(EventScrapeData):
    def __init__(self):
        super(ScoreRowData, self).__init__()
        self.datetime = None
        self.status = None
        self.regulation_score_away = None
        self.regulation_score_home = None
        self.final_score_away = None
        self.final_score_home = None
        self.extra_time = None

class WettpointRowData(EventScrapeData):
    def __init__(self):
        super(WettpointRowData, self).__init__()
        self.time_string = None
        self.tip_team = None
        self.tip_total = None
        self.tip_stake = None

from google.appengine.api import urlfetch

import sys
sys.path.append('utils')

from datetime import datetime
from utils import appvar_util, sys_util, requests_util

import re
import time
import random
import logging
import teamconstants
import models

class WettpointScraper(Scraper):
    __WETTPOINT_FEED = constants.WETTPOINT_FEED
    
    def __init__(self, sport_key):
        self.sport_key = sport_key
        self._sport_table = None
    
    @property
    @sys_util.function_timer()
    def sport_table(self):
        if self._sport_table is None:
            # get wettpoint tip table page for particular sport
            sport = appvar_util.get_sport_names_appvar()[self.sport_key][appvar_util.APPVAR_KEY_WETTPOINT]
            feed = 'http://www.forum.'+self.__WETTPOINT_FEED+'/fr_toptipsys.php?cat='+sport
            
            soup = requests_util.request(
                                  request_lib        = requests_util.REQUEST_LIB_REQUESTS, 
                                  response_type      = requests_util.RESPONSE_TYPE_HTML, 
                                  response_encoding  = None, 
                                  min_wait_time       = 9.9, 
                                  max_wait_time       = 30.1, 
                                  max_hits           = len(appvar_util.get_sport_names_appvar()),
                                  url               = feed,
                                  headers           = sys_util.get_header()
                                  )
            
            # store table information in a list
            event_rows = []
            if soup:
                # get the tip table for this sport
                tables = soup.find_all('table', {'class' : 'gen'})
                tip_table = tables[1]
                tip_rows = tip_table.find_all('tr')[2:]
                
                for tip_row in tip_rows:
                    columns = tip_row.find_all('td')
                    
                    # table may be empty if there are no near-scheduled events (e.g. baseball during winter)
                    if 6 >= len(columns):
                        break
                    
                    # get all text as-is and store in a dict
                    team_names = columns[0].get_text()
                    tip_team = columns[1].get_text().strip()
                    tip_total = columns[2].get_text().strip()
                    tip_stake = columns[3].get_text()
                    # column 4 is bookie referral links
                    league_name = columns[5].get_text().strip()
                    game_time = columns[6].get_text().strip()
                    
                    team_splitter = ' - '
                    index = team_names.find(team_splitter)
                    home_team = team_names[0:index].strip()
                    away_team = team_names[index+len(team_splitter):len(team_names)].strip()
                    
                    tip_row_obj = WettpointRowData()
                    tip_row_obj.sport = self.sport_key
                    tip_row_obj.league = league_name
                    tip_row_obj.time_string = game_time
                    tip_row_obj.team_home = home_team
                    tip_row_obj.team_away = away_team
                    tip_row_obj.tip_team = tip_team
                    tip_row_obj.tip_total = tip_total
                    tip_row_obj.tip_stake = tip_stake
                    
                    event_rows.append(tip_row_obj)
                
            self._sport_table = event_rows
        return self._sport_table
    
    @sys_util.function_timer()
    def get_wettpoint_h2h(self, league_key, team_home, team_away, **kwargs):
        h2h_total, h2h_team, h2h_risk = False, False, False
        
        datastore_team_home, team_home_id = teamconstants.get_team_datastore_name_and_id(self.sport_key, league_key, team_home)
        datastore_team_away, team_away_id = teamconstants.get_team_datastore_name_and_id(self.sport_key, league_key, team_away)
        
        h2h_details = {
                       'total'  : h2h_total, 
                       'team'   : h2h_team, 
                       'risk'   : h2h_risk
                       }
        
        # one of the teams has no team id
        if team_home_id is None or team_away_id is None:
            return h2h_details
        
        no_limit = False
        if 'nolimit' in kwargs and kwargs['nolimit'] and not sys_util.is_local():
            no_limit = True
            logging.debug('Doing a NOLIMIT fetch. Not counting following fetch towards the H2H fetch limit.')
        
        sport = appvar_util.get_sport_names_appvar()[self.sport_key][appvar_util.APPVAR_KEY_WETTPOINT]
        
        # wettpoint h2h link is home team - away team
        h2h_link = 'http://'+sport+'.'+self.__WETTPOINT_FEED+'/h2h/'+team_home_id+'-'+team_away_id+'.html'
        
        h2h_soup = requests_util.request(
                                  request_lib           = requests_util.REQUEST_LIB_URLFETCH, 
                                  response_type         = requests_util.RESPONSE_TYPE_HTML, 
                                  response_encoding     = None, 
                                  min_wait_time         = 16.87, 
                                  max_wait_time         = 30.9, 
                                  max_hits              = 5,
                                  no_hit                = no_limit,
                                  log_info              = '(%s-%s)' % (team_home, team_away),
                                  url                   = h2h_link,
                                  headers               = { "Accept-Encoding" : "identity" }
                                  )
        
        if not h2h_soup:
            logging.debug('Wettpoint H2H fetches have reached their limit.')
            # return None object to indicate no scrape was attempted and one should be queued up for next execution
            return None
        
        h2h_soup = h2h_soup.find('div', {'class' : 'inhalt2'})
        
        # ensure teams are correct and we got the right link
        team_links = h2h_soup.find('table').find_all('tr')[-1].find_all('a')
        team_link_text_home = team_links[0].get_text()
        team_link_text_away = team_links[1].get_text()
        
        team_link_home = teamconstants.get_team_datastore_name_and_id(self.sport_key, league_key, team_link_text_home)[0]
        team_link_away = teamconstants.get_team_datastore_name_and_id(self.sport_key, league_key, team_link_text_away)[0]
        if (
            datastore_team_home == team_link_home 
            and datastore_team_away == team_link_away
        ):
            h2h_header = h2h_soup.find_all('h3', recursive=False)[1]
            
            h2h_total_text = h2h_header.find_next_sibling(text=re.compile('Over\s?/\s?Under'))
            if h2h_total_text:
                h2h_total_text = h2h_total_text.find_next_sibling('b').get_text().strip()
                if 'UNDER' in h2h_total_text:
                    h2h_total = models.TIP_SELECTION_TOTAL_UNDER
                elif 'OVER' in h2h_total_text: 
                    h2h_total = models.TIP_SELECTION_TOTAL_OVER
                    
            h2h_team_text = h2h_header.find_next_sibling(text=re.compile('1X2 System'))
            if h2h_team_text:
                h2h_team = h2h_team_text.find_next_sibling('b').get_text().strip()
                
            h2h_risk_text = h2h_header.find_next_sibling(text=re.compile('Risikofaktor'))
            if h2h_risk_text:
                h2h_risk_text = h2h_risk_text.find_next_sibling('b').get_text().strip()
                try:
                    h2h_risk = float(h2h_risk_text)
                    
                    if h2h_risk == 10.0 or h2h_risk == 0.0:
                        mail_message = 'Special case of risk factor (%s) : %s @ %s [%s / %s]' % (
                                                                                                 str(h2h_risk_text),
                                                                                                 team_away,
                                                                                                 team_home,
                                                                                                 league_key,
                                                                                                 self.sport_key
                                                                                                 )+"\n\n"
                        sys_util.add_mail(constants.MAIL_TITLE_TIP_WARNING, mail_message, logging='warning')
                        
                        if h2h_risk == 10.0:
                            h2h_risk = 9.9
                        else:
                            h2h_risk = 0.1
                except ValueError:
                    h2h_risk = False
        else:
            mail_message = ('Wettpoint H2H page retrieved has teams %s-%s which points to datastore %s-%s, but expected %s-%s.'
                            ' Wettpoint ID in application variable may be incorrect. [%s / %s]' % (
                                                                                                  team_link_text_home,
                                                                                                  team_link_text_away,
                                                                                                  str(team_link_home),
                                                                                                  str(team_link_away),
                                                                                                  team_home,
                                                                                                  team_away,
                                                                                                  league_key,
                                                                                                  self.sport_key
                                                                                                  ))
            sys_util.add_mail(constants.MAIL_TITLE_TEAM_ERROR, mail_message, logging='warning')
        
        h2h_details = {
                       'total'  : h2h_total, 
                       'team'   : h2h_team, 
                       'risk'   : h2h_risk
                       }
        
        return h2h_details

class PinnacleScraper(BookieScraper):
    BOOKIE_KEY = appvar_util.APPVAR_KEY_PINNACLE
    __PINNACLE_FEED = 'pinnaclesports.com'
    
    @sys_util.function_timer()
    def scrape(self):
        """Find a list of games (and their details) corresponding to our interests
        """
        sport_feed = 'http://xml.'+self.__PINNACLE_FEED+'/pinnacleFeed.aspx'#?sporttype=' + keys['pinnacle']
        
        lxml_tree = requests_util.request(
                                      request_lib        = requests_util.REQUEST_LIB_URLFETCH, 
                                      response_type      = requests_util.RESPONSE_TYPE_XML, 
                                      response_encoding  = None, 
                                      min_wait_time      = 73.6, # pinnacle rules state no more than 1 request per minute
                                      max_wait_time      = 73.6, 
                                      max_hits           = 3,
                                      no_hit             = False,
                                      log_info           = None,
                                      url                = sport_feed
                                  )
        
        # will return the scraped information
        events_by_sport_league = {}
        
        if lxml_tree is None:
            return events_by_sport_league
        
        try:
            # get feed time for line date data
            feed_epoch_time = float(lxml_tree.xpath("/pinnacle_line_feed/PinnacleFeedTime/text()")[0])
            pinnacle_feed_time = datetime.utcfromtimestamp(feed_epoch_time / 1000.0)
        except IndexError:
            raise ScrapeException('PinnacleFeedTime tag text was not found in the feed!')
        
        # get pinnacle sports / league names from app variable
        for sport_key, sport_values in appvar_util.get_sport_names_appvar().iteritems():
            events_by_sport_league[sport_key] = {}
            for league_key, league_values in appvar_util.get_league_names_appvar()[sport_key].iteritems():
                events_by_sport_league[sport_key][league_key] = []
                
                pinnacle_league_key = league_values[appvar_util.APPVAR_KEY_PINNACLE]
                league_xpath = None
                # single league can have multiple league names (ex. conferences)
                if isinstance(pinnacle_league_key, list):
                    for pinnacle_league_value in pinnacle_league_key:
                        if league_xpath is None:
                            league_xpath = "league='"+pinnacle_league_value+"'"
                        else:
                            league_xpath += " or league='"+pinnacle_league_value+"'"
                else:
                    league_xpath = "league='"+pinnacle_league_key+"'"
                    
                # get all the game (event) tags for this league (not live games)
                all_games = lxml_tree.xpath("//event[sporttype='"+sport_values[appvar_util.APPVAR_KEY_PINNACLE]+"' and IsLive='No']["+league_xpath+"]")
                
                for event_tag in all_games:
                    # convert game datetime string to standard GMT datettime object
                    date_GMT = datetime.strptime(event_tag.find('event_datetimeGMT').text, '%Y-%m-%d %H:%M')
                    
                    # when testing only scrape games within couple days
                    if sys_util.is_local():
                        if 172800 < (date_GMT - datetime.utcnow()).total_seconds():
                            continue
                    
                    participants = event_tag.xpath('./participants/participant')
                    participant_name_home = participant_name_visiting = None
                    participant_rot_num_home = participant_rot_num_visiting = None
                    # get both teams information
                    for participant_tag in participants:
                        participant_side = unicode(participant_tag.find('visiting_home_draw').text)
                        
                        if participant_side == 'Visiting':
                            participant_name_visiting = unicode(participant_tag.find('participant_name').text)
                            participant_rot_num_visiting = int(participant_tag.find('rotnum').text)
                        elif participant_side == 'Home':
                            participant_name_home = unicode(participant_tag.find('participant_name').text)
                            participant_rot_num_home = int(participant_tag.find('rotnum').text)
                    
                    # skip test cases
                    if re.match('^TEST\s?\d', participant_name_visiting, re.IGNORECASE):
                        continue
                    # also skip grand salami cases
                    elif participant_name_visiting.split(' ')[0].lower() == 'away' and participant_name_home.split(' ')[0].lower() == 'home':
                        continue
                    # also skip pinnacle being stupid
                    elif (
                          participant_name_visiting == '2nd Half Wagering' 
                          or participant_name_home == '2nd Half Wagering'
                          or 'Pre-Game Wagering' in participant_name_visiting 
                          or 'Will Be Available For' in participant_name_home
                      ):
                        continue
                    
                    total_points = total_over_odds = total_under_odds = None
                    period_moneyline_home = period_moneyline_visiting = period_moneyline_draw = None
                    period_spread_home = period_spread_visiting = period_spread_adjust_home = period_spread_adjust_visiting = None
                    
                    is_full_game = False
                    for period in event_tag.xpath('./periods/period'):
                        # currently only interested in full game lines
                        if (
                            (
                             period.find('period_number').text.isdigit() 
                             and int(period.find('period_number').text) == 0
                             ) 
                            or unicode(period.find('period_description').text) in ['Game','Match']
                        ):
                            is_full_game = True
                            
                            # get the total lines
                            period_total = period.find('total')
                            if period_total is not None:
                                total_points = unicode(period_total.find('total_points').text)
                                total_over_odds = unicode(period_total.find('over_adjust').text)
                                total_under_odds = unicode(period_total.find('under_adjust').text)
                                    
                            # get the moneyline
                            period_moneyline = period.find('moneyline')
                            if period_moneyline is not None:
                                period_moneyline_home = unicode(period_moneyline.find('moneyline_home').text)
                                period_moneyline_visiting = unicode(period_moneyline.find('moneyline_visiting').text)
                                try:
                                    period_moneyline_draw = unicode(period_moneyline.find('moneyline_draw').text)
                                except AttributeError:
                                    pass
                                
                            period_spread = period.find('spread')
                            if period_spread is not None:
                                period_spread_home = unicode(period_spread.find('spread_home').text)
                                period_spread_visiting = unicode(period_spread.find('spread_visiting').text)
                                period_spread_adjust_home = unicode(period_spread.find('spread_adjust_home').text)
                                period_spread_adjust_visiting = unicode(period_spread.find('spread_adjust_visiting').text)
                            
                            break
                        
                    # not a full game tag, skip
                    if is_full_game is not True:
                        continue
                    
                    event = BookieScrapeData()
                    event.line_datetime = pinnacle_feed_time
                    event.datetime = date_GMT
                    event.sport = sport_key
                    event.league = league_key
                    event.team_away = participant_name_visiting
                    event.team_home = participant_name_home
                    event.rot_away = participant_rot_num_visiting
                    event.rot_home = participant_rot_num_home
                    event.spread_away = {event.LINE_KEY_POINTS : period_spread_visiting, event.LINE_KEY_ODDS : period_spread_adjust_visiting}
                    event.spread_home = {event.LINE_KEY_POINTS : period_spread_home, event.LINE_KEY_ODDS : period_spread_adjust_home}
                    event.moneyline_away = period_moneyline_visiting
                    event.moneyline_home = period_moneyline_home
                    event.moneyline_draw = period_moneyline_draw
                    event.total_over = {event.LINE_KEY_POINTS : total_points, event.LINE_KEY_ODDS : total_over_odds}
                    event.total_under = {event.LINE_KEY_POINTS : total_points, event.LINE_KEY_ODDS : total_under_odds}
                    
                    events_by_sport_league[sport_key][league_key].append(event)
        return events_by_sport_league

sys.path.append('libs/'+constants.LIB_DIR_PYTZ)
import pytz

# TODO: Xscores and ScoresPro should have a common parent class below general Scraper class
class XscoresScraper(ScoreboardScraper):
    __XSCORES_FEED = 'xscores.com'
    _timezone = pytz.timezone(constants.TIMEZONE_SCOREBOARD)
    
    _STATUS_FINISHED = 'Fin'
    
    def __init__(self, sport_key):
        self.sport_key = sport_key
        self._scores_by_date = {}
        
    def convert_utc_to_local(self, dataDatetime):
        return dataDatetime.replace(tzinfo=pytz.utc).astimezone(self._timezone)
    
    def is_complete(self, status):
        if status in [
                      self._STATUS_FINISHED, 
                      'Post',
                      ]:
            return True
        return False
    
    def is_live(self, status):
        if status in [
                      'Live',
                      ]:
            return True
        return False
    
    @sys_util.function_timer()
    def scrape(self, dataDatetime):
        scoreboard_game_time = self.convert_utc_to_local(dataDatetime)
        scoreboard_date_string = scoreboard_game_time.strftime('%d-%m')
        
        # have we gotten the scoreboard for this day before
        # only get it if we don't already have it
        if not scoreboard_date_string in self._scores_by_date:
            self._scores_by_date[scoreboard_date_string] = []
            score_row_key_indices = {}
            
            feed_url = 'http://www.'+self.__XSCORES_FEED+'/'+appvar_util.get_sport_names_appvar()[self.sport_key][appvar_util.APPVAR_KEY_SCOREBOARD]+'/finished_games/'+scoreboard_date_string
        
            soup = requests_util.request(
                                  request_lib        = requests_util.REQUEST_LIB_REQUESTS, 
                                  response_type      = requests_util.RESPONSE_TYPE_HTML, 
                                  response_encoding  = None, 
                                  min_wait_time       = 8.2, 
                                  max_wait_time       = 15.5, 
                                  max_hits           = len(appvar_util.get_sport_names_appvar()),
                                  url               = feed_url,
                                  headers           = sys_util.get_header()
                                  )
            
            if not soup:
                return self._scores_by_date[scoreboard_date_string]
            
            scores_rows = None
            
            # get the results table
            score_header = soup.find('tbody', {'id' : 'scoretable'}).find('tr', {'id' : 'finHeader'})
            if len(score_row_key_indices) < 5:
                score_header_columns = score_header.find_all('td', recursive=False)
                index_offset = 0
                for index, score_header_column in enumerate(score_header_columns):
                    if score_header_column.has_attr('colspan'):
                        index_offset += int(score_header_column['colspan']) - 1
                    score_header_column_text = score_header_column.get_text().strip()
                    if score_header_column_text in ['K/O', 'League', 'Stat', 'Home', 'Away', 'FT', 'FINAL', 'R']:
                        score_row_key_indices[score_header_column_text] = index + index_offset
            
            if len(score_row_key_indices) < 6:
                raise ScrapeException('Attempted to get XSCORES feed for %s of %s, but encountered improperly formatted table headers.' % (
                                                                                                                                           self.sport_key,
                                                                                                                                           scoreboard_date_string
                                                                                                                                           ))
                
            header_column_count = index + index_offset + 1
            
            scores_rows = score_header.find_next_siblings('tr')
            for score_row in scores_rows:
                if not score_row.has_attr('id'):
                    continue
                
                row_columns = score_row.find_all('td', recursive=False)
                if len(row_columns) != header_column_count:
                    # blank or otherwise invalid row
                    continue
                
                row_league = row_columns[score_row_key_indices['League']].get_text().strip()
                row_game_time = self._timezone.localize(datetime.strptime(scoreboard_game_time.strftime('%m-%d-%Y') + ' ' + row_columns[score_row_key_indices['K/O']].get_text().replace('(','').replace(')','').strip(), '%m-%d-%Y %H:%M'))
                row_home_team = row_columns[score_row_key_indices['Home']].get_text().strip()
                row_away_team = row_columns[score_row_key_indices['Away']].get_text().strip()
                row_game_status = row_columns[score_row_key_indices['Stat']].get_text().strip()
                
                extra_time = False
                row_home_reg_score = row_away_reg_score = None
                row_home_final_score = row_away_final_score = None
                if row_game_status == self._STATUS_FINISHED:
                    if self.sport_key == 'Baseball':
                        if score_row_key_indices['Home'] < score_row_key_indices['Away']:
                            row_home_final_score = row_columns[score_row_key_indices['R'] - 1].get_text().strip()
                            row_away_final_score = row_columns[score_row_key_indices['R']].get_text().strip()
                        else:
                            row_home_final_score = row_columns[score_row_key_indices['R']].get_text().strip()
                            row_away_final_score = row_columns[score_row_key_indices['R'] - 1].get_text().strip()
                            
                        row_home_reg_score = row_home_final_score
                        row_away_reg_score = row_away_final_score
                    else:
                        row_FT_score = row_columns[score_row_key_indices['FT']].get_text().strip()
                        row_FINAL_score = None
                        if 'FINAL' in score_row_key_indices:
                            row_FINAL_score = row_columns[score_row_key_indices['FINAL']].get_text().strip()
                            
                        row_FT_split_scores = row_FT_score.split('-')
                        if row_FINAL_score is not None and row_FINAL_score != row_FT_score:
                            extra_time = True
                            row_FINAL_split_scores = row_FINAL_score.split('-')
                            if score_row_key_indices['Home'] < score_row_key_indices['Away']:
                                row_home_reg_score = row_FT_split_scores[0].strip()
                                row_away_reg_score = row_FT_split_scores[1].strip()
                                row_home_final_score = row_FINAL_split_scores[0].strip()
                                row_away_final_score = row_FINAL_split_scores[1].strip()
                            else:
                                row_home_reg_score = row_FT_split_scores[1].strip()
                                row_away_reg_score = row_FT_split_scores[0].strip()
                                row_home_final_score = row_FINAL_split_scores[1].strip()
                                row_away_final_score = row_FINAL_split_scores[0].strip()
                        else:
                            if score_row_key_indices['Home'] < score_row_key_indices['Away']:
                                row_home_final_score = row_FT_split_scores[0].strip()
                                row_away_final_score = row_FT_split_scores[1].strip()
                            else:
                                row_home_final_score = row_FT_split_scores[1].strip()
                                row_away_final_score = row_FT_split_scores[0].strip()
                                
                            row_home_reg_score = row_home_final_score
                            row_away_reg_score = row_away_final_score
                
                score_row_obj = ScoreRowData()
                score_row_obj.sport = self.sport_key
                score_row_obj.league = row_league
                score_row_obj.datetime = row_game_time
                score_row_obj.team_away = row_away_team
                score_row_obj.team_home = row_home_team
                score_row_obj.status = row_game_status
                score_row_obj.regulation_score_away = row_away_reg_score
                score_row_obj.regulation_score_home = row_home_reg_score
                score_row_obj.final_score_away = row_away_final_score
                score_row_obj.final_score_home = row_home_final_score
                score_row_obj.extra_time = extra_time
                
                self._scores_by_date[scoreboard_date_string].append(score_row_obj)
        return self._scores_by_date[scoreboard_date_string]
    
class ScoresProScraper(ScoreboardScraper):
    __FEED = 'scorespro.com'
    _timezone = pytz.timezone(constants.TIMEZONE_BACKUP)
    
    def __init__(self, sport_key, league_key):
        self.sport_key = sport_key
        self.league_key = league_key
        self._scores_by_date = {}
        
    def convert_utc_to_local(self, dataDatetime):
        return dataDatetime.replace(tzinfo=pytz.utc).astimezone(self._timezone)
    
    def is_complete(self, status):
        if status in [
                      'FT', 
                      'Pst',
                      ]:
            return True
        return False
    
    def is_live(self, status):
        if status in [
                      ]:
            return True
        return False
    
    @sys_util.function_timer()
    def scrape(self, dataDatetime):
        scoreboard_game_time = self.convert_utc_to_local(dataDatetime)
        scoreboard_date_string = scoreboard_game_time.strftime('%a %d %b %Y')
        
        # have we gotten the scoreboard for this day before
        # only get it if we don't already have it
        if not scoreboard_date_string in self._scores_by_date:
            self._scores_by_date[scoreboard_date_string] = []
            
            feed_url = 'http://www.'+self.__FEED+'/'+appvar_util.get_sport_names_appvar()[self.sport_key][appvar_util.APPVAR_KEY_SCOREBOARD]+'/'+appvar_util.get_league_names_appvar()[self.sport_key][self.league_key][appvar_util.APPVAR_KEY_SCOREBOARD]
            
            soup = requests_util.request(
                                  request_lib        = requests_util.REQUEST_LIB_REQUESTS, 
                                  response_type      = requests_util.RESPONSE_TYPE_HTML, 
                                  response_encoding  = requests_util.RESPONSE_ENCODING_UTF8, 
                                  min_wait_time       = 8.2, 
                                  max_wait_time       = 15.5, 
                                  max_hits           = len(appvar_util.get_sport_names_appvar()),
                                  url               = feed_url,
                                  headers           = sys_util.get_header()
                                  )
            
            if soup:
                results_table = soup.find('div', {'id' : 'national'}).find('table')
                score_tables = []
                for results_table_row in results_table.next_siblings:
                    try:
                        if results_table_row.name == 'div':
                            score_tables.append(results_table_row)
                        elif results_table_row.name == 'table':
                            break
                    except AttributeError:
                        pass
                
                scores_rows = []
                correct_date = False
                for score_table_row in score_tables:
                    row_date = score_table_row.find('li', {'class' : 'ncet_date'})
                    if row_date:
                        if correct_date is False:
                            if row_date.get_text().strip() == scoreboard_date_string:
                                correct_date = True
                            elif len(scores_rows) > 0:
                                break
                        else:
                            break
                    elif correct_date is True:
                        if score_table_row.find('table'):
                            scores_rows += score_table_row.find_all('table', recursive=False)
                            correct_date = False
                
                for score_row in scores_rows:
                    row_status = score_row.find('td', {'class' : 'status'}).get_text().strip()
                    
                    row_game_time = self._timezone.localize(datetime.strptime(scoreboard_date_string + ' ' + score_row.find('td', {'class' : 'datetime'}).get_text().replace('(','').replace(')','').strip(), '%a %d %b %Y %H:%M'))
                    
                    row_teams = score_row.find_all('tr')
                    row_home_team = row_teams[0].find('td', {'class' : 'hometeam'}).get_text().strip()
                    row_away_team = row_teams[1].find('td', {'class' : 'awayteam'}).get_text().strip()
                    
                    row_score_home = row_teams[0].find('td', {'class' : 'ts_setB'}).get_text().strip()
                    row_score_away = row_teams[1].find('td', {'class' : 'ts_setB'}).get_text().strip()
                
                    score_row_obj = ScoreRowData()
                    score_row_obj.sport = self.sport_key
                    score_row_obj.league = self.league_key
                    score_row_obj.datetime = row_game_time
                    score_row_obj.team_away = row_away_team
                    score_row_obj.team_home = row_home_team
                    score_row_obj.status = row_status
                    score_row_obj.regulation_score_away = row_score_away
                    score_row_obj.regulation_score_home = row_score_home
                    score_row_obj.final_score_away = row_score_away
                    score_row_obj.final_score_home = row_score_home
                    score_row_obj.extra_time = False
                
                    self._scores_by_date[scoreboard_date_string].append(score_row_obj)
        return self._scores_by_date[scoreboard_date_string]