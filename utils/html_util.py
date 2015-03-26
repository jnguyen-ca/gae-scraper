#usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

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
        with open(html) as f:
            for line in f:
                line = replace_template_tags(line, __TEMPLATE_TAGS__)
                if '</head>' in line:
                    output.write("".join(__CSS_SHEETS__))
                    output.write("".join(__JS_FILES__))
                    output.write(__JS_SCRIPTS__)
                    output.write(__CSS_STYLES__)
                output.write(line)
                
    __reset_all_meta()