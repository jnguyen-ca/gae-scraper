#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.insert(0, 'libs')

from google.appengine.ext import webapp, ndb
from google.appengine.api import mail, urlfetch, memcache

from models import Tip, TipChange

# from _symtable import LOCAL

from httplib import HTTPException
from datetime import datetime, timedelta
from timeit import itertools
from bs4 import BeautifulSoup
from bs4.element import Tag as bs4_Tag
from lxml import etree

import re
import json
import time
import random
import logging
import requests
import constants
import teamconstants

def get_team_aliases(sport, league, team_name):
    # remove the game digit to get correct team name aliases
    doubleheader_search = re.search('^G\d+\s+(.+)', team_name)
    if doubleheader_search:
        team_name = doubleheader_search.group(1).strip()
    
    team_aliases = [team_name]
    
    if sport not in teamconstants.TEAMS or league not in teamconstants.TEAMS[sport]:
        logging.warning(league+' for '+sport+' has no team information (1)!')
        return team_aliases, None
    
    league_team_info = teamconstants.TEAMS[sport][league]
    if isinstance(league_team_info, basestring):
        # reference to another league information
        league_team_info = teamconstants.TEAMS[sport][league_team_info]
    
    if (
        'keys' not in league_team_info 
        or 'values' not in league_team_info 
        ):
        logging.warning(league+' for '+sport+' has no team information (2)!')
        return team_aliases, None
    
    # get all team aliases
    team_id = None
    if team_name in league_team_info['keys']:
        team_id = league_team_info['keys'][team_name]
        if team_id in league_team_info['values']:
            team_aliases += league_team_info['values'][team_id]
    else:
        logging.warning(team_name+' in '+league+' for '+sport+' has no team id!')
        
    return team_aliases, team_id

