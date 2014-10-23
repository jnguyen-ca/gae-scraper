#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('libs/oauth2client-1.3')
sys.path.append('libs/gspread-0.2.2')
sys.path.append('libs/pytz-2014.7')

from google.appengine.ext import webapp
from oauth2client.client import SignedJwtAssertionCredentials

from httplib import HTTPException
from datetime import date, datetime, timedelta

import string
import logging
import pytz
import gspread
import constants
import models
import teamconstants
import tipanalysis

BET_TYPE_AWAY_UNDERDOG = 'Away Underdog'
BET_TYPE_AWAY_FAVOURITE = 'Away Favourite'
BET_TYPE_HOME_UNDERDOG = 'Home Underdog'
BET_TYPE_HOME_FAVOURITE = 'Home Favourite'

BET_TYPE_SPREAD_AWAY_UNDERDOG = 'Spread Away Underdog'
BET_TYPE_SPREAD_AWAY_FAVOURITE = 'Spread Away Favourite'
BET_TYPE_SPREAD_HOME_UNDERDOG = 'Spread Home Underdog'
BET_TYPE_SPREAD_HOME_FAVOURITE = 'Spread Home Favourite'

BET_TYPE_SPREAD_DRAW_AWAY_UNDERDOG = 'Spread X2 Away Underdog'
BET_TYPE_SPREAD_DRAW_AWAY_FAVOURITE = 'Spread X2 Away Favourite'
BET_TYPE_SPREAD_DRAW_HOME_UNDERDOG = 'Spread 1X Home Underdog'
BET_TYPE_SPREAD_DRAW_HOME_FAVOURITE = 'Spread 1X Home Favourite'
BET_TYPE_SPREAD_NO_DRAW_HOME_UNDERDOG = 'Spread 12 Home Underdog'
BET_TYPE_SPREAD_NO_DRAW_HOME_FAVOURITE = 'Spread 12 Home Favourite'

BET_TYPE_SIDE_DRAW = 'Side Draw'
BET_TYPE_SIDE_DRAW_AWAY_UNDERDOG = 'Side X2 Away Underdog'
BET_TYPE_SIDE_DRAW_AWAY_FAVOURITE = 'Side X2 Away Favourite'
BET_TYPE_SIDE_DRAW_HOME_UNDERDOG = 'Side 1X Home Underdog'
BET_TYPE_SIDE_DRAW_HOME_FAVOURITE = 'Side 1X Home Favourite'
BET_TYPE_SIDE_NO_DRAW_AWAY_UNDERDOG = 'Side 12 Away Underdog'
BET_TYPE_SIDE_NO_DRAW_AWAY_FAVOURITE = 'Side 12 Away Favourite'
BET_TYPE_SIDE_NO_DRAW_HOME_UNDERDOG = 'Side 12 Home Underdog'
BET_TYPE_SIDE_NO_DRAW_HOME_FAVOURITE = 'Side 12 Home Favourite'

BET_TYPE_TOTAL_OVER = models.TIP_SELECTION_TOTAL_OVER
BET_TYPE_TOTAL_UNDER = models.TIP_SELECTION_TOTAL_UNDER
BET_TYPE_TOTAL_NONE = 'None'

BET_TIME_NIGHT = '9PM Day Before'
BET_TIME_MORNING = '8AM Same Day'
BET_TIME_NOON = '11:30AM Same Day'
BET_TIME_LATEST = 'Latest'

