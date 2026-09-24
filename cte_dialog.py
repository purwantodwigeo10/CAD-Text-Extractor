# -*- coding: utf-8 -*-
import os
import re
import traceback
import webbrowser
import math

from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QPushButton, QTextEdit, QVBoxLayout
)
from qgis.PyQt.QtGui import QPixmap, QDesktopServices
from qgis.core import (
    QgsDistanceArea, QgsMapLayerType, QgsProject, QgsUnitTypes,
    QgsVectorLayer, QgsWkbTypes
)

from .licensehub_cte_qgis import LicenseManager, PRODUCT_NAME, PRODUCT_CODE, FIXED_CODE, TRIAL_LIMIT
from .dxf_writer import SimpleDxfWriter
from .text_layout import line_pitch, text_height_for_area, vertical_offsets

HELP_URL = 'https://aktivasi.ruangspasial.my.id/help/cad-text-extractor-qgis'


class ActivationDialog(QDialog):
    def __init__(self, lm, parent=None):
        super(ActivationDialog, self).__init__(parent)
        self.lm = lm
        self.setWindowTitle('License Activation')
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setSizeGripEnabled(True)
        self.resize(700, 190)
        self.setStyleSheet("QDialog { background-color: white; } QGroupBox { background-color: white; border: 1px solid #d9d9d9; margin-top: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; background-color: white; }")
        self._build_ui()
        self.refresh_status(True)

    def _build_ui(self):
        main = QVBoxLayout(self)
        grid = QGridLayout()
        self.lbl_status = QLabel('-')
        self.txt_device_id = QLineEdit(); self.txt_device_id.setReadOnly(True)
        self.btn_copy = QPushButton('Copy Device ID'); self.btn_copy.clicked.connect(self.copy_device_id)
        self.lbl_trial = QLabel('-')
        self.txt_code = QLineEdit(); self.txt_code.setPlaceholderText('Enter the activation code from License Hub')
        grid.addWidget(QLabel('Activation Status'), 0, 0); grid.addWidget(self.lbl_status, 0, 1, 1, 2)
        grid.addWidget(QLabel('Device ID'), 1, 0); grid.addWidget(self.txt_device_id, 1, 1); grid.addWidget(self.btn_copy, 1, 2)
        grid.addWidget(QLabel('Trial Usage'), 2, 0); grid.addWidget(self.lbl_trial, 2, 1, 1, 2)
        grid.addWidget(QLabel('Activation Code'), 3, 0); grid.addWidget(self.txt_code, 3, 1, 1, 2)
        main.addLayout(grid)
        row = QHBoxLayout()
        self.btn_request = QPushButton('Submit Request'); self.btn_request.clicked.connect(self.open_request_page)
        self.btn_activate = QPushButton('Activate'); self.btn_activate.clicked.connect(self.activate_license)
        self.btn_refresh = QPushButton('Refresh Status'); self.btn_refresh.clicked.connect(lambda: self.refresh_status(False))
        self.btn_close = QPushButton('Close'); self.btn_close.clicked.connect(self.accept)
        row.addStretch(1); row.addWidget(self.btn_request); row.addWidget(self.btn_activate); row.addWidget(self.btn_refresh); row.addWidget(self.btn_close)
        main.addLayout(row)

    def refresh_status(self, quiet=True):
        self.txt_device_id.setText(self.lm.get_device_id())
        status = self.lm.status_text()
        self.lbl_status.setText(status)
        remaining = self.lm.trial_remaining()
        self.lbl_trial.setText('%s/%s used, %s remaining' % (TRIAL_LIMIT - remaining, TRIAL_LIMIT, remaining))
        if status.startswith('Active'):
            self.lbl_status.setStyleSheet('font-weight:bold;color:#0B7A2A;')
        elif status.startswith('Trial'):
            self.lbl_status.setStyleSheet('font-weight:bold;color:#B35C00;')
        elif status.startswith('Expired'):
            self.lbl_status.setStyleSheet('font-weight:bold;color:#B00020;')
        else:
            self.lbl_status.setStyleSheet('font-weight:bold;color:#7A003C;')
        if not quiet:
            ok, msg = self.lm.refresh_activation_from_server()
            self.txt_device_id.setText(self.lm.get_device_id())
            self.lbl_status.setText(self.lm.status_text())
            remaining = self.lm.trial_remaining()
            self.lbl_trial.setText('%s/%s used, %s remaining' % (TRIAL_LIMIT - remaining, TRIAL_LIMIT, remaining))
            if ok is True:
                QMessageBox.information(self, PRODUCT_NAME, 'License status was refreshed from the website.')
            elif ok is False:
                QMessageBox.warning(self, PRODUCT_NAME, msg or 'License is not active.')
            else:
                QMessageBox.warning(self, PRODUCT_NAME, msg or 'License status could not be confirmed from the website.')

    def copy_device_id(self):
        QApplication.clipboard().setText(self.txt_device_id.text().strip())
        QMessageBox.information(self, PRODUCT_NAME, 'Device ID copied successfully.')

    def open_request_page(self):
        try:
            self.lm.open_request_url()
            QMessageBox.information(self, PRODUCT_NAME, 'The activation request page has been opened. Please submit the request with Product Code CDTER and Fixed Code SMI.')
        except Exception as e:
            QMessageBox.warning(self, PRODUCT_NAME, 'Failed to open request page: %s' % e)

    def activate_license(self):
        ok, msg = self.lm.activate(self.txt_code.text().strip())
        self.refresh_status(True)
        if ok:
            QMessageBox.information(self, PRODUCT_NAME, msg)
            self.accept()
        else:
            QMessageBox.warning(self, PRODUCT_NAME, msg)


