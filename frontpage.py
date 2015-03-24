#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import webapp
from google.appengine.api import users

from models import DisplaySession

import json
import constants
import util
import memcache_util

INPUT_NAME_TIPDISPLAY_TYPE = 'display'

DISPLAY_VALUE_SCRAPE = 'Scrape'
DISPLAY_VALUE_UPCOMING = 'Upcoming'
DISPLAY_VALUE_RESULTS = 'Results'
DISPLAY_VALUE_DASHBOARD = 'Analyze'

class FrontPage(webapp.RequestHandler):
    def get(self):
        util.add_template_tags({
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
            
        util.add_template_tag('display_leagues', '<div class="sport-columns">')
        sports = sorted(constants.get_league_names_appvar())
        for sport in sports:
            leagues = constants.get_league_names_appvar()[sport]
            util.add_template_tag('display_leagues', '<div class="sport-column">')
            util.add_template_tag('display_leagues', '<h3>'+sport+'</h3>')
            for league in sorted(leagues.keys()):
                util.add_template_tag('display_leagues', '<div class="league-row">')
                util.add_template_tag('display_leagues', '<span class="league-title">'+league+'</span>')
                util.add_template_tag('display_leagues', '<div class="league-seasons">')
                util.add_template_tag('display_leagues', '<button class="add-season-button" onclick="return false;">Add Season</button>')
                util.add_template_tag('display_leagues', '<div class="add-season-inputs" style="display:none;">')
                util.add_template_tag('display_leagues', '<div class="from-inputs"><span>From:</span><input class="month-input"><input class="day-input"><input class="year-input"> (EST)</div>')
                util.add_template_tag('display_leagues', '<div class="to-inputs"><span>To:</span><input class="month-input"><input class="day-input"><input class="year-input"> (EST)</div>')
                util.add_template_tag('display_leagues', '</div>')
                if not session_leagues is None:
                    if league in session_leagues:
                        for dateRange, checked in session_leagues[league].iteritems():
                            util.add_template_tag('display_leagues', '<div class="season-control">')
                            util.add_template_tag('display_leagues', '<input type="checkbox" class="season-display-control" name="season-display-control" value="'+league+'&'+dateRange+'"')
                            if checked is True:
                                util.add_template_tag('display_leagues', ' checked=checked')
                            util.add_template_tag('display_leagues', '><span class="season-label">'+dateRange+'</span>')
                            util.add_template_tag('display_leagues', '<input type="checkbox" class="season-display-hidden-control" name="season-display-hidden-control" value="'+league+'&'+dateRange+'"')
                            if not checked is True:
                                util.add_template_tag('display_leagues', ' checked=checked')
                            util.add_template_tag('display_leagues', ' style="display: none;">')
                            util.add_template_tag('display_leagues', '</div>')
                util.add_template_tag('display_leagues', '</div>')
                util.add_template_tag('display_leagues', '</div>')
                    
            util.add_template_tag('display_leagues', '</div>')
        util.add_template_tag('display_leagues', '</div>')
        
        util.print_html(self.response.out, html='frontpage.html')