#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import frontpage
import tipdisplay
import dashboard
import settings
import taskhandler
import tiparchive
import superadmin

application = webapp.WSGIApplication([
                                      ('/', frontpage.FrontPage), 
                                      ('/'+taskhandler.TASK_SCRAPE_CRON, taskhandler.TaskHandler), 
                                      ('/display', tipdisplay.TipDisplay),
                                      ('/archive', tiparchive.TipArchive),
                                      ('/dashboard', dashboard.Dashboard),
                                      ('/appvars', settings.AppSettings),
                                      ('/superadmin', superadmin.SuperAdmin),
                                    ], 
                                    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()