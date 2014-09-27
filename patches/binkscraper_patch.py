#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.insert(0, 'libs')

from mapreduce import operation

from patch_3_1_0_doubleheader_tip import patch_3_1_0_doubleheader_tip

def run_patch(tip_instance):
    if tip_instance.game_sport == 'Baseball':
        result = patch_3_1_0_doubleheader_tip(tip_instance)
        
        if result:
            yield operation.counters.Increment(result)
        else:
            yield operation.counters.Increment('Pass')
    else:
        yield operation.counters.Increment('Sport Pass')