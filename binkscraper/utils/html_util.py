#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import json
import cgi

__TEMPLATE_TAGS__ = {}
__CSS_STYLES__ = ''
__CSS_SHEETS__ = []
__JS_SCRIPTS__ = ''
__JS_FILES__ = []

def add_template_tag(key, value, overwrite=False):
    global __TEMPLATE_TAGS__
    if key not in __TEMPLATE_TAGS__ or overwrite is True:
        __TEMPLATE_TAGS__[key] = value
    else:
        __TEMPLATE_TAGS__[key] += value
    return

def add_template_tags(tags, overwrite=False):
    global __TEMPLATE_TAGS__
    if not __TEMPLATE_TAGS__ or overwrite is True:
        __TEMPLATE_TAGS__ = tags
    else:
        __TEMPLATE_TAGS__.update(tags)
    return

def add_css_styles(styles):
    global __CSS_STYLES__
    __CSS_STYLES__ += styles
    return

def add_css_sheets(sheets):
    global __CSS_SHEETS__
    if isinstance(sheets, list):
        for sheet in sheets:
            __CSS_STYLES__ += '<link rel="stylesheet" type="text/css" href="'+sheet+'">'
    else:
        __CSS_STYLES__ += '<link rel="stylesheet" type="text/css" href="'+sheets+'">'
    return

def add_js_scripts(scripts):
    global __JS_SCRIPTS__
    __JS_SCRIPTS__ += scripts
    return

def add_js_files(files):
    global __JS_FILES__
    if isinstance(files, list):
        for js in files:
            __JS_FILES__ += '<script src='+js+'"></script>'
    else:
        __JS_FILES__ += '<script src='+files+'"></script>'
    return

def __reset_all_meta():
    global __TEMPLATE_TAGS__
    global __CSS_STYLES__
    global __CSS_SHEETS__
    global __JS_SCRIPTS__
    global __JS_FILES__
    __TEMPLATE_TAGS__ = {}
    __CSS_STYLES__ = ''
    __CSS_SHEETS__ = []
    __JS_SCRIPTS__ = ''
    __JS_FILES__ = []
    return

def replace_template_tags(line, templates):
    """Replaces [template:tag_name] in a line with the tag_name value in templates
    """
    template_tags = re.finditer('\[template:(\S+)\]', line)
    if template_tags:
        for match in template_tags:
            if match.group(1) in templates:
                line = line.replace(match.group(0), templates[match.group(1)])
    
    return line

def print_html(output, html=None):
    global __TEMPLATE_TAGS__
    global __CSS_STYLES__
    global __CSS_SHEETS__
    global __JS_SCRIPTS__
    global __JS_FILES__
    
    if html is not None:
        with open('templates/'+html) as f:
            for line in f:
                line = replace_template_tags(line, __TEMPLATE_TAGS__)
                if '</head>' in line:
                    output.write("".join(__CSS_SHEETS__))
                    output.write("".join(__JS_FILES__))
                    output.write(__JS_SCRIPTS__)
                    output.write(__CSS_STYLES__)
                output.write(line)
                
    __reset_all_meta()
    
def display_dict(dictonary, level=0):
    '''Create a HTML representation of a dictionary. This is a recursive function for nested dicts.
    '''
    entries_html = '<div class="dict-entries dict-level-%d">' % (level)
    entries_html += '<input class="dict-level" type="hidden" val="%d">' % (level)
    entries_html += '''
    <div class="dict-level-controls">
        <input type="button" class="styleless-button add-entry" value="Add Entry">
        <input type="button" class="styleless-button minimize-dict-level" value="Minimize">
    </div>
    '''
    for key, value in dictonary.iteritems():
        entries_html += _display_dict_entry(key, value, level)
    
    entries_html += '</div>'
    
    return entries_html

def _display_dict_entry(key, value, level=0):
    if isinstance(value, dict):
        value_html = '<span class="dict-value">'+display_dict(value, level+1)+'</span>'
    else:
        value_html = '''
        %s
        <span class="dict-entry-controls">
            <input type="button" class="styleless-button edit-entry" value="Edit">
            <input type="button" class="styleless-button delete-entry" value="Delete">
        </span>
        ''' % (_display_dict_value(value))
        
    entry_html = '''
    <div class="dict-entry">
        <span class="dict-key">%s</span>
        %s
    </div>
    ''' % (
           key,
           value_html
           )
    
    return entry_html

def _display_dict_value(value):
    '''Create a HTML representation of a dict entry's value.
    '''
    # value must either be a list or a string, if it was a dict it shouldn't have got here
    if isinstance(value, list):
        value_display = display_list(value)
        # convert list to json string for output
        value = json.dumps(value, ensure_ascii=False)
    else:
        value_display = display_string(value)
    
    value_html = '''
    <span class="dict-value">
        <input type="hidden" class="source" value="%s">
        <span class="value-entry">
            %s
        </span>
    </span>
    ''' % (
           cgi.escape(value, True),
           value_display
           )
    
    return value_html

def display_list(dataList):
    insert_breaks = False
    
    list_display = ''
    for x in dataList:
        list_display += '<span class="list-entry">'+x+'</span>'
        
        if len(x) >= 50:
            insert_breaks = True
        
    value_display = '''
    <span class="list-entries%s">
        %s
    </span>
    ''' % (
           ' list-bullets-format' if insert_breaks is True else '',
           list_display
           )
        
    return value_display

def display_string(dataString):
    return '<span class="string-entry">'+dataString+'</span>'