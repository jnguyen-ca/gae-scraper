#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import webapp

import sys
from datetime import datetime

import json
import cgi
import constants
import util
import memcache_util
import tiparchive

def replace_filter_col_with_name(spreadsheet=None, filter_cols=None):
    memcache_columns = memcache_util.get(memcache_util.MEMCACHE_KEY_DASHBOARD_SPREADSHEET_FILTER_COLUMNS)
    if memcache_columns is not None:
        for filter_key, filter_col in json.loads(memcache_columns).iteritems():
            filter_cols[filter_key] = filter_col
        return
    
    if spreadsheet is None:
        spreadsheet = tiparchive.get_spreadsheet()
    worksheet = spreadsheet.get_worksheet(0)
    
    if isinstance(filter_cols, dict):
        for filter_key, filter_col in filter_cols.iteritems():
            filter_cols[filter_key] = worksheet.cell(1, filter_col).value
#     elif isinstance(filter_cols, list):
#         new_name_list = []
#         for filter_col in filter_cols:
#             new_name_list.append(worksheet.cell(1, filter_col).value)
#         filter_cols = new_name_list
    elif filter_cols is not None:
        raise TypeError('Filter columns should be a list or dictionary!')
    
    memcache_util.set(memcache_util.MEMCACHE_KEY_DASHBOARD_SPREADSHEET_FILTER_COLUMNS, json.dumps(filter_cols))
    return

def get_spreadsheet_data(spreadsheet=None, filter_cols=None, replace_filter_values=None):
    # filter columns options for select menus
    data = {'entries' : {}}
    if filter_cols is not None:
        data['filters'] = {}
        
    if spreadsheet is None:
        spreadsheet = tiparchive.get_spreadsheet()
    
    if replace_filter_values is True:
        # get the filter columns text (replacing the column number)
        replace_filter_col_with_name(spreadsheet, filter_cols)
    
    i = 1
    worksheet = spreadsheet.get_worksheet(i)
    # go through all leagues stored in archive
    while worksheet is not None:
        league = worksheet.title
        worksheet_data = worksheet.get_all_records()
        
        data['entries'][league] = worksheet_data
        
        if filter_cols is not None:
            data['filters'][league] = {}
            
            for entry in data['entries'][league]:
                for filter_key, filter_col in filter_cols.iteritems():
                    if replace_filter_values is not True:
                        filter_col = worksheet.cell(1, filter_col).value
                    
                    if filter_key not in data['filters'][league]:
                        data['filters'][league][filter_key] = [entry[filter_col]]
                    elif entry[filter_col] not in data['filters'][league][filter_key]:
                        data['filters'][league][filter_key].append(entry[filter_col])
                        
            for filter_value_lists in data['filters'].values():
                for filter_values in filter_value_lists.values():
                    filter_values.sort()
                        
        i += 1
        worksheet = spreadsheet.get_worksheet(i)
    
    return data

class Dashboard(webapp.RequestHandler):
    # input names for form submission for the dashboard
    INPUT_NAME_DATE_FILTER = 'enable-disable-date-input'
    INPUT_NAME_DATE_RANGE_START_MONTH = 'date-input-start-month'
    INPUT_NAME_DATE_RANGE_START_DAY = 'date-input-start-day'
    INPUT_NAME_DATE_RANGE_START_YEAR = 'date-input-start-year'
    INPUT_NAME_DATE_RANGE_END_MONTH = 'date-input-end-month'
    INPUT_NAME_DATE_RANGE_END_DAY = 'date-input-end-day'
    INPUT_NAME_DATE_RANGE_END_YEAR = 'date-input-end-year'
    INPUT_NAME_LEAGUE_FILTER = 'league-select'
    INPUT_NAME_TYPE_FILTER = 'type-select'
    INPUT_NAME_FILTERA_FILTER = 'filtera-select'
    INPUT_NAME_FILTERB_FILTER = 'filterb-select'
    
    # constant input values for dashboard
    DASHBOARD_FILTER_DISABLE_DATE = 'disable-date-filter'
    DASHBOARD_FILTER_ENABLE_DATE = 'enable-date-filter'
    
    FILTER_KEY_DATE = 'filter-date'
    FILTER_KEY_LEAUGE = 'filter-league'
    FILTER_KEY_TYPE = 'filter-type'
    FILTER_KEY_FILTERA = 'filter-filtera'
    FILTER_KEY_FILTERB = 'filter-filterb'
    
    def post(self):