class Scraper(webapp.RequestHandler):
    def get(self):
        self.FEED = {}
        self.REQUEST_COUNT = {constants.PINNACLE_FEED : 0, constants.WETTPOINT_FEED: 0, constants.XSCORES_FEED : 0, constants.BACKUP_SCORES_FEED : 0}
        #sys.stderr.write("ARRRRGHH")
        #sys.stderr.write("\n")
        #reload(sys)
        #sys.setdefaultencoding('utf-8')
        #sys.stderr = codecs.getwriter('utf8')(sys.stderr)
        
        self.WARNING_MAIL = False
        self.MAIL_BODY = False
        self.PPD_MAIL_BODY = False
        
        urlfetch.set_default_fetch_deadline(30)
        
        new_or_updated_tips = {}
        try:
            new_or_updated_tips = self.find_games()
        except HTTPException:
            logging.warning('Pinnacle XML feed down')
            
        update_tips = self.fill_games(new_or_updated_tips)
        #self.response.out.write(self.print_items())
         
        self.commit_tips(update_tips)
        
        if self.WARNING_MAIL != False:
            mail.send_mail('BlackCanine@gmail.com', 'BlackCanine@gmail.com', 'WARNING Notice', self.WARNING_MAIL)
            
        if self.MAIL_BODY != False:
            mail.send_mail('BlackCanine@gmail.com', 'BlackCanine@gmail.com', 'Tip Change Notice', self.MAIL_BODY)
            
        if self.PPD_MAIL_BODY != False:
            mail.send_mail('BlackCanine@gmail.com', 'BlackCanine@gmail.com', 'Tip Limbo Notice', self.PPD_MAIL_BODY)
        
        self.response.out.write('<br />')
        logging_info = ''
        for x in self.REQUEST_COUNT:
            logging_info += x + ' : ' + str(self.REQUEST_COUNT[x]) + '; '
            self.response.out.write(x + ' : ' + str(self.REQUEST_COUNT[x]))
            
            if int(self.REQUEST_COUNT[x]) > 20:
                mail.send_mail('BlackCanine@gmail.com', 'BlackCanine@gmail.com', 'Scrape Abuse WARNING', x + ' being hit: ' + str(self.REQUEST_COUNT[x]))
            
            self.response.out.write('<br />')
        logging.info(logging_info)
    
    def commit_tips(self, update_tips):
        ndb.put_multi(update_tips.values())
        
    def fill_games(self, new_or_updated_tips):
        """Now with all the games stored as incomplete Tip objects, fill out the lines and stuff
        """
        wettpoint_check_tables_sport = []
        wettpoint_tables_memcache = memcache.get('lastWettpointTablesInfo')
        
        if wettpoint_tables_memcache:
            for sport_key in constants.SPORTS:
                if sport_key not in wettpoint_check_tables_sport and sport_key in wettpoint_tables_memcache:
                    sport_wettpoint_memcache = wettpoint_tables_memcache[sport_key]
                    
                    sport_updated = sport_wettpoint_memcache['time_updated']
                    sport_minutes_between_checks = sport_wettpoint_memcache['minutes_between_checks']
                    
                    if sport_wettpoint_memcache['tip_changed'] is True:
                        logging.debug('Checking '+sport_key+' due to last change')
                        wettpoint_check_tables_sport.append(sport_key)
                    elif sport_wettpoint_memcache['h2h_limit_reached'] is True:
                        logging.debug('Checking '+sport_key+' due to H2H limit reached')
                        wettpoint_check_tables_sport.append(sport_key)
                    elif divmod((datetime.utcnow() - datetime.strptime(sport_updated, '%d.%m.%Y %H:%M')).total_seconds(), 60)[0] > sport_minutes_between_checks:
                        logging.debug('Checking '+sport_key+' due to expiration ('+str(sport_minutes_between_checks)+'min since '+sport_updated+')')
                        wettpoint_check_tables_sport.append(sport_key)
                elif sport_key not in wettpoint_tables_memcache:
                    wettpoint_check_tables_sport.append(sport_key)
        else:
            logging.debug('Checking all sports due to memcache expiration')
            for sport_key in constants.SPORTS:
                if sport_key not in wettpoint_check_tables_sport:
                    wettpoint_check_tables_sport.append(sport_key)
        
        # get all non-elapsed datastore entities so we can store current lines and wettpoint data
        not_elapsed_tips_by_sport_league = {}
        for sport_key in constants.SPORTS:
            query = Tip.gql('WHERE elapsed != True AND game_sport = :1', sport_key)
            for tip_instance in query:
                if sport_key not in not_elapsed_tips_by_sport_league:
                    not_elapsed_tips_by_sport_league[sport_key] = {}
                if tip_instance.game_league not in not_elapsed_tips_by_sport_league[sport_key]:
                    not_elapsed_tips_by_sport_league[sport_key][tip_instance.game_league] = {}
                # use cached entity if new or updated by pinnacle scrape
                key_string = unicode(tip_instance.key.urlsafe())
                if key_string in new_or_updated_tips:
                    tip_instance = new_or_updated_tips[key_string].get()
                    not_elapsed_tips_by_sport_league[sport_key][tip_instance.game_league][key_string] = tip_instance
                    
                    if sport_key not in wettpoint_check_tables_sport:
                        logging.debug('Checking '+sport_key+' due to new tip')
                        wettpoint_check_tables_sport.append(sport_key)
                else:
                    not_elapsed_tips_by_sport_league[sport_key][tip_instance.game_league][key_string] = tip_instance
                    
                if sport_key not in wettpoint_check_tables_sport:
                    minutes_until_start = divmod((tip_instance.date - datetime.now()).total_seconds(), 60)[0]
                    if minutes_until_start <= 180:
                        logging.debug('Checking '+sport_key+' starting within 3 hours')
                        wettpoint_check_tables_sport.append(sport_key)
                    elif tip_instance.wettpoint_tip_stake is None:
                        if wettpoint_tables_memcache and sport_key in wettpoint_tables_memcache:
                            first_event_UTC_time = datetime.strptime(wettpoint_tables_memcache[sport_key]['first_event_time'], '%d.%m.%Y %H:%M') - timedelta(hours=2)
                            
                            if ((first_event_UTC_time - timedelta(minutes=15)) - datetime.utcnow()).total_seconds() <= 0:
                                logging.debug('Checking '+sport_key+' for updated table (UTC: '+first_event_UTC_time.strftime('%d.%m.%Y %H:%M')+')')
                                wettpoint_check_tables_sport.append(sport_key)
                        else:
                            wettpoint_check_tables_sport.append(sport_key)
                    
        not_archived_tips_by_sport_league = {}
        for sport_key, sport_leagues in constants.LEAGUES.iteritems():
            for league_key in sport_leagues:
                query = Tip.gql('WHERE elapsed = True AND archived != True AND game_league = :1', league_key)
                for tip_instance in query:
                    if sport_key not in not_archived_tips_by_sport_league:
                        not_archived_tips_by_sport_league[sport_key] = {}
                    if league_key not in not_archived_tips_by_sport_league[sport_key]:
                        not_archived_tips_by_sport_league[sport_key][league_key] = {}
                    not_archived_tips_by_sport_league[sport_key][league_key][unicode(tip_instance.key.urlsafe())] = tip_instance
                    
        for index, sport_key in enumerate(wettpoint_check_tables_sport):
            if sport_key not in not_elapsed_tips_by_sport_league:
                del wettpoint_check_tables_sport[index]
        
        not_elapsed_tips_by_sport_league = self.fill_wettpoint_tips(not_elapsed_tips_by_sport_league, not_archived_tips_by_sport_league, wettpoint_check_tables_sport)
        not_elapsed_tips_by_sport_league, possible_ppd_tips_by_sport_league = self.fill_lines(not_elapsed_tips_by_sport_league)
        
        archived_tips = {}
        try:
            archived_tips = self.fill_scores(not_archived_tips_by_sport_league, possible_ppd_tips_by_sport_league)
        except HTTPException:
            logging.warning('Scoreboard feed down')
            
        update_tips = {}
        for not_elapsed_tips_by_league in not_elapsed_tips_by_sport_league.values():
            for not_elapsed_tips in not_elapsed_tips_by_league.values():
                for tip_instance_key, tip_instance in not_elapsed_tips.iteritems():
                    if tip_instance_key in update_tips:
                        raise Exception(tip_instance_key+' appears more than once in not_elapsed_tips?!')
                    update_tips[tip_instance_key] = tip_instance
        for tip_instance_key, tip_instance in archived_tips.iteritems():
            if tip_instance_key in update_tips:
                raise Exception(tip_instance_key+' duplicate located in archived_tips?!')
            update_tips[tip_instance_key] = tip_instance
        return update_tips
        
    def fill_scores(self, not_archived_tips_by_sport_league, possible_ppd_tips_by_sport_league):
        archived_tips = {}
        for sport_key, sport_leagues in constants.LEAGUES.iteritems():
            scores_by_date = {}
            score_row_key_indices = {}
            for league_key, values in sport_leagues.iteritems():
                if 'scoreboard' not in values:
                    continue
                
                all_tip_check_scores = []
                if (
                    sport_key in not_archived_tips_by_sport_league 
                    and league_key in not_archived_tips_by_sport_league[sport_key]
                    ):
                    all_tip_check_scores += not_archived_tips_by_sport_league[sport_key][league_key].values()
                if (
                    sport_key in possible_ppd_tips_by_sport_league 
                    and league_key in possible_ppd_tips_by_sport_league[sport_key]
                    ):
                    all_tip_check_scores += possible_ppd_tips_by_sport_league[sport_key][league_key].values()
                
                league = values['scoreboard']
                
                if sport_key == 'Handball':
                    archived_tips, scores_by_date = self.fill_handball_scores(archived_tips, scores_by_date, all_tip_check_scores, sport_key, league_key)
                    continue
                
                # go through all non-archived tips that have already begun
                for tip_instance in all_tip_check_scores:
                    scoreboard_game_time = tip_instance.date + timedelta(hours = 3)
                    
                    # have we gotten the scoreboard for this day before
                    # only get it if we don't already have it
                    scoreboard_date_string = scoreboard_game_time.strftime('%d-%m')
                    
                    if not scoreboard_date_string in scores_by_date:
                        scores_by_date[scoreboard_date_string] = []
                        
                        logging.debug('scraping scoreboard for '+scoreboard_game_time.strftime('%d-%m %H:%M')+' | '+tip_instance.game_team_away+' @ '+tip_instance.game_team_home)
                        feed_url = 'http://www.'+constants.XSCORES_FEED+'/'+constants.SPORTS[sport_key]['scoreboard']+'/finished_games/'+scoreboard_date_string
                    
                        self.REQUEST_COUNT[constants.XSCORES_FEED] += 1
                        if self.REQUEST_COUNT[constants.XSCORES_FEED] > 1:
                            time.sleep(random.uniform(8.2, 15.5))
                        
                        feed_html = requests.get(feed_url, headers=constants.get_header())
                        soup = BeautifulSoup(feed_html.text)
                        
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
                                if score_header_column_text in ['K/O', 'League', 'Stat', 'Home', 'Away']:
                                    score_row_key_indices[score_header_column_text] = index + index_offset
                                    
                                if len(score_row_key_indices) == 5:
                                    break
                        
                        if len(score_row_key_indices) < 5:
                            logging.warning(sport_key+' score header indices not adding up!')
                            break
                        
                        scores_rows = score_header.find_next_siblings('tr')
                        for score_row in scores_rows:
                            if not score_row.has_attr('id'):
                                continue
                            
                            scores_by_date[scoreboard_date_string].append(score_row)
                            
                    # remove the game digit before committing (only if scores get successfully scraped)    
                    doubleheader_search = re.search('^G(\d+)\s+(.+)', tip_instance.game_team_away)
                    if doubleheader_search:
                        game_digit = int(doubleheader_search.group(1))
                        tip_instance.game_team_away = doubleheader_search.group(2).strip()
                        tip_instance.game_team_home = re.search('^G\d+\s+(.+)', tip_instance.game_team_home).group(1).strip()
                    else:
                        game_digit = False
                    
                    # get all team aliases
                    team_home_aliases = get_team_aliases(sport_key, league_key, tip_instance.game_team_home)[0]
                    team_away_aliases = get_team_aliases(sport_key, league_key, tip_instance.game_team_away)[0]
                        
                    # should now have the scoreboard for this date, if not something went wrong    
                    score_date_rows = None
                    if scoreboard_date_string in scores_by_date:
                        score_date_rows = scores_by_date[scoreboard_date_string]
                          
                    for score_row in score_date_rows:
                        row_columns = score_row.find_all('td', recursive=False)
                        
                        # should be the correct league
                        row_league = row_columns[score_row_key_indices['League']].get_text().strip()
                        if isinstance(league, list):
                            if row_league not in league:
                                continue
                        else:
                            if row_league != league:
                                continue
                        
                        row_game_time = datetime.strptime(scoreboard_game_time.strftime('%m-%d-%Y') + ' ' + row_columns[score_row_key_indices['K/O']].get_text().replace('(','').replace(')','').strip(), '%m-%d-%Y %H:%M')
                        row_home_team = row_columns[score_row_key_indices['Home']].get_text().strip()
                        row_away_team = row_columns[score_row_key_indices['Away']].get_text().strip()
                        
                        # row should have same time (30 minute error window) and team names
                        time_difference = row_game_time - scoreboard_game_time
                        if abs(divmod(time_difference.total_seconds(), 60)[0]) <= 15:
                            if row_away_team.strip().upper() in (name.upper() for name in team_away_aliases):
                                if row_home_team.strip().upper() in (name.upper() for name in team_home_aliases):
                                    row_game_status = row_columns[score_row_key_indices['Stat']].get_text().strip()
                                    
                                    if row_game_status == 'Fin':
                                        row_game_bolds = score_row.find_all('b')
                                        row_last_bold = row_game_bolds[-1].get_text().strip()
                                        
                                        # should have both sides' scores
                                        if '-' not in row_last_bold:
                                            if score_row_key_indices['Home'] < score_row_key_indices['Away']:
                                                row_home_score = row_game_bolds[-2].get_text().strip()
                                                row_away_score = row_last_bold
                                            else:
                                                row_home_score = row_last_bold
                                                row_away_score = row_game_bolds[-2].get_text().strip()
                                        else:
                                            row_scores = row_last_bold.split('-')
                                            if score_row_key_indices['Home'] < score_row_key_indices['Away']:
                                                row_home_score = row_scores[0].strip()
                                                row_away_score = row_scores[1].strip()
                                            else:
                                                row_home_score = row_scores[1].strip()
                                                row_away_score = row_scores[0].strip()
                                        
                                        tip_instance.score_home = row_home_score
                                        tip_instance.score_away = row_away_score
                                    elif row_game_status != 'Abd' and row_game_status != 'Post' and row_game_status != 'Canc':
                                        break
                                    
                                    tip_instance.archived = True
                                    
                                    # commit
                                    archived_tips[unicode(tip_instance.key.urlsafe())] = tip_instance
                                    break
                                else:
                                    if self.WARNING_MAIL is False:
                                        self.WARNING_MAIL = ''
                                    else:
                                        self.WARNING_MAIL += "\n"
                                    self.WARNING_MAIL += 'Probable ' + str(row_home_team) + ' SCOREBOARD NAMES for ' + league_key + ', ' + sport_key + ' MISMATCH!' + "\n"
                            elif row_home_team.strip().upper() in (name.upper() for name in team_home_aliases):
                                if self.WARNING_MAIL is False:
                                    self.WARNING_MAIL = ''
                                else:
                                    self.WARNING_MAIL += "\n"
                                self.WARNING_MAIL += 'Probable ' + str(row_away_team) + ' SCOREBOARD NAMES for ' + league_key + ', ' + sport_key + ' MISMATCH!' + "\n"
                            
                    # if tip is not archived and it's over a day old... something is probably wrong
                    if (
                        tip_instance.archived != True 
                        and (datetime.now() - tip_instance.date).total_seconds() > 86400
                        ):
                        if self.PPD_MAIL_BODY is False:
                            self.PPD_MAIL_BODY = ''
                        else:
                            self.PPD_MAIL_BODY = self.PPD_MAIL_BODY + "\n\n"
                            
                        self.PPD_MAIL_BODY = self.PPD_MAIL_BODY + (tip_instance.date - timedelta(hours = 6)).strftime('%B-%d %I:%M%p') + " " + tip_instance.game_team_away + " @ " + tip_instance.game_team_home
                        
        return archived_tips
    
    def fill_handball_scores(self, archived_tips, scores_by_date, all_tip_check_scores_by_league, sport_key, league_key):
        for tip_instance in all_tip_check_scores_by_league:
            scoreboard_game_time = tip_instance.date + timedelta(hours = 1)
            scoreboard_date_string = scoreboard_game_time.strftime('%a %d %b %Y')
                
            if not tip_instance.game_league in scores_by_date:
                scores_by_date[tip_instance.game_league] = []
                
                logging.debug('scraping scoreboard for '+scoreboard_game_time.strftime('%d-%m %H:%M')+' | '+tip_instance.game_team_away+' @ '+tip_instance.game_team_home)
                feed_url = 'http://www.'+constants.BACKUP_SCORES_FEED+'/'+constants.SPORTS[sport_key]['scoreboard']+'/'+constants.LEAGUES[sport_key][league_key]['scoreboard']
            
                self.REQUEST_COUNT[constants.BACKUP_SCORES_FEED] += 1
                if self.REQUEST_COUNT[constants.BACKUP_SCORES_FEED] > 1:
                    time.sleep(random.uniform(8.2, 15.5))
                
                feed_html = requests.get(feed_url, headers=constants.get_header())
                feed_html.encoding = 'utf-8'
                soup = BeautifulSoup(feed_html.text)
                
                results_table = soup.find('div', {'id' : 'national'}).find('table')
                score_tables = []
                for results_table_row in results_table.next_siblings:
                    if isinstance(results_table_row, bs4_Tag) and results_table_row.name == 'div':
                        score_tables.append(results_table_row)
                    elif isinstance(results_table_row, bs4_Tag) and results_table_row.name == 'table':
                        break
                
                scores_by_date[tip_instance.game_league] = score_tables
            else:
                score_tables = scores_by_date[tip_instance.game_league]
                
            # remove the game digit before committing (only if scores get successfully scraped)    
            doubleheader_search = re.search('^G(\d+)\s+(.+)', tip_instance.game_team_away)
            if doubleheader_search:
                tip_instance.game_team_away = doubleheader_search.group(2).strip()
                tip_instance.game_team_home = re.search('^G\d+\s+(.+)', tip_instance.game_team_home).group(1).strip()
            
            # get all team aliases
            team_home_aliases = get_team_aliases(sport_key, league_key, tip_instance.game_team_home)[0]
            team_away_aliases = get_team_aliases(sport_key, league_key, tip_instance.game_team_away)[0]
            
            scores_rows = []
            correct_date = False
            for score_table_row in score_tables:
                row_date = score_table_row.find('li', {'class' : 'ncet_date'})
                if row_date:
                    if correct_date is False:
                        if row_date.get_text().strip() == scoreboard_date_string:
                            correct_date = True
                    else:
                        break
                elif correct_date is True:
                    if score_table_row.find('table'):
                        scores_rows = score_table_row.find_all('table', recursive=False)
                        break
            
            for score_row in scores_rows:
                if score_row.find('td', {'class' : 'status'}).get_text().strip() != 'FT':
                    continue
                
                row_game_time = datetime.strptime(scoreboard_date_string + ' ' + score_row.find('td', {'class' : 'datetime'}).get_text().replace('(','').replace(')','').strip(), '%a %d %b %Y %H:%M')
                
                row_teams = score_row.find_all('tr')
                
                row_home_team = row_teams[0].find('td', {'class' : 'hometeam'}).get_text().strip()
                row_away_team = row_teams[1].find('td', {'class' : 'awayteam'}).get_text().strip()
                
                # row should have same time (30 minute error window) and team names
                time_difference = row_game_time - scoreboard_game_time
                if abs(divmod(time_difference.total_seconds(), 60)[0]) <= 15:
                    if row_away_team.strip().upper() in (name.upper() for name in team_away_aliases):
                        if row_home_team.strip().upper() in (name.upper() for name in team_home_aliases):
                            
                            tip_instance.score_home = row_teams[0].find('td', {'class' : 'ts_setB'}).get_text().strip()
                            tip_instance.score_away = row_teams[1].find('td', {'class' : 'ts_setB'}).get_text().strip()
                            
                            tip_instance.archived = True
                            
                            # commit
                            archived_tips[unicode(tip_instance.key.urlsafe())] = tip_instance
                            break
        
            # if tip is not archived and it's over a day old... something is probably wrong
            if (
                tip_instance.archived != True 
                and (datetime.now() - tip_instance.date).total_seconds() > 86400
                ):
                if self.PPD_MAIL_BODY is False:
                    self.PPD_MAIL_BODY = ''
                else:
                    self.PPD_MAIL_BODY = self.PPD_MAIL_BODY + "\n\n"
                    
                self.PPD_MAIL_BODY = self.PPD_MAIL_BODY + (tip_instance.date - timedelta(hours = 6)).strftime('%B-%d %I:%M%p') + " " + tip_instance.game_team_away + " @ " + tip_instance.game_team_home
        
        return archived_tips, scores_by_date

    def fill_wettpoint_tips(self, not_elapsed_tips_by_sport_league, not_archived_tips_by_sport_league, wettpoint_check_tables_sport):
        self.wettpoint_tables_memcache = memcache.get('lastWettpointTablesInfo')
        if not self.wettpoint_tables_memcache:
            self.wettpoint_tables_memcache = {}
        
        wettpoint_current_time = datetime.utcnow() + timedelta(hours = 2)
        wettpoint_current_date = wettpoint_current_time.strftime('%d.%m.%Y')
        # go through all our sports
        for sport_key in constants.SPORTS:
            if sport_key not in not_elapsed_tips_by_sport_league or sport_key not in wettpoint_check_tables_sport:
                continue
            
            # get wettpoint tip table page for particular sport
            sport = constants.SPORTS[sport_key]['wettpoint']
            feed = 'http://www.forum.'+constants.WETTPOINT_FEED+'/fr_toptipsys.php?cat='+sport
            
            self.REQUEST_COUNT[constants.WETTPOINT_FEED] += 1
            if self.REQUEST_COUNT[constants.WETTPOINT_FEED] > 1:
                time.sleep(random.uniform(9.9,30.1))
            
            html = requests.get(feed, headers=constants.get_header())
            soup = BeautifulSoup(html.text)
            
            # get the tip table for this sport
            tables = soup.find_all('table', {'class' : 'gen'})
            tip_table = tables[1]
            tip_rows = tip_table.find_all('tr')
            
            first_event_time = re.sub('[^0-9\.\s:]', '', tip_rows[2].find_all('td')[6].get_text())
            # format the tip time to a standard
            if not re.match('\d{2}\.\d{2}\.\d{4}', first_event_time):
                first_event_time = wettpoint_current_date + ' ' + first_event_time
            
            self.wettpoint_tables_memcache[sport_key] = {
                                                    'first_event_time' : first_event_time,
                                                    'time_updated' : datetime.utcnow().strftime('%d.%m.%Y %H:%M'),
                                                    'tip_changed' : False,
                                                    'minutes_between_checks' : 120,
                                                    'h2h_limit_reached' : False,
                                                    }
            
            for league_key in constants.LEAGUES[sport_key]:
                if league_key not in not_elapsed_tips_by_sport_league[sport_key]:
                    continue
                
                # now let's fill out those tips!
                for tip_instance in not_elapsed_tips_by_sport_league[sport_key][league_key].values():
                    tip_stake_changed = False
                    minutes_until_start = divmod((tip_instance.date - datetime.now()).total_seconds(), 60)[0]
                    
                    if minutes_until_start < 0:
                        # game has already begun, move on to next
                        tip_instance.elapsed = True
                        # set tip to be updated
                        not_elapsed_tips_by_sport_league[sport_key][league_key][unicode(tip_instance.key.urlsafe())] = tip_instance
                        continue
                    elif (
                          minutes_until_start < 20 
                          and tip_instance.wettpoint_tip_stake is not None
                          ):
                        # tip has already been filled out and table updated past tip time, move on to next to avoid resetting tip to 0
                        continue
                    elif not 'wettpoint' in constants.LEAGUES[tip_instance.game_sport][tip_instance.game_league]:
                        # constant missing league identifier?
                        logging.warning('no wettpoint scraping for '+tip_instance.game_league)
                        continue
                    
                    team_home_aliases = get_team_aliases(tip_instance.game_sport, tip_instance.game_league, tip_instance.game_team_home)[0]
                    team_away_aliases = get_team_aliases(tip_instance.game_sport, tip_instance.game_league, tip_instance.game_team_away)[0]
                    
                    matchup_finalized = False
                    if minutes_until_start <= 720:
                        if sport_key not in not_archived_tips_by_sport_league or league_key not in not_archived_tips_by_sport_league[sport_key] or len(not_archived_tips_by_sport_league[sport_key][league_key]) < 1:
                            matchup_finalized = self.matchup_data_finalized([tip_instance.game_team_away, tip_instance.game_team_home], tip_instance.date, not_elapsed_tips_by_sport_league[sport_key][league_key].values())
                    
