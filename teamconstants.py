#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('utils')

from utils import appvar_util

import re
import logging

def get_base_league_key(sport, league):
    appvar_team_names = appvar_util.get_team_names_appvar()
    
    league_value = appvar_team_names[sport][league]
    if isinstance(league_value, basestring):
        return league_value
    
    return league

def is_league_alias(site_key, sport_key, league_key, possible_league_alias):
    possible_league_alias = possible_league_alias.strip()
    if league_key.strip() == possible_league_alias:
        return True
    
    try:
        site_league_name = appvar_util.get_league_names_appvar()[sport_key][league_key][site_key]
    except KeyError:
        raise appvar_util.ApplicationVariableException('%s does not have a league name for [%s / %s]' % (site_key, league_key, sport_key))
                        
    if isinstance(site_league_name, list):
        if possible_league_alias in site_league_name:
            return True
    else:
        if possible_league_alias == site_league_name:
            return True
    return False

def split_doubleheaders_team_names(team_name):
    team_game_string = None
    
    team_name_multi = re.search('^(G\d+\s+)(.+)', team_name)
    if team_name_multi:
        team_game_string = team_name_multi.group(1)
        team_name = team_name_multi.group(2).strip()
        
    return team_name, team_game_string

def get_league_teams(sport, league):
    appvar_team_names = appvar_util.get_team_names_appvar()
    
    league_teams = appvar_team_names[sport][league]
    if isinstance(league_teams, basestring):
        # reference to another league information
        league_teams = appvar_team_names[sport][league_teams]
            
    return league_teams

def get_team_datastore_name_and_id(sport, league, team_name):
    league_team_info = get_league_teams(sport, league)
    
    OTB_search = re.search('^OTB\s+(.+)', team_name)
    if OTB_search:
        team_name = OTB_search.group(1)
    
    team_name = split_doubleheaders_team_names(team_name)[0]
    
    team_name_upper = team_name.upper().strip()
    for datastore_name, key_team_id in league_team_info['keys'].iteritems():
        if team_name_upper == datastore_name.upper():
            # letter casing was just off
            return datastore_name, key_team_id
        
    for value_team_id, possible_team_aliases in league_team_info['values'].iteritems():
        if team_name_upper in (name_alias.upper() for name_alias in possible_team_aliases):
            for datastore_name, key_team_id in league_team_info['keys'].iteritems():
                if value_team_id == key_team_id:
                    # team name was an alias of a datastore name
                    return datastore_name, key_team_id
    
    return None, None