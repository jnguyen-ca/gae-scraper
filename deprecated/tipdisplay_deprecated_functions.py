        self.cssheader.append(
'''<link rel="stylesheet" href="/javascript/scatterplot/css/scatterplot.css" />''')
        self.jsheader.append(
'''<script src="//ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>
<script src="/javascript/scatterplot/js/scatterplot.min.js"></script>''')

.hour {text-decoration: underline; text-align: center;}
.line_hour_interval {display: inline-block; vertical-align: top; width: 20%; margin: 1%; padding: 1%; border: 1px solid black;}
.point {margin-bottom: -4.5px; margin-left: -6.5px;}
.point .data {display: none; background: lightblue; padding: 3px; margin-left: 12px; float: left; text-align: right; position: absolute; z-index: 1;}
.intervals .interval {float: left; display: inline-block; width: 120px; height: 35px; opacity: 0.25; font-weight: bold; color: white; margin: -1px 1px 1px -1px;}

    def line_by_time(self, league):
        if hasattr(self, 'hour_intervals'):
            return self.hour_intervals
        else:
            self.hour_line_interval(league)
            return self.hour_intervals

    def line_movement_by_hour(self, league):
        if hasattr(self, 'movement_hour'):
            return self.movement_hour
        else:
            self.hour_line_interval(league)
            return self.movement_hour
  
    def line_movement_by_remaining(self, league):
        if hasattr(self, 'movement_intervals'):
            return self.movement_intervals
        else:
            self.hour_line_interval(league)
            return self.movement_intervals
  
    def hour_line_interval(self, league):
        self.hour_intervals = {}
        self.movement_hour = {}
        self.movement_intervals = {}
         
        for tip_instance in self.datastore[league]:
            if tip_instance.team_lines:
                team_lines = json.loads(tip_instance.team_lines)
                date_list = sorted(team_lines, key=lambda x: datetime.strptime(x, '%d.%m.%Y %H:%M'))
                 
                line = None
                previous_line = None
                for date in date_list:
                    if line is not None:
                        previous_line = line
                     
                    line = team_lines[date]
                    date = datetime.strptime(date, '%d.%m.%Y %H:%M')
                     
                    if previous_line is not None:
                        if int(line) >= 100 and int(previous_line) < 100:
                            movement = (int(line) - 100) +  (abs(int(previous_line)) - 100)
                        elif int(line) < 100 and int(previous_line) >= 100:
                            movement = (int(line) + 100) - (int(previous_line) - 100)
                        else:
                            movement = int(line) - int(previous_line)
                             
                        remaining_hour = (tip_instance.date - date).total_seconds() / 60 / 60
                             
                        if not date.time().hour in self.movement_hour:
                            self.movement_hour[date.time().hour] = {}
                        if not remaining_hour in self.movement_intervals:
                            self.movement_intervals[remaining_hour] = {}
                         
                        if not str(movement) in self.movement_hour[date.time().hour]:
                            self.movement_hour[date.time().hour][str(movement)] = [0, 0, 0]
                        if not str(movement) in self.movement_intervals[remaining_hour]:
                            self.movement_intervals[remaining_hour][str(movement)] = [0, 0, 0]
                         
                        if tip_instance.score_away is None and tip_instance.score_home is None:
                            self.movement_hour[date.time().hour][str(movement)][2] += 1
                        elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) > float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) < float(tip_instance.score_home)):
                            self.movement_hour[date.time().hour][str(movement)][0] += 1
                        elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) < float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) > float(tip_instance.score_home)):
                            self.movement_hour[date.time().hour][str(movement)][1] += 1
                        else:
                            self.movement_hour[date.time().hour][str(movement)][2] += 1
                        if tip_instance.score_away is None and tip_instance.score_home is None:
                            self.movement_intervals[remaining_hour][str(movement)][2] += 1
                        elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) > float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) < float(tip_instance.score_home)):
                            self.movement_intervals[remaining_hour][str(movement)][0] += 1
                        elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) < float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) > float(tip_instance.score_home)):
                            self.movement_intervals[remaining_hour][str(movement)][1] += 1
                        else:
                            self.movement_intervals[remaining_hour][str(movement)][2] += 1
                             
                    if not date.time().hour in self.hour_intervals:
                        self.hour_intervals[date.time().hour] = {}
                         
                    if not line in self.hour_intervals[date.time().hour]:
                        self.hour_intervals[date.time().hour][line] = [0, 0, 0]
                     
                    if tip_instance.score_away is None and tip_instance.score_home is None:
                        self.hour_intervals[date.time().hour][line][2] += 1
                    elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) > float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) < float(tip_instance.score_home)):
                        self.hour_intervals[date.time().hour][line][0] += 1
                    elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) < float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) > float(tip_instance.score_home)):
                        self.hour_intervals[date.time().hour][line][1] += 1
                    else:
                        self.hour_intervals[date.time().hour][line][2] += 1
                        