#                     last_game_time = re.sub('[^0-9\.\s:]', '', tip_rows[-1].find_all('td')[6].get_text())
#                     # format the tip time to a standard
#                     if not re.match('\d{2}\.\d{2}\.\d{4}', last_game_time):
#                         wettpoint_current_time = datetime.utcnow() + timedelta(hours = 2)
#                         wettpoint_current_date = wettpoint_current_time.strftime('%d.%m.%Y')
#                          
#                         last_game_time = wettpoint_current_date + ' ' + last_game_time
#                          
#                     last_game_time = datetime.strptime(last_game_time, '%d.%m.%Y %H:%M') - timedelta(hours = 2)
#                     last_minutes_past_start = divmod((last_game_time - tip_instance.date).total_seconds(), 60)[0]
                    
                    # has the wettpoint tip been changed
                    tip_change_created = False
                    self.temp_holder = False
                    # go through the events listed
                    for tip_row in tip_rows[2:]:
                        columns = tip_row.find_all('td')
                        
                        # standard information to determine if tip is of interest
                        team_names = columns[0].get_text()
                        league_name = columns[5].get_text()
                        game_time = re.sub('[^0-9\.\s:]', '', columns[6].get_text())
                        
                        # format the tip time to a standard
                        if not re.match('\d{2}\.\d{2}\.\d{4}', game_time):
                            game_time = wettpoint_current_date + ' ' + game_time
                        
                        # set game time to UTC    
                        game_time = datetime.strptime(game_time, '%d.%m.%Y %H:%M') - timedelta(hours = 2)
                        row_minutes_past_start = divmod((game_time - tip_instance.date).total_seconds(), 60)[0]
                        
                        # is it a league we're interested in and does the game time match the tip's game time?
                        correct_league = False
                        
                        # is it the league of the tip object?
                        wettpoint_league_key = constants.LEAGUES[tip_instance.game_sport][tip_instance.game_league]['wettpoint']
                        if isinstance(wettpoint_league_key, list):
                            if league_name.strip() in wettpoint_league_key:
                                correct_league = True
                        else:
                            if league_name.strip() == wettpoint_league_key.strip():
                                correct_league = True
                        
                        # if the league is correct then does the time match (30 minute error window)    
                        if (
                            correct_league is True 
                            and abs(row_minutes_past_start) <= 15
                            ):
                            index = team_names.find('-')
                            home_team = team_names[0:index].strip()
                            away_team = team_names[index+1:len(team_names)].strip()
                            
                            # finally, are the teams correct?
                            if (
                                away_team.strip().upper() in (name.upper() for name in team_away_aliases) 
                                and home_team.strip().upper() in (name.upper() for name in team_home_aliases)
                                ):
                                # so now we know that this wettpoint tip (probably) refers to this tip object... yay!
                                tip_team = columns[1].get_text().strip()
                                tip_total = columns[2].get_text().strip()
                                tip_stake = columns[3].get_text()
                                tip_stake = float(tip_stake[0:tip_stake.find('/')])
                                
                                # team tip changed
                                if (
                                    tip_instance.wettpoint_tip_team is not None 
                                    and tip_instance.wettpoint_tip_team != tip_team
                                    ):
                                    tip_instance = self.create_tip_change_object(tip_instance, 'team', 'team_general', not tip_change_created)
                                    tip_change_created = True
                                
                                tip_instance.wettpoint_tip_team = tip_team
    
                                # tip is over
                                if tip_total.lower().find('over') != -1:
                                    # total tip changed
                                    if (
                                        tip_instance.total_lines is not None 
                                        and tip_instance.wettpoint_tip_total != 'Over'
                                        ):
                                        tip_instance = self.create_tip_change_object(tip_instance, 'total', 'total_over', not tip_change_created)
                                        tip_change_created = True
                                    
                                    tip_instance.wettpoint_tip_total = 'Over'
                                # tip is under
                                elif tip_total.lower().find('under') != -1:
                                    # total tip changed
                                    if (
                                        tip_instance.wettpoint_tip_total is not None 
                                        and tip_instance.wettpoint_tip_total != 'Under'
                                        ):
                                        tip_instance = self.create_tip_change_object(tip_instance, 'total', 'total_under', not tip_change_created)
                                        tip_change_created = True
                                    
                                    tip_instance.wettpoint_tip_total = 'Under'
                                
                                # stake tip changed
                                if (
                                    tip_instance.wettpoint_tip_stake is not None 
                                    and tip_instance.wettpoint_tip_stake != tip_stake 
                                    and int(tip_instance.wettpoint_tip_stake) != int(round(tip_stake))
                                    ):
                                    tip_instance = self.create_tip_change_object(tip_instance, 'stake', 'stake_chart', not tip_change_created)
                                    tip_change_created = True
                                    
                                    tip_stake_changed = True
                                    tip_instance.wettpoint_tip_stake = tip_stake
                                elif tip_instance.wettpoint_tip_stake is None:
                                    tip_stake_changed = True
                                    tip_instance.wettpoint_tip_stake = tip_stake
                                
                                if (
                                    sport_key not in constants.SPORTS_H2H_EXCLUDE 
                                    and tip_instance.wettpoint_tip_stake % 1 == 0 
                                    and (
                                         matchup_finalized 
                                         or tip_stake_changed is True 
                                         )
                                    ):
                                    tip_stake_changed = True
                                    tip_instance.wettpoint_tip_stake = self.add_wettpoint_h2h_details(tip_instance)
                                
                                break
                            # one of the team names matches but the other doesn't, send admin mail to check team names
                            # could either be 1) team name missing or 2) wettpoint has wrong game listed
                            elif home_team.strip().upper() in (name.upper() for name in team_home_aliases):
                                if self.WARNING_MAIL is False:
                                    self.WARNING_MAIL = ''
                                else:
                                    self.WARNING_MAIL += "\n"
                                self.WARNING_MAIL += 'Probable ' + away_team + ' WETTPOINT NAMES for ' + tip_instance.game_league + ', ' + tip_instance.game_sport + ' MISMATCH!' + "\n"
                            elif away_team.strip().upper() in (name.upper() for name in team_away_aliases):
                                if self.WARNING_MAIL is False:
                                    self.WARNING_MAIL = ''
                                else:
                                    self.WARNING_MAIL += "\n"
                                self.WARNING_MAIL += 'Probable ' + home_team + ' WETTPOINT NAMES for ' + tip_instance.game_league + ', ' + tip_instance.game_sport + ' MISMATCH!' + "\n"
                        # tip has passed this object (i.e. no tip upcoming for this event therefore tip stake = 0)
                        elif row_minutes_past_start > 15:
                            if (
                                tip_instance.wettpoint_tip_stake is not None 
                                and tip_instance.wettpoint_tip_stake >= 1.0
                                ):
                                tip_instance = self.create_tip_change_object(tip_instance, 'team', 'stake_team_all', not tip_change_created)
                                tip_change_created = True
                                tip_instance = self.create_tip_change_object(tip_instance, 'total', 'stake_total_all', not tip_change_created)
                                tip_instance = self.create_tip_change_object(tip_instance, 'stake', 'stake_all', not tip_change_created)
                            
                            if tip_instance.wettpoint_tip_stake is None:
                                if tip_instance.wettpoint_tip_team is None and tip_instance.wettpoint_tip_total is None:
                                    tip_stake_changed = True
                                    tip_instance.wettpoint_tip_stake = 0.0
                            elif tip_instance.wettpoint_tip_stake >= 1.0:
                                tip_stake_changed = True
                                tip_instance.wettpoint_tip_stake = 0.0
                                
                            break
                    
                    if (
                        sport_key not in constants.SPORTS_H2H_EXCLUDE 
                        and (
                             # 1. finalized -> within 12 hours, no running games, no games with either team in an earlier date
                             # 2. just got changed (into 0.0)
                             # 3. is about to start (and is either not filled out (None) or has no table info (0.0))
                             matchup_finalized 
                             or tip_stake_changed is True 
                             or minutes_until_start <= (45 + 5) 
                             ) 
                        and (
                             tip_instance.wettpoint_tip_stake is None 
                             or tip_instance.wettpoint_tip_stake == 0.0 
                             )
                        and (
                             # 1. about to start so fill with H2H stake rounded (if team provided)
                             # 2. first time doing a H2H scrape
                             minutes_until_start <= (45 + 5) 
                             or (
                                tip_instance.wettpoint_tip_team is None 
                                and tip_instance.wettpoint_tip_total is None
                                )
                             )
                        ):
                        nolimit = False
                        if minutes_until_start <= (45 + 5):
                            nolimit = True
                        h2h_total, h2h_team, h2h_stake = self.get_wettpoint_h2h(tip_instance.game_sport, tip_instance.game_league, tip_instance.game_team_home, tip_instance.game_team_away, nolimit=nolimit)
                    
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
                       
                        if h2h_stake is not False and tip_instance.wettpoint_tip_stake == 0.0:
                            if h2h_team is not False:
                                tip_stake_changed = False
                                if minutes_until_start <= (45 + 5):
                                    tip_instance.wettpoint_tip_stake = round(10.0 - h2h_stake)
                                else:
                                    tip_instance.wettpoint_tip_stake = None
                            else:
                                h2h_stake = (10.0 - h2h_stake) / 10.0
                                tip_instance.wettpoint_tip_stake = 0.0 + h2h_stake
                                tip_stake_changed = True
                        elif minutes_until_start <= (45 + 5):
                            tip_stake_changed = False