def is_side_team_favourite(**kwargs):
    side_line = draw_line = spread_no = spread_line = is_home = None
    
    if 'side' in kwargs:
        try:
            side_line = float(kwargs['side'])
        except (ValueError, TypeError):
            side_line = None
    if 'draw' in kwargs:
        try:
            draw_line = float(kwargs['draw'])
        except (ValueError, TypeError):
            draw_line = None
    if 'spread_no' in kwargs:
        try:
            spread_no = float(kwargs['spread_no'])
        except (ValueError, TypeError):
            spread_no = None
    if 'spread' in kwargs:
        try:
            spread_line = float(kwargs['spread'])
        except (ValueError, TypeError):
            spread_line = None
    if 'home' in kwargs:
        is_home = kwargs['home']
        
    if (
        spread_no is not None 
        and spread_no != 0
    ):
        if 0 > spread_no:
            return True
        elif 0 < spread_no:
            return False
    elif side_line is not None:
        if -104 > side_line:
            return True
        elif (
              -104 == side_line 
              and (
                   draw_line is not None 
                   or (
                      is_home is not None 
                      and is_home is True
                    )
              )
        ):
            return True
        elif (
              -104 < side_line 
              and draw_line is None
        ):
            return False
        elif draw_line is not None:
            decimal_side_line = tipanalysis.convert_to_decimal_odds(side_line)
            decimal_draw_line = tipanalysis.convert_to_decimal_odds(draw_line)
            
            if 33 >= (100 - ((100 / decimal_side_line) + (100 / decimal_draw_line))):
                return True
            else:
                return False
        else:
            return None
    elif (
          spread_no == 0 
          and spread_line is not None
    ):
        if -104 > spread_line:
            return True
        elif (
              -104 == spread_line 
              and is_home is not None 
              and is_home is True
        ):
            return True
        elif -104 < spread_line:
            return False
        else:
            return None
    else:
        return None
    
