#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.insert(0, 'libs')

from google.appengine.ext import webapp, ndb
from google.appengine.api import mail, urlfetch

from models import Tip, TipChange

# from _symtable import LOCAL

from httplib import HTTPException
from datetime import datetime, timedelta
from timeit import itertools
from bs4 import BeautifulSoup
from lxml import etree

import re
import json
import time
import logging
import requests
import constants
import teamconstants

class Scraper(webapp.RequestHandler):
    def get(self):
        self.FEED = {}
        self.REQUEST_COUNT = {constants.PINNACLE_FEED : 0, constants.WETTPOINT_FEED: 0, constants.SCOREBOARD_FEED : 0}
        #sys.stderr.write("ARRRRGHH")
        #sys.stderr.write("\n")
        
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
            
            if int(self.REQUEST_COUNT[x]) > 10:
                mail.send_mail('BlackCanine@gmail.com', 'BlackCanine@gmail.com', 'Scrape Abuse WARNING', x + ' being hit: ' + str(self.REQUEST_COUNT[x]))
            
            self.response.out.write('<br />')
        logging.info(logging_info)
    
    def commit_tips(self, update_tips):
        ndb.put_multi(update_tips.values())
        
    def fill_games(self, new_or_updated_tips):
        """Now with all the games stored as incomplete Tip objects, fill out the lines and stuff
        """
        # get all non-elapsed datastore entities so we can store current lines and wettpoint data
        not_elapsed_tips_by_sport = {}
        for sport_key in constants.SPORTS:
            query = Tip.gql('WHERE elapsed != True AND game_sport = :1', sport_key)
            for tip_instance in query:
                if sport_key not in not_elapsed_tips_by_sport:
                    not_elapsed_tips_by_sport[sport_key] = {}
                # use cached entity if new or updated by pinnacle scrape
                if tip_instance.key in new_or_updated_tips:
                    not_elapsed_tips_by_sport[sport_key][tip_instance.key] = new_or_updated_tips[tip_instance.key].get()
                else:
                    not_elapsed_tips_by_sport[sport_key][tip_instance.key] = tip_instance
        
        not_elapsed_tips_by_sport = self.fill_wettpoint_tips(not_elapsed_tips_by_sport)
        not_elapsed_tips_by_sport, possible_ppd_tips_by_sport_league = self.fill_lines(not_elapsed_tips_by_sport)
        
        archived_tips = {}
        try:
            not_archived_tips_by_sport_league = {}
            for sport_key, sport_leagues in constants.LEAGUES.iteritems():
                for league_key in sport_leagues:
                    query = Tip.gql('WHERE elapsed = True AND archived != True AND game_league = :1', league_key)
                    for tip_instance in query:
                        if sport_key not in not_archived_tips_by_sport_league:
                            not_archived_tips_by_sport_league[sport_key] = {}
                        if league_key not in not_archived_tips_by_sport_league[sport_key]:
                            not_archived_tips_by_sport_league[sport_key][league_key] = {}
                        not_archived_tips_by_sport_league[sport_key][league_key][tip_instance.key] = tip_instance
            
            archived_tips = self.fill_scores(not_archived_tips_by_sport_league, possible_ppd_tips_by_sport_league)
        except HTTPException:
            logging.warning('Scoreboard feed down')
            
        update_tips = {}
        for not_elapsed_tips in not_elapsed_tips_by_sport.values():
            for tip_instance_key, tip_instance in not_elapsed_tips.iteritems():
                if tip_instance_key in update_tips:
                    raise Exception(str(tip_instance_key)+' appears more than once in not_elapsed_tips?!')
                update_tips[tip_instance_key] = tip_instance
        for tip_instance_key, tip_instance in archived_tips.iteritems():
            if tip_instance_key in update_tips:
                raise Exception(str(tip_instance_key)+' duplicate located in archived_tips?!')
            update_tips[tip_instance_key] = tip_instance
        return update_tips
        
    def fill_scores(self, not_archived_tips_by_sport_league, possible_ppd_tips_by_sport_league):
        archived_tips = {}
        for sport_key, sport_leagues in constants.LEAGUES.iteritems():
            scores_by_date = {}
            for league_key, values in sport_leagues.iteritems():
                if 'scoreboard' not in values:
                    continue
                
                if sport_key not in teamconstants.TEAMS or league_key not in teamconstants.TEAMS[sport_key]:
                    # team info missing for this league, move on to next
                    logging.warning('due to no team info, no scoreboard scraping for '+str(league_key))
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
                
                league_team_info = teamconstants.TEAMS[sport_key][league_key]
                if isinstance(league_team_info, basestring):
                    # reference to another league information
                    league_team_info = teamconstants.TEAMS[sport_key][league_team_info]
                
                league = values['scoreboard']
                # go through all non-archived tips that have already begun
                for tip_instance in all_tip_check_scores:
                    scoreboard_game_time = tip_instance.date + timedelta(hours = 3)
                    
                    # have we gotten the scoreboard for this day before
                    # only get it if we don't already have it
                    scoreboard_date_string = scoreboard_game_time.strftime('%d-%m')
                    if not scoreboard_date_string in scores_by_date:
                        scores_by_date[scoreboard_date_string] = []
                        
                        logging.debug('scraping scoreboard for '+scoreboard_game_time.strftime('%d-%m %H:%M')+' | '+tip_instance.game_team_away+' @ '+tip_instance.game_team_home)
                        feed_url = constants.SCOREBOARD_FEED + '/' + constants.SPORTS[sport_key]['scoreboard'] + '/finished_games/' + scoreboard_date_string
                        
                        self.REQUEST_COUNT[constants.SCOREBOARD_FEED] += 1
                        if self.REQUEST_COUNT[constants.SCOREBOARD_FEED] > 1:
                            time.sleep(15.2)
                        
                        feed_html = requests.get(feed_url, headers=constants.HEADER)
                        soup = BeautifulSoup(feed_html.text)
                        
                        scores_rows = False
                        # get the results table
                        scores_rows = soup.find('tbody', {'id' : 'scoretable'}).find('tr', {'id' : 'finHeader'}).find_next_siblings('tr')
                        
                        for score_row in scores_rows:
                            scores_by_date[scoreboard_date_string].append(score_row)
                            
                    # remove the game digit before committing (only if scores get successfully scraped)    
                    game_digit = re.search('^G(\d)\s+', tip_instance.game_team_away)
                    if game_digit:
                        game_digit = game_digit.group(1)
                    else:
                        game_digit = False
                    
                    if game_digit != False:
                        tip_instance.game_team_away = re.sub('^G\d\s+', '', tip_instance.game_team_away)
                        tip_instance.game_team_home = re.sub('^G\d\s+', '', tip_instance.game_team_home)
