#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import ndb

import json
import logging
import models

__APPVAR_SPORT_NAMES = 'sportconstants'
__APPVAR_LEAGUE_NAMES = 'leagueconstants'
__APPVAR_TEAM_NAMES = 'teamconstants'
__APPVAR_SPORTS_H2H_EXCLUDE = 'sportsh2hexclude'
__APPVAR_SPORTS_WEEKLY = 'sportsweekly'
__APPVAR_LEAGUES_OT_INCLUDED = 'leaguesotincluded'

__APPVAR_USER_AGENTS = 'header_user_agents'

VALID_APPVAR_LIST = [
               __APPVAR_SPORT_NAMES,
               __APPVAR_LEAGUE_NAMES,
               __APPVAR_TEAM_NAMES, 
               __APPVAR_SPORTS_H2H_EXCLUDE,
               __APPVAR_SPORTS_WEEKLY,
               __APPVAR_LEAGUES_OT_INCLUDED,
               __APPVAR_USER_AGENTS,
               ]

def get_sport_names_appvar():
    return get_or_set_app_var(__APPVAR_SPORT_NAMES)

def get_league_names_appvar():
    return get_or_set_app_var(__APPVAR_LEAGUE_NAMES)

def get_team_names_appvar():
    return get_or_set_app_var(__APPVAR_TEAM_NAMES)

def get_h2h_excluded_sports_appvar():
    return get_or_set_app_var(__APPVAR_SPORTS_H2H_EXCLUDE)

def get_weekly_sports_appvar():
    return get_or_set_app_var(__APPVAR_SPORTS_WEEKLY)

def get_leagues_ot_included_appvar():
    return get_or_set_app_var(__APPVAR_LEAGUES_OT_INCLUDED)

def get_header_user_agents():
    return get_or_set_app_var(__APPVAR_USER_AGENTS)

def set_app_var(key, value):
    if key not in VALID_APPVAR_LIST:
        raise KeyError('Invalid application variable key ('+key+')')
    
    if not isinstance(value, basestring) and value is not None:
        value = json.dumps(value)
    elif not value:
        value = None
    
    return models.ApplicationVariables(id=key, value=value).put()

def get_or_set_app_var(key):
    app_var = ndb.Key(models.ApplicationVariables, key).get()
    if app_var is None:
        logging.info('Creating new application variable ('+key+')!')
        app_var = set_app_var(key, None).get()
    value = app_var.value
    
    if value is not None:
        try:
            value = json.loads(value)
        except ValueError:
            pass
    
    return value