class TipArchive(webapp.RequestHandler):
    # spreadsheet column information row and col indices
    SPREADSHEET_MODIFIED_DATE_CELL = 'B2'
    SPREADSHEET_DATE_COL = 1
    SPREADSHEET_LIMIT_ROW = 3
    
    # list indices for row values
    LEAGUE_INDEX = 2
    SELECTION_INDEX = 3
    TYPE_INDEX = 4
    TIME_INDEX = 6
    ODDS_INDEX = 11
    RESULT_INDEX = 13
    CLOSE_ODDS_INDEX = 19
    LINE_INDEX = 20
    CLOSE_LINE_INDEX = 21
    
    DATE_FORMAT = '%m/%d/%Y' # format for date stored in spreadsheet
    
    def get(self):
        self.DATASTORE_READS = 0
        
        self.response.out.write('Hello<br />')
        
        day_limit = self.request.get('day_limit', default_value='2')
        try:
            day_limit = int(day_limit)
        except ValueError:
            day_limit = 2
        
        self.update_archive(day_limit)
        self.response.out.write('<br />Goodbye')
        
        logging.debug('Total Reads: '+str(self.DATASTORE_READS))
        
    def get_client(self):
        if not hasattr(self, 'gclient'):
            G_EMAIL = '260128773013-vineg4bdug5q27rlbdr3j9s7jlm4sp7l@developer.gserviceaccount.com'
            
            f = file('key-drive-gl-05.pem', 'r')
            OAUTH_KEY = f.read()
            f.close()
            
            OAUTH_SCOPE = 'https://spreadsheets.google.com/feeds'
            
            logging.info('Authorizing Google spreadsheet client...')
            spreadsheet_oauth_credentials = SignedJwtAssertionCredentials(G_EMAIL, OAUTH_KEY, scope=OAUTH_SCOPE)
            self.gclient = gspread.authorize(spreadsheet_oauth_credentials)
        
        return self.gclient
    
    def get_spreadsheet(self):
        if not hasattr(self, 'spreadsheet'):
            if constants.is_local():
                logging.info('Opening Test Tracking spreadsheet...')
                self.spreadsheet = self.get_client().open('Test Tracking')
            else:
                logging.info('Opening Tips Tracking spreadsheet...')
                self.spreadsheet = self.get_client().open('Tips Tracking')
            
        return self.spreadsheet
    
    def get_league_worksheet(self, sport_key, league_key):
        try:
            if isinstance(teamconstants.TEAMS[sport_key][league_key], basestring):
                league_key = teamconstants.TEAMS[sport_key][league_key]
        except KeyError:
            logging.warning('missing '+league_key+' teamconstant')
        
        if not hasattr(self, 'league_worksheets'):
            self.league_worksheets = {}
            
        if league_key in self.league_worksheets:
            worksheet = self.league_worksheets[league_key]
        else:
            try:
                logging.debug('Retrieving worksheet for: '+league_key)
                worksheet = self.get_spreadsheet().worksheet(league_key)
            except gspread.exceptions.WorksheetNotFound:
                logging.info('Creating new worksheet for: '+league_key)
                worksheet = self.get_spreadsheet().add_worksheet(title=league_key, rows='1', cols='22')
                
            self.league_worksheets[league_key] = worksheet
        
        return worksheet
    
    def update_archive(self, day_limit):
        local_timezone = pytz.timezone(constants.TIMEZONE_LOCAL)
        
        info_worksheet = self.get_spreadsheet().worksheet('Information')
        latest_MST_MDY_string = info_worksheet.acell(self.SPREADSHEET_MODIFIED_DATE_CELL).value
        
        if latest_MST_MDY_string == '':
            logging.error('No archive date given!')
            raise Exception('No archive date given!')
                
        dates_to_archive_keys = [x.strip() for x in info_worksheet.cell(self.SPREADSHEET_LIMIT_ROW, self.SPREADSHEET_DATE_COL).value.split(';')]
                
        latest_UTC_date = local_timezone.localize(datetime.strptime(latest_MST_MDY_string+' 23:59.59.999999', '%m/%d/%Y %H:%M.%S.%f')).astimezone(pytz.utc)
        limit_UTC_date = latest_UTC_date + timedelta(days = abs(day_limit))
        
        self.DATASTORE_READS += 1
        all_tips_by_date = models.Tip.gql('WHERE date > :1 AND date <= :2 ORDER BY date ASC',
                                          latest_UTC_date.replace(tzinfo=None),
                                          limit_UTC_date.replace(tzinfo=None)
                                          )
        
        tips_to_archive_by_date = {}
        for tip_instance in all_tips_by_date:
            self.DATASTORE_READS += 1
            if tip_instance.pinnacle_game_no.startswith('OTB '):
                continue
            
            date_MST = tip_instance.date.replace(tzinfo=pytz.utc).astimezone(local_timezone)
            date_MST_MDY_string = date_MST.strftime(self.DATE_FORMAT)
            
            if tip_instance.archived is True:
                # store by sport and league (so that league worksheet can be gotten and thrown away before accessing another)
                if (
                    date_MST_MDY_string in tips_to_archive_by_date 
                    and tip_instance.game_sport in tips_to_archive_by_date[date_MST_MDY_string] 
                    and tip_instance.game_league in tips_to_archive_by_date[date_MST_MDY_string][tip_instance.game_sport]
                ):
                    tips_to_archive_by_date[date_MST_MDY_string][tip_instance.game_sport][tip_instance.game_league].append(tip_instance)
                elif (
                      date_MST_MDY_string in tips_to_archive_by_date 
                      and tip_instance.game_sport in tips_to_archive_by_date[date_MST_MDY_string]
                ):
                    tips_to_archive_by_date[date_MST_MDY_string][tip_instance.game_sport][tip_instance.game_league] = [tip_instance]
                elif date_MST_MDY_string in tips_to_archive_by_date:
                    tips_to_archive_by_date[date_MST_MDY_string][tip_instance.game_sport] = {tip_instance.game_league : [tip_instance]}
                else:
                    tips_to_archive_by_date[date_MST_MDY_string] = {tip_instance.game_sport : {tip_instance.game_league : [tip_instance]}}
            else:
                # day not done, do not archive any tips from this day (nor any day after)
                tips_to_archive_by_date.pop(date_MST_MDY_string, None)
                break
        
        tips_to_archive_date_order = sorted(tips_to_archive_by_date.keys(), key=lambda x: datetime.strptime(x, self.DATE_FORMAT))
        
        latest_date_split = latest_MST_MDY_string.split('/')
        latest_date = date(int(latest_date_split[2]), int(latest_date_split[0]), int(latest_date_split[1]))
        
        new_date = (limit_UTC_date.astimezone(local_timezone)).date()
        
        number_of_updated_cells = 0
        for date_MST_MDY_string in tips_to_archive_date_order:
            date_split = date_MST_MDY_string.split('/')
            new_date = date(int(date_split[2]), int(date_split[0]), int(date_split[1]))
            
            tip_instances_by_sport_league = tips_to_archive_by_date[date_MST_MDY_string]
            for sport_key, tip_instances_by_league in tip_instances_by_sport_league.iteritems():
                self.league_worksheets = {}
                
                for league_key, tip_instances in tip_instances_by_league.iteritems():
                    league_worksheet = self.get_league_worksheet(sport_key, league_key)
                    
                    league_latest_date_split = league_worksheet.cell(league_worksheet.row_count, self.SPREADSHEET_DATE_COL).value.split('/')
                    if len(league_latest_date_split) == 3:
                        if new_date <= date(int(league_latest_date_split[2]), int(league_latest_date_split[0]), int(league_latest_date_split[1])):
                            logging.warning('Failure to complete during previous instance. Skipping redundant '+date_MST_MDY_string+' for '+league_key)
                            continue
                    
                    # get all new rows in value lists (i.e. each new row is a list)
                    new_tip_archive_row_lists = []
                    for tip_instance in tip_instances:
                        new_tip_archive_row_lists = self.get_tip_archive_values(new_tip_archive_row_lists, tip_instance, dates_to_archive_keys)
                    
                    # need to know how many new rows will need to be added    
                    total_tips_to_archive = len(new_tip_archive_row_lists)
                    
                    if total_tips_to_archive < 1:
                        logging.warning(date_MST_MDY_string+' '+league_key+' has empty archived tips.')
                        continue
                    
                    logging.info('Adding ('+str(total_tips_to_archive)+') '+date_MST_MDY_string+' tips to '+league_key+' archive')
                    
                    # get cell lists for worksheets to be updated in batch
                    worksheet_current_row_count = league_worksheet.row_count
                    worksheet_col_max_alpha = string.uppercase[league_worksheet.col_count - 1]
                     
                    worksheet_new_row_start = worksheet_current_row_count + 1
                    worksheet_new_row_end = worksheet_current_row_count + total_tips_to_archive
                     
                    # add new rows and get their cell range
                    league_worksheet.add_rows(total_tips_to_archive)
                    cell_list = league_worksheet.range('A'+str(worksheet_new_row_start)+':'+worksheet_col_max_alpha+str(worksheet_new_row_end))
                     
                    current_cell_index = 0
                    current_cell_row = None
                    # modify cell objects to batch update
                    for new_row_list in new_tip_archive_row_lists:
                        # row value should increase for every new tip list
                        if cell_list[current_cell_index].row == current_cell_row:
                            logging.error('Row number expected to increase, but did not meaning number of cell values inaccurate')
                            raise Exception('Row number expected to increase, but did not meaning number of cell values inaccurate')
                        else:
                            current_cell_row = cell_list[current_cell_index].row
                        
                        for new_cell_value in new_row_list:
                            if new_cell_value is None:
                                new_cell_value = ''
                            elif not isinstance(new_cell_value, (basestring, int, float)):
                                logging.warning('Unsupported type: '+type(new_cell_value))
                                raise Exception('Unsupported type: '+type(new_cell_value))
                            
                            cell_list[current_cell_index].value = new_cell_value
                            current_cell_index += 1
                             
                    number_of_updated_cells += len(cell_list)
                    try:
                        league_worksheet.update_cells(cell_list)
                    except HTTPException as e:
                        logging.warning(str(e))
                        
        if new_date > latest_date:
            new_date_string = new_date.strftime(self.DATE_FORMAT)
            logging.info('Updating archive date to '+new_date_string)
            info_worksheet.update_acell(self.SPREADSHEET_MODIFIED_DATE_CELL, new_date_string)
            number_of_updated_cells += 1
                
        logging.debug('Total number of cells updated: '+str(number_of_updated_cells))
        
    def get_tip_archive_values(self, new_tip_archive_row_lists, tip_instance, dates_to_archive_keys):
        date_MST = tip_instance.date.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(constants.TIMEZONE_LOCAL))
        
        tip_scores = None
        if tip_instance.score_away is not None and tip_instance.score_home is not None:
            tip_scores = tip_instance.score_away+' - '+tip_instance.score_home
                        
        default_row_values = [
                      date_MST.strftime(self.DATE_FORMAT),                  # DATE
                      'Tracker',                                            # Bookmaker
                      tip_instance.game_league,                             # Sport / League
                      None,                                                 # Selection
                      None,                                                 # Bet Type
                      tip_instance.wettpoint_tip_stake,                     # Tipper
                      None,                                                 # Time of Line
                      date_MST.strftime('%H:%M')+' '+tip_instance.game_team_away+' @ '+tip_instance.game_team_home, # Fixture / Event
                      'N',                                                  # Live Bet
                      tip_scores,                                           # Score / Result
                      1,                                                    # Stake
                      None,                                                 # Odds (US)
                      'N',                                                  # FB
                      None,                                                 # Win
                      None,                                                 # Commission
                      None,                                                 # Lay Bet?
                      None,                                                 # Tipper's Odds
                      None,                                                 # Tipper's Line
                      None,                                                 # Tipper's Win
                      None,                                                 # Closing Odds
                      None,                                                 # Wager Line
                      None                                                  # Closing Line
                      ]
        
        nine_pm_UTC = (date_MST - timedelta(days = 1)).replace(hour=21, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
        eight_am_UTC = date_MST.replace(hour=8, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
        eleven_am_UTC = date_MST.replace(hour=11, minute=30, second=0, microsecond=0).astimezone(pytz.utc)
        
        # see BET_TIME class constants
        dates_to_archive = {
                            BET_TIME_NIGHT : nine_pm_UTC,
                            BET_TIME_MORNING : eight_am_UTC,
                            BET_TIME_NOON : eleven_am_UTC,
                            BET_TIME_LATEST : 'latest',
                            }
        
        dates_to_remove = []
        for date_to_archive in dates_to_archive:
            if date_to_archive not in dates_to_archive_keys:
                dates_to_remove.append(date_to_archive)
                
        for date_to_remove in dates_to_remove:
            dates_to_archive.pop(date_to_remove, None)
        
        # Team/Side & Spread bets
        new_tip_archive_row_lists += self.get_new_archive_team_value_lists(default_row_values, dates_to_archive, tip_instance.wettpoint_tip_team, tip_instance.team_lines, tip_instance.spread_no, tip_instance.spread_lines, tip_instance.score_away, tip_instance.score_home)
        # Total bets
        new_tip_archive_row_lists += self.get_new_archive_total_value_lists(default_row_values, dates_to_archive, tip_instance.wettpoint_tip_total, tip_instance.total_no, tip_instance.total_lines, tip_instance.score_away, tip_instance.score_home)
        
        return new_tip_archive_row_lists
        
    def get_new_archive_team_value_lists(self, default_row_values, dates_to_archive, team_selection, team_lines, spread_no, spread_lines, score_away, score_home):
        archive_tip_team_lists = []
        
        if team_selection is None:
            return archive_tip_team_lists
        
        event_with_draw = True
        if default_row_values[self.LEAGUE_INDEX] in constants.LEAGUES_OT_INCLUDED:
            event_with_draw = False
        
        # get closing line for comparison data
        closing_line = tipanalysis.get_line(team_lines)[0]
        closing_spread_no = tipanalysis.get_line(spread_no)[0]
        closing_spread_line = tipanalysis.get_line(spread_lines)[0]
        for date_label, date_to_archive in dates_to_archive.iteritems():
            new_row_values = default_row_values
            
            archive_team_line = tipanalysis.get_line(team_lines, date=date_to_archive)[0]
            archive_spread_no = tipanalysis.get_line(spread_no, date=date_to_archive)[0]
            archive_spread_line = tipanalysis.get_line(spread_lines, date=date_to_archive)[0]
            
            bet_types = {}
            
            # 1X2 event
            if archive_team_line is None or models.TIP_SELECTION_LINE_SEPARATOR in archive_team_line:
                if archive_team_line is None:
                    archive_split_lines = [None, None]
                    closing_split_line = [None, None]
                else:
                    archive_split_lines = archive_team_line.split(models.TIP_SELECTION_LINE_SEPARATOR)
                    closing_split_line = closing_line.split(models.TIP_SELECTION_LINE_SEPARATOR)
                
                # draw result included
                if models.TIP_SELECTION_TEAM_DRAW in team_selection:
                    if models.TIP_SELECTION_TEAM_AWAY in team_selection:
                        bet_types[BET_TYPE_SIDE_DRAW] = [archive_split_lines[0], closing_split_line[0]]
                        
                        if is_side_team_favourite(home=False,side=archive_split_lines[1],draw=archive_split_lines[0],spread_no=archive_spread_no,spread=archive_spread_line):
                            bet_types[BET_TYPE_SIDE_DRAW_AWAY_FAVOURITE] = [archive_split_lines[1], closing_split_line[1]]
                            bet_types[BET_TYPE_SPREAD_DRAW_AWAY_FAVOURITE] = [archive_spread_line, archive_spread_no]
                        else:
                            bet_types[BET_TYPE_SIDE_DRAW_AWAY_UNDERDOG] = [archive_split_lines[1], closing_split_line[1]]
                            bet_types[BET_TYPE_SPREAD_DRAW_AWAY_UNDERDOG] = [archive_spread_line, archive_spread_no]
                    elif models.TIP_SELECTION_TEAM_HOME in team_selection:
                        bet_types[BET_TYPE_SIDE_DRAW] = [archive_split_lines[1], closing_split_line[1]]
                        
                        if is_side_team_favourite(home=True,side=archive_split_lines[0],draw=archive_split_lines[1],spread_no=archive_spread_no,spread=archive_spread_line):
                            bet_types[BET_TYPE_SIDE_DRAW_HOME_FAVOURITE] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[BET_TYPE_SPREAD_DRAW_HOME_FAVOURITE] = [archive_spread_line, archive_spread_no]
                        else:
                            bet_types[BET_TYPE_SIDE_DRAW_HOME_UNDERDOG] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[BET_TYPE_SPREAD_DRAW_HOME_UNDERDOG] = [archive_spread_line, archive_spread_no]
                    else:
                        logging.error('Encountered unsupported side draw team selection')
                        raise Exception('Encountered unsupported side draw team selection')
                # no draw result
                else:
                    if team_selection == models.TIP_SELECTION_TEAM_AWAY:
                        if is_side_team_favourite(home=False,side=archive_split_lines[0],spread_no=archive_spread_no,spread=archive_spread_line):
                            bet_types[BET_TYPE_AWAY_FAVOURITE] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[BET_TYPE_SPREAD_AWAY_FAVOURITE] = [archive_spread_line, archive_spread_no]
                        else:
                            bet_types[BET_TYPE_AWAY_UNDERDOG] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[BET_TYPE_SPREAD_AWAY_UNDERDOG] = [archive_spread_line, archive_spread_no]
                    elif team_selection == models.TIP_SELECTION_TEAM_HOME:
                        if is_side_team_favourite(home=True,side=archive_split_lines[0],spread_no=archive_spread_no,spread=archive_spread_line):
                            bet_types[BET_TYPE_HOME_FAVOURITE] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[BET_TYPE_SPREAD_HOME_FAVOURITE] = [archive_spread_line, archive_spread_no]
                        else:
                            bet_types[BET_TYPE_HOME_UNDERDOG] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[BET_TYPE_SPREAD_HOME_UNDERDOG] = [archive_spread_line, archive_spread_no]
                    elif team_selection == (models.TIP_SELECTION_TEAM_HOME + models.TIP_SELECTION_TEAM_AWAY):
                        if float(archive_split_lines[0]) <= float(archive_split_lines[1]):
                            bet_types[BET_TYPE_SIDE_NO_DRAW_HOME_FAVOURITE] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[BET_TYPE_SIDE_NO_DRAW_AWAY_UNDERDOG] = [archive_split_lines[1], closing_split_line[1]]
                            bet_types[BET_TYPE_SPREAD_NO_DRAW_HOME_FAVOURITE] = [archive_spread_line, archive_spread_no]
                        else:
                            bet_types[BET_TYPE_SIDE_NO_DRAW_HOME_UNDERDOG] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[BET_TYPE_SIDE_NO_DRAW_AWAY_FAVOURITE] = [archive_split_lines[1], closing_split_line[1]]
                            bet_types[BET_TYPE_SPREAD_NO_DRAW_HOME_UNDERDOG] = [archive_spread_line, archive_spread_no]
                    else:
                        logging.error('Encountered unsupported side only team selection')
                        raise Exception('Encountered unsupported side only team selection')
            # ML event
            else:
                if team_selection == models.TIP_SELECTION_TEAM_AWAY:
                    if is_side_team_favourite(home=False,side=archive_team_line,spread_no=archive_spread_no,spread=archive_spread_line):
                        bet_types[BET_TYPE_AWAY_FAVOURITE] = [archive_team_line, closing_line]
                        bet_types[BET_TYPE_SPREAD_AWAY_FAVOURITE] = [archive_spread_line, archive_spread_no]
                    else:
                        bet_types[BET_TYPE_AWAY_UNDERDOG] = [archive_team_line, closing_line]
                        bet_types[BET_TYPE_SPREAD_AWAY_UNDERDOG] = [archive_spread_line, archive_spread_no]
                elif team_selection == models.TIP_SELECTION_TEAM_HOME:
                    if is_side_team_favourite(home=True,side=archive_team_line,spread_no=archive_spread_no,spread=archive_spread_line):
                        bet_types[BET_TYPE_HOME_FAVOURITE] = [archive_team_line, closing_line]
                        bet_types[BET_TYPE_SPREAD_HOME_FAVOURITE] = [archive_spread_line, archive_spread_no]
                    else:
                        bet_types[BET_TYPE_HOME_UNDERDOG] = [archive_team_line, closing_line]
                        bet_types[BET_TYPE_SPREAD_HOME_UNDERDOG] = [archive_spread_line, archive_spread_no]
                else:
                    logging.error('Encountered unsupported single team selection')
                    raise Exception('Encountered unsupported single team selection')
            
            # update row specific values
            new_row_values[self.SELECTION_INDEX] = team_selection
            new_row_values[self.TIME_INDEX] = date_label
                
            for bet_type, bet_odds in bet_types.iteritems():
                if bet_odds[0] is None or bet_odds[1] is None:
                    continue
                
                new_row_values[self.TYPE_INDEX] = bet_type
                
                spread_mod = None
                if (
                    bet_type in [
                                BET_TYPE_SPREAD_AWAY_FAVOURITE,
                                BET_TYPE_SPREAD_AWAY_UNDERDOG,
                                BET_TYPE_SPREAD_DRAW_AWAY_FAVOURITE,
                                BET_TYPE_SPREAD_DRAW_AWAY_UNDERDOG,
                                BET_TYPE_SPREAD_HOME_FAVOURITE,
                                BET_TYPE_SPREAD_HOME_UNDERDOG,
                                BET_TYPE_SPREAD_DRAW_HOME_FAVOURITE,
                                BET_TYPE_SPREAD_DRAW_HOME_UNDERDOG,
                                BET_TYPE_SPREAD_NO_DRAW_HOME_FAVOURITE,
                                BET_TYPE_SPREAD_NO_DRAW_HOME_UNDERDOG,
                                ]
                ):
                    spread_mod = bet_odds[1]
                
                if (
                    bet_type in [
                                BET_TYPE_AWAY_FAVOURITE, 
                                BET_TYPE_AWAY_UNDERDOG, 
                                BET_TYPE_SIDE_DRAW_AWAY_FAVOURITE, 
                                BET_TYPE_SIDE_DRAW_AWAY_UNDERDOG,
                                BET_TYPE_SIDE_NO_DRAW_AWAY_FAVOURITE,
                                BET_TYPE_SIDE_NO_DRAW_AWAY_UNDERDOG,
                                BET_TYPE_SPREAD_AWAY_FAVOURITE,
                                BET_TYPE_SPREAD_AWAY_UNDERDOG,
                                BET_TYPE_SPREAD_DRAW_AWAY_FAVOURITE,
                                BET_TYPE_SPREAD_DRAW_AWAY_UNDERDOG,
                                ]
                ):
                    bet_result = tipanalysis.calculate_event_score_result(score_away, score_home, regulation_only=event_with_draw, draw_lose=event_with_draw, spread_modifier=spread_mod)
                elif (
                    bet_type in [
                                BET_TYPE_HOME_FAVOURITE, 
                                BET_TYPE_HOME_UNDERDOG, 
                                BET_TYPE_SIDE_DRAW_HOME_FAVOURITE, 
                                BET_TYPE_SIDE_DRAW_HOME_UNDERDOG,
                                BET_TYPE_SIDE_NO_DRAW_HOME_FAVOURITE,
                                BET_TYPE_SIDE_NO_DRAW_HOME_UNDERDOG,
                                BET_TYPE_SPREAD_HOME_FAVOURITE,
                                BET_TYPE_SPREAD_HOME_UNDERDOG,
                                BET_TYPE_SPREAD_DRAW_HOME_FAVOURITE,
                                BET_TYPE_SPREAD_DRAW_HOME_UNDERDOG,
                                BET_TYPE_SPREAD_NO_DRAW_HOME_FAVOURITE,
                                BET_TYPE_SPREAD_NO_DRAW_HOME_UNDERDOG,
                                ]
                ):
                    bet_result = tipanalysis.calculate_event_score_result(score_home, score_away, regulation_only=event_with_draw, draw_lose=event_with_draw, spread_modifier=spread_mod)
                elif (
                      bet_type in [
                                BET_TYPE_SIDE_DRAW,
                                ]
                ):
                    bet_result = tipanalysis.calculate_event_score_result(score_home, score_away, regulation_only=event_with_draw, draw_result=True)
                    
                new_row_values[self.RESULT_INDEX] = bet_result
                
                if spread_mod is not None:
                    new_row_values[self.ODDS_INDEX] = bet_odds[0]
                    new_row_values[self.CLOSE_ODDS_INDEX] = closing_spread_line
                    new_row_values[self.LINE_INDEX] = spread_mod
                    new_row_values[self.CLOSE_LINE_INDEX] = closing_spread_no
                else:
                    new_row_values[self.ODDS_INDEX] = bet_odds[0]
                    new_row_values[self.CLOSE_ODDS_INDEX] = bet_odds[1]
                    new_row_values[self.LINE_INDEX] = None
                    new_row_values[self.CLOSE_LINE_INDEX] = None
                
                archive_tip_team_lists.append(new_row_values[:])
                
        return archive_tip_team_lists
    
    def get_new_archive_total_value_lists(self, default_row_values, dates_to_archive, total_selection, total_no, total_lines, score_away, score_home):
        archive_tip_total_lists = []
        
        if score_away is None or score_home is None:
            total_score = None
        else:
            if default_row_values[self.LEAGUE_INDEX] in constants.LEAGUES_OT_INCLUDED:
                total_score = float(score_away.split('(', 1)[0]) + float(score_home.split('(', 1)[0])
            else:
                score_away = score_away.split('(', 1)
                if len(score_away) > 1:
                    total_score = float(score_away[1].rstrip(')')) + float(score_home.split('(', 1)[1].rstrip(')'))
                else:
                    total_score = float(score_away[0]) + float(score_home)
        
        closing_total_no = tipanalysis.get_line(total_no)[0]
        closing_total_line = tipanalysis.get_line(total_lines)[0]
        for date_label, date_to_archive in dates_to_archive.iteritems():
            new_row_values = default_row_values
            
            archive_total_no = tipanalysis.get_line(total_no, date=date_to_archive)[0]
            archive_total_line = tipanalysis.get_line(total_lines, date=date_to_archive)[0]
            
            if archive_total_no is None or archive_total_line is None:
                continue
            
            new_row_values[self.SELECTION_INDEX] = total_selection
            
            if total_selection == models.TIP_SELECTION_TOTAL_OVER:
                bet_type = BET_TYPE_TOTAL_OVER
                bet_result = tipanalysis.calculate_event_score_result(total_score, archive_total_no)
            elif total_selection == models.TIP_SELECTION_TOTAL_UNDER:
                bet_type = BET_TYPE_TOTAL_UNDER
                bet_result = tipanalysis.calculate_event_score_result(archive_total_no, total_score)
            else:
                bet_type = BET_TYPE_TOTAL_NONE
                bet_result = tipanalysis.calculate_event_score_result(archive_total_no, total_score)
            
            new_row_values[self.TYPE_INDEX] = bet_type
            
            new_row_values[self.TIME_INDEX] = date_label
            new_row_values[self.RESULT_INDEX] = bet_result
            
            new_row_values[self.ODDS_INDEX] = archive_total_line
            new_row_values[self.CLOSE_ODDS_INDEX] = closing_total_line
            new_row_values[self.LINE_INDEX] = archive_total_no
            new_row_values[self.CLOSE_LINE_INDEX] = closing_total_no
                
            archive_tip_total_lists.append(new_row_values[:])
                
        return archive_tip_total_lists