#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('utils')

from google.appengine.ext import webapp
from utils import appvar_util, html_util, sys_util

import re
import cgi
import json
import logging
import ast

class AppSettings(webapp.RequestHandler):
    INPUT_NAME_REQUEST_TYPE = 'request-type'
    INPUT_NAME_REQUEST_VALUE = 'request-value'
    INPUT_NAME_REQUEST_LEVEL = 'request-level'
    INPUT_NAME_APP_VAR_KEY = 'app_var-key'
    INPUT_NAME_APP_VAR_ENTRY = 'app_var-entry'

    REQUEST_TYPE_EDIT_SOURCE = 'edit-source'
    REQUEST_TYPE_ADD_EDIT_ENTRY = 'add-edit-entry'
    REQUEST_TYPE_DELETE_ENTRY = 'delete-entry'
    
    def get(self):
        self.display()
        return
    
    def post(self):
        if sys_util.is_ajax(self.request):
            request_type = self.request.get(self.INPUT_NAME_REQUEST_TYPE)
            app_key = self.request.get(self.INPUT_NAME_APP_VAR_KEY)
            request_entry = self.request.get(self.INPUT_NAME_APP_VAR_ENTRY)
            request_value = self.request.get(self.INPUT_NAME_REQUEST_VALUE)
            
            # keys are stored in [key] format so regex all characters between 2 square brackets
            entry_keys = re.findall('\[([^\]]+)\]', request_entry)
            
            try:
                # leave numeric strings alone but evaluate lists and dicts
                if not request_value.isnumeric():
                    request_value = ast.literal_eval(request_value)
                    
                    # convert everything to unicode
                    # TODO: how to handle dict
                    if isinstance(request_value, str):
                        request_value = request_value.decode('utf-8')
                    elif isinstance(request_value, list):
                        request_value = [x.decode('utf-8') if isinstance(x, str) else x for x in request_value]
            except (SyntaxError, ValueError):
                # return error response due to incorrect formatting
                self.response.set_status(400)
            else:
                logging.debug('Request : (%s), AppVar : (%s), Keys : (%s)' % (request_type, app_key, str(entry_keys)))
                # determine the request type
                if request_type == self.REQUEST_TYPE_EDIT_SOURCE:
                    # set and dump to output so display source can be updated
                    appvar_util.set_app_var(app_key, request_value)
                    self.response.out.write(cgi.escape(json.dumps(request_value, ensure_ascii=False)))
                elif request_type == self.REQUEST_TYPE_ADD_EDIT_ENTRY:
                    # modify the entry and overwrite the var
                    app_var = appvar_util.get_or_set_app_var(app_key)
                    sys_util.set_in_dict(app_var, entry_keys, request_value)
                    appvar_util.set_app_var(app_key, app_var)
                    # re-create the value display to replace old
                    
                    try:
                        request_level = int(self.request.get(self.INPUT_NAME_REQUEST_LEVEL))
                    except ValueError:
                        request_level = 0
                    entry_html = self.display_dict_entry(entry_keys[-1], request_value, request_level)
                    self.response.out.write(entry_html)
                elif request_type == self.REQUEST_TYPE_DELETE_ENTRY:
                    app_var = appvar_util.get_or_set_app_var(app_key)
                    sys_util.del_in_dict(app_var, entry_keys)
                    appvar_util.set_app_var(app_key, app_var)
                
        return
    
    def display(self):
        '''Creates the settings display for application variables
        '''
        app_var_html = ''
        for app_var_key in appvar_util.VALID_APPVAR_LIST:
            # if variable does not exist, create empty one
            app_var_value = appvar_util.get_or_set_app_var(app_var_key)
            formatted_display = self.app_vars_display(app_var_key, app_var_value)
            
            # each variable has its title (key), source (value), and working display (value)
            app_var_html += '''
            <div class="app-variable">
                <div class="app-title">
                    <span class="app-key">%s</span>
                    <input type="button" class="edit-source" value="Edit Source">
                </div>
                <div class="app-value">
                    <form id="%s-source_form" class="source_form" style="display:none;">
                        <input type="hidden" name="%s" value="%s">
                        <input type="hidden" name="%s" value="%s">
                        <textarea class="source" name="%s" rows="20" cols="100">%s</textarea>
                        <input type="submit" value="Submit">
                    </form>
                    <div class="formatted">%s</div>
                </div>
            </div>
            ''' % (
                   app_var_key,
                   app_var_key,
                   self.INPUT_NAME_REQUEST_TYPE,
                   self.REQUEST_TYPE_EDIT_SOURCE,
                   self.INPUT_NAME_APP_VAR_KEY,
                   app_var_key,
                   self.INPUT_NAME_REQUEST_VALUE,
                   cgi.escape(json.dumps(app_var_value, ensure_ascii=False)) if app_var_value is not None else '',
                   formatted_display
                   )
            
        html_util.add_template_tag('app_vars_display', app_var_html)
        
        # use form templates that can be copied for common ajax requests
        form_templates = self.create_form_template(self.REQUEST_TYPE_ADD_EDIT_ENTRY)
        form_templates += self.create_form_template(self.REQUEST_TYPE_DELETE_ENTRY)
        
        html_util.add_template_tag('form_templates', form_templates)
        
        html_util.print_html(self.response.out, html='appsettings.html')
        return
    
    def create_form_template(self, request_type, show_value=True):
        form_template = '''
        <form class="%s-form">
            <input type="hidden" name="%s" value="%s">
            <input type="hidden" name="%s" value="" class="app-key">
            <input type="hidden" name="%s" value="" class="entry-level">
            <input type="hidden" name="%s" value="" class="entry-key">
            <input type="%s" name="%s" value="" class="entry-value">
            <input type="submit" value="Submit">
        </form>
        ''' % (
               request_type,
               self.INPUT_NAME_REQUEST_TYPE,
               request_type,
               self.INPUT_NAME_APP_VAR_KEY,
               self.INPUT_NAME_REQUEST_LEVEL,
               self.INPUT_NAME_APP_VAR_ENTRY,
               'text' if show_value is True else 'hidden',
               self.INPUT_NAME_REQUEST_VALUE,
               )
        
        return form_template
    
    def app_vars_display(self, app_var_key, app_var_value):
        '''Create a working display for an application variable based on the
        variable's object
        '''
        if isinstance(app_var_value, dict):
            entries_html = html_util.display_dict(app_var_value)
        elif isinstance(app_var_value, list):
            entries_html = html_util.display_list(app_var_value)
        elif isinstance(app_var_value, basestring):
            entries_html = html_util.display_string(app_var_value)
        else:
            entries_html = ''
            
        html = '''
        %s
        ''' % (
               entries_html
               )
        
        return html