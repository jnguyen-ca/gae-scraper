#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('libs/oauth2client-1.3')
sys.path.append('libs/gspread-0.2.2')
sys.path.append('libs/pytz-2014.7')
sys.path.append('utils')

from google.appengine.ext import webapp
from google.appengine.api import urlfetch, taskqueue
from oauth2client.client import SignedJwtAssertionCredentials

from httplib import HTTPException
from datetime import date, datetime, timedelta
from utils import memcache_util, sys_util

import string
import logging
import pytz
import gspread
import constants
import models
import teamconstants
import tipanalysis

# spreadsheet column information row and col indices
SPREADSHEET_DATE_COL = 1
SPREADSHEET_LEAGUE_COL = 3
SPREADSHEET_SELECTION_COL = 4
SPREADSHEET_TYPE_COL = 5
SPREADSHEET_FILTERA_COL = 6
SPREADSHEET_FILTERB_COL = 7
SPREADSHEET_ODDS_COL = 12
SPREADSHEET_RESULT_COL = 14
SPREADSHEET_CLOSE_ODDS_COL = 20
SPREADSHEET_LINE_COL = 21
SPREADSHEET_CLOSE_LINE_COL = 22

SPREADSHEET_MODIFIED_DATE_CELL = 'B2'
SPREADSHEET_LIMIT_ROW = 3
# list indices for row values

SPREADSHEET_DATE_FORMAT = '%m/%d/%Y' # format for date stored in spreadsheet

def get_client():
    gclient = memcache_util.get(memcache_util.MEMCACHE_KEY_TIPARCHIVE_CLIENT)
    if gclient is None:
        G_EMAIL = '260128773013-vineg4bdug5q27rlbdr3j9s7jlm4sp7l@developer.gserviceaccount.com'
        
        f = file('key-drive-gl-05.pem', 'r')
        OAUTH_KEY = f.read()
        f.close()
        
        OAUTH_SCOPE = 'https://spreadsheets.google.com/feeds'
        
        logging.info('Authorizing Google spreadsheet client...')
        spreadsheet_oauth_credentials = SignedJwtAssertionCredentials(G_EMAIL, OAUTH_KEY, scope=OAUTH_SCOPE)
        
        gclient = gspread.authorize(spreadsheet_oauth_credentials)
        memcache_util.set(memcache_util.MEMCACHE_KEY_TIPARCHIVE_CLIENT, gclient)
    else:
        logging.debug('Using Google client from memcache...')
    
    return gclient

def get_spreadsheet():
    spreadsheet = memcache_util.get(memcache_util.MEMCACHE_KEY_TIPARCHIVE_SPREADSHEET)
    if spreadsheet is None:
        if sys_util.is_local():
            logging.info('Opening Test Tracking spreadsheet...')
            spreadsheet = get_client().open('Test Tracking')
        else:
            logging.info('Opening Tips Tracking spreadsheet...')
            spreadsheet = get_client().open('Tips Tracking')
        
        memcache_util.set(memcache_util.MEMCACHE_KEY_TIPARCHIVE_SPREADSHEET, spreadsheet)
        
    return spreadsheet

def get_league_worksheet(sport_key, league_key, obj=None, valid_leagues=None, get_or_create=True):
    league_key = teamconstants.get_base_league_key(sport_key, league_key)
    
    if (
        valid_leagues is not None 
        and league_key not in valid_leagues
    ):
        return None
    
    if obj is not None and not hasattr(obj, 'league_worksheets'):
        obj.league_worksheets = {}
        
    if obj is not None and league_key in obj.league_worksheets:
        worksheet = obj.league_worksheets[league_key]
    else:
        try:
            logging.debug('Retrieving worksheet for: '+league_key)
            worksheet = get_spreadsheet().worksheet(league_key)
        except gspread.exceptions.WorksheetNotFound:
            if get_or_create is True:
                logging.info('Creating new worksheet for: '+league_key)
                worksheet = get_spreadsheet().add_worksheet(title=league_key, rows='1', cols='22')
            else:
                logging.info(league_key+' worksheet does not exist!')
                return None
            
        if obj is not None:
            obj.league_worksheets[league_key] = worksheet
    
    return worksheet

