#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import webapp

class SuperAdmin(webapp.RequestHandler):
    def get(self):
        patcher = RunPatch()
        patcher.run_patch()

import sys
sys.path.append('patches')

from patches import patch_4_0_1_spread_fix

class RunPatch(object):
    def __init__(self):
        pass
        
    def run_patch(self):
        patch_4_0_1_spread_fix.patch()