#                         if tip.wettpoint_tip_team:
#                             tip.wettpoint_tip_team = re.sub('^G\d\s+', '', tip.wettpoint_tip_team)
                        game_digit = int(game_digit)
                    
                    if (
                        tip_instance.game_team_home not in league_team_info['keys'] 
                        or tip_instance.game_team_away not in league_team_info['keys']
                        ):
                        # team info missing, move on to next
                        logging.warning('due to no team '+tip_instance.game_team_home+' or '+tip_instance.game_team_away+' info, no scoreboard scraping for '+str(league_key))
                        continue
                    
                    # get all team aliases
                    team_home_aliases = league_team_info['keys'][tip_instance.game_team_home]
                    team_away_aliases = league_team_info['keys'][tip_instance.game_team_away]
                    
                    if team_home_aliases in league_team_info['values']:
                        team_home_aliases = league_team_info['values'][team_home_aliases] + [tip_instance.game_team_home]
                    else:
                        team_home_aliases = [tip_instance.game_team_home]
                        
                    if team_away_aliases in league_team_info['values']:
                        team_away_aliases = league_team_info['values'][team_away_aliases] + [tip_instance.game_team_away]
                    else:
                        team_away_aliases = [tip_instance.game_team_away]
                        
                    # should now have the scoreboard for this date, if not something went wrong    
                    score_date_rows = False
                    if scoreboard_date_string in scores_by_date:
                        score_date_rows = scores_by_date[scoreboard_date_string]
                          
                    for score_row in score_date_rows:
                        row_columns = score_row.find_all('td', recursive=False)
                        
                        if len(row_columns) < 8:
                            continue
                        
                        # should be the correct league
                        row_league = row_columns[3].find('span', {'class' : 'league'})
                        if row_league is None:
                            continue
                        
                        if isinstance(league, list):
                            if row_league.get_text().strip() not in league:
                                continue
                        else:
                            if row_league.get_text().strip() != league:
                                continue
                        
                        row_game_time = datetime.strptime(scoreboard_game_time.strftime('%m-%d-%Y') + ' ' + row_columns[0].get_text().replace('(','').replace(')','').strip(), '%m-%d-%Y %H:%M')
                        row_home_team = row_columns[5].get_text().strip()
                        row_away_team = row_columns[7].get_text().strip()
                        
                        # row should have same time (30 minute error window) and team names
                        time_difference = row_game_time - scoreboard_game_time
                        if abs(divmod(time_difference.total_seconds(), 60)[0]) <= 15:
                            if row_away_team.strip().upper() in (name.upper() for name in team_away_aliases):
                                if row_home_team.strip().upper() in (name.upper() for name in team_home_aliases):
                                    row_game_status = row_columns[1].get_text().strip()
                                    
                                    if row_game_status == 'Fin':
                                        row_game_scores = score_row.find_all('span', {'class' : 'scorersB'})
                                        
                                        # should have both sides' scores
                                        if len(row_game_scores) != 2:
                                            break
                                        
                                        tip_instance.score_home = row_game_scores[0].get_text().strip()
                                        tip_instance.score_away = row_game_scores[1].get_text().strip()
                                    elif row_game_status != 'Abd' and row_game_status != 'Post' and row_game_status != 'Canc':
                                        break
                                    
                                    tip_instance.archived = True
                                    
                                    # commit
                                    archived_tips[tip_instance.key] = tip_instance
                                    break
                                else:
                                    if self.WARNING_MAIL is False:
                                        self.WARNING_MAIL = ''
                                    else:
                                        self.WARNING_MAIL += "\n"
                                    self.WARNING_MAIL += 'Probable ' + str(row_home_team) + ' SCOREBOARD NAMES for ' + str(league_key) + ', ' + str(sport_key) + ' MISMATCH!' + "\n"
                            elif row_home_team.strip().upper() in (name.upper() for name in team_home_aliases):
                                if self.WARNING_MAIL is False:
                                    self.WARNING_MAIL = ''
                                else:
                                    self.WARNING_MAIL += "\n"
                                self.WARNING_MAIL += 'Probable ' + str(row_away_team) + ' SCOREBOARD NAMES for ' + str(league_key) + ', ' + str(sport_key) + ' MISMATCH!' + "\n"
                            
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

    def fill_wettpoint_tips(self, not_elapsed_tips_by_sport):
        # go through all our sports
        for sport_key in constants.SPORTS:
            if sport_key not in not_elapsed_tips_by_sport:
                continue
            
            # get wettpoint tip table page for particular sport
            sport = constants.SPORTS[sport_key]['wettpoint']
            feed = 'http://www.forum.'+constants.WETTPOINT_FEED+'/fr_toptipsys.php?cat='+sport
            
            self.REQUEST_COUNT[constants.WETTPOINT_FEED] += 1
            if self.REQUEST_COUNT[constants.WETTPOINT_FEED] > 1:
                time.sleep(29.3)
            
            html = requests.get(feed, headers=constants.HEADER)
            soup = BeautifulSoup(html.text)
            
            # get the tip table for this sport
            tables = soup.find_all('table', {'class' : 'gen'})
            tip_table = tables[1]
            tip_rows = tip_table.find_all('tr')
            
