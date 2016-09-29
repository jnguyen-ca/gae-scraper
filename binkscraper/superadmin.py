#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import webapp

import logging
from patches import patch_5_0_0_populate_tiplines

class SuperAdmin(webapp.RequestHandler):
    def get(self):
        self.response.out.write('''
<html>
<body>
    <form action="/superadmin" method="post" onsubmit="return confirm('Confirm Populate')">
        <span>Patch 5.0.0 - Populate TipLines</span>
        <input type="hidden" name="patch_function" value="populate">
        <input type="submit" value="Run Populate">
    </form>
    <form action="/superadmin" method="post" onsubmit="return confirm('Confirm Delete')">
        <span>Patch 5.0.0 - Delete TipLines</span>
        <input type="hidden" name="patch_function" value="delete">
        <input type="submit" value="Run Delete">
    </form>
</body>
</html>
        ''')
        
    def post(self):
        patch_function = self.request.get('patch_function')
        patcher = RunPatch(patch_function)
        patcher.run_patch()

class RunPatch(object):
    def __init__(self, service):
        self.service = service
        self.patch = patch_5_0_0_populate_tiplines.Patch_5_0_0()
        
    def run_patch(self):
        if self.service == 'populate':
            logging.info('Starting patch populate...')
            self.patch.patch_populate()
        elif self.service == 'delete':
            logging.info('Starting patch delete...')
            self.patch.patch_delete()
        else:
            raise ValueError('No such patch function')
        logging.info('...Ending patch')