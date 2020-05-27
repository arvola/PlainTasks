import sublime
import math
from sublime import Region
from .view_utils import extract_selector, selector_in_region, all_selectors_in_region, adjust_region

import logging

def tasks_in_selection(view):
    selections = [it for it in view.sel()]
    tasks = []
    for sel in selections:
        item_regions = all_selectors_in_region(view, "meta.item.todo", sel, True)
        for item in item_regions:
            tasks.append(item)
    return tasks

def project_name(view, project):
    # Project region starts at the colon, -1 is on the title
    title_region = extract_selector(view, 'keyword.project.title.todo', project.begin() - 1)
    return view.substr(title_region)

def project_depth(view, project):
    i = project.begin()

    while view.substr(i - 1) != "\n" and i > 0:
        i = i - 1

    indent_region = extract_selector(view, 'keyword.project.indent.todo', i)

    if indent_region is None:
        return 0
    else:
        return indent_region.size()

def project_for_task(view, task):
    """Finds the project hierarchy for the given task.

    `task` is expected to be a region corresponding to the meta.item.todo 
    for the task.

    Example:
        project_for_task(view, region)

    Returns a list of project names that make up the hierarchy, with top-
    level first.
    """
    section = extract_selector(view, 'meta.section.todo', task)
    if section:
        section_begin = section.begin()
    else:
        section_begin = 0

    projects = view.find_by_selector('meta.project.todo')

    for i, project in enumerate(projects):
        if project.contains(task):
            project_index = i
            break

    if project_index is None:
        return None

    hierarchy = []
    hierarchy.append(project_name(view, projects[project_index]))
    depth = project_depth(view, projects[project_index])
    i = project_index - 1

    while i >= 0:
        logging.info(i)
        if projects[i].begin() < section_begin:
            break
        d = project_depth(view, projects[i])
        if d < depth:
            hierarchy.append(project_name(view, projects[i]))
            depth = d
        if d == 0:
            break
        i = i - 1

    hierarchy.reverse()
    return hierarchy
