#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

APPVAR_KEY_SCOREBOARD = 'scoreboard'
APPVAR_KEY_WETTPOINT = 'wettpoint'
APPVAR_KEY_PINNACLE = 'pinnacle'

from binkscraper import constants

class ApplicationVariableException(constants.ApplicationException):
    """Base exception for operations on app var"""
    def __init__(self, message):
        super(ApplicationVariableException, self).__init__(message, constants.MAIL_TITLE_APPLICATION_ERROR)

from google.appengine.ext import ndb

import json
import logging
from binkscraper import models

__APPVAR_SPORT_NAMES = 'sportconstants'
__APPVAR_LEAGUE_NAMES = 'leagueconstants'
__APPVAR_TEAM_NAMES = 'teamconstants'
__APPVAR_SPORTS_H2H_EXCLUDED = 'sportsh2hexcluded'
__APPVAR_SPORTS_WEEKLY = 'sportsweekly'
__APPVAR_LEAGUES_OT_INCLUDED = 'leaguesotincluded'
__APPVAR_TEAM_NAMES_EXCLUDED = 'teamnamesexcluded'

__APPVAR_USER_AGENTS = 'header_user_agents'

VALID_APPVAR_LIST = [
               __APPVAR_SPORT_NAMES,
               __APPVAR_LEAGUE_NAMES,
               __APPVAR_TEAM_NAMES, 
               __APPVAR_SPORTS_H2H_EXCLUDED,
               __APPVAR_SPORTS_WEEKLY,
               __APPVAR_LEAGUES_OT_INCLUDED,
               __APPVAR_TEAM_NAMES_EXCLUDED,
               __APPVAR_USER_AGENTS,
               ]

def get_sport_names_appvar():
    return get_or_set_app_var(__APPVAR_SPORT_NAMES)

def get_league_names_appvar():
    return get_or_set_app_var(__APPVAR_LEAGUE_NAMES)

def get_team_names_appvar():
    return get_or_set_app_var(__APPVAR_TEAM_NAMES)

def get_team_names_excluded_appvar():
    return get_or_set_app_var(__APPVAR_TEAM_NAMES_EXCLUDED)

def get_h2h_excluded_sports_appvar():
    return get_or_set_app_var(__APPVAR_SPORTS_H2H_EXCLUDED)

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