class CADTextExtractorDialog(QDialog):
    def __init__(self, iface, parent=None):
        super(CADTextExtractorDialog, self).__init__(parent)
        self.iface = iface
        self.lm = LicenseManager()
        self._processing = False
        self.setWindowTitle('CAD Text Extractor')
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setSizeGripEnabled(True)
        self.resize(860, 650)
        self.setStyleSheet("QDialog { background-color: white; } QGroupBox { background-color: white; border: 1px solid #d9d9d9; margin-top: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; background-color: white; } QTextEdit { background-color: white; } QLabel { background-color: white; }")
        self._build_ui()
        self.load_layers()
        self.refresh_license_status()

    def _build_ui(self):
        main = QVBoxLayout(self)
        hero = QGroupBox()
        hero_layout = QHBoxLayout(hero)
        self.lbl_logo = QLabel()
        self.lbl_logo.setStyleSheet('background-color: white;')
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            self.lbl_logo.setPixmap(pix.scaled(155, 155, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.lbl_logo.setMinimumWidth(170)
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.lbl_logo)

        center = QVBoxLayout()
        self.lbl_title = QLabel("<span style='font-size:24px; font-weight:700;'>CAD Text Extractor</span>")
        self.lbl_title.setTextFormat(Qt.RichText)
        self.lbl_desc = QLabel('CAD Text Extractor exports selected attribute fields as CAD text and source geometries into a CAD-compatible DXF output.')
        self.lbl_desc.setWordWrap(True)
        center.addWidget(self.lbl_title); center.addWidget(self.lbl_desc); center.addStretch(1)
        hero_layout.addLayout(center, 1)

        right = QVBoxLayout()
        self.lbl_plugin_status = QLabel(); self.lbl_plugin_status.setTextFormat(Qt.RichText)
        self.lbl_activation = QLabel(); self.lbl_activation.setTextFormat(Qt.RichText)
        self.btn_manage = QPushButton('Manage Activation'); self.btn_manage.clicked.connect(self.show_activation_dialog)
        self.btn_help_main = QPushButton('User Guide and Activation'); self.btn_help_main.clicked.connect(self.open_help_page)
        right.addWidget(self.lbl_plugin_status, 0, Qt.AlignRight); right.addWidget(self.lbl_activation, 0, Qt.AlignRight); right.addWidget(self.btn_manage, 0, Qt.AlignRight); right.addWidget(self.btn_help_main, 0, Qt.AlignRight); right.addStretch(1)
        hero_layout.addLayout(right)
        main.addWidget(hero)

        tool_box = QGroupBox('CAD Export Workspace')
        layout = QVBoxLayout(tool_box)

        grid = QGridLayout()
        self.txt_input_file = QLineEdit()
        self.txt_input_file.setPlaceholderText('Optional: browse source features directly from a folder')
        self.btn_input_file = QPushButton('Browse Input...')
        self.btn_input_file.clicked.connect(self.choose_input_file)
        self.cmb_layer = QComboBox()
        self.cmb_layer.currentIndexChanged.connect(self.on_layer_changed)
        self.cmb_placement = QComboBox()
        self.cmb_placement.addItems(['Auto', 'Centroid (Polygon)', 'Inside Point (Polygon)', 'Midpoint (Line)', 'Point (As-is)'])
        self.txt_output = QLineEdit()
        self.btn_output = QPushButton('Browse Output...')
        self.btn_output.clicked.connect(self.choose_output)
        self.cmb_dxf_version = QComboBox()
        self.cmb_dxf_version.addItems(['DXF_R12_ASCII (Maximum Compatibility)'])

        grid.addWidget(QLabel('Input Features From Folder'), 0, 0); grid.addWidget(self.txt_input_file, 0, 1); grid.addWidget(self.btn_input_file, 0, 2)
        grid.addWidget(QLabel('Input Layer From Project'), 1, 0); grid.addWidget(self.cmb_layer, 1, 1, 1, 2)
        grid.addWidget(QLabel('Placement Mode'), 2, 0); grid.addWidget(self.cmb_placement, 2, 1, 1, 2)
        grid.addWidget(QLabel('Output CAD File (.dxf)'), 3, 0); grid.addWidget(self.txt_output, 3, 1); grid.addWidget(self.btn_output, 3, 2)
        grid.addWidget(QLabel('DXF Compatibility Mode'), 4, 0); grid.addWidget(self.cmb_dxf_version, 4, 1, 1, 2)
        layout.addLayout(grid)

        fields_box = QGroupBox('Fields to Export (Order Follows Source Field Order)')
        fields_layout = QVBoxLayout(fields_box)
        btn_row = QHBoxLayout()
        self.btn_select_all = QPushButton('Select All'); self.btn_select_all.clicked.connect(self.select_all_fields)
        self.btn_unselect_all = QPushButton('Unselect All'); self.btn_unselect_all.clicked.connect(self.unselect_all_fields)
        btn_row.addStretch(1); btn_row.addWidget(self.btn_select_all); btn_row.addWidget(self.btn_unselect_all)
        fields_layout.addLayout(btn_row)
        self.lst_fields = QListWidget(); self.lst_fields.setMinimumHeight(150)
        fields_layout.addWidget(self.lst_fields)
        layout.addWidget(fields_box)

        progress_row = QHBoxLayout()
        self.lbl_progress = QLabel('Ready')
        self.lbl_progress.setMinimumWidth(190)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('%p%')
        self.progress_bar.setTextVisible(True)
        progress_row.addWidget(self.lbl_progress)
        progress_row.addWidget(self.progress_bar, 1)
        layout.addLayout(progress_row)

        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMinimumHeight(190)
        layout.addWidget(self.log)
        main.addWidget(tool_box)

        bottom = QHBoxLayout()
        self.btn_run = QPushButton('Run'); self.btn_run.clicked.connect(self.run_tool)
        self.btn_cancel = QPushButton('Cancel'); self.btn_cancel.clicked.connect(self.close)
        bottom.addStretch(1); bottom.addWidget(self.btn_run); bottom.addWidget(self.btn_cancel)
        main.addLayout(bottom)

        self._analysis_controls = (
            self.btn_manage,
            self.btn_help_main,
            self.txt_input_file,
            self.btn_input_file,
            self.cmb_layer,
            self.cmb_placement,
            self.txt_output,
            self.btn_output,
            self.cmb_dxf_version,
            self.lst_fields,
            self.btn_select_all,
            self.btn_unselect_all,
        )

    def open_help_page(self):
        try:
            QDesktopServices.openUrl(QUrl(HELP_URL))
        except Exception as e:
            QMessageBox.warning(self, PRODUCT_NAME, 'Failed to open help page: %s' % e)

    def show_activation_dialog(self):
        dlg = ActivationDialog(self.lm, self)
        dlg.exec_()
        self.refresh_license_status()

    def refresh_license_status(self):
        self.lbl_plugin_status.setText("<b><span style='color:#0B7A2A;'>Plugin Status : Ready</span></b> | <span style='color:#2D6A4F;'>Background Service: Enabled</span>")
        status = self.lm.status_text()
        if status.startswith('Active'):
            txt = "<b><span style='color:#0B7A2A;'>Activation : Active</span></b>"
        elif status.startswith('Trial'):
            txt = "<b><span style='color:#B35C00;'>Activation : Trial</span></b>"
        elif status.startswith('Expired'):
            txt = "<b><span style='color:#B00020;'>Activation : Expired</span></b>"
        else:
            txt = "<b><span style='color:#7A003C;'>Activation : Deactivated</span></b>"
        self.lbl_activation.setText(txt)

    def log_msg(self, msg):
        self.log.append(str(msg))

    def _set_progress(self, value, message=None):
        value = max(0, min(100, int(value)))
        value_changed = self.progress_bar.value() != value
        message_changed = (
            message is not None and self.lbl_progress.text() != message)
        if value_changed:
            self.progress_bar.setValue(value)
        if message is not None:
            self.lbl_progress.setText(message)
        if value_changed or message_changed:
            QApplication.processEvents()

    def _set_progress_fraction(
            self, start, end, completed, total, message=None):
        total = max(1, int(total))
        completed = max(0, min(int(completed), total))
        value = int(start + ((end - start) * completed / float(total)))
        self._set_progress(value, message)

    def _set_processing_state(self, active):
        self._processing = bool(active)
        for widget in self._analysis_controls:
            widget.setEnabled(not self._processing)
        self.btn_run.setEnabled(not self._processing)
        self.btn_cancel.setEnabled(not self._processing)

    def closeEvent(self, event):
        if self._processing:
            event.ignore()
            return
        super(CADTextExtractorDialog, self).closeEvent(event)

    def load_layers(self):
        self.cmb_layer.clear()
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.type() == QgsMapLayerType.VectorLayer:
                self.cmb_layer.addItem(lyr.name(), lyr.id())
        self.on_layer_changed()

    def _open_vector_from_path(self, path):
        if not path or not os.path.exists(path):
            return None
        layer = QgsVectorLayer(path, os.path.basename(path), 'ogr')
        return layer if layer.isValid() else None

    def current_layer(self):
        input_path = self.txt_input_file.text().strip() if hasattr(self, 'txt_input_file') else ''
        if input_path:
            return self._open_vector_from_path(input_path)
        lid = self.cmb_layer.currentData()
        if not lid:
            return None
        return QgsProject.instance().mapLayer(lid)

    def on_layer_changed(self):
        self.lst_fields.clear()
        lyr = self.current_layer()
        if lyr is None:
            return
        for f in lyr.fields():
            if f.name().lower() in ('fid', 'objectid'):
                pass
            item = QListWidgetItem(f.name())
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.lst_fields.addItem(item)
        self._auto_placement(lyr)

    def _auto_placement(self, lyr):
        if self.cmb_placement.currentText() != 'Auto':
            return
        geom_type = lyr.geometryType()
        if geom_type == QgsWkbTypes.PolygonGeometry:
            self.cmb_placement.setCurrentText('Inside Point (Polygon)')
        elif geom_type == QgsWkbTypes.LineGeometry:
            self.cmb_placement.setCurrentText('Midpoint (Line)')
        else:
            self.cmb_placement.setCurrentText('Point (As-is)')

    def choose_input_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Select source features from folder',
            '',
            'Vector Data (*.shp *.gpkg *.geojson *.json *.kml *.tab);;All Files (*.*)'
        )
        if path:
            layer = self._open_vector_from_path(path)
            if layer is None:
                QMessageBox.warning(self, PRODUCT_NAME, 'The selected input data cannot be opened as a valid vector layer.')
                return
            self.txt_input_file.setText(path)
            self.on_layer_changed()
            self.log_msg('Input selected from folder: %s' % path)

    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Save CAD output', '', 'DXF File (*.dxf)')
        if path:
            if not path.lower().endswith('.dxf'):
                path += '.dxf'
            self.txt_output.setText(path)

    def select_all_fields(self):
        for i in range(self.lst_fields.count()):
            self.lst_fields.item(i).setCheckState(Qt.Checked)

    def unselect_all_fields(self):
        for i in range(self.lst_fields.count()):
            self.lst_fields.item(i).setCheckState(Qt.Unchecked)

    def selected_fields(self):
        names = []
        for i in range(self.lst_fields.count()):
            item = self.lst_fields.item(i)
            if item.checkState() == Qt.Checked:
                names.append(item.text())
        return names

    def run_tool(self):
        can_run, msg = self.lm.can_run()
        if not can_run:
            self.refresh_license_status()
            QMessageBox.warning(self, PRODUCT_NAME, msg)
            return
        if not self.lm.is_activated_local():
            if not self.lm.consume_trial_for_run():
                self.refresh_license_status()
                QMessageBox.warning(self, PRODUCT_NAME, 'Trial has expired. Please activate the license first.')
                return
            self.log_msg('Trial mode is being used. Remaining trial after this run: %s of %s.' % (self.lm.trial_remaining(), TRIAL_LIMIT))
            self.refresh_license_status()
        self._set_processing_state(True)
        self._set_progress(0, 'Preparing export...')
        try:
            output = self._process()
            self.log_msg('Done. Export includes source geometry and generated CAD text entities.')
            self.log_msg('Output: %s' % output)
            self._set_progress(100, 'Export completed.')
            QMessageBox.information(self, PRODUCT_NAME, 'Process completed.\n\nOutput: %s' % output)
            self.refresh_license_status()
        except Exception as e:
            self._set_progress(
                self.progress_bar.value(), 'Export failed.')
            self.log_msg('ERROR: %s\n%s' % (e, traceback.format_exc()))
            QMessageBox.critical(self, PRODUCT_NAME, 'Failed to run tool:\n%s' % e)
        finally:
            self._set_processing_state(False)

    def _process(self):
        self._set_progress(3, 'Validating inputs...')
        layer = self.current_layer()
        if layer is None:
            raise RuntimeError('Please select input features from the project or browse data from a folder.')
        fields = self.selected_fields()
        if not fields:
            raise RuntimeError('Select at least one attribute field.')
        output = self.txt_output.text().strip()
        if not output:
            raise RuntimeError('Please choose an output DXF file.')
        if not output.lower().endswith('.dxf'):
            output += '.dxf'

        output_dir = os.path.dirname(os.path.abspath(output))
        if not os.path.isdir(output_dir):
            raise RuntimeError('The output folder does not exist: %s' % output_dir)

        if (
                layer.geometryType() == QgsWkbTypes.PolygonGeometry
                and not layer.crs().isValid()):
            raise RuntimeError(
                'Polygon input needs a valid CRS so the automatic text height '
                'can be calculated from area in square metres.')

        self._set_progress(8, 'Preparing DXF output...')
        temp_output = output + '.cte_tmp'
        writer = SimpleDxfWriter(temp_output)
        writer.add_layer('SOURCE_FEATURES', color=7)
        for fname in fields:
            writer.add_layer(self._sanitize_layer_name(fname), color=7)
        writer.begin()

        placement = self.cmb_placement.currentText() or 'Auto'
        angle = 0.0

        try:
            self._set_progress(10, 'Exporting features and centred text...')
            total_features = max(0, int(layer.featureCount()))
            for feature_number, feat in enumerate(layer.getFeatures(), 1):
                geom = feat.geometry()
                if geom is None or geom.isEmpty():
                    self._set_progress_fraction(
                        10, 92, feature_number, total_features,
                        'Exporting features and centred text...')
                    continue
                writer.add_geometry(geom, 'SOURCE_FEATURES')
                anchor = self._anchor_point(geom, layer.geometryType(), placement)
                if anchor is None:
                    self._set_progress_fraction(
                        10, 92, feature_number, total_features,
                        'Exporting features and centred text...')
                    continue
                labels = []
                for fname in fields:
                    value = feat[fname] if layer.fields().indexOf(fname) != -1 else None
                    if value is None:
                        continue
                    txt = self._to_string(value)
                    if not txt.strip():
                        continue
                    labels.append((fname, txt))

                area_m2 = self._feature_area_m2(geom, layer)
                height = text_height_for_area(area_m2)
                pitch = line_pitch(height)
                offsets = vertical_offsets(len(labels))
                for (fname, txt), row_offset in zip(labels, offsets):
                    x = float(anchor.x())
                    y = float(anchor.y()) + (pitch * row_offset)
                    writer.add_text(x, y, txt, self._sanitize_layer_name(fname), height=height, angle=angle)

                self._set_progress_fraction(
                    10, 92, feature_number, total_features,
                    'Exporting features and centred text...')

            self._set_progress(95, 'Finalising DXF structure...')
            writer.end()
            self._set_progress(98, 'Validating DXF output...')
            SimpleDxfWriter.validate_file(temp_output)
            os.replace(temp_output, output)
            self._set_progress(100, 'Export completed.')
            self.log_msg('DXF compatibility: AutoCAD R12 ASCII (Windows CRLF).')
        except Exception:
            writer.abort()
            try:
                if os.path.exists(temp_output):
                    os.remove(temp_output)
            except Exception:
                pass
            raise
        return output

    def _feature_area_m2(self, geom, layer):
        if layer.geometryType() != QgsWkbTypes.PolygonGeometry:
            return None
        calculator = QgsDistanceArea()
        calculator.setSourceCrs(
            layer.crs(), QgsProject.instance().transformContext())
        ellipsoid = QgsProject.instance().ellipsoid()
        if not ellipsoid or str(ellipsoid).upper() == 'NONE':
            ellipsoid = 'WGS84'
        calculator.setEllipsoid(ellipsoid)
        measured = calculator.measureArea(geom)
        area_m2 = calculator.convertAreaMeasurement(
            measured, QgsUnitTypes.AreaSquareMeters)
        return abs(float(area_m2))

    def _to_string(self, value):
        try:
            return str(value)
        except Exception:
            return ''

    def _anchor_point(self, geom, geom_type, placement):
        try:
            if geom_type == QgsWkbTypes.PolygonGeometry:
                if placement == 'Centroid (Polygon)':
                    g = geom.centroid()
                else:
                    g = geom.pointOnSurface()
                return g.asPoint()
            if geom_type == QgsWkbTypes.LineGeometry:
                try:
                    return geom.interpolate(geom.length() * 0.5).asPoint()
                except Exception:
                    return geom.centroid().asPoint()
            return geom.asPoint() if geom_type == QgsWkbTypes.PointGeometry else geom.centroid().asPoint()
        except Exception:
            try:
                return geom.centroid().asPoint()
            except Exception:
                return None

    def _sanitize_layer_name(self, text):
        name = str(text or 'TXT_ATTR').strip().replace(' ', '_')
        name = re.sub(r'[^A-Za-z0-9_\\-]', '', name)
        return (name or 'TXT_ATTR')[:255]


