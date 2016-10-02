#usr/bin/python
# -*- coding: utf-8 -*-

from google.appengine.ext import ndb

import logging
import json
from binkscraper import models

class Patch_5_0_0():
    '''
    v5.0.0 is the milestone where TipLine becomes the sole container of the odds for an event. In the later
    versions 4.x.x we started storing odds in both TipLine and Tip (and TipChange) to maintain backwards 
    compatibility in preparation but before that the only odds information was stored in Tip. Therefore only 
    a portion of Tips in the datastore have a corresponding TipLine.
    '''
    def __init__(self, datetime_start, datetime_end):
        self._count_tips = 0
        self._count_tips_empty = 0
        self._count_tiplines_created = 0
        self._count_tiplines = 0
        self._count_tip_team_lines_copied = 0
        self._count_tipchange_team_lines_copied = 0
        self._count_tip_spread_lines_copied = 0
        self._count_tipchange_spread_lines_copied = 0
        self._count_tip_total_lines_copied = 0
        self._count_tipchange_total_lines_copied = 0
        
        self.datetime_start = datetime_start
        self.datetime_end = datetime_end
        logging.info('Date range between %s and %s' % (datetime_start.strptime('%b-%d-%Y'),datetime_end.strptime('%b-%d-%Y')))
    
    def patch_populate(self):
        '''
        Populates the datastore with TipLines for Tips that do not already have one. If a Tip already has
        a TipLine, it will verify that the odds info from Tip (if there is any) has been transferred over
        correctly. Will fill in newly created Tips with odds info from their corresponding Tip and TipChange.
        Afterwards, it should be safe to run patch_delete()
        '''
        tiplines_to_put = []
        
        self.bookie_key = models.APPVAR_KEY_PINNACLE
        for tip_instance in models.Tip.query(models.Tip.date >= self.datetime_start, models.Tip.date <= self.datetime_end):
            updated = False
            self._count_tips += 1
            tipchange_instance = models.TipChange.query(models.TipChange.tip_key == unicode(tip_instance.key.urlsafe())).get()
            if (tip_instance.team_lines is None
                and tip_instance.total_no is None
                and tip_instance.total_lines is None
                and tip_instance.spread_no is None
                and tip_instance.spread_lines is None
            ):
                self._count_tips_empty += 1
                if tipchange_instance is not None:
                    if (tipchange_instance.team_lines is None
                        and tipchange_instance.total_no is None
                        and tipchange_instance.total_lines is None
                        and tipchange_instance.spread_no is None
                        and tipchange_instance.spread_lines is None
                    ):
                        # if both the Tip and TipChange lines are null then no need for a TipLine
                        continue
                    
            tipline_instance = models.TipLine.query(ancestor=tip_instance.key).get()
            if tipline_instance is None:
                updated = True
                self._count_tiplines_created += 1
                tipline_instance = models.TipLine(parent=tip_instance.key)
            self._count_tiplines += 1
            
            if tip_instance.team_lines:
                self._count_tip_team_lines_copied += 1
                updated = Patch_5_0_0._populate_money_lines(tip_instance, tipline_instance, self.bookie_key)
            if (tipchange_instance.wettpoint_tip_team != tip_instance.wettpoint_tip_team
                and tipchange_instance.team_lines
            ):
                self._count_tipchange_team_lines_copied += 1
                updated = Patch_5_0_0._populate_money_lines(tipchange_instance, tipline_instance, self.bookie_key)
    
            if tip_instance.spread_lines and tip_instance.spread_no:
                self._count_tip_spread_lines_copied += 1
                updated = Patch_5_0_0._populate_spread_lines(tip_instance, tipline_instance, self.bookie_key)
            if (tipchange_instance.wettpoint_tip_team != tip_instance.wettpoint_tip_team
                and tipchange_instance.spread_lines and tipchange_instance.spread_no
            ):
                self._count_tipchange_spread_lines_copied += 1
                updated = Patch_5_0_0._populate_spread_lines(tipchange_instance, tipline_instance, self.bookie_key)
                
            if tip_instance.total_lines and tip_instance.total_no:
                self._count_tip_total_lines_copied += 1
                updated = Patch_5_0_0._populate_total_lines(tip_instance, tipline_instance, self.bookie_key)
            if (tipchange_instance.wettpoint_tip_total != tip_instance.wettpoint_tip_total
                and tipchange_instance.total_lines and tipchange_instance.total_no
            ):
                self._count_tipchange_total_lines_copied += 1
                updated = Patch_5_0_0._populate_total_lines(tipchange_instance, tipline_instance, self.bookie_key)
    
            if updated is True:
                tiplines_to_put.append(tipline_instance)
                
        logging.info('%d Tips in datastore' % (self._count_tips))
        logging.info('%d Tips have no line information' % (self._count_tips_empty))
        logging.info('%d TipLines were created' % (self._count_tiplines_created))
        logging.info('%d TipLines (new+existing) in datastore' % (self._count_tiplines))
        logging.info('Tip properties extracted: team_lines (%d), spread_lines/spread_no (%d), total_lines/total_no (%d)' % (
                                                                                                                         self._count_tip_team_lines_copied,
                                                                                                                         self._count_tip_spread_lines_copied,
                                                                                                                         self._count_tip_total_lines_copied
                                                                                                                         ))
        logging.info('TipChange properties extracted: team_lines (%d), spread_lines/spread_no (%d), total_lines/total_no (%d)' % (
                                                                                                                         self._count_tipchange_team_lines_copied,
                                                                                                                         self._count_tipchange_spread_lines_copied,
                                                                                                                         self._count_tipchange_total_lines_copied
                                                                                                                         ))
        logging.info('%d TipLines to be put' % (len(tiplines_to_put)))
        ndb.put_multi(tiplines_to_put)
            
    @staticmethod
    def _populate_money_lines(cls, tipline_instance, bookie_key):
        '''Transfers team_lines to corresponding TipLine money properties
        cls is a class instance that has the properties team_lines and wettpoint_tip_team
        '''
        updated = False
        cls_team_lines = json.loads(cls.team_lines)
        
        # get the properties that are going to be modified based on the object's wettpoint_tip_team
        money_properties = []
        tipline_instance_properties = []
        # wettpoint_tip_team is 1X2 format
        for x in cls.wettpoint_tip_team:
            if x == models.TIP_SELECTION_TEAM_HOME:
                money_property = 'money_home'
            elif x == models.TIP_SELECTION_TEAM_DRAW:
                money_property = 'money_draw'
            elif x == models.TIP_SELECTION_TEAM_AWAY:
                money_property = 'money_away'
            else:
                raise Exception('Invalid tip team selection : '+str(x)+' : '+str(cls.key.urlsafe()))
                
            tipline_instance_properties.append(getattr(tipline_instance, money_property))
            money_properties.append(money_property)
        
        # go through each individual entry and insert into TipLine
        for line_date, money_line in cls_team_lines.iteritems():
            if models.TIP_SELECTION_LINE_SEPARATOR in money_line:
                # if draw line was included then need to separate
                entry_lines = money_line.split(models.TIP_SELECTION_LINE_SEPARATOR)
            else:
                entry_lines = [money_line]
                
            for index, money_property in enumerate(money_properties):
                # each tip team specified should have a line associated, thus indices should match up
                try:
                    # if the entry value already exists in the tipline instance, no need to modify
                    current_entry_value = tipline_instance_properties[index][bookie_key][line_date]
                    if current_entry_value != entry_lines[index]:
                        logging.warning('Existing TipLine value does not equal incoming Tip(Change) value?! ('+cls.key.urlsafe()+")\n"
                                        +'TipLine: '+str(current_entry_value)+' vs Tip(Change): '+str(entry_lines[index]))
                    continue
                except KeyError:
                    pass
                updated = True
                tipline_instance.insert_property_entry(entry_property=money_property, 
                                                       bookie_key=bookie_key, 
                                                       line_date=line_date, 
                                                       odds_values=entry_lines[index]
                                                       )
            
        return updated
    
    @staticmethod
    def _populate_spread_lines(cls, tipline_instance, bookie_key):
        '''Transfer spread_no and spread_lines to TipLine spread_away and spread_home properties
        cls is object with properties spread_no, spread_lines, wettpoint_tip_team
        '''
        cls_spread_no = cls.spread_no
        cls_spread_lines = cls.spread_lines
        
        if (models.TIP_SELECTION_TEAM_HOME in cls.wettpoint_tip_team
            or models.TIP_SELECTION_TEAM_DRAW == cls.wettpoint_tip_team
        ):
            entry_property = 'spread_home'
        elif models.TIP_SELECTION_TEAM_AWAY in cls.wettpoint_tip_team:
            entry_property = 'spread_away'
        else:
            raise Exception('wettpoint_tip_team has neither home nor away selection in it and is not draw selection : '+str(cls.key.urlsafe()))
        
        return Patch_5_0_0.__populate_point_odd_lines(cls_urlsafe_key   = cls.key.urlsafe(), 
                                                       cls_nos          = cls_spread_no, 
                                                       cls_lines        = cls_spread_lines, 
                                                       tipline_instance = tipline_instance, 
                                                       entry_property   = entry_property, 
                                                       bookie_key       = bookie_key
                                                       )
        
    @staticmethod
    def _populate_total_lines(cls, tipline_instance, bookie_key):
        '''Transfer total_no and total_lines to TipLine total_under and total_over properties
        cls is object with properties total_no, total_lines, wettpoint_tip_total
        '''
        cls_total_no = cls.total_no
        cls_total_lines = cls.total_lines
        
        if cls.wettpoint_tip_total == models.TIP_SELECTION_TOTAL_OVER:
            entry_property = 'total_over'
        else:
            entry_property = 'total_under'
        
        return Patch_5_0_0.__populate_point_odd_lines(cls_urlsafe_key   = cls.key.urlsafe(), 
                                                       cls_nos          = cls_total_no, 
                                                       cls_lines        = cls_total_lines, 
                                                       tipline_instance = tipline_instance, 
                                                       entry_property   = entry_property, 
                                                       bookie_key       = bookie_key
                                                       )
        
    @staticmethod
    def __populate_point_odd_lines(cls_urlsafe_key, cls_nos, cls_lines, tipline_instance, entry_property, bookie_key):
        '''Sub-method for _populate_spread_lines and _populate_total_lines
        '''
        updated = False
        for line_date, cls_no in cls_nos:
            if line_date not in cls_lines:
                raise KeyError('line_date in spread_no but not in spread_line : '+str(cls_urlsafe_key))
            cls_line = cls_lines[line_date]
            
            try:
                current_entry_value = getattr(tipline_instance, entry_property)[bookie_key][line_date]
                if (current_entry_value[models.TIPLINE_KEY_POINTS] != cls_no
                    and current_entry_value[models.TIPLINE_KEY_ODDS] != cls_line
                ):
                    logging.warning('Spread values for '+str(line_date)+' : '+str(cls_urlsafe_key)+' do not match!'+"\n"
                                    +'TipLine: '+str(current_entry_value[models.TIPLINE_KEY_POINTS])+' , '+str(current_entry_value[models.TIPLINE_KEY_ODDS])+"\n"
                                    +'cls: '+str(cls_no)+' , '+str(cls_line))
                continue
            except KeyError:
                pass
            updated = True
            tipline_instance.insert_property_entry(entry_property=entry_property, 
                                                   bookie_key=bookie_key, 
                                                   line_date=line_date, 
                                                   points_values=cls_no,
                                                   odds_values=cls_line
                                                   )
        
        return updated
    
    #TODO: need to reset wettpoint_tip_team for old/existing Tips where the favourite would get set if it was a 0 tip
    def patch_modify(self):
        '''Before TipLine was implemented, Tip was only able to store a single side's lines. Therefore, if there was
        no wettpoint_tip_team it needed to be decided that Tip would simply store the favourite side's lines. This would
        be done by setting wettpoint_tip_team to the favourite side and treating it as if it was an actual tip. However,
        now that TipLine is available, both sides' lines are stored regardless of the wettpoint_tip_team, so there's no 
        reason to keep wettpoint_tip_team as a "fake" value.
        Should only be run after patch_populate()
        '''
        tips_to_put = []
    
    def patch_delete(self):
        '''
        Deletes existing odds properties from Tips 
        Should only be run after patch_populate()
        '''
        tips_to_put = []
        for tip_instance in models.Tip.query():
            delattr(tip_instance, 'team_lines')
            delattr(tip_instance, 'spread_lines')
            delattr(tip_instance, 'total_lines')
            delattr(tip_instance, 'spread_no')
            delattr(tip_instance, 'total_no')
            tips_to_put.append(tip_instance)
        ndb.put_multi(tips_to_put)