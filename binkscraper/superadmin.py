#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import webapp
from google.appengine.api import taskqueue

import logging
from patches import patch_5_0_0_populate_tiplines
from datetime import datetime

class SuperAdmin(webapp.RequestHandler):
    def get(self):
        if self.request.get('patch_function') == 'populate':
            taskqueue.add(url=self.request.path,
                          params={
                                  'patch_function' : 'populate',
                                  'datetime-start' : self.request.get('month-start')+'-'+self.request.get('day-start')+'-'+self.request.get('year-start'),
                                  'datetime-end' : self.request.get('month-end')+'-'+self.request.get('day-end')+'-'+self.request.get('year-end')
                                  })
            self.response.out.write('Adding populate task to queue')
        else:
            self.response.out.write('''
<html>
<body>
    <form action="/superadmin" method="get" onsubmit="return confirm('Confirm Populate')">
        <div>
            <span>Patch 5.0.0 - Populate TipLines</span>
            <input type="hidden" name="patch_function" value="populate">
            <input type="submit" value="Run Populate">
        </div>
        <div>
            Start: <input name="month-start" placeholder="MM"><input name="day-start" placeholder="DD"><input name="year-start" placeholder="YYYY">
        </div>
        <div>
            End: <input name="month-end" placeholder="MM"><input name="day-end" placeholder="DD"><input name="year-end" placeholder="YYYY">
        </div>
    </form>
<!--
    <form action="/superadmin" method="get" onsubmit="return confirm('Confirm Delete')">
        <span>Patch 5.0.0 - Delete TipLines</span>
        <input type="hidden" name="patch_function" value="delete">
        <input type="submit" value="Run Delete">
    </form>
-->
</body>
</html>
        ''')
        
    def post(self):
        patch_function = self.request.get('patch_function')
        datetime_start = datetime.strptime(self.request.get('datetime-start'),
                                           '%m-%d-%Y')
        datetime_end = datetime.strptime(self.request.get('datetime-end'),
                                           '%m-%d-%Y')
        patcher = RunPatch(patch_function, datetime_start, datetime_end)
        patcher.run_patch()

class RunPatch(object):
    def __init__(self, service, datetime_start, datetime_end):
        self.service = service
        self.patch = patch_5_0_0_populate_tiplines.Patch_5_0_0(datetime_start, datetime_end)
        
    def run_patch(self):
        if self.service == 'populate':
            logging.info('Starting patch populate...')
            self.patch.patch_populate()
        elif self.service == 'delete':
            logging.info('Starting patch delete...')
#             self.patch.patch_delete()
        else:
            raise ValueError('No such patch function')
        logging.info('...Ending patch')