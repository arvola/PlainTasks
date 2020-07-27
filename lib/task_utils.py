import sublime
import math
import re

from sublime import Region
from .view_utils import extract_selector, selector_in_region, all_selectors_in_region, adjust_region
from .project import Project
from .task import Task
from .config import get_config

import logging

def tasks_in_selection(view):
    selections = [it for it in view.sel()]
    tasks = []
    for sel in selections:
        item_regions = all_selectors_in_region(view, "meta.item.todo", sel, True)
        for item in item_regions:
            tasks.append(Task(view, item))
    return tasks

def project_for_task(view, task):
    """Finds the project hierarchy for the given task.

    `task` is typically a region corresponding to the meta.item.todo 
    for the task, but it can be any region.

    Example:
        project_for_task(view, region)

    Returns a list of Project instances, with top-level being first.
    """
    section = extract_selector(view, 'meta.section.todo', task)
    if section:
        section_begin = section.begin()
    else:
        section_begin = 0

    project_regions = view.find_by_selector('meta.project.todo')

    for i, region in enumerate(project_regions):
        if region.contains(task):
            project_index = i
            break

    if project_index is None:
        return None

    hierarchy = []
    project = Project(view, project_regions[project_index])

    hierarchy.append(project)
    depth = project.depth()
    i = project_index - 1

    while i >= 0:
        if project_regions[i].begin() < section_begin:
            break
        project = Project(view, project_regions[i])
        if project.depth() < depth:
            hierarchy.append(project)
            depth = project.depth()
        if project.depth() == 0:
            break
        i = i - 1

    hierarchy.reverse()
    return hierarchy

def all_sections(view):
    regions = view.find_by_selector('meta.section.todo')
    sections = []

    for region in regions:
        # Title ends two characters before the meta section begins
        title_region = extract_selector(view, 'markup.heading.section.todo', region.begin() - 2)
        title = view.substr(title_region).strip()

        sections.append({'title': title, 'region': region})

    return sections

def get_section(view, edit, section_title):
    titles = view.find_by_selector('markup.heading.section.todo')

    for region in titles:
        title = view.substr(region).strip()
        if title == section_title:
            section_region = extract_selector(view, 'meta.section.todo', region.end() + 2)
            return {'title': title, 'region': section_region}

    # Section not found, create it at the end of the file

    view.insert(edit, view.size(), "\n--- %s\n " % (section_title))

    # The region will include the newline after the title,
    # and the space we inserted
    reg = Region(view.size() - 2, view.size())
    logging.info('New section region %s has "%s"' % (reg, view.substr(reg)))
    return {'title': section_title, 'region': reg}

def all_projects_in_section(view, section):
    regions = all_selectors_in_region(view, 'meta.project.todo', section)
    projects = []
    stack = []

    for project_region in regions:
        project = Project(view, project_region)

        # We set this here instead of in the constructor of Project so that
        # there's a distinction between not having children, and not being
        # sure if there are children. This function always lists all children,
        # so we can set it to empty now.
        project.children = []

        if (len(stack) == 0):
            projects.append(project)
            stack.append(project)
        else:
            while (len(stack) > 0 and stack[-1].depth() >= project.depth()):
                stack.pop()
            if (len(stack) == 0):
                projects.append(project)
            else:
                stack[-1].children.append(project)
            stack.append(project)
    return projects

def tasks_in_region(view, region):
    tasks = []
    item_regions = all_selectors_in_region(view, "meta.item.todo", region, True)
    for item in item_regions:
        tasks.append(Task(view, item))
    return tasks

def project_in_section(view, edit, section, project_names):
    """ Finds a project in the given section, or creates it
    if it doesn't exist.

    Returns a list of 2 items, the first is the project, the second is
    a region signifying inserted text, or None if nothing was inserted.
    """
    regions = all_selectors_in_region(view, 'meta.project.todo', section)
    logging.info('Project regions in section %s' % (regions))
    logging.info('All projects everywhere %s' % (view.find_by_selector('meta.project.todo')))
    stack = []
    i = 0

    logging.info('Finding project %s' % project_names)

    for project_region in regions:
        project = Project(view, project_region)
        
        if (len(stack) > 0 and project.depth() < stack[-1].depth()):
            # Sub-project wasn't found, create the remaining levels
            return create_project(view, stack[-1].region, stack[-1].depth(), project_names[i:])

        if (project.name() != project_names[i]):
            continue
        stack.append(project)

        if (len(stack) == len(project_names)):
            return [project, None]

        i += 1  

    logging.info('Top-level project not found, creating %s' % project_names)
    # Top-level project wasn't found, create all of it
    return create_project(view, edit, section, 0, project_names)
    