#                               and abs(last_minutes_past_start) <= 15
                            if h2h_stake is not False:
                                if h2h_team is not False:
                                    tip_instance.wettpoint_tip_stake = round(10.0 - h2h_stake)
                                else:
                                    tip_instance.wettpoint_tip_stake = 0.0 + h2h_stake
                            else:
                                tip_instance.wettpoint_tip_stake = 0.0
                            
                    # change object created, put in datastore
                    if self.temp_holder != False:
                        self.temp_holder.put()
                    
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
                    
                    not_elapsed_tips_by_sport_league[sport_key][league_key][unicode(tip_instance.key.urlsafe())] = tip_instance
        
        memcache.set('lastWettpointTablesInfo', self.wettpoint_tables_memcache)
        return not_elapsed_tips_by_sport_league
    
    def matchup_data_finalized(self, team_list, matchup_date, possible_earlier_games):
        for check_tip_instance in possible_earlier_games:
            if (
                check_tip_instance.date < matchup_date 
                and (
                     check_tip_instance.game_team_away in team_list 
                     or check_tip_instance.game_team_home in team_list
                     )
                ):
                return False
            
        return True
    
    def get_wettpoint_h2h(self, sport_key, league_key, team_home, team_away, **kwargs):
        if 'nolimit' not in kwargs or kwargs['nolimit'] is not True:
            logging.debug('Upcoming connection counts towards limit of '+str(self.REQUEST_COUNT[constants.WETTPOINT_FEED] - len(constants.SPORTS)))
            if (self.REQUEST_COUNT[constants.WETTPOINT_FEED] - len(constants.SPORTS)) > 5:
                logging.debug('wettpoint limit H2H reached')
                if sport_key in self.wettpoint_tables_memcache:
                    self.wettpoint_tables_memcache[sport_key]['h2h_limit_reached'] = True
                return False, False, False
        else:
            logging.debug('A nolimit request')
        
        team_home_aliases, team_home_id = get_team_aliases(sport_key, league_key, team_home)
        team_away_aliases, team_away_id = get_team_aliases(sport_key, league_key, team_away)
        
        if team_home_id is None or team_away_id is None:
            return False, False, False
        
        sport = constants.SPORTS[sport_key]['wettpoint']
        
        h2h_total, h2h_team, h2h_stake = False, False, False
        
        # wettpoint h2h link is home team - away team
        h2h_link = 'http://'+sport+'.'+constants.WETTPOINT_FEED+'/h2h/'+team_home_id+'-'+team_away_id+'.html'
        
        if 'nolimit' not in kwargs or kwargs['nolimit'] is not True:
            self.REQUEST_COUNT[constants.WETTPOINT_FEED] += 1
        if self.REQUEST_COUNT[constants.WETTPOINT_FEED] > 1:
            time.sleep(random.uniform(16.87,30.9))
        
