#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import logging

TEAMS = {
# keys are pinnacle team names
# values are corresponding aliases
# value keys are wettpoint team ids if they exist
    'Baseball' : {
        'MLB Spring Training' : 'MLB',
        'MLB' : {
            'keys' : {
                      # AL East
                     'Baltimore Orioles'         : '01',
                     'Boston Red Sox'            : '02',
                     'New York Yankees'          : '10',
                     'Tampa Bay Rays'            : '13',
                     'Toronto Blue Jays'         : '15',
                     # AL Central
                     'Chicago White Sox'         : '03',
                     'Cleveland Indians'         : '04',
                     'Detroit Tigers'            : '05',
                     'Kansas City Royals'        : '07',
                     'Minnesota Twins'           : '09',
                     # AL West
                     'Houston Astros'            : '06',
                     'LAA Angels'                : '08',
                     'Oakland Athletics'         : '11',
                     'Seattle Mariners'          : '12',
                     'Texas Rangers'             : '14',
                     # NL East
                     'Atlanta Braves'            : '17',
                     'Miami Marlins'             : '22',
                     'New York Mets'             : '24',
                     'Philadelphia Phillies'     : '25',
                     'Washington Nationals'      : '30',
                     # NL Central
                     'Chicago Cubs'              : '18',
                     'Cincinnati Reds'           : '19',
                     'Milwaukee Brewers'         : '23',
                     'Pittsburgh Pirates'        : '26',
                     'St. Louis Cardinals'       : '29',
                     # NL West
                     'Arizona Diamondbacks'      : '16',
                     'Colorado Rockies'          : '20',
                     'Los Angeles Dodgers'       : '21',
                     'San Diego Padres'          : '27',
                     'San Francisco Giants'      : '28',
                },
            'values' : {
                     # AL East
                     '01' :         ['BAL ORIOLES'],
                     '02' :         ['BOS RED SOX'],
                     '10' :         ['NY YANKEES'],
                     '13' :         ['TB RAYS'],
                     '15' :         ['TOR BLUE JAYS'],
                     # AL Central
                     '03' :         ['CHI WHITE SOX'],
                     '04' :         ['CLE INDIANS'],
                     '05' :         ['DET TIGERS'],
                     '07' :         ['KC ROYALS'],
                     '09' :         ['MIN TWINS'],
                     # AL West
                     '06' :         ['HOU ASTROS'],
                     '08' :         ['Los Angeles Angels', 'ANA ANGELS'],
                     '11' :         ['OAK ATHLETICS'],
                     '12' :         ['SEA MARINERS'],
                     '14' :         ['TEX RANGERS'],
                     # NL East
                     '17' :         ['ATL BRAVES'],
                     '22' :         ['MIA MARLINS'],
                     '24' :         ['NY METS'],
                     '25' :         ['PHI PHILLIES'],
                     '30' :         ['WAS NATIONALS'],
                     # NL Central
                     '18' :         ['CHI CUBS'],
                     '19' :         ['CIN REDS'],
                     '23' :         ['MIL BREWERS'],
                     '26' :         ['PIT PIRATES'],
                     '29' :         ['STL CARDINALS'],
                     # NL West
                     '16' :         ['ARI DIAMONDBACKS'],
                     '20' :         ['COL ROCKIES'],
                     '21' :         ['LA DODGERS'],
                     '27' :         ['SD PADRES'],
                     '28' :         ['SF GIANTS'],
                },
        },
    },
    'Soccer' : {
        'MLS Regular Season' : {
            'keys' : {
                      # Eastern Conference
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
                      # Western Conference
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
                        # Eastern Conference
                        '76607'                 : ['DC United'],
                        '76601'                 : ['NEW ENG. REVOLUTION'],
                        # Western Conference
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
                        '809'                   : ['Bayern München', 'BAYERN MUNICH'],
                        '821'                   : ['FC SCHALKE 04'],
                        '811'                   : ['Borussia Mönchengladbach', 'BOR. MONCHENGLADBACH'],
                        '1900'                  : ['FSV Mainz'],
                        '16732'                 : ['FC Augsburg'],
                        '16740'                 : ['TSG 1899 Hoffenheim', '1899 HOFFENHEIM'],
                        '816'                   : ['Sport-Club Freiburg'],
                        '813'                   : ['FC Köln', 'FC KOLN'],
            },
        },
        'Premier League' : {
            'keys' : {
                      'Arsenal'             : '3',
                      'Aston Villa'         : '18',
                      'Burnley'             : '978',
                      'Chelsea'             : '4',
                      'Crystal Palace'      : '981',
                      'Everton'             : '12',
                      'Hull City'           : '1030',
                      'Leicester City'      : '13',
                      'Liverpool'           : '19',
                      'Manchester City'     : '984',
                      'Manchester United'   : '22',
                      'Newcastle United'    : '8',
                      'Queens Park Rangers' : '1015',
                      'Southampton'         : '15',
                      'Stoke City'          : '1017',
                      'Sunderland'          : '14',
                      'Swansea City'        : '1044',
                      'Tottenham Hotspur'   : '21',
                      'W.B.A'               : '996',
                      'West Ham United'     : '11',
            },
            'values' : {
                        '13'    : ['LEICESTER'],
                        '21'    : ['TOTTENHAM'],
                        '1044'  : ['SWANSEA'],
                        '22'    : ['MANCHESTER UTD'],
                        '8'     : ['NEWCASTLE'],
                        '1015'  : ['QPR'],
                        '996'   : ['West Bromwich Albion', 'WEST BROM'],
                        '11'    : ['WEST HAM'],
            },
        },
        'La Liga' : {
            'keys' : {
                      'Almeria'             : '14925',
                      'Athletic Bilbao'     : '746',
                      'Atletico Madrid'     : '1668',
                      'Barcelona'           : '747',
                      'Celta Vigo'          : '748',
                      'Cordoba'             : '1670',
                      'Deportivo La Coruna' : '749',
                      'Eibar'               : '1679',
                      'Elche'               : '1683',
                      'Getafe'              : '14923',
                      'Granada'             : '158258',
                      'Levante'             : '1667',
                      'Malaga'              : '752',
                      'Rayo Vallecano'      : '755',
                      'RCD Espanyol'        : '750',
                      'Real Madrid'         : '757',
                      'Real Sociedad'       : '758',
                      'Sevilla'             : '761',
                      'Valencia'            : '763',
                      'Villarreal'          : '764',
            },
            'values' : {
                        '14925' : ['Almería'],
                        '746'   : ['ATHLETIC CLUB'],
                        '1668'  : ['Atlético Madrid', 'ATL. MADRID'],
                        '747'   : ['FC Barcelona'],
                        '748'   : ['Celta'],
                        '1670'  : ['Córdoba'],
                        '749'   : ['Deportivo La Coruña', 'DEP. LA CORUNA'],
                        '158258': ['GRANADA CF'],
                        '752'   : ['Málaga'],
                        '750'   : ['Espanyol'],
            },
        },
        'Serie A' : {
            'keys' : {
                      'AC Milan'            : '728',
                      'AS Roma'             : '732',
                      'Atalanta'            : '719',
                      'Cagliari'            : '1049',
                      'Cesena'              : '83359',
                      'Chievo'              : '722',
                      'Empoli'              : '1055',
                      'Fiorentina'          : '723',
                      'Genoa'               : '1057',
                      'Hellas Verona'       : '736',
                      'Inter Milan'         : '724',
                      'Juventus'            : '725',
                      'Lazio'               : '726',
                      'Napoli'              : '1058',
                      'Palermo'             : '1056',
                      'Parma'               : '729',
                      'Sampdoria'           : '1062',
                      'Sassuolo'            : '134312',
                      'Torino'              : '733',
                      'Udinese'             : '734',
            },
            'values' : {
                        '732'   : ['ROMA'],
                        '724'   : ['Inter'],
                        '736'   : ['VERONA'],
            },
        },
    },
    'Handball' : {
        'Handball Bundesliga' : {
            'keys' : {
                      'SG Flensburg-Handewitt'  : '6608',
                      'Frisch auf Goppingen'    : '6614',
                      'VfL Gummersbach'         : '6621',
                      'HSV Hamburg'             : '23447',
                      'THW Kiel'                : '6607',
                      'Rhein-Neckar Lowen'      : '158007',
                      'TBV Lemgo'               : '6606',
                      'TuS N-Lubbecke'          : '23448',
                      'SC Magdeburg'            : '6609',
                      'MT Melsungen'            : '106062',
                      'HSG Wetzlar'             : '6617',
                      'Fuchse Berlin'           : '158008',
                      'TSV Hannover-Burgdorf'   : '207688',
                      'HBW Balingen-Weilstetten': '132814',
                      'SG BBM Bietigheim'       : '215171',
                      'TSG Friesenheim'         : '215159',
                      'Bergischer HC'           : '215165',
                      'HC Erlangen'             : '215169',
                      'TSV GWD Minden'          : '6613',
            },
            'values' : {
                        '6608'                  : ['Flensburg-Handewitt'],
                        '6614'                  : ['FA Göppingen', 'FA Goppingen'],
                        '6621'                  : ['Gummersbach'],
                        '23447'                 : ['Hamburg', 'HSV Handball'],
                        '6607'                  : ['Kiel'],
                        '158007'                : ['Rhein-Neckar Löwen', 'Rhein-Neckar-Löwen', 'Rhein-Neckar Loewen'],
                        '6606'                  : ['Lemgo'],
                        '23448'                 : ['TuS N-Lübbecke', 'TuS-N-Lubbecke', 'N-Lubbecke'],
                        '6609'                  : ['Magdeburg'],
                        '6617'                  : ['Wetzlar'],
                        '158008'                : ['Füchse Berlin'],
                        '132814'                : ['HBW Balingen/Weilstetten', 'Balingen-Weilsteten', 'Balingen/Weilstetten'],
                        '215171'                : ['BBM Bietigheim'],
                        '215159'                : ['TSG Lu.-Friesenheim', 'TSG Ludwigshafen-Friesenheim'],
                        '215169'                : ['Erlangen'],
                        '6613'                  : ['GWD Minden', 'Minden-Hannover', 'Minden'],
            },
        },
    },
    'Football' : {
        'NFL' : {
            'keys' : {
                      # AFC North
                      'Baltimore Ravens'        : '03',
                      'Cincinnati Bengals'      : '07',
                      'Cleveland Browns'        : '08',
                      'Pittsburgh Steelers'     : '25',
                      # AFC South
                      'Houston Texans'          : '13',
                      'Indianapolis Colts'      : '14',
                      'Jacksonville Jaguars'    : '15',
                      'Tennessee Titans'        : '31',
                      # AFC East
                      'Buffalo Bills'           : '04',
                      'Miami Dolphins'          : '17',
                      'New England Patriots'    : '19',
                      'New York Jets'           : '22',
                      # AFC West
                      'Denver Broncos'          : '10',
                      'Kansas City Chiefs'      : '16',
                      'Oakland Raiders'         : '23',
                      'San Diego Chargers'      : '26',
                      # NFC North
                      'Chicago Bears'           : '06',
                      'Detroit Lions'           : '11',
                      'Green Bay Packers'       : '12',
                      'Minnesota Vikings'       : '18',
                      # NFC South
                      'Atlanta Falcons'         : '02',
                      'Carolina Panthers'       : '05',
                      'New Orleans Saints'      : '20',
                      'Tampa Bay Buccaneers'    : '30',
                      # NFC East
                      'Dallas Cowboys'          : '09',
                      'New York Giants'         : '21',
                      'Philadelphia Eagles'     : '24',
                      'Washington Redskins'     : '32',
                      # NFC West
                      'Arizona Cardinals'       : '01',
                      'San Francisco 49ers'     : '27',
                      'Seattle Seahawks'        : '28',
                      'St. Louis Rams'          : '29',
            },
            'values' : {
                        # AFC North
                        '03'                    : ['BAL RAVENS'],
                        '07'                    : ['CIN BENGALS'],
                        '08'                    : ['CLE BROWNS'],
                        '25'                    : ['PIT STEELERS'],
                        # AFC South
                        '13'                    : ['HOU TEXANS'],
                        '14'                    : ['IND COLTS'],
                        '15'                    : ['JAC JAGUARS'],
                        '31'                    : ['TEN TITANS'],
                        # AFC East
                        '04'                    : ['BUF BILLS'],
                        '17'                    : ['MIA DOLPHINS'],
                        '19'                    : ['NE PATRIOTS'],
                        '22'                    : ['NY JETS'],
                        # AFC West
                        '10'                    : ['DEN BRONCOS'],
                        '16'                    : ['KC CHIEFS'],
                        '23'                    : ['OAK RAIDERS'],
                        '26'                    : ['SD CHARGERS'],
                        # NFC North
                        '06'                    : ['CHI BEARS'],
                        '11'                    : ['DET LIONS'],
                        '12'                    : ['GB PACKERS'],
                        '18'                    : ['MIN VIKINGS'],
                        # NFC South
                        '02'                    : ['ATL FALCONS'],
                        '05'                    : ['CAR PANTHERS'],
                        '20'                    : ['NO SAINTS'],
                        '30'                    : ['TB BUCCANEERS'],
                        # NFC East
                        '09'                    : ['DAL COWBOYS'],
                        '21'                    : ['NY GIANTS'],
                        '24'                    : ['PHI EAGLES'],
                        '32'                    : ['WAS REDSKINS'],
                        # NFC West
                        '01'                    : ['ARI CARDINALS'],
                        '27'                    : ['SF 49ers'],
                        '28'                    : ['SEA SEAHAWKS'],
                        '29'                    : ['STL RAMS'],
            },
        },
    },
    'Hockey' : {
        'NHL' : {
            'keys' : {
                      # Atlantic division
                      'Boston Bruins'           : '5540',
                      'Buffalo Sabres'          : '5541',
                      'Detroit Red Wings'       : '5552',
                      'Florida Panthers'        : '5547',
                      'Montreal Canadiens'      : '5542',
                      'Ottawa Senators'         : '5543',
                      'Tampa Bay Lightning'     : '5548',
                      'Toronto Maple Leafs'     : '5544',
                      # Metropolitan division
                      'Carolina Hurricanes'     : '5546',
                      'Columbus Blue Jackets'   : '5551',
                      'New Jersey Devils'       : '5535',
                      'New York Islanders'      : '5536',
                      'New York Rangers'        : '5537',
                      'Philadelphia Flyers'     : '5538',
                      'Pittsburgh Penguins'     : '5539',
                      'Washington Capitals'     : '5549',
                      # Central division
                      'Chicago Blackhawks'      : '5550',
                      'Colorado Avalanche'      : '5556',
                      'Dallas Stars'            : '5561',
                      'Minnesota Wild'          : '5558',
                      'Nashville Predators'     : '5553',
                      'St Louis Blues'          : '5554',
                      'Winnipeg Jets'           : '5545',
                      # Pacific division
                      'Anaheim Ducks'           : '5560',
                      'Arizona Coyotes'         : '5563',
                      'Calgary Flames'          : '5555',
                      'Edmonton Oilers'         : '5557',
                      'Los Angeles Kings'       : '5562',
                      'San Jose Sharks'         : '5564',
                      'Vancouver Canucks'       : '5559',
            },
            'values' : {
                        # Atlantic division
                        '5540'  : ['BOS BRUINS'],
                        '5541'  : ['BUF SABRES'],
                        '5552'  : ['DET RED WINGS'],
                        '5547'  : ['FLO PANTHERS'],
                        '5542'  : ['MON CANADIENS'],
                        '5543'  : ['OTT SENATORS'],
                        '5548'  : ['TB LIGHTNING'],
                        '5544'  : ['TOR MAPLE LEAFS'],
                        # Metropolitan division
                        '5546'  : ['CAR HURRICANES'],
                        '5551'  : ['COB BLUE JACKETS'],
                        '5535'  : ['NJ DEVILS'],
                        '5536'  : ['NY ISLANDERS'],
                        '5537'  : ['NY RANGERS'],
                        '5538'  : ['PHI FLYERS'],
                        '5539'  : ['PIT PENGUINS'],
                        '5549'  : ['WAS CAPITALS'],
                        # Central division
                        '5550'  : ['CHI BLACKHAWKS'],
                        '5556'  : ['COL AVALANCHE'],
                        '5561'  : ['DAL STARS'],
                        '5558'  : ['MIN WILD'],
                        '5553'  : ['NAS PREDATORS'],
                        '5554'  : ['St. Louis Blues', 'STL BLUES'],
                        '5545'  : ['WIN JETS'],
                        # Pacific division
                        '5560'  : ['ANA DUCKS'],
                        '5563'  : ['ARI COYOTES'],
                        '5555'  : ['CAL FLAMES'],
                        '5557'  : ['EDM OILERS'],
                        '5562'  : ['LA KINGS'],
                        '5564'  : ['SJ SHARKS'],
                        '5559'  : ['VAN CANUCKS'],
            },
         },
        'KHL' : {
            'keys' : {
                      # Bobrov divison
                      'Atlant'                      : '174550',
                      'Dinamo Minsk'                : '174553',
                      'Dinamo Riga'                 : '174549',
                      'Jokerit'                     : '4649',
                      'Medvescak Zagreb'            : '205839', #change datatstore
                      'SKA St Petersburg'           : '99847',
                      'Slovan Bratislava'           : '134210',
                      # Tarasov division
                      'Vityaz Chehov'               : '106361',
                      'Dynamo Moscow'               : '99836',
                      'Lokomotiv Yaroslavl'         : '99840',
                      'Severstal Cherepovec'        : '99842',
                      'Torpedo NN'                  : '152909',
                      'HC Sochi'                    : '324041',
                      'CSKA Moscow'                 : '99846',
                      # Kharlamov division
                      'Avtomobilist'                : '174552',
                      'Ak Bars Kazan'               : '99839',
                      'Lada Togliatti'              : '99837',
                      'Metallurg Magnitogorsk'      : '99838',
                      'Neftekhimik Nizhnekamsk'     : '99843',
                      'Traktor Chelyabinsk'         : '132276', # change datastore
                      'Yugra'                       : '216748',
                      # Chernyshev division
                      'Avangard Omsk'               : '99844',
                      'Admiral'                     : '300725',
                      'Amur Khabarovsk'             : '132277',
                      'Barys Astana'                : '174551',
                      'Metallurg Novokuznetsk'      : '99841',
                      'Salavat Ufa'                 : '99848',
                      'Sibir Novosibirsk'           : '99850',
            },
            'values' : {
                        # Bobrov divison
                        '174550'    : ['Atlant Mytischi', 'ATLANT MSK.'],
                        '174553'    : ['Dynamo Minsk', 'DINAMO MN.'],
                        '174549'    : ['Dynamo Riga', 'DINAMO R.'],
                        '4649'      : ['Jokerit Helsinki'],
                        '205839'    : ['KHL Medvescak Zagreb', 'KHL MEDVESCAK Z.', 'KHL Medvescak'],
                        '99847'     : ['SKA St. Petersburg', 'SKA S.PETERSBURG'],
                        '134210'    : ['HC Slovan Bratislava', 'HC SL. BRATISLAVA'],
                        # Tarasov division
                        '106361'    : ['Vityaz Podolsk Chekhov', 'VITYAZ', 'Vitiaz Chehov', 'HC Vityaz'],
                        '99836'     : ['Dynamo Moskva', 'DYNAMO MSK.', 'Dinamo Moscow'],
                        '99840'     : ['LOKOMOTIV'],
                        '99842'     : ['Severstal Cherepovets', 'SEVERSTAL'],
                        '152909'    : ['Torpedo Novgorod', 'TORPEDO', 'Nizhny Novgorod'],
                        '324041'    : ['Sochi'],
                        '99846'     : ['CSKA Moskva', 'CSKA MSK.'],
                        # Kharlamov division
                        '174552'    : ['Avtomobilist Yekaterinburg', 'AVTOMOBILIST EK.'],
                        '99839'     : ['AK BARS', 'Bars Kazan'],
                        '99837'     : ['LADA T.'],
                        '99838'     : ['METALLURG MG', 'Magnitogorsk'],
                        '99843'     : ['NEFTEKHIMIK'],
                        '132276'    : ['Traktor Chel', 'TRAKTOR', 'Tractor'],
                        '216748'    : ['Yugra Khanty-Mansiysk', 'HC YUGRA', 'Ugra', 'HC Ugra'],
                        # Chernyshev division
                        '99844'     : ['AVANGARD'],
                        '300725'    : ['Admiral Vladivostok', 'ADMIRAL VL.', 'Vladivostok'],
                        '132277'    : ['HC Amur', 'AMUR'],
                        '174551'    : ['BARYS A.', 'HC Barys Astana'],
                        '99841'     : ['METALLURG NK', 'Novokuznetsk'],
                        '99848'     : ['Salavat Yulaev Ufa', 'SALAVAT Y.'],
                        '99850'     : ['SIBIR N.'],
            },
        },
        'Czech Extraliga' : {
            'keys' : {
                      'HC Vitkovice Steel'              : '100307',
                      'Mountfield HK'                   : '159227',
                      'PSG Zlin'                        : '159229',
                      'BK Mlada Boleslav'               : '174556',
                      'HC Verva Litvinov'               : '100315',
                      'HC Energie Karlovy Vary'         : '100318',
                      'HC Bili Tygri Liberec'           : '100311',
                      'HC Kometa Brno'                  : '204733',
                      'HC OLomouc'                      : '206137',
                      'HC Slavia Praha'                 : '100317',
                      'HC Sparta Praha'                 : '100310',
                      'HC Skoda Plzen'                  : '100314',
                      'HC Ocelari Trinec'               : '100319',
                      'HC CSOB Poistovna Pardubice'     : '100309',
            },
            'values' : {
                        '100307'    : ['Vitkovice Steel'],
                        '159227'    : ['HC Mountfield', 'Hradec Kralove', 'HC Mountfield HK'],
                        '100315'    : ['HC Litvinov', 'HC V LITVINOV', 'HC Benzina Litvinov'],
                        '100318'    : ['HC E KARLOVY VARY', 'HC Energie Karlove Vary', 'HC Karlovy Vary'],
                        '100311'    : ['Bili Tygri Liberec', 'BT LIBEREC', 'HC Liberec'],
                        '100319'    : ['HC O TRINEC', 'HC Trinec', 'Trinec'],
                        '100309'    : ['HC CSOB PARDUBICE', 'HC CSOB Pojistovna Pardubice', 'HC Pardubice'],
                        '100310'    : ['HC Sparta Prague'],
                        '100314'    : ['HC S. PLZEN', 'HC Plzen', 'HC Škoda Plzen'],
                        '174556'    : ['HC Mlada Boleslav', 'HK Mlada Boleslav'],
                        '100317'    : ['HC Slavia Prague'],
            },
        },
        'Finnish Elite League' : {
            'keys' : {
                      'Karpat'      : '4651',
                      'Tappara'     : '4655',
                      'HIFK'        : '4647',
                      'Blues'       : '4645',
                      'Lukko'       : '4652',
                      'Assat'       : '4657',
                      'Ilves'       : '4646',
                      'JYP'         : '4650',
                      'Sport'       : '6441',
                      'KalPa'       : '6436',
                      'SaiPa'       : '4654',
                      'Pelicans'    : '4653',
                      'HPK'         : '4648',
                      'TPS'         : '4656',
            },
            'values' : {
                        '4651'  : ['Kärpät'],
                        '4647'  : ['IFK Helsinki'],
                        '4654'  : ['Salpa'],
                        '4657'  : ['Ässät'],
                        '4650'  : ['Jyvaskyla'],
                        '6441'  : ['Vaasan Sport', 'Sport Vaasa'],
                        '6436'  : ['KaIPa'],
            },
        },
        'SEL' : {
            'keys' : {
                      'Lulea HF'        : '5097',
                      'Skelleftea AIK'  : '5408',
                      'Leksands IF'     : '5417',
                      'Farjestads BK'   : '5093',
                      'MODO Hockey'     : '5101',
                      'Orebro HK'       : '5414',
                      'Vaxjo Lakers HC' : '79527',
                      'HV 71'           : '5094',
                      'Frolunda HC'     : '5107',
                      'Brynas IF'       : '5091',
                      'Linkopings HC'   : '5096',
                      'Djurgardens IF'  : '5092',
            },
            'values' : {
                        '5097'  : ['Luleå HF'],
                        '5408'  : ['Skellefteå AIK'],
                        '5417'  : ['Leksand'],
                        '5093'  : ['Färjestads BK'],
                        '5414'  : ['Örebro HK'],
                        '79527' : ['Växjö Lakers HC'],
                        '5107'  : ['Frölunda HC'],
                        '5091'  : ['Brynäs IF'],
                        '5096'  : ['Linköpings HC'],
                        '5092'  : ['Djurgårdens IF'],
            },
        },
    },
    'Basketball' : {
        'NBA Preseason' : 'NBA',
        'NBA' : {
            'keys' : {
                      # Atlantic
                      'Boston Celtics'          : '14979',
                      'Brooklyn Nets'           : '14981',
                      'New York Knicks'         : '14982',
                      'Philadelphia 76ers'      : '14984',
                      'Toronto Raptors'         : '14993',
                      # Central
                      'Chicago Bulls'           : '14987',
                      'Cleveland Cavaliers'     : '14988',
                      'Detroit Pistons'         : '14989',
                      'Indiana Pacers'          : '14990',
                      'Milwaukee Bucks'         : '14991',
                      # Southeast
                      'Atlanta Hawks'           : '14986',
                      'Charlotte Hornets'       : '95396',
                      'Miami Heat'              : '14980',
                      'Orlando Magic'           : '14983',
                      'Washington Wizards'      : '14985',
                      # Southwest
                      'Dallas Mavericks'        : '14994',
                      'Houston Rockets'         : '14996',
                      'Memphis Grizzlies'       : '14998',
                      'New Orleans Pelicans'    : '14992',
                      'San Antonio Spurs'       : '15000',
                      # Northwest
                      'Denver Nuggets'          : '14995',
                      'Minnesota Timberwolves'  : '14999',
                      'Oklahoma City Thunder'   : '184586',
                      'Portland Trail Blazers'  : '15006',
                      'Utah Jazz'               : '15001',
                      # Pacific
                      'Golden State Warriors'   : '15002',
                      'Los Angeles Clippers'    : '15003',
                      'Los Angeles Lakers'      : '15004',
                      'Phoenix Suns'            : '15005',
                      'Sacramento Kings'        : '15007',
            },
            'values' : {
                        # Atlantic
                        '14979'     : ['BOS CELTICS'],
                        '14981'     : ['BKN NETS'],
                        '14982'     : ['NY KNICKS'],
                        '14984'     : ['PHI 76ers'],
                        '14993'     : ['TOR RAPTORS'],
                        # Central
                        '14987'     : ['CHI BULLS'],
                        '14988'     : ['CLE CAVALIERS'],
                        '14989'     : ['DET PISTONS'],
                        '14990'     : ['IND PACERS'],
                        '14991'     : ['MIL BUCKS'],
                        # Southeast
                        '14986'     : ['ATL HAWKS'],
                        '95396'     : ['CHA HORNETS', 'Charlotte Bobcats'],
                        '14980'     : ['MIA HEAT'],
                        '14983'     : ['ORL MAGIC'],
                        '14985'     : ['WAS WIZARDS'],
                        # Southwest
                        '14994'     : ['DAL MAVERICKS'],
                        '14996'     : ['HOU ROCKETS'],
                        '14998'     : ['MEM GRIZZLIES'],
                        '14992'     : ['NO PELICANS', 'New Orleans Hornets'],
                        '15000'     : ['SA SPURS'],
                        # Northwest
                        '14995'     : ['DEN NUGGETS'],
                        '14999'     : ['MIN TIMBERWOLVES'],
                        '184586'    : ['OKC THUNDER'],
                        '15006'     : ['POR T BLAZERS'],
                        '15001'     : ['UTA JAZZ'],
                        # Pacific
                        '15002'     : ['GS WARRIORS'],
                        '15003'     : ['L.A. Clippers', 'LA CLIPPERS'],
                        '15004'     : ['L.A. Lakers', 'LA LAKERS'],
                        '15005'     : ['PHO SUNS'],
                        '15007'     : ['SAC KINGS'],
            },
        },
    },
}