def is_side_team_favourite(**kwargs):
    """To determine whether team A is the favourite or not
    
    Kwargs:
        side (numeric): The team line for team A
        draw (numeric): The draw line in 1X2 tip
        spread_no (numeric): Spread value for team A
        spread (numeric): The spread line for team A
        home (bool): Whether or not team A is the home team
    
    Returns:
        bool: True if favourite, False otherwise
        None: Not enough information
    """
    side_line = draw_line = spread_no = spread_line = is_home = None
    
    # normalize all optional parameters
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
    
    # spread (when it's not 0) is the easiest to determine favourite
    if (
        spread_no is not None 
        and spread_no != 0
    ):
        if 0 > spread_no:
            return True
        elif 0 < spread_no:
            return False
    # otherwise try the team lines
    elif side_line is not None:
        # assuming -104 lines
        # simple favourite
        if -104 > side_line:
            return True
        # pick'em (choose home) OR favourite in a 1X2
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
        # if not a 1X2 then anything above -104 is underdog
        elif (
              -104 < side_line 
              and draw_line is None
        ):
            return False
        # 1X2 complicates things a little
        elif draw_line is not None:
            decimal_side_line = tipanalysis.convert_to_decimal_odds(side_line)
            decimal_draw_line = tipanalysis.convert_to_decimal_odds(draw_line)
            
            # 100 / 3 = 33.33.., therefore estimate that if line and draw equals greater than 66.66.. then favourite
            if 33 >= (100 - ((100 / decimal_side_line) + (100 / decimal_draw_line))):
                return True
            else:
                return False
        else:
            return None
    # spread 0 lines is the last resort
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
    # list indices for row values
    LEAGUE_INDEX = SPREADSHEET_LEAGUE_COL-1
    SELECTION_INDEX = SPREADSHEET_SELECTION_COL-1
    TYPE_INDEX = SPREADSHEET_TYPE_COL-1
    TIME_INDEX = SPREADSHEET_FILTERB_COL-1
    ODDS_INDEX = SPREADSHEET_ODDS_COL-1
    RESULT_INDEX = SPREADSHEET_RESULT_COL-1
    CLOSE_ODDS_INDEX = SPREADSHEET_CLOSE_ODDS_COL-1
    LINE_INDEX = SPREADSHEET_LINE_COL-1
    CLOSE_LINE_INDEX = SPREADSHEET_CLOSE_LINE_COL-1
    
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
    BET_TIME_AFTERNOON = '2PM Same Day'
    BET_TIME_LATEST = 'Latest'
    
    def get(self):
        self.response.out.write('Hello<br />')
        taskqueue.add(queue_name='archive', url='/archive', params={'day_limit' : self.request.get('day_limit')})
        self.response.out.write('<br />Goodbye')
    
    def post(self):
        self.DATASTORE_READS = 0
        
        urlfetch.set_default_fetch_deadline(30)
        
        day_limit = self.request.get('day_limit')
        
        self.update_archive(day_limit)
        
        logging.debug('Total Reads: '+str(self.DATASTORE_READS))
        
    def update_archive(self, day_limit):
        local_timezone = pytz.timezone(constants.TIMEZONE_LOCAL)
        
        # Information worksheet contains basic information such as date and valid values for certain columns
        info_worksheet = get_spreadsheet().worksheet('Information')
        
        # get last date archive was updated to
        latest_MST_MDY_string = info_worksheet.acell(SPREADSHEET_MODIFIED_DATE_CELL).value
        if latest_MST_MDY_string == '':
            logging.error('No archive date given!')
            raise Exception('No archive date given!')
                
        # archive entries can be filtered by time, get the valid times to archive
        dates_to_archive_keys = [x.strip() for x in info_worksheet.cell(SPREADSHEET_LIMIT_ROW, SPREADSHEET_DATE_COL).value.split(';')]
        
        # archive entries can be filtered by league, get the valid leagues to archive
        leagues_to_archive_cell_value = info_worksheet.cell(SPREADSHEET_LIMIT_ROW, SPREADSHEET_LEAGUE_COL).value
        if leagues_to_archive_cell_value == '':
            leagues_to_archive_keys = None
        else:
            leagues_to_archive_keys = [x.strip() for x in leagues_to_archive_cell_value.split(';')]
        
        # first day to archive should be day immediately after last archive date
        latest_UTC_date = local_timezone.localize(datetime.strptime(latest_MST_MDY_string+' 23:59.59.999999', '%m/%d/%Y %H:%M.%S.%f')).astimezone(pytz.utc)
        
        try:
            day_limit = int(day_limit)
            additional_task_required = False
        except (TypeError, ValueError):
            # day_limit parameter not given, default to 7 days
            day_limit = 7
            additional_task_required = None
            
        limit_UTC_date = latest_UTC_date + timedelta(days = abs(day_limit))
        
        # if no day_limit parameter given then we want to update archive to latest possible date
        # will need to queue up another task if current run will not update archive to current date
        if (
            additional_task_required is None 
            and limit_UTC_date.date() < (datetime.utcnow() - timedelta(days = 1)).date()
        ):
            additional_task_required = True
        else:
            additional_task_required = False
            
        self.DATASTORE_READS += 1
        all_tips_by_date = models.Tip.gql('WHERE date > :1 AND date <= :2 ORDER BY date ASC',
                                          latest_UTC_date.replace(tzinfo=None),
                                          limit_UTC_date.replace(tzinfo=None)
                                          )
        
        # run through all tips between the valid dates to get days' tips that are ready to be archived
        tips_to_archive_by_date = {}
        for tip_instance in all_tips_by_date:
            self.DATASTORE_READS += 1
            # skip off the board games since they will have a duplicate tip without the OTB pre-string
            if teamconstants.is_game_off_the_board(tip_instance):
                continue
            
            # store tips in a list with date string keys so that a invalid date can be thrown away easily
            date_MST = tip_instance.date.replace(tzinfo=pytz.utc).astimezone(local_timezone)
            date_MST_MDY_string = date_MST.strftime(SPREADSHEET_DATE_FORMAT)
            
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
        
        # sort the list keys so that archive is ordered
        tips_to_archive_date_order = sorted(tips_to_archive_by_date.keys(), key=lambda x: datetime.strptime(x, SPREADSHEET_DATE_FORMAT))
        
        latest_date_split = latest_MST_MDY_string.split('/')
        latest_date = date(int(latest_date_split[2]), int(latest_date_split[0]), int(latest_date_split[1]))
        
        # initially set the potential new archive date as the limit date so that if there were no valid tips between the dates
        # then we can skip it next time (instead of getting stuck)
        # will be overridden if there are valid tips
        new_date = (limit_UTC_date.astimezone(local_timezone)).date()
        
        # if a date has already been updated (or has no valid tips), we'll want to make sure to update archive date
        skipped_update = False
        
        number_of_updated_cells = 0
        for date_MST_MDY_string in tips_to_archive_date_order:
            date_split = date_MST_MDY_string.split('/')
            new_date = date(int(date_split[2]), int(date_split[0]), int(date_split[1]))
            
            tip_instances_by_sport_league = tips_to_archive_by_date[date_MST_MDY_string]
            for sport_key, tip_instances_by_league in tip_instances_by_sport_league.iteritems():
                self.league_worksheets = {}
                
                for league_key, tip_instances in tip_instances_by_league.iteritems():
                    #TODO: update by league first rather than by date to increase size of cell batch update
                    league_worksheet = get_league_worksheet(sport_key, league_key, obj=self, valid_leagues=leagues_to_archive_keys)
                    # if a league is not valid then we skip, still want to update the archive date though
                    if league_worksheet is None:
                        skipped_update = True
