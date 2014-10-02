#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from models import Tip

def patch_3_1_0_doubleheader_tip(tip_instance):
    game_time = tip_instance.date - datetime.timedelta(hours = 6)
    
    start_day = datetime.datetime.combine(game_time, datetime.time()) + datetime.timedelta(hours = 6)
    end_day = datetime.datetime.combine(game_time, datetime.time(hour=23,minute=59,second=59,microsecond=59)) + datetime.timedelta(hours = 6)
    
    query = Tip.gql('WHERE date >= :1 AND date <= :2 AND game_team_away = :3 AND game_team_home = :4',
                    start_day,
                    end_day,
                    tip_instance.game_team_away,
                    tip_instance.game_team_home
                    )
    
    if query.count(limit=2) > 1:
        return tip_instance.date.strftime('%d.%m.%Y')+': '+tip_instance.game_team_away+' @ '+tip_instance.game_team_home
            
    return False