######### SCATTERPLOT #######          
    def line_by_time_scatterplot(self, league):
        hour_intervals = self.line_by_time(league)
         
        current_time = datetime.utcnow() - timedelta(hours = 6)
         
        maxp = 0
        points = []
        for tip_instance in self.datastore[league]:
            game_time = tip_instance.date - timedelta(hours = 6)
             
            line_hour_track = [0,0,0]
            game_count = {}
            if tip_instance.team_lines:
                latest_date = False
                latest_line = False
                 
                for date, line in json.loads(tip_instance.team_lines).iteritems():
                    date = datetime.strptime(date, '%d.%m.%Y %H:%M')
                    if not latest_date:
                        latest_date = date
                        latest_line = int(line)
                    if date > latest_date:
                        latest_date = date
                        latest_line = int(line)
                     
                    if date.time().hour in hour_intervals:
                        if line in hour_intervals[date.time().hour]:
                            line_hour_track[0] += hour_intervals[date.time().hour][line][0]
                            line_hour_track[1] += hour_intervals[date.time().hour][line][1]
                            line_hour_track[2] += hour_intervals[date.time().hour][line][2]
                             
                            if date.time().hour in game_count:
                                if line in game_count[date.time().hour]:
                                    game_count[date.time().hour][line][0] += 1
                                else:
                                    game_count[date.time().hour][line] = [1, hour_intervals[date.time().hour][line][0], hour_intervals[date.time().hour][line][1]]
                            else:
                                game_count[date.time().hour] = {}
                                game_count[date.time().hour][line] = [1, hour_intervals[date.time().hour][line][0], hour_intervals[date.time().hour][line][1]]
                             
            color = False
            result = False
            if tip_instance.score_away is None and tip_instance.score_home is None:
                continue
            elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) > float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) < float(tip_instance.score_home)):
                if (current_time.date() - game_time.date()).days == 0:
                    color = 'yellow'
                elif (current_time.date() - game_time.date()).days == 1:
                    color = 'darkgreen'
                elif tip_instance.wettpoint_tip_stake > 0:
                    color = 'grey'
                else:
                    color = 'black'
                 
                for i in game_count.itervalues():
                    for j in i.itervalues():
                        line_hour_track[0] -= (j[0] * j[0])
                result = 'W'
            elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) < float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) > float(tip_instance.score_home)):
                if (current_time.date() - game_time.date()).days == 0:
                    color = 'orange'
                elif (current_time.date() - game_time.date()).days == 1:
                    color = 'purple'
                elif tip_instance.wettpoint_tip_stake > 0:
                    color = 'red'
                else:
                    color = 'darkred'
                     
                for i in game_count.itervalues():
                    for j in i.itervalues():
                        line_hour_track[1] -= (j[0] * j[0])
                result = 'L'
            else:
                continue
             
            line_hour_total = line_hour_track[0] + line_hour_track[1]
            if line_hour_total <= 0:
                continue
            elif line_hour_total > maxp:
                maxp = line_hour_total
             
            line_hour_percentage = (line_hour_track[0] / float(line_hour_total)) * 100.00
             
            points.append([line_hour_total, line_hour_percentage, color, tip_instance.wettpoint_tip_stake, latest_line, result])
         
        self.draw_scatterplot('line_hour_interval_scatterplot', points, int(ceil(maxp / 1000.0) * 1000))
         
        self.scriptheader.append(
'''<script>
jQuery(document).ready(function() {
''')
        self.scriptheader.append('var maxp = '+str(maxp)+';')
        self.scriptheader.append(
'''
    jQuery('.upcoming_game .today').each(function() {
        var game = jQuery(this).parent();
        var position_x = String.fromCharCode(65 + Math.floor(game.find('.tip-line-past-count').text() / 2000.0 * 10))
        var position_y = Math.floor(game.find('.tip-line-past').text() * 100 / 5 + 1)
     
        game.append('<span class="upcoming_interval" style="min-width: 30px;">'+position_x+position_y+'</span>')
         
        if (position_y != 21 && position_x != 'J')
        {
            var unit_count = jQuery.data(jQuery('.scatterplot #'+position_x+position_y)[0], 'unit_count');
            var bet_amount = Math.round(Math.abs(((0.65 - jQuery('.scatterplot #'+position_x+position_y).css('opacity')) * 10) - 5));
            if (typeof unit_count == 'undefined' || unit_count >= 0)
            {
                game.append('<span class="upcoming_tail" style="background-color: lightgreen; text-align: center;">'+bet_amount+'</span>')
            }
            else
            {
                game.append('<span class="upcoming_fade" style="background-color: pink; text-align: center;">'+bet_amount+'</span>')
            }
        }
         
//        game.find('.tip-line-adjusted_win, .tip-line-adjusted_loss').hover(function() {
//            var a_position_x = String.fromCharCode(65 + Math.floor(game.find('.tip-line-adjusted_count').text() / maxp * 10))
//            var a_position_y = Math.floor(jQuery(this).text() * 100 / 5 + 1)
             
//            game.find('.upcoming_interval').css('color', 'red').text(a_position_x+a_position_y)
//        }, function() {game.find('.upcoming_interval').css('color', '').text(position_x+position_y)})
    });
     
    jQuery('<input>')
        .attr('id', 'line_hour_interval-simplify')
        .attr('type', 'checkbox')
        .attr('style', 'margin-left: 1270px; margin-top: -750px; position: absolute;')
        .insertAfter('#line_hour_interval_scatterplot')
        .on('change', function() {
            var $this = jQuery(this);
         
            jQuery('#line_hour_interval_scatterplot .point:not(".today-point")').each(function() {
                if ($this.is(':checked'))
                {
                    jQuery.data(this, 'original-color', jQuery(this).find('.data .color').text())
                    if (jQuery(this).find('.data .result').text() == 'W')
                    {
                        jQuery(this).css('background-color', 'black');
                    }
                    else
                    {
                        jQuery(this).css('background-color', 'darkred');
                    }
                }
                else
                {
                    jQuery(this).css('background-color', jQuery.data(this, 'original-color'));
                }
            });
        });
     
    jQuery('<input>')
        .attr('id', 'line_hour_interval-today')
        .attr('type', 'checkbox')
        .attr('style', 'margin-left: 1270px; margin-top: -700px; position: absolute;')
        .insertAfter('#line_hour_interval_scatterplot')
        .on('change', function() {
            if (jQuery(this).is(':checked'))
            {
                if (jQuery('#line_hour_interval_scatterplot .today-point').length == 0)
                {
                    var today_games = jQuery('.upcoming_game .today');
                    if (today_games.length == 0)
                    {
                        today_games = jQuery('.upcoming_game .tomorrow')
                    }
                 
                    today_games.each(function() {
                        var game = jQuery(this).parent();
                        var left = (game.find('.tip-line-past-count').text() / 2000.0) * jQuery('#line_hour_interval_scatterplot').width()
                        var bottom = game.find('.tip-line-past').text() * jQuery('#line_hour_interval_scatterplot').height()
                         
                        var today_point = jQuery('#line_hour_interval_scatterplot .point')
                            .first()
                            .clone(true)
                            .css('background-color', 'lightblue')
                            .css('bottom', bottom)
                            .css('left', left)
                            .addClass('today-point')
                            .appendTo('#line_hour_interval_scatterplot');
                             
                        today_point.find('.data')
                            .css('width', '115px')
                            .empty()
                            .append('<div class="game-data">'+game.find('.game-count').text()+'. '+game.find('.game_time-MST').text()+'<br/>'+game.find('.participants .away').text()+' @ '+game.find('.participants .home').text()+'</div>');
                         
                        var style = today_point.attr('style');
/*                        
                        jQuery('<span></span>')
                            .addClass('adjustment')
                            .addClass('win-adjust')
                            .attr('style', style)
                            .css('left', (game.find('.tip-line-adjusted_count').text() / maxp) * jQuery('#line_hour_interval_scatterplot').width() - left)
                            .css('bottom', game.find('.tip-line-adjusted_win').text() * jQuery('#line_hour_interval_scatterplot').height() - bottom)
                            .css('background-color', 'darkblue')
                            .css('position', 'absolute')
                            .css('z-index', 1)
                            .appendTo(today_point)
                            .hide();
                             
                        jQuery('<span></span>')
                            .addClass('adjustment')
                            .addClass('loss-adjust')
                            .attr('style', style)
                            .css('left', (game.find('.tip-line-adjusted_count').text() / maxp) * jQuery('#line_hour_interval_scatterplot').width() - left)
                            .css('bottom', game.find('.tip-line-adjusted_loss').text() * jQuery('#line_hour_interval_scatterplot').height() - bottom)
                            .css('background-color', 'darkblue')
                            .css('position', 'absolute')
                            .css('z-index', 1)
                            .appendTo(today_point)
                            .hide();
                             
                        today_point.hover(function() {jQuery(this).find('.adjustment').show()}, function() {jQuery(this).find('.adjustment').hide()});
*/
                    });
                }
                else
                {
                    jQuery('#line_hour_interval_scatterplot .today-point').show()
                }
            }
            else
            {
                jQuery('#line_hour_interval_scatterplot .today-point').hide()
            }
        });
});
</script>''')
        
    def line_movement_scatterplot(self, league):
        hour_intervals = self.line_movement_by_hour(league)
        remaining_intervals = self.line_movement_by_remaining(league)
         
        max_hour = 0
        max_remaining = 0
        points_hour = []
        points_remaining = []
        for tip_instance in self.datastore[league]:
            line_hour_track = [0,0,0]
            line_remaining_track = [0,0,0]
            if tip_instance.team_lines:
                team_lines = json.loads(tip_instance.team_lines)
                date_list = sorted(team_lines, key=lambda x: datetime.strptime(x, '%d.%m.%Y %H:%M'))
                 
                line = None
                previous_line = None
                for date in date_list:
                    if line is not None:
                        previous_line = line
                     
                    line = team_lines[date]
                    date = datetime.strptime(date, '%d.%m.%Y %H:%M')
                    remaining_hour = (tip_instance.date - date).total_seconds() / 60 / 60
                     
                    if previous_line is not None:
                        if int(line) >= 100 and int(previous_line) < 100:
                            movement = (int(line) - 100) +  (abs(int(previous_line)) - 100)
                        elif int(line) < 100 and int(previous_line) >= 100:
                            movement = (int(line) + 100) - (int(previous_line) - 100)
                        else:
                            movement = int(line) - int(previous_line)
                    else:
                        continue
                     
                    if date.time().hour in hour_intervals:
                        if str(movement) in hour_intervals[date.time().hour]:
                            line_hour_track[0] += hour_intervals[date.time().hour][str(movement)][0]
                            line_hour_track[1] += hour_intervals[date.time().hour][str(movement)][1]
                            line_hour_track[2] += hour_intervals[date.time().hour][str(movement)][2]
                    if remaining_hour in remaining_intervals:
                        if str(movement) in remaining_intervals[remaining_hour]:
                            line_remaining_track[0] += remaining_intervals[remaining_hour][str(movement)][0]
                            line_remaining_track[1] += remaining_intervals[remaining_hour][str(movement)][1]
                            line_remaining_track[2] += remaining_intervals[remaining_hour][str(movement)][2]
                             
            line_hour_total = line_hour_track[0] + line_hour_track[1]
            line_remaining_total = line_remaining_track[0] + line_remaining_track[1]
            if line_hour_total > 0:
                line_hour_percentage = (line_hour_track[0] / float(line_hour_total)) * 100.00
                if line_hour_total > max_hour:
                    max_hour = line_hour_total
            if line_remaining_total > 0:
                line_remaining_percentage = (line_remaining_track[0] / float(line_remaining_total)) * 100.00
                if line_remaining_total > max_remaining:
                    max_remaining = line_remaining_total
             
            color = False
            if tip_instance.score_away is None and tip_instance.score_home is None:
                continue
            elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) > float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) < float(tip_instance.score_home)):
                if tip_instance.wettpoint_tip_stake > 0:
                    color = 'grey'
                else:
                    color = 'black'
            elif (tip_instance.wettpoint_tip_team == tip_instance.game_team_away and float(tip_instance.score_away) < float(tip_instance.score_home)) or (tip_instance.wettpoint_tip_team == tip_instance.game_team_home and float(tip_instance.score_away) > float(tip_instance.score_home)):
                if tip_instance.wettpoint_tip_stake > 0:
                    color = 'red'
                else:
                    color = 'darkred'
            else:
                continue
             
            if line_hour_total > 0:
                points_hour.append([line_hour_total, line_hour_percentage, color])
            if line_remaining_total > 0:
                points_remaining.append([line_remaining_total, line_remaining_percentage, color])
                 
        self.draw_scatterplot('line_movement_hour_scatterplot', points_hour, max_hour)
        self.draw_scatterplot('line_movement_remaining_scatterplot', points_remaining, max_remaining)
                
    def draw_scatterplot(self, id, points, maxy):
        self.html.append("<div id='"+id+"'>")
         
        for point in points:
            total_percentage = (float(point[0])/float(maxy))*100.00
            self.html.append("<span class='point' style='width: 9px;")
            self.html.append('background-color:'+point[2]+';')
            self.html.append('left: '+str( total_percentage )+'%;')
            self.html.append('bottom: '+str(point[1])+'%;')
            self.html.append("'>")
            self.html.append("<div class='data'>")
            self.html.append("<div class='percentage'>"+"{0:.2f}".format(round(point[1], 2))+"%</div>")
            self.html.append("<div class='total'>"+str( point[0] )+"</div>")
            self.html.append("<div class='stake'>"+str( point[3] )+"</div>")
            self.html.append("<div class='line'>"+str( point[4] )+"</div>")
            self.html.append("<div class='color' style='display: none;'>"+str( point[2] )+"</div>")
            self.html.append("<div class='result'>"+str( point[5] )+"</div>")
             
            position_x = string.uppercase[int(total_percentage / 10)]
            position_y = int(point[1] / 5) + 1
             
            self.html.append("<div class='interval'>"+position_x + str( position_y )+"</div>")
             
            self.html.append("</div>")
            self.html.append("</span>")
             
        self.html.append("</div>")
        self.scriptheader.append(
'''<script>
jQuery(document).ready(function() {
''')
        self.scriptheader.append("var id = '"+id+"';")
        self.scriptheader.append("jQuery('#'+id).scatter({")
        self.scriptheader.append(
'''
        width: 1200,
        height: 700,
        xLabel: 'Total',
        yLabel: 'Percentage',
        responsive: true,
''')
        increments = float(maxy) / 5
        self.scriptheader.append("xUnits: ['0', '"+str(increments)+"', '"+str((increments*2))+"', '"+str((increments*3))+"', '"+str((increments*4))+"', '"+str(maxy)+"'],")
        self.scriptheader.append(
'''
        yUnits: ['0', '.1', '.2', '.3', '.4', '.5', '.6', '.7', '.8', '.9', '1'],
        rows: 10,
        columns: 5,
        subsections: 2,
    });
''')
        self.scriptheader.append(
'''
jQuery('#'+id+' .point').plot();
jQuery('#'+id+' .point').hover(function() {jQuery(this).find('.data').show()}, function() {jQuery(this).find('.data').hide()});
 
jQuery('#'+id).prepend('<div class="intervals"></div>');
for (var i = 0; i < 200; i++) {
    var position_x = String.fromCharCode(65 + (i % 10));
    var position_y = 20 - Math.floor(i / 10);
    jQuery('#'+id+' .intervals').append('<div id="'+position_x + position_y+'" class="interval"></div>');
}
 
jQuery('#'+id).after('<span id="'+id+'-interval-unit-total" style="background: lightgrey; border: 1px solid black; margin-left: 1270px; margin-top: -300px; padding: 3px; position: absolute;"></span>');
 
var max_plus_count = 0;
var max_neg_count = 0;
jQuery('#'+id+' .interval').each(function() {
    var interval = jQuery(this).attr('id')
    var points = jQuery('#'+id+' .point .data .interval:contains("'+interval+'")')
     
    var unit_count = 0;
    var wins = 0;
    var losses = 0;
    points.each(function() {
        if (jQuery(this).html() != interval || jQuery(this).closest('.point').hasClass('today-point'))
        {
            return true;
        }
     
        var result = jQuery(this).closest('.data').find('.result').html()
        var line = jQuery(this).closest('.data').find('.line').html()
         
        if (result == 'W') {
            wins += 1;
         
            if (line >= 100) {
                unit_count += line / 100
            }
            else {
                unit_count += 100 / (line * -1) 
            }
        }
        else
        {
            losses += 1
            unit_count -= 1;
        }
         
        jQuery(this).closest('.point').hover(function() {jQuery('#'+interval).text(unit_count);jQuery('#'+id+'-interval-unit-total').text(interval+' : '+unit_count+' ('+wins+'-'+losses+')');}, function() {jQuery('#'+interval).text('')});
    });
     
    jQuery.data(this, 'unit_count', unit_count)
     
    if (unit_count != 0) {
        if (unit_count > 0) {
            jQuery(this).css('background-color', 'green')
             
            if (unit_count > max_plus_count)
            {
                max_plus_count = unit_count;
            }
        }
        else if (unit_count < 0) {
            jQuery(this).css('background-color', 'red')
             
            if (unit_count < max_neg_count)
            {
                max_neg_count = unit_count;
            }
        }
         
        unit_count = Math.round(unit_count * 100) / 100
        jQuery(this).hover(function() {jQuery(this).text(unit_count);jQuery('#'+id+'-interval-unit-total').text(interval+' : '+unit_count+' ('+wins+'-'+losses+')');}, function() {jQuery(this).text('')});
    }
});
 
var max_opacity = 0.65;
jQuery('#'+id+' .interval').each(function() {
    var unit_count = jQuery.data(this, 'unit_count')
     
    if (unit_count > 0)
    {
        var new_opacity = max_opacity - (Math.ceil((max_plus_count - unit_count) / (max_plus_count / 4)) * 0.1);
        jQuery(this).css('opacity', new_opacity);
    }
    else if (unit_count < 0)
    {
        var new_opacity = max_opacity - (Math.ceil((Math.abs(max_neg_count) - Math.abs(unit_count)) / (Math.abs(max_neg_count) / 4)) * 0.1);
        jQuery(this).css('opacity', new_opacity);
    }
});
 
jQuery('#'+id).mousemove(function(e) {
    var relX = e.pageX - jQuery(this).offset().left;
    var relY = e.pageY - jQuery(this).offset().top;
     
    if (relX > 0 && relX <= jQuery(this).width() && relY > 0 && relY <= jQuery(this).height())
    {
        var position_x = String.fromCharCode(65 + Math.floor(relX / jQuery(this).width() * 10));
        var position_y = Math.floor((jQuery(this).height() - relY) / jQuery(this).height() * 100 / 5 + 1)
    }
});
''')
        self.scriptheader.append(
'''});
</script>''')
         
    def display_line_by_time(self, league):
        hour_intervals = self.line_by_time(league)
        time = datetime.utcnow()
         
        limit = 24
        while limit > 0:
            add = 24 - limit
            limit -= 1
             
            hour = time.time().hour
            if hour in hour_intervals:
                self.html.append("<div class='line_hour_interval'>")
                self.html.append("<div class='hour'><b>%(hour)s</b> (Current Hour +%(add)d)</div>" % locals())
                 
                for line in sorted(hour_intervals[hour].iterkeys()):
                    results = hour_intervals[hour][line]
                     
                    wins = results[0]
                    losses = results[1]
                    pushes = results[2]
                     
                    self.html.append("<div class='lines'>")
                    self.html.append("<span class='line'><b>%(line)s</b></span> : " % locals())
                    self.html.append("<span class='results'>")
                    self.html.append("<span class='wins'>%(wins)d</span> - " % locals())
                    self.html.append("<span class='losses'>%(losses)d</span> - " % locals())
                    self.html.append("<span class='pushes'>%(pushes)d</span>" % locals())
                    self.html.append("</span>")
                    self.html.append("</div>")
                     
                self.html.append("</div>")
                     
            time = time + timedelta(hours = 1)