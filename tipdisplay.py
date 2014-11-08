#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('libs/pytz-2014.7')

from google.appengine.ext import webapp
from google.appengine.api import users, memcache

from models import Tip, DisplaySession

from datetime import datetime, timedelta

import json
import logging
import constants
import teamconstants
import pytz
import tipanalysis

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
.game_time-MST {width: 12%;}
.upcoming_game {margin: 6px 0;}
.upcoming_game > span {display: inline-block; margin-right: 12px; min-width: 60px;}
.upcoming_game .participants {width: 22%; text-overflow: ellipsis;}
.upcoming_game .tip-team {text-overflow: ellipsis;}
.upcoming_game .tip-date {width: 10%;}
.upcoming_game .tip-line-adjusted_win, .upcoming_game .tip-line-adjusted_loss {background: lightgrey; text-align: center;}
.upcoming_game .today {font-weight: bold;}
.upcoming_game .closing {color: red;}
.upcoming_game .pending {color: green;}
''')
        self.html.append('<body>')
        
        #TODO: move to tipanalysis
        # get user to get league dates for tip analysis
        self.DATASTORE_READS += 1
        session = DisplaySession.gql('WHERE user = :1', users.get_current_user()).get()
        
        if session is None:
            self.DATASTORE_PUTS += 1
            session = DisplaySession()
            session.user = users.get_current_user()
        
        visible_seasons = self.request.get_all('season-display-control')
        hidden_seasons = self.request.get_all('season-display-hidden-control')
        
        display_seasons = {}
        
        # sort the given dates into visible vs hidden
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
        
        # update the dates (every time, regardless of change or not)
        ds_json_string = json.dumps(display_seasons)
        memcache.set('DisplaySessionCookie', ds_json_string)
        session.leagues = ds_json_string
        
        self.DATASTORE_READS += 1
        query = Tip.gql('WHERE archived != True')
        not_archived_tips_values_by_sport_league = {}
        unsorted_sport_league_date = []
        for tip_instance in query:
            self.DATASTORE_READS += 1
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
                        
            if initialize is True:
                unsorted_sport_league_date.append([tip_instance.game_sport, tip_instance.game_league, tip_instance.date])
        
        # sort leagues based on league's next game
        sorted_sport_league_date = sorted(unsorted_sport_league_date, key=lambda x: x[2])
        
        for sport_league_date in sorted_sport_league_date:
            sport_key = sport_league_date[0]
            league_key = sport_league_date[1]
            
            # sort all the league's tips
            not_archived_tips_values = sorted(not_archived_tips_values_by_sport_league[sport_key][league_key], key=lambda x: x.date)
            
            wettpoint_table = 'http://www.forum.'+constants.WETTPOINT_FEED+'/fr_toptipsys.php?cat='+constants.SPORTS[sport_key]['wettpoint']
            
            # display all non-archived tips
            self.html.append("<div class='league_key'><b>%(league_key)s</b> <a href='%(wettpoint_table)s'>Table</a></div>" % locals())
            self.list_next_games(league_key, not_archived_tips_values)
        
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
        
        session.last_login = datetime.utcnow()
        self.DATASTORE_PUTS += 1
        session.put()
        
        logging.debug('Total Reads: '+str(self.DATASTORE_READS)+', Total Writes: '+str(self.DATASTORE_PUTS))
        
    def list_next_games(self, league, not_archived_tips):
        next_games_html = []
        
        local_timezone = pytz.timezone(constants.TIMEZONE_LOCAL)
        
        game_count = 0
        next_games_html.append('<div class="upcoming_games">')
        for tip_instance in not_archived_tips:
            game_count += 1
            game_row_id = league.lower().replace(' ','_')+'-'+str(game_count)
            
            current_time = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(local_timezone)
            game_time = tip_instance.date.replace(tzinfo=pytz.utc).astimezone(local_timezone)
            
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
            
            wettpoint_h2h_link = None
            if (
                tip_instance.game_sport not in constants.SPORTS_H2H_EXCLUDE 
                and team_away_id is not None 
                and team_home_id is not None
            ):
                wettpoint_h2h_link = 'http://'+constants.SPORTS[tip_instance.game_sport]['wettpoint']+'.'+constants.WETTPOINT_FEED+'/h2h/'+team_home_id+'-'+team_away_id+'.html'
            
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
                    
            next_games_html.append('<div id="%(game_row_id)s" class="upcoming_game">' % locals())
            next_games_html.append('<span class="game-count" style="min-width: 16px;">%(game_count)d</span>' % locals())
            next_games_html.append('<span class="%(date_class)s">%(game_time)s</span>' % locals())
            next_games_html.append('<span class="participants"><span class="away">%(team_away)s</span> - <span class="home">%(team_home)s</span></span>' % locals())
            next_games_html.append('<span class="tip-stake">%(wettpoint_stake)s</span>' % locals())
            next_games_html.append('<span class="tip-team">%(wettpoint_team)s</span>' % locals())
            next_games_html.append('<span class="tip-line">%(latest_line)s</span>' % locals())
            next_games_html.append('<span class="tip-line">%(spread_no)s</span>' % locals())
            next_games_html.append('<span class="tip-date">%(latest_date)s</span>' % locals())
            next_games_html.append('<span class="tip-total">%(wettpoint_total)s</span>' % locals())
            next_games_html.append('<span class="tip-total_no">%(total_no)s</span>' % locals())
            if wettpoint_h2h_link is not None:
                next_games_html.append('<span class="h2h-link"><a href="%(wettpoint_h2h_link)s">H2H</a></span>' % locals())
            next_games_html.append('</div>')
        
        next_games_html.append('</div>')
        
        self.html.append("".join(next_games_html))
