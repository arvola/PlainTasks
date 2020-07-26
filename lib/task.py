import sublime
import math
import re
from datetime import datetime

from sublime import Region
from .config import get_config
from .view_utils import extract_selector, selector_in_region, all_selectors_in_region, adjust_region
from .project import Project

# Special automatic attributes for tags
class Attribute:
    def timestamp(view):
        return datetime.now().strftime(get_config(view).date_format)


class Task:
    def __init__(self, view, region):
        self.view = view
        self.region = region
        self._indent = None
        self._title = None
        self._project = None

    def __str__(self):
        return "Task: %s" % (self.title())

    def __repr__(self):
        return '<Task title="%s" indent="%s" region="%d,%d">' % (
            self.title(),
            self.indent(),
            self.region.begin(), self.region.end())

    def title(self):
        if (self._title is None):
            title_region = selector_in_region(self.view, 'meta.item.heading.todo', self.region)
            # Skip the bullet
            start = title_region.begin() + 1
            end = title_region.end()
            # Skip whitespace
            while re.match(r'\s', self.view.substr(start)):
                start += 1

            self._title = self.view.substr(Region(start, end))
        return self._title

    def indent(self):
        """ Gets the task's indentation as a string
        """
        if (self._indent is None):
            # Region starts at the bullet, so the difference to the beginnin of line is
            # the indent.
            line = self.view.line(self.region)
            self._indent = self.view.substr(Region(line.begin(), self.region.begin() - 1))

        return self._indent

    def completed(self):
        return selector_in_region(self.view, "string.item.completed", self.region) is not None

    def pending(self):
        return selector_in_region(self.view, "markup.list.item.pending", self.region) is not None

    def cancelled(self):
        return selector_in_region(self.view, "string.item.cancelled", self.region) is not None

    def complete(self, edit):
        config = get_config(self.view)
        self.view.replace(edit, Region(self.region.begin(), self.region.begin() + 1), config.completed_task)

    def pend(self, edit):
        config = get_config(self.view)
        self.view.replace(edit, Region(self.region.begin(), self.region.begin() + 1), config.pending_task)

    def cancel(self, edit):
        config = get_config(self.view)
        self.view.replace(edit, Region(self.region.begin(), self.region.begin() + 1), config.cancelled_task)

    def add_tag(self, edit, tag, attribute = None):
        if attribute is None:
            tag = '@%s' % (tag)
        else:
            if callable(attribute):
                attr = attribute(self)
            else:
                attr = attribute

            tag = '@%s(%s)' % (tag, attr)

        heading = selector_in_region(self.view, "meta.item.heading", self.region)
        pos = heading.end()

        # Keep white space at the end. The first check is for cases where
        # the task has no title, but we don't want to also go before the whitespace
        # next to the bullet.
        while (pos > heading.begin() + 2 and re.match(r'\s', self.view.substr(pos - 1))):
            pos = pos - 1

        length = self.view.insert(edit, pos, ' ' + tag)
        self.region = Region(self.region.begin(), self.region.end() + length)

        return sublime.Region(pos, pos + length)

    def remove_tag(self, edit, tag):
        tags = all_selectors_in_region(self.view, "meta.tag.todo", self.region)
        # Delete them in reverse so the search doesn't get messed up
        tags.reverse()
        length = 0
        pos = 0
        for reg in tags:
            name = selector_in_region(self.view, "support.constant.name.tag", reg)
            if self.view.substr(name).casefold() == tag.casefold():
                erased = Region(reg.begin() - 1, reg.end())
                self.view.erase(edit, erased)
                length += erased.size()
                pos = erased.begin()
                self.region = Region(self.region.begin(), self.region.end() - length)

        return sublime.Region(pos, pos - length)

    def project(self):
        """ Gets the project hierarchy this task is under.

        Returns a list of Project objects, with the topmost project first.
        """
        if self._project is None:
            section = extract_selector(self.view, 'meta.section.todo', self.region)
            if section:
                section_begin = section.begin()
            else:
                section_begin = 0

            project_regions = self.view.find_by_selector('meta.project.todo')

            for i, region in enumerate(project_regions):
                if region.contains(self.region):
                    project_index = i
                    break

            if project_index is None:
                return None

            hierarchy = []
            project = Project(self.view, project_regions[project_index])

            hierarchy.append(project)
            depth = project.depth()
            i = project_index - 1

            while i >= 0:
                if project_regions[i].begin() < section_begin:
                    break
                project = Project(self.view, project_regions[i])
                if project.depth() < depth:
                    hierarchy.append(project)
                    depth = project.depth()
                if project.depth() == 0:
                    break
                i = i - 1

            hierarchy.reverse()
            self._project = hierarchy
        return self._project