#         sys.stderr.write(str(self.request.headers['X-Requested-With'])+"\n")
        if util.is_ajax(self.request):
            sys.stderr.write("Doing AJAXy stuff\n")
        return
    
    def get(self):
        # set what columns will be filtered on
        filter_columns = {
                          self.FILTER_KEY_DATE          :       tiparchive.SPREADSHEET_DATE_COL,
                          self.FILTER_KEY_LEAUGE        :       tiparchive.SPREADSHEET_LEAGUE_COL, 
                          self.FILTER_KEY_TYPE          :       tiparchive.SPREADSHEET_TYPE_COL, 
                          self.FILTER_KEY_FILTERA       :       tiparchive.SPREADSHEET_FILTERA_COL, 
                          self.FILTER_KEY_FILTERB       :       tiparchive.SPREADSHEET_FILTERB_COL,
                          }
        
        # check to see if spreadsheet data is in the memcache
        cached_data = memcache_util.get(memcache_util.MEMCACHE_KEY_DASHBOARD_SPREADSHEET_DATA)
        spreadsheet_data = None
        if cached_data is not None:
            spreadsheet_data = json.loads(cached_data)
            replace_filter_col_with_name(filter_cols=filter_columns)

        # if no data in memcache or memcache data is more than half a day old
        if spreadsheet_data is None or 43200 < (datetime.utcnow() - datetime.strptime(spreadsheet_data['time_of_entry'], constants.DATETIME_ISO_8601_FORMAT)).total_seconds():
            spreadsheet_data = get_spreadsheet_data(filter_cols=filter_columns, replace_filter_values=True)
            spreadsheet_data['time_of_entry'] = datetime.utcnow().strftime(constants.DATETIME_ISO_8601_FORMAT)
        
        memcache_util.set(memcache_util.MEMCACHE_KEY_DASHBOARD_SPREADSHEET_DATA, json.dumps(spreadsheet_data))
        
        # create the filter template html
        self.create_filter_set(filter_columns, spreadsheet_data['filters'])
        
        # print out the page line by line replacing template tags as you go
        util.print_html(self.response.out, html='dashboard.html')
        
        return
    
    def create_filter_set(self, filter_keys, filter_data):
        # date filters (2 radio, 2 date menus)
        util.add_template_tag('dashboard_filters', self.date_filter(filter_keys, filter_data))
        # C (sport/league) selection
        util.add_template_tag('dashboard_filters', self.league_filter(filter_data))
        # E (bet type) selection
        util.add_template_tag('dashboard_filters', self.create_select_filter(self.FILTER_KEY_TYPE, self.INPUT_NAME_TYPE_FILTER))
        # F & G selection
        util.add_template_tag('dashboard_filters', self.create_select_filter(self.FILTER_KEY_FILTERA, self.INPUT_NAME_FILTERA_FILTER))
        util.add_template_tag('dashboard_filters', self.create_select_filter(self.FILTER_KEY_FILTERB, self.INPUT_NAME_FILTERB_FILTER))
        
        util.add_template_tag('filters_values', '<input type="hidden" class="filter-values" value="%s">' % (cgi.escape(json.dumps(filter_data), True)))
        return
    
    def date_filter(self, filter_keys, filter_data):
        leagues = []
        
        # get the first year the date selections should have (earliest tip date)
        earliest_year = 2014
        for league, filter_values in filter_data.iteritems():
            leagues.append(league)
            first_year_entry = int(filter_values[self.FILTER_KEY_DATE][0][-4:])
            
            if first_year_entry < earliest_year:
                earliest_year = first_year_entry
        
        # remove unique date values as they are not needed since date filter is not a single select menu
        for league in leagues:
            filter_data[league].pop(self.FILTER_KEY_DATE, None)
        
        # 2 radio buttons to enable or disable filter and 6 select menus split for start and end dates (M-D-Y)
        # blank select menus where valid options are filled out with javascript
        HTML = '''
        <span class="%s filter">
            <div class="enable-disable-date">
                <span class="disable-date">
                    <input id="disable-date-input-00" type="radio" value="%s" class="disable-date-input" name="%s"><label for="disable-date-input-00">All dates</label>
                </span>
                <span class="enable-date">
                    <input id="enable-date-input-00" type="radio" value="%s" class="enable-date-input" name="%s"><label for="enable-date-input-00">Specific dates</label>
                </span>
            </div>
            <div class="date-selection">
                <div class="start-date">
                    <span class="label">Start:</span>
                    <span class="month">
                        <select name="%s"></select>
                    </span>
                    <span class="day">
                        <select name="%s"></select>
                    </span>
                    <span class="year">
                        <select name="%s"></select>
                    </span>
                </div>
                <div class="end-date">
                    <span class="label">End:</span>
                    <span class="month">
                        <select name="%s"></select>
                    </span>
                    <span class="day">
                        <select name="%s"></select>
                    </span>
                    <span class="year">
                        <select name="%s">
                            <option value="%s">%s</option>
                        </select>
                    </span>
                </div>
            </div>
        </span>
        ''' % (
               self.FILTER_KEY_DATE,
               self.DASHBOARD_FILTER_DISABLE_DATE,
               self.INPUT_NAME_DATE_FILTER,
               self.DASHBOARD_FILTER_ENABLE_DATE,
               self.INPUT_NAME_DATE_FILTER,
               self.INPUT_NAME_DATE_RANGE_START_MONTH,
               self.INPUT_NAME_DATE_RANGE_START_DAY,
               self.INPUT_NAME_DATE_RANGE_START_YEAR,
               self.INPUT_NAME_DATE_RANGE_END_MONTH,
               self.INPUT_NAME_DATE_RANGE_END_DAY,
               self.INPUT_NAME_DATE_RANGE_END_YEAR,
               earliest_year,
               earliest_year
               )
        
        return HTML
    
    def league_filter(self, filter_data):
        super_league_selections = ''
        for league in filter_data:
            super_league_selections += '<option value="%s">%s</option>' % (league, league)
        
        HTML = '''
        <span class="super-league-filter super-filter filter">
            <select>%s</select>
        </span>
        ''' % (super_league_selections) + self.create_select_filter(self.FILTER_KEY_LEAUGE, self.INPUT_NAME_LEAGUE_FILTER)
        
        return HTML
    
    def create_select_filter(self, filter_key, filter_name):
        HTML = '''
        <span class="%s filter" data-filter-key="%s">
            <select name="%s"></select>
        </span>
        ''' % (
               filter_key,
               filter_key,
               filter_name
               )
        return HTML