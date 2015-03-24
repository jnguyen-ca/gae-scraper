#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.ext import ndb
import models
import re
import json
import logging

APPVAR_SPORT_NAMES = 'sportconstants'
APPVAR_LEAGUE_NAMES = 'leagueconstants'
APPVAR_TEAM_NAMES = 'teamconstants'
APPVAR_SPORTS_H2H_EXCLUDE = 'sportsh2hexclude'
APPVAR_SPORTS_WEEKLY = 'sportsweekly'
APPVAR_LEAGUES_OT_INCLUDED = 'leaguesotincluded'

APPVAR_USER_AGENTS = 'header_user_agents'

VALID_APPVAR_LIST = [
               APPVAR_SPORT_NAMES,
               APPVAR_LEAGUE_NAMES,
               APPVAR_TEAM_NAMES, 
               APPVAR_SPORTS_H2H_EXCLUDE,
               APPVAR_SPORTS_WEEKLY,
               APPVAR_LEAGUES_OT_INCLUDED,
               APPVAR_USER_AGENTS,
               ]

__TEMPLATE_TAGS__ = {}
__CSS_STYLES__ = ''
__CSS_SHEETS__ = []
__JS_SCRIPTS__ = ''
__JS_FILES__ = []

def add_template_tag(key, value, overwrite=False):
    global __TEMPLATE_TAGS__
    if key not in __TEMPLATE_TAGS__ or overwrite is True:
        __TEMPLATE_TAGS__[key] = value
    else:
        __TEMPLATE_TAGS__[key] += value
    return

def add_template_tags(tags, overwrite=False):
    global __TEMPLATE_TAGS__
    if not __TEMPLATE_TAGS__ or overwrite is True:
        __TEMPLATE_TAGS__ = tags
    else:
        __TEMPLATE_TAGS__.update(tags)
    return

def add_css_styles(styles):
    global __CSS_STYLES__
    __CSS_STYLES__ += styles
    return

def add_css_sheets(sheets):
    global __CSS_SHEETS__
    if isinstance(sheets, list):
        for sheet in sheets:
            __CSS_STYLES__ += '<link rel="stylesheet" type="text/css" href="'+sheet+'">'
    else:
        __CSS_STYLES__ += '<link rel="stylesheet" type="text/css" href="'+sheets+'">'
    return

def add_js_scripts(scripts):
    global __JS_SCRIPTS__
    __JS_SCRIPTS__ += scripts
    return

def add_js_files(files):
    global __JS_FILES__
    if isinstance(files, list):
        for js in files:
            __JS_FILES__ += '<script src='+js+'"></script>'
    else:
        __JS_FILES__ += '<script src='+files+'"></script>'
    return

def reset_all_meta():
    global __TEMPLATE_TAGS__
    global __CSS_STYLES__
    global __CSS_SHEETS__
    global __JS_SCRIPTS__
    global __JS_FILES__
    __TEMPLATE_TAGS__ = {}
    __CSS_STYLES__ = ''
    __CSS_SHEETS__ = []
    __JS_SCRIPTS__ = ''
    __JS_FILES__ = []
    return

def replace_template_tags(line, templates):
    """Replaces [template:tag_name] in a line with the tag_name value in templates
    """
    template_tags = re.finditer('\[template:(\S+)\]', line)
    if template_tags:
        for match in template_tags:
            if match.group(1) in templates:
                line = line.replace(match.group(0), templates[match.group(1)])
    
    return line

def print_html(output, html=None):
    global __TEMPLATE_TAGS__
    global __CSS_STYLES__
    global __CSS_SHEETS__
    global __JS_SCRIPTS__
    global __JS_FILES__
    
    if html is not None:
        with open(html) as f:
            for line in f:
                line = replace_template_tags(line, __TEMPLATE_TAGS__)
                if '</head>' in line:
                    output.write("".join(__CSS_SHEETS__))
                    output.write("".join(__JS_FILES__))
                    output.write(__JS_SCRIPTS__)
                    output.write(__CSS_STYLES__)
                output.write(line)
                
    reset_all_meta()
    
def set_app_var(key, value):
    if key not in VALID_APPVAR_LIST:
        raise KeyError('Invalid application variable key ('+key+')')
    
    if not isinstance(value, basestring) and value is not None:
        value = json.dumps(value)
    elif not value:
        value = None
    
    return models.ApplicationVariables(id=key, value=value).put()

def get_or_set_app_var(key):
    app_var = ndb.Key(models.ApplicationVariables, key).get()
    if app_var is None:
        logging.info('Creating new application variable ('+key+')!')
        app_var = set_app_var(key, None).get()
    value = app_var.value
    
    if value is not None:
        try:
            value = json.loads(value)
        except ValueError:
            pass
    
    return value

def is_ajax(request):
    """Check if a request is from AJAX
    """
    if 'X-Requested-With' in request.headers and request.headers['X-Requested-With'] == 'XMLHttpRequest':
        return True
    return False

def list_unique(seq, preserve_order=False):
    """Creates a new list of the unique values in a given list.
    
    Params:
        seq (list)
        preserve_order (boolean): whether new list should keep the order the values first appear in 
    
    Returns:
        list: list of unique values
    
    http://www.peterbe.com/plog/uniqifiers-benchmark
    """
    if preserve_order is True:
        seen = set()
        return [x for x in seq if x not in seen and not seen.add(x)]
    else:
        return list(set(seq))
    
def get_from_dict(dataDict, mapList):
    '''Get a dictionary entry via a list of keys
    
    https://stackoverflow.com/questions/14692690/access-python-nested-dictionary-items-via-a-list-of-keys/14692747#14692747
    '''
    return reduce(lambda d, k: d[k], mapList, dataDict)

def set_in_dict(dataDict, mapList, value):
    '''Set a value for a dictionary entry via a list of keys
    
    https://stackoverflow.com/questions/14692690/access-python-nested-dictionary-items-via-a-list-of-keys/14692747#14692747
    '''
    get_from_dict(dataDict, mapList[:-1])[mapList[-1]] = value
    
def del_in_dict(dataDict, mapList):
    '''Delete a element in a dictionary entry via a list of keys
    '''
    get_from_dict(dataDict, mapList[:-1]).pop(mapList[-1], None)