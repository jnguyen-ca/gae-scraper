HEADER = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:31.0) Gecko/20100101 Firefox/31.0', 'Accept-Encoding' : 'gzip, deflate'}

SPORTS = {
  'Baseball' : {'pinnacle' : 'Baseball', 'wettpoint' : 'baseball', 'scoreboard' : 'baseball'},
#   'Soccer' : {'pinnacle' : 'Soccer', 'wettpoint' : 'fussball', 'scoreboard' : 'soccer'},
}

LEAGUES = {
   'Baseball' : { 
        'MLB Spring Training' : {'pinnacle' : 'MLB Pre Seas', 'wettpoint' : 'MLB Pre Season', 'scoreboard' : 'MLB'},
        'MLB Regular Season' : {'pinnacle' : 'MLB', 'wettpoint' : 'MLB', 'scoreboard' : 'MLB'},
#         'NPB Regular Season' : {'pinnacle' : ['Japan CL', 'Japan PL']},
    },
#     'Soccer' : {
#         'MLS Regular Season' : {'pinnacle' : 'USA (MLS)', 'wettpoint' : 'Major League Soccer MLS', 'scoreboard' : 'MLS'},
#     },
}

# use pinnacle sports xml feed as our official game list feed
PINNACLE_FEED = 'pinnaclesports.com'
WETTPOINT_FEED = 'wettpoint.com'
# TSN_FEED = 'http://www.tsn.ca/'
SCOREBOARD_FEED = 'http://www.xscores.com'