# REMOVE
            # extra information available for most sports
#             team_info = False
#             if sport != 'baseball':
#                 # see if wettpoint has a actual page for the sport
#                 team_info_link = 'http://'+sport+'.'+constants.WETTPOINT_FEED+'/teams.html'
#                 try:
#                     self.REQUEST_COUNT[constants.WETTPOINT_FEED] += 1
#                     if self.REQUEST_COUNT[constants.WETTPOINT_FEED] > 1:
#                         time.sleep(231.1)
#                         
#                     html = requests.get(team_info_link, headers=constants.HEADER)
#                     if html.status_code == requests.codes.ok: 
#                         team_info = True
#                 except Exception as inst:
#                     logging.warning(sport + ' does not have more in-depth wettpoint page. Fix please.')
                
            # now let's fill out those tips!
            for tip_instance in not_elapsed_tips_by_sport[sport_key].values():
                h2h_total, h2h_team, h2h_stake = False, False, False
                
                if (tip_instance.date - datetime.now()).total_seconds() < 0:
                    # game has already begun, move on to next
                    tip_instance.elapsed = True
                    # set tip to be updated
                    not_elapsed_tips_by_sport[sport_key][tip_instance.key] = tip_instance
                    continue
                elif (
                      divmod((tip_instance.date - datetime.now()).total_seconds(), 60)[0] < 20 
                      and tip_instance.wettpoint_tip_stake is not None
                      ):
                    # tip has already been filled out and table updated past tip time, move on to next to avoid resetting tip to 0
                    continue
                elif not 'wettpoint' in constants.LEAGUES[unicode(tip_instance.game_sport)][unicode(tip_instance.game_league)]:
                    # constant missing league identifier?
                    logging.warning('no wettpoint scraping for '+str(unicode(tip_instance.game_league)))
                    continue
                
                if (
                    unicode(tip_instance.game_sport) not in teamconstants.TEAMS 
                    or unicode(tip_instance.game_league) not in teamconstants.TEAMS[unicode(tip_instance.game_sport)]
                    ):
                    # team info missing for this league, move on to next
                    logging.warning('due to no team info, no wettpoint scraping for '+str(unicode(tip_instance.game_league)))
                    continue
                
                league_team_info = teamconstants.TEAMS[unicode(tip_instance.game_sport)][unicode(tip_instance.game_league)]
                if isinstance(league_team_info, basestring):
                    # reference to another league information
                    league_team_info = teamconstants.TEAMS[unicode(tip_instance.game_sport)][league_team_info]
                
                # remove the game digit to get correct team name aliases
                game_digit = re.search('^G(\d)\s+', tip_instance.game_team_away)
                if game_digit:
                    tip_game_team_away = re.sub('^G\d\s+', '', tip_instance.game_team_away)
                    tip_game_team_home = re.sub('^G\d\s+', '', tip_instance.game_team_home)
                else:
                    tip_game_team_away = tip_instance.game_team_away
                    tip_game_team_home = tip_instance.game_team_home
                    
                if (
                    tip_game_team_home not in league_team_info['keys'] 
                    or tip_game_team_away not in league_team_info['keys']
                    ):
                    # team info missing, move on to next
                    logging.warning('due to no team '+tip_game_team_home+' or '+tip_game_team_away+' info, no wettpoint scraping for '+str(unicode(tip_instance.game_league)))
                    continue
                
                # get all team aliases
                team_home_id = league_team_info['keys'][tip_game_team_home]
                team_away_id = league_team_info['keys'][tip_game_team_away]
                
                if team_home_id in league_team_info['values']:
                    team_home_aliases = league_team_info['values'][team_home_id] + [tip_game_team_home]
                else:
                    team_home_aliases = [tip_game_team_home]
                    
                if team_away_id in league_team_info['values']:
                    team_away_aliases = league_team_info['values'][team_away_id] + [tip_game_team_away]
                else:
                    team_away_aliases = [tip_game_team_away]

# REMOVE ?                
#                 last_game_time = re.sub('[^0-9\.\s:]', '', tip_rows[-1].find_all('td')[6].get_text())
#                  
#                 # format the tip time to a standard
#                 if not re.match('\d{2}\.\d{2}\.\d{4}', last_game_time):
#                     wettpoint_current_time = datetime.utcnow() + timedelta(hours = 1)
#                     wettpoint_current_date = wettpoint_current_time.strftime('%d.%m.%Y')
#                     
#                     last_game_time = wettpoint_current_date + ' ' + last_game_time
#                     
#                 last_game_time = datetime.strptime(last_game_time, '%d.%m.%Y %H:%M') - timedelta(hours = 2)
#                 last_date_difference = last_game_time - tip.date
# and divmod(last_date_difference.total_seconds(), 60)[0] >= 0
                