#         h2h_html = requests.get(h2h_link, headers=constants.HEADER)
        logging.debug('Connecting to '+h2h_link)
        h2h_html = urlfetch.fetch(h2h_link, headers={ "Accept-Encoding" : "identity" })
        h2h_soup = BeautifulSoup(h2h_html.content).find('div', {'class' : 'inhalt2'})
        
        # ensure teams are correct and we got the right link
        team_links = h2h_soup.find('table').find_all('tr')[-1].find_all('a')
        if (
            team_links[0].get_text().strip().upper() in (name.upper() for name in team_home_aliases) 
            and team_links[1].get_text().strip().upper() in (name.upper() for name in team_away_aliases)
            ):
            h2h_header = h2h_soup.find_all('h3', recursive=False)[1]
            
            h2h_total_text = h2h_header.find_next_sibling(text=re.compile('Over / Under'))
            if h2h_total_text:
                h2h_total_text = h2h_total_text.find_next_sibling('b').get_text().strip()
                if 'UNDER' in h2h_total_text:
                    h2h_total = 'Under'
                elif 'OVER' in h2h_total_text: 
                    h2h_total = 'Over'
                    
            h2h_team_text = h2h_header.find_next_sibling(text=re.compile('1X2 System'))
            if h2h_team_text:
                h2h_team = h2h_team_text.find_next_sibling('b').get_text().strip()
                
            h2h_stake_text = h2h_header.find_next_sibling(text=re.compile('Risikofaktor'))
            if h2h_stake_text:
                h2h_stake_text = h2h_stake_text.find_next_sibling('b').get_text().strip()
                try:
                    h2h_stake = float(h2h_stake_text)
                except ValueError:
                    h2h_stake = False
        else:
            if self.WARNING_MAIL is False:
                self.WARNING_MAIL = ''
            else:
                self.WARNING_MAIL += "\n"
            self.WARNING_MAIL += 'Probable '+team_away+'('+team_away_id+') @ '+team_home+'('+team_home_id+') wettpoint H2H ids for ' + league_key + ' MISMATCH!' + "\n"
        
        return h2h_total, h2h_team, h2h_stake
    
    def add_wettpoint_h2h_details(self, tip_instance):
        h2h_total, h2h_team, h2h_stake = self.get_wettpoint_h2h(tip_instance.game_sport, tip_instance.game_league, tip_instance.game_team_home, tip_instance.game_team_away)
        
        if h2h_stake is not False:
            h2h_stake = (10.0 - h2h_stake) / 10.0
        
        mail_warning = ''
        if h2h_total is not False and h2h_total != tip_instance.wettpoint_tip_total:
            mail_warning += tip_instance.game_team_away + ' @ ' + tip_instance.game_team_home + ' TOTAL DISCREPANCY' + "\n"
        if h2h_team is not False and h2h_team != tip_instance.wettpoint_tip_team:
            mail_warning += tip_instance.game_team_away + ' @ ' + tip_instance.game_team_home + ' TEAM DISCREPANCY' + "\n"
        if h2h_stake is not False and round(h2h_stake) != tip_instance.wettpoint_tip_stake:
            mail_warning += tip_instance.game_team_away + ' @ ' + tip_instance.game_team_home + ' STAKE DISCREPANCY' + "\n"
        if len(mail_warning) > 0:
            if self.WARNING_MAIL is False:
                self.WARNING_MAIL = ''+tip_instance.game_league+"\n"+mail_warning
            else:
                self.WARNING_MAIL += "\n"+tip_instance.game_league+"\n"+mail_warning
        
        if h2h_stake is not False:
            return tip_instance.wettpoint_tip_stake + h2h_stake
        
        return tip_instance.wettpoint_tip_stake
                                    
    def create_tip_change_object(self, tip_instance, ctype, line, create_mail):
        if create_mail is True:
            if self.MAIL_BODY is False:
                self.MAIL_BODY = ''
            else:
                self.MAIL_BODY = self.MAIL_BODY + "\n\n"
            
            self.MAIL_BODY = self.MAIL_BODY + (tip_instance.date - timedelta(hours = 6)).strftime('%B-%d %I:%M%p') + " " + tip_instance.game_team_away + " @ " + tip_instance.game_team_home + "\n"
            self.MAIL_BODY = self.MAIL_BODY + str(tip_instance.wettpoint_tip_stake) + " " + str(tip_instance.wettpoint_tip_team) + " " + str(tip_instance.wettpoint_tip_total) 
            self.MAIL_BODY = self.MAIL_BODY + "\n" + ctype + " (" + line + ")"
        else:
            self.MAIL_BODY = self.MAIL_BODY + "\n" + ctype + " (" + line + ")"
        
        key_string = unicode(tip_instance.key.urlsafe())
        
        query = TipChange.gql('WHERE tip_key = :1', key_string)
        
        if query.count() == 0 and self.temp_holder is False:
            tip_change_object = TipChange()
            tip_change_object.changes = 1
            tip_change_object.type = ctype
        else:
            if query.count() == 0:
                tip_change_object = self.temp_holder
            else:
                tip_change_object = query.get()
            tip_change_object.changes += 1
            tip_change_object.type = tip_change_object.type + ctype
            
        tip_change_object.date = datetime.now()
        tip_change_object.tip_key = key_string
            
        tip_change_object.wettpoint_tip_stake = tip_instance.wettpoint_tip_stake
        
        if ctype == 'team':
            if tip_instance.wettpoint_tip_team:
                tip_change_object.wettpoint_tip_team = tip_instance.wettpoint_tip_team
                tip_instance.wettpoint_tip_team = None
            if tip_instance.team_lines:
                tip_change_object.team_lines = tip_instance.team_lines
                tip_instance.team_lines = None
            if tip_instance.spread_no:
                tip_change_object.spread_no = tip_instance.spread_no
                tip_instance.spread_no = None
            if tip_instance.spread_lines:
                tip_change_object.spread_lines = tip_instance.spread_lines
                tip_instance.spread_lines = None
        elif ctype == 'total':
            if tip_instance.wettpoint_tip_total:
                tip_change_object.wettpoint_tip_total = tip_instance.wettpoint_tip_total
                tip_instance.wettpoint_tip_total = None
            if tip_instance.total_no:
                tip_change_object.total_no = tip_instance.total_no
                tip_instance.total_no = None
            if tip_instance.total_lines:
                tip_change_object.total_lines = tip_instance.total_lines
                tip_instance.total_lines = None
        
        self.temp_holder = tip_change_object
        return tip_instance
    
    def fill_lines(self, not_elapsed_tips_by_sport_league):
        possible_ppd_tips_by_sport_league = {}
        
        # go through all our sports
        for sport_key in constants.SPORTS:
            if sport_key not in not_elapsed_tips_by_sport_league:
                continue
            for league_key in constants.LEAGUES[sport_key]:
                if league_key not in not_elapsed_tips_by_sport_league[sport_key]:
                    continue
                for tip_instance in not_elapsed_tips_by_sport_league[sport_key][league_key].values():
                    key_string = unicode(tip_instance.key.urlsafe())
                    if (tip_instance.date - datetime.now()).total_seconds() < 0:
                        # tip has started, move onto next
                        tip_instance.elapsed = True
                        # update this tip
                        not_elapsed_tips_by_sport_league[sport_key][league_key][key_string] = tip_instance
                        continue
                    
                    if (
                        tip_instance.wettpoint_tip_stake is None 
                        and tip_instance.wettpoint_tip_team is None 
                        and tip_instance.wettpoint_tip_total is None
                        ):
                        # tip stake hasn't been determined yet, move on
                        continue
                    
                    # pinnacle call failed, go to next sport/league
                    if sport_key not in self.FEED:
                        break
                    elif tip_instance.game_league not in self.FEED[sport_key]:
                        continue
                    
                    if tip_instance.pinnacle_game_no in self.FEED[sport_key][tip_instance.game_league]:
                        # successful pinnacle call + game line exists
                        event_tag = self.FEED[sport_key][tip_instance.game_league][tip_instance.pinnacle_game_no]
                        
                        for period in event_tag.xpath('./periods/period'):
                            # currently only interested in full game lines
                            if (
                                (
                                 period.find('period_number').text.isdigit() 
                                 and int(period.find('period_number').text) == 0
                                 ) 
                                or unicode(period.find('period_description').text) in ['Game','Match']
                                ):
                                # get the total lines
                                period_total = period.find('total')
                                if period_total is not None:
                                    # get actual total number
                                    if tip_instance.total_no:
                                        hash1 = json.loads(tip_instance.total_no)
                                    else:
                                        hash1 = {}
                                        
                                    hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = unicode(period_total.find('total_points').text)
                                    tip_instance.total_no = json.dumps(hash1)
                                    
                                    # get the total odds line
                                    if tip_instance.total_lines:
                                        hash1 = json.loads(tip_instance.total_lines)
                                    else:
                                        hash1 = {}
                                    
                                    if tip_instance.wettpoint_tip_total == 'Over':
                                        hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = unicode(period_total.find('over_adjust').text)
                                    else:
                                        hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = unicode(period_total.find('under_adjust').text)
                                        
                                    tip_instance.total_lines = json.dumps(hash1)
                                # get the moneyline
                                period_moneyline = period.find('moneyline')
                                if period_moneyline is not None:
                                    if tip_instance.team_lines:
                                        hash1 = json.loads(tip_instance.team_lines)
                                    else:
                                        hash1 = {}
                                    
                                    period_moneyline_home = period_moneyline.find('moneyline_home')
                                    period_moneyline_visiting = period_moneyline.find('moneyline_visiting')
                                    period_moneyline_draw = period_moneyline.find('moneyline_draw')
                                    
                                    if period_moneyline_home is not None:
                                        period_moneyline_home = unicode(period_moneyline_home.text)
                                    if period_moneyline_visiting is not None:
                                        period_moneyline_visiting = unicode(period_moneyline_visiting.text)
                                    if period_moneyline_draw is not None:
                                        period_moneyline_draw = unicode(period_moneyline_draw.text)
                                    
                                    # get tip team line
                                    if tip_instance.wettpoint_tip_team is not None:
                                        moneyline = ''
                                        for i in tip_instance.wettpoint_tip_team:
                                            if i == '1':
                                                moneyline += period_moneyline_home + '|'
                                            elif i == 'X':
                                                moneyline += period_moneyline_draw + '|'
                                            elif i == '2':
                                                moneyline += period_moneyline_visiting + '|'
                                        
                                        if (
                                            period_moneyline_draw 
                                            and len(tip_instance.wettpoint_tip_team) < 2
                                            ):
                                            moneyline += period_moneyline_draw
                                            
                                        moneyline = moneyline.rstrip('|')
                                        hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = moneyline
                                    else:
                                        # if no tip team, get favourite line
                                        moneyline = ''
                                        if float(period_moneyline_visiting) < float(period_moneyline_home):
                                            tip_instance.wettpoint_tip_team = '2'
                                            moneyline = period_moneyline_visiting
                                        else:
                                            tip_instance.wettpoint_tip_team = '1'
                                            moneyline = period_moneyline_home
                                            
                                        if period_moneyline_draw:
                                            moneyline += '|'+period_moneyline_draw
                                            
                                        hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = moneyline
                                            
                                    tip_instance.team_lines = json.dumps(hash1)
                                    
                                period_spread = period.find('spread')
                                if period_spread is not None:
                                    if tip_instance.spread_no:
                                        hash1 = json.loads(tip_instance.spread_no)
                                    else:
                                        hash1 = {}
                                        
                                    if tip_instance.spread_lines:
                                        hash2 = json.loads(tip_instance.spread_lines)
                                    else:
                                        hash2 = {}
                                        
                                    period_spread_home = unicode(period_spread.find('spread_home').text)
                                    period_spread_visiting = unicode(period_spread.find('spread_visiting').text)
                                        
                                    if tip_instance.wettpoint_tip_team is not None:
                                        if tip_instance.wettpoint_tip_team.find('1') != -1 or tip_instance.wettpoint_tip_team == 'X':
                                            hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = period_spread_home
                                            hash2[datetime.now().strftime('%d.%m.%Y %H:%M')] = unicode(period_spread.find('spread_adjust_home').text)
                                        elif tip_instance.wettpoint_tip_team.find('2') != -1:
                                            hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = period_spread_visiting
                                            hash2[datetime.now().strftime('%d.%m.%Y %H:%M')] = unicode(period_spread.find('spread_adjust_visiting').text)
                                    else:
                                        if float(period_spread_visiting) < float(period_spread_home):
                                            tip_instance.wettpoint_tip_team = '2'
                                            hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = period_spread_visiting
                                            hash2[datetime.now().strftime('%d.%m.%Y %H:%M')] = unicode(period_spread.find('spread_adjust_visiting').text)
                                        else:
                                            tip_instance.wettpoint_tip_team = '1'
                                            hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = period_spread_home
                                            hash2[datetime.now().strftime('%d.%m.%Y %H:%M')] = unicode(period_spread.find('spread_adjust_home').text)
                                        
                                    tip_instance.spread_no = json.dumps(hash1)
                                    tip_instance.spread_lines = json.dumps(hash2)
                                
                                not_elapsed_tips_by_sport_league[sport_key][league_key][key_string] = tip_instance
                                break
                    else:
                        #TODO: check for a duplicate game in feed... if one is found, either email admin or delete automatically
                        # either game was taken off the board (for any number of reasons) - could be temporary
                        # or game is a duplicate (something changed that i didn't account for)
                        logging.warning('Missing Game: Cannot find '+tip_instance.game_team_home.strip()+' or '+tip_instance.game_team_away.strip()+' for '+key_string)
                        
                        if tip_instance.game_sport not in possible_ppd_tips_by_sport_league:
                            possible_ppd_tips_by_sport_league[tip_instance.game_sport] = {}
                        if tip_instance.game_league not in possible_ppd_tips_by_sport_league[tip_instance.game_sport]:
                            possible_ppd_tips_by_sport_league[tip_instance.game_sport][tip_instance.game_league] = {}
                        possible_ppd_tips_by_sport_league[tip_instance.game_sport][tip_instance.game_league][key_string] = tip_instance
                    
        return not_elapsed_tips_by_sport_league, possible_ppd_tips_by_sport_league
        
    def find_games(self):
        """Find a list of games (and their details) corresponding to our interests
        """
        new_or_updated_tips = {}
        
        # grab entire pinnacle feed
        sport_feed = 'http://xml.'+constants.PINNACLE_FEED+'/pinnacleFeed.aspx'#?sporttype=' + keys['pinnacle']
        
        self.REQUEST_COUNT[constants.PINNACLE_FEED] += 1
        if self.REQUEST_COUNT[constants.PINNACLE_FEED] > 1:
            time.sleep(73.6)
            