#                         logging.info('Skipping '+date_MST_MDY_string+' '+league_key+' tips due to invalid league')
                        continue
                    
                    # ensure last league archived tip date is less than new archive tip date
                    # if not, then there was a failure in previous run(s) and this league should skip this date
                    league_latest_date_split = league_worksheet.cell(league_worksheet.row_count, SPREADSHEET_DATE_COL).value.split('/')
                    if len(league_latest_date_split) == 3:
                        if new_date <= date(int(league_latest_date_split[2]), int(league_latest_date_split[0]), int(league_latest_date_split[1])):
                            skipped_update = True
                            logging.warning('Failure to complete during previous instance. Skipping redundant '+date_MST_MDY_string+' for '+league_key)
                            continue
                    
                    # get all new rows in value lists (i.e. each new row is a list)
                    new_tip_archive_row_lists = []
                    for tip_instance in tip_instances:
                        # 1 tip to n archive entries
                        self.get_tip_archive_values(new_tip_archive_row_lists, tip_instance, dates_to_archive_keys)
                    
                    # need to know how many new rows will need to be added    
                    total_tips_to_archive = len(new_tip_archive_row_lists)
                    
                    # tip lines were not filled out
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
                        
                        # have to update the cell values individually
                        for new_cell_value in new_row_list:
                            if new_cell_value is None:
                                new_cell_value = ''
                            elif not isinstance(new_cell_value, (basestring, int, float)):
                                logging.warning('Unsupported type: '+type(new_cell_value))
                                raise Exception('Unsupported type: '+type(new_cell_value))
                            
                            cell_list[current_cell_index].value = new_cell_value
                            current_cell_index += 1
                             
                    # once cell list is updated, send the updates to the worksheet in single call
                    number_of_updated_cells += len(cell_list)
                    try:
                        league_worksheet.update_cells(cell_list)
                    except HTTPException as e:
                        # DeadlineExceeded but it still seems to update fine
                        logging.warning(str(e))
                        
        # update archive date last to ensure all tips have been properly archived
        # if there was an error, then archive date won't be updated and it'll catch any unarchived tips on next run
        # also update archive date if there were no tips (valid or not) between the dates to actually archive (to avoid loop)
        # however don't update archive date if there were invalid tips (i.e. tips that haven't finished)
        if (
            (
             0 < number_of_updated_cells 
             and new_date > latest_date
            ) 
            or (
                0 == number_of_updated_cells 
                and (
                     skipped_update is True 
                     or 0 == all_tips_by_date.count(limit=1)
                )
            )
        ):
            new_date_string = new_date.strftime(SPREADSHEET_DATE_FORMAT)
            logging.info('Updating archive date to '+new_date_string)
            info_worksheet.update_acell(SPREADSHEET_MODIFIED_DATE_CELL, new_date_string)
            number_of_updated_cells += 1
            
            # only queue up another task if the archive date was updated (possible loop otherwise if a day doesn't have an event to archive)
            if additional_task_required is True:
                logging.info('Queuing additional task to archive queue to update archive to current date.')
                taskqueue.add(queue_name='archive', url='/archive')
                
        logging.debug('Total number of cells updated: '+str(number_of_updated_cells))
        
    def get_tip_archive_values(self, new_tip_archive_row_lists, tip_instance, dates_to_archive_keys):
        date_MST = tip_instance.date.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(constants.TIMEZONE_LOCAL))
        
        # will also archive PPD or suspended games
        tip_scores = None
        if tip_instance.score_away is not None and tip_instance.score_home is not None:
            tip_scores = tip_instance.score_away+' - '+tip_instance.score_home
                        
        # certain values don't change per tip
        default_row_values = [
                      date_MST.strftime(SPREADSHEET_DATE_FORMAT),      # DATE
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
        
        # archive time filter
        nine_pm_UTC = (date_MST - timedelta(days = 1)).replace(hour=21, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
        eight_am_UTC = date_MST.replace(hour=8, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
        eleven_am_UTC = date_MST.replace(hour=11, minute=30, second=0, microsecond=0).astimezone(pytz.utc)
        two_pm_UTC = date_MST.replace(hour=14, minute=00, second=0, microsecond=0).astimezone(pytz.utc)
        
        # see BET_TIME class constants
        dates_to_archive = {
                            self.BET_TIME_NIGHT : nine_pm_UTC,
                            self.BET_TIME_MORNING : eight_am_UTC,
                            self.BET_TIME_NOON : eleven_am_UTC,
                            self.BET_TIME_AFTERNOON : two_pm_UTC,
                            self.BET_TIME_LATEST : 'latest',
                            }
        
        # remove invalid archive time filters
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
        
    def get_new_archive_team_value_lists(self, default_row_values, dates_to_archive, team_selection, team_lines, spread_no, spread_lines, score_away, score_home):
        archive_tip_team_lists = []
        
        if team_selection is None:
            return archive_tip_team_lists
        
        original_league_value = default_row_values[self.LEAGUE_INDEX]
        
        # get closing line for comparison data
        closing_line = tipanalysis.get_line(team_lines)[0]
        closing_spread_no = tipanalysis.get_line(spread_no)[0]
        closing_spread_line = tipanalysis.get_line(spread_lines)[0]
        
        new_row_values = default_row_values[:]
        for date_label, date_to_archive in dates_to_archive.iteritems():
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
                        bet_types[self.BET_TYPE_SIDE_DRAW] = [archive_split_lines[0], closing_split_line[0]]
                        
                        if is_side_team_favourite(home=False,side=archive_split_lines[1],draw=archive_split_lines[0],spread_no=archive_spread_no,spread=archive_spread_line):
                            bet_types[self.BET_TYPE_SIDE_DRAW_AWAY_FAVOURITE] = [archive_split_lines[1], closing_split_line[1]]
                            bet_types[self.BET_TYPE_SPREAD_DRAW_AWAY_FAVOURITE] = [archive_spread_line, archive_spread_no]
                        else:
                            bet_types[self.BET_TYPE_SIDE_DRAW_AWAY_UNDERDOG] = [archive_split_lines[1], closing_split_line[1]]
                            bet_types[self.BET_TYPE_SPREAD_DRAW_AWAY_UNDERDOG] = [archive_spread_line, archive_spread_no]
                    elif models.TIP_SELECTION_TEAM_HOME in team_selection:
                        bet_types[self.BET_TYPE_SIDE_DRAW] = [archive_split_lines[1], closing_split_line[1]]
                        
                        if is_side_team_favourite(home=True,side=archive_split_lines[0],draw=archive_split_lines[1],spread_no=archive_spread_no,spread=archive_spread_line):
                            bet_types[self.BET_TYPE_SIDE_DRAW_HOME_FAVOURITE] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[self.BET_TYPE_SPREAD_DRAW_HOME_FAVOURITE] = [archive_spread_line, archive_spread_no]
                        else:
                            bet_types[self.BET_TYPE_SIDE_DRAW_HOME_UNDERDOG] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[self.BET_TYPE_SPREAD_DRAW_HOME_UNDERDOG] = [archive_spread_line, archive_spread_no]
                    else:
                        logging.error('Encountered unsupported side draw team selection')
                        raise Exception('Encountered unsupported side draw team selection')
                # no draw result
                else:
                    if team_selection == models.TIP_SELECTION_TEAM_AWAY:
                        if is_side_team_favourite(home=False,side=archive_split_lines[0],spread_no=archive_spread_no,spread=archive_spread_line):
                            bet_types[self.BET_TYPE_AWAY_FAVOURITE] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[self.BET_TYPE_SPREAD_AWAY_FAVOURITE] = [archive_spread_line, archive_spread_no]
                        else:
                            bet_types[self.BET_TYPE_AWAY_UNDERDOG] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[self.BET_TYPE_SPREAD_AWAY_UNDERDOG] = [archive_spread_line, archive_spread_no]
                    elif team_selection == models.TIP_SELECTION_TEAM_HOME:
                        if is_side_team_favourite(home=True,side=archive_split_lines[0],spread_no=archive_spread_no,spread=archive_spread_line):
                            bet_types[self.BET_TYPE_HOME_FAVOURITE] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[self.BET_TYPE_SPREAD_HOME_FAVOURITE] = [archive_spread_line, archive_spread_no]
                        else:
                            bet_types[self.BET_TYPE_HOME_UNDERDOG] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[self.BET_TYPE_SPREAD_HOME_UNDERDOG] = [archive_spread_line, archive_spread_no]
                    elif team_selection == (models.TIP_SELECTION_TEAM_HOME + models.TIP_SELECTION_TEAM_AWAY):
                        if float(archive_split_lines[0]) <= float(archive_split_lines[1]):
                            bet_types[self.BET_TYPE_SIDE_NO_DRAW_HOME_FAVOURITE] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[self.BET_TYPE_SIDE_NO_DRAW_AWAY_UNDERDOG] = [archive_split_lines[1], closing_split_line[1]]
                            bet_types[self.BET_TYPE_SPREAD_NO_DRAW_HOME_FAVOURITE] = [archive_spread_line, archive_spread_no]
                        else:
                            bet_types[self.BET_TYPE_SIDE_NO_DRAW_HOME_UNDERDOG] = [archive_split_lines[0], closing_split_line[0]]
                            bet_types[self.BET_TYPE_SIDE_NO_DRAW_AWAY_FAVOURITE] = [archive_split_lines[1], closing_split_line[1]]
                            bet_types[self.BET_TYPE_SPREAD_NO_DRAW_HOME_UNDERDOG] = [archive_spread_line, archive_spread_no]
                    else:
                        logging.error('Encountered unsupported side only team selection')
                        raise Exception('Encountered unsupported side only team selection')
            # ML event
            else:
                if team_selection == models.TIP_SELECTION_TEAM_AWAY:
                    if is_side_team_favourite(home=False,side=archive_team_line,spread_no=archive_spread_no,spread=archive_spread_line):
                        bet_types[self.BET_TYPE_AWAY_FAVOURITE] = [archive_team_line, closing_line]
                        bet_types[self.BET_TYPE_SPREAD_AWAY_FAVOURITE] = [archive_spread_line, archive_spread_no]
                    else:
                        bet_types[self.BET_TYPE_AWAY_UNDERDOG] = [archive_team_line, closing_line]
                        bet_types[self.BET_TYPE_SPREAD_AWAY_UNDERDOG] = [archive_spread_line, archive_spread_no]
                elif team_selection == models.TIP_SELECTION_TEAM_HOME:
                    if is_side_team_favourite(home=True,side=archive_team_line,spread_no=archive_spread_no,spread=archive_spread_line):
                        bet_types[self.BET_TYPE_HOME_FAVOURITE] = [archive_team_line, closing_line]
                        bet_types[self.BET_TYPE_SPREAD_HOME_FAVOURITE] = [archive_spread_line, archive_spread_no]
                    else:
                        bet_types[self.BET_TYPE_HOME_UNDERDOG] = [archive_team_line, closing_line]
                        bet_types[self.BET_TYPE_SPREAD_HOME_UNDERDOG] = [archive_spread_line, archive_spread_no]
                else:
                    logging.error('Encountered unsupported single team selection')
                    raise Exception('Encountered unsupported single team selection')
            
            # update row specific values
            new_row_values[self.SELECTION_INDEX] = team_selection
            new_row_values[self.TIME_INDEX] = date_label
                
            # archive each bet for this tip
            for bet_type, bet_odds in bet_types.iteritems():
                if bet_odds[0] is None or bet_odds[1] is None:
                    continue
                
                new_row_values[self.TYPE_INDEX] = bet_type
                
                spread_mod = None
                if (
                    bet_type in [
                                self.BET_TYPE_SPREAD_AWAY_FAVOURITE,
                                self.BET_TYPE_SPREAD_AWAY_UNDERDOG,
                                self.BET_TYPE_SPREAD_DRAW_AWAY_FAVOURITE,
                                self.BET_TYPE_SPREAD_DRAW_AWAY_UNDERDOG,
                                self.BET_TYPE_SPREAD_HOME_FAVOURITE,
                                self.BET_TYPE_SPREAD_HOME_UNDERDOG,
                                self.BET_TYPE_SPREAD_DRAW_HOME_FAVOURITE,
                                self.BET_TYPE_SPREAD_DRAW_HOME_UNDERDOG,
                                self.BET_TYPE_SPREAD_NO_DRAW_HOME_FAVOURITE,
                                self.BET_TYPE_SPREAD_NO_DRAW_HOME_UNDERDOG,
                                ]
                ):
                    spread_mod = bet_odds[1]
                
                # get bet result
                # away team bet
                if (
                    bet_type in [
                                self.BET_TYPE_AWAY_FAVOURITE, 
                                self.BET_TYPE_AWAY_UNDERDOG, 
                                self.BET_TYPE_SIDE_DRAW_AWAY_FAVOURITE, 
                                self.BET_TYPE_SIDE_DRAW_AWAY_UNDERDOG,
                                self.BET_TYPE_SIDE_NO_DRAW_AWAY_FAVOURITE,
                                self.BET_TYPE_SIDE_NO_DRAW_AWAY_UNDERDOG,
                                self.BET_TYPE_SPREAD_AWAY_FAVOURITE,
                                self.BET_TYPE_SPREAD_AWAY_UNDERDOG,
                                self.BET_TYPE_SPREAD_DRAW_AWAY_FAVOURITE,
                                self.BET_TYPE_SPREAD_DRAW_AWAY_UNDERDOG,
                                ]
                ):
                    bet_result = tipanalysis.calculate_event_score_result(original_league_value, score_away, score_home, draw=tipanalysis.BET_RESULT_LOSS, spread_modifier=spread_mod)
                # home team bet
                elif (
                    bet_type in [
                                self.BET_TYPE_HOME_FAVOURITE, 
                                self.BET_TYPE_HOME_UNDERDOG, 
                                self.BET_TYPE_SIDE_DRAW_HOME_FAVOURITE, 
                                self.BET_TYPE_SIDE_DRAW_HOME_UNDERDOG,
                                self.BET_TYPE_SIDE_NO_DRAW_HOME_FAVOURITE,
                                self.BET_TYPE_SIDE_NO_DRAW_HOME_UNDERDOG,
                                self.BET_TYPE_SPREAD_HOME_FAVOURITE,
                                self.BET_TYPE_SPREAD_HOME_UNDERDOG,
                                self.BET_TYPE_SPREAD_DRAW_HOME_FAVOURITE,
                                self.BET_TYPE_SPREAD_DRAW_HOME_UNDERDOG,
                                self.BET_TYPE_SPREAD_NO_DRAW_HOME_FAVOURITE,
                                self.BET_TYPE_SPREAD_NO_DRAW_HOME_UNDERDOG,
                                ]
                ):
                    bet_result = tipanalysis.calculate_event_score_result(original_league_value, score_home, score_away, draw=tipanalysis.BET_RESULT_LOSS, spread_modifier=spread_mod)
                # draw bet
                elif (
                      bet_type in [
                                self.BET_TYPE_SIDE_DRAW,
                                ]
                ):
                    bet_result = tipanalysis.calculate_event_score_result(original_league_value, score_home, score_away, draw=tipanalysis.BET_RESULT_WIN)
                    
                new_row_values[self.RESULT_INDEX] = bet_result
                
                if spread_mod is not None:
                    new_row_values[self.LEAGUE_INDEX] = original_league_value + ' Spread'
                    new_row_values[self.ODDS_INDEX] = round(tipanalysis.convert_to_decimal_odds(bet_odds[0]),3)
                    new_row_values[self.CLOSE_ODDS_INDEX] = round(tipanalysis.convert_to_decimal_odds(closing_spread_line),3)
                    new_row_values[self.LINE_INDEX] = spread_mod
                    new_row_values[self.CLOSE_LINE_INDEX] = closing_spread_no
                else:
                    new_row_values[self.LEAGUE_INDEX] = original_league_value + ' Money Line'
                    new_row_values[self.ODDS_INDEX] = round(tipanalysis.convert_to_decimal_odds(bet_odds[0]),3)
                    new_row_values[self.CLOSE_ODDS_INDEX] = round(tipanalysis.convert_to_decimal_odds(bet_odds[1]),3)
                    new_row_values[self.LINE_INDEX] = None
                    new_row_values[self.CLOSE_LINE_INDEX] = None
                
                archive_tip_team_lists.append(new_row_values[:])
                
        return archive_tip_team_lists
    
    def get_new_archive_total_value_lists(self, default_row_values, dates_to_archive, total_selection, total_no, total_lines, score_away, score_home):
        archive_tip_total_lists = []
        
        original_league_value = default_row_values[self.LEAGUE_INDEX]
        
        # archive PPD or suspended games too
        if score_away is None or score_home is None:
            total_score = None
        # otherwise get total score to compare against total no bet
        else:
            total_score = float(tipanalysis.strip_score(original_league_value, score_away)) + float(tipanalysis.strip_score(original_league_value, score_home))
        
        closing_total_no = tipanalysis.get_line(total_no)[0]
        closing_total_line = tipanalysis.get_line(total_lines)[0]

        new_row_values = default_row_values[:]
        for date_label, date_to_archive in dates_to_archive.iteritems():
            archive_total_no = tipanalysis.get_line(total_no, date=date_to_archive)[0]
            archive_total_line = tipanalysis.get_line(total_lines, date=date_to_archive)[0]
            
            if archive_total_no is None or archive_total_line is None:
                continue
            
            new_row_values[self.SELECTION_INDEX] = total_selection
            
            # get bet result
            if total_selection == models.TIP_SELECTION_TOTAL_OVER:
                bet_type = self.BET_TYPE_TOTAL_OVER
                bet_result = tipanalysis.calculate_event_score_result(original_league_value, total_score, archive_total_no)
            elif total_selection == models.TIP_SELECTION_TOTAL_UNDER:
                bet_type = self.BET_TYPE_TOTAL_UNDER
                bet_result = tipanalysis.calculate_event_score_result(original_league_value, archive_total_no, total_score)
            else:
                bet_type = self.BET_TYPE_TOTAL_NONE
                bet_result = tipanalysis.calculate_event_score_result(original_league_value, archive_total_no, total_score)
            
            new_row_values[self.LEAGUE_INDEX] = original_league_value + ' Total'
            new_row_values[self.TYPE_INDEX] = bet_type
            
            new_row_values[self.TIME_INDEX] = date_label
            new_row_values[self.RESULT_INDEX] = bet_result
            
            new_row_values[self.ODDS_INDEX] = round(tipanalysis.convert_to_decimal_odds(archive_total_line),3)
            new_row_values[self.CLOSE_ODDS_INDEX] = round(tipanalysis.convert_to_decimal_odds(closing_total_line),3)
            new_row_values[self.LINE_INDEX] = archive_total_no
            new_row_values[self.CLOSE_LINE_INDEX] = closing_total_no
                
            archive_tip_total_lists.append(new_row_values[:])
                
        return archive_tip_total_lists