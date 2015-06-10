#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('utils')

from utils import sys_util

import models

class TipLineData(object):
    """Wrapper object for viewing and modifying TipLine game objects. Provides
    structure to TipLine functionality for more rigid and consistent results."""
    LINE_KEY_POINTS = models.TIPLINE_KEY_POINTS
    LINE_KEY_ODDS = models.TIPLINE_KEY_ODDS
    
    def __init__(self, tipline_instance):
        self.tipline_instance = tipline_instance
        self._bookies = None
        
    @property
    def bookies(self):
        '''Unique list of bookies (their keys) that have at least 1 entry of 
        data in any of the TipLine's attributes
        '''
        if self._bookies is None:
            bookieKeys = self.tipline_instance.spread_home.keys()
            bookieKeys += self.tipline_instance.money_home.keys()
            bookieKeys += self.tipline_instance.total_under.keys()
            
            self._bookies = sys_util.list_unique(bookieKeys)
        return self._bookies
    
    def _insert_attribute_entry(self, tipline_attribute, bookie_key, date_key, entry_value):
        '''General function for inserting an entry to any of TipLine's attributes
        '''
        if not entry_value:
            return
        
        if not tipline_attribute:
            tipline_attribute = {}
            
        if bookie_key not in tipline_attribute:
            tipline_attribute[bookie_key] = {}
        
        tipline_attribute[bookie_key][date_key] = entry_value
        return tipline_attribute
                
    def _create_points_odds_entry(self, points, odds):
        return {self.LINE_KEY_POINTS : points, self.LINE_KEY_ODDS : odds}
    
    def insert_spread_home_entry(self, bookie, line_date, spread_points, spread_odds):
        self.tipline_instance.spread_home = self._insert_attribute_entry(self.tipline_instance.spread_home, bookie, line_date, self._create_points_odds_entry(spread_points, spread_odds))
    def insert_spread_away_entry(self, bookie, line_date, spread_points, spread_odds):
        self.tipline_instance.spread_away = self._insert_attribute_entry(self.tipline_instance.spread_away, bookie, line_date, self._create_points_odds_entry(spread_points, spread_odds))
    def insert_money_home_entry(self, bookie, line_date, odds):
        self.tipline_instance.money_home = self._insert_attribute_entry(self.tipline_instance.money_home, bookie, line_date, odds)
    def insert_money_away_entry(self, bookie, line_date, odds):
        self.tipline_instance.money_away = self._insert_attribute_entry(self.tipline_instance.money_away, bookie, line_date, odds)
    def insert_money_draw_entry(self, bookie, line_date, odds):
        self.tipline_instance.money_draw = self._insert_attribute_entry(self.tipline_instance.money_draw, bookie, line_date, odds)
    def insert_total_under_entry(self, bookie, line_date, total_points, total_odds):
        self.tipline_instance.total_under = self._insert_attribute_entry(self.tipline_instance.total_under, bookie, line_date, self._create_points_odds_entry(total_points, total_odds))
    def insert_total_over_entry(self, bookie, line_date, total_points, total_odds):
        self.tipline_instance.total_over = self._insert_attribute_entry(self.tipline_instance.total_over, bookie, line_date, self._create_points_odds_entry(total_points, total_odds))
