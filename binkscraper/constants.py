#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.api import mail

class ApplicationException(Exception):
    def __init__(self, message, mail_title='No Title'):
        mail.send_mail_to_admins(MAIL_SENDER, mail_title, message)
        super(ApplicationException, self).__init__(message)

# use pinnacle sports xml feed as our official game list feed
# TSN_FEED = 'http://www.tsn.ca/'
WETTPOINT_FEED = 'wettpoint.com'

MAIL_SENDER = 'noreply@binkscraper.appspotmail.com'

MAIL_TITLE_DATASTORE_ERROR = 'Datastore Exception'
MAIL_TITLE_APPLICATION_ERROR = 'Application Exception'
MAIL_TITLE_TEAM_ERROR = 'Team Error'
MAIL_TITLE_TIP_WARNING = 'Game Warning'
MAIL_TITLE_MISSING_EVENT = 'Missing Event'
MAIL_TITLE_GENERIC_WARNING = 'Warning Notice'
MAIL_TITLE_UPDATE_NOTIFICATION = 'Update Notice'
MAIL_TITLE_EXTERNAL_WARNING = 'Site Warning'

TIMEZONE_LOCAL = 'America/Edmonton'
TIMEZONE_WETTPOINT = 'Europe/Berlin'
TIMEZONE_SCOREBOARD = 'Europe/Athens'
TIMEZONE_SCORESPRO = 'Europe/Nicosia'

DATETIME_ISO_8601_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
DATE_ISO_8601_FORMAT = '%Y-%m-%d'