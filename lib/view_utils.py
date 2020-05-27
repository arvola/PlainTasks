"""
https://github.com/SublimeText/PackageDev/blob/master/plugins_/lib/view_utils.py

Copyright (c) 2010-2014 Guillermo López-Anglada (Vintageous)
Copyright (c) 2012-2019 FichteFoll <fichtefoll2@googlemail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sublime
from sublime import Region

def has_file_ext(view, ext):
    """Returns `True` if `view` has file extension `ext`.
    `ext` may be specified with or without leading ".".
    """
    if not view.file_name() or not ext.strip().replace('.', ''):
        return False

    if not ext.startswith('.'):
        ext = '.' + ext

    return view.file_name().endswith(ext)


def base_scope(view):
    """Returns the view's base scope.
    """
    return view.scope_name(0).split(' ', 1)[0]


def rowcount(view):
    """Returns the 1-based number of rows in ``view``.
    """
    return view.rowcol(view.size())[0] + 1


def rowwidth(view, row):
    """Returns the 1-based number of characters of ``row`` in ``view``.
    """
    return view.rowcol(view.line(view.text_point(row, 0)).end())[1] + 1


def relative_point(view, row=0, col=0, p=None):
    """Returns a point (int) to the given coordinates.

    Supports relative (negative) parameters and checks if they are in the
    bounds (other than `View.text_point()`).

    If p (indexable -> `p[0]`, `len(p) == 2`; preferrably a tuple) is
    specified, row and col parameters are overridden.
    """
    if p is not None:
        if len(p) != 2:
            raise TypeError("Coordinates have 2 dimensions, not %d" % len(p))
        (row, col) = p

    # shortcut
    if row == -1 and col == -1:
        return view.size()

    # calc absolute coords and check if coords are in the bounds
    rowc = rowcount(view)
    if row < 0:
        row = max(rowc + row, 0)
    else:
        row = min(row, rowc - 1)

    roww = rowwidth(view, row)
    if col < 0:
        col = max(roww + col, 0)
    else:
        col = min(col, roww - 1)

    return view.text_point(row, col)


def coorded_region(view, reg1=None, reg2=None, rel=None):
    """Turn two coordinate pairs into a region.

    The pairs are checked for boundaries by `relative_point`.

    You may also supply a `rel` parameter which will determine the
    Region's end point relative to `reg1`, as a pair. The pairs are
    supposed to be indexable and have a length of 2. Tuples are preferred.

    Defaults to the whole buffer (`reg1=(0, 0), reg2=(-1, -1)`).

    Examples:
    coorded_region(view, (20, 0), (22, -1))    # normal usage
    coorded_region(view, (20, 0), rel=(2, -1)) # relative, works because 0-1=-1
    coorded_region(view, (22, 6), rel=(2, 15)) # relative, ~ more than 3 lines,
                                               # if line 25 is long enough

    """
    reg1 = reg1 or (0, 0)
    if rel:
        reg2 = (reg1[0] + rel[0], reg1[1] + rel[1])
    else:
        reg2 = reg2 or (-1, -1)

    p1 = relative_point(view, p=reg1)
    p2 = relative_point(view, p=reg2)
    return Region(p1, p2)


def coorded_substr(view, reg1=None, reg2=None, rel=None):
    """Returns the string of two coordinate pairs forming a region.

    The pairs are supporsed to be indexable and have a length of 2.
    Tuples are preferred.

    Defaults to the whole buffer.

        For examples, see `coorded_region`.
    """
    return view.substr(coorded_region(view, reg1, reg2))


def get_text(view):
    """Returns the whole string of a buffer. Alias for `coorded_substr(view)`.
    """
    return coorded_substr(view)


def get_viewport_point(view):
    """Returns the text point of the current viewport.
    """
    return view.layout_to_text(view.viewport_position())


def get_viewport_coords(view):
    """Returns the text coordinates of the current viewport.
    """
    return view.rowcol(get_viewport_point(view))

def adjust_region(region, adjustment):
    """Modifies the given region to account for added or removed text.

    Adjustment should be a Region for the added text. If text was removed
    it should have b as the starting position of removal, and a as the
    start minus the length
    """
    if adjustment.size() > 0 and region.begin() > adjustment.a:
        if adjustment.a > adjustment.b:
            return sublime.Region(region.a - adjustment.size(), region.b - adjustment.size());
        else:
            return sublime.Region(region.a + adjustment.size(), region.b + adjustment.size());

    return region;


def set_viewport(view, row, col=None):
    """Sets the current viewport from either a text point or relative coords.

        set_viewport(view, 892)      # point
        set_viewport(view, 2, 27)    # coords1
        set_viewport(view, (2, 27))  # coords2
    """
    if col is None:
        pos = row

    if type(row) == tuple:
        pos = relative_point(view, p=row)
    else:
        pos = relative_point(view, row, col)

    view.set_viewport_position(view.text_to_layout(pos))


def extract_selector(view, selector, point):
    """Works similar to view.extract_scope except that you may define the
    selector (scope) on your own and it does not use the point's scope by
    default.

    Example:
        extract_selector(view, "source string", view.sel()[0].begin())

    Returns the Region for the out-most "source string" which contains the
    beginning of the first selection.
    """
    regs = view.find_by_selector(selector)
    for reg in regs:
        if reg.contains(point):
            return reg
    return None

def selector_in_region(view, selector, region):
    """Searches for the first occurrence of a selector fully inside the
    given Region.

    Example:
        selector_in_region(view, "source string", view.sel()[0])

    Returns the Region for the first match.
    """
    regs = view.find_by_selector(selector)
    for reg in regs:
        if region.contains(reg):
            return reg
    return None

def all_selectors_in_region(view, selector, region, partial = False):
    """Searches for all occurrences of a selector inside the
    given Region.

    If partial is True, also includes selectors that are partially inside
    the region.

    Example:
        all_selectors_in_region(view, "source string", view.sel()[0])

    Returns all matching Regions.
    """
    if partial is True:
        return [it for it in view.find_by_selector(selector) if region.intersects(it)]
    else:
        return [it for it in view.find_by_selector(selector) if region.contains(it)]
