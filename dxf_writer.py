# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Conservative ASCII DXF writer for maximum AutoCAD compatibility.

The file intentionally contains only the ENTITIES section documented by
Autodesk as a valid minimal DXF.  It uses pre-R13 LINE, POINT, and TEXT
entities, so no symbol tables, handles, owner references, blocks, or subclass
markers need to be kept in sync. Connected source geometry is retained as
old-style R12 POLYLINE/VERTEX/SEQEND entities.
"""

import math
import os

from qgis.core import QgsGeometry, QgsWkbTypes


class SimpleDxfWriter(object):
    def __init__(self, path):
        self.path = path
        self.layers = set()
        self.f = None
        self._started = False
        self._ended = False
        self._entity_count = 0

    def add_layer(self, name, color=7):
        # Minimal DXF files may reference a layer without a LAYER table.
        # AutoCAD creates it automatically with color 7 and CONTINUOUS
        # linetype.
        self.layers.add(str(name or '0'))

    def _safe_number(self, value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(
                'DXF coordinate is not a finite number: %r' %
                value)
        return format(number, '.15g')

    def _safe_text(self, value):
        text = str(value if value is not None else '')
        text = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
        text = text.replace('\x00', '')[:250]
        safe = []
        for char in text:
            codepoint = ord(char)
            if 32 <= codepoint <= 126:
                safe.append(char)
            elif codepoint <= 0xFFFF:
                safe.append('\\U+%04X' % codepoint)
            else:
                safe.append('?')
        return ''.join(safe)

    def _write_pair(self, code, value):
        if self.f is None:
            raise RuntimeError('DXF writer is not open.')
        code_text = str(code)
        value_text = str(value)
        if (
            '\n' in code_text
            or '\r' in code_text
            or '\n' in value_text
            or '\r' in value_text
        ):
            raise ValueError(
                'A DXF group code and value must each occupy one line.')
        self.f.write(code_text + '\n')
        self.f.write(value_text + '\n')

    def _require_open(self):
        if not self._started or self.f is None:
            raise RuntimeError(
                'DXF writer must be started before adding entities.')
        if self._ended:
            raise RuntimeError('DXF writer has already been finalized.')

    def begin(self):
        if self._started:
            raise RuntimeError('DXF writer has already been started.')
        # Explicit Windows CRLF line endings maximize compatibility with
        # AutoCAD releases that are stricter than GDAL/QGIS DXF readers.
        self.f = open(self.path, 'w', encoding='ascii', newline='\r\n')
        self._started = True
        self._write_pair(0, 'SECTION')
        self._write_pair(2, 'ENTITIES')

    def add_line(self, x1, y1, x2, y2, layer):
        self._require_open()
        x1 = self._safe_number(x1)
        y1 = self._safe_number(y1)
        x2 = self._safe_number(x2)
        y2 = self._safe_number(y2)
        if x1 == x2 and y1 == y2:
            return
        self._write_pair(0, 'LINE')
        self._write_pair(8, layer)
        self._write_pair(10, x1)
        self._write_pair(20, y1)
        self._write_pair(30, 0.0)
        self._write_pair(11, x2)
        self._write_pair(21, y2)
        self._write_pair(31, 0.0)
        self._entity_count += 1

    def add_point(self, x, y, layer):
        self._require_open()
        self._write_pair(0, 'POINT')
        self._write_pair(8, layer)
        self._write_pair(10, self._safe_number(x))
        self._write_pair(20, self._safe_number(y))
        self._write_pair(30, 0.0)
        self._entity_count += 1

    def add_text(self, x, y, text, layer, height=20.0, angle=0.0):
        self._require_open()
        safe_text = self._safe_text(text)
        if not safe_text:
            return
        self._write_pair(0, 'TEXT')
        self._write_pair(8, layer)
        self._write_pair(10, self._safe_number(x))
        self._write_pair(20, self._safe_number(y))
        self._write_pair(30, 0.0)
        self._write_pair(40, self._safe_number(height))
        self._write_pair(1, safe_text)
        self._write_pair(50, self._safe_number(angle))
        self._entity_count += 1

    def add_lwpolyline(self, points, layer, closed=False):
        # Old-style POLYLINE is used instead of LWPOLYLINE. It keeps each
        # source ring/line connected while remaining compatible with R12.
        if not points:
            return
        vertices = list(points)
        if len(vertices) == 1:
            self.add_point(vertices[0].x(), vertices[0].y(), layer)
            return

        if closed and len(vertices) > 2:
            first = vertices[0]
            last = vertices[-1]
            if float(
                first.x()) != float(
                last.x()) or float(
                first.y()) != float(
                    last.y()):
                # Keep an explicit closing vertex as well as flag 70 = 1.
                # Some non-Autodesk viewers ignore the closed flag alone.
                vertices.append(first)

        self._require_open()
        self._write_pair(0, 'POLYLINE')
        self._write_pair(8, layer)
        self._write_pair(66, 1)
        self._write_pair(10, 0.0)
        self._write_pair(20, 0.0)
        self._write_pair(30, 0.0)
        self._write_pair(70, 1 if closed else 0)
        for point in vertices:
            self._write_pair(0, 'VERTEX')
            self._write_pair(8, layer)
            self._write_pair(10, self._safe_number(point.x()))
            self._write_pair(20, self._safe_number(point.y()))
            self._write_pair(30, 0.0)
            self._write_pair(70, 0)
        self._write_pair(0, 'SEQEND')
        self._write_pair(8, layer)
        self._entity_count += 1

    def add_geometry(self, geom, layer):
        if geom is None or geom.isEmpty():
            return
        try:
            working = QgsGeometry(geom)
            working.convertToStraightSegment()

            wkb = working.wkbType()
            geom_type = QgsWkbTypes.geometryType(wkb)
            is_multi = QgsWkbTypes.isMultiType(wkb)

            if geom_type == QgsWkbTypes.PointGeometry:
                if is_multi:
                    for point in working.asMultiPoint():
                        self.add_point(point.x(), point.y(), layer)
                else:
                    point = working.asPoint()
                    self.add_point(point.x(), point.y(), layer)
                return

            if geom_type == QgsWkbTypes.LineGeometry:
                if is_multi:
                    for line in working.asMultiPolyline():
                        self.add_lwpolyline(line, layer, closed=False)
                else:
                    self.add_lwpolyline(
                        working.asPolyline(), layer, closed=False)
                return

            if geom_type == QgsWkbTypes.PolygonGeometry:
                if is_multi:
                    for polygon in working.asMultiPolygon():
                        for ring in polygon:
                            self.add_lwpolyline(ring, layer, closed=True)
                else:
                    for ring in working.asPolygon():
                        self.add_lwpolyline(ring, layer, closed=True)
                return

            # Geometry collections are handled recursively where supported.
            for part in working.asGeometryCollection():
                self.add_geometry(part, layer)
        except Exception as exc:
            raise RuntimeError(
                'A source geometry could not be converted to DXF: %s' %
                exc)

    def end(self):
        self._require_open()
        if self._entity_count == 0:
            raise RuntimeError(
                'No valid geometry or text entities were produced for the '
                'DXF output.')
        self._write_pair(0, 'ENDSEC')
        self._write_pair(0, 'EOF')
        self.f.close()
        self.f = None
        self._ended = True

    def abort(self):
        if self.f is not None:
            try:
                self.f.close()
            except OSError:
                self.f = None
            else:
                self.f = None

    @staticmethod
    def validate_file(path):
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise RuntimeError('DXF output was not created or is empty.')
        with open(path, 'r', encoding='ascii') as stream:
            lines = [line.rstrip('\r\n') for line in stream]
        if len(lines) % 2 != 0:
            raise RuntimeError(
                'Invalid DXF structure: group-code pairs are incomplete.')
        pairs = list(zip(lines[0::2], lines[1::2]))
        if pairs[:2] != [('0', 'SECTION'), ('2', 'ENTITIES')]:
            raise RuntimeError(
                'Invalid DXF structure: ENTITIES section is missing.')
        if pairs[-2:] != [('0', 'ENDSEC'), ('0', 'EOF')]:
            raise RuntimeError(
                'Invalid DXF structure: ENDSEC or EOF marker is missing.')

        entity_requirements = {
            'LINE': {'8', '10', '20', '11', '21'},
            'POLYLINE': {'8', '66', '10', '20', '70'},
            'VERTEX': {'8', '10', '20', '70'},
            'SEQEND': {'8'},
            'POINT': {'8', '10', '20'},
            'TEXT': {'8', '10', '20', '40', '1'},
        }
        records = []
        current = None
        for code, value in pairs:
            try:
                int(code)
            except ValueError:
                raise RuntimeError('Invalid DXF group code: %s' % code)
            if code == '0':
                if current is not None:
                    records.append(current)
                current = [value, set()]
            elif current is not None:
                current[1].add(code)
        if current is not None:
            records.append(current)

        entity_count = 0
        for entity_name, codes in records:
            required = entity_requirements.get(entity_name)
            if required is None:
                continue
            if entity_name in ('LINE', 'POLYLINE', 'POINT', 'TEXT'):
                entity_count += 1
            missing = required.difference(codes)
            if missing:
                raise RuntimeError(
                    'Invalid %s entity: missing group code(s) %s.' %
                    (entity_name, ', '.join(sorted(missing)))
                )
        if entity_count == 0:
            raise RuntimeError(
                'DXF output contains no readable POLYLINE, LINE, POINT, or '
                'TEXT entities.')
