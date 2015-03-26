#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random
import os
import appvar_util

def is_local():
    return os.environ['SERVER_SOFTWARE'].startswith('Development')

def get_header():
    header = {}
    
    user_agents = appvar_util.get_header_user_agents()
    
    header['User-Agent'] = random.choice(user_agents)
    header['Accept-Encoding'] = 'gzip, deflate'
    
    return header

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