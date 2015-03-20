#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# all memcache keys used by the app following the format: MEMCACHE_KEY_(module)_(key)
MEMCACHE_KEY_FRONTPAGE_DISPLAY_LEAGUES = 'DisplaySessionCookie'
MEMCACHE_KEY_SCRAPER_WETTPOINT_TABLE = 'lastWettpointTablesInfo'
MEMCACHE_KEY_TIPARCHIVE_SPREADSHEET = 'tipArchiveSpreadsheet'
MEMCACHE_KEY_TIPARCHIVE_CLIENT = 'tipArchiveClient'
MEMCACHE_KEY_DASHBOARD_SPREADSHEET_DATA = 'spreadsheetData'
MEMCACHE_KEY_DASHBOARD_SPREADSHEET_FILTER_COLUMNS = 'spreadsheetFilterColumns'

from google.appengine.api import memcache

def get(key, namespace=None, for_cas=False):
    return memcache.get(key, namespace=namespace, for_cas=for_cas)
    
def set(key, value, time=0, min_compress_len=0, namespace=None):
    return memcache.set(key, value, time=time, min_compress_len=min_compress_len, namespace=namespace)