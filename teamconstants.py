#usr/bin/python
# -*- coding: utf-8 -*-

TEAMS = {
# keys are pinnacle team names
# values are corresponding aliases
# value keys are wettpoint team ids if they exist
    'Baseball' : {
        'MLB Spring Training' : 'MLB Regular Season',
        'MLB Regular Season' : {
            'keys' : {
                     'Baltimore Orioles'         : '01',
                     'Boston Red Sox'            : '02',
                     'Chicago White Sox'         : '03',
                     'Cleveland Indians'         : '04',
                     'Detroit Tigers'            : '05',
                     'Houston Astros'            : '06',
                     'Kansas City Royals'        : '07',
                     'LAA Angels'                : '08',
                     'Minnesota Twins'           : '09',
                     'New York Yankees'          : '10',
                     'Oakland Athletics'         : '11',
                     'Seattle Mariners'          : '12',
                     'Tampa Bay Rays'            : '13',
                     'Texas Rangers'             : '14',
                     'Toronto Blue Jays'         : '15',
                     'Arizona Diamondbacks'      : '16',
                     'Atlanta Braves'            : '17',
                     'Chicago Cubs'              : '18',
                     'Cincinnati Reds'           : '19',
                     'Colorado Rockies'          : '20',
                     'Los Angeles Dodgers'       : '21',
                     'Miami Marlins'             : '22',
                     'Milwaukee Brewers'         : '23',
                     'New York Mets'             : '24',
                     'Philadelphia Phillies'     : '25',
                     'Pittsburgh Pirates'        : '26',
                     'San Diego Padres'          : '27',
                     'San Francisco Giants'      : '28',
                     'St. Louis Cardinals'       : '29',
                     'Washington Nationals'      : '30',
                },
            'values' : {
                     '01' :         ['BAL ORIOLES'],
                     '02' :         ['BOS RED SOX'],
                     '03' :         ['CHI WHITE SOX'],
                     '04' :         ['CLE INDIANS'],
                     '05' :         ['DET TIGERS'],
                     '06' :         ['HOU ASTROS'],
                     '07' :         ['KC ROYALS'],
                     '08' :         ['Los Angeles Angels', 'ANA ANGELS'],
                     '09' :         ['MIN TWINS'],
                     '10' :         ['NY YANKEES'],
                     '11' :         ['OAK ATHLETICS'],
                     '12' :         ['SEA MARINERS'],
                     '13' :         ['TB RAYS'],
                     '14' :         ['TEX RANGERS'],
                     '15' :         ['TOR BLUE JAYS'],
                     '16' :         ['ARI DIAMONDBACKS'],
                     '17' :         ['ATL BRAVES'],
                     '18' :         ['CHI CUBS'],
                     '19' :         ['CIN REDS'],
                     '20' :         ['COL ROCKIES'],
                     '21' :         ['LA DODGERS'],
                     '22' :         ['MIA MARLINS'],
                     '23' :         ['MIL BREWERS'],
                     '24' :         ['NY METS'],
                     '25' :         ['PHI PHILLIES'],
                     '26' :         ['PIT PIRATES'],
                     '27' :         ['SD PADRES'],
                     '28' :         ['SF GIANTS'],
                     '29' :         ['STL CARDINALS'],
                     '30' :         ['WAS NATIONALS'],
                },
        },
    },
    'Soccer' : {
        'MLS Regular Season' : {
            'keys' : {
                      'Chicago Fire'            : '76602',
                      'Columbus Crew'           : '76603',
                      'D.C. United'             : '76607',
                      'Houston Dynamo'          : '119742',
                      'New England Revolution'  : '76601',
                      'New York Red Bulls'      : '76605',
                      'Montreal Impact'         : '148693',
                      'Philadelphia Union'      : '224216',
                      'Sporting Kansas City'    : '76606',
                      'Toronto FC'              : '146416',
                      'Deportivo Chivas USA'    : '100985',
                      'Colorado Rapids'         : '76608',
                      'FC Dallas'               : '76600',
                      'LA Galaxy'               : '76604',
                      'Portland Timbers'        : '148694',
                      'Real Salt Lake'          : '100984',
                      'San Jose Earthquakes'    : '76609',
                      'Seattle Sounders FC'     : '148697',
                      'Vancouver Whitecaps'     : '148696',
            },
            'values' : {
                        '76607'                 : ['DC United'],
                        '76601'                 : ['NEW ENG. REVOLUTION'],
                        '100985'                : ['Chivas USA'],
                        '76604'                 : ['Los Angeles Galaxy'],
                        '148697'                : ['Seattle Sounders'],
            },
        },
        'Bundesliga' : {
            'keys' : {
                      'Bayern Munchen'          : '809',
                      'Borussia Dortmund'       : '810',
                      'Schalke 04'              : '821',
                      'Bayer Leverkusen'        : '808',
                      'VfL Wolfsburg'           : '824',
                      'Borussia Monchengladbach': '811',
                      'FSV Mainz 05'            : '1900',
                      'Augsburg'                : '16732',
                      'TSG Hoffenheim'          : '16740',
                      'Hannover 96'             : '1895',
                      'Hertha Berlin'           : '819',
                      'Werder Bremen'           : '823',
                      'Eintracht Frankfurt'     : '1888',
                      'SC Freiburg'             : '816',
                      'VfB Stuttgart'           : '822',
                      'Hamburger SV'            : '817',
                      'Koln'                    : '813',
                      'SC Paderborn 07'         : '16722',
            },
            'values' : {
                        '809'                   : ['Bayern M�nchen', 'BAYERN MUNICH'],
                        '821'                   : ['FC SCHALKE 04'],
                        '811'                   : ['Borussia M�nchengladbach', 'BOR. MONCHENGLADBACH'],
                        '1900'                  : ['FSV Mainz'],
                        '16732'                 : ['FC Augsburg'],
                        '16740'                 : ['TSG 1899 Hoffenheim', '1899 HOFFENHEIM'],
                        '816'                   : ['Sport-Club Freiburg'],
                        '813'                   : ['FC K�ln', 'FC KOLN'],
            },
        },
    },
}