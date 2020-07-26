# coding: utf-8
import sublime, sublime_plugin
import itertools
import logging
from .config import get_config

def get_all_projects_and_separators(view):
    # because tmLanguage need \n to make background full width of window
    # multiline headers are possible, thus we have to split em to be sure that
    # one header == one line
    projects = itertools.chain(*[view.lines(r) for r in view.find_by_selector('keyword.control.header.todo')])
    return sorted(list(projects) +
                  view.find_by_selector('meta.punctuation.separator.todo'))


class PlainTasksBase(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        self.config = get_config(self.view)
        self.runCommand(edit, **kwargs)

    def format_line_end(self, tag, tznow):
        try:
            date = tznow.strftime(self.date_format).decode(self.sys_enc)
        except:
            date = tznow.strftime(self.date_format)
        done_line_end = ' %s%s%s' % (tag, self.before_date_space, date if self.done_date else '')
        return done_line_end.replace('  ', ' ').rstrip(), date


class PlainTasksEnabled(sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.score_selector(0, "text.todo") > 0

    is_visible = is_enabled


class PlainTasksFold(PlainTasksEnabled):
    def exec_folding(self, visible_region):
        self.view.unfold(sublime.Region(0, self.view.size()))
        for i, d in enumerate(visible_region):
            if not i:  # beginning of document
                self.folding(0, d.a - 1)
            else:  # all regions within
                self.folding(visible_region[i-1].b + 1, d.a - 1)
        if d:  # ending of document
            self.folding(d.b + 1, self.view.size())

    def folding(self, start, end):
        if start < end:
            self.view.fold(sublime.Region(start, end))

    def add_projects_and_notes(self, task_regions):
        '''Context is important, if task has note and belongs to projects, make em visible'''
        def add_note(region):
            # refactor: method in ArchiveCommand
            next_line_begins = region.end() + 1
            while self.view.scope_name(next_line_begins) == 'text.todo notes.todo ':
                note = self.view.line(next_line_begins)
                if note not in task_regions:
                    task_regions.append(note)
                next_line_begins = self.view.line(next_line_begins).end() + 1

        projects = [r for r in get_all_projects_and_separators(self.view) if r.a < task_regions[~0].a]
        for d in reversed(task_regions):
            add_note(d)
            for p in reversed(projects):
                # refactor: different implementation in ArchiveCommand
                project_block = self.view.indented_region(p.end() + 1)
                due_block     = self.view.indented_region(d.begin())
                if all((p not in task_regions, project_block.contains(due_block))):
                    task_regions.append(p)
                    add_note(p)
                if self.view.indented_region(p.begin()).empty():
                    break
        task_regions.sort()
        return task_regions
