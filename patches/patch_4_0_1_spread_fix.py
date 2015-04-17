#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
from models import Tip

from google.appengine.ext import ndb
from timeit import itertools
import json
import logging

def patch():
    '''When v4.0.0 was set as the default version, there was a bug where in the scraper.PinnacleScraper.scrape() function
    the spread points and odds were being mixed up with each other. That is to say that the BookieScrapeData spread_away and
    spread_home attributes were being created where the odds value was actually points text (period_spread) while the points
    value was actually the odds text (period_spread_adjust). Obviously this meant that spread results would be broken.
    This patch fixes the issue in all Tips that did not yet elapse when the version was set to default.
    
    The patch works by going through each Tip and going through the spread attributes entries individually to determine
    whether it is a point or odd string. This can be done due to the fact that the odds are stored in American format 
    and that spreads will not reach 3 digit numbers.
    '''
    datetime_set_default = datetime.strptime('2015-04-14 02:16:05', '%Y-%m-%d %H:%M:%S') # date that 4.0.0 went live
    
    commit_tips = []
    
    query = Tip.gql('WHERE date >= :1', datetime_set_default)
    for tip_instance in query:
        unfixed_spread_points = json.loads(tip_instance.spread_no) if tip_instance.spread_no else {}
        unfixed_spread_odds = json.loads(tip_instance.spread_lines) if tip_instance.spread_lines else {}
        
        fixed_spread_points = {}
        fixed_spread_odds = {}
        
        updated = False
        for date_string, data_string in itertools.chain(unfixed_spread_points.iteritems(), unfixed_spread_odds.iteritems()):
            if float(data_string) > 99 or float(data_string) < -99:
                fixed_spread_odds[date_string] = data_string
                
                if (
                    updated is False 
                    and (
                         date_string not in unfixed_spread_odds 
                         or unfixed_spread_odds[date_string] != data_string
                    )
                 ):
                    updated = True
            else:
                fixed_spread_points[date_string] = data_string

                if (
                    updated is False 
                    and (
                         date_string not in unfixed_spread_points 
                         or unfixed_spread_points[date_string] != data_string
                    )
                 ):
                    updated = True
        
        if updated is True and fixed_spread_points and fixed_spread_odds:
            tip_instance.spread_no = json.dumps(fixed_spread_points)
            tip_instance.spread_lines = json.dumps(fixed_spread_odds)
            
            commit_tips.append(tip_instance)
    
    logging.info('Total Writes: '+str(len(commit_tips)))
    ndb.put_multi(commit_tips)