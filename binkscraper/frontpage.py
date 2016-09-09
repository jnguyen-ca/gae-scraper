#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('utils')

from google.appengine.ext import webapp
from google.appengine.api import users

from utils import appvar_util, html_util, memcache_util
from models import DisplaySession

import json

INPUT_NAME_TIPDISPLAY_TYPE = 'display'

DISPLAY_VALUE_SCRAPE = 'Scrape'
DISPLAY_VALUE_UPCOMING = 'Upcoming'
DISPLAY_VALUE_RESULTS = 'Results'
DISPLAY_VALUE_DASHBOARD = 'Analyze'

class FrontPage(webapp.RequestHandler):
    def get(self):
        html_util.add_template_tags({
                              'display_value_input_name' : INPUT_NAME_TIPDISPLAY_TYPE,
                              'display_value_scrape' : DISPLAY_VALUE_SCRAPE,
                              'display_value_upcoming' : DISPLAY_VALUE_UPCOMING,
                              'display_value_results' : DISPLAY_VALUE_RESULTS,
                              'display_value_dashboard' : DISPLAY_VALUE_DASHBOARD,
                              })
        
        session_cookie = memcache_util.get(memcache_util.MEMCACHE_KEY_FRONTPAGE_DISPLAY_LEAGUES)
        session_leagues = None
        if not session_cookie:
            session = DisplaySession.gql('WHERE user = :1', users.get_current_user()).get()
            if not session is None:
                session_leagues = json.loads(session.leagues)
                memcache_util.set(memcache_util.MEMCACHE_KEY_FRONTPAGE_DISPLAY_LEAGUES, session.leagues)
        else:
            session_leagues = json.loads(session_cookie)
            
        html_util.add_template_tag('display_leagues', '<div class="sport-columns">')
        sports = sorted(appvar_util.get_league_names_appvar())
        for sport in sports:
            leagues = appvar_util.get_league_names_appvar()[sport]
            html_util.add_template_tag('display_leagues', '<div class="sport-column">')
            html_util.add_template_tag('display_leagues', '<h3>'+sport+'</h3>')
            for league in sorted(leagues.keys()):
                html_util.add_template_tag('display_leagues', '<div class="league-row">')
                html_util.add_template_tag('display_leagues', '<span class="league-title">'+league+'</span>')
                html_util.add_template_tag('display_leagues', '<div class="league-seasons">')
                html_util.add_template_tag('display_leagues', '<button class="add-season-button" onclick="return false;">Add Season</button>')
                html_util.add_template_tag('display_leagues', '<div class="add-season-inputs" style="display:none;">')
                html_util.add_template_tag('display_leagues', '<div class="from-inputs"><span>From:</span><input class="month-input"><input class="day-input"><input class="year-input"> (EST)</div>')
                html_util.add_template_tag('display_leagues', '<div class="to-inputs"><span>To:</span><input class="month-input"><input class="day-input"><input class="year-input"> (EST)</div>')
                html_util.add_template_tag('display_leagues', '</div>')
                if not session_leagues is None:
                    if league in session_leagues:
                        for dateRange, checked in session_leagues[league].iteritems():
                            html_util.add_template_tag('display_leagues', '<div class="season-control">')
                            html_util.add_template_tag('display_leagues', '<input type="checkbox" class="season-display-control" name="season-display-control" value="'+league+'&'+dateRange+'"')
                            if checked is True:
                                html_util.add_template_tag('display_leagues', ' checked=checked')
                            html_util.add_template_tag('display_leagues', '><span class="season-label">'+dateRange+'</span>')
                            html_util.add_template_tag('display_leagues', '<input type="checkbox" class="season-display-hidden-control" name="season-display-hidden-control" value="'+league+'&'+dateRange+'"')
                            if not checked is True:
                                html_util.add_template_tag('display_leagues', ' checked=checked')
                            html_util.add_template_tag('display_leagues', ' style="display: none;">')
                            html_util.add_template_tag('display_leagues', '</div>')
                html_util.add_template_tag('display_leagues', '</div>')
                html_util.add_template_tag('display_leagues', '</div>')
                    
            html_util.add_template_tag('display_leagues', '</div>')
        html_util.add_template_tag('display_leagues', '</div>')
        
        html_util.print_html(self.response.out, html='frontpage.html')