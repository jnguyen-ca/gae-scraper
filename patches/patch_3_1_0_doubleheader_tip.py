#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from models import Tip

def patch_3_1_0_doubleheader_tip(tip_instance):
    game_time = tip_instance.date - datetime.timedelta(hours = 6)
    
    start_day = datetime.datetime.combine(game_time, datetime.time())
    end_day = datetime.datetime.combine(game_time, datetime.time(hour=23,minute=59,second=59,microsecond=59))
    
    query = Tip.gql('WHERE date != :1 AND date >= :2 AND date <= :3 AND game_team_away = :4 AND game_team_home = :5',
                    tip_instance.date,
                    start_day,
                    end_day,
                    tip_instance.game_team_away,
                    tip_instance.game_team_home
                    )
    
    if query.count() != 0:
        return game_time.strftime('%d.%m.%Y %H:%M')+': '+tip_instance.game_team_away+' @ '+tip_instance.game_team_home
    else:
        return False