############# NEEDS TESTING ######################
                # baseball is (currently) only sport without specific website
                if sport != 'baseball':
                    # only want to get details of tips that have been filled
                    if tip_instance.wettpoint_tip_stake != None:
                        # wettpoint h2h link is home team - away team
                        h2h_link = 'http://'+sport+'.'+constants.WETTPOINT_FEED+'/h2h/'+team_home_id+'-'+team_away_id+'.html'
                        
                        self.REQUEST_COUNT[constants.WETTPOINT_FEED] += 1
                        if self.REQUEST_COUNT[constants.WETTPOINT_FEED] > 1:
                            time.sleep(16.87)
                        
                        h2h_html = requests.get(h2h_link, headers=constants.HEADER)
                        h2h_soup = BeautifulSoup(h2h_html.text)
                        
                        # ensure teams are correct and we got the right link
                        team_links = h2h_soup.find('table').find_all('tr')[1].find_all('a')
                        if (
                            team_links[0].get_text().strip().upper() in (name.upper() for name in team_home_aliases) 
                            and team_links[1].get_text().strip().upper() in (name.upper() for name in team_away_aliases)
                            ):
                            h2h_header = h2h_soup.find('div', {'class' : 'inhalt2'}).find_all('h3', recursive=False)[1]
                            
                            h2h_total_text = h2h_header.find_next(text='Over / Under')
                            if h2h_total_text:
                                h2h_total_text = h2h_total_text.find_next('b').get_text().strip()
                                if 'UNDER' in h2h_total_text:
                                    h2h_total = 'Under'
                                elif 'OVER' in h2h_total_text: 
                                    h2h_total = 'Over'
                                    
                            h2h_team_text = h2h_header.find_next(text='1X2 System')
                            if h2h_team_text:
                                h2h_team = h2h_team_text.find_next('b').get_text().strip()
                                
                            h2h_stake_text = h2h_header.find_next(text='Risikofaktor')
                            if h2h_stake_text:
                                h2h_stake_text = h2h_stake_text.find_next('b').get_text().strip()
                                if h2h_stake_text.isdigt():
                                    h2h_stake = float(h2h_stake_text)
                        else:
                            if self.WARNING_MAIL is False:
                                self.WARNING_MAIL = ''
                            else:
                                self.WARNING_MAIL += "\n"
                            self.WARNING_MAIL += 'Probable '+tip_game_team_away+'('+team_away_id+') @ '+tip_game_team_home+'('+team_home_id+') wettpoint H2H ids for ' + tip_instance.game_league + ' MISMATCH!' + "\n"
