# LEGACY FUNCTION        
#     def fill_scores_tsn(self):
#         for sport_key, sport_leagues in constants.LEAGUES.iteritems():
#             for league_key, values in sport_leagues.iteritems():
#                 if isinstance(league_key, list):
#                     query = Tip.gql('WHERE elapsed = True AND archived != True AND game_league IN (:1)', ', '.join(league_key))
#                 else:
#                     query = Tip.gql('WHERE elapsed = True AND archived != True AND game_league = :1', league_key)
#                 
#                 league = values['tsn']
#                 feed_url = constants.TSN_FEED + league + '/scores'
#                 
#                 boxscores_by_date = {}
#                 archived_boxscores_by_date = {}
#                 
#                 global_tip_key = {}
#                 
#                 for tip in itertools.chain(query.run(), self.PPDCHECK):
#                     if tip.key() in self.DATASTORE_TIPS:
#                         tip = self.DATASTORE_TIPS[tip.key()]
#                         
#                     game_digit = re.search('^G(\d)\s+', tip.game_team_away)
#                     if game_digit:
#                         game_digit = game_digit.group(1)
#                     else:
#                         game_digit = False
#                     
#                     if game_digit != False:
#                         tip.game_team_away = re.sub('^G\d\s+', '', tip.game_team_away)
#                         tip.game_team_home = re.sub('^G\d\s+', '', tip.game_team_home)
#                         if tip.wettpoint_tip_team:
#                             tip.wettpoint_tip_team = re.sub('^G\d\s+', '', tip.wettpoint_tip_team)
#                         game_digit = int(game_digit)
#                         
#                     tsn_game_time = tip.date - datetime.timedelta(hours = 4)
#                     tsn_game_time = tsn_game_time.strftime('%B/%d/%Y').replace('/0','/')
#                     
#                     if tip.game_team_away.split(' ')[0].lower() == 'away' and tip.game_team_home.split(' ')[0].lower() == 'home':
#                         global_tip_key[tsn_game_time] = tip.key()
#                         self.DATASTORE_TIPS[tip.key()] = tip
#                         continue
#                         
#                     if tsn_game_time in boxscores_by_date:
#                         boxscores = boxscores_by_date[tsn_game_time]
#                     else:
#                         self.REQUEST_COUNT[constants.TSN_FEED] += 1
#                         
#                         feed = feed_url + '/?date=' + tsn_game_time
#                         feed_request = urllib2.Request(feed, headers=constants.HEADER)
#                         feed_html = urllib2.urlopen(feed_request)
#                         soup = BeautifulSoup(feed_html)
#                         boxscores = soup.find('div', {'id' : 'tsnMain'}).find_all('table', {'class' : 'boxScore'})
#                         boxscores_by_date[tsn_game_time] = boxscores
#                         
#                     index = 0
#                     for boxscore in boxscores:
#                         rows = boxscore.find_all('tr')
#                         
#                         if not 'final' in rows[0].find('th').get_text().lower() and not 'ppd' in rows[0].find('th').get_text().lower() and not 'cancelled' in rows[0].find('th').get_text().lower() and not 'suspended' in rows[0].find('th').get_text().lower():
#                             continue
#                         
#                         away_row = rows[1]
#                         home_row = rows[2]
#                         
#                         boxscore_away_team = away_row.find('td').find('a').get_text().strip()
#                         boxscore_home_team = home_row.find('td').find('a').get_text().strip()
#                         
#                         if boxscore_away_team.split(' ')[0].lower() == tip.game_team_away.split(' ')[0].lower() or boxscore_away_team.split(' ')[-1].lower() == tip.game_team_away.split(' ')[-1].lower():
#                             if boxscore_home_team.split(' ')[0].lower() == tip.game_team_home.split(' ')[0].lower() or boxscore_home_team.split(' ')[-1].lower() == tip.game_team_home.split(' ')[-1].lower():
#                                 if game_digit != False and game_digit > 1:
#                                     temp_bs_count = 0
#                                     
#                                     if index > 0:
#                                         for temp_boxscore in boxscores[0:(index-1)]:
#                                             temp_rows = temp_boxscore.find_all('tr')
#                                             
#                                             if temp_rows[1].find('td').find('a').get_text().strip() == boxscore_away_team and temp_rows[2].find('td').find('a').get_text().strip() == boxscore_home_team:
#                                                 temp_bs_count += 1
#                                     
#                                     if tsn_game_time in archived_boxscores_by_date:
#                                         for temp_boxscore in archived_boxscores_by_date[tsn_game_time]:
#                                             temp_rows = temp_boxscore.find_all('tr')
#                                             
#                                             if temp_rows[1].find('td').find('a').get_text().strip() == boxscore_away_team and temp_rows[2].find('td').find('a').get_text().strip() == boxscore_home_team:
#                                                 temp_bs_count += 1
#                                     
#                                     if temp_bs_count != (game_digit - 1):
#                                         index += 1
#                                         continue
#                                 
#                                 if 'ppd' in rows[0].find('th').get_text().lower() or 'cancelled' in rows[0].find('th').get_text().lower() or 'suspended' in rows[0].find('th').get_text().lower():
#                                     tip.score_away = '0'
#                                     tip.score_home = '0'
#                                 else:
#                                     away_columns = away_row.find_all('td')
#                                     home_columns = home_row.find_all('td')
#                                     
#                                     for column in away_columns:
#                                         if column.b:
#                                             tip.score_away = column.b.get_text().strip()
#                                             break
#                                     
#                                     for column in home_columns:
#                                         if column.b:
#                                             tip.score_home = column.b.get_text().strip()
#                                             break
#                                 
#                                 tip.archived = True
#                                 
#                                 if not tsn_game_time in archived_boxscores_by_date:
#                                     archived_boxscores_by_date[tsn_game_time] = []
#                                 
#                                 archived_boxscores_by_date[tsn_game_time].append(boxscores[index])
#                                 del boxscores[index]
#                                 
#                                 self.DATASTORE_TIPS[tip.key()] = tip
#                                 break
#                                 
#                         index += 1
#                 
#                 for i, j in global_tip_key.iteritems():
#                     global_tip = self.DATASTORE_TIPS[j]
#                     
#                     self.REQUEST_COUNT[constants.TSN_FEED] += 1
#                     
#                     tsn_game_time = i
#                     
#                     feed = feed_url + '/?date=' + tsn_game_time
#                     feed_request = urllib2.Request(feed, headers=constants.HEADER)
#                     feed_html = urllib2.urlopen(feed_request)
#                     soup = BeautifulSoup(feed_html)
#                     global_boxscores = soup.find('div', {'id' : 'tsnMain'}).find_all('table', {'class' : 'boxScore'})
#                     
#                     all_done = True
#                     
#                     away_count = 0
#                     home_count = 0
#                     
#                     for k in global_boxscores:
#                         rows = k.find_all('tr')
#                         
#                         if not 'final' in rows[0].find('th').get_text().lower() and not 'ppd' in rows[0].find('th').get_text().lower() and not 'cancelled' in rows[0].find('th').get_text().lower() and not 'suspended' in rows[0].find('th').get_text().lower():
#                             all_done = False
#                             break
#                         
#                         away_row = rows[1]
#                         home_row = rows[2]
#                         away_columns = away_row.find_all('td')
#                         home_columns = home_row.find_all('td')
#                         
#                         for column in away_columns:
#                             if column.b:
#                                 away_count += int(column.b.get_text().strip())
#                                 break
#                         
#                         for column in home_columns:
#                             if column.b:
#                                 home_count += int(column.b.get_text().strip())
#                                 break
#                     
#                     if all_done == True:
#                         global_tip.score_away = str(away_count)
#                         global_tip.score_home = str(home_count)
#                         
#                         global_tip.archived = True
#                         
#                         self.DATASTORE_TIPS[global_tip.key()] = global_tip