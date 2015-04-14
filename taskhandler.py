#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('utils')

from google.appengine.ext import webapp
from google.appengine.api import taskqueue, urlfetch

from datetime import datetime
from utils import sys_util

import logging
import scraper
import datahandler

TASK_SCRAPE_CRON = 'scrape'

class TaskHandler(webapp.RequestHandler):
    def get(self):
        taskqueue.add(queue_name='scraper', url=self.request.path)
        self.response.out.write('Adding task to queue for: '+str(self.request.path))
        
    def post(self):
        self.utc_task_start = datetime.utcnow()
        request_type = self.request.path[1:]
        
        if request_type == TASK_SCRAPE_CRON:
            self.scrape_and_update_tips()
            
    def scrape_and_update_tips(self):
        urlfetch.set_default_fetch_deadline(15)
        logging.getLogger('requests').setLevel(logging.WARNING) # disable requests library info and debug messages (to replace with my own)
        scraper.reset_request_count()
        
        # Scraper: find all relevant games
        events = {}
        try:
            pinnacleScraper = scraper.PinnacleScraper()
            events = pinnacleScraper.scrape()
        except scraper.HTTP_EXCEPTION_TUPLE:
            task_execution_count = int(self.request.headers['X-AppEngine-TaskExecutionCount'])
            # if there are retries for the queue left, re-raise exception to retry; otherwise complete without pinnacle lines
            if self.TASK_RETRY_LIMIT > task_execution_count:
                logging.warning('Pinnacle XML feed down; Retrying (%d)' % (task_execution_count+1))
                raise
            else:
                logging.warning('Pinnacle XML feed down; Retry limit reached, continuing on')
                
        # DataHandler: Update and insert Tip objects, creating a relational dict as you go
        bookieData = datahandler.BookieData(events)
        bookieData.update_tips()
        
        tipData = datahandler.TipData({'pinnacle' : bookieData})
        tipData.utc_task_start = self.utc_task_start

        tipData.update_tips()

        # log the scrape hits for each host
        logging_info = ''
        for request_host, request_count in scraper.get_request_count().iteritems():
            logging_info += request_host + ' : ' + str(request_count) + '; '
            
            if int(request_count) > 20:
                logging.critical('%s host being hit %d times in a single execution!' % (request_host, int(request_count)))
        logging.info(logging_info)
        
        for timerMod, modFunc in sys_util.function_timer().iteritems():
            logging_info = ''
            for timerFunc, funcTimer in modFunc.iteritems():
                logging_info += timerFunc+' : '+ str("{0:.2f}".format(funcTimer)) + '; '
            logging.debug('%s [%s]' % (timerMod, logging_info))