############# END TESTING ######################
                  
                # go through the events listed
                for tip_row in tip_rows[2:]:
                    # has the wettpoint tip been changed
                    tip_change_created = False
                    self.temp_holder = False
                    
                    columns = tip_row.find_all('td')
                    
                    # standard information to determine if tip is of interest
                    team_names = columns[0].get_text()
                    league_name = columns[5].get_text()
                    game_time = re.sub('[^0-9\.\s:]', '', columns[6].get_text())
                    
                    # format the tip time to a standard
                    if not re.match('\d{2}\.\d{2}\.\d{4}', game_time):
                        wettpoint_current_time = datetime.utcnow() + timedelta(hours = 2)
                        wettpoint_current_date = wettpoint_current_time.strftime('%d.%m.%Y')
                        
                        game_time = wettpoint_current_date + ' ' + game_time
                    
                    # set game time to UTC    
                    game_time = datetime.strptime(game_time, '%d.%m.%Y %H:%M') - timedelta(hours = 2)
                    date_difference = game_time - tip_instance.date
                    
                    # is it a league we're interested in and does the game time match the tip's game time?
                    correct_league = False
                    
                    # is it the league of the tip object?
                    wettpoint_league_key = constants.LEAGUES[unicode(tip_instance.game_sport)][unicode(tip_instance.game_league)]['wettpoint']
                    if isinstance(wettpoint_league_key, list):
                        if league_name.strip() in wettpoint_league_key:
                            correct_league = True
                    else:
                        if league_name.strip() == wettpoint_league_key.strip():
                            correct_league = True
                    
                    # if the league is correct then does the time match (30 minute error window)    
                    if (
                        correct_league is True 
                        and abs(divmod(date_difference.total_seconds(), 60)[0]) <= 15
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
                            
                            if h2h_stake != False:
                                h2h_stake = (10 - h2h_stake) / 10.0
                                # stake tip changed
                                if (
                                    tip_instance.wettpoint_tip_stake is not None 
                                    and tip_instance.wettpoint_tip_stake != tip_stake + h2h_stake
                                    ):
                                    tip_instance = self.create_tip_change_object(tip_instance, 'stake', 'stake_both', not tip_change_created)
                                    tip_change_created = True
                                
                                tip_instance.wettpoint_tip_stake = tip_stake + h2h_stake
                            else:
                                # stake tip changed
                                if (
                                    tip_instance.wettpoint_tip_stake is not None 
                                    and tip_instance.wettpoint_tip_stake != tip_stake
                                    ):
                                    tip_instance = self.create_tip_change_object(tip_instance, 'stake', 'stake_chart', not tip_change_created)
                                    tip_change_created = True
                                
                                tip_instance.wettpoint_tip_stake = tip_stake
                            
                            # change object created, put in datastore
                            if self.temp_holder != False:
                                self.temp_holder.put()
                            
                            break
                        # one of the team names matches but the other doesn't, send admin mail to check team names
                        # could either be 1) team name missing or 2) wettpoint has wrong game listed
                        elif home_team.strip().upper() in (name.upper() for name in team_home_aliases):
                            if self.WARNING_MAIL is False:
                                self.WARNING_MAIL = ''
                            else:
                                self.WARNING_MAIL += "\n"
                            self.WARNING_MAIL += 'Probable ' + str(away_team) + ' WETTPOINT NAMES for ' + str(unicode(tip_instance.game_league)) + ', ' + str(unicode(tip_instance.game_sport)) + ' MISMATCH!' + "\n"
                        elif away_team.strip().upper() in (name.upper() for name in team_away_aliases):
                            if self.WARNING_MAIL is False:
                                self.WARNING_MAIL = ''
                            else:
                                self.WARNING_MAIL += "\n"
                            self.WARNING_MAIL += 'Probable ' + str(home_team) + ' WETTPOINT NAMES for ' + str(unicode(tip_instance.game_league)) + ', ' + str(unicode(tip_instance.game_sport)) + ' MISMATCH!' + "\n"
                    # tip has passed this object (i.e. no tip upcoming for this event therefore tip stake = 0)
                    elif divmod(date_difference.total_seconds(), 60)[0] >= 15:
                        if (
                            tip_instance.wettpoint_tip_total is not None 
                            and h2h_total is not False 
                            and tip_instance.wettpoint_tip_total != h2h_total
                            ):
                            tip_instance = self.create_tip_change_object(tip_instance, 'total', 'site_total', not tip_change_created)
                            tip_change_created = True
                        if h2h_total != False:
                            tip_instance.wettpoint_tip_total = h2h_total
                            
                        if h2h_team != False:
                            # currently going on the assumption that if no tip stake then there's no tip team
                            # email admin if this proves not to be the case... then we panic
                            if self.WARNING_MAIL is False:
                                self.WARNING_MAIL = ''
                            else:
                                self.WARNING_MAIL += "\n"
                            self.WARNING_MAIL += 'No tip stake, but tip team exists! Now we panic... ' + str(away_team) + ' @ ' + str(home_team) + ' for ' + str(unicode(tip_instance.game_league)) + "\n"
#                             if tip.wettpoint_tip_team is not None and h2h_team is not False and tip.wettpoint_tip_team != h2h_team:
#                                 tip = self.create_tip_change_object(tip, 'team', 'site_team', not tip_change_created)
#                                 tip_change_created = True
#                                 tip.wettpoint_tip_team = h2h_team
                       
                        if h2h_stake != False:
                            h2h_stake = (10 - h2h_stake) / 10.0
                            if (
                                tip_instance.wettpoint_tip_stake is not None 
                                and tip_instance.wettpoint_tip_stake != h2h_stake 
                                and tip_instance.wettpoint_tip_stake != 0.0
                                ):
                                tip_instance = self.create_tip_change_object(tip_instance, 'stake', 'site_stake', not tip_change_created)
                                tip_change_created = True
                            
                            tip_instance.wettpoint_tip_stake = h2h_stake
                        else:
                            if (
                                tip_instance.wettpoint_tip_stake is not None 
                                and tip_instance.wettpoint_tip_stake != 0.0
                                ):
                                tip_instance = self.create_tip_change_object(tip_instance, 'stake', 'stake_only', not tip_change_created)
                                tip_change_created = True
                                    
                            tip_instance.wettpoint_tip_stake = 0.0
                        
                        # change object created, put in datastore
                        if self.temp_holder != False:
                            self.temp_holder.put()
                            
                        break
                
                not_elapsed_tips_by_sport[sport_key][tip_instance.key] = tip_instance
                
        return not_elapsed_tips_by_sport
                                    
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
        
        query = TipChange.gql('WHERE tip_key = :1', str(tip_instance.key))
        
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
        tip_change_object.tip_key = str(tip_instance.key)
            
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
    
    def fill_lines(self, not_elapsed_tips_by_sport):
        possible_ppd_tips_by_sport_league = {}
        
        # go through all our sports
        for sport_key in constants.SPORTS:
            if sport_key not in not_elapsed_tips_by_sport:
                continue
            
            for tip_instance in not_elapsed_tips_by_sport[sport_key].values():
                if (tip_instance.date - datetime.now()).total_seconds() < 0:
                    # tip has started, move onto next
                    tip_instance.elapsed = True
                    # update this tip
                    not_elapsed_tips_by_sport[sport_key][tip_instance.key] = tip_instance
                    continue
                
                if tip_instance.wettpoint_tip_stake is None:
                    # tip stake hasn't been determined yet, move on
                    continue
                
                # pinnacle call failed, go to next sport/league
                if sport_key not in self.FEED:
                    break
                elif tip_instance.game_league not in self.FEED[sport_key]:
                    continue
                
                if tip_instance.pinnacle_game_no in self.FEED[sport_key][tip_instance.game_league]:
                    # successful pinnacle call + game line exists
                    game_tag = self.FEED[sport_key][tip_instance.game_league][tip_instance.pinnacle_game_no]
                    
                    for period in game_tag.find('periods').find_all('period'):
                        # currently only interested in full game lines
                        if int(period.period_number.get_text()) == 0 or period.period_description.get_text() in ['Game','Match']:
                            # get the total lines
                            if period.total:
                                # get actual total number
                                if tip_instance.total_no:
                                    hash1 = json.loads(unicode(tip_instance.total_no))
                                else:
                                    hash1 = {}
                                    
                                hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = period.total.total_points.get_text()
                                tip_instance.total_no = json.dumps(hash1)
                                
                                # get the total odds line
                                if tip_instance.total_lines:
                                    hash1 = json.loads(unicode(tip_instance.total_lines))
                                else:
                                    hash1 = {}
                                
                                if tip_instance.wettpoint_tip_total == 'Over':
                                    hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = period.total.over_adjust.get_text()
                                else:
                                    hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = period.total.under_adjust.get_text()
                                    
                                tip_instance.total_lines = json.dumps(hash1)
                            # get the moneyline
                            if period.moneyline:
                                if tip_instance.team_lines:
                                    hash1 = json.loads(unicode(tip_instance.team_lines))
                                else:
                                    hash1 = {}
                                
                                # get tip team line
                                if tip_instance.wettpoint_tip_team != None:
                                    moneyline = ''
                                    for i in tip_instance.wettpoint_tip_team:
                                        if i == '1':
                                            moneyline += period.moneyline.moneyline_home.get_text() + '|'
                                        elif i == 'X':
                                            moneyline += period.moneyline.moneyline_draw.get_text() + '|'
                                        elif i == '2':
                                            moneyline += period.moneyline.moneyline_visiting.get_text() + '|'
                                    
                                    if (
                                        period.moneyline.moneyline_draw 
                                        and len(tip_instance.wettpoint_tip_team) < 2
                                        ):
                                        moneyline += period.moneyline.moneyline_draw.get_text()
                                        
                                    moneyline = moneyline.rstrip('|')
                                    hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = moneyline
                                else:
                                    # if no tip team, get favourite line
                                    moneyline = ''
                                    if float(period.moneyline.moneyline_visiting.get_text()) < float(period.moneyline.moneyline_home.get_text()):
                                        tip_instance.wettpoint_tip_team = '2'
                                        moneyline = period.moneyline.moneyline_visiting.get_text()
                                    else:
                                        tip_instance.wettpoint_tip_team = '1'
                                        moneyline = period.moneyline.moneyline_home.get_text()
                                        
                                    if period.moneyline.moneyline_draw:
                                        moneyline += '|'+period.moneyline.moneyline_draw.get_text()
                                        
                                    hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = moneyline
                                        
                                tip_instance.team_lines = json.dumps(hash1)
                                
                            if period.spread:
                                if tip_instance.spread_no:
                                    hash1 = json.loads(unicode(tip_instance.spread_no))
                                else:
                                    hash1 = {}
                                    
                                if tip_instance.spread_lines:
                                    hash2 = json.loads(unicode(tip_instance.spread_lines))
                                else:
                                    hash2 = {}
                                    
                                if tip_instance.wettpoint_tip_team.find('1') != -1:
                                    hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = period.spread.spread_home.get_text()
                                    hash2[datetime.now().strftime('%d.%m.%Y %H:%M')] = period.spread.spread_adjust_home.get_text()
                                elif tip_instance.wettpoint_tip_team.find('2') != -1:
                                    hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = period.spread.spread_visiting.get_text()
                                    hash2[datetime.now().strftime('%d.%m.%Y %H:%M')] = period.spread.spread_adjust_visiting.get_text()
                                else:
                                    if float(period.spread.spread_visiting.get_text()) < float(period.spread.spread_home.get_text()):
                                        tip_instance.wettpoint_tip_team = '2'
                                        hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = period.spread.spread_visiting.get_text()
                                        hash2[datetime.now().strftime('%d.%m.%Y %H:%M')] = period.spread.spread_adjust_visiting.get_text()
                                    else:
                                        tip_instance.wettpoint_tip_team = '1'
                                        hash1[datetime.now().strftime('%d.%m.%Y %H:%M')] = period.spread.spread_home.get_text()
                                        hash2[datetime.now().strftime('%d.%m.%Y %H:%M')] = period.spread.spread_adjust_home.get_text()
                                    
                                tip_instance.spread_no = json.dumps(hash1)
                                tip_instance.spread_lines = json.dumps(hash2)
                            
                            not_elapsed_tips_by_sport[sport_key][tip_instance.key] = tip_instance
                            break
                else:
                    #TODO: check for a duplicate game in feed... if one is found, either email admin or delete automatically
                    # either game was taken off the board (for any number of reasons) - could be temporary
                    # or game is a duplicate (something changed that i didn't account for)
                    logging.warning('Missing Game: Cannot find '+tip_instance.game_team_home.strip()+' or '+tip_instance.game_team_away.strip()+' for '+str(tip_instance.key))
                    
                    if tip_instance.game_sport not in possible_ppd_tips_by_sport_league:
                        possible_ppd_tips_by_sport_league[tip_instance.game_sport] = {}
                    if tip_instance.game_league not in possible_ppd_tips_by_sport_league[tip_instance.game_sport]:
                        possible_ppd_tips_by_sport_league[tip_instance.game_sport][tip_instance.game_league] = {}
                    possible_ppd_tips_by_sport_league[tip_instance.game_sport][tip_instance.game_league][tip_instance.key] = tip_instance
                    
        return not_elapsed_tips_by_sport, possible_ppd_tips_by_sport_league
        
    def find_games(self):
        """Find a list of games (and their details) corresponding to our interests
        """
        new_or_updated_tips = {}
        
        # get sports we're interested in listed in constant SPORTS
        for sport, keys in constants.SPORTS.iteritems():
            sport_feed = constants.PINNACLE_FEED + '?sporttype=' + keys['pinnacle']
            
            self.REQUEST_COUNT[constants.PINNACLE_FEED] += 1
            if self.REQUEST_COUNT[constants.PINNACLE_FEED] > 1:
                time.sleep(73.6)
            
            #TODO: grab entire pinnacle feed to avoid hitting pinnacle more than once (how much bytes get transferred on each request?)
            # scrape the pinnacle XML feed
            xml = requests.get(sport_feed, headers=constants.HEADER)
            soup = BeautifulSoup(xml.text, 'xml')
            
            # get all the game (event) tags
            all_games = soup.find_all('event')
            
            # store all relevant game tags for future use
            self.FEED[sport] = {}
            
            # iterate over all the games
            for game_tag in all_games:
                # convert game datetime string to standard GMT datettime object
                date_GMT = datetime.strptime(unicode(game_tag.find('event_datetimeGMT').string), '%Y-%m-%d %H:%M')
                # get teams
                participants = game_tag.find_all('participant')
                
                # game already elapsed, move on to next
                if (date_GMT - datetime.now()).total_seconds() < 0:
                    continue
                
                # store team information in tip object - first initialization of tip object
                tip_instance = False
                # get both teams information
                for participant_tag in participants:
                    # create tip object variable if not yet done, otherwise work on existing tip object created by opponent
                    if not tip_instance:
                        # get the league string so we can find universal sport key
                        pinnacle_league = unicode(game_tag.find('league').string)
                        league = False
                        
                        # unfinished constant (the sport has no leagues specified)?!
                        if not sport in constants.LEAGUES:
                            logging.warning(str(sport)+' has no leagues?!')
                            break
                        
                        # is this a league we're interested in (i.e. exists in LEAGUES constant)?
                        for sport_key, sport_leagues in constants.LEAGUES[sport].iteritems():
                            # find the universal sport key for future reference
                            pinnacle_league_key = sport_leagues['pinnacle']
                            
                            # single league can have multiple league names (ex. conferences)
                            if isinstance(pinnacle_league_key, list):
                                if pinnacle_league in pinnacle_league_key:
                                    league = sport_key
                            else:
                                if pinnacle_league == pinnacle_league_key:
                                    league = sport_key
                        
                        if league is False:
                            # not a league we're interested in, move onto next game tag
                            break
                        else:
                            # keep all tag information so don't have to scrape again if we need more information later
                            if not league in self.FEED[sport]:
                                self.FEED[sport][league] = {}
                            
                            # pinnacle game numbers should be unique for each league
                            if game_tag.find('gamenumber').string in self.FEED[sport][league]:
                                for period in game_tag.find('periods').find_all('period'):
                                    # currently only interested in full game lines
                                    if (
                                        int(period.period_number.get_text()) == 0 
                                        or period.period_description.get_text() in ['Game','Match']
                                        ):
                                        raise Exception('Multiple matching game numbers in same league listed at the same time! ' + game_tag.find('gamenumber').string)
                                break
                            else:
                                for period in game_tag.find('periods').find_all('period'):
                                    # currently only interested in full game lines
                                    if (
                                        int(period.period_number.get_text()) == 0 
                                        or period.period_description.get_text() in ['Game','Match']
                                        ):
#                                         sys.stderr.write("Add game: "+game_tag.find('gamenumber').string+" for "+unicode(participant_tag.find('participant_name').string))
#                                         sys.stderr.write("\n")
                                        self.FEED[sport][league][game_tag.find('gamenumber').string] = game_tag
                                        break
                                if game_tag.find('gamenumber').string not in self.FEED[sport][league]:
                                    break
                        
                        # skip test cases
                        if re.match('^TEST\d', unicode(participant_tag.find('participant_name').string)):
                            break
                        # also skip grand salami cases
                        elif (
                              unicode(participant_tag.find('participant_name').string).split(' ')[0].lower() == 'away' 
                              and participant_tag.find('visiting_home_draw').string == 'Visiting'
                              ):
                            break
                        elif (
                              unicode(participant_tag.find('participant_name').string).split(' ')[0].lower() == 'home' 
                              and participant_tag.find('visiting_home_draw').string == 'Home'
                              ):
                            break
                        
                        dh_team_string = unicode(participant_tag.find('participant_name').string)
                        if (
                            sport in teamconstants.TEAMS 
                            and league in teamconstants.TEAMS[sport]
                            ):
                            league_team_info = teamconstants.TEAMS[sport][league]
                            if isinstance(league_team_info, basestring):
                                # reference to another league information
                                league_team_info = teamconstants.TEAMS[sport][league_team_info]
                            
                            # pinnacle prefixes G# on team names if team has multiple games in a single day
                            # search and replace a existing tip object if an additional game gets added
                            dh_team_string_multi = re.search('^G\d\s+(.+)', dh_team_string)
                            if dh_team_string_multi:
                                dh_team_string_multi = dh_team_string_multi.group(1).strip()
                            
                            # ensure team string exists in team constant, otherwise email admin
                            if (
                                not dh_team_string in league_team_info['keys'] 
                                and (
                                     dh_team_string_multi 
                                     and not dh_team_string_multi in league_team_info['keys']
                                     )
                                ):
                                if self.WARNING_MAIL is False:
                                    self.WARNING_MAIL = ''
                                else:
                                    self.WARNING_MAIL += "\n"
                                self.WARNING_MAIL += str(dh_team_string) + ' for ' + str(league) + ', ' + str(sport) + ' does not exist!' + "\n"
                        # if team information hasn't been filled out for this league, can still store it but raise a warning
                        else:
                            logging.warning(str(league)+', '+str(sport)+' has no team information!')
                        
                        # away or home team?
                        if participant_tag.find('visiting_home_draw').string == 'Visiting':
                            # do a search of the datastore to see if current tip object already created based on game number, sport, league, and team name
                            query = Tip.gql('WHERE elapsed != True AND pinnacle_game_no = :1 AND game_sport = :2 AND game_league = :3 AND game_team_away = :4', 
                                            unicode(game_tag.find('gamenumber').string), 
                                            sport,
                                            league,
                                            dh_team_string
                                        )
                            
                            # safety measure to prevent count() function from doing multiple queries
                            query_count = query.count()
                            
                            # if tip object does not yet exist, create it
                            if query_count == 0:
                                # do a search for doubleheaders - game number would have changed so search for same time
                                if dh_team_string_multi:
                                    query = Tip.gql('WHERE elapsed != True AND date = :1 AND game_sport = :2 AND game_league = :3 AND game_team_away = :4', 
                                                    date_GMT,
                                                    sport,
                                                    league,
                                                    dh_team_string_multi
                                                )
                                    
                                    # safety measure to prevent count() function from doing multiple queries
                                    query_count = query.count()
                                
                                if query_count == 0:
                                    # no tip object exists yet, create new one
                                    tip_instance = Tip()
                                    tip_instance.rot_away = int(unicode(participant_tag.find('rotnum').string))
                                    tip_instance.game_team_away = unicode(participant_tag.find('participant_name').string)
                                else:
                                    # should be only one result if it exists
                                    if query_count > 1:
                                        raise Exception('Multiple matching datastore Tip objects to fill_games query!')
                                    
                                    # tip object exists, grab it
                                    tip_instance = query.get()
                                    
                                    # if any information is different (ex. time change) update it
                                    if (
                                        tip_instance.pinnacle_game_no != unicode(game_tag.find('gamenumber').string) 
                                        or tip_instance.game_team_away != unicode(participant_tag.find('participant_name').string) 
                                        or tip_instance.rot_away != int(unicode(participant_tag.find('rotnum').string))
                                        ):
                                        tip_instance.rot_away = int(unicode(participant_tag.find('rotnum').string))
                                        tip_instance.game_team_away = unicode(participant_tag.find('participant_name').string)
                                    # otherwise no need to update it because all data has already been stored so move onto next game tag
                                    else:
                                        tip_instance = False
                                        break
                            else:
                                # should be only one result if it exists
                                if query_count > 1:
                                    raise Exception('Multiple matching datastore Tip objects to fill_games query!')
                                
                                # tip object exists, grab it
                                tip_instance = query.get()
                                
                                # if any information is different (ex. time change) update it
                                if (
                                    tip_instance.date != date_GMT 
                                    or tip_instance.rot_away != int(unicode(participant_tag.find('rotnum').string))
                                    ):
                                    tip_instance.rot_away = int(unicode(participant_tag.find('rotnum').string))
                                # otherwise no need to update it because all data has already been stored so move onto next game tag
                                else:
                                    tip_instance = False
                                    break
                        elif participant_tag.find('visiting_home_draw').string == 'Home':
                            # do a search of the datastore to see if current tip object already created based on game number, sport, league, and team name
                            query = Tip.gql('WHERE elapsed != True AND pinnacle_game_no = :1 AND game_sport = :2 AND game_league = :3 AND game_team_home = :4', 
                                            unicode(game_tag.find('gamenumber').string),
                                            sport,
                                            league,
                                            dh_team_string
                                        )
                            
                            # safety measure to prevent count() function from doing multiple queries
                            query_count = query.count()
                            
                            # if tip object does not yet exist, create it
                            if query_count == 0:
                                # do a search for doubleheaders - game number would have changed so search for same time
                                if dh_team_string_multi:
                                    query = Tip.gql('WHERE elapsed != True AND date = :1 AND game_sport = :2 AND game_league = :3 AND game_team_home = :4', 
                                                    date_GMT,
                                                    sport,
                                                    league,
                                                    dh_team_string_multi
                                                )
                                    
                                    # safety measure to prevent count() function from doing multiple queries
                                    query_count = query.count()
                                
                                if query_count == 0:
                                    # no tip object exists yet, create new one
                                    tip_instance = Tip()
                                    tip_instance.rot_home = int(unicode(participant_tag.find('rotnum').string))
                                    tip_instance.game_team_home = unicode(participant_tag.find('participant_name').string)
                                else:
                                    # should be only one result if it exists
                                    if query_count > 1:
                                        raise Exception('Multiple matching datastore Tip objects to fill_games query!')
                                    
                                    # tip object exists, grab it
                                    tip_instance = query.get()
                                    
                                    # if any information is different (ex. time change) update it
                                    if (
                                        tip_instance.pinnacle_game_no != unicode(game_tag.find('gamenumber').string) 
                                        or tip_instance.game_team_home != unicode(participant_tag.find('participant_name').string) 
                                        or tip_instance.rot_home != int(unicode(participant_tag.find('rotnum').string))
                                        ):
                                        tip_instance.rot_home = int(unicode(participant_tag.find('rotnum').string))
                                        tip_instance.game_team_home = unicode(participant_tag.find('participant_name').string)
                                    # otherwise no need to update it because all data has already been stored so move onto next game tag
                                    else:
                                        tip_instance = False
                                        break
                            else:
                                # should be only one result if it exists
                                if query_count > 1:
                                    raise Exception('Multiple matching datastore Tip objects to fill_games query!')
                                
                                # tip object exists, grab it
                                tip_instance = query.get()
                                
                                # if any information is different (ex. time change) update it
                                if (
                                    tip_instance.date != date_GMT 
                                    or tip_instance.rot_home != int(unicode(participant_tag.find('rotnum').string))
                                    ):
                                    tip_instance.rot_home = int(unicode(participant_tag.find('rotnum').string))
                                # otherwise no need to update it because all data has already been stored so move onto next game tag
                                else:
                                    tip_instance = False
                                    break
                        
                        # add basic information to tip object
                        tip_instance.date = date_GMT
                        tip_instance.game_sport = sport
                        tip_instance.game_league = league
                        tip_instance.pinnacle_game_no = unicode(game_tag.find('gamenumber').string)
                    else:
                        # tip object already created (or set to be updated) by opponent
                        if participant_tag.find('visiting_home_draw').string == 'Visiting':
                            tip_instance.rot_away = int(unicode(participant_tag.find('rotnum').string))
                            tip_instance.game_team_away = unicode(participant_tag.find('participant_name').string)
                        elif participant_tag.find('visiting_home_draw').string == 'Home':
                            tip_instance.rot_home = int(unicode(participant_tag.find('rotnum').string))
                            tip_instance.game_team_home = unicode(participant_tag.find('participant_name').string)
                
                # if tip object is new or needs to be updated, do so now    
                if tip_instance != False:
                    # store in datastore immediately to ensure no conflicts in this session
                    tip_instance_key = tip_instance.put()
                    # store in constant for future use and additional commit
                    new_or_updated_tips[tip_instance.key] = tip_instance_key
        
        return new_or_updated_tips