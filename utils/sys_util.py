#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from google.appengine.api import mail

import random
import os
import time
import logging
import appvar_util
import constants

__MAIL_OBJECT__ = None
__FUNCTION_TIMERS__ = {}

FUNCTION_TIMER_MODE_RESET = 'forceStart'
FUNCTION_TIMER_MODE_INCREMENT = 'increment'
FUNCTION_TIMER_MODE_DEFAULT = FUNCTION_TIMER_MODE_INCREMENT

def is_local():
    return os.environ['SERVER_SOFTWARE'].startswith('Development')

def function_timer(module_name='default', function_name='', mode=FUNCTION_TIMER_MODE_DEFAULT):
    global __FUNCTION_TIMERS__
    
    if function_name and module_name:
        if module_name not in __FUNCTION_TIMERS__:
            __FUNCTION_TIMERS__[module_name] = {}
            
        if mode == FUNCTION_TIMER_MODE_RESET or function_name not in __FUNCTION_TIMERS__[module_name]:
            __FUNCTION_TIMERS__[module_name][function_name] = {}
            
        if 'startTime' not in __FUNCTION_TIMERS__[module_name][function_name]:
            __FUNCTION_TIMERS__[module_name][function_name]['startTime'] = time.time()
            __FUNCTION_TIMERS__[module_name][function_name]['timer'] = None
        else:
            if __FUNCTION_TIMERS__[module_name][function_name]['timer'] is None:
                __FUNCTION_TIMERS__[module_name][function_name]['timer'] = 0.0
            
            __FUNCTION_TIMERS__[module_name][function_name]['timer'] += time.time() - __FUNCTION_TIMERS__[module_name][function_name]['startTime']
            __FUNCTION_TIMERS__[module_name][function_name].pop('startTime', None)
    else:
        for timerMod, modFunc in __FUNCTION_TIMERS__.iteritems():
            remove_keys = []
            for timerFunc, funcTimer in modFunc.iteritems():
                if funcTimer['timer'] is None or 'startTime' in funcTimer:
                    logging.warning('%s[%s] timer was not closed off.' % (timerMod, timerFunc))
                    remove_keys.append(timerFunc)
                else:
                    __FUNCTION_TIMERS__[timerMod][timerFunc] = funcTimer['timer']
            for timerFunc in remove_keys:
                __FUNCTION_TIMERS__[timerMod].pop(timerFunc, None)
        timers = __FUNCTION_TIMERS__
        __FUNCTION_TIMERS__ = {}
        return timers
    
def get_header():
    header = {}
    
    user_agents = appvar_util.get_header_user_agents()
    
    header['User-Agent'] = random.choice(user_agents)
    header['Accept-Encoding'] = 'gzip, deflate'
    
    return header

def add_mail(mail_title, mail_message, **kwargs):
    global __MAIL_OBJECT__
    if 'logging' in kwargs:
        try:
            getattr(logging, kwargs['logging'])(mail_message.strip())
        except (AttributeError, TypeError):
            logging.error('logging function not found "%s" (%s)' % (kwargs['logging'], mail_message))
        
    try:
        if mail_title not in __MAIL_OBJECT__:
            __MAIL_OBJECT__[mail_title] = ''
            
        __MAIL_OBJECT__[mail_title] += mail_message
    except TypeError:
        __MAIL_OBJECT__ = {mail_title : mail_message}

def send_all_mail():
    global __MAIL_OBJECT__
    try:
        mail_count = 0
        for mail_title, mail_message in __MAIL_OBJECT__.iteritems():
            mail.send_mail_to_admins(constants.MAIL_SENDER, mail_title, mail_message.strip())
            mail_count += 1
            
        logging.debug('%d mail sent.' % (mail_count))
    except (TypeError, AttributeError):
        # if mail_object is not iterable or not a dict do nothing
        pass
    
    __MAIL_OBJECT__ = {}

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