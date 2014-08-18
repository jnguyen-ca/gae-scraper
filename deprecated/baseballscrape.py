#usr/bin/python
# -*- coding: utf-8 -*-

from imports import *
from scraper import Tip
import constants

class BaseballValues(db.Model):
    tip_key = db.StringProperty()
    
    pitcher_away = db.StringProperty()
    pitcher_home = db.StringProperty()
    
    pitching_change = db.BooleanProperty()
    
    away_gs = db.IntegerProperty()
    home_gs = db.IntegerProperty()
    
    away_whip = db.FloatProperty()
    home_whip = db.FloatProperty()
    
    away_batter_pa = db.IntegerProperty()
    home_batter_pa = db.IntegerProperty()
    
    away_batter_ops = db.FloatProperty()
    home_batter_ops = db.FloatProperty()
    
    away_umpire_g = db.IntegerProperty()
    home_umpire_g = db.IntegerProperty()
    
    away_umpire_tops = db.IntegerProperty()
    home_umpire_tops = db.IntegerProperty()
    
class BaseballScrape(webapp.RequestHandler):
    def get(self):
        self.REQUEST_COUNT = {'http://www.baseball-reference.com/' : 0, constants.PINNACLE_FEED : 0}
        self.fill_tips()
        
        self.response.out.write('<br />')
        for x in self.REQUEST_COUNT:
            self.response.out.write(x + ' : ' + str(self.REQUEST_COUNT[x]))
            self.response.out.write('<br />')
        
    def fill_tips(self):
        reference_feed = 'http://www.baseball-reference.com/'
        
        current_eastern_time = datetime.datetime.utcnow() - datetime.timedelta(hours = 4)
        
        # get initial previews page
        self.REQUEST_COUNT['http://www.baseball-reference.com/'] += 1
        
        request = urllib2.Request('http://www.baseball-reference.com/previews/', headers=constants.HEADER)
        html = urllib2.urlopen(request)
        self.previews_soup = {}
        self.previews_soup[current_eastern_time.date()] = BeautifulSoup(html)
        preview_date = datetime.datetime.strptime(re.search('(\d+-\d+-\d+)\.shtml', self.previews_soup[current_eastern_time.date()].find('div', {'id' : 'page_content'}).find('form').find('a')['href']).group(1), '%Y-%m-%d') + datetime.timedelta(days = 1)
        
        self.REQUEST_COUNT[constants.PINNACLE_FEED] += 1
        
        sport_feed = constants.PINNACLE_FEED + '?sporttype=baseball'
        request = urllib2.Request(sport_feed, headers=constants.HEADER)
        xml = urllib2.urlopen(request)
        soup = BeautifulSoup(xml, 'xml')
        all_games = soup.find_all('event')
        
        # go through all not yet completed tips
        query = Tip.gql("WHERE elapsed != True AND game_sport = 'Baseball'")
        for tip in query:
            tip_key = str(tip.key())
            bquery = BaseballValues.gql("WHERE tip_key = :1", tip_key)
            
            # either create corresponding baseballvalues object or retrieve existing one
            if bquery.count() == 0:
                bvalues = BaseballValues()
                bvalues.tip_key = tip_key
                bvalues.pitching_change = False
            else:
                bvalues = bquery.get()
                
            # page in eastern time
            game_eastern_time = tip.date - datetime.timedelta(hours = 4)
            # tomorrow's games are for another day
            if game_eastern_time.date() > current_eastern_time.date() or game_eastern_time.date() > preview_date.date():
                continue
            
            if game_eastern_time.date() == preview_date.date():
                bvalues = self.get_pitchers(bvalues, tip, all_games)
            else:
                if not game_eastern_time.date() in self.previews_soup:
                    self.REQUEST_COUNT['http://www.baseball-reference.com/'] += 1
                    
                    request = urllib2.Request('http://www.baseball-reference.com/previews/'+game_eastern_time.strftime('%Y')+'/'+game_eastern_time.strftime('%Y-%m-%d'), headers=constants.HEADER)
                    html = urllib2.urlopen(request)
                    self.previews_soup = {}
                    self.previews_soup[game_eastern_time.date()] = BeautifulSoup(html)
            
            bvalues = self.get_pitcher_stats(bvalues, tip, current_eastern_time)
    
    def get_pitcher_stats(self, bvalues, tip, current_eastern_time):
        previews = self.previews_soup[current_eastern_time.date()].find('div', {'id' : 'page_content'}).find_all('table')[1].find_all('p', {'class' : 'mobile_text'})
        
        away_team = tip.game_team_away
        home_team = tip.game_team_home
        
        eastern_time = tip.date - datetime.timedelta(hours = 4)
        
        for preview in previews:
            links = preview.find_all('a')
            
            teams = links[0]
            away_pitcher = links[1]
            home_pitcher = links[2]
            
            # make sure we got the right game
            team_regex = '[^@]*'+away_team.strip().split(' ')[-1].lower()+'[^@]+@[^@]+'+home_team.strip().split(' ')[-1].lower()
            time_regex = eastern_time.strftime('/%I:%M%p').lower().replace('/0','/').replace('/','')
            if not re.match(team_regex+'.+'+time_regex, teams.get_text().lower()):
                continue
            if bvalues.pitcher_away:
                name = bvalues.pitcher_away.lower().strip().split(' ')
                if name[-1] != away_pitcher.get_text().lower().strip().split(' ')[-1]:
                    continue
            if bvalues.pitcher_home:
                name = bvalues.pitcher_home.lower().strip().split(' ')
                if name[-1] != home_pitcher.get_text().lower().strip().split(' ')[-1]:
                    continue
            
            preview_href = teams['href']
            self.REQUEST_COUNT['http://www.baseball-reference.com/'] += 1
            request = urllib2.Request(preview_href, headers=constants.HEADER)
            html = urllib2.urlopen(request)
            preview_soup = BeautifulSoup(html)
            
            stats_tables = preview_soup.find('div', {'id' : 'page_content'}).find_all('table', {'class', 'stats_table'})
            
            rows = stats_tables[0].find_all('tr')
            index = 0
            for row in rows:
                header = row.find('td').find('span').get_text()
                game_count = re.search('Last (\d+) GS', header).group(1)
                if game_count:
                    game_score_total = 0
                    game_score_games = 0
                    for row2 in rows[index+1:index+game_count]:
                        game_date = datetime.datetime.strptime(row.find('td').find('a').get_text(), '%Y-%m-%d')
                        if game_date.date().year != tip.date.date().year:
                            break
                        game_score_total += int(row2.find_all('td')[-1].get_text())
                        game_score_games += 1
                    break
                index += 1
            bvalues.away_gs = game_score_total / game_score_games
            
            rows = stats_tables[1].find_all('tr')
            index = 0
            for row in rows:
                header = row.find('td').find('span').get_text()
                game_count = re.search('Last (\d+) GS', header).group(1)
                if game_count:
                    game_score_total = 0
                    game_score_games = 0
                    for row2 in rows[index+1:index+game_count]:
                        game_date = datetime.datetime.strptime(row.find('td').find('a').get_text(), '%Y-%m-%d')
                        if game_date.date().year != tip.date.date().year:
                            break
                        game_score_total += int(row2.find_all('td')[-1].get_text())
                        game_score_games += 1
                    break
                index += 1
            bvalues.home_gs = game_score_total / game_score_games
                    
        return bvalues
                
    def get_pitchers(self, bvalues, tip, all_games):
        for game_tag in all_games:
            if unicode(game_tag.find('gamenumber').string) == tip.pinnacle_game_no:
                participants = game_tag.find_all('participant')
                for participant_tag in participants:
                    if participant_tag.find('visiting_home_draw').string == 'Visiting':
                        if participant_tag.pitcher:
                            if bvalues.pitcher_away != None and bvalues.pitcher_away != participant_tag.pitcher.get_text():
                                bvalues.pitching_change = True
                                
                            bvalues.pitcher_away = participant_tag.pitcher.get_text()
                    else:
                        if participant_tag.pitcher:
                            if bvalues.pitcher_home != None and bvalues.pitcher_home != participant_tag.pitcher.get_text():
                                bvalues.pitching_change = True
                                
                            bvalues.pitcher_home = participant_tag.pitcher.get_text()
                            
                break
            
        return bvalues
            