def get_team_aliases(sport, league, team_name):
    # remove the game digit to get correct team name aliases
    doubleheader_search = re.search('^G\d+\s+(.+)', team_name)
    if doubleheader_search:
        team_name = doubleheader_search.group(1).strip()
        
    OTB_search = re.search('^OTB\s+(.+)', team_name)
    if OTB_search:
        team_name = OTB_search.group(1).strip()
    
    team_aliases = [team_name]
    
    if sport not in TEAMS or league not in TEAMS[sport]:
        logging.warning(league+' for '+sport+' has no team information (1)!')
        return team_aliases, None
    
    league_team_info = TEAMS[sport][league]
    if isinstance(league_team_info, basestring):
        # reference to another league information
        league_team_info = TEAMS[sport][league_team_info]
    
    if (
        'keys' not in league_team_info 
        or 'values' not in league_team_info 
        ):
        logging.warning(league+' for '+sport+' has no team information (2)!')
        return team_aliases, None
    
    # get all team aliases
    team_id = None
    if team_name in league_team_info['keys']:
        team_id = league_team_info['keys'][team_name]
        if team_id in league_team_info['values']:
            team_aliases += league_team_info['values'][team_id]
    else:
        logging.warning(team_name+' in '+league+' for '+sport+' has no team id!')
        
    return team_aliases, team_id