class _SimpleDxfWriter(object):
    VERSION_CODES = {
        'DXF_R2013': 'AC1027',
        'DXF_R2010': 'AC1024',
        'DXF_R2007': 'AC1021',
        'DXF_R2004': 'AC1018',
        'DXF_R2000': 'AC1015',
    }

    def __init__(self, path, version='DXF_R2013'):
        self.path = path
        self.layers = {}
        self.version = version if version in self.VERSION_CODES else 'DXF_R2013'
        self.f = None
        self._started = False
        self._ended = False
        self._next_entity_handle = 0x1000

    def _safe_text(self, value):
        text = str(value if value is not None else '')
        text = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
        text = text.replace('\x00', '')[:250]

        # Keep the DXF stream ASCII-safe. AutoCAD-compatible Unicode escapes
        # prevent non-ASCII attribute values from corrupting group-code lines.
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

    def _safe_number(self, value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('DXF coordinate is not a finite number: %r' % value)
        return format(number, '.15g')

    def _write_pair(self, f, code, value):
        code_text = str(code)
        value_text = str(value)
        if '\n' in code_text or '\r' in code_text or '\n' in value_text or '\r' in value_text:
            raise ValueError('DXF group codes and values must each occupy exactly one line.')
        f.write(code_text + '\n')
        f.write(value_text + '\n')

    def _new_entity_handle(self):
        handle = format(self._next_entity_handle, 'X')
        self._next_entity_handle += 1
        return handle

    def _write_table_header(self, name, handle, count):
        self._write_pair(self.f, 0, 'TABLE')
        self._write_pair(self.f, 2, name)
        self._write_pair(self.f, 5, handle)
        self._write_pair(self.f, 330, 0)
        self._write_pair(self.f, 100, 'AcDbSymbolTable')
        self._write_pair(self.f, 70, count)

    def _write_ltype_table(self):
        self._write_table_header('LTYPE', '2', 1)
        self._write_pair(self.f, 0, 'LTYPE')
        self._write_pair(self.f, 5, '10')
        self._write_pair(self.f, 330, '2')
        self._write_pair(self.f, 100, 'AcDbSymbolTableRecord')
        self._write_pair(self.f, 100, 'AcDbLinetypeTableRecord')
        self._write_pair(self.f, 2, 'CONTINUOUS')
        self._write_pair(self.f, 70, 0)
        self._write_pair(self.f, 3, 'Solid line')
        self._write_pair(self.f, 72, 65)
        self._write_pair(self.f, 73, 0)
        self._write_pair(self.f, 40, 0.0)
        self._write_pair(self.f, 0, 'ENDTAB')

    def _write_layer_table(self):
        self._write_table_header('LAYER', '3', len(self.layers))
        for index, (name, color) in enumerate(self.layers.items()):
            self._write_pair(self.f, 0, 'LAYER')
            self._write_pair(self.f, 5, format(0x30 + index, 'X'))
            self._write_pair(self.f, 330, '3')
            self._write_pair(self.f, 100, 'AcDbSymbolTableRecord')
            self._write_pair(self.f, 100, 'AcDbLayerTableRecord')
            self._write_pair(self.f, 2, name)
            self._write_pair(self.f, 70, 0)
            self._write_pair(self.f, 62, color)
            self._write_pair(self.f, 6, 'CONTINUOUS')
        self._write_pair(self.f, 0, 'ENDTAB')

    def _write_style_table(self):
        self._write_table_header('STYLE', '4', 1)
        self._write_pair(self.f, 0, 'STYLE')
        self._write_pair(self.f, 5, '11')
        self._write_pair(self.f, 330, '4')
        self._write_pair(self.f, 100, 'AcDbSymbolTableRecord')
        self._write_pair(self.f, 100, 'AcDbTextStyleTableRecord')
        self._write_pair(self.f, 2, 'STANDARD')
        self._write_pair(self.f, 70, 0)
        self._write_pair(self.f, 40, 0.0)
        self._write_pair(self.f, 41, 1.0)
        self._write_pair(self.f, 50, 0.0)
        self._write_pair(self.f, 71, 0)
        self._write_pair(self.f, 42, 2.5)
        self._write_pair(self.f, 3, 'txt')
        self._write_pair(self.f, 4, '')
        self._write_pair(self.f, 0, 'ENDTAB')

    def _write_block_record_table(self):
        self._write_table_header('BLOCK_RECORD', '5', 2)
        for handle, name in (('1F', '*MODEL_SPACE'), ('20', '*PAPER_SPACE')):
            self._write_pair(self.f, 0, 'BLOCK_RECORD')
            self._write_pair(self.f, 5, handle)
            self._write_pair(self.f, 330, '5')
            self._write_pair(self.f, 100, 'AcDbSymbolTableRecord')
            self._write_pair(self.f, 100, 'AcDbBlockTableRecord')
            self._write_pair(self.f, 2, name)
            self._write_pair(self.f, 70, 0)
            self._write_pair(self.f, 280, 1)
            self._write_pair(self.f, 281, 0)
        self._write_pair(self.f, 0, 'ENDTAB')

    def _write_block(self, name, owner_handle, block_handle, end_handle):
        self._write_pair(self.f, 0, 'BLOCK')
        self._write_pair(self.f, 5, block_handle)
        self._write_pair(self.f, 330, owner_handle)
        self._write_pair(self.f, 100, 'AcDbEntity')
        self._write_pair(self.f, 8, '0')
        self._write_pair(self.f, 100, 'AcDbBlockBegin')
        self._write_pair(self.f, 2, name)
        self._write_pair(self.f, 70, 0)
        self._write_pair(self.f, 10, 0.0)
        self._write_pair(self.f, 20, 0.0)
        self._write_pair(self.f, 30, 0.0)
        self._write_pair(self.f, 3, name)
        self._write_pair(self.f, 1, '')
        self._write_pair(self.f, 0, 'ENDBLK')
        self._write_pair(self.f, 5, end_handle)
        self._write_pair(self.f, 330, owner_handle)
        self._write_pair(self.f, 100, 'AcDbEntity')
        self._write_pair(self.f, 8, '0')
        self._write_pair(self.f, 100, 'AcDbBlockEnd')

    def begin(self):
        if self._started:
            raise RuntimeError('DXF writer has already been started.')
        if '0' not in self.layers:
            registered_layers = self.layers
            self.layers = {'0': 7}
            self.layers.update(registered_layers)
        self.f = open(self.path, 'w', encoding='ascii', newline='\n')
        self._started = True
        self._write_pair(self.f, 0, 'SECTION')
        self._write_pair(self.f, 2, 'HEADER')
        self._write_pair(self.f, 9, '$ACADVER')
        self._write_pair(self.f, 1, self.VERSION_CODES[self.version])
        self._write_pair(self.f, 9, '$DWGCODEPAGE')
        self._write_pair(self.f, 3, 'ANSI_1252')
        self._write_pair(self.f, 9, '$HANDSEED')
        self._write_pair(self.f, 5, 'FFFFF')
        self._write_pair(self.f, 0, 'ENDSEC')

        self._write_pair(self.f, 0, 'SECTION')
        self._write_pair(self.f, 2, 'TABLES')
        self._write_ltype_table()
        self._write_layer_table()
        self._write_style_table()
        self._write_block_record_table()
        self._write_pair(self.f, 0, 'ENDSEC')

        self._write_pair(self.f, 0, 'SECTION')
        self._write_pair(self.f, 2, 'BLOCKS')
        self._write_block('*MODEL_SPACE', '1F', '21', '22')
        self._write_block('*PAPER_SPACE', '20', '23', '24')
        self._write_pair(self.f, 0, 'ENDSEC')

        self._write_pair(self.f, 0, 'SECTION')
        self._write_pair(self.f, 2, 'ENTITIES')

    def add_layer(self, name, color=7):
        if self._started:
            raise RuntimeError('DXF layers must be registered before writing begins.')
        if name in self.layers:
            return
        self.layers[name] = int(color)

    def _start_entities_if_needed(self):
        if not self._started or self.f is None:
            raise RuntimeError('DXF writer must be started before adding entities.')
        if self._ended:
            raise RuntimeError('DXF writer has already been finalized.')

    def _write_entity_header(self, entity_type, layer, subclass):
        self._start_entities_if_needed()
        self._write_pair(self.f, 0, entity_type)
        self._write_pair(self.f, 5, self._new_entity_handle())
        self._write_pair(self.f, 330, '1F')
        self._write_pair(self.f, 100, 'AcDbEntity')
        self._write_pair(self.f, 8, layer)
        self._write_pair(self.f, 100, subclass)

    def add_text(self, x, y, text, layer, height=20.0, angle=0.0):
        self._write_entity_header('TEXT', layer, 'AcDbText')
        self._write_pair(self.f, 10, self._safe_number(x))
        self._write_pair(self.f, 20, self._safe_number(y))
        self._write_pair(self.f, 30, 0)
        self._write_pair(self.f, 40, self._safe_number(height))
        self._write_pair(self.f, 1, self._safe_text(text))
        self._write_pair(self.f, 50, self._safe_number(angle))
        self._write_pair(self.f, 7, 'STANDARD')
        self._write_pair(self.f, 72, 1)
        self._write_pair(self.f, 73, 2)
        self._write_pair(self.f, 11, self._safe_number(x))
        self._write_pair(self.f, 21, self._safe_number(y))
        self._write_pair(self.f, 31, 0)

    def add_point(self, x, y, layer):
        self._write_entity_header('POINT', layer, 'AcDbPoint')
        self._write_pair(self.f, 10, self._safe_number(x))
        self._write_pair(self.f, 20, self._safe_number(y))
        self._write_pair(self.f, 30, 0)

    def add_lwpolyline(self, points, layer, closed=False):
        if not points:
            return
        self._write_entity_header('LWPOLYLINE', layer, 'AcDbPolyline')
        self._write_pair(self.f, 90, len(points))
        self._write_pair(self.f, 70, 1 if closed else 0)
        for pt in points:
            self._write_pair(self.f, 10, self._safe_number(pt.x()))
            self._write_pair(self.f, 20, self._safe_number(pt.y()))

    def add_geometry(self, geom, layer):
        try:
            wkb = geom.wkbType()
            geom_type = QgsWkbTypes.geometryType(wkb)
            is_multi = QgsWkbTypes.isMultiType(wkb)
            if geom_type == QgsWkbTypes.PointGeometry:
                if is_multi:
                    for pt in geom.asMultiPoint():
                        self.add_point(float(pt.x()), float(pt.y()), layer)
                else:
                    pt = geom.asPoint()
                    self.add_point(float(pt.x()), float(pt.y()), layer)
            elif geom_type == QgsWkbTypes.LineGeometry:
                if is_multi:
                    for line in geom.asMultiPolyline():
                        self.add_lwpolyline(line, layer, closed=False)
                else:
                    self.add_lwpolyline(geom.asPolyline(), layer, closed=False)
            elif geom_type == QgsWkbTypes.PolygonGeometry:
                if is_multi:
                    for poly in geom.asMultiPolygon():
                        for ring in poly:
                            self.add_lwpolyline(ring, layer, closed=True)
                else:
                    for ring in geom.asPolygon():
                        self.add_lwpolyline(ring, layer, closed=True)
        except Exception:
            pass

    def end(self):
        self._start_entities_if_needed()
        self._write_pair(self.f, 0, 'ENDSEC')
        self._write_pair(self.f, 0, 'SECTION')
        self._write_pair(self.f, 2, 'OBJECTS')
        self._write_pair(self.f, 0, 'DICTIONARY')
        self._write_pair(self.f, 5, 'C')
        self._write_pair(self.f, 330, 0)
        self._write_pair(self.f, 100, 'AcDbDictionary')
        self._write_pair(self.f, 281, 1)
        self._write_pair(self.f, 0, 'ENDSEC')
        self._write_pair(self.f, 0, 'EOF')
        self.f.close()
        self.f = None
        self._ended = True

    def abort(self):
        if self.f is not None:
            try:
                self.f.close()
            except Exception:
                pass
            self.f = None

    @staticmethod
    def validate_file(path):
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise RuntimeError('DXF output was not created or is empty.')

        with open(path, 'r', encoding='ascii') as stream:
            lines = [line.rstrip('\r\n') for line in stream]

        if len(lines) % 2 != 0:
            raise RuntimeError('Invalid DXF structure: group-code pairs are incomplete.')
        pairs = list(zip(lines[0::2], lines[1::2]))
        if not pairs or pairs[0] != ('0', 'SECTION') or pairs[-1] != ('0', 'EOF'):
            raise RuntimeError('Invalid DXF structure: missing SECTION or EOF markers.')

        required_sections = {'HEADER', 'TABLES', 'BLOCKS', 'ENTITIES'}
        found_sections = set()
        for index, pair in enumerate(pairs[:-1]):
            try:
                int(pair[0])
            except ValueError:
                raise RuntimeError('Invalid DXF group code: %s' % pair[0])
            if pair == ('0', 'SECTION') and pairs[index + 1][0] == '2':
                found_sections.add(pairs[index + 1][1])
        missing = required_sections.difference(found_sections)
        if missing:
            raise RuntimeError('Invalid DXF structure: missing section(s): %s' % ', '.join(sorted(missing)))
