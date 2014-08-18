#usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.api import memcache

import sys
from datetime import timedelta
from pprint import pprint
sys.path.insert(0, 'libs')

from _symtable import LOCAL

from timeit import itertools
from math import ceil

from bs4 import BeautifulSoup
from lxml import etree

import string
# import urllib2
import requests
import time
import datetime
import re
import json
import logging
import constants