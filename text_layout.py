# -*- coding: utf-8 -*-
"""Pure helpers for automatic CAD text sizing and vertical stacking."""

import math


AREA_HEIGHT_RULES = (
    (100.0, 2.0),
    (500.0, 3.0),
    (1000.0, 4.0),
    (3000.0, 5.0),
    (5000.0, 5.5),
    (10000.0, 6.0),
    (25000.0, 6.5),
    (50000.0, 7.0),
)


def text_height_for_area(area_m2, default_height=5.0):
    """Return the requested DXF text height for an area in square metres."""
    if area_m2 is None:
        return float(default_height)
    try:
        area_m2 = abs(float(area_m2))
    except (TypeError, ValueError):
        return float(default_height)
    if not math.isfinite(area_m2):
        return float(default_height)
    for maximum_area, height in AREA_HEIGHT_RULES:
        if area_m2 <= maximum_area:
            return height
    return 7.0


def vertical_offsets(text_count):
    """Return top-to-bottom row offsets around one selected anchor point."""
    text_count = max(0, int(text_count))
    rows_above = max(0, (text_count - 1) // 2)
    return [rows_above - index for index in range(text_count)]


def line_pitch(text_height):
    """Use one text height plus a gap equal to half the text height."""
    return float(text_height) * 1.5
