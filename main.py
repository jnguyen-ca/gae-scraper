#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import frontpage
from tiparchive import TipArchive
import tipdisplay
import dashboard
import settings
import taskhandler

application = webapp.WSGIApplication([
                                      ('/', frontpage.FrontPage), 
                                      ('/'+taskhandler.TASK_SCRAPE_CRON, taskhandler.TaskHandler), 
                                      ('/display', tipdisplay.TipDisplay),
                                      ('/archive', TipArchive),
                                      ('/dashboard', dashboard.Dashboard),
                                      ('/appvars', settings.AppSettings),
                                    ], 
                                    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()