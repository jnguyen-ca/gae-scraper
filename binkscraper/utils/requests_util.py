#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

REQUEST_LIB_REQUESTS = 'requests'
REQUEST_LIB_URLFETCH = 'urlfetch'

RESPONSE_TYPE_HTML = 'html'
RESPONSE_TYPE_XML = 'xml'

RESPONSE_ENCODING_UTF8 = 'utf-8'

from google.appengine.api import urlfetch

import sys
sys.path.append('libs/requests-2.3.0')
sys.path.append('libs/BeautifulSoup-4.3.2')

from httplib import HTTPException
from requests.packages.urllib3.exceptions import ProtocolError

from urlparse import urlparse
from lxml import etree
from bs4 import BeautifulSoup
import requests
import logging
import time
import random

HTTP_EXCEPTION_TUPLE = (HTTPException, urlfetch.DeadlineExceededError, ProtocolError)

__REQUEST_COUNT__ = {}

def get_request_count(host=None):
    global __REQUEST_COUNT__
    if isinstance(host, basestring):
        if host in __REQUEST_COUNT__:
            return __REQUEST_COUNT__[host]
        return 0
    return __REQUEST_COUNT__

def reset_request_count():
    global __REQUEST_COUNT__
    __REQUEST_COUNT__ = {}

def _increment_request(host, increment_value=1):
    global __REQUEST_COUNT__
    if host in __REQUEST_COUNT__:
        __REQUEST_COUNT__[host] += increment_value
    else:
        __REQUEST_COUNT__[host] = increment_value
        
    return __REQUEST_COUNT__[host]

def request(request_lib=REQUEST_LIB_REQUESTS, response_type=RESPONSE_TYPE_HTML, response_encoding=None,
            min_wait_time=15, max_wait_time=60, max_hits=10, no_hit=False,
            log_info=None, **kwargs):
    hostname = urlparse(kwargs['url']).hostname
    
    increment = 1
    if no_hit:
        increment = 0
    
    if get_request_count(hostname)+increment > max_hits:
        return None
    hits = _increment_request(hostname, increment_value=increment)
    
    if hits > 1:
        time.sleep(random.uniform(min_wait_time,max_wait_time))
    
    log_string = 'Executing a %s for %s' % (request_lib, kwargs['url'])
    if 'headers' in kwargs:
        log_string += "\n    Headers: %s" % (str(kwargs['headers']))
    if log_info:
        log_string += "\n    %s" % log_info
    logging.debug(log_string)
    
    if request_lib == REQUEST_LIB_URLFETCH:
        result = urlfetch.fetch(**kwargs)
        result = result.content
    elif request_lib == REQUEST_LIB_REQUESTS:
        result = requests.get(**kwargs)
        if response_encoding:
            result.encoding = response_encoding
        result = result.text
        
    if response_type == RESPONSE_TYPE_HTML:
        return BeautifulSoup(result)
    elif response_type == RESPONSE_TYPE_XML:
        etree_parser = etree.XMLParser(ns_clean=True,recover=True)
        return etree.fromstring(result, etree_parser)