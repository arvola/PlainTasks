import sublime
import math

from sublime import Region
from .view_utils import extract_selector, selector_in_region, all_selectors_in_region, adjust_region

class Project:
    def __init__(self, view, region):
        self.view = view
        self.region = region
        self.children = None
        self._depth = None
        self._name = None

    def __str__(self):
        return "Project: %s" % (self.name())

    def __repr__(self):
        return '<Project name="%s" depth="%d" region="%d,%d" childcount="%s">' % (
            self.name(),
            self.depth(),
            self.region.begin(), self.region.end(),
            "unknown" if self.children is None else len(self.children))

    def name(self):
        if (self._name is None):
            title_region = extract_selector(self.view, 'keyword.project.title.todo', self.region.begin() - 1)
            self._name = self.view.substr(title_region)
        return self._name

    def depth(self):
        if (self._depth is None):
            i = self.region.begin()

            while self.view.substr(i - 1) != "\n" and i > 0:
                i = i - 1

            indent_region = extract_selector(self.view, 'keyword.project.indent.todo', i)

            if indent_region is None:
                self._depth = 0
            else:
                self._depth = indent_region.size()
        return self._depth