def create_project(view, edit, after, depth, project_names):
    """ Creates the projects in the section.

    Returns the new project, plus a region for any text that was inserted.
    """
    pos = after.end() - 1
    config = get_config(view)

    # Go back to the last non-blank line
    while (pos > 0 and re.match(r'[\s\n\r]', view.substr(pos))):
        pos -= 1

    # Then go to the end of that line
    pos = view.line(pos).end()

    newline_added = 0
    # If it's a newline, go back one more
    if view.substr(pos - 1) == "\n":
        pos -= 1
    else:
        # If it's not a newline it's the end of the file, and
        # we need to add an extra newline
        view.insert(edit, pos, "\n")
        newline_added = 1

    a = pos
    i = 0
    for name in project_names:
        logging.info("Inserting project %s" % (name))
        inserted = view.insert(edit, pos, "\n%s%s%s:" % (depth * " ", i * config.indent(), name))
        pos += inserted
        i += 1

    return [
        Project(view, extract_selector(view, 'meta.project.todo', pos)),
        Region(a, pos + newline_added)
    ]

def move_tasks_to_section(view, edit, move_tasks, section):
    tasks = move_tasks[:]
    while len(tasks) > 0:
        task = tasks.pop(0)
        logging.info('Moving task %s to section %s' % (task, section))
        project = task.project()
        to, project_adjustment = project_in_section(view, edit, section['region'], [p.name() for p in project])

        if project_adjustment is not None:
            logging.info('Adjusting due to project insertion %s' % (project_adjustment))
            task.region = adjust_region(task.region, project_adjustment)
            section['region'] = adjust_region(section['region'], project_adjustment)
            for adjust in tasks:
                adjust.region = adjust_region(adjust.region, project_adjustment)

        logging.info('Section is now %s' % (section))
        region = Region(task.region.begin(), task.region.end())
        # Move to the beginning of the line to include the indentation
        while view.substr(region.a - 1) != "\n" and region.a > 0:
            region.a = region.a - 1

        # Reverse to signify it's a removal
        erasure = Region(region.end(), region.begin())
        content = view.substr(region)
        view.erase(edit, erasure)
        to.region = adjust_region(to.region, erasure)
        logging.info('Project to insert is %s: %s' % (to.region, view.substr(to.region)))
        # Converting the end of the region to a point seems to put it at
        # the next character AFTER the region
        insert_point = to.region.end() - 1
        logging.info('Insertion point before %s' % (insert_point))
        logging.info('Insertion point is now at "%s"' % (repr(view.substr(insert_point))))
        # Go back to the last non-blank line
        while (insert_point > 0 and re.match(r'[\s\n\r\x00]', view.substr(insert_point))):
            insert_point -= 1
            logging.info('Insertion point is now at "%s"' % (view.substr(insert_point)))

        # Then go to past the end of that line
        insert_point = view.full_line(insert_point).end()

        logging.info('Insertion point after %s' % (insert_point))

        view.insert(edit, insert_point, content)
        insertion = Region(insert_point, insert_point + len(content))

        if len(tasks) > 0:
            change_area = Region(erasure.begin(), insert_point)
            if change_area.a > change_area.b:
                # If a > b, the task was moved towards the beginning of the file
                # and adjustments need to be moved forward
                change = insertion
                # Also need to adjust the section
                section['region'].b = section['region'].b + len(content)
            else:
                # Otherwise the erased region is the change
                change = erasure
                # Also need to adjust the section
                section['region'].a = section['region'].a - len(content)
            for adjust in tasks:
                logging.info('Checking change area %s against adjust task %s' % (change_area, adjust.region))
                if change_area.intersects(adjust.region):
                    adjust.region = adjust_region(adjust.region, change)
                    logging.info('Adjusted %s' % (adjust.region))
