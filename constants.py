#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import random
import os
import util

# use pinnacle sports xml feed as our official game list feed
PINNACLE_FEED = 'pinnaclesports.com'
WETTPOINT_FEED = 'wettpoint.com'
# TSN_FEED = 'http://www.tsn.ca/'
XSCORES_FEED = 'xscores.com'
BACKUP_SCORES_FEED = 'scorespro.com'

TIMEZONE_LOCAL = 'America/Edmonton'
TIMEZONE_WETTPOINT = 'Europe/Berlin'
TIMEZONE_SCOREBOARD = 'Europe/Athens'
TIMEZONE_BACKUP = 'Etc/GMT-1'

DATETIME_ISO_8601_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

def get_sport_names_appvar():
    return util.get_or_set_app_var(util.APPVAR_SPORT_NAMES)

def get_league_names_appvar():
    return util.get_or_set_app_var(util.APPVAR_LEAGUE_NAMES)

def get_h2h_excluded_sports_appvar():
    return util.get_or_set_app_var(util.APPVAR_SPORTS_H2H_EXCLUDE)

def get_weekly_sports_appvar():
    return util.get_or_set_app_var(util.APPVAR_SPORTS_WEEKLY)

def get_leagues_ot_included_appvar():
    return util.get_or_set_app_var(util.APPVAR_LEAGUES_OT_INCLUDED)

def __get_header_user_agents():
    return util.get_or_set_app_var(util.APPVAR_USER_AGENTS)

def is_local():
    return os.environ['SERVER_SOFTWARE'].startswith('Development')

def get_header():
    header = {}
    
    user_agents = __get_header_user_agents()
    
    header['User-Agent'] = random.choice(user_agents)
    header['Accept-Encoding'] = 'gzip, deflate'
    
    return header