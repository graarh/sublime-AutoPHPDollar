'''
AutoPHPDollar - sublime text 2 plugin, automatically adds "$" before variables
Copyright (c) 2012, Gennadiy Kovalev
All rights reserved.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
import re

import sublime
import sublime_plugin
from sets import Set


settings = sublime.load_settings('AutoPHPDollar.sublime-settings')
ignore_names = settings.get("ignore names", [])
rules = settings.get("rules", [])
ignore_after = settings.get("ignore after", [])

def get_patterns(view):
    return rules + [
        #already known variables
        #quick hack: ignore variables adjaced to ", my personal preferense
        {
            "search":  r"(?<![\$\w\d\>\"])"
                + variables_set_to_regex(find_variables(view))
                + "(?=[^\w^\d])",
            "replace": r"$\1"
        },
        #remove if const, function, class before
        {
            "search":  variables_set_to_regex(ignore_after) + r"(\s+)\$",
            "replace": r"\1\2"
        }
    ]


def in_list(region, list):
    if len(list) == 0:
        return True
    for item in list:
        if item.contains(region):
            return True
    return False


def find_variables(view):
    #find all php variables in current view
    variables = Set()
    regions = view.find_all("\$\w[\w\d]*")

    for region in regions:
        text = view.substr(region)[1:]
        if text in ignore_names:
            continue
        variables.add(text)

    return variables


def syntax_name(view):
    syntax = os.path.basename(view.settings().get('syntax'))
    syntax = os.path.splitext(syntax)[0]
    return syntax


def variables_set_to_regex(variables):
    regex = "(this|"

    for variable in variables:
        regex += variable + "|"
    regex = regex[0:-1] + ")"

    return regex


def apply_patterns(text, patterns):
    for pattern in patterns:
        text = re.sub(
            pattern["search"],
            pattern["replace"],
            text
        )
    return text


class CphpListener(sublime_plugin.EventListener):
    def on_modified(self, view):
        if syntax_name(view) == "PHP":
            # avoid heavy calculations for "hold delete/backspace and wait"
            action = view.command_history(0, True)[0]
            if action == "left_delete" or action == "right_delete":
                return
            #do not change text again if undo requested
            if view.command_history(1, True)[0] == "cphp":
                return

            #generate patterns
            #worst way, first point to optimize
            patterns = get_patterns(view)

            #get list of <? .. ?> segments
            php_regions = view.find_all(r"<\?.+?\?>")

            #get list of commented regions
            comments = view.find_all(r"(#|//).+|/\*[\w\W]+?\*/")

            #strings should be modified in the reversed order
            #to keep upper regions positions correct
            edit = None
            selection = view.sel()
            for i in range(len(selection) - 1, -1, -1):
                #do not make changes inside comments
                if len(comments) and in_list(selection[i], comments):
                    continue
                #do not make any changes outside <? ... ?> segments
                if not in_list(selection[i], php_regions):
                    continue
                line = view.line(selection[i])
                #fix line position, do not place cursor to the end of line
                to_cursor = sublime.Region(line.a, selection[i].b)

                text = view.substr(to_cursor)
                corrected = apply_patterns(text, patterns)

                if corrected != text:
                    if edit == None:
                        edit = view.begin_edit("cphp")
                    view.replace(edit, to_cursor, corrected)

            if edit != None:
                view.end_edit(edit)