#         xml = requests.get(sport_feed, headers=constants.HEADER)
        # use etree for xpath search to easily filter specific leagues
        etree_parser = etree.XMLParser(ns_clean=True,recover=True)
        logging.debug('Connecting to '+sport_feed)
        pinnacle_xml = urlfetch.fetch(sport_feed)
        lxml_tree = etree.fromstring(pinnacle_xml.content, etree_parser)
        
        # get sports we're interested in listed in constant SPORTS
        for sport_key, sport_values in constants.SPORTS.iteritems():
            self.FEED[sport_key] = {}
            for league_key, league_values in constants.LEAGUES[sport_key].iteritems():
                # keep all tag information so don't have to scrape again if we need more information later
                self.FEED[sport_key][league_key] = {}
                
                pinnacle_league_key = league_values['pinnacle']
                league_xpath = None
                # single league can have multiple league names (ex. conferences)
                if isinstance(pinnacle_league_key, list):
                    for pinnacle_league_value in pinnacle_league_key.values():
                        if league_xpath is None:
                            league_xpath = "league='"+pinnacle_league_value+"'"
                        else:
                            league_xpath += " OR league='"+pinnacle_league_value+"'"
                else:
                    league_xpath = "league='"+pinnacle_league_key+"'"
                    
                # get all the game (event) tags for this league (not live games)
                all_games = lxml_tree.xpath("//event[sporttype='"+sport_values['pinnacle']+"' and ("+league_xpath+") and IsLive='No']")
                
                for event_tag in all_games:
                    # convert game datetime string to standard GMT datettime object
                    date_GMT = datetime.strptime(event_tag.find('event_datetimeGMT').text, '%Y-%m-%d %H:%M')
                    event_game_number = unicode(event_tag.find('gamenumber').text)
                    
                    # get teams
                    participants = event_tag.xpath('./participants/participant')
                    
                    # game already elapsed, move on to next
                    if (date_GMT - datetime.now()).total_seconds() < 0:
                        continue
                    
                    # store team information in tip object - first initialization of tip object
                    tip_instance = False
                    
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
                            
                    for period in event_tag.xpath('./periods/period'):
                        # currently only interested in full game lines
                        if (
                            (
                             period.find('period_number').text.isdigit() 
                             and int(period.find('period_number').text) == 0
                             ) 
                            or unicode(period.find('period_description').text) in ['Game','Match']
                            ):
                            # pinnacle game numbers should be unique for each league
                            if event_game_number in self.FEED[sport_key][league_key]:
                                logging.error('Multiple matching game numbers in same league listed at the same time! ' + event_game_number)
                                raise Exception('Multiple matching game numbers in same league listed at the same time! ' + event_game_number)
                            else:
