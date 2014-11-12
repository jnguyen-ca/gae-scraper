#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users, memcache

from models import DisplaySession
from scraper import Scraper
from tiparchive import TipArchive
import tipdisplay

import re
import json
import constants

class AwaitAction(webapp.RequestHandler):
    def get(self):
        self.TEMPLATE_TAGS = {
                              'display_value_input_name' : tipdisplay.DISPLAY_INPUT_NAME,
                              'display_value_upcoming' : tipdisplay.DISPLAY_VALUE_UPCOMING,
                              'display_value_results' : tipdisplay.DISPLAY_VALUE_RESULTS,
                              }
        
#         session_cookie = self.request.cookies.get('DisplaySessionCookie')
        session_cookie = memcache.get('DisplaySessionCookie')
        session_leagues = None
        if not session_cookie:
            session = DisplaySession.gql('WHERE user = :1', users.get_current_user()).get()
            if not session is None:
                session_leagues = json.loads(session.leagues)
#                 self.response.set_cookie('DisplaySessionCookie', unicode(session.leagues), expires=(datetime.datetime.now() + datetime.timedelta(days=1)), overwrite=True)
                memcache.set('DisplaySessionCookie', session.leagues)
        else:
            session_leagues = json.loads(session_cookie)
            
        self.TEMPLATE_TAGS['display_leagues'] = ''
        self.TEMPLATE_TAGS['display_leagues'] += '<div class="sport-columns">'
        for sport in sorted(constants.LEAGUES):
            leagues = constants.LEAGUES[sport]
            self.TEMPLATE_TAGS['display_leagues'] += '<div class="sport-column">'
            self.TEMPLATE_TAGS['display_leagues'] += '<h3>'+sport+'</h3>'
            for league in sorted(leagues.keys()):
                self.TEMPLATE_TAGS['display_leagues'] += '<div class="league-row">'
                self.TEMPLATE_TAGS['display_leagues'] += '<span class="league-title">'+league+'</span>'
                self.TEMPLATE_TAGS['display_leagues'] += '<div class="league-seasons">'
                self.TEMPLATE_TAGS['display_leagues'] += '<button class="add-season-button" onclick="return false;">Add Season</button>'
                self.TEMPLATE_TAGS['display_leagues'] += '<div class="add-season-inputs" style="display:none;">'
                self.TEMPLATE_TAGS['display_leagues'] += '<div class="from-inputs"><span>From:</span><input class="month-input"><input class="day-input"><input class="year-input"> (EST)</div>'
                self.TEMPLATE_TAGS['display_leagues'] += '<div class="to-inputs"><span>To:</span><input class="month-input"><input class="day-input"><input class="year-input"> (EST)</div>'
                self.TEMPLATE_TAGS['display_leagues'] += '</div>'
                if not session_leagues is None:
                    if league in session_leagues:
                        for dateRange, checked in session_leagues[league].iteritems():
                            self.TEMPLATE_TAGS['display_leagues'] += '<div class="season-control">'
                            self.TEMPLATE_TAGS['display_leagues'] += '<input type="checkbox" class="season-display-control" name="season-display-control" value="'+league+'&'+dateRange+'"'
                            if checked is True:
                                self.TEMPLATE_TAGS['display_leagues'] += ' checked=checked'
                            self.TEMPLATE_TAGS['display_leagues'] += '><span class="season-label">'+dateRange+'</span>'
                            self.TEMPLATE_TAGS['display_leagues'] += '<input type="checkbox" class="season-display-hidden-control" name="season-display-hidden-control" value="'+league+'&'+dateRange+'"'
                            if not checked is True:
                                self.TEMPLATE_TAGS['display_leagues'] += ' checked=checked'
                            self.TEMPLATE_TAGS['display_leagues'] += ' style="display: none;">'
                            self.TEMPLATE_TAGS['display_leagues'] += '</div>'
                self.TEMPLATE_TAGS['display_leagues'] += '</div>'
                self.TEMPLATE_TAGS['display_leagues'] += '</div>'
                    
            self.TEMPLATE_TAGS['display_leagues'] += '</div>'
        self.TEMPLATE_TAGS['display_leagues'] += '</div>'
        
        with open('frontpage.html') as f:
            for line in f:
                template_tags = re.finditer('\[template:(\S+)\]', line)
                if template_tags:
                    line = self.replace_template_tags(line, template_tags)
                    
                self.response.out.write(line)
                
    def replace_template_tags(self, line, template_tags):
        for match in template_tags:
            if match.group(1) in self.TEMPLATE_TAGS:
                line = line.replace(match.group(0), self.TEMPLATE_TAGS[match.group(1)])
        
        return line
                            
application = webapp.WSGIApplication([('/', AwaitAction), 
                                      ('/scrape', Scraper), 
                                      ('/display', tipdisplay.TipDisplay),
                                      ('/archive', TipArchive),
                                    ], 
                                    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()