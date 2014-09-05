#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import random

HEADER = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:31.0) Gecko/20100101 Firefox/31.0', 'Accept-Encoding' : 'gzip, deflate'}

SPORTS_H2H_EXCLUDE = ['Baseball', 'Football']

SPORTS = {
'Baseball'  : {'pinnacle' : 'Baseball', 'wettpoint' : 'baseball', 'scoreboard' : 'baseball'},
'Soccer'    : {'pinnacle' : 'Soccer', 'wettpoint' : 'fussball', 'scoreboard' : 'soccer'},
'Handball'  : {'pinnacle' : 'Handball', 'wettpoint' : 'handball', 'scoreboard' : 'handball'},
'Hockey'    : {'pinnacle' : 'Hockey', 'wettpoint' : 'eishockey', 'scoreboard' : 'hockey'},
'Football'  : {'pinnacle' : 'Football', 'wettpoint' : 'football', 'scoreboard' : 'americanfootball'},
# 'Basketball': {'pinnacle' : 'Basketball', 'wettpoint' : 'basketball', 'scoreboard' : 'basketball'},
}

LEAGUES = {
   'Baseball' : {
        'MLB Spring Training' : {'pinnacle' : 'MLB Pre Seas', 'wettpoint' : 'MLB Pre Season', 'scoreboard' : 'MLB'},
        'MLB Regular Season' : {'pinnacle' : 'MLB', 'wettpoint' : 'MLB', 'scoreboard' : 'MLB'},
#         'NPB Regular Season' : {'pinnacle' : ['Japan CL', 'Japan PL']},
    },
    'Soccer' : {
#         'MLS Regular Season' : {'pinnacle' : 'USA (MLS)', 'wettpoint' : 'Major League Soccer MLS', 'scoreboard' : 'MLS'},
        'Bundesliga' : {'pinnacle' : 'Bundesliga', 'wettpoint' : '1. Bundesliga', 'scoreboard' : 'BL'},
        'Premier League' : {'pinnacle' : 'Eng. Premier', 'wettpoint' : 'Premier League', 'scoreboard' : 'PR'},
        'La Liga' : {'pinnacle' : 'La Liga', 'wettpoint' : 'Primera Division', 'scoreboard' : 'PD'},
        'Serie A' : {'pinnacle' : 'Serie A', 'wettpoint' : 'Serie A', 'scoreboard' : 'A'},
    },
    'Handball' : {
        'Handball Bundesliga' : {'pinnacle' : 'GerBundes 3', 'wettpoint' : '1. Bundesliga', 'scoreboard' : 'germany/bundesliga-1/'},
    },
    'Football' : {
        'NFL' : {'pinnacle' : 'NFL', 'wettpoint' : 'NFL', 'scoreboard' : 'NFL'},
    },
    'Hockey' : {
#         'NHL' : {},
        'KHL' : {'pinnacle' : 'Russia KHL 3', 'wettpoint' : 'Continental League', 'scoreboard' : 'KHL'},
#         'SEL' : {'pinnacle' : 'Swed Elits 3', 'wettpoint' : 'Elitserien', 'scoreboard' : ''},
#         'SM-Liiga' : {'pinnacle' : 'Finland SM 3', 'wettpoint' : 'SM Liga', 'scoreboard' : ''},
    },
#     'Basketball' : {
#         'NBA' : {},
#         'NCAAB' : {},
#     },
}

# use pinnacle sports xml feed as our official game list feed
PINNACLE_FEED = 'pinnaclesports.com'
WETTPOINT_FEED = 'wettpoint.com'
# TSN_FEED = 'http://www.tsn.ca/'
XSCORES_FEED = 'xscores.com'
BACKUP_SCORES_FEED = 'scorespro.com'

def get_header():
    header = {}
    
    user_agents = [
                   # FIREFOX 31.0
                   'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:31.0) Gecko/20100101 Firefox/31.0',
                   'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:31.0) Gecko/20100101 Firefox/31.0',
                   'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:31.0) Gecko/20100101 Firefox/31.0',
                   # SAFARI 7.0
                   'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.77.4 (KHTML, like Gecko) Version/7.0.5 Safari/537.77.4',
                   # CHROME 36.0
                   'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36',
                   'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36',
                   'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36',
                   'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36',
                   # IE 11.0
                   'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
                   'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
                   ]
    
    header['User-Agent'] = random.choice(user_agents)
    header['Accept-Encoding'] = 'gzip, deflate'
    
    return header