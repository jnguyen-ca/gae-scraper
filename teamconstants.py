#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import logging
import util

def get_team_names_appvar():
    return util.get_or_set_app_var(util.APPVAR_TEAM_NAMES)

def get_base_league_key(sport, league):
    appvar_team_names = get_team_names_appvar()
    
    league_value = appvar_team_names[sport][league]
    if isinstance(league_value, basestring):
        return league_value
    
    return league

def get_league_teams(sport, league):
    appvar_team_names = get_team_names_appvar()
    
    league_teams = appvar_team_names[sport][league]
    if isinstance(league_teams, basestring):
        # reference to another league information
        league_teams = appvar_team_names[sport][league_teams]
            
    return league_teams

def get_team_aliases(sport, league, team_name):
    # remove the game digit to get correct team name aliases
    doubleheader_search = re.search('^G\d+\s+(.+)', team_name)
    if doubleheader_search:
        team_name = doubleheader_search.group(1).strip()
        
    OTB_search = re.search('^OTB\s+(.+)', team_name)
    if OTB_search:
        team_name = OTB_search.group(1).strip()
    
    team_aliases = [team_name]
    
    try:
        league_team_info = get_league_teams(sport, league)
    except KeyError:
        logging.warning(league+' for '+sport+' has no team information (1)!')
        return team_aliases, None
        
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