#                                         sys.stderr.write("Add game: "+event_tag.find('gamenumber').string+" for "+participant_name))
#                                         sys.stderr.write("\n")
                                self.FEED[sport_key][league_key][event_game_number] = event_tag
                            break
                        
                    # not a full game tag, skip
                    if event_game_number not in self.FEED[sport_key][league_key]:
                        continue
                    
                    # skip test cases
                    if re.match('^TEST\d', participant_name_visiting):
                        continue
                    # also skip grand salami cases
                    elif participant_name_visiting.split(' ')[0].lower() == 'away' and participant_name_home.split(' ')[0].lower() == 'home':
                        continue
                    # also skip pinnacle being stupid
                    elif participant_name_visiting == '2nd Half Wagering' or participant_name_home == '2nd Half Wagering':
                        continue
                    
                    if (
                        sport_key in teamconstants.TEAMS 
                        and league_key in teamconstants.TEAMS[sport_key]
                        ):
                        league_team_info = teamconstants.TEAMS[sport_key][league_key]
                        if isinstance(league_team_info, basestring):
                            # reference to another league information
                            league_team_info = teamconstants.TEAMS[sport_key][league_team_info]
                    # if team information hasn't been filled out for this league, can still store it but raise a warning
                    else:
                        logging.warning(league_key+', '+sport_key+' has no team information!')
                        league_team_info = None
                    
                    participant_name_multi_visiting = participant_name_multi_home = False
                    for participant_name in [participant_name_visiting, participant_name_home]:
                        # pinnacle prefixes G# on team names if team has multiple games in a single day
                        # search and replace a existing tip object if an additional game gets added
                        participant_name_multi = re.search('^(G\d+\s+)(.+)', participant_name)
                        participant_game_string = None
                        if participant_name_multi:
                            participant_game_string = participant_name_multi.group(1)
                            participant_name_multi = participant_name_multi.group(2).strip()
                            
                            if participant_name == participant_name_visiting:
                                participant_name_multi_visiting = participant_name_multi
                            elif participant_name == participant_name_home:
                                participant_name_multi_home = participant_name_multi
                        
                        if league_team_info:
                            # ensure team string exists in team constant, otherwise email admin
                            if (
                                participant_name not in league_team_info['keys'].keys() 
                                and not (
                                     participant_name_multi 
                                     and participant_name_multi in league_team_info['keys'].keys()
                                     )
                                ):
                                
                                team_name_exists = False
                                for value_team_id, possible_team_aliases in league_team_info['values'].iteritems():
                                    if participant_name_multi and participant_name_multi in possible_team_aliases:
                                        for datastore_name, key_team_id in league_team_info['keys'].iteritems():
                                            if value_team_id == key_team_id:
                                                team_name_exists = True
                                                
                                                if participant_name == participant_name_visiting:
                                                    logging.warning('(3) Changing pinnacle name ('+participant_name_visiting+') to datastore ('+participant_game_string + datastore_name+')')
                                                    participant_name_multi_visiting = datastore_name
                                                    participant_name_visiting = participant_game_string + datastore_name
                                                elif participant_name == participant_name_home:
                                                    logging.warning('(4) Changing pinnacle name ('+participant_name_home+') to datastore ('+participant_game_string + datastore_name+')')
                                                    participant_name_multi_home = datastore_name
                                                    participant_name_home = participant_game_string + datastore_name
                                                break
                                        break
                                    elif participant_name in possible_team_aliases:
                                        for datastore_name, key_team_id in league_team_info['keys'].iteritems():
                                            if value_team_id == key_team_id:
                                                team_name_exists = True
                                                
                                                if participant_name == participant_name_visiting:
                                                    logging.warning('(1) Changing pinnacle name ('+participant_name_visiting+') to datastore ('+datastore_name+')')
                                                    participant_name_visiting = datastore_name
                                                elif participant_name == participant_name_home:
                                                    logging.warning('(2) Changing pinnacle name ('+participant_name_home+') to datastore ('+datastore_name+')')
                                                    participant_name_home = datastore_name
                                                break
                                        break
                                
                                if team_name_exists is False:
                                    if self.WARNING_MAIL is False:
                                        self.WARNING_MAIL = ''
                                    else:
                                        self.WARNING_MAIL += "\n"
                                    logging.warning(participant_name + ' for ' + league_key + ', ' + sport_key + ' does not exist!')
                                    self.WARNING_MAIL += participant_name + ' for ' + league_key + ', ' + sport_key + ' does not exist!' + "\n"
                            
                    # do a search of the datastore to see if current tip object already created based on game number, sport, league, and team name
                    query = Tip.gql('WHERE elapsed != True AND pinnacle_game_no = :1 AND game_sport = :2 AND game_league = :3 AND game_team_away = :4 AND game_team_home = :5', 
                                    event_game_number, 
                                    sport_key,
                                    league_key,
                                    participant_name_visiting,
                                    participant_name_home,
                                )
                    
                    # safety measure to prevent count() function from doing multiple queries
                    query_count = query.count()
                    
                    # if tip object does not yet exist, create it
                    if query_count == 0:
                        # do a search for doubleheaders - game number would have changed so search for same time
                        if participant_name_multi_visiting is not False and participant_name_multi_home is not False:
                            query = Tip.gql('WHERE elapsed != True AND date = :1 AND game_sport = :2 AND game_league = :3 AND game_team_away = :4 AND game_team_home = :5', 
                                            date_GMT,
                                            sport_key,
                                            league_key,
                                            participant_name_multi_visiting,
                                            participant_name_multi_home,
                                        )
                            
                            # safety measure to prevent count() function from doing multiple queries
                            query_count = query.count()
                        
                        if query_count == 0:
                            # no tip object exists yet, create new one
                            tip_instance = Tip()
                            tip_instance.game_team_away = participant_name_visiting
                            tip_instance.game_team_home = participant_name_home
                            tip_instance.rot_away = participant_rot_num_visiting
                            tip_instance.rot_home = participant_rot_num_home
                        else:
                            # should be only one result if it exists
                            if query_count > 1:
                                raise Exception('Multiple matching datastore Tip objects to fill_games query!')
                            
                            # tip object exists, grab it
                            tip_instance = query.get()
                            
                            # if any information is different (ex. time change) update it
                            if (
                                tip_instance.pinnacle_game_no != event_game_number 
                                or tip_instance.game_team_away != participant_name_visiting 
                                or tip_instance.game_team_home != participant_name_home 
                                or tip_instance.rot_away != participant_rot_num_visiting
                                or tip_instance.rot_home != participant_rot_num_home
                                ):
                                tip_instance.game_team_away = participant_name_visiting
                                tip_instance.game_team_home = participant_name_home
                                tip_instance.rot_away = participant_rot_num_visiting
                                tip_instance.rot_home = participant_rot_num_home
                            # otherwise no need to update it because all data has already been stored so move onto next game tag
                            else:
                                tip_instance = False
                                continue
                    else:
                        # should be only one result if it exists
                        if query_count > 1:
                            raise Exception('Multiple matching datastore Tip objects to fill_games query!')
                        
                        # tip object exists, grab it
                        tip_instance = query.get()
                        
                        # if any information is different (ex. time change) update it
                        if (
                            tip_instance.date != date_GMT 
                            or tip_instance.rot_away != participant_rot_num_visiting
                            or tip_instance.rot_home != participant_rot_num_home
                            ):
                            tip_instance.rot_away = participant_rot_num_visiting
                            tip_instance.rot_home = participant_rot_num_home
                        # otherwise no need to update it because all data has already been stored so move onto next game tag
                        else:
                            tip_instance = False
                            continue
                        
                    # if tip object is new or needs to be updated, do so now    
                    if tip_instance != False:
                        # add basic information to tip object
                        tip_instance.date = date_GMT
                        tip_instance.game_sport = sport_key
                        tip_instance.game_league = league_key
                        tip_instance.pinnacle_game_no = event_game_number
                        
                        # store in datastore immediately to ensure no conflicts in this session
                        tip_instance_key = tip_instance.put()
                        # store in constant for future use and additional commit
                        new_or_updated_tips[unicode(tip_instance.key.urlsafe())] = tip_instance_key
        
        return